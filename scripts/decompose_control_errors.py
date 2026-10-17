"""Separate V63's saved exact-target errors by color mean and spatial scale.

No inference or corrected images: these are additive error energies, not scores
for an oracle mean-subtracted restoration. All inputs come from a hash-bound
completed endpoint comparison. Real captures have no exact target and are omitted.
"""

import argparse
import hashlib
import json
import math
import shutil
from datetime import UTC, datetime
from pathlib import Path

import numpy as np


def reference(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def verify(ref):
    actual = reference(ref["path"])
    if actual["sha256"] != ref["sha256"]:
        raise ValueError(f"Changed input: {ref['path']}")
    return Path(actual["path"])


def read(ref):
    return json.loads(verify(ref).read_text())


def decompose(error, levels=4):
    error = np.asarray(error, dtype=np.float64)
    if error.ndim != 3 or error.shape[0] != 3 or not np.isfinite(error).all():
        raise ValueError("Expected finite RGB CHW error")
    if levels < 1 or any(side < 1 or side % 2**levels for side in error.shape[-2:]):
        raise ValueError("Spatial dimensions must divide into complete Haar blocks")
    bias = error.mean(axis=(-2, -1), keepdims=True)
    residual = error - bias
    coarse = residual
    bands = {}
    for level in range(1, levels + 1):
        a, b = coarse[:, ::2, ::2], coarse[:, ::2, 1::2]
        c, d = coarse[:, 1::2, ::2], coarse[:, 1::2, 1::2]
        details = [(a - b + c - d) / 2, (a + b - c - d) / 2, (a - b - c + d) / 2]
        bands[str(2**level)] = sum(float(np.sum(x * x)) for x in details) / error.size
        coarse = (a + b + c + d) / 2
    bands[f"coarser_than_{2**levels}"] = float(np.sum(coarse * coarse) / error.size)
    result = {
        "MSE": float(np.mean(error * error)),
        "signed_channel_mean_error": bias.ravel().tolist(),
        "mean_bias_MSE": float(np.mean(bias * bias)),
        "zero_mean_MSE": float(np.mean(residual * residual)),
        "zero_mean_Haar_MSE_by_block_side": bands,
    }
    return result


def audit(error, result, levels=4):
    """Independent scalar moments and nested block-average energy differences."""
    error = np.asarray(error, dtype=np.float64)
    channel_values = [channel.ravel().tolist() for channel in error]
    means = [math.fsum(values) / len(values) for values in channel_values]
    mse = math.fsum(x * x for values in channel_values for x in values) / error.size
    bias_mse = math.fsum(x * x for x in means) / 3
    residual_mse = (
        math.fsum((x - mean) ** 2 for values, mean in zip(channel_values, means) for x in values)
        / error.size
    )
    differences = [
        abs(result["MSE"] - mse),
        abs(result["mean_bias_MSE"] - bias_mse),
        abs(result["zero_mean_MSE"] - residual_mse),
        abs(result["MSE"] - result["mean_bias_MSE"] - result["zero_mean_MSE"]),
        abs(math.fsum(result["zero_mean_Haar_MSE_by_block_side"].values()) - residual_mse),
        *(abs(a - b) for a, b in zip(result["signed_channel_mean_error"], means)),
    ]
    previous = residual_mse
    channels, height, width = error.shape
    for level in range(1, levels + 1):
        side = 2**level
        block_means = error.reshape(channels, height // side, side, width // side, side).mean(
            axis=(2, 4)
        )
        remaining = float(np.mean((block_means - np.array(means)[:, None, None]) ** 2))
        differences.append(
            abs(result["zero_mean_Haar_MSE_by_block_side"][str(side)] - (previous - remaining))
        )
        previous = remaining
    differences.append(
        abs(result["zero_mean_Haar_MSE_by_block_side"][f"coarser_than_{2**levels}"] - previous)
    )
    maximum = max(differences)
    if maximum > 1e-14:
        raise ValueError(f"Error-energy decomposition failed independent identities: {maximum}")
    return maximum


def display(rgb, wb, matrix):
    linear = np.einsum("ij,jhw->ihw", matrix, rgb * wb[:, None, None]).clip(0, 1)
    return np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError("Refuse to replace an existing analysis")
    parent_ref = {"path": str(args.comparison.resolve()), "sha256": args.sha256}
    parent = read(parent_ref)
    if parent["status"] != "completed-actual-control-original20k-CPU-array-and-native-comparison":
        raise ValueError("Expected the completed V63 endpoint comparison")
    stages = ("first4k", "final20k")
    plans = [read(parent["plans"][stage]["receipt"]) for stage in stages]
    if plans[0]["observations"] != plans[1]["observations"]:
        raise ValueError("Endpoint observations differ")
    observation_plan = read(plans[0]["observations"])
    cases = {case["id"]: case for case in observation_plan["cases"]}
    exact = {key: value for key, value in cases.items() if value["kind"] in ("photo", "analytic")}
    if set(exact) != {"exact-photo-0", "exact-photo-1", "fabric-mean", "fabric-cyclic-gbr"}:
        raise ValueError("Unexpected exact-target cohort")
    records, inputs, maximum = [], [], 0.0
    for stage, step, plan in zip(stages, (4000, 20000), plans, strict=True):
        execution = read(parent["executions"][stage])
        if execution["checkpoint"] != plan["checkpoint"] or execution["step"] != step:
            raise ValueError("Wrong endpoint")
        verify(execution["checkpoint"])
        predictions = {item["case"]: item for item in execution["float_predictions"]}
        for name, case in exact.items():
            prediction_ref = predictions[name]
            prediction = np.load(verify(prediction_ref), allow_pickle=False)
            observation_path = verify(case["arrays"])
            with np.load(observation_path, allow_pickle=False) as arrays:
                target = arrays["target"]
                wb, matrix = (
                    arrays["wb"][0].astype(np.float64),
                    arrays["matrix"][0].astype(np.float64),
                )
                if target.dtype != np.float32 or prediction.dtype != np.float32:
                    raise ValueError("Expected the original F32 arrays")
                if prediction.shape != target.shape or target.shape != (1, 3, 256, 256):
                    raise ValueError("Wrong native context dimensions")
                if not np.isfinite(target).all() or not np.isfinite(prediction).all():
                    raise ValueError("Nonfinite target/prediction")
                target, prediction = target[0].astype(np.float64), prediction[0].astype(np.float64)
            if case["display_exposure"] != 1:
                raise ValueError("Unexpected display exposure")
            inputs.append(
                {
                    "stage": stage,
                    "case": name,
                    "prediction": prediction_ref,
                    "observation": case["arrays"],
                    "checkpoint": execution["checkpoint"],
                }
            )
            for space, pred, truth in (
                ("camera_linear_unclipped", prediction, target),
                (
                    "sRGB_clipped_float64",
                    display(prediction, wb, matrix),
                    display(target, wb, matrix),
                ),
            ):
                for region, xywh in (
                    ("border8", [8, 8, 240, 240]),
                    ("native_crop", case["ROI_xywh"]),
                ):
                    x, y, width, height = xywh
                    error = (pred - truth)[:, y : y + height, x : x + width]
                    result = decompose(error)
                    maximum = max(maximum, audit(error, result))
                    records.append(
                        {
                            "case": name,
                            "stage": stage,
                            "space": space,
                            "region": region,
                            "ROI_xywh": xywh,
                            **result,
                        }
                    )
    pairs = []
    for before in (row for row in records if row["stage"] == "first4k"):
        after = next(
            row
            for row in records
            if row["stage"] == "final20k"
            and all(row[key] == before[key] for key in ("case", "space", "region"))
        )
        pairs.append(
            {
                **{key: before[key] for key in ("case", "space", "region")},
                "delta_MSE": after["MSE"] - before["MSE"],
                "delta_mean_bias_MSE": after["mean_bias_MSE"] - before["mean_bias_MSE"],
                "delta_zero_mean_MSE": after["zero_mean_MSE"] - before["zero_mean_MSE"],
                "delta_zero_mean_Haar_MSE_by_block_side": {
                    key: after["zero_mean_Haar_MSE_by_block_side"][key] - value
                    for key, value in before["zero_mean_Haar_MSE_by_block_side"].items()
                },
            }
        )
    result = {
        "status": "completed-saved-control-error-decomposition-no-inference",
        "created_UTC": datetime.now(UTC).isoformat(),
        "parent": parent_ref,
        "operator": reference(__file__),
        "inputs": inputs,
        "records": records,
        "pairs": pairs,
        "independent_scalar_and_block_average_audit_max_absolute_error": maximum,
        "audit_tolerance": 1e-14,
        "new_neural_forwards": 0,
        "limits": [
            "Four previously selected exact targets; no population estimate or causal claim.",
            "Haar scales are aligned block supports, not a Fourier transfer function.",
            "sRGB uses float64 rendering and is not an exact replay of float32 PSNR.",
            "Subtracting target-based means here does not produce a deployable correction.",
            "No real-photo reference is scored, and no model is promoted.",
        ],
    }
    args.output.mkdir(parents=True)
    shutil.copyfile(__file__, args.output / "operator-source.py")
    (args.output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "result": reference(args.output / "result.json"),
                "records": len(records),
                "independent_max_error": maximum,
            }
        )
    )


if __name__ == "__main__":
    main()
