"""Independently rebuild fresh-trial summary statistics from saved case scores.

No model inference, production aggregation imports, photo decoding or CUDA.
This audits coverage and arithmetic; it does not validate metric definitions,
inspect restoration pixels, estimate training uncertainty or select a model.
"""

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

import numpy as np

from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
CLASSICAL = {"Bilinear", "Malvar2004:WB", "Wiener7+Malvar2004:WB"}
TOLERANCE = 2e-10


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def load_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream]


def average(values):
    valid = [value for value in values if value is not None]
    return math.fsum(valid) / len(valid) if valid else None


def group_means(rows, fields):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(row[field] for field in fields)].append(row["metrics"])
    return {
        key: {name: average([row[name] for row in values]) for name in values[0]}
        for key, values in groups.items()
    }


def validate_rows(rows, expected, core_metrics, nullable_metrics):
    actual = set()
    missing_values = defaultdict(int)
    supports = {}
    for row in rows:
        key = (row["model"], row["kind"], row["id"], row["condition"], row["pattern"])
        require(key not in actual, f"Duplicate observation: {key}")
        actual.add(key)
        require(set(row["metrics"]) == core_metrics | nullable_metrics, "Metric names changed")
        support = {name for name, value in row["metrics"].items() if value is not None}
        observation = key[1:]
        require(
            supports.setdefault(observation, support) == support,
            f"Metric validity differs between methods: {observation}",
        )
        for name, value in row["metrics"].items():
            if value is None:
                require(name in nullable_metrics, f"Missing core metric: {key} {name}")
                missing_values[name] += 1
            else:
                require(
                    isinstance(value, (float, int)) and math.isfinite(value),
                    f"Nonfinite/non-numeric metric: {key} {name}",
                )
    require(
        actual == expected,
        f"Observation coverage mismatch: missing={len(expected - actual)}, extra={len(actual - expected)}",
    )
    return dict(missing_values)


def compare_summary(rows, summary):
    errors = []

    def close(actual, expected, label):
        if actual is None or expected is None:
            require(actual is expected, f"Missing-value mismatch: {label}")
            return
        error = abs(actual - expected)
        require(math.isfinite(actual) and error <= TOLERANCE, f"Summary mismatch: {label}: {error}")
        errors.append(error)

    def check_means(records, fields, source_rows):
        expected = group_means(source_rows, fields)
        partition = defaultdict(list)
        for row in source_rows:
            partition[tuple(row[field] for field in fields)].append(row)
        actual = {tuple(row[field] for field in fields): row for row in records}
        require(
            len(actual) == len(records) and actual.keys() == expected.keys(), "Summary keys differ"
        )
        for key, means in expected.items():
            require(actual[key]["metrics"].keys() == means.keys(), "Summary metric names differ")
            matching = partition[key]
            for name, value in means.items():
                metric = actual[key]["metrics"][name]
                require(
                    metric["count"] == sum(row["metrics"][name] is not None for row in matching),
                    f"Summary count mismatch: {key} {name}",
                )
                close(metric["mean"], value, (key, name))

    check_means(summary["groups"], ["model", "kind", "condition", "pattern"], rows)
    source = group_means(rows, ["model", "kind", "id"])
    source_rows = [
        {"model": key[0], "kind": key[1], "id": key[2], "metrics": metrics}
        for key, metrics in source.items()
    ]
    check_means(summary["overall"], ["model", "kind"], source_rows)
    comparisons = summary["paired_comparisons"]
    keys = {(row["first"], row["second"], row["kind"], row["metric"]) for row in comparisons}
    require(len(keys) == len(comparisons), "Duplicate paired comparison")
    names = {row["metric"] for row in comparisons}
    methods = sorted({row["model"] for row in source_rows})
    kinds = sorted({row["kind"] for row in source_rows})
    expected_keys = {
        (a, b, kind, name)
        for i, a in enumerate(methods)
        for b in methods[i + 1 :]
        for kind in kinds
        for name in names
    }
    require(keys == expected_keys, "Missing paired comparisons")
    for row in comparisons:
        first, second, kind, metric = (row[key] for key in ["first", "second", "kind", "metric"])
        identities = sorted(
            key[2]
            for key in source
            if key[:2] == (first, kind)
            and source[key][metric] is not None
            and source[second, kind, key[2]][metric] is not None
        )
        delta = np.array(
            [
                source[first, kind, key][metric] - source[second, kind, key][metric]
                for key in identities
            ]
        )
        require(row["sources"] == len(delta), "Paired comparison source count differs")
        close(
            row["mean_first_minus_second"], average(delta.tolist()), (first, second, kind, metric)
        )
        # Reproduce the declared 1000 resamples/seed42 percentile procedure.
        indices = np.random.default_rng(42).integers(len(delta), size=(1000, len(delta)))
        interval = np.quantile(delta[indices].mean(axis=1), [0.025, 0.975])
        require(len(row["source_bootstrap_95_interval"]) == 2, "Invalid bootstrap interval length")
        for actual, expected in zip(row["source_bootstrap_95_interval"], interval):
            close(actual, float(expected), (first, second, kind, metric, "interval"))
    return {
        "group_rows": len(summary["groups"]),
        "overall_rows": len(summary["overall"]),
        "paired_comparisons": len(comparisons),
        "max_absolute_arithmetic_difference": max(errors),
    }


