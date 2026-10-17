"""Independently rebuild descriptive hue-grid groups after the case-array audit."""

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path

from prepare_color_grid import sha, validate

from demosaic.safety import writable_path


def percentile(values, fraction):
    values = sorted(values)
    index = (len(values) - 1) * fraction
    lo = math.floor(index)
    hi = math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def descriptive(values):
    return {
        "mean": math.fsum(values) / len(values),
        "median": percentile(values, 0.5),
        "p95": percentile(values, 0.95),
        "maximum": max(values),
    }


def rebuild(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[
            r["model_index"], r["condition"], r["source"]["saturation"], r["source"]["peak"]
        ].append(r["metrics"])
    result = {}
    for key, values in groups.items():
        items = {
            "max_abs_channel_mean_error": [
                max(abs(x) for x in r["camera_RGB_mean_error"]) for r in values
            ],
            "camera_RGB_RMSE": [math.sqrt(r["camera_RGB_MSE"]) for r in values],
            "centered_camera_RGB_RMS": [r["spatially_centered_camera_RGB_RMS"] for r in values],
        }
        result[key] = {
            "cases": len(values),
            "descriptive_metrics": {name: descriptive(v) for name, v in items.items()},
        }
    return result


def main(report_path, case_audit, output):
    report = json.loads(Path(report_path).read_text())
    audit = json.loads(Path(case_audit).read_text())
    assert audit["input_report_sha256"] == sha(report_path)
    plan = json.loads(Path(report["plan"]).read_text())
    assert sha(report["plan"]) == report["plan_sha256"]
    original = json.loads(Path(plan["inputs"]).read_text())
    assert sha(plan["inputs"]) == plan["input_plan_sha256"]
    validate(original)
    models = len(report["checkpoints"])
    assert audit["observations"] == 1176 and audit["float_predictions"] == 1176 * models
    seen = set()
    for r in report["results"]:
        key = r["model_index"], r["case"]
        assert key not in seen and 0 <= key[0] < models
        seen.add(key)
        c = original["cases"][r["case"]]
        assert (
            r["palette"] == c["palette"]
            and r["source"] == c["source"]
            and r["condition"] == c["condition"]["name"]
            and r["pattern"] == c["pattern"]
        )
    assert seen == {(m, c) for m in range(models) for c in range(1176)}
    actual = {
        (r["model_index"], r["condition"], r["saturation"], r["peak"]): r
        for r in report["group_summary"]
    }
    expected = rebuild(report["results"])
    assert (
        len(actual) == len(report["group_summary"]) == len(expected) == 18 * models
        and actual.keys() == expected.keys()
    )
    differences = []
    for key, r in expected.items():
        assert r["cases"] == actual[key]["cases"] == (4 if key[2] == 0 else 96)
        assert r["descriptive_metrics"].keys() == actual[key]["descriptive_metrics"].keys()
        for name, values in r["descriptive_metrics"].items():
            assert values.keys() == actual[key]["descriptive_metrics"][name].keys()
            for metric, value in values.items():
                delta = abs(value - actual[key]["descriptive_metrics"][name][metric])
                assert delta < 2e-14, (key, name, metric, delta)
                differences.append(delta)
    output = writable_path(output)
    if output.exists():
        raise ValueError("Summary audit exists; choose a new output")
    result = {
        "status": "completed-independent-descriptive-color-grid-summary-audit",
        "report": str(report_path),
        "report_sha256": sha(report_path),
        "case_audit": str(case_audit),
        "case_audit_sha256": sha(case_audit),
        "all_source_case_labels_and_model_coverage_exact": True,
        "groups": len(expected),
        "descriptive_scalar_fields": len(differences),
        "maximum_independent_scalar_difference": max(differences),
        "driver_sha256": sha(__file__),
        "scope": "Math.fsum and explicit sorted linear percentiles, separate from NumPy aggregation. Case prediction arithmetic supplied by the pinned preceding audit. These quantiles describe the fixed grid, not confidence intervals or real-photo quality.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--case-audit", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    main(a.report, a.case_audit, a.output)
