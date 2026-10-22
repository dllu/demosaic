"""Separate saved photo contrasts by explicit ADC/positive-noise priors, without inference."""

import argparse
import datetime
import math
import shutil
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from audit_fresh_dino_statistics import CLASSICAL, audit_photo, load_rows
from train_directional_bank_trial import read, ref, save

from demosaic.safety import writable_path


def condition_subsets(conditions):
    names, adc, positive = [], [], []
    for condition in conditions:
        name = condition["name"]
        assert isinstance(name, str) and name and name not in names
        values = [condition[key] for key in ("shot", "read")]
        assert all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in values)
        names.append(name)
        (adc if values == [0, 0] else positive).append(name)
    assert len(adc) == 1 and positive, "Require one explicit ADC prior and positive-noise cases"
    return {"all": names, "ADC": adc, "positive_noise": positive}


def paired_sources(first, second):
    assert first.keys() == second.keys() and first
    identities = sorted(first)
    deltas = [first[key] - second[key] for key in identities]
    mean = math.fsum(deltas) / len(deltas)
    indices = np.random.default_rng(42).integers(len(deltas), size=(1000, len(deltas)))
    draws = np.asarray(deltas)[indices].mean(axis=1)
    interval = np.quantile(draws, [0.025, 0.975]).tolist()
    ranked = sorted(zip(identities, deltas, strict=True), key=lambda item: (item[1], item[0]))
    return {
        "sources": len(deltas),
        "mean_first_minus_second": mean,
        "source_bootstrap_95_interval": interval,
        "sources_improved": sum(value > 0 for value in deltas),
        "sources_unchanged": sum(value == 0 for value in deltas),
        "minimum": min(deltas),
        "median": float(np.median(deltas)),
        "maximum": max(deltas),
        "worst10": [{"id": key, "delta": value} for key, value in ranked[:10]],
        "source_deltas": [
            {"id": key, "delta": value} for key, value in zip(identities, deltas, strict=True)
        ],
    }


def summarize(rows, *, methods, primary_models, sources, conditions, patterns):
    """Require the full declared grid, then average within each source before comparisons."""
    assert len(primary_models) == len(set(primary_models)) == 4
    assert set(primary_models) <= set(methods) and len(methods) == len(set(methods))
    assert len(patterns) == len(set(patterns)) and patterns
    assert set(sources) == {"photo", "synthetic"}
    assert all(ids and len(ids) == len(set(ids)) for ids in sources.values())
    subsets = condition_subsets(conditions)
    expected = {
        (model, kind, identity, condition, pattern)
        for model in methods
        for kind, identities in sources.items()
        for identity in identities
        for condition in subsets["all"]
        for pattern in patterns
    }
    keyed = {}
    for row in rows:
        key = tuple(row[name] for name in ("model", "kind", "id", "condition", "pattern"))
        assert key in expected and key not in keyed, ("Unexpected or duplicate observation", key)
        values = {name: row["metrics"][name] for name in ("srgb_psnr", "srgb_ssim")}
        assert all(
            type(value) in (float, int) and math.isfinite(value) for value in values.values()
        )
        keyed[key] = values
    assert keyed.keys() == expected, "Missing observation in the declared score grid"
    groups, means = {}, []
    for subset, condition_names in subsets.items():
        for kind, identities in sources.items():
            for model in primary_models:
                for metric in ("srgb_psnr", "srgb_ssim"):
                    source_means = {
                        identity: math.fsum(
                            keyed[model, kind, identity, condition, pattern][metric]
                            for condition in condition_names
                            for pattern in patterns
                        )
                        / (len(condition_names) * len(patterns))
                        for identity in identities
                    }
                    groups[subset, kind, model, metric] = source_means
                    means.append(
                        {
                            "subset": subset,
                            "kind": kind,
                            "model": model,
                            "metric": metric,
                            "sources": len(identities),
                            "cases_per_source": len(condition_names) * len(patterns),
                            "mean": math.fsum(source_means.values()) / len(source_means),
                        }
                    )
    pairs = [(3, 2), (2, 1), (3, 1), (1, 0), (2, 0), (3, 0)]
    comparisons = []
    for subset in subsets:
        for kind in sources:
            for metric in ("srgb_psnr", "srgb_ssim"):
                for a, b in pairs:
                    first, second = primary_models[a], primary_models[b]
                    comparisons.append(
                        {
                            "subset": subset,
                            "kind": kind,
                            "metric": metric,
                            "first": first,
                            "second": second,
                            **paired_sources(
                                groups[subset, kind, first, metric],
                                groups[subset, kind, second, metric],
                            ),
                        }
                    )
    return {
        "conditions_by_subset": subsets,
        "source_balanced_means": means,
        "paired_comparisons": comparisons,
    }


