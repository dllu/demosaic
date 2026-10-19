"""Audit saved component scalars and publish their complete conditional contrasts."""

import argparse
import hashlib
import itertools
import json
import math
from collections import defaultdict
from pathlib import Path

FIELDS = ("kind", "level", "contrast", "period", "condition", "pattern", "draw", "model")
MODES = (
    "control/full",
    "control/base",
    "bank/full",
    "bank/base",
    "bank/bank-logits-zero",
)
CONTRASTS = (
    ("bank/full", "control/full"),
    ("bank/base", "control/base"),
    ("bank/full", "bank/bank-logits-zero"),
    ("bank/bank-logits-zero", "bank/base"),
    ("control/full", "control/base"),
)
METRICS = {
    "carrier": {
        "in_phase_gain",
        "gain_channel_std",
        "quadrature_gain",
        "amplitude_ratio",
        "dc_bias_abs",
        "noncarrier_rms",
        "linear_srgb_rmse",
    },
    "flat": {
        "dc_bias_abs_rgb",
        "linear_srgb_rmse",
        "spatial_luma_rms",
        "relative_band_rms",
        "relative_peak_band_contrast",
    },
}


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def check_ref(item):
    assert ref(item["path"])["sha256"] == item["sha256"], item["path"]


def stats(values):
    mean = math.fsum(values) / len(values)
    return {
        "mean": mean,
        "std": math.sqrt(math.fsum((x - mean) ** 2 for x in values) / len(values)),
        "min": min(values),
        "max": max(values),
    }


