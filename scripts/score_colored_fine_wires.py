"""Score the complete new coloured cohort, retaining signed per-colour response."""

import argparse
import sys
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.edge_response import measure


def colour_increments(target, value):
    target, value = np.asarray(target, np.float64), np.asarray(value, np.float64)
    if target.shape != value.shape or target.ndim != 4 or target.shape[:2] != (3, 3):
        raise ValueError("Require matching zero/one/two-direction RGB predictions")
    result = {}
    for label, first, second in [("strong", 0, 1), ("weak", 1, 2)]:
        truth, predicted = target[second] - target[first], value[second] - value[first]
        direction = truth.sum(axis=(-1, -2))
        norm = np.linalg.norm(direction)
        if not norm or not np.isfinite(predicted).all():
            raise ValueError("Require nonzero signed colour increments and finite values")
        direction /= norm
        projection = np.einsum("c,cyx->yx", direction, predicted)[None] * direction[:, None, None]
        result[label + "_colour_orthogonal_RMS_DN16"] = float(
            np.sqrt(np.mean((predicted - projection) ** 2)) * 65535
        )
        for color, name in enumerate("RGB"):
            energy = np.sum(truth[color] ** 2)
            if not energy:
                raise ValueError("Every declared increment colour must have nonzero energy")
            result[label + "_" + name + "_gain"] = float(
                np.sum(predicted[color] * truth[color]) / energy
            )
    return result


def score(root):
    assert "torch" not in sys.modules
    completion = read_json(root / "comparison-result.json")
    assert completion["all_corrections_closed"] and completion["cases"] == 192
    plan = read_json(root / "plan.json")
    comparison = read_json(root / "comparison-plan.json")
    parents = {
        g["group"]: g["parent"] for g in read_json(root / "parents-collection.json")["groups"]
    }
    variants = {}
    for variant in comparison["variants"]:
        collection = read_json(Path(variant["root"]) / "collection.json")
        assert (
            len(collection["rows"]) == 48
            and collection["new_neural_forwards"] == 0
            and collection["target_or_reference_arrays_loaded"] == 0
        )
        variants[variant["name"]] = {r["id"]: r for r in collection["rows"]}
    matches = 0
    for case, baseline in variants["broad"].items():
        for name, values in variants.items():
            if name == "broad":
                continue
            for key in ["parent_values", "packed_values", "colors_values"]:
                assert baseline[key] == values[case][key]
            for method in ["H1-global-t2", "H1-local-t2"]:
                np.testing.assert_array_equal(
                    np.load(checked(baseline["predictions"][method])),
                    np.load(checked(values[case]["predictions"][method])),
                )
                matches += 1
    rows = []
    for group in plan["groups"]:
        with np.load(checked(group["arrays"]), allow_pickle=False) as z:
            arrays = {k: z[k] for k in ["target", "quiet", "edge_band"]}
        values = {"V120": np.load(checked(parents[group["id"]]))}
        for name, records in variants.items():
            for method in records[group["cases"][0]]["predictions"]:
                values[name + "::" + method] = np.stack(
                    [
                        np.load(checked(records[case]["predictions"][method]))
                        for case in group["cases"]
                    ]
                )
        for method, value in values.items():
            rows.append(
                {
                    "profile": group["profile"],
                    "source": group["source"],
                    "pattern": group["pattern"],
                    "method": method,
                    **measure(arrays, value),
                    **colour_increments(arrays["target"], value),
                }
            )
    means = []
    for profile in sorted({r["profile"] for r in rows}):
        for method in values:
            subset = [r for r in rows if (r["profile"], r["method"]) == (profile, method)]
            assert len(subset) == 8
            means.append(
                {
                    "profile": profile,
                    "method": method,
                    **{
                        k: float(np.mean([r[k] for r in subset]))
                        for k in subset[0]
                        if k not in ["profile", "source", "pattern", "method"]
                    },
                }
            )
    write_json(
        root / "scores-v1.json",
        {
            "script": reference(__file__),
            "comparison": reference(root / "comparison-result.json"),
            "rows": rows,
            "means": means,
            "H1_exact_pair_checks": matches,
            "paired_input_cases": 48,
            "scope": "All192 corrections close before any target scoring.48 new observations/2 geometries/allCFAs/two priors, V120 parent. Signed per-colour projected response plus colour-orthogonal sensorRGB error, not perceptual colour accuracy or calibrated confidence. RawH1 controls exact across all variants; native viewing/report remain pending. No inference/noise/training replay.",
        },
    )
    print(
        len(rows),
        "metric rows;",
        matches,
        "H1 comparisons exact; native review pending",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    score(parser.parse_args().root)
