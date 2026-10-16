"""Audit saved CPU color-flat diagnostics without rerunning inference."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from demosaic.cfa import malvar
from demosaic.reporting import display_crop
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def metrics(prediction, batch):
    """Independent NumPy64 arithmetic on the saved, unquantized arrays."""
    p = prediction[..., 48:208, 48:208].astype(np.float64)
    t = batch["target"][..., 48:208, 48:208].astype(np.float64)
    error = p - t
    mean = error.mean((0, 2, 3))
    mse = np.square(error).mean()
    predicted, truth = [], []
    for phase, channel in enumerate(batch["colors"][0]):
        y, x = divmod(phase, 2)
        predicted.append(p[:, channel, y::2, x::2])
        truth.append(t[:, channel, y::2, x::2])
    predicted, truth = np.stack(predicted, 1), np.stack(truth, 1)
    measured = batch["packed"][..., 24:104, 24:104].astype(np.float64)
    return {
        "camera_RGB_mean_error": mean.tolist(),
        "camera_RGB_MSE": float(mse),
        "camera_RGB_mean_component_fraction": float(np.square(mean).mean() / max(mse, 1e-24)),
        "spatially_centered_camera_RGB_RMS": float(
            np.sqrt(np.square(error - mean[None, :, None, None]).mean())
        ),
        "predicted_minus_GT_CFA_phase_mean": (predicted - truth).mean((0, 2, 3)).tolist(),
        "observed_minus_GT_CFA_phase_mean": (measured - truth).mean((0, 2, 3)).tolist(),
    }


@torch.inference_mode()
def main(parent, intervention, output):
    parent, intervention = Path(parent), Path(intervention)
    output = writable_path(output)
    assert not output.exists() and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    plan = read(parent / "plan.json")
    original = read(parent / "report.json")
    changed = read(intervention / "report.json")
    assert sha(parent / "plan.json") == original["plan_sha256"]
    assert sha(parent / "report.json") == changed["parent_sha256"]
    assert plan["roi_xywh"] == [48, 48, 160, 160]
    assert len(plan["cases"]) == 32 and len(original["results"]) == 64
    assert len(changed["results"]) == 32
    for model in plan["models"]:
        assert sha(model["path"]) == model["sha256"]
    assert changed["model"] == plan["models"][1]
    for name, expected in plan["source_files"].items():
        assert sha(parent / "source" / name) == expected
    assert sha(parent / "source/probe_colored_flats_cpu.py") == plan["driver_sha256"]
    assert sha(intervention / "probe_colored_flat_camera_slice.py") == changed["driver_sha256"]
    arrays = []
    shapes = {
        "packed": (1, 4, 128, 128),
        "variance": (1, 4, 128, 128),
        "colors": (1, 4),
        "wb": (1, 3),
        "matrix": (1, 3, 3),
        "target": (1, 3, 256, 256),
    }
    for case in plan["cases"]:
        assert sha(case["arrays"]) == case["sha256"]
        with np.load(case["arrays"], allow_pickle=False) as data:
            batch = {k: data[k] for k in data.files}
        assert batch.keys() == shapes.keys()
        for key, shape in shapes.items():
            assert batch[key].shape == shape and np.isfinite(batch[key]).all()
            assert batch[key].dtype == (np.int64 if key == "colors" else np.float32)
        desired = np.array(case["target_camera_RGB"])[None, :, None, None]
        assert np.max(np.abs(batch["target"].astype(np.float64) - desired)) < 2e-7
        assert np.array_equal(
            batch["target"], np.broadcast_to(batch["target"][..., :1, :1], (1, 3, 256, 256))
        )
        assert batch["target"].min() > 0 and batch["target"].max() < 1
        arrays.append(batch)
    predictions, errors, groups = {}, [], []
    for label, report, field in [
        ("original", original, "metrics"),
        ("camera-slice-zero", changed, "camera_feature_slice_zero"),
    ]:
        for item in report["float_predictions"]:
            assert sha(item["path"]) == item["sha256"]
            prediction = np.load(item["path"], allow_pickle=False)
            assert prediction.dtype == np.float32 and prediction.shape == (1, 3, 256, 256)
            assert np.isfinite(prediction).all()
            case = item["case"]
            step = item.get("step", 10000)
            key = (label, step, case)
            assert key not in predictions
            predictions[key] = prediction
            row = next(
                r for r in report["results"] if r["case"] == case and r.get("step", 10000) == step
            )
            actual = metrics(prediction, arrays[case])
            assert actual.keys() == row[field].keys()
            for name, values in actual.items():
                difference = float(
                    np.max(np.abs(np.asarray(values) - np.asarray(row[field][name])))
                )
                errors.append(difference)
                assert difference < 2e-14, (key, name, difference)
    for row in changed["results"]:
        original_row = next(
            r for r in original["results"] if r["case"] == row["case"] and r["step"] == 10000
        )
        assert row["original"] == original_row["metrics"]
    for label, report, field in [
        ("original", original, "metrics"),
        ("camera-slice-zero", changed, "camera_feature_slice_zero"),
    ]:
        for step in [3000, 10000] if label == "original" else [10000]:
            for palette in dict.fromkeys(c["palette"] for c in plan["cases"]):
                for condition in ["adc-only", "iso12800-prior"]:
                    selected = [
                        r
                        for r in report["results"]
                        if r["palette"] == palette
                        and r["condition"] == condition
                        and r.get("step", 10000) == step
                    ]
                    assert len(selected) == 4 and len({r["pattern"] for r in selected}) == 4
                    groups.append(
                        {
                            "method": label,
                            "step": step,
                            "palette": palette,
                            "condition": condition,
                            "mean_camera_RGB_error_across_four_CFAs": np.mean(
                                [r[field]["camera_RGB_mean_error"] for r in selected], axis=0
                            ).tolist(),
                            "max_abs_observed_CFA_phase_mean_error": float(
                                np.abs(
                                    [r[field]["observed_minus_GT_CFA_phase_mean"] for r in selected]
                                ).max()
                            ),
                            "CFA_count": 4,
                            "noise_draws_per_CFA": 1,
                        }
                    )
    images = []
    common_panels = {}
    for label, root, report in [
        ("original", parent, original),
        ("camera-slice-zero", intervention, changed),
    ]:
        for crop in report["native_crops"]:
            path = root / crop["image"]
            assert sha(path) == crop["png_sha256"]
            assert read(path.with_suffix(".json")) == crop
            case_index = next(i for i, c in enumerate(plan["cases"]) if c == crop["case"])
            batch = {k: torch.from_numpy(v.copy()) for k, v in arrays[case_index].items()}
            assert crop["roi_xywh"] == plan["roi_xywh"]
            assert crop["display_exposure"] == plan["display_exposure"] == 1.0
            assert (
                crop["white_balance"] == plan["white_balance"]
                and crop["camera_to_srgb"] == plan["camera_to_srgb"]
            )
            assert crop["conditioning"] == plan["cases"][case_index]["condition"]
            with Image.open(path) as im:
                assert im.mode == "RGB" and im.size == (512, 192)
                pixels = np.array(im)
            outputs = [
                malvar(batch["packed"], batch["colors"], batch["wb"]),
                torch.from_numpy(predictions[(label, crop["model"]["step"], case_index)]),
                batch["target"],
            ]
            for panel_index, (panel, rgb) in enumerate(zip(crop["panels"], outputs, strict=True)):
                x, y, width, height = panel["png_xywh"]
                assert width == height == 160
                display = display_crop(rgb, batch["wb"], batch["matrix"], crop["roi_xywh"])
                expected = np.rint(np.clip(display, 0, 1) * 255).astype(np.uint8)
                actual = pixels[y : y + height, x : x + width]
                assert np.array_equal(actual, expected)
                if panel_index in [0, 2]:
                    common_key = (case_index, panel_index)
                    if common_key in common_panels:
                        assert np.array_equal(common_panels[common_key], actual)
                    common_panels[common_key] = actual.copy()
            images.append(
                {
                    "path": str(path),
                    "sha256": sha(path),
                    "all_three_native_panels_rerender_exactly": True,
                }
            )
    assert len(predictions) == 96 and len(images) == 6 and not torch.cuda.is_initialized()
    result = {
        "status": "completed-independent-saved-array-and-native-panel-audit",
        "parent_report": {
            "path": str(parent / "report.json"),
            "sha256": sha(parent / "report.json"),
        },
        "intervention_report": {
            "path": str(intervention / "report.json"),
            "sha256": sha(intervention / "report.json"),
        },
        "observations_checked": 32,
        "float_predictions_checked": 96,
        "metric_fields_checked": len(errors),
        "max_numpy64_metric_difference": max(errors),
        "images": images,
        "four_CFA_summaries": groups,
        "CUDA_initialized": False,
        "driver_sha256": sha(__file__),
        "scope": "Finite synthetic diagnostic; one observation per color/condition/CFA. Native-panel rerendering uses the common production display; scalar metric arithmetic is independently NumPy64. This audit does not claim visual review, quality promotion or a training cause.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    output.with_suffix(".py").write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            {
                "output": str(output),
                "predictions": len(predictions),
                "max_metric_difference": max(errors),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parent",
        type=Path,
        default=Path("/mnt/external/demosaic/evaluation/fresh-none-colored-flats-cpu-v1"),
    )
    parser.add_argument(
        "--intervention",
        type=Path,
        default=Path(
            "/mnt/external/demosaic/evaluation/fresh-none-colored-flat-camera-slice-cpu-v1"
        ),
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.parent, args.intervention, args.output)
