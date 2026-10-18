"""Reanalyze completed photo case scores on predeclared Commons source subsets.

No inference, new targets, dataset edits or selection from model errors. Rebuild
the original full-panel comparisons before adding the fixed418/416 sensitivities.
"""

import argparse
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

import numpy as np
import torch
from audit_fresh_dino_statistics import CLASSICAL, average, group_means, require, sha
from audit_nonlocal_reference_review import control_differences
from compare_long_commons_scores import PHOTO_FIELDS

from demosaic.safety import writable_path

METRICS = ["linear_psnr", "srgb_psnr", "srgb_ssim"]
TOLERANCE = 2e-10


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def statistics_payload(container):
    if container.get("review_complete") is True:
        require(
            container["status"] == "completed-controlled-first4000-long-data-review-no-promotion",
            "Unsupported historical review",
        )
        return container["primary_statistics"]
    require(
        container.get("status")
        in {
            "completed-original20k-long-data-statistics-and-4k-progress",
            "completed-normalization-trial-statistics-and-parent-comparisons",
            "completed-normalization-original4000-statistics-and-first1k-progress",
            "completed-packed-isotropic-first32000-example-statistics",
            "completed-packed-isotropic-quarter-statistics-and-first8k-progress",
            "completed-packed-isotropic-mixed16-first32000-example-statistics",
            "completed-packed-isotropic-mixed16-quarter160000-example-statistics",
            "completed-objective-primary-numerical-review-awaiting-native-and-color-review",
        },
        "Model comparison statistics are incomplete",
    )
    return container


def source_model(summary, source):
    """Bind the method label as well as shared weights (e.g. gain adapters)."""
    models = [
        model
        for model in summary["models"]
        if model.get("sha256", model.get("weight_sha256")) == source["checkpoint_sha256"]
        and model["label"] == source["model_label"]
    ]
    require(len(models) == 1, "Checkpoint/model label binding differs")
    return models[0]


def photo_scores(records, label, source_ids, conditions, patterns):
    chosen = [r for r in records if r["model"] == label and r["kind"] == "photo"]
    keys = [(r["id"], r["condition"], r["pattern"]) for r in chosen]
    require(len(keys) == len(set(keys)), "Duplicate photographic observation")
    expected = {(identity, c, p) for identity in source_ids for c in conditions for p in patterns}
    require(set(keys) == expected, "Photographic source/condition/CFA coverage differs")
    require(
        all(
            r["metrics"].get(k) is not None and math.isfinite(r["metrics"][k])
            for r in chosen
            for k in METRICS
        ),
        "Missing/nonfinite core photo metric",
    )
    return {
        identity[0]: {k: values[k] for k in METRICS}
        for identity, values in group_means(chosen, ["id"]).items()
    }


def compare_values(first, second, indices):
    first, second = np.asarray(first, dtype=np.float64), np.asarray(second, dtype=np.float64)
    require(
        first.shape == second.shape and first.ndim == 1 and first.size > 0,
        "Invalid paired source vectors",
    )
    require(np.isfinite(first).all() and np.isfinite(second).all(), "Nonfinite source means")
    require(
        indices.ndim == 2
        and indices.shape[1] == first.size
        and indices.min() >= 0
        and indices.max() < first.size,
        "Invalid bootstrap source indices",
    )
    delta = first - second
    return {
        "first_source_balanced_mean": average(first.tolist()),
        "second_source_balanced_mean": average(second.tolist()),
        "mean_first_minus_second": average(delta.tolist()),
        "source_bootstrap_95_interval": np.quantile(
            delta[indices].mean(1), [0.025, 0.975]
        ).tolist(),
    }


