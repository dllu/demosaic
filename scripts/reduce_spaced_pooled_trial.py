"""Compare new readout endpoints with their frozen V183 EMA and all older strengths."""

import argparse
import math
from collections import defaultdict
from pathlib import Path

from audit_coherent_pair_evidence_trial import terminal, validate_summary
from balanced_spatial_metrics import summarize
from spatial_trial_protocol import read, ref, save
from train_spaced_pooled_trial import METHODS, ROOT, guard

V175 = ROOT.parent / "V175-fresh-noise-matching-v2"

EARLIER = ["parent", "V161-EMA", "V169-EMA", "V171-EMA", "V172-EMA", "V173-EMA", "V174-EMA"]
CANDIDATES = list(METHODS.values())
MATCHED_METHODS = [f"V178-{a}-{e}" for a in ["control", "evidence"] for e in ["raw", "EMA"]]
MATCHED_METHODS += [f"V180-local-phase-{e}" for e in ["raw", "EMA"]]
MATCHED_METHODS += [f"V181-flat-spatial-{e}" for e in ["raw", "EMA"]]
MATCHED_METHODS += [f"V183-coherent-pair-{e}" for e in ["raw", "EMA"]]
MATCHED_METHODS += [f"V184-wave-readout-{e}" for e in ["raw", "EMA"]]
MATCHED_METHODS += [f"V185-spatial-context-{e}" for e in ["raw", "EMA"]]
MATCHED_METHODS += [f"V187-pooled-wave-{e}" for e in ["raw", "EMA"]]
PRIMARY_BASELINE = {e: f"V187-pooled-wave-{e}" for e in ["raw", "EMA"]}
ALL_METHODS = EARLIER + ["V175-raw", "V175-EMA"] + MATCHED_METHODS + CANDIDATES
REQUIRED = {
    "mesh": [
        "template_gain",
        "blank_error_RMS_DN16",
        "blank_spatial_RMS_DN16",
        "blank_DC_RMS_DN16",
    ],
    "photo": ["crop_linear_sRGB_luma_band_gain", "crop_relative_band_error"],
    "flat": ["full_spatial_RMS_DN16", "block32_RMS_DN16"],
    # Older parent rows contain crop_DC_RMS_DN16, checked below, without the
    # later duplicate quiet_DC_RMS_DN16 name. Keep the common original field.
    "mixed-quiet": ["quiet_error_RMS_DN16", "quiet_spatial_RMS_DN16"],
}


def condition(row):
    return row.get("present", row.get("variant", row.get("noise")))


