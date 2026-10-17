"""Render retained original-export GPU predictions on CPU; never run a network."""

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch
from audit_colored_flats import sha
from PIL import Image

from demosaic.cfa import PATTERNS, malvar
from demosaic.color import render
from demosaic.metrics import quality_metrics
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def read(path):
    return json.loads(Path(path).read_text())


def load_saved_case(case):
    """Load one immutable observation/reference for reuse across models and modes."""
    assert sha(case["observation"]) == case["observation_sha256"]
    if case["kind"] == "synthetic-photo":
        with np.load(case["observation"], allow_pickle=False) as values:
            batch = {k: torch.from_numpy(values[k].copy()) for k in values.files}
        target, wb, matrix = batch["target"], batch["wb"], batch["matrix"]
    else:
        assert sha(case["reference_array"]) == case["reference_array_sha256"]
        batch = {
            "packed": torch.from_numpy(np.load(case["observation"], allow_pickle=False)),
            "colors": torch.tensor([PATTERNS[case["pattern"]]]),
        }
        target = torch.from_numpy(np.load(case["reference_array"], allow_pickle=False))
        wb = torch.tensor(case["wb"], dtype=torch.float32).reshape(1, 3)
        matrix = torch.tensor(case["matrix"], dtype=torch.float32).reshape(1, 3, 3)
    return batch, target, wb, matrix


def prepare_saved_prediction(raw, case, model, observation=None):
    """Apply the published output convention without fitting to a reference."""
    assert raw.dtype == np.float32 and np.isfinite(raw).all()
    batch, target, wb, matrix = load_saved_case(case) if observation is None else observation
    assert raw.shape == (1, 3, 2 * batch["packed"].shape[-2], 2 * batch["packed"].shape[-1])
    black = float(np.mean(case["black"])) / case["adc_white"]
    subtract = model["registry"]["subtract_bl"]
    prediction = (torch.from_numpy(raw).clamp(0, 1) - (0 if subtract else black)) / (1 - black)
    # Independent float64 unit conversion, without clipping the resulting RGB.
    expected = (np.clip(raw.astype(np.float64), 0, 1) - (0 if subtract else black)) / (1 - black)
    delta = float(np.abs(expected - prediction.numpy()).max())
    assert delta < 2e-7
    return prediction, batch, target, wb, matrix, delta