def audit_photo(root, expected_methods=8):
    summary = json.loads((root / "summary.json").read_text())
    require(sha(summary["manifest"]) == summary["manifest_sha256"], "Photo manifest hash changed")
    manifest = load_rows(summary["manifest"])
    ids = {row["id"] for row in manifest if row["split"] == "val"}
    require(len(ids) == summary["sources"] == 427, "Expected 427 validation photos")
    require(summary["synthetic_sources"] == 16, "Expected 16 procedural sources")
    labels = [row["label"] for row in summary["models"]]
    methods = CLASSICAL | set(labels)
    require(
        len(labels) == len(set(labels)) == expected_methods - len(CLASSICAL)
        and len(methods) == expected_methods,
        f"Expected {expected_methods} photo methods",
    )
    conditions = {row["name"] for row in summary["protocol"]["conditions"]}
    patterns = set(summary["protocol"]["patterns"])
    require(
        len(conditions) == 7 and patterns == {"RGGB", "BGGR", "GRBG", "GBRG"}, "Photo grid changed"
    )
    expected = {
        (method, kind, identity, condition, pattern)
        for kind, sources in [("photo", ids), ("synthetic", {f"synthetic-{i}" for i in range(16)})]
        for identity in sources
        for method in methods
        for condition in conditions
        for pattern in patterns
    }
    rows = load_rows(root / "per-image.jsonl")
    nulls = validate_rows(
        rows,
        expected,
        {"linear_psnr", "srgb_psnr", "srgb_ssim", "chroma_mae", "gradient_mae"},
        {"highlight_boundary_chroma_mae", "highlight_boundary_rgb_mae", "shadow_linear_psnr"},
    )
    require(
        {row["metric"] for row in summary["paired_comparisons"]}
        == {"linear_psnr", "srgb_psnr", "srgb_ssim"},
        "Photo comparison metrics changed",
    )
    return {
        "cases": len(rows),
        "sources": 443,
        "methods": expected_methods,
        "nullable_metric_cases": nulls,
        **compare_summary(rows, summary),
    }


def audit_real(root, scenes, pairs, crops, expected_methods=8, *, require_rawnind=True):
    summary = json.loads((root / "summary.json").read_text())
    require(
        sha(summary["prepared_manifest"]) == summary["prepared_sha256"], "Prepared manifest changed"
    )
    prepared = json.loads(Path(summary["prepared_manifest"]).read_text())
    require(
        summary["scenes"] == scenes and summary["pairs"] == pairs, "Real scene/pair counts changed"
    )
    # Real reports retain one publisher-weight receipt for two gain adapters.
    labels = {row["label"] for row in summary["models"]}
    if require_rawnind:
        require("RawNIND" in labels, "Missing RawNIND publisher receipt")
    methods = (
        CLASSICAL
        | (labels - {"RawNIND"})
        | (
            {"RawNIND:cfa-ls:publisher", "RawNIND:cfa-channel:publisher"}
            if "RawNIND" in labels
            else set()
        )
    )
    require(len(methods) == expected_methods, f"Expected {expected_methods} real methods")
    expected = {
        (method, "real", crop["id"], case["noisy"]["sha256"], case["metadata"]["pattern"])
        for case in prepared["cases"]
        for crop in case["crops"]
        for method in methods
    }
    require(len(expected) == crops * expected_methods, "Real crop count changed")
    original = load_rows(root / "per-crop.jsonl")
    tile_scene = {crop["id"]: case["scene"] for case in prepared["cases"] for crop in case["crops"]}
    for row in original:
        require(row["scene"] == tile_scene.get(row["tile_id"]), "Crop scene changed")
    normalized = [
        {**row, "kind": "real", "id": row["tile_id"], "condition": row["pair"]} for row in original
    ]
    validate_rows(
        normalized,
        expected,
        {
            "sensor_psnr",
            "reference_samples",
            "ahd_srgb_psnr",
            "ahd_srgb_ssim",
            "ahd_chroma_mae",
            "ahd_gradient_mae",
        },
        set(),
    )
    capture = group_means(original, ["model", "scene", "pair", "pattern"])
    capture_rows = [
        {
            "model": key[0],
            "id": key[1],
            "condition": key[2],
            "pattern": key[3],
            "kind": "real",
            "metrics": scores,
        }
        for key, scores in capture.items()
    ]
    actual_pairs = {
        (row["model"], row["id"], row["condition"], row["pattern"]): row["metrics"]
        for row in summary["per_pair"]
    }
    require(
        len(actual_pairs) == len(summary["per_pair"]) == len(capture), "Capture records changed"
    )
    for key, scores in capture.items():
        require(
            key in actual_pairs and scores.keys() == actual_pairs[key].keys(),
            "Capture keys changed",
        )
        require(
            all(
                abs(value - actual_pairs[key][name]) <= TOLERANCE for name, value in scores.items()
            ),
            "Saved capture mean differs from crop means",
        )
    require(
        {row["metric"] for row in summary["paired_comparisons"]}
        == {"sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim"},
        "Real comparison metrics changed",
    )
    return {
        "cases": len(original),
        "scenes": scenes,
        "pairs": pairs,
        "crops_per_method": crops,
        "methods": expected_methods,
        **compare_summary(capture_rows, summary),
    }