def numeric(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and math.isfinite(value)


def source_rows(binding, method, label, plan):
    assert ref(binding["path"]) == binding
    scores = read(binding["path"])
    if "plan" in scores:
        assert ref(scores["plan"]["path"]) == scores["plan"]
        context = read(scores["plan"]["path"])
    else:
        context = scores
    assert context["design"] == plan["design"]
    assert context.get("metrics_sources", context.get("metric_sources")) == plan["metrics_sources"]
    return [dict(row, method=label) for row in scores["rows"] if row["method"] == method]


def earlier_rows(plan):
    previous = read(V175 / "plan-v1.json")
    post = read(V175 / "postprocess-inputs-v1.json")
    assert post["training_plan"] == ref(V175 / "plan-v1.json")
    specifications = [
        (previous["parent_scores"], "parent", "parent"),
        (post["V161_current_metrics"], "V161-EMA", "V161-EMA"),
        (previous["prior_scores"], "balanced-EMA", "V169-EMA"),
        (previous["earlier_flat_scores"], "V171-EMA", "V171-EMA"),
        (post["canonical_V172_scores"], "V172-EMA", "V172-EMA"),
        (previous["earlier_quiet_scores"], "V173-EMA", "V173-EMA"),
        (previous["spread_scores"], "V174-EMA", "V174-EMA"),
    ]
    rows = [
        row
        for binding, method, label in specifications
        for row in source_rows(binding, method, label, plan)
    ]
    return rows, [binding for binding, _, _ in specifications]


def comparisons(rows, methods, case_ids):
    """Keep actual paired values and direction counts without ranking signed gains."""
    maps = {(row["id"], row["method"]): row for row in rows}
    assert len(maps) == len(rows) == len(methods) * len(case_ids)
    for method in methods:
        assert {row["id"] for row in rows if row["method"] == method} == set(case_ids)
    for name in case_ids:
        group = [maps[name, method] for method in methods]
        assert len({(row["kind"], condition(row), row.get("cohort")) for row in group}) == 1
        for row in group:
            if row["kind"] == "real":
                assert row["reference_scored"] is False
                assert not any(
                    key.endswith("error_RMS_DN16") or key == "template_gain" for key in row
                )
            else:
                for field in [
                    "full_error_RMS_DN16",
                    "crop_spatial_RMS_DN16",
                    "crop_DC_RMS_DN16",
                    *REQUIRED[row["kind"]],
                ]:
                    assert numeric(row[field]), (name, method, field)
    summary = summarize(rows)
    checks = validate_summary(rows, summary)
    summary_map = {(r["kind"], r["condition"], r["cohort"], r["method"]): r for r in summary}
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["kind"], condition(row), row.get("cohort"), row["method"]].append(row)
    contrasts = [
        (METHODS[e], PRIMARY_BASELINE[e], "matched-spaced-selection-" + e) for e in ["raw", "EMA"]
    ]
    contrasts += [
        (candidate, baseline, "context")
        for candidate in CANDIDATES
        for baseline in EARLIER + ["V175-raw", "V175-EMA"] + MATCHED_METHODS
        if baseline != PRIMARY_BASELINE[next(e for e, m in METHODS.items() if m == candidate)]
    ]
    paired = []
    for candidate, baseline, role in contrasts:
        for (kind, state, cohort, method), group in grouped.items():
            if method != candidate or kind == "real":
                continue
            for field in group[0]:
                if not field.endswith(("DN16", "gain", "error")):
                    continue
                if not all(
                    numeric(row.get(field)) and numeric(maps[row["id"], baseline].get(field))
                    for row in group
                ):
                    continue
                values = [
                    {
                        "id": row["id"],
                        "candidate": row[field],
                        "baseline": maps[row["id"], baseline][field],
                        "difference": row[field] - maps[row["id"], baseline][field],
                    }
                    for row in group
                ]
                a, b = [
                    math.fsum(float(value[key]) for value in values) / len(values)
                    for key in ["candidate", "baseline"]
                ]
                differences = [value["difference"] for value in values]
                mean_difference = math.fsum(differences) / len(differences)
                assert abs(a - summary_map[kind, state, cohort, candidate][field]) < 1e-10
                assert abs(b - summary_map[kind, state, cohort, baseline][field]) < 1e-10
                assert abs(mean_difference - (a - b)) < 1e-10
                ratio = (
                    None
                    if (kind == "mesh" and state is False and field == "template_gain") or b <= 0
                    else 100 * (a / b - 1)
                )
                paired.append(
                    {
                        "kind": kind,
                        "condition": state,
                        "cohort": cohort,
                        "method": candidate,
                        "baseline": baseline,
                        "comparison_role": role,
                        "field": field,
                        "cases": len(values),
                        "mean_candidate": a,
                        "mean_baseline": b,
                        "mean_difference": mean_difference,
                        "percent_change_of_means": ratio,
                        "decreased": sum(value < 0 for value in differences),
                        "increased": sum(value > 0 for value in differences),
                        "equal": sum(value == 0 for value in differences),
                        "minimum_difference": min(differences),
                        "maximum_difference": max(differences),
                        "pairs": values,
                    }
                )
    return {
        "summary": summary,
        "groups": paired,
        "independent_Decimal_summary_means": checks,
        "paired_mean_and_difference_checks": 3 * len(paired),
        "methods": len(methods),
        "metric_rows": len(rows),
        "contrasts": len(contrasts),
        "primary_endpoint_contrasts": 2,
        "real_references_scored": False,
    }


