"""Audit retained faint-detail reductions with mirrored FFT and channelwise display."""

import argparse
import hashlib
import os
import sys
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import checked, coefficients, crop, rgb, srgb
from PIL import Image
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import noisy_malvar


def audit(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Independent faint audit requires CPU-only NumPy without Torch")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    policy = read(path)
    guard(policy)
    assert ref(__file__) == policy["auditor"]
    root, output = Path(policy["quality_root"]), Path(policy["output"])
    result = read(output / "result-v1.json")
    assert result["analysis_plan"] == ref(path)
    assert result["primary_collection"] == ref(root / "collection-v1.json")
    (output / "independent-audit.claim").open("x").close()
    plan = read(root / "plan-v1.json")
    guard(plan)
    collection = read(root / "collection-v1.json")
    assert collection["plan"] == ref(root / "plan-v1.json")
    assert collection["counts"] == {"root": 102, "encoder": 102}
    newrows = {r["id"]: r for r in collection["observations"]}
    strata = {
        (r["case"], r["pattern"], r["method"], r["original_bin"]): r
        for r in result["original_source_strata"]
    }
    decomposition = {
        (r["case"], r["pattern"], r["method"], r["space"]): r for r in result["decomposition"]
    }
    images = {r["observation_id"]: r for r in result["images"]}
    assert len(strata) == len(result["original_source_strata"])
    assert len(decomposition) == len(result["decomposition"])
    assert len(images) == len(result["images"]) == 4
    checked_strata, checked_decomposition, checked_observations = set(), set(), set()
    png_channels = 0
    max_strata = max_decomposition = 0.0
    for o in plan["observations"]:
        if o["id"] not in policy["observation_ids"]:
            continue
        checked_observations.add(o["id"])
        with np.load(checked(o["arrays"])) as f:
            data = {k: f[k] for k in f.files}
        with np.load(checked(o["case"]["original_target"])) as f:
            original = f["target"]
        with np.load(checked(o["target"])) as f:
            target = f["target"]
        predictions = [
            (c["model"]["label"], np.load(checked(c["prediction"]))) for c in o["controls"]
        ] + [(plan["model_label"], np.load(checked(newrows[o["id"]]["prediction"])))]
        assert [label for label, p in predictions] == policy["methods"]
        old, means, rendered = coefficients(original, data)
        rms = np.linalg.norm(old, axis=1) / 16
        valid = np.array(
            [
                np.all(
                    (rendered[0, :, y : y + 16, x : x + 16] >= 0)
                    & (rendered[0, :, y : y + 16, x : x + 16] <= 1)
                )
                for y in range(0, 160, 16)
                for x in range(0, 160, 16)
            ]
        )
        valid &= (means >= 0.02) & (means <= 0.9) & (rms >= 1e-5)
        contrast = rms / np.maximum(means, 1e-12)
        truth, _, _ = coefficients(target, data)
        for label, prediction in predictions:
            pred, _, _ = coefficients(prediction, data)
            edges = [0, 0.02, 0.05, 0.1, 0.2, np.inf]
            for b in range(5):
                keep = valid & (contrast >= edges[b]) & (contrast < edges[b + 1])
                if not keep.any():
                    continue
                key = (o["case"]["original_case_id"], o["pattern"], label, b)
                expected = strata[key]
                p, t = pred[keep].ravel(), truth[keep].ravel()
                values = {
                    "gain": np.dot(p, t) / np.dot(t, t),
                    "relative_band_error": np.linalg.norm(p - t) / np.linalg.norm(t),
                }
                assert int(keep.sum()) == expected["blocks"]
                assert hashlib.sha256(keep.tobytes()).hexdigest() == expected["mask_sha256"]
                max_strata = max(max_strata, *(abs(values[k] - expected[k]) for k in values))
                checked_strata.add(key)
            for space, a, b in [
                (
                    "camera",
                    prediction[..., 48:208, 48:208].clip(0, 1),
                    target[..., 48:208, 48:208].clip(0, 1),
                ),
                (
                    "sRGB",
                    srgb(rgb(prediction[..., 48:208, 48:208], data)),
                    srgb(rgb(target[..., 48:208, 48:208], data)),
                ),
            ]:
                error = (a.astype(np.longdouble) - b.astype(np.longdouble)).reshape(3, -1)
                channel_mean = np.sum(error, axis=1) / error.shape[1]
                mse = np.sum(error * error) / error.size
                dc_mse = np.dot(channel_mean, channel_mean) / 3
                spatial_mse = np.sum((error - channel_mean[:, None]) ** 2) / error.size
                values = {
                    "MSE": mse,
                    "DC_MSE": dc_mse,
                    "spatial_MSE": spatial_mse,
                    "DC_fraction": dc_mse / mse if mse else 0,
                }
                key = (o["case_id"], o["pattern"], label, space)
                max_decomposition = max(
                    max_decomposition,
                    *(float(abs(values[k] - decomposition[key][k])) for k in values),
                )
                checked_decomposition.add(key)
        if o["pattern"] == "RGGB":
            board = images[o["id"]]
            png = np.asarray(Image.open(checked(board["image"])))
            dc = original.astype(np.float64).mean((-1, -2), keepdims=True)
            values = [noisy_malvar(data), *(p for _, p in predictions), target]
            for panel, value in zip(board["panels"], values, strict=True):
                enhanced = dc + policy["display_contrast"] * (value.astype(np.float64) - dc)
                expected = crop(enhanced, data, [48, 48, 160, 160], 1)
                x, y, w, h = panel["xywh"]
                assert (w, h) == (160, 160)
                np.testing.assert_array_equal(png[y : y + h, x : x + w], expected)
                png_channels += expected.size
    assert checked_observations == set(policy["observation_ids"])
    assert checked_strata == set(strata) and checked_decomposition == set(decomposition)
    assert max_strata < 1e-10 and max_decomposition < 1e-12
    assert png_channels == result["PNG_panel_channels_checked"]
    assert png_channels == len(images) * (len(policy["methods"]) + 2) * 160 * 160 * 3
    destination = output / "independent-audit-v1.json"
    assert not destination.exists()
    save(
        destination,
        {
            "status": "passed-independent-retained-faint-detail-audit",
            "auditor": ref(__file__),
            "independent_FFT_and_display_helpers": ref(
                sys.modules["audit_checkpoint_pilot"].__file__
            ),
            "analysis_plan": ref(path),
            "result": ref(output / "result-v1.json"),
            "stratum_rows": len(checked_strata),
            "decomposition_rows": len(checked_decomposition),
            "PNG_images": len(images),
            "PNG_channels_exact": png_channels,
            "max_strata_error": max_strata,
            "max_decomposition_error": max_decomposition,
            "root_forwards": 0,
            "encoder_forwards": 0,
            "RAW_decodes": 0,
            "new_noise_observations": 0,
            "optimizer_updates": 0,
            "Torch_imported": "torch" in sys.modules,
        },
    )
    return destination


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    print(audit(p.parse_args().plan.resolve()))