def main(steps, output, trial="fresh"):
    if trial == "convnext-v58":
        require(steps in [1000, 10000], "ConvNeXt audits support the evaluated1000/10000 gates")
        suffix = "1k" if steps == 1000 else "10k"
        workflow = BASE / (
            "runs/dino-convnext-pyramid-v58-workflow.json"
            if steps == 1000
            else "runs/dino-convnext-pyramid-v58-10k-workflow.json"
        )
        expected_status = (
            "completed-first1000-and-evaluation-awaiting-manual-review"
            if steps == 1000
            else "completed-to10000-and-evaluation-awaiting-manual-review"
        )
        expected_methods = 9
        directories = [
            ("photo", f"synthetic-convnext-v58-fresh-{suffix}-full427"),
            ("known", f"paired-known-convnext-v58-fresh-{suffix}"),
            ("unseen", f"paired-unseen-convnext-v58-fresh-{suffix}"),
        ]
    else:
        require(steps in [3000, 10000], "Original fresh audits support3000/10000")
        suffix = {3000: "3k", 10000: "10k"}[steps]
        workflow = BASE / f"runs/fresh-dino-capacity-{suffix}-workflow.json"
        expected_status = f"completed-to{steps}-and-full-review"
        expected_methods = 8
        directories = [
            ("photo", f"synthetic-fresh-dino-capacity-{suffix}-full427"),
            ("known", f"paired-known-fresh-dino-capacity-{suffix}"),
            ("unseen", f"paired-unseen-fresh-dino-capacity-{suffix}"),
        ]
    state = json.loads(workflow.read_text())
    require(
        state["status"] == expected_status,
        "Workflow is not complete; inspect/wait, do not restart",
    )
    output = writable_path(output)
    require(not output.exists(), "Audit output already exists")
    results, inputs = {}, {}
    for name, directory in directories:
        root = BASE / "evaluation" / directory
        results[name] = (
            audit_photo(root, expected_methods)
            if name == "photo"
            else audit_real(
                root,
                *({"known": (4, 8, 72), "unseen": (5, 10, 90)}[name]),
                expected_methods=expected_methods,
            )
        )
        inputs[name] = {
            path.name: sha(path) for path in [root / "summary.json", *root.glob("*.jsonl")]
        }
    receipt = {
        "scope": "Independent saved-score coverage and arithmetic audit only; no inference, pixel/GT-definition validation, speed result, training-repeat uncertainty or model selection.",
        "steps": steps,
        "trial": trial,
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "results": results,
        "inputs": inputs,
        "driver_sha256": sha(__file__),
        "production_aggregation_imported": False,
        "resampling": "1000 paired source/scene bootstrap resamples, seed42, percentile95 interval; matches current declared procedure.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"output": str(output), "results": results}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steps", type=int, choices=[1000, 3000, 10000], required=True)
    parser.add_argument("--trial", choices=["fresh", "convnext-v58"], default="fresh")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.steps, args.output, args.trial)