def table_specs():
    return [
        (
            "Mesh response and blank error",
            [
                (
                    f"{'Present' if present else 'Absent'} {label}",
                    "mesh",
                    present,
                    None,
                    field,
                    digits,
                )
                for present in [True, False]
                for label, field, digits in [
                    ("full RMS", "full_error_RMS_DN16", 6),
                    ("signed template gain", "template_gain", 8),
                    ("blank RMS", "blank_error_RMS_DN16", 6),
                    ("blank spatial RMS", "blank_spatial_RMS_DN16", 6),
                    ("blank DC RMS", "blank_DC_RMS_DN16", 6),
                ]
            ],
        ),
        (
            "Quiet fields beside detail",
            [
                (f"{prior} {label}", "mixed-quiet", prior, None, field, 6)
                for prior in ["iso6400-prior", "iso12800-prior"]
                for label, field in [
                    ("whole RMS", "full_error_RMS_DN16"),
                    ("quiet RMS", "quiet_error_RMS_DN16"),
                    ("quiet spatial RMS", "quiet_spatial_RMS_DN16"),
                    ("quiet DC RMS", "crop_DC_RMS_DN16"),
                ]
            ],
        ),
        (
            "Standalone 512-pixel flats",
            [
                (f"{prior} {label}", "flat", prior, "fresh-flat512", field, 6)
                for prior in ["iso6400-prior", "iso12800-prior"]
                for label, field in [
                    ("full RMS", "full_error_RMS_DN16"),
                    ("spatial RMS", "full_spatial_RMS_DN16"),
                    ("coarse32 RMS", "block32_RMS_DN16"),
                ]
            ],
        ),
        (
            "Natural photographic detail",
            [
                (f"{cohort}/{variant} {label}", "photo", variant, cohort, field, 6)
                for cohort in ["retained512", "organic384"]
                for variant in ["photo-faint", "photo-dark"]
                for label, field in [
                    ("full RMS", "full_error_RMS_DN16"),
                    ("band response", "crop_linear_sRGB_luma_band_gain"),
                    ("band error", "crop_relative_band_error"),
                ]
            ],
        ),
        (
            "ADC controls",
            [
                (f"Photo {label}", "photo", "adc-only", "adc-photo256", field, 6)
                for label, field in [
                    ("full RMS", "full_error_RMS_DN16"),
                    ("band error", "crop_relative_band_error"),
                ]
            ]
            + [
                (f"{cohort} {label}", "flat", "adc-only", cohort, field, 6)
                for cohort in ["fresh-flat512", "adc-sloped512"]
                for label, field in [
                    ("full RMS", "full_error_RMS_DN16"),
                    ("coarse32 RMS", "block32_RMS_DN16"),
                ]
            ],
        ),
    ]


