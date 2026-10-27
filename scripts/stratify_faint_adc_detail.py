"""Measure faint-ADC errors in the original reference-defined detail strata."""

import argparse
import csv
import os
import sys
from itertools import pairwise
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import coefficients
from report_checkpoint_pilot import band
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import linear_rgb


def strata(value, arrays, *, independent=False):
    if independent:
        c, means, rgb = coefficients(value, arrays)
    else:
        rgb = linear_rgb(value.astype(np.float64), arrays)[..., 48:208, 48:208]
        c, means = band(rgb)
        c, means = c[0], means[0]
    color = np.array(
        [
            (
                (rgb[0, :, y : y + 16, x : x + 16] >= 0) & (rgb[0, :, y : y + 16, x : x + 16] <= 1)
            ).all()
            for y in range(0, 160, 16)
            for x in range(0, 160, 16)
        ]
    )
    rms = np.sqrt((c * c).sum(1) / 256)
    valid = color & (means >= 0.02) & (means <= 0.9) & (rms >= 1e-5)
    contrast = rms / np.maximum(means, 1e-12)
    edges = (0, 0.02, 0.05, 0.1, 0.2, np.inf)
    return [valid & (contrast >= lo) & (contrast < hi) for lo, hi in pairwise(edges)]


def measures(prediction, target):
    energy = float(np.sum(target * target))
    gain = float(np.sum(prediction * target) / energy)
    return {
        "gain": gain,
        "relative_band_error_RMS": float(np.sqrt(np.sum((prediction - target) ** 2) / energy)),
        "relative_orthogonal_residual_RMS": float(
            np.sqrt(np.sum((prediction - gain * target) ** 2) / energy)
        ),
    }


def analyze(path, labels):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Stratification requires CPU/NumPy without Torch")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    if not labels or len(set(labels)) != len(labels) or not set(labels) <= set(plan["methods"]):
        raise ValueError("Declare distinct methods from this fixed faint-ADC plan")
    destination = root / ("source-strata-" + "-".join(labels) + "-v1")
    destination.mkdir(exist_ok=False)
    collections, bindings = {}, {}
    for label in labels:
        binding = ref(root / label / "collection-v1.json")
        collection = read(binding["path"])
        assert collection["plan"] == ref(root / label / "plan-v1.json")
        assert collection["counts"] == {"root": 16, "encoder": 16}
        collections[label] = {r["id"]: r for r in collection["observations"]}
        bindings[label] = binding
    rows, maximum, scalar_checks = [], 0.0, 0
    for case in plan["cases"]:
        observations = [o for o in plan["observations"] if o["case_id"] == case["id"]]
        assert len(observations) == 4
        with np.load(observations[0]["arrays"]["path"], allow_pickle=False) as data:
            arrays = {k: data[k] for k in data.files}
        with np.load(case["original_target"]["path"], allow_pickle=False) as data:
            original = data["target"]
        masks = strata(original, arrays)
        independent_masks = strata(original, arrays, independent=True)
        for primary, independent in zip(masks, independent_masks, strict=True):
            np.testing.assert_array_equal(primary, independent)
        with np.load(case["target"]["path"], allow_pickle=False) as data:
            target = data["target"]
        target_coeff, _ = band(linear_rgb(target.astype(np.float64), arrays)[..., 48:208, 48:208])
        independent_target, _, _ = coefficients(target, arrays)
        for observation in observations:
            for label in labels:
                binding = collections[label][observation["id"]]["prediction"]
                assert ref(binding["path"]) == binding
                prediction = np.load(binding["path"], allow_pickle=False)
                pred_coeff, _ = band(
                    linear_rgb(prediction.astype(np.float64), arrays)[..., 48:208, 48:208]
                )
                independent_pred, _, _ = coefficients(prediction, arrays)
                for index, mask in enumerate(masks):
                    if not mask.any():
                        continue
                    measured = measures(pred_coeff[0, mask], target_coeff[0, mask])
                    # Separate FFT coefficients, independent flattened dot/norm reductions.
                    a, b = independent_pred[mask].ravel(), independent_target[mask].ravel()
                    projection = float(np.dot(a, b) / np.dot(b, b))
                    independent = {
                        "gain": projection,
                        "relative_band_error_RMS": float(np.linalg.norm(a - b) / np.linalg.norm(b)),
                        "relative_orthogonal_residual_RMS": float(
                            np.linalg.norm(a - projection * b) / np.linalg.norm(b)
                        ),
                    }
                    for key in measured:
                        error = abs(measured[key] - independent[key])
                        assert error < 1e-10
                        maximum = max(maximum, error)
                        scalar_checks += 1
                    rows.append(
                        {
                            "case": case["original_case_id"],
                            "source_id": case["source_id"],
                            "method": label,
                            "CFA": observation["pattern"],
                            "source_contrast_bin": index,
                            "blocks": int(mask.sum()),
                            "reference_band_RMS": float(
                                np.sqrt(
                                    np.mean(target_coeff[0, mask] ** 2)
                                    * target_coeff.shape[-1]
                                    / 256
                                )
                            ),
                            **measured,
                        }
                    )
    summaries = []
    for case in plan["cases"]:
        for label in labels:
            for index in range(5):
                selected = [
                    r
                    for r in rows
                    if (r["case"], r["method"], r["source_contrast_bin"])
                    == (case["original_case_id"], label, index)
                ]
                if not selected:
                    continue
                assert len(selected) == 4 and len({r["blocks"] for r in selected}) == 1
                summaries.append(
                    {
                        "case": case["original_case_id"],
                        "method": label,
                        "source_contrast_bin": index,
                        "blocks": selected[0]["blocks"],
                        "CFAs": 4,
                        **{
                            k: float(np.mean([r[k] for r in selected]))
                            for k in (
                                "gain",
                                "relative_band_error_RMS",
                                "relative_orthogonal_residual_RMS",
                            )
                        },
                    }
                )
    with (destination / "rows.csv").open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    result = {
        "status": "completed-original-reference-stratification-with-independent-FFT-audit",
        "plan": ref(path),
        "collections": bindings,
        "source": ref(__file__),
        "rows": rows,
        "summaries": summaries,
        "scalar_fields_independently_checked": scalar_checks,
        "maximum_independent_absolute_error": maximum,
        "contrast_bins": ["0-2%", "2-5%", "5-10%", "10-20%", ">=20%"],
        "new_neural_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "scope": "Descriptive original-target detail strata, defined by existing DCT16/luminance/gamut/RMS rules before the.025 contrast transform. Identical target-only masks across all methods/CFAs; no output-based mask or inference fitting. Not an independent photographic validation or predeclared significance study.",
    }
    if "V130" in labels:
        prior = root / "source-strata-V120-V129-v1/result.json"
        original = read(prior)
        assert original["plan"] == ref(path)
        assert all(original["collections"][label] == bindings[label] for label in ("V120", "V129"))
        result["pre_V130_control_stratification"] = ref(prior)
        result["scope"] += (
            " Original reference strata and V120/V129 measurements were published before V130 predictions; this reduction adds only the new V130 endpoint to the same masks."
        )
    else:
        result["scope"] += " Derived after V120/V129 outputs and before V130 outputs."
    save(destination / "result.json", result)
    print(
        {
            "rows": len(rows),
            "summary_groups": len(summaries),
            "independent_fields": scalar_checks,
            "max_error": maximum,
        }
    )
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--labels", nargs="+", default=["V120", "V129"])
    args = parser.parse_args()
    analyze(args.plan.resolve(), args.labels)
