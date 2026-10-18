"""Fixed input-only channel gain on the mature parent's saved color grid."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import psutil
import torch

from demosaic.cfa import malvar, mosaic
from demosaic.reporting import display_crop, save_triplet


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    return {"path": str(Path(path).absolute()), "sha256": sha(path)}


def channel_gain(prediction, packed, colors):
    """Whole-image CFA least squares; no target, clipping, masks or gain bounds.

    This tests the existing RawNIND channel-adapter expression on our output.
    FP64 reductions/multiplication precede one FP32 cast. Each sample is fitted
    separately; both green phases contribute. A zero denominator uses1e-12,
    exactly as the existing expression, rather than an invented fallback.
    """
    if packed.ndim != 4 or packed.shape[1] != 4:
        raise ValueError("Expected four packed Bayer phases")
    batch, _, h, w = packed.shape
    if prediction.shape != (batch, 3, 2 * h, 2 * w):
        raise ValueError("Prediction and Bayer shapes disagree")
    if colors.ndim == 1:
        colors = colors[None].expand(batch, -1)
    if colors.shape != (batch, 4) or colors.dtype != torch.int64:
        raise ValueError("Expected integer Bayer color labels")
    expected = colors.new_tensor([0, 1, 1, 2]).expand(batch, -1)
    if not torch.equal(colors.sort(-1).values, expected):
        raise ValueError("Each Bayer sample must have one red, two green and one blue phase")
    if not torch.isfinite(prediction).all() or not torch.isfinite(packed).all():
        raise ValueError("Nonfinite prediction or observation")
    with torch.autocast(device_type=prediction.device.type, enabled=False):
        predicted = mosaic(prediction.double(), colors)
        observed = packed.double()
        gains = []
        for channel in range(3):
            mask = (colors == channel)[..., None, None]
            numerator = (predicted * observed * mask).sum((1, 2, 3))
            denominator = (predicted.square() * mask).sum((1, 2, 3)).clamp_min(1e-12)
            gains.append(numerator / denominator)
        gain = torch.stack(gains, 1)
        return (prediction.double() * gain[..., None, None]).float(), gain


def numpy_gain(prediction, packed, colors):
    """Independent phase slices/dot products, without mosaic or channel_gain."""
    gains = []
    for labels, rgb, observed in zip(colors, prediction, packed):
        row = []
        for channel in range(3):
            p = np.concatenate(
                [
                    rgb[channel, phase // 2 :: 2, phase % 2 :: 2].astype(np.float64).ravel()
                    for phase in range(4)
                    if labels[phase] == channel
                ]
            )
            y = np.concatenate(
                [
                    observed[phase].astype(np.float64).ravel()
                    for phase in range(4)
                    if labels[phase] == channel
                ]
            )
            row.append(float(np.dot(p, y) / max(float(np.dot(p, p)), 1e-12)))
        gains.append(row)
    return np.asarray(gains)


@torch.inference_mode()
def main(plan_path):
    from audit_colored_flats import metrics
    from evaluate_color_grid_cuda import summarize
    from prepare_color_grid import validate

    os.nice(10)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan = read(plan_path)
    root, output = Path(plan["root"]), Path(plan["output"])
    assert ref(__file__) == plan["worker"]
    for item in plan["source_files"]:
        assert ref(item["path"]) == item
    for key in ["saved_report", "case_audit", "inputs"]:
        assert ref(plan[key]["path"]) == plan[key]
    assert psutil.virtual_memory().available > 24 * 2**30
    assert psutil.disk_usage(root).free > 128 * 2**30
    with (root / "claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed_cases": 0,
    }

    def record(state, **values):
        status.update(status=state, updated_unix=time.time(), **values)
        temporary = root / "status.tmp"
        temporary.write_text(json.dumps(status, indent=2, allow_nan=False) + "\n")
        temporary.replace(root / "status.json")
        print(
            json.dumps({"status": state, "completed_cases": status["completed_cases"]}), flush=True
        )

    try:
        record("running-CPU-fixed-input-only-gain-on-saved-parent-grid")
        output.mkdir(parents=True, exist_ok=False)
        inputs, saved, audit = [
            read(plan[k]["path"]) for k in ["inputs", "saved_report", "case_audit"]
        ]
        validate(inputs)
        assert audit["input_report_sha256"] == sha(plan["saved_report"]["path"])
        assert audit["observations"] == 1176 and audit["float_predictions"] == 3528
        old_plan = read(saved["plan"])
        assert sha(saved["plan"]) == saved["plan_sha256"]
        assert old_plan["input_plan_sha256"] == sha(plan["inputs"]["path"])
        assert old_plan["cases"] == inputs["cases"]
        model = saved["checkpoints"][plan["model_index"]]
        assert model["sha256"] == plan["checkpoint_sha256"]
        predictions = {
            r["case"]: r
            for r in saved["float_predictions"]
            if r["model_index"] == plan["model_index"]
        }
        original_metrics = {
            r["case"]: r["metrics"]
            for r in saved["results"]
            if r["model_index"] == plan["model_index"]
        }
        assert len(predictions) == len(original_metrics) == 1176
        rows, fits, crops = [], [], []
        max_gain_error = max_pixel_error = 0.0
        for ci, case in enumerate(inputs["cases"]):
            assert sha(case["arrays"]) == case["sha256"]
            item = predictions[ci]
            assert sha(item["path"]) == item["sha256"]
            with np.load(case["arrays"], allow_pickle=False) as values:
                arrays = {k: values[k].copy() for k in values.files}
            before = np.load(item["path"], allow_pickle=False)
            assert before.shape == (1, 3, 256, 256) and before.dtype == np.float32
            b = {k: torch.from_numpy(v) for k, v in arrays.items()}
            corrected, gain = channel_gain(torch.from_numpy(before), b["packed"], b["colors"])
            # Independent fit is input-only too. Target is used below, after both fits.
            oracle = numpy_gain(before, arrays["packed"], arrays["colors"])
            np.testing.assert_allclose(gain.numpy(), oracle, rtol=2e-12, atol=2e-12)
            expected = (before.astype(np.float64) * oracle[..., None, None]).astype(np.float32)
            pixel_error = float(np.max(np.abs(expected - corrected.numpy())))
            assert pixel_error <= 2e-7 and torch.isfinite(corrected).all()
            max_gain_error = max(max_gain_error, float(np.max(np.abs(gain.numpy() - oracle))))
            max_pixel_error = max(max_pixel_error, pixel_error)
            for mi, values in enumerate([before, corrected.numpy()]):
                measured = metrics(values, arrays)
                if mi == 0:
                    assert measured == original_metrics[ci]
                rows.append(
                    {
                        "model_index": mi,
                        "case": ci,
                        "palette": case["palette"],
                        "condition": case["condition"]["name"],
                        "pattern": case["pattern"],
                        "source": case["source"],
                        "metrics": measured,
                    }
                )
            fits.append(
                {
                    "case": ci,
                    "gains": gain.tolist()[0],
                    "input_prediction": item,
                    "input_observation": case,
                    "gain_oracle_max_difference": float(np.max(np.abs(gain.numpy() - oracle))),
                    "corrected_pixel_oracle_max_difference": pixel_error,
                }
            )
            if (
                case["palette"] in plan["native_palettes"]
                and case["condition"]["name"] == "iso12800-prior"
                and case["pattern"] == "RGGB"
            ):
                noisy = malvar(b["packed"], b["colors"], b["wb"])
                for mi, prediction in enumerate([torch.from_numpy(before), corrected]):
                    label = ["V63-parent", "V63-input-CFA-channel-gain"][mi]
                    crops.append(
                        save_triplet(
                            output,
                            f"{case['id']}:{label}",
                            [
                                (name, display_crop(rgb, b["wb"], b["matrix"], inputs["roi_xywh"]))
                                for name, rgb in [
                                    ("Noisy (Malvar)", noisy),
                                    (label, prediction),
                                    ("GT (analytic)", b["target"]),
                                ]
                            ],
                            caption=f"{case['id']} / {label}",
                            metadata={
                                "case": case,
                                "model": {**model, "label": label},
                                "checkpoint_sha256": model["sha256"],
                                "ROI_xywh": inputs["roi_xywh"],
                                "white_balance": inputs["white_balance"],
                                "camera_to_srgb": inputs["camera_to_srgb"],
                                "conditioning": case["condition"],
                                "display_exposure": 1.0,
                                "reference": "Exact uniform analytic GT, not a photograph",
                                "gain": gain.tolist()[0] if mi else [1, 1, 1],
                                "fit_extent": "Entire native256 prediction/observation; target unavailable",
                            },
                        )
                    )
            if (ci + 1) % 196 == 0:
                record(
                    "running-CPU-fixed-input-only-gain-on-saved-parent-grid", completed_cases=ci + 1
                )
        assert len(rows) == 2352 and len(fits) == 1176 and len(crops) == 14
        assert not torch.cuda.is_initialized()
        report = {
            "status": "completed-saved-parent-input-gain-grid-awaiting-native-review",
            "plan": ref(plan_path),
            "checkpoint": model,
            "results": rows,
            "fits": fits,
            "group_summary": summarize(rows),
            "native_crops": crops,
            "independent_numpy_gain_max_difference": max_gain_error,
            "independent_corrected_FP32_pixel_max_difference": max_pixel_error,
            "CUDA_initialized": False,
            "actual_model_forwards": 0,
            "scope": plan["scope"],
        }
        (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        record(report["status"], completed_cases=1176, result=ref(output / "report.json"))
    except BaseException as error:
        record("failed-saved-input-gain-grid-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