def tables(summary, *, fixture=False):
    lookup = {(row["kind"], row["condition"], row["cohort"], row["method"]): row for row in summary}
    title = (
        "CPU COMPARISON FIXTURE — reused baseline values, no V189 quality"
        if fixture
        else "Pooled-selection wave readout and retained flat/local/global/control comparison tables"
    )
    lines = [
        "# " + title,
        "",
        "RMS values are camera-RGB DN16. Signed gain 1 is exact constructed amplitude. Real ISO100 references are unscored. This reused development suite is not blind validation.",
        "",
    ]
    cells = []
    for section, methods in [
        (
            "New readout and retained local/global/control",
            MATCHED_METHODS + CANDIDATES,
        ),
        ("Earlier strengths and both endpoints", ALL_METHODS),
    ]:
        lines += ["## " + section, ""]
        for heading, specifications in table_specs():
            lines += [
                "### " + heading,
                "",
                "| Metric | " + " | ".join(methods) + " |",
                "| --- | " + " | ".join(["---:"] * len(methods)) + " |",
            ]
            for label, kind, state, cohort, field, digits in specifications:
                values = []
                for method in methods:
                    value = lookup[kind, state, cohort, method][field]
                    rendered = f"{value:.{digits}f}"
                    cells.append(
                        {
                            "section": section,
                            "kind": kind,
                            "condition": state,
                            "cohort": cohort,
                            "field": field,
                            "method": method,
                            "value": value,
                            "rendered": rendered,
                            "digits": digits,
                        }
                    )
                    values.append(rendered)
                lines.append("| " + label + " | " + " | ".join(values) + " |")
            lines.append("")
    assert len(cells) == 1890
    return "\n".join(lines), cells


def reduce(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    seal = read(root / "reduction-source-v1.json")
    assert seal["reducer"] == ref(__file__) and seal["plan"] == ref(root / "plan-v1.json")
    scores = terminal(root / "scores-v1.json")
    assert scores["owner"] == read(root / "review-launch-v1.json")["owner"]
    assert scores["plan"] == ref(root / "plan-v1.json")
    training = terminal(root / "wave-train-result-v1.json")
    assert training["owner"] == read(root / "wave-train-launch-v1.json")["owner"]
    for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
        audit = read(root / name)
        assert audit["status"].startswith("pass-") and audit["plan"] == ref(root / "plan-v1.json")
    assert read(root / "quality-audit-v1.json")["scores"] == ref(root / "scores-v1.json")
    rows, sources = earlier_rows(plan)
    context = read(plan["baseline_plan"]["path"])
    historical = [
        context[k] for k in ["V175_scores", "matched_scores", "local_scores", "flat_spatial_scores"]
    ] + [
        plan["baseline_scores"],
        ref(ROOT.parent / "V184-wave-readout-trial-v1/scores-v1.json"),
        plan["V185_scores"],
        plan["V187_scores"],
    ]
    for binding in historical:
        old = terminal(binding["path"])
        assert ref(binding["path"]) == binding
        for method in dict.fromkeys(row["method"] for row in old["rows"]):
            assert method in ALL_METHODS
            rows += source_rows(binding, method, method, plan)
    rows += scores["rows"]
    design = read(plan["design"]["path"])["observations"]
    assert len(design) == 822
    result = comparisons(rows, ALL_METHODS, [case["id"] for case in design])
    text, cells = tables(result["summary"])
    result.update(
        status="completed-twentyseven-method-wave-readout-increment-and-context-reductions-awaiting-native-conclusion",
        plan=ref(root / "plan-v1.json"),
        scores=ref(root / "scores-v1.json"),
        earlier_score_sources=sources + historical,
        table_cells=cells,
        new_neural_forwards=0,
        new_sensor_draws=0,
        source=dict(ref(__file__), text=Path(__file__).read_text()),
        scope="Two primary matched900headupdate contrasts raw/raw andEMA/EMA versusV187,plus48contextualcontrasts. Same508params,193state,frozenV183EMA,freshinitialhead,data/nine losses/AdamEMAschedules. Only pooled suppression radius changes1toceil(maxpackedaxis/65). All27methods/22194rows/50contrasts/1890cells retainolderstrengths withoutinference. Realrefsunscored,signedabsentgainsnorelativepercent,reuseddevelopmentsuite. Actualnativeviewingrequired; no safety/generalization claim frommetricsalone.",
    )
    save(root / "paired-comparisons-v1.json.gz", result)
    with (root / "comparison-tables-v1.md").open("x") as stream:
        stream.write(text + "\n")
    print("Reduced27methods/22194rows/50contrasts/1890tablecells;no new inference", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    reduce(parser.parse_args().root)
