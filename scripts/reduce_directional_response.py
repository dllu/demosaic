"""Compact current-baseline comparisons for V195, retaining source score bindings."""

import math
from collections import defaultdict

from audit_coherent_pair_evidence_trial import validate_summary
from balanced_spatial_metrics import summarize
from directional_trial_protocol import MODES, read, ref
from directional_trial_protocol import TRIAL as ROOT
from review_directional_response import source_guard
from spatial_trial_protocol import save


def condition(row):
    return row.get("present", row.get("variant", row.get("noise")))


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def reduce():
    plan = read(ROOT / "plan-v1.json")
    seal = source_guard(plan)
    assert ref(__file__) == seal["reducer"]
    assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V195-four-endpoint")
    scores = read(ROOT / "scores-v1.json")
    rows = list(scores["rows"])
    sources = []
    for key, method in [
        ("baseline_scores", "V183-coherent-pair-EMA"),
        ("V187_scores", "V187-pooled-wave-EMA"),
    ]:
        binding = plan[key]
        assert ref(binding["path"]) == binding
        old = read(binding["path"])
        previous = read(old["plan"]["path"])
        assert (
            previous["design"] == plan["design"]
            and previous["metrics_sources"] == plan["metrics_sources"]
        )
        selected = [r for r in old["rows"] if r["method"] == method]
        assert len(selected) == 822
        rows += selected
        sources.append({"scores": binding, "method": method})
    methods = ["V183-coherent-pair-EMA", "V187-pooled-wave-EMA"] + [
        m for mode in MODES for m in plan["methods"][mode].values()
    ]
    by_id = {(r["id"], r["method"]): r for r in rows}
    assert len(rows) == len(by_id) == 4932
    summary = summarize(rows)
    decimal_checks = validate_summary(rows, summary)
    groups = defaultdict(list)
    for row in rows:
        groups[row["kind"], condition(row), row.get("cohort"), row["method"]].append(row)
    contrasts = [
        (
            plan["methods"]["directional"][endpoint],
            plan["methods"]["whole"][endpoint],
            "matched-response-" + endpoint,
        )
        for endpoint in ["raw", "EMA"]
    ]
    contrasts += [
        (m, "V187-pooled-wave-EMA", "shared-donor")
        for mode in MODES
        for m in plan["methods"][mode].values()
    ]
    paired = []
    for candidate, baseline, role in contrasts:
        for (kind, state, cohort, method), group in groups.items():
            if method != candidate or kind == "real":
                continue
            for field in group[0]:
                if not field.endswith(("DN16", "gain", "error")):
                    continue
                if not all(
                    numeric(r.get(field)) and numeric(by_id[r["id"], baseline].get(field))
                    for r in group
                ):
                    continue
                values = [
                    {
                        "id": r["id"],
                        "candidate": r[field],
                        "baseline": by_id[r["id"], baseline][field],
                        "difference": r[field] - by_id[r["id"], baseline][field],
                    }
                    for r in group
                ]
                a, b = [
                    math.fsum(v[k] for v in values) / len(values) for k in ["candidate", "baseline"]
                ]
                diffs = [v["difference"] for v in values]
                signed_gain = field.endswith("gain") and not (kind == "mesh" and state is True)
                paired.append(
                    {
                        "candidate": candidate,
                        "baseline": baseline,
                        "role": role,
                        "kind": kind,
                        "condition": state,
                        "cohort": cohort,
                        "field": field,
                        "cases": len(group),
                        "candidate_mean": a,
                        "baseline_mean": b,
                        "mean_difference": math.fsum(diffs) / len(diffs),
                        "relative_mean_percent": None
                        if signed_gain or b <= 0
                        else 100 * (a - b) / b,
                        "positive": sum(d > 0 for d in diffs),
                        "negative": sum(d < 0 for d in diffs),
                        "equal": sum(d == 0 for d in diffs),
                        "values": values,
                    }
                )
    table = []
    dimensions = {(r["kind"], condition(r), r.get("cohort")) for r in rows if r["kind"] != "real"}
    for kind, state, cohort in sorted(dimensions, key=repr):
        summary_group = {
            r["method"]: r
            for r in summary
            if (r["kind"], r["condition"], r["cohort"]) == (kind, state, cohort)
        }
        common = set.intersection(*(set(r) for r in summary_group.values()))
        for field in sorted(common):
            if field.endswith(("DN16", "gain", "error")) and all(
                numeric(summary_group[m][field]) for m in methods
            ):
                table.append(
                    {
                        "kind": kind,
                        "condition": state,
                        "cohort": cohort,
                        "field": field,
                        "cases": summary_group[methods[0]]["cases"],
                        "values": {m: summary_group[m][field] for m in methods},
                    }
                )
    save(
        ROOT / "paired-comparisons-v1.json.gz",
        {
            "status": "completed-V195-six-current-method-compact-comparison",
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "source_scores": sources,
            "methods": methods,
            "metric_rows": len(rows),
            "summary": summary,
            "independent_Decimal_summary_checks": decimal_checks,
            "contrasts": paired,
            "table_rows": table,
            "real_references_scored": False,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "scope": "Two primary same-state directional/whole contrasts, four shared V187 EMA donor contrasts. V183 EMA aggregate context. All historical scores/reports/viewers preserved at their existing paths; no recopy of all historical columns. Signed/absent gains use absolute differences, not misleading relative percentages.",
        },
    )
    print(
        "Reduced",
        len(rows),
        "rows /",
        len(table),
        "table rows /",
        len(paired),
        "paired metric groups",
    )


if __name__ == "__main__":
    reduce()
