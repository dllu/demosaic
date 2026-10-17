"""Check complete declared carrier/flat coverage and saved summary arithmetic."""

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def audit(summary, rows, candidates=1):
    """Use independent scalar arithmetic, without inference or unavailable arrays."""
    if type(candidates) is not int or candidates < 1:
        raise ValueError("Expected candidate count must be a positive integer")
    labels = [r["label"] for r in summary["models"]]
    assert len(labels) == len(set(labels)) == candidates and "malvar" not in labels
    models = {*labels, "malvar"}
    assert summary["roi_xywh"] == [48, 48, 160, 160]
    assert summary["flat_frequency_band_cycles_per_pixel"] == [1 / 48, 0.22]
    signals = [
        ("carrier", level, contrast, period)
        for level in [0.01, 0.18]
        for contrast in [0.02, 0.1]
        for period in [4, 8, 16]
    ] + [("flat", level, 0, None) for level in [0.01, 0.18]]
    expected = {
        (kind, level, contrast, period, condition, pattern, draw, model)
        for kind, level, contrast, period in signals
        for condition in ["adc-only", "iso12800-prior"]
        for pattern in ["RGGB", "BGGR", "GRBG", "GBRG"]
        for draw in range(4)
        for model in models
    }
    fields = ["kind", "level", "contrast", "period", "condition", "pattern", "draw", "model"]
    seen, grouped = set(), defaultdict(list)
    names_by_kind = {
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
    for row in rows:
        key = tuple(row[k] for k in fields)
        assert key not in seen and key in expected, key
        seen.add(key)
        assert set(row["metrics"]) == names_by_kind[row["kind"]]
        assert all(math.isfinite(x) for x in row["metrics"].values())
        grouped[
            (row["level"], row["contrast"], row["period"], row["condition"], row["model"])
        ].append(row["metrics"])
    assert seen == expected and len(rows) == len(expected)
    assert len(summary["carrier_summary"]) == 24 * len(models)
    assert len(summary["flat_summary"]) == 4 * len(models)
    records = summary["carrier_summary"] + summary["flat_summary"]
    actual = {
        tuple(r[k] for k in ["level", "contrast", "period", "condition", "model"]): r
        for r in records
    }
    assert len(actual) == len(records) == len(grouped) == 28 * len(models)
    assert actual.keys() == grouped.keys()
    errors = []
    for key, values in grouped.items():
        row = actual[key]
        assert row["cases"] == len(values) == 16
        assert row["metrics"].keys() == values[0].keys()
        for name in values[0]:
            xs = [v[name] for v in values]
            mean = math.fsum(xs) / len(xs)
            std = math.sqrt(math.fsum((x - mean) ** 2 for x in xs) / len(xs))
            metrics = {"mean": mean, "std": std, "min": min(xs), "max": max(xs)}
            assert row["metrics"][name].keys() == metrics.keys()
            for metric, value in metrics.items():
                error = abs(value - row["metrics"][name][metric])
                assert error < 1e-12, (key, name, metric, error)
                errors.append(error)
    assert len(errors) == sum(4 * len(r["metrics"]) for r in records)
    return {
        "cases": len(rows),
        "distinct_observations_per_model": len(expected) // len(models),
        "methods": len(models),
        "groups": len(grouped),
        "scalar_fields": len(errors),
        "maximum_arithmetic_error": max(errors),
        "arithmetic_bound": 1e-12,
    }


def main(root, output, candidates=1, checkpoint_sha=None):
    summary_path, case_path = root / "summary.json", root / "per-case.jsonl"
    before = {str(p): sha(p) for p in [summary_path, case_path]}
    summary = json.loads(summary_path.read_text())
    rows = [json.loads(line) for line in case_path.read_text().splitlines()]
    if checkpoint_sha is not None:
        assert candidates == 1 and len(summary["models"]) == 1
        assert summary["models"][0]["sha256"] == checkpoint_sha
    result = {
        "status": "completed-independent-analytic-coverage-and-summary-arithmetic",
        "inputs": before,
        **audit(summary, rows, candidates),
        "driver_sha256": sha(__file__),
        "scope": "Saved scalar rows only: complete declared signal/condition/CFA/draw/method coverage; independent math.fsum/population-std/min/max reconstruction. No model inference, observation regeneration or recomputation of per-case metrics from unavailable full predictions; no blind/training uncertainty or quality promotion.",
    }
    assert all(sha(p) == digest for p, digest in before.items())
    output = writable_path(output)
    if output.exists():
        raise ValueError("Audit output exists; inspect it or choose a fresh path")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    archive = output.with_name(output.stem + "-executed-source.py")
    assert not archive.exists()
    archive.write_bytes(Path(__file__).read_bytes())
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidates", default=1, type=int)
    parser.add_argument("--checkpoint-sha")
    args = parser.parse_args()
    main(args.root, args.output, args.candidates, args.checkpoint_sha)
