"""Apply the predeclared context criteria without promoting a model."""

import argparse
import math
from collections import defaultdict
from pathlib import Path

import score_directional_bank_eligibility as shared
from review_context_trial import BOUNDARY
from train_directional_interval_trial import guard, read, ref, save


def evaluate_primary(statistics, control, context, parent):
    result = shared.evaluate_primary(statistics, control, context, parent)
    result["matched_context_effect"] = result.pop("matched_bank_effect")
    return result


def adc_detail(rows, models):
    cases = {}
    for role, label in models.items():
        selected = [
            r
            for r in rows
            if r["model"] == label and r["kind"] == "carrier" and r["condition"] == "adc-only"
        ]
        keyed = {
            (r["level"], r["contrast"], r["period"], r["pattern"], r["draw"]): r for r in selected
        }
        shared.require(len(keyed) == len(selected) == 192, "Incomplete or duplicate ADC cases")
        cases[role] = keyed
    shared.require(cases["control"].keys() == cases["context"].keys(), "ADC cases differ")
    groups, comparisons = defaultdict(list), []
    for key in sorted(cases["control"]):
        first = cases["control"][key]["metrics"]["in_phase_gain"]
        second = cases["context"][key]["metrics"]["in_phase_gain"]
        shared.require(math.isfinite(first) and math.isfinite(second), "Nonfinite ADC gain")
        delta = second - first
        groups[key[:3]].append(delta)
        comparisons.append(
            {
                "case": list(key),
                "context_minus_control_gain": delta,
                "gain_loss_at_most_.05": delta >= -0.05,
            }
        )
    shared.require(
        len(groups) == 12 and all(len(v) == 16 for v in groups.values()),
        "ADC layout/draw coverage differs",
    )
    return {
        "cases": comparisons,
        "group_means": [
            {"level_contrast_period": list(k), "context_minus_control_gain": math.fsum(v) / 16}
            for k, v in sorted(groups.items())
        ],
        "no_ADC_case_loses_more_than_.05": all(c["gain_loss_at_most_.05"] for c in comparisons),
    }


def evaluate_analytic(summary, rows, control, context):
    weak = shared.evaluate_analytic(summary, rows, control, context)
    for comparison in weak["comparisons"]:
        comparison["measurements"]["context"] = comparison["measurements"].pop("bank")
        comparison["context_minus_control_gain"] = comparison.pop("bank_minus_control_gain")
    weak["checkpoint_bindings"]["context"] = weak["checkpoint_bindings"].pop("bank")
    models = {role: item["analytic_label"] for role, item in weak["checkpoint_bindings"].items()}
    adc = adc_detail(rows, models)
    return {
        "high_noise_weak_carriers": weak,
        "ADC_detail": adc,
        "weak_detail_claim_criteria_pass": weak["all_criteria_pass"]
        and adc["no_ADC_case_loses_more_than_.05"],
        "scope": "Full analytic coverage/arithmetic first. Two high-noise gain/flat contrasts and all192 ADC layout/draw cases; retain12 group means. These descriptive fixtures do not establish photo quality or training-seed uncertainty.",
    }


def main(plan_path, output):
    from compare_long_commons_scores import rows

    from demosaic.safety import writable_path

    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    boundary = read(root / "training-boundary.json")
    shared.require(
        boundary["status"] == BOUNDARY and boundary["engineering_preflight"] is False,
        "Production context training boundary has not been verified",
    )
    control, context = boundary["checkpoints"]
    shared.require(
        [c["label"] for c in [control, context]] == ["V86-original4000", "V87-original4000"]
        and all(c["step"] == 4000 for c in [control, context]),
        "Wrong study/boundary",
    )
    for checkpoint in [control, context]:
        shared.require(
            ref(checkpoint["path"])["sha256"] == checkpoint["sha256"], "Checkpoint changed"
        )
    statistics = read(root / "primary-statistics.json")
    shared.require(
        not statistics.get("preflight_only"), "Historical replay is not production evidence"
    )
    checked = set()
    for source in statistics["sources"]:
        for side in ["first", "second"]:
            for key in ["report", "cases"]:
                path = source[side][key]
                if path not in checked:
                    shared.require(
                        ref(path)["sha256"] == source[side][key + "_sha256"], "Source changed"
                    )
                    checked.add(path)
    analytic = Path(plan["outputs"]["analytic"])
    result = {
        "status": "applied-predeclared-context-numerical-criteria-manual-review-pending",
        "plan": ref(plan_path),
        "training_boundary": ref(root / "training-boundary.json"),
        "primary_statistics": ref(root / "primary-statistics.json"),
        "analytic_summary": ref(analytic / "summary.json"),
        "analytic_cases": ref(analytic / "per-case.jsonl"),
        "primary": evaluate_primary(
            statistics, control, context, dict(plan["parent"], label="V63-parent")
        ),
        "analytic": evaluate_analytic(
            read(analytic / "summary.json"), rows(analytic / "per-case.jsonl"), control, context
        ),
        "manual_native_color_detail_highlight_review": "required; not evaluated by this tool",
        "eligible_for_automatic_extension_or_promotion": False,
    }
    output = writable_path(output)
    shared.require(not output.exists(), "Output exists; preserve previous criteria applications")
    save(output, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.plan, args.output)