@torch.inference_mode()
def main(report_path, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    report = read(report_path)
    assert (
        report["status"]
        == "completed-original-RawForge-GPU-probe-awaiting-numerical-and-native-review"
    )
    assert sha(report["plan"]) == report["plan_sha256"]
    plan = read(report["plan"])
    assert sha(plan["CPU_report"]) == plan["CPU_report_sha256"]
    assert sha(plan["CPU_audit"]) == plan["CPU_audit_sha256"]
    cpu = read(plan["CPU_report"])
    assert sha(cpu["plan"]) == cpu["plan_sha256"]
    cases = {case["id"]: case for case in read(cpu["plan"])["cases"]}
    models = {model["name"]: model for model in plan["models"]}
    modes = {"no-enclosing-autocast", "publisher-FP16-autocast"}
    keys = {(row["model"], row["case"], row["mode"]) for row in report["results"]}
    assert len(keys) == len(report["results"]) == 24
    assert keys == {(model, case, mode) for model in models for case in cases for mode in modes}
    assert plan["predeclared_no_autocast_CPU_parity_tolerance"] == {
        "absolute": 0.002,
        "relative_to_CPU": 0.002,
    }
    observations = {key: load_saved_case(case) for key, case in cases.items()}
    noisy_inputs = {
        key: malvar(batch["packed"], batch["colors"], wb)
        for key, (batch, _, wb, _) in observations.items()
    }
    baselines = {}
    for model in models.values():
        assert sha(model["original"]) == model["original_sha256"]
    for item in cpu["arrays"]:
        baseline_file = item["files"]["raw-network-f32"]
        assert sha(baseline_file["path"]) == baseline_file["sha256"]
        baselines[item["model"], item["case"]] = np.load(
            baseline_file["path"], allow_pickle=False
        ).astype(np.float64)
    output = writable_path(output)
    if output.exists():
        raise ValueError("GPU crop output exists; inspect it rather than replacing it")
    output.mkdir(parents=True, exist_ok=False)
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    arrays, crops, results, checks, parity = [], [], [], [], []
    for row in report["results"]:
        model, case = models[row["model"]], cases[row["case"]]
        assert model["original_sha256"] == row["original_checkpoint_sha256"]
        assert sha(row["raw_output"]) == row["raw_output_sha256"]
        raw = np.load(row["raw_output"], allow_pickle=False)
        assert list(raw.shape) == row["shape"]
        baseline = baselines[row["model"], row["case"]]
        error = np.abs(raw.astype(np.float64) - baseline)
        outside = int((error > 0.002 + 0.002 * np.abs(baseline)).sum())
        assert outside == row["outside_predeclared_no_autocast_tolerance"]
        for name, actual in [
            ("CPU_max_abs_difference", error.max()),
            ("CPU_mean_abs_difference", error.mean()),
            ("CPU_RMS_difference", np.sqrt(np.square(error).mean())),
        ]:
            assert abs(float(actual) - row[name]) < 1e-14
        if row["mode"] == "no-enclosing-autocast":
            assert row["no_autocast_parity_pass"] == (outside == 0)
            parity.append(outside == 0)
        prediction, _batch, target, wb, matrix, delta = prepare_saved_prediction(
            raw, case, model, observations[row["case"]]
        )
        key = row["model"] + "-" + row["case"] + "-" + row["mode"]
        path = output / (key + "-normalized-RGB-f32.npy")
        np.save(path, prediction.numpy(), allow_pickle=False)
        arrays.append(
            {
                "model": row["model"],
                "case": row["case"],
                "mode": row["mode"],
                "path": str(path),
                "sha256": sha(path),
                "shape": list(prediction.shape),
                "dtype": "float32",
            }
        )
        exact = case["kind"] == "synthetic-photo"
        scores = {}
        if exact:
            for label, roi in [("native160", case["roi_xywh"]), ("saved240", [8, 8, 240, 240])]:
                x, y, w, h = roi
                p, t = prediction[..., y : y + h, x : x + w], target[..., y : y + h, x : x + w]
                values = {
                    k: float(v[0]) if math.isfinite(float(v[0])) else None
                    for k, v in quality_metrics(p, t, wb, matrix).items()
                }
                for name, first, second in [
                    ("linear_psnr", p.clamp(0, 1), t.clamp(0, 1)),
                    ("srgb_psnr", render(p, wb, matrix), render(t, wb, matrix)),
                ]:
                    mse = np.square(
                        first.numpy().astype(np.float64) - second.numpy().astype(np.float64)
                    ).mean()
                    assert abs(-10 * math.log10(max(float(mse), 1e-12)) - values[name]) < 1e-5
                scores[label] = {"ROI_xywh": roi, "metrics": values}
        noisy = noisy_inputs[row["case"]]
        crop = save_triplet(
            output,
            key,
            [
                (label, display_crop(rgb, wb, matrix, roi, exposure=case["display_exposure"]))
                for label, rgb, roi in [
                    ("Noisy (Malvar)", noisy, case["roi_xywh"]),
                    (
                        "GPU / FP16 AMP"
                        if row["mode"] == "publisher-FP16-autocast"
                        else "GPU / no AMP",
                        prediction,
                        case["roi_xywh"],
                    ),
                    (
                        "GT (synthetic)" if exact else "ISO100 ref (not GT)",
                        target,
                        case["roi_xywh"] if exact else [0, 0, 160, 160],
                    ),
                ]
            ],
            caption=key,
            metadata={
                "case": case,
                "model": model,
                "mode": row["mode"],
                "native_output_dtype": row["native_output_dtype"],
                "ROI_xywh": case["roi_xywh"],
                "white_balance": wb.tolist(),
                "camera_to_srgb": matrix.tolist(),
                "display_exposure": case["display_exposure"],
                "reference": case["reference"],
                "conditioning": "Blind: no ISO/shot/read model input",
                "compute_precision": "Original signed GPU export; captured convolution TF32 flags retained. Separate no-enclosing-autocast and publisher FP16-autocast modes; no IEEE-FP32 claim.",
            },
        )
        old_crop = next(
            c
            for c in cpu["native_crops"]
            if c["case"]["id"] == case["id"] and c["model"]["name"] == model["name"]
        )
        old_path = Path(plan["CPU_report"]).parent / old_crop["image"]
        assert sha(old_path) == old_crop["png_sha256"]
        with Image.open(output / crop["image"]) as image, Image.open(old_path) as old_image:
            assert image.size == old_image.size == (512, 192)
            current, previous = np.array(image), np.array(old_image)
        for x in [8, 344]:
            np.testing.assert_array_equal(
                current[24:184, x : x + 160], previous[24:184, x : x + 160]
            )
        crops.append(crop)
        results.append(
            {
                "model": row["model"],
                "case": row["case"],
                "mode": row["mode"],
                "photo_scores": scores if exact else None,
            }
        )
        checks.append(
            {
                "model": row["model"],
                "case": row["case"],
                "mode": row["mode"],
                "float64_unit_conversion_max_error": delta,
                "raw_drift_scalars_recomputed": True,
                "noisy_and_reference_native_panels_identical_to_CPU_pilot": True,
            }
        )
    assert len(arrays) == len(crops) == len(checks) == 24 and len(parity) == 12
    assert (
        all(parity)
        == report["all_original_no_autocast_outputs_within_predeclared_CPU_parity_tolerance"]
    )
    assert not torch.cuda.is_initialized()
    result = {
        "status": "completed-saved-original-GPU-rendering-awaiting-visual-review",
        "input_report": str(report_path),
        "input_report_sha256": sha(report_path),
        "arrays": arrays,
        "native_crops": crops,
        "results": results,
        "checks": checks,
        "all_no_autocast_CPU_parity_pass": all(parity),
        "CUDA_initialized_by_renderer": False,
        "driver_sha256": sha(__file__),
        "scope": "Only six selected saved observations/two models/two precision modes. No new model inference, noise draws or RAW decode. Each score ROI is distinct and recorded. Real ISO100 is not GT and has no score. Crops still require actual viewing; no broad quality, SOTA or full-frame speed claim.",
    }
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {"output": str(output), "native_triplets": len(crops), "CPU_parity_pass": all(parity)}
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.report, args.output)