def main(root, output):
    root, output = root.resolve(), output.resolve()
    repository = Path(__file__).resolve().parents[1]
    assert root.is_relative_to(repository) and output.is_relative_to(repository)
    assert not output.exists()
    inputs = [
        ref(root / p) for p in ("plan.json", "cpu-preflight/summary.json", "cuda/summary.json")
    ]
    plan, cpu, result = [json.loads(Path(p["path"]).read_text()) for p in inputs]
    assert result["status"] == "completed-read-only-bank-component-diagnostic"
    assert cpu["status"] == "completed-CPU-hook-and-state-preflight-no-quality-result"
    assert result["driver"] == cpu["driver"] == plan["worker"]
    assert (
        ref(repository / "scripts/diagnose_directional_bank_components.py")["sha256"]
        == (plan["worker"]["sha256"])
    )
    assert ref(result["plan"]["path"]) == ref(cpu["plan"]["path"]) == inputs[0]
    assert result["plan"]["sha256"] == cpu["plan"]["sha256"] == inputs[0]["sha256"]
    inputs += plan["inputs"] + [result["per_case"], result["driver"], cpu["per_case"]]
    inputs += [{"path": p, "sha256": s} for p, s in plan["frozen_files"].items()]
    for item in inputs:
        check_ref(item)
    assert len(plan["frozen_files"]) == 236
    assert result["device"] == "cuda:0" and not result["preflight"]
    assert result["size"] == 256 and result["roi_xywh"] == [48, 48, 160, 160]
    assert result["input_batches"] == 112 and result["distinct_observations_per_mode"] == 448
    assert result["shared_inputs_exact"] and result["new_training_updates"] == 0
    assert result["new_checkpoint_or_default"] is False
    assert tuple(plan["configured_modes"]) == MODES
    assert len(result["weights_unchanged"]) == 2
    for weight, checkpoint in zip(result["weights_unchanged"], plan["checkpoints"], strict=True):
        assert weight["checkpoint"] == checkpoint
        assert weight["DINO_sha256"] == plan["DINO_sha256"]
        assert len(weight["full_state_sha256_before_and_after"]) == 64

    signals = [
        ("carrier", level, contrast, period)
        for level, contrast, period in itertools.product([0.01, 0.18], [0.02, 0.1], [4, 8, 16])
    ] + [("flat", level, 0, None) for level in [0.01, 0.18]]
    batches = {
        (*signal, condition, pattern)
        for signal in signals
        for condition, pattern in itertools.product(
            ["adc-only", "iso12800-prior"], ["RGGB", "BGGR", "GRBG", "GBRG"]
        )
    }
    expected = {(*batch, draw, mode) for batch in batches for draw in range(4) for mode in MODES}
    rows = [json.loads(line) for line in Path(result["per_case"]["path"]).read_text().splitlines()]
    keyed, grouped = {}, defaultdict(list)
    for row in rows:
        key = tuple(row[k] for k in FIELDS)
        assert key in expected and key not in keyed, key
        assert row["metrics"].keys() == METRICS[row["kind"]]
        assert all(math.isfinite(v) for v in row["metrics"].values())
        keyed[key] = row["metrics"]
        grouped[key[:5] + (key[-1],)].append(row["metrics"])
    assert set(keyed) == expected and len(rows) == 2240
    observations = {tuple(json.loads(k)): v for k, v in result["observations"].items()}
    assert set(observations) == batches
    component_stats = result["case_component_statistics"]
    assert len(component_stats) == 224
    assert {(r["model"], *r["case"]) for r in component_stats} == {
        (model, *batch) for model in ["control", "bank"] for batch in batches
    }
    for row in component_stats:
        assert row["input_sha256"] == observations[tuple(row["case"])]
        assert row["full_replays_exactly"] and row["model_output_is_final_directional_output"]
        assert row["censored_input_fraction"] == 0
        assert row["variance_floor_fraction"] == (1.0 if row["case"][4] == "adc-only" else 0.0)

    errors = []
    summaries = result["carrier_summary"] + result["flat_summary"]
    assert len(summaries) == len(grouped) == 140
    seen = set()
    for row in summaries:
        key = ("carrier" if row["period"] else "flat",) + tuple(
            row[k] for k in ("level", "contrast", "period", "condition", "model")
        )
        assert key not in seen
        seen.add(key)
        cases = grouped[key]
        assert row["cases"] == len(cases) == 16 and row["metrics"].keys() == cases[0].keys()
        for name in cases[0]:
            computed = stats([r[name] for r in cases])
            assert row["metrics"][name].keys() == computed.keys()
            for field, value in computed.items():
                error = abs(value - row["metrics"][name][field])
                assert error < 1e-12
                errors.append(error)
    assert seen == grouped.keys()

    original = {
        tuple(row[k] for k in FIELDS): row["metrics"]
        for row in map(json.loads, Path(plan["original_cases"]["path"]).read_text().splitlines())
    }
    replay = defaultdict(float)
    for key, metric in keyed.items():
        if not key[-1].endswith("/full"):
            continue
        index = 0 if key[-1] == "control/full" else 1
        checkpoint = plan["checkpoints"][index]
        run = Path(checkpoint["path"]).parent.name
        baseline = original[key[:-1] + (f"{index}:{run}:step-4000",)]
        for name, value in metric.items():
            error = abs(value - baseline[name])
            replay[name] = max(replay[name], error)
            tolerance = (
                plan["baseline_gain_atol"]
                if "gain" in name or name == "amplitude_ratio"
                else plan["baseline_absolute_error_atol"]
            )
            assert error <= tolerance
    assert dict(replay) == result["baseline_metric_replay_max_abs_errors"]

    contrasts = []
    for signal in signals:
        for condition in ["adc-only", "iso12800-prior"]:
            record = dict(zip(FIELDS[:5], (*signal, condition), strict=True))
            record["paired_cases"] = 16
            record["differences_of_metrics"] = {}
            for positive, negative in CONTRASTS:
                differences = defaultdict(list)
                for pattern, draw in itertools.product(["RGGB", "BGGR", "GRBG", "GBRG"], range(4)):
                    base = (*signal, condition, pattern, draw)
                    for name in METRICS[signal[0]]:
                        differences[name].append(
                            keyed[base + (positive,)][name] - keyed[base + (negative,)][name]
                        )
                record["differences_of_metrics"][f"{positive} minus {negative}"] = {
                    name: stats(values) for name, values in sorted(differences.items())
                }
            contrasts.append(record)
    for item in inputs:
        check_ref(item)
    publication = {
        "status": "completed-independent-bank-component-scalar-audit",
        "audit_driver": ref(__file__),
        "audit": {
            "metric_rows": len(rows),
            "full_model_replay_rows": 896,
            "groups": len(summaries),
            "summary_scalars_checked": len(errors),
            "max_summary_arithmetic_error": max(errors),
            "bound": 1e-12,
            "frozen_files_verified": len(plan["frozen_files"]),
            "inputs": inputs[:3],
        },
        "plan": plan,
        "diagnostic": result,
        "paired_contrasts": contrasts,
        "scope": "Independent saved-scalar coverage/arithmetic/replay and file-SHA checks only. Model replay and tensor-state identity were asserted by the separately executed diagnostic, not recomputed here. Contrasts are differences of metrics at fixed trained weights, not metrics of isolated component images, independent retraining effects, scene confidence intervals, or training-gradient causes. No new training/checkpoint/default or quality promotion.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x") as stream:
        stream.write(json.dumps(publication, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "output": ref(output),
                **{k: v for k, v in publication["audit"].items() if k != "inputs"},
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.root, args.output)
