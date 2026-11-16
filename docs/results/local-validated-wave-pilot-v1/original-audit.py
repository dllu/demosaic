"""Independent scalar/FFT/native-pixel checks for the input-only local-wave pilot."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import coefficients, crop, rgb, srgb
from PIL import Image

from demosaic.archive_metrics import noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def audit(root):
    if "torch" in sys.modules:
        raise RuntimeError("Require independent CPU audit without Torch")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    plan, collection = read_json(root / "plan.json"), read_json(root / "collection.json")
    report = read_json(root / "report/report.json")
    if collection["plan"] != reference(root / "plan.json") or report["collection"] != reference(
        root / "collection.json"
    ):
        raise ValueError("Collection/report bindings differ")
    records = {r["id"]: r for r in collection["rows"]}
    material = {(r["case"], r["method"]): r for r in report["material_metrics"]}
    maximum = {"score_dB": 0.0, "band_scalar": 0.0, "finite_metric": 0.0}
    metric_fields, channels = 0, 0
    cache = {}
    for item in plan["rows"]:
        with np.load(checked(item["arrays"]), allow_pickle=False) as z:
            data = dict(z)
        sample = item["sample"]
        calibration = {k: data[k][sample : sample + 1] for k in ["wb", "matrix"]}
        physical = {
            **calibration,
            "packed": data["packed"][sample : sample + 1],
            "colors": data["colors"][sample : sample + 1],
        }
        predictions = {
            "V120": np.load(checked(item["parent"]), allow_pickle=False)[sample : sample + 1],
            **{
                k: np.load(checked(v), allow_pickle=False)[None]
                for k, v in records[item["id"]]["predictions"].items()
            },
        }
        target = None
        if item["kind"] == "finite-wire":
            target = data["target"][sample : sample + 1]
        elif item["kind"] == "material":
            with np.load(checked(item["observation"]["target"]), allow_pickle=False) as z:
                target = z["target"]
            t, means, truth = coefficients(target, calibration)
            valid = np.array(
                [
                    np.all(
                        (truth[0, :, y : y + 16, x : x + 16] >= 0)
                        & (truth[0, :, y : y + 16, x : x + 16] <= 1)
                    )
                    for y in range(0, 160, 16)
                    for x in range(0, 160, 16)
                ]
            )
            rms = np.sqrt((t * t).sum(1) / 256)
            valid &= (means >= 0.02) & (means <= 0.9) & (rms >= 1e-5)
            contrast = rms / np.maximum(means, 1e-12)
            edges = (0, 0.02, 0.05, 0.1, 0.2, np.inf)
            for method, value in predictions.items():
                recorded = material[item["id"], method]
                p, q = [v[..., 48:208, 48:208].astype(np.float64) for v in [value, target]]
                camera = -10 * np.log10(
                    max(float(np.mean((p.clip(0, 1) - q.clip(0, 1)) ** 2)), 1e-12)
                )
                displayed = -10 * np.log10(
                    max(
                        float(
                            np.mean((srgb(rgb(p, calibration)) - srgb(rgb(q, calibration))) ** 2)
                        ),
                        1e-12,
                    )
                )
                maximum["score_dB"] = max(
                    maximum["score_dB"],
                    abs(camera - recorded["camera_RGB_PSNR"]),
                    abs(displayed - recorded["sRGB_PSNR"]),
                )
                metric_fields += 2
                pband, _, _ = coefficients(value, calibration)
                expected = {
                    i
                    for i in range(5)
                    if np.any(valid & (contrast >= edges[i]) & (contrast < edges[i + 1]))
                }
                if expected != {e["bin"] for e in recorded["bands"]}:
                    raise ValueError("Reference-defined band strata differ")
                for entry in recorded["bands"]:
                    i = entry["bin"]
                    selected = valid & (contrast >= edges[i]) & (contrast < edges[i + 1])
                    a, b = pband[selected], t[selected]
                    n = int(selected.sum())
                    if n != entry["blocks"]:
                        raise ValueError("Reference band block counts differ")
                    gain = float(np.dot(a.ravel(), b.ravel()) / np.dot(b.ravel(), b.ravel()))
                    values = {
                        "gain": gain,
                        "band_error_RMS": float(np.sqrt(np.sum((a - b) ** 2) / (n * 256))),
                        "orthogonal_residual_RMS": float(
                            np.sqrt(np.sum((a - gain * b) ** 2) / (n * 256))
                        ),
                    }
                    for key, v in values.items():
                        maximum["band_scalar"] = max(maximum["band_scalar"], abs(v - entry[key]))
                        metric_fields += 1
                if records[item["id"]]["aux"]["identity_zero_noise"]:
                    np.testing.assert_array_equal(value, predictions["V120"])
        elif item["kind"] == "gfx":
            target = np.load(checked(item["observation"]["target"]), allow_pickle=False)
        else:
            target = data["reference_rgb"]
        cache[item["id"]] = (data, calibration, predictions, target, physical)
    finite = read_json(root / "finite-scores.json")
    finite_rows = {(r["source"], r["placement"], r["method"]): r for r in finite["rows"]}
    for group in plan["finite_groups"]:
        data = cache[group["cases"][0]][0]
        truth = data["target"].astype(np.float64)
        for method in cache[group["cases"][0]][2]:
            value = np.concatenate([cache[case][2][method] for case in group["cases"]]).astype(
                np.float64
            )
            error = value - truth
            expected = {}
            for name, mask in [("quiet", data["quiet"]), ("edge", data["edge_band"])]:
                e = error[..., mask]
                dc = e.mean(-1, keepdims=True)
                expected[name + "_error_RMS_DN16"] = float(np.sqrt(np.mean(e * e)) * 65535)
                expected[name + "_DC_RMS_DN16"] = float(np.sqrt(np.mean(dc * dc)) * 65535)
                expected[name + "_spatial_RMS_DN16"] = float(
                    np.sqrt(np.mean((e - dc) ** 2)) * 65535
                )
            expected["full_error_RMS_DN16"] = float(np.sqrt(np.mean(error * error)) * 65535)
            for name, a, b in [("strong", 0, 1), ("weak", 1, 2)]:
                delta = truth[b] - truth[a]
                predicted = value[b] - value[a]
                gain = float(
                    np.dot(predicted.ravel(), delta.ravel()) / np.dot(delta.ravel(), delta.ravel())
                )
                expected[name + "_gain"] = gain
                expected[name + "_increment_error_RMS_DN16"] = float(
                    np.sqrt(np.mean((predicted - delta) ** 2)) * 65535
                )
                expected[name + "_orthogonal_RMS_DN16"] = float(
                    np.sqrt(np.mean((predicted - gain * delta) ** 2)) * 65535
                )
            recorded = finite_rows[
                group["metadata"]["recipe"]["source"], group["metadata"]["placement"], method
            ]
            for k, v in expected.items():
                maximum["finite_metric"] = max(maximum["finite_metric"], abs(v - recorded[k]))
                metric_fields += 1
    for figure in report["figures"]:
        item = figure["source"]
        data, calibration, predictions, target, physical = cache[item["id"]]
        roi = figure["ROI_xywh"]
        exposure = figure["display_exposure"]
        noisy = data["noisy_rgb"] if item["kind"] == "mesh" else noisy_malvar(physical)
        png = np.asarray(Image.open(checked(figure["image"])))
        for panel in figure["panels"]:
            label = panel["label"]
            if label.startswith("SOOC"):
                key = "noisy_camera_jpeg" if "6400" in label else "reference_camera_jpeg"
                expected = np.load(
                    checked(figure["case"]["camera_JPEGs"][key]["pixels"]), allow_pickle=False
                )
            elif label == "Noisy Malvar":
                expected = crop(noisy, calibration, roi, exposure)
            elif label in ["V120", "Global support t2", "Local support t2"]:
                method = {
                    "V120": "V120",
                    "Global support t2": "global-t2",
                    "Local support t2": "local-t2",
                }[label]
                expected = crop(predictions[method], calibration, roi, exposure)
            else:
                expected = crop(target, calibration, figure["reference_ROI_xywh"], exposure)
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(png[y : y + h, x : x + w], expected)
            channels += expected.size
    if (
        maximum["score_dB"] > 1e-11
        or maximum["band_scalar"] > 1e-12
        or maximum["finite_metric"] > 1e-10
        or "torch" in sys.modules
    ):
        raise ValueError(f"Independent pilot audit differs: {maximum}")
    write_json(
        root / "independent-audit.json",
        {
            "status": "passed-local-wave-pilot-independent-metric-and-native-pixel-audit",
            "plan": reference(root / "plan.json"),
            "collection": reference(root / "collection.json"),
            "report": reference(root / "report/report.json"),
            "finite_scores": reference(root / "finite-scores.json"),
            "script": reference(__file__),
            "FFT_display_helper": reference(Path(__file__).with_name("audit_checkpoint_pilot.py")),
            "metric_fields": metric_fields,
            "PNG_channels_exact": channels,
            "PNG_boards": len(report["figures"]),
            "material_rows": len(material),
            "finite_rows": len(finite_rows),
            "maximum_absolute_errors": maximum,
            "new_neural_forwards": 0,
            "Torch_imported": False,
            "scope": "Direct finite-increment reductions, mirrored-FFT material DCT and channelwise native display, all existing JPEG cells exact. Zero-noise outputs bit-identical. Input-only inference remains distinct from target/reference scoring; independent real references never scored.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    audit(parser.parse_args().root.resolve())
