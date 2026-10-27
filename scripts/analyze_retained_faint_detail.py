"""Predeclared faint-detail analysis using existing predictions and source strata."""

import argparse
import hashlib
import os
import sys
from itertools import pairwise
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from report_checkpoint_pilot import band, checked
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import display, linear_rgb, noisy_malvar

EDGES = (0, 0.02, 0.05, 0.1, 0.2, np.inf)


def error_components(prediction, target):
    error = np.asarray(prediction, dtype=np.float64) - np.asarray(target, dtype=np.float64)
    dc = error.mean((-1, -2), keepdims=True)
    total, bias, spatial = [float(np.mean(x * x)) for x in [error, dc, error - dc]]
    np.testing.assert_allclose(total, bias + spatial, rtol=1e-13, atol=1e-30)
    return {
        "MSE": total,
        "DC_MSE": bias,
        "spatial_MSE": spatial,
        "DC_fraction": bias / total if total else 0.0,
    }


def original_source_strata(original, prediction, faint_target, arrays):
    original, prediction, faint_target = [
        linear_rgb(np.asarray(x[..., 48:208, 48:208], dtype=np.float64), arrays)
        for x in (original, prediction, faint_target)
    ]
    coeff, means = band(original)
    rms = np.linalg.norm(coeff[0], axis=-1) / 16
    valid = ((original[0] >= 0) & (original[0] <= 1)).all(0)
    valid = valid.reshape(10, 16, 10, 16).transpose(0, 2, 1, 3).reshape(100, 256).all(1)
    valid &= (means[0] >= 0.02) & (means[0] <= 0.9) & (rms >= 1e-5)
    contrast = rms / np.maximum(means[0], 1e-12)
    p, _ = band(prediction)
    t, _ = band(faint_target)
    rows = []
    for index, (low, high) in enumerate(pairwise(EDGES)):
        selected = valid & (contrast >= low) & (contrast < high)
        if not selected.any():
            continue
        a, b = p[0, selected].ravel(), t[0, selected].ravel()
        denominator = np.dot(b, b)
        if denominator <= 0:
            raise ValueError("Original-source stratum has zero faint target energy")
        rows.append(
            {
                "original_bin": index,
                "blocks": int(selected.sum()),
                "mask_sha256": hashlib.sha256(selected.tobytes()).hexdigest(),
                "gain": float(np.dot(a, b) / denominator),
                "relative_band_error": float(np.linalg.norm(a - b) / np.sqrt(denominator)),
            }
        )
    return rows


def enhanced_pixels(value, original, arrays, factor=40):
    dc = np.asarray(original, dtype=np.float64).mean((-1, -2), keepdims=True)
    enhanced = dc + factor * (np.asarray(value, dtype=np.float64) - dc)
    rendered = display(enhanced, arrays, 1)
    return np.rint(rendered[0, :, 48:208, 48:208].transpose(1, 2, 0) * 255).astype(np.uint8)