def main(root, output, *, expect_adc_pair=False):
    output = writable_path(output)
    assert not output.exists() and not output.with_suffix(".executed-source.py").exists()
    assert root.is_dir()
    inputs = [ref(root / name) for name in ("summary.json", "per-image.jsonl")]
    summary = read(root / "summary.json")
    models = summary["models"]
    assert len(models) == 6, "Expected four joint models and both RawNIND adapters"
    primary = models[:4]
    assert len({model["sha256"] for model in primary}) == 4
    assert all(model["compute_precision"] == "float32" for model in primary)
    if expect_adc_pair:
        assert all(
            model["effective_model_config"]["adc_cfa_projection"] is True for model in primary[2:]
        )
    # Reuse the independent full-grid/summary arithmetic audit before any subset arithmetic.
    coverage = audit_photo(root, expected_methods=9)
    manifest = ref(summary["manifest"])
    assert manifest["sha256"] == summary["manifest_sha256"]
    inputs.append(manifest)
    sources = {
        "photo": sorted(row["id"] for row in load_rows(manifest["path"]) if row["split"] == "val"),
        "synthetic": [f"synthetic-{i}" for i in range(summary["synthetic_sources"])],
    }
    result = summarize(
        load_rows(root / "per-image.jsonl"),
        methods=sorted(CLASSICAL | {model["label"] for model in models}),
        primary_models=[model["label"] for model in primary],
        sources=sources,
        conditions=summary["protocol"]["conditions"],
        patterns=summary["protocol"]["patterns"],
    )
    # All-condition means must agree with the completed production summaries.
    for item in result["source_balanced_means"]:
        if item["subset"] == "all":
            previous = next(
                row
                for row in summary["overall"]
                if row["model"] == item["model"] and row["kind"] == item["kind"]
            )
            assert abs(previous["metrics"][item["metric"]]["mean"] - item["mean"]) < 2e-10
    for item in inputs:
        assert ref(item["path"]) == item
    output.parent.mkdir(parents=True, exist_ok=True)
    operator = output.with_suffix(".executed-source.py")
    shutil.copyfile(__file__, operator)
    save(
        output,
        {
            "status": "completed-CPU-saved-photo-ADC-and-positive-noise-source-contrasts",
            "recorded_local": datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            "operator": ref(operator),
            "inputs": inputs,
            "full_grid_and_summary_arithmetic": coverage,
            "primary_checkpoints": [
                {
                    key: model[key]
                    for key in (
                        "label",
                        "sha256",
                        "step",
                        "compute_precision",
                        "effective_model_config",
                    )
                }
                for model in primary
            ],
            "common_ADC_policy_required_and_checked": expect_adc_pair,
            "resampling": "1000 paired-source bootstrap resamples; seed42; percentile95 intervals. Average the selected condition/CFA cells within each source before resampling. ADC/positive groups use explicit shot/read values, regardless of labels. No training-seed or independent-test uncertainty.",
            **result,
            "scope": "Independent saved scalar coverage/aggregation and subset contrasts only. No model inference, noise generation, image decoding, metric recomputation from pixels, checkpoint selection or promotion. The contrast between model indices3 and2 is primary; interpreting it as ADC-training benefit additionally requires the completed experiment's matched lineage, audits and declared common inference policy. Full camera/color/texture checks and actual native-crop review remain separate.",
        },
    )
    print(ref(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expect-adc-pair", action="store_true")
    args = parser.parse_args()
    main(args.root, args.output, expect_adc_pair=args.expect_adc_pair)
