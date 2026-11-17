"""Paired full-cohort comparison to an independently audited closed baseline."""

import argparse
import sys
from pathlib import Path

from report_local_wave_panel import summarize
from review_neural_nuisance_panel import independent_summary_check

from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def compare(review, baseline_path, output):
    current_path = review / "summary.json"
    current, baseline = read_json(current_path), read_json(baseline_path)
    audits = [read_json(checked(d["independent_audit"])) for d in [current, baseline]]
    assert all(
        d["status"] == "passed-full-cohort-independent-metrics-roles-and-source-statistics"
        for d in audits
    )
    assert all(len(d["rows"]) == 2688 for d in [current, baseline])
    plans = [
        read_json(checked(read_json(checked(d["collection"]))["plan"])) for d in [current, baseline]
    ]
    inputs = []
    for plan in plans:
        rows = {r["id"]: r for r in plan["rows"]}
        assert len(rows) == 1164
        inputs.append(rows)
    assert set(inputs[0]) == set(inputs[1])
    verified = set()
    for name, first in inputs[0].items():
        second = inputs[1][name]
        assert first["noise"] == second["noise"] and first["sample"] == second["sample"]
        for key in ["arrays", "parent"]:
            assert first[key]["sha256"] == second[key]["sha256"]
            for binding in [first[key], second[key]]:
                identity = (binding["path"], binding["sha256"])
                if identity not in verified:
                    checked(binding)
                    verified.add(identity)
    before = {(r["group_index"], r["method"]): r for r in baseline["rows"]}
    methods = ("prior256-NN", "current-NN", "current-analytic")
    joined, maximum_parent = [], 0.0
    metric_names = [k for k, value in current["rows"][0].items() if isinstance(value, float)]
    for row in current["rows"]:
        previous = before[row["group_index"], row["method"]]
        assert all(
            row[k] == previous[k] for k in ["profile", "source", "placement", "pattern", "repeat"]
        )
        if row["method"] == "V143":
            maximum_parent = max(
                maximum_parent, max(abs(row[k] - previous[k]) for k in metric_names)
            )
        elif row["method"] == "local-t2":
            joined.extend([{**previous, "method": methods[0]}, {**row, "method": methods[1]}])
        elif row["method"] == "conditional-local-t2":
            joined.append({**row, "method": methods[2]})
    assert maximum_parent < 1e-10 and len(joined) == 1152
    summary = summarize(
        joined, methods=methods, contrast_pairs=((methods[0], methods[1]), (methods[0], methods[2]))
    )
    independent = independent_summary_check(summary, joined, metric_names)
    assert "torch" not in sys.modules
    write_json(
        output,
        {
            **summary,
            "rows": joined,
            "current_summary": reference(current_path),
            "baseline_summary": reference(baseline_path),
            "script": reference(__file__),
            "paired_input_cases_exact": 1164,
            "maximum_parent_metric_error": maximum_parent,
            "independent_source_summary_check": independent,
            "new_neural_forwards": 0,
            "scope": "All8 sources/all4 CFAs/two repeats/three priors matched by actual archive/parent hashes, noise and sample. Current/baseline full metrics independently audited before joining. Exact paired8-source bootstrap, not camera-population confidence; old baseline predictions not replayed.",
        },
    )
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("review", type=Path)
    parser.add_argument("baseline_summary", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(compare(args.review.resolve(), args.baseline_summary.resolve(), args.output.resolve()))