def analyze(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Retained faint analysis requires CPU-only NumPy without Torch")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    policy = read(path)
    guard(policy)
    if ref(__file__) != policy["operator"]:
        raise ValueError("Use the prospectively frozen analysis source")
    quality_root = Path(policy["quality_root"])
    status = read(quality_root / "status.json")
    assert status["owner"] == policy["quality_owner"]
    assert status["status"] == "completed-global1000-review-awaiting-actual-native-viewing"
    execution = read(quality_root / "plan-v1.json")
    guard(execution)
    collection = read(quality_root / "collection-v1.json")
    assert collection["plan"] == ref(quality_root / "plan-v1.json")
    assert collection["counts"] == {"root": 102, "encoder": 102}
    report = read(quality_root / "report-v1/report.json")
    assert read(quality_root / "independent-audit-v1.json")["status"].startswith("passed")
    new = {r["id"]: r for r in collection["observations"]}
    expected = {(r["case"], r["pattern"], r["method"]): r for r in report["metrics"]}
    observations = [o for o in execution["observations"] if o["id"] in policy["observation_ids"]]
    assert len(observations) == len(policy["observation_ids"]) == 16
    out = Path(policy["output"])
    out.mkdir(exist_ok=False)
    decomposition, strata, images = [], [], []
    for o in observations:
        assert o["noise"]["shot"] == o["noise"]["read"] == 0
        assert o["case"]["additional_contrast_factor"] == 0.025
        with np.load(checked(o["arrays"])) as f:
            arrays = {k: f[k] for k in f.files}
        with np.load(checked(o["case"]["original_target"])) as f:
            original = f["target"]
        with np.load(checked(o["target"])) as f:
            target = f["target"]
        predictions = [
            (c["model"]["label"], np.load(checked(c["prediction"]))) for c in o["controls"]
        ]
        predictions += [(execution["model_label"], np.load(checked(new[o["id"]]["prediction"])))]
        assert [label for label, p in predictions] == policy["methods"]
        for label, prediction in predictions:
            a, b = [x[..., 48:208, 48:208].astype(np.float64) for x in (prediction, target)]
            for space, x, y, score in [
                ("camera", a.clip(0, 1), b.clip(0, 1), "camera_RGB_PSNR"),
                ("sRGB", display(a, arrays), display(b, arrays), "sRGB_PSNR"),
            ]:
                components = error_components(x, y)
                psnr = -10 * np.log10(max(components["MSE"], 1e-12))
                assert abs(psnr - expected[o["case_id"], o["pattern"], label][score]) < 1e-11
                decomposition.append(
                    {
                        "case": o["case_id"],
                        "pattern": o["pattern"],
                        "method": label,
                        "space": space,
                        **components,
                    }
                )
            strata += [
                {
                    "case": o["case"]["original_case_id"],
                    "pattern": o["pattern"],
                    "method": label,
                    **r,
                }
                for r in original_source_strata(original, prediction, target, arrays)
            ]
        if o["pattern"] != "RGGB":
            continue
        role = "GT synthetic" if o["reference_role"].startswith("Exact") else "Binned ref, not GT"
        panels = [("ADC Malvar", noisy_malvar(arrays)), *predictions, (role, target)]
        canvas = Image.new("RGB", (8 + 168 * len(panels), 192), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        cells = []
        for i, (label, value) in enumerate(panels):
            pixels = enhanced_pixels(value, original, arrays, policy["display_contrast"])
            x, y = 8 + 168 * i, 24
            draw.text((x, 5), label, fill="black")
            canvas.paste(Image.fromarray(pixels), (x, y))
            cells.append({"label": label, "xywh": [x, y, 160, 160]})
        dest = out / (o["case_id"] + "-contrast40.png")
        canvas.save(dest)
        reread = np.asarray(Image.open(dest))
        for cell, (_, value) in zip(cells, panels, strict=True):
            x, y, w, h = cell["xywh"]
            np.testing.assert_array_equal(
                reread[y : y + h, x : x + w], enhanced_pixels(value, original, arrays)
            )
        images.append(
            {
                "image": ref(dest),
                "observation_id": o["id"],
                "panels": cells,
                "case": o["case"],
                "ROI_xywh": [48, 48, 160, 160],
                "reference_role": o["reference_role"],
                "checkpoint": execution["checkpoint"],
                "noise": o["noise"],
                "display_exposure": 1,
                "display_contrast": 40,
                "common_DC_source": o["case"]["original_target"],
                "no_resize": True,
            }
        )
    assert len(decomposition) == 96 and len(images) == 4
    save(
        out / "result-v1.json",
        {
            "status": "completed-predeclared-retained-faint-detail-supplement",
            "analysis_plan": ref(path),
            "primary_collection": ref(quality_root / "collection-v1.json"),
            "decomposition": decomposition,
            "original_source_strata": strata,
            "images": images,
            "PNG_panel_channels_checked": sum(len(i["panels"]) * 160 * 160 * 3 for i in images),
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "optimizer_updates": 0,
            "scope": policy["scope"],
        },
    )
    return out / "result-v1.json"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    print(analyze(p.parse_args().plan.resolve()))
