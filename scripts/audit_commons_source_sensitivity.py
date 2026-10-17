"""Independently audit saved source sensitivities with Decimal and scalar sums.

Read only numeric case logs and metadata. No production aggregation import,
image/RAW decode, model load or inference.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np

from demosaic.safety import writable_path

METRICS = ["linear_psnr", "srgb_psnr", "srgb_ssim"]
TOLERANCE = 2e-10


def read(p):
    return json.loads(Path(p).read_text())


def sha(p):
    with Path(p).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(p):
    return {"path": str(Path(p).resolve()), "sha256": sha(p)}


def require(value, message):
    if not value:
        raise ValueError(message)


def quantile(sorted_values, probability):
    position = (len(sorted_values) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    fraction = position - lower
    return sorted_values[lower] * (1 - fraction) + sorted_values[upper] * fraction


def native_aliases(sources):
    """Keep display aliases while requiring one exact native-model binding."""
    wanted = defaultdict(list)
    identities = set()
    for source in sources:
        key = (source["label"], source["checkpoint_sha256"])
        require(key not in identities, "Duplicate source descriptor")
        identities.add(key)
        aliases = wanted[source["model_label"]]
        if aliases:
            require(
                {k: v for k, v in source.items() if k != "label"}
                == {k: v for k, v in aliases[0].items() if k != "label"},
                "Conflicting native model alias binding",
            )
        aliases.append(source)
    return wanted


def audit(folder):
    folder = Path(folder)
    result = read(folder / "result.json")
    require(
        result["actual_new_neural_forwards"] == 0 and result["CUDA_initialized"] is False,
        "Expected CPU-only saved-case analysis",
    )
    for key in ["statistics", "frozen_cohorts", "per_source_scores"]:
        require(ref(result[key]["path"]) == result[key], "Input hash differs")
    for item in result["driver_and_helpers"]:
        require(
            sha(folder / "source" / Path(item["path"]).name) == item["sha256"],
            "Archived executed source differs",
        )
    frozen = read(result["frozen_cohorts"]["path"])
    original_ids = set(result["cohorts"]["original427"]["source_ids"])
    require(len(original_ids) == 427, "Expected427 original source IDs")
    require(
        ref(frozen["query_manifest"]["path"]) == frozen["query_manifest"],
        "Query manifest hash differs",
    )
    query_ids = {
        json.loads(line)["id"]
        for line in Path(frozen["query_manifest"]["path"]).read_text().splitlines()
    }
    require(original_ids == query_ids, "Original query identities differ")
    for name, cohort in result["cohorts"].items():
        ids = cohort["source_ids"]
        require(ids == sorted(set(ids)), "Source order/uniqueness differs")
        if name != "original427":
            require(
                ids == sorted(frozen["cohorts"][name]["retained_source_ids"]),
                "Fixed cohort changed",
            )
    source_statistics = read(result["statistics"]["path"])
    source_statistics = source_statistics.get("primary_statistics", source_statistics)
    expected_comparisons = {
        (name, row["first"], row["second"], row["metric"])
        for name in result["cohorts"]
        for row in source_statistics["comparisons"]
        if row["panel"] == "full427" and row["kind"] == "photo"
    }
    actual_comparisons = [
        (r["cohort"], r["first"], r["second"], r["metric"]) for r in result["comparisons"]
    ]
    require(
        len(actual_comparisons) == len(set(actual_comparisons))
        and set(actual_comparisons) == expected_comparisons,
        "Comparison coverage/uniqueness differs",
    )
    grouped = defaultdict(list)
    for source in result["sources"]:
        require(
            sha(source["cases"]) == source["cases_sha256"]
            and sha(source["report"]) == source["report_sha256"],
            "Case/report hash differs",
        )
        grouped[source["cases"]].append(source)
    means, scalar_values = {}, 0
    for path, sources in grouped.items():
        wanted = native_aliases(sources)
        cells = defaultdict(set)
        sums = defaultdict(lambda: {m: Decimal(0) for m in METRICS})
        counts = defaultdict(int)
        with localcontext() as context:
            context.prec = 60
            with Path(path).open() as stream:
                for line in stream:
                    r = json.loads(line)
                    if r["model"] not in wanted or r["kind"] != "photo":
                        continue
                    for source in wanted[r["model"]]:
                        key = (source["label"], source["checkpoint_sha256"], r["id"])
                        cell = (r["condition"], r["pattern"])
                        require(cell not in cells[key], "Duplicate case")
                        cells[key].add(cell)
                        counts[key] += 1
                        for metric in METRICS:
                            value = r["metrics"][metric]
                            require(value is not None and math.isfinite(value), "Invalid metric")
                            sums[key][metric] += Decimal.from_float(float(value))
                            scalar_values += 1
            for source in sources:
                protocol = read(source["report"])["protocol"]
                expected = {
                    (c["name"], p) for c in protocol["conditions"] for p in protocol["patterns"]
                }
                keys = [k for k in cells if k[:2] == (source["label"], source["checkpoint_sha256"])]
                require({k[2] for k in keys} == original_ids, "Source coverage differs")
                for key in keys:
                    require(
                        cells[key] == expected and counts[key] == 28, "Noise/CFA coverage differs"
                    )
                    means[key] = {m: float(sums[key][m] / Decimal(28)) for m in METRICS}
    source_errors = []
    source_rows = [
        json.loads(s) for s in Path(result["per_source_scores"]["path"]).read_text().splitlines()
    ]
    seen = set()
    for row in source_rows:
        key = (row["label"], row["checkpoint_sha256"], row["source_id"])
        require(key not in seen and key in means, "Unexpected/duplicate source score")
        seen.add(key)
        for metric in METRICS:
            error = abs(row["metrics"][metric] - means[key][metric])
            require(error <= TOLERANCE, "Decimal source mean differs")
            source_errors.append(error)
    require(seen == means.keys(), "Missing source score")
    indices = {}
    for name, cohort in result["cohorts"].items():
        n = len(cohort["source_ids"])
        values = np.random.default_rng(42).integers(n, size=(1000, n))
        require(
            hashlib.sha256(values.tobytes()).hexdigest()
            == cohort["bootstrap_indices_bytes_sha256"],
            "Bootstrap draw binding differs",
        )
        indices[name] = values
    comparison_errors = []

    def close(actual, expected):
        if actual is None or expected is None:
            require(actual is expected, "Nullable statistic differs")
            return
        error = abs(actual - expected)
        require(math.isfinite(actual) and error <= TOLERANCE, "Independent statistic differs")
        comparison_errors.append(error)

    for row in result["comparisons"]:
        name, metric = row["cohort"], row["metric"]
        ids = result["cohorts"][name]["source_ids"]
        require(row["sources"] == len(ids), "Comparison source count differs")
        keys = [
            (row["first"], row["first_checkpoint_sha256"]),
            (row["second"], row["second_checkpoint_sha256"]),
        ]
        x, y = [[means[(*key, identity)][metric] for identity in ids] for key in keys]
        delta = [a - b for a, b in zip(x, y, strict=True)]
        close(math.fsum(x) / len(ids), row["first_source_balanced_mean"])
        close(math.fsum(y) / len(ids), row["second_source_balanced_mean"])
        close(math.fsum(delta) / len(ids), row["mean_first_minus_second"])
        resamples = sorted(
            math.fsum(delta[int(i)] for i in draw) / len(ids) for draw in indices[name]
        )
        for probability, expected in zip(
            [0.025, 0.975], row["source_bootstrap_95_interval"], strict=True
        ):
            close(quantile(resamples, probability), expected)
        all_delta = [
            means[(*keys[0], identity)][metric] - means[(*keys[1], identity)][metric]
            for identity in sorted(original_ids)
        ]
        close(
            math.fsum(delta) / len(ids) - math.fsum(all_delta) / 427,
            row["change_from_original_mean_delta"],
        )
        excluded = sorted(original_ids - set(ids))
        require(row["excluded_source_count"] == len(excluded), "Excluded source count differs")
        excluded_values = [
            means[(*keys[0], identity)][metric] - means[(*keys[1], identity)][metric]
            for identity in excluded
        ]
        close(
            None if not excluded else math.fsum(excluded_values) / len(excluded),
            row["excluded_source_mean_delta_descriptive_only"],
        )
    return {
        "status": "completed-independent-Decimal-source-and-scalar-bootstrap-audit",
        "producer_result": ref(folder / "result.json"),
        "auditor": ref(__file__),
        "source_rows": len(means),
        "raw_case_metric_values_reaggregated": scalar_values,
        "source_metric_scalars": len(source_errors),
        "source_max_difference": max(source_errors),
        "comparisons": len(result["comparisons"]),
        "comparison_statistic_scalars": len(comparison_errors),
        "comparison_max_difference": max(comparison_errors),
        "actual_new_neural_forwards": 0,
        "limits": "Independent arithmetic and coverage from existing score logs only; metrics/prediction pixels and classical witness definitions are not recomputed. Same specified NumPy PCG64 draws, separately reconstructed and byte-bound; scalar summation and manual quantile replace production vectorized bootstrap. Does not measure training/selection or unknown scene-family uncertainty or promote a model.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result_directory", type=Path)
    args = parser.parse_args()
    os.nice(10)
    output = writable_path(args.result_directory / "independent-audit.json")
    require(not output.exists(), "Audit already exists")
    result = audit(args.result_directory)
    output.write_text(json.dumps(result, indent=2) + "\n")
    shutil.copyfile(__file__, output.parent / "independent-auditor-source.py")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
