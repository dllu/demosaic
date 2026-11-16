"""Posthoc association of closed carrier coverage and actual weak increments."""

import argparse
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json

METRICS = (
    "strong_gain",
    "weak_gain",
    "quiet_error_RMS_DN16",
    "full_error_RMS_DN16",
    "weak_increment_error_RMS_DN16",
    "weak_orthogonal_RMS_DN16",
)
SELECTORS = ("current", "complementary", "additional-only")


def unique(rows, key):
    out = {}
    for row in rows:
        k = key(row)
        if k in out:
            raise ValueError(f"Duplicate identity: {k}")
        out[k] = row
    return out


def category(old_distance, new_distance, threshold):
    if old_distance <= threshold and new_distance > threshold:
        raise ValueError("Combined bank lost an inherited carrier")
    return (
        "inherited"
        if old_distance <= threshold
        else ("added-only" if new_distance <= threshold else "neither")
    )


def independent_distances(choice, recipe):
    bins = np.asarray(choice["bins_yx"], dtype=np.int64).reshape(3, -1, 2)
    valid = np.asarray(choice["valid"], dtype=bool).reshape(3, -1)
    native = recipe["size"]
    packed = native // 2
    signed = (bins + packed // 2) % packed - packed // 2
    target = np.array(
        [
            [math.sin(a) * native / p, math.cos(a) * native / p]
            for a, p in zip(recipe["wire_angles"], recipe["periods"], strict=True)
        ]
    )
    result = {}
    for role in range(3):
        for direction in range(2):
            distances = []
            for value, keep in zip(signed[role], valid[role], strict=True):
                if keep:
                    distances.append(
                        min(
                            math.hypot(*(value - target[direction])),
                            math.hypot(*(value + target[direction])),
                        )
                    )
            result[role, direction] = min(distances, default=math.inf)
    return result


def join_metrics(closed, geometry, score_rows, baselines, caches):
    choices = unique(closed, lambda r: (r["profile"], r["index"]))
    geom = unique(
        geometry, lambda r: (r["profile"], r["index"], r["selector"], r["role"], r["direction"])
    )
    scores = unique(score_rows, lambda r: (r["profile"], r["index"], r["method"], r["gain_scale"]))
    expected = {
        (p, i, m, g)
        for p, i in choices
        for m in ["complementary-raw", "complementary-ema"]
        for g in [0.0, 0.25, 0.5, 0.75, 1.0]
    }
    if set(scores) != expected:
        raise ValueError("Candidate score coverage differs")
    expected_geo = {
        (p, i, s, r, d) for p, i in choices for s in SELECTORS for r in range(3) for d in range(2)
    }
    if set(geom) != expected_geo:
        raise ValueError("Closed geometry coverage differs")
    joined = []
    max_error = 0.0
    checks = 0
    for (profile, index), selection in sorted(choices.items()):
        item = caches[profile]["rows"][index]
        meta = item["metadata"]
        recipe = meta["recipe"]
        if item["index"] != index or item["arrays"] != selection["arrays"]:
            raise ValueError("Wrong cached observation")
        original, extra, combined = [
            selection["choices"][s] for s in ["current", "additional-only", "complementary"]
        ]
        for key in ["bins_yx", "valid"]:
            if not np.array_equal(
                np.concatenate([np.asarray(original[key]), np.asarray(extra[key])], axis=2),
                np.asarray(combined[key]),
            ):
                raise ValueError("Combined carrier bank is not the closed concatenation")
        for name, choice in selection["choices"].items():
            actual = independent_distances(choice, recipe)
            for (role, direction), distance in actual.items():
                row = geom[profile, index, name, role, direction]
                if row["source"] != recipe["source"] or row["placement"] != meta["placement"]:
                    raise ValueError("Geometry metadata differs")
                error = abs(distance - row["nearest_fundamental_native_bins"])
                max_error = max(max_error, error)
                checks += 1
                if error > 1e-10 or any(
                    (distance <= t) != (row["nearest_fundamental_native_bins"] <= t) for t in [1, 3]
                ):
                    raise ValueError("Independent geometry score differs")
        control = baselines[profile, index]
        metric_keys = [k for k in control if k.endswith(("_DN16", "_gain"))]
        endpoints = {}
        for state in ["raw", "ema"]:
            zero = scores[profile, index, "complementary-" + state, 0.0]
            new = scores[profile, index, "complementary-" + state, 1.0]
            for row in [zero, new]:
                if any(row[k] != control[k] for k in ["source", "placement", "pattern", "repeat"]):
                    raise ValueError("Quality conditions differ")
                if not all(math.isfinite(row[k]) for k in metric_keys):
                    raise ValueError("Nonfinite quality metric")
            if any(zero[k] != control[k] for k in metric_keys):
                raise ValueError("Gain zero is not full V200 EMA")
            endpoints[state] = {k: new[k] for k in METRICS}
        joined.append(
            {
                "profile": profile,
                "index": index,
                "source": recipe["source"],
                "placement": meta["placement"],
                "pattern": control["pattern"],
                "repeat": control["repeat"],
                "weak_distance": {
                    s: [
                        geom[profile, index, s, r, 1]["nearest_fundamental_native_bins"]
                        for r in range(3)
                    ]
                    for s in SELECTORS
                },
                "baseline": {k: control[k] for k in METRICS},
                "candidate": endpoints,
            }
        )
    return joined, {
        "independent_distance_checks": checks,
        "maximum_distance_error_native_bins": max_error,
        "zero_gain_metric_checks": sum(
            len([k for k in baselines[p, i] if k.endswith(("_DN16", "_gain"))]) * 2
            for p, i in choices
        ),
    }


def summarize(rows):
    out = []
    for threshold in [1, 3]:
        for state in ["raw", "ema"]:
            groups = defaultdict(list)
            for row in rows:
                c = category(
                    row["weak_distance"]["current"][2],
                    row["weak_distance"]["complementary"][2],
                    threshold,
                )
                groups[row["profile"], row["placement"], c].append(row)
            for (profile, placement, c), items in sorted(groups.items()):
                metrics = {}
                population = [
                    r for r in rows if r["profile"] == profile and r["placement"] == placement
                ]
                for field in METRICS:
                    before = float(np.mean([r["baseline"][field] for r in items]))
                    after = float(np.mean([r["candidate"][state][field] for r in items]))
                    difference = float(
                        np.mean(
                            [r["candidate"][state][field] - r["baseline"][field] for r in items]
                        )
                    )
                    metrics[field] = {
                        "baseline_mean": before,
                        "candidate_mean": after,
                        "paired_difference": difference,
                        "contribution_to_full_condition_difference": difference
                        * len(items)
                        / len(population),
                    }
                sources = []
                for source in sorted({r["source"] for r in items}):
                    subset = [r for r in items if r["source"] == source]
                    sources.append(
                        {
                            "source": source,
                            "observations": len(subset),
                            "weak_gain_difference": float(
                                np.mean(
                                    [
                                        r["candidate"][state]["weak_gain"]
                                        - r["baseline"]["weak_gain"]
                                        for r in subset
                                    ]
                                )
                            ),
                        }
                    )
                out.append(
                    {
                        "threshold_native_bins": threshold,
                        "state": state,
                        "profile": profile,
                        "placement": placement,
                        "category": c,
                        "observations": len(items),
                        "sources": len(sources),
                        "source_rows": sources,
                        "metrics": metrics,
                    }
                )
    for threshold in [1, 3]:
        for state in ["raw", "ema"]:
            for profile, placement in sorted({(r["profile"], r["placement"]) for r in rows}):
                groups = [
                    r
                    for r in out
                    if (r["threshold_native_bins"], r["state"], r["profile"], r["placement"])
                    == (threshold, state, profile, placement)
                ]
                population = [
                    r for r in rows if (r["profile"], r["placement"]) == (profile, placement)
                ]
                assert sum(r["observations"] for r in groups) == len(population)
                for field in METRICS:
                    expected = float(
                        np.mean(
                            [
                                r["candidate"][state][field] - r["baseline"][field]
                                for r in population
                            ]
                        )
                    )
                    assert (
                        abs(
                            sum(
                                r["metrics"][field]["contribution_to_full_condition_difference"]
                                for r in groups
                            )
                            - expected
                        )
                        < 1e-12
                    )
    return out


def analyze(output, bridge_root):
    assert "torch" not in sys.modules
    os.nice(10)
    root = Path.cwd()
    base = root / ".cache/experiments"
    bindings = {
        "geometry": reference(base / "complementary-phase-diagnostic-v1/result.json"),
        "selections": reference(base / "complementary-phase-diagnostic-v1/selections.json"),
        "quality": reference(base / "complementary-edge-review-corrected-v1/scores.json"),
        "bridge": reference(bridge_root / "result.json"),
    }
    docs = {k: read_json(checked(v)) for k, v in bindings.items()}
    geometry, closed, quality, bridge = [
        docs[k] for k in ["geometry", "selections", "quality", "bridge"]
    ]
    assert geometry["selections"] == bindings["selections"]
    bp = read_json(checked(bridge["plan"]))
    assert bp["selections"] == bindings["selections"]
    assert (
        bridge["status"] == "all-closed-choices-exact-on-CUDA"
        and bridge["counts"]["batches"] == 384
        and bridge["counts"]["selector_calls"] == 768
    )
    assert bridge["counts"]["model_constructions"] == bridge["counts"]["neural_forwards"] == 0
    qp = read_json(checked(quality["plan"]))
    baselines = {}
    caches = {}
    inputs = list(bindings.values()) + [quality["plan"], bridge["plan"]]
    for cohort in qp["baselines"]:
        profile = cohort["profile"]
        inputs.extend([cohort["cache"], cohort["scores"]])
        caches[profile] = read_json(checked(cohort["cache"]))
        old = read_json(checked(cohort["scores"]))
        for row in old["rows"]:
            if row["method"] == "V200-ema" and row["gain_scale"] == 1.0:
                k = profile, row["index"]
                assert k not in baselines
                baselines[k] = row
    assert len(closed["rows"]) == len(baselines) == 384
    rows, audit = join_metrics(closed["rows"], geometry["rows"], quality["rows"], baselines, caches)
    groups = summarize(rows)
    overall = []
    for profile, placement in sorted({(r["profile"], r["placement"]) for r in rows}):
        subset = [r for r in rows if (r["profile"], r["placement"]) == (profile, placement)]
        overall.append(
            {
                "profile": profile,
                "placement": placement,
                "observations": len(subset),
                "sources": len({r["source"] for r in subset}),
                "coverage": {
                    str(t): {
                        s: [
                            float(np.mean([r["weak_distance"][s][role] <= t for r in subset]))
                            for role in range(3)
                        ]
                        for s in SELECTORS
                    }
                    for t in [1, 3]
                },
            }
        )
    assert "torch" not in sys.modules
    output.mkdir(parents=True, exist_ok=False)
    write_json(
        output / "analysis.json",
        {
            "status": "posthoc-closed-coverage-quality-association",
            "inputs": inputs,
            "script": reference(__file__),
            "rows": rows,
            "groups": groups,
            "overall": overall,
            "audit": audit,
            "checkpoint_exports": quality["exports"],
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "Torch_imported": False,
            "scope": "Existing384 triplets/1152 images from eight sources, not independent scenes. Fixed1/3-native-bin proximity thresholds from earlier diagnostic. All closed CPU choices now exact on CUDA, independent scalar geometry checks, full V200EMA zero anchors and observation metadata exact. Conditional groups overlap sources and differ in difficulty; descriptive association and exact arithmetic contribution, not causal allocation effects, reconstruction bounds, calibrated support or false-activation rates.",
        },
    )
    for row in groups:
        if (
            row["threshold_native_bins"] == 3
            and row["state"] == "ema"
            and row["profile"] in ["iso1600", "iso400"]
            and row["placement"] == "far"
        ):
            print(
                row["profile"],
                row["category"],
                row["observations"],
                row["sources"],
                "weak%",
                row["metrics"]["weak_gain"]["candidate_mean"] * 100,
                "differencepp",
                row["metrics"]["weak_gain"]["paired_difference"] * 100,
            )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--bridge", type=Path, required=True)
    a = p.parse_args()
    analyze(a.output.resolve(), a.bridge.resolve())