def run(statistics_path, statistics_sha256, cohort_path, cohort_sha256, output):
    output = writable_path(output)
    require(not output.exists(), "Output already exists; choose a new result directory")
    require(
        sha(statistics_path) == statistics_sha256 and sha(cohort_path) == cohort_sha256,
        "Statistics/cohort input hash differs",
    )
    container, frozen = read(statistics_path), read(cohort_path)
    stats = statistics_payload(container)
    query_ref = frozen["query_manifest"]
    require(ref(query_ref["path"]) == query_ref, "Frozen query manifest changed")
    query_rows = [json.loads(s) for s in Path(query_ref["path"]).read_text().splitlines()]
    original_ids = sorted(r["id"] for r in query_rows)
    require(
        len(original_ids) == len(set(original_ids)) == 427
        and all(r["split"] == "val" for r in query_rows),
        "Expected427 distinct existing development sources",
    )
    cohorts = {"original427": original_ids}
    for name, count in [
        ("known-capture-series-excluded", 418),
        ("known-capture-series-and-sites-excluded", 416),
    ]:
        definition = frozen["cohorts"][name]
        ids = sorted(definition["retained_source_ids"])
        excluded = {r["source"]["id"] for r in definition["excluded"]}
        require(
            len(ids) == len(set(ids)) == definition["source_count"] == count,
            "Frozen cohort size differs",
        )
        require(
            not set(ids) & excluded and set(ids) | excluded == set(original_ids),
            "Frozen retained/excluded identities do not partition original427",
        )
        cohorts[name] = ids
    pairs = [p for p in stats["sources"] if p["panel"] == "full427"]
    expected_pairs = {
        "completed-normalization-trial-statistics-and-parent-comparisons": [3],
        "completed-normalization-original4000-statistics-and-first1k-progress": [5],
        "completed-packed-isotropic-first32000-example-statistics": [9],
        "completed-packed-isotropic-quarter-statistics-and-first8k-progress": [11],
        "completed-packed-isotropic-mixed16-first32000-example-statistics": [13],
        "completed-packed-isotropic-mixed16-quarter160000-example-statistics": [13],
    }.get(container.get("status"), [7, 9])
    require(len(pairs) in expected_pairs, "Unexpected original photo comparison coverage")
    expected = {
        (r["first"], r["second"], r["metric"]): r
        for r in stats["comparisons"]
        if r["panel"] == "full427" and r["kind"] == "photo"
    }
    require(
        len(expected) == len(pairs) * 3,
        "Published full-panel comparisons are missing or duplicated",
    )
    file_cache, descriptors, controls = {}, {}, {}

    def records(path, digest):
        require(sha(path) == digest, "Saved case/report hash changed: " + str(path))
        if path not in file_cache:
            file_cache[path] = (
                [json.loads(s) for s in Path(path).read_text().splitlines()]
                if str(path).endswith(".jsonl")
                else read(path)
            )
        return file_cache[path]

    def descriptor(source):
        key = (source["label"], source["checkpoint_sha256"])
        if key in descriptors:
            require(descriptors[key]["source"] == source, "Conflicting model/source descriptor")
            return descriptors[key]
        summary = records(source["report"], source["report_sha256"])
        cases = records(source["cases"], source["cases_sha256"])
        model = source_model(summary, source)
        protocol = summary["protocol"]
        conditions, patterns = [r["name"] for r in protocol["conditions"]], protocol["patterns"]
        require(
            len(conditions) == len(set(conditions)) == 7
            and set(patterns) == {"RGGB", "BGGR", "GRBG", "GBRG"},
            "Noise/CFA protocol differs",
        )
        scores = photo_scores(cases, source["model_label"], original_ids, conditions, patterns)
        if source["cases"] not in controls:
            selected = [r for r in cases if r["model"] in CLASSICAL]
            identity = lambda r: tuple(
                r[k] for k in ["model", "kind", "id", "condition", "pattern"]
            )
            values = {identity(r): r["metrics"] for r in selected}
            require(
                len(values) == len(selected) == 443 * 28 * 3,
                "Classical observation coverage/uniqueness differs",
            )
            controls[source["cases"]] = values
        value = {
            "source": source,
            "summary": summary,
            "scores": scores,
            "native_model_metadata": model,
        }
        descriptors[key] = value
        return value

    indices = {
        name: np.random.default_rng(42).integers(len(ids), size=(1000, len(ids)))
        for name, ids in cohorts.items()
    }
    comparisons, witnesses = [], []
    full_max = 0.0
    for pair in pairs:
        first, second = descriptor(pair["first"]), descriptor(pair["second"])
        require(
            all(first["summary"].get(k) == second["summary"].get(k) for k in PHOTO_FIELDS),
            "Observation metadata differs",
        )
        witness = control_differences(
            controls[pair["second"]["cases"]], controls[pair["first"]["cases"]]
        )
        witnesses.append(
            {"first": pair["first"]["label"], "second": pair["second"]["label"], **witness}
        )
        for name, ids in cohorts.items():
            for metric in METRICS:
                x, y = [
                    [d["scores"][identity][metric] for identity in ids] for d in [first, second]
                ]
                result = compare_values(x, y, indices[name])
                original = expected[(pair["first"]["label"], pair["second"]["label"], metric)]
                if name == "original427":
                    for field, actual in result.items():
                        error = float(
                            np.max(np.abs(np.asarray(actual) - np.asarray(original[field])))
                        )
                        require(
                            error <= TOLERANCE, "Original published statistic does not reproduce"
                        )
                        full_max = max(full_max, error)
                excluded_ids = sorted(set(original_ids) - set(ids))
                excluded_delta = [
                    first["scores"][identity][metric] - second["scores"][identity][metric]
                    for identity in excluded_ids
                ]
                excluded_mean = average(excluded_delta)
                if excluded_mean is not None:
                    reconstructed = (
                        len(ids) * result["mean_first_minus_second"]
                        + len(excluded_ids) * excluded_mean
                    ) / 427
                    require(
                        abs(reconstructed - original["mean_first_minus_second"]) <= TOLERANCE,
                        "Retained/excluded source decomposition differs",
                    )
                comparisons.append(
                    {
                        "cohort": name,
                        "sources": len(ids),
                        "kind": "photo",
                        "metric": metric,
                        "first": pair["first"]["label"],
                        "second": pair["second"]["label"],
                        "first_checkpoint_sha256": pair["first"]["checkpoint_sha256"],
                        "second_checkpoint_sha256": pair["second"]["checkpoint_sha256"],
                        **result,
                        "change_from_original_mean_delta": result["mean_first_minus_second"]
                        - original["mean_first_minus_second"],
                        "excluded_source_count": len(excluded_ids),
                        "excluded_source_mean_delta_descriptive_only": excluded_mean,
                    }
                )
    output.mkdir(parents=True)
    per_source = output / "per-source.jsonl"
    with per_source.open("x") as stream:
        for (label, digest), d in sorted(descriptors.items()):
            for identity, metrics in sorted(d["scores"].items()):
                stream.write(
                    json.dumps(
                        {
                            "label": label,
                            "checkpoint_sha256": digest,
                            "source_id": identity,
                            "metrics": metrics,
                        }
                    )
                    + "\n"
                )
    helpers = [
        Path(__file__),
        Path(__file__).with_name("audit_fresh_dino_statistics.py"),
        Path(__file__).with_name("audit_nonlocal_reference_review.py"),
        Path(__file__).with_name("compare_long_commons_scores.py"),
    ]
    (output / "source").mkdir()
    for p in helpers:
        shutil.copyfile(p, output / "source" / p.name)
    result = {
        "status": "completed-existing-photo-case-source-sensitivity-no-inference",
        "statistics": ref(statistics_path),
        "source_statistics_status": container["status"],
        "frozen_cohorts": ref(cohort_path),
        "driver_and_helpers": [ref(p) for p in helpers],
        "cohorts": {
            name: {
                "source_ids": ids,
                "source_count": len(ids),
                "source_IDs_newline_sha256": hashlib.sha256(
                    ("\n".join(ids) + "\n").encode()
                ).hexdigest(),
                "bootstrap_indices_shape": list(indices[name].shape),
                "bootstrap_indices_bytes_sha256": hashlib.sha256(
                    indices[name].tobytes()
                ).hexdigest(),
            }
            for name, ids in cohorts.items()
        },
        "sources": [d["source"] for d in descriptors.values()],
        "native_model_metadata": [d["native_model_metadata"] for d in descriptors.values()],
        "observation_metadata_fields_exact": PHOTO_FIELDS,
        "per_source_scores": ref(per_source),
        "comparisons": comparisons,
        "classical_witnesses": witnesses,
        "original_statistics_reproduced": len(pairs) * 3,
        "original_max_difference": full_max,
        "resampling": {
            "paired_source_bootstrap": 1000,
            "seed": 42,
            "numpy": np.__version__,
            "interval": "linear quantile .025/.975",
        },
        "actual_new_neural_forwards": 0,
        "CUDA_initialized": torch.cuda.is_initialized(),
        "limits": "Source-ID sensitivity on existing development scores, not fresh inference or a new scene-independent test. Fixed cohorts selected from content/metadata after historical4k review but before original20k full427 scoring. Unknown aliases, ancestor-model/foundation pretraining exposure and training/selection uncertainty remain unmeasured. Classical bounds/observation metadata and all original427 results are retained. No quality promotion or native-pixel review is supplied by these statistics.",
    }
    require(not torch.cuda.is_initialized(), "Unexpected CUDA initialization")
    require(
        sha(statistics_path) == statistics_sha256 and sha(cohort_path) == cohort_sha256,
        "Input changed during analysis",
    )
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--statistics", required=True, type=Path)
    parser.add_argument("--statistics-sha256", required=True)
    parser.add_argument("--cohorts", required=True, type=Path)
    parser.add_argument("--cohort-sha256", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    os.nice(10)
    torch.set_num_threads(2)
    require(not torch.cuda.is_initialized(), "Run with CUDA hidden")
    result = run(
        args.statistics, args.statistics_sha256, args.cohorts, args.cohort_sha256, args.output
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "status",
                    "original_statistics_reproduced",
                    "original_max_difference",
                    "actual_new_neural_forwards",
                ]
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
