"""Independently recompute retained-pilot FFT/detail scores and native PNG cells."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import noisy_malvar


def rgb(value, data):
    value = value.astype(np.float64) * data["wb"].astype(np.float64)[..., None, None]
    return np.stack(
        [sum(value[:, j] * float(data["matrix"][0, i, j]) for j in range(3)) for i in range(3)],
        axis=1,
    )


def srgb(value):
    v = value.clip(0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)


def coefficients(value, data):
    rendered = rgb(value[..., 48:208, 48:208], data)
    luma = sum(rendered[:, i] * w for i, w in enumerate([0.2126, 0.7152, 0.0722]))
    blocks = np.stack(
        [luma[0, y : y + 16, x : x + 16] for y in range(0, 160, 16) for x in range(0, 160, 16)]
    )

    def dct_axis(a):
        mirrored = np.concatenate([a, a[..., ::-1]], axis=-1)
        result = (
            np.fft.fft(mirrored, axis=-1)[..., :16] * np.exp(-1j * np.pi * np.arange(16) / 32)
        ).real / 2
        scale = np.full(16, np.sqrt(2 / 16))
        scale[0] = np.sqrt(1 / 16)
        return result * scale

    transformed = dct_axis(dct_axis(blocks).swapaxes(-1, -2)).swapaxes(-1, -2)
    radius = np.sqrt(np.add.outer((np.arange(16) / 32) ** 2, (np.arange(16) / 32) ** 2))
    return transformed[:, (radius >= 0.125) & (radius < 1 / 3)], blocks.mean((-1, -2)), rendered


def crop(value, data, roi, exposure):
    x, y, w, h = roi
    rendered = srgb(rgb(value.astype(np.float64) * exposure, data))
    return np.rint(rendered[0, :, y : y + h, x : x + w].transpose(1, 2, 0) * 255).astype(np.uint8)


def checked(binding):
    assert ref(binding["path"]) == binding
    return binding["path"]


def audit(root, output=None):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Independent audit requires CPU without Torch")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    plan_path = root / "plan-v1.json"
    plan = read(plan_path)
    guard(plan)
    report_path = root / "report-v1/report.json"
    report = read(report_path)
    collection = read(root / "collection-v1.json")
    assert collection["plan"] == ref(plan_path)
    output = root if output is None else output
    output.mkdir(parents=True, exist_ok=True)
    assert not (output / "independent-audit-v1.json").exists()
    (output / "independent-audit.claim").open("x").close()
    save(
        output / "independent-audit-plan-v1.json",
        {
            "plan": ref(plan_path),
            "report": ref(report_path),
            "collection": ref(root / "collection-v1.json"),
            "auditor": ref(__file__),
            "scope": "Channelwise FP64 display, independently mirrored-FFT DCT16 and every native PNG cell. No model/noise/RAW work. Shared independently verified NumPy Malvar preview only.",
        },
    )
    newrows = {r["id"]: r for r in collection["observations"]}
    measured = {(r["case"], r["method"], r["pattern"]): r for r in report["metrics"]}
    assert len(measured) == len(report["metrics"])
    images = {r["name"]: r for r in report["images"]}
    maximum = {"score_dB": 0.0, "gain": 0.0, "band_error_RMS": 0.0, "orthogonal_residual_RMS": 0.0}
    metric_fields = png_channels = 0
    rows_checked, images_checked = set(), set()
    independent_rows = []

    def check_board(name, cells):
        nonlocal png_channels
        row = images[name]
        png = np.asarray(Image.open(checked(row["image"])))
        for cell, panel in zip(cells, row["panels"], strict=True):
            x, y, w, h = panel["png_xywh"]
            assert (w, h) == (160, 160)
            np.testing.assert_array_equal(
                png[y : y + h, x : x + w], cell, err_msg=f"{name}: {panel['label']}"
            )
            png_channels += cell.size
        images_checked.add(name)

    for o in plan["observations"]:
        with np.load(checked(o["arrays"]), allow_pickle=False) as archive:
            data = {k: archive[k] for k in archive.files}
        new = np.load(checked(newrows[o["id"]]["prediction"]), allow_pickle=False)
        preds = [
            (
                c.get("label", c.get("model", {}).get("label")),
                np.load(checked(c["prediction"]), allow_pickle=False),
            )
            for c in o.get("controls", [])
        ] + [(report["model_label"], new)]
        exposure = o["display_exposure"]
        if o["kind"] in {"material", "shadow-material"}:
            with np.load(checked(o["target"]), allow_pickle=False) as archive:
                target = archive["target"]
            t, means, truth = coefficients(target.astype(np.float64) * exposure, data)
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
            case_id = o["case_id"] + (
                "-" + o["noise"]["name"] if o["kind"] == "shadow-material" else ""
            )
            for method, pred in preds:
                key = (case_id, method, o["pattern"])
                row = measured[key]
                a, b = [
                    v[..., 48:208, 48:208].astype(np.float64) * exposure for v in (pred, target)
                ]
                cam = -10 * np.log10(max(np.mean((a.clip(0, 1) - b.clip(0, 1)) ** 2), 1e-12))
                score = -10 * np.log10(
                    max(np.mean((srgb(rgb(a, data)) - srgb(rgb(b, data))) ** 2), 1e-12)
                )
                maximum["score_dB"] = max(
                    maximum["score_dB"],
                    abs(cam - row["camera_RGB_PSNR"]),
                    abs(score - row["sRGB_PSNR"]),
                )
                metric_fields += 2
                p, _, _ = coefficients(pred.astype(np.float64) * exposure, data)
                edges = (0, 0.02, 0.05, 0.1, 0.2, np.inf)
                expected_bins = {
                    k
                    for k in range(5)
                    if np.any(valid & (contrast >= edges[k]) & (contrast < edges[k + 1]))
                }
                assert {entry["bin"] for entry in row["bands"]} == expected_bins
                independently_measured_bands = []
                for entry in row["bands"]:
                    k = entry["bin"]
                    keep = valid & (contrast >= edges[k]) & (contrast < edges[k + 1])
                    n = int(keep.sum())
                    assert n == entry["blocks"]
                    gain = np.dot(p[keep].ravel(), t[keep].ravel()) / np.dot(
                        t[keep].ravel(), t[keep].ravel()
                    )
                    values = {
                        "gain": gain,
                        "band_error_RMS": np.linalg.norm(p[keep] - t[keep]) / np.sqrt(n * 256),
                        "orthogonal_residual_RMS": np.linalg.norm(p[keep] - gain * t[keep])
                        / np.sqrt(n * 256),
                    }
                    for k, value in values.items():
                        maximum[k] = max(maximum[k], abs(value - entry[k]))
                        metric_fields += 1
                    independently_measured_bands.append(
                        {"bin": entry["bin"], "blocks": n, **values}
                    )
                independent_rows.append(
                    {
                        "case": case_id,
                        "method": method,
                        "pattern": o["pattern"],
                        "camera_RGB_PSNR": cam,
                        "sRGB_PSNR": score,
                        "bands": independently_measured_bands,
                    }
                )
                rows_checked.add(key)
            if o["pattern"] != "RGGB":
                continue
            roi = o["ROI_xywh"]
            noisy = crop(noisy_malvar(data), data, roi, exposure)
            gt = crop(target, data, roi, exposure)
            check_board(
                case_id + "-comparison",
                [noisy] + [crop(p, data, roi, exposure) for _, p in preds] + [gt],
            )
            check_board(case_id + "-triplet", [noisy, crop(new, data, roi, exposure), gt])
        elif o["kind"] == "gfx":
            target = np.load(checked(o["target"]), allow_pickle=False)
            roi = o["ROI_xywh"]
            noisy = crop(noisy_malvar(data), data, roi, exposure)
            gt = crop(target, data, [0, 0, 160, 160], exposure)
            check_board(
                o["id"] + "-comparison",
                [noisy] + [crop(p, data, roi, exposure) for _, p in preds] + [gt],
            )
            check_board(o["id"] + "-triplet", [noisy, crop(new, data, roi, exposure), gt])
        else:
            for case in o["cases"]:
                roi = case["ROI_xywh"]
                noisy = crop(data["noisy_rgb"], data, roi, exposure)
                gt = crop(data["reference_rgb"], data, roi, exposure)
                name = o["id"] + "-" + case["name"]
                check_board(
                    name + "-comparison",
                    [noisy] + [crop(p, data, roi, exposure) for _, p in preds] + [gt],
                )
                check_board(name + "-triplet", [noisy, crop(new, data, roi, exposure), gt])
    assert rows_checked == set(measured) and images_checked == set(images)
    for summary in report["summaries"]:
        selected = [
            r
            for r in independent_rows
            if (r["case"], r["method"]) == (summary["case"], summary["method"])
        ]
        assert len(selected) == 4 and {r["pattern"] for r in selected} == {
            "RGGB",
            "BGGR",
            "GRBG",
            "GBRG",
        }
        for score_key in ("camera_RGB_PSNR", "sRGB_PSNR"):
            maximum["score_dB"] = max(
                maximum["score_dB"],
                abs(float(np.mean([r[score_key] for r in selected])) - summary[score_key]),
            )
            metric_fields += 1
        for entry in summary["bands"]:
            matched = [next(b for b in r["bands"] if b["bin"] == entry["bin"]) for r in selected]
            assert {b["blocks"] for b in matched} == {entry["blocks"]}
            for key in ("gain", "band_error_RMS", "orthogonal_residual_RMS"):
                maximum[key] = max(
                    maximum[key], abs(float(np.mean([b[key] for b in matched])) - entry[key])
                )
                metric_fields += 1
    assert (
        maximum["score_dB"] < 1e-11 and max(maximum[k] for k in maximum if k != "score_dB") < 1e-10
    )
    assert png_channels == report["PNG_channels_verified"]
    assert "torch" not in sys.modules
    result = {
        "status": "passed-independent-FFT-metric-and-native-pixel-audit",
        "audit_plan": ref(output / "independent-audit-plan-v1.json"),
        "maximum_absolute_errors": maximum,
        "metric_fields": metric_fields,
        "metric_rows": len(rows_checked),
        "summary_groups": len(report["summaries"]),
        "PNG_channels_exact": png_channels,
        "PNG_images": len(images_checked),
        "root_forwards": 0,
        "encoder_forwards": 0,
        "RAW_decodes": 0,
        "new_noise_observations": 0,
        "optimizer_updates": 0,
        "Torch_imported": False,
        "scope": "All retained material methods/CFAs and published native cells, independently recomputed. Real low-ISO and native-binned references remain approximate; no real-reference PSNR or model recommendation.",
    }
    save(output / "independent-audit-v1.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(audit(args.root.resolve(), args.output.resolve() if args.output else None))
