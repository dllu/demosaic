"""Apply V92 candidate criteria without treating historical V90 as a new arm."""

import argparse
from pathlib import Path

import score_late_rgb_eligibility as previous
from review_late_rgb_only import BOUNDARY, LABELS
from train_directional_bank_trial import guard, read, ref, save


def historical_keys(value):
    if isinstance(value, dict):
        return {
            k.replace("spatial", "head_only").replace("control", "historical"): historical_keys(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [historical_keys(v) for v in value]
    return value


def evaluate_primary(statistics, historical, candidate, parent):
    result = previous.evaluate_primary(statistics, historical, candidate, parent)
    baseline, updated = result["arms"]
    return {
        "status": "applied-head-only-primary-criteria-manual-review-pending",
        "historical_reference_vs_parent": baseline,
        "candidate_vs_parent": updated,
        "candidate_primary_criteria_pass": updated["all_numerical_criteria_pass"],
        "candidate_minus_historical_comparisons": result["matched_spatial_effect"]["comparisons"],
        "eligible_for_automatic_extension_or_promotion": False,
        "limits": "V92 alone must gain at least.05dB with positive lower95% bounds on photo/known/unseen versus V63, with photoSSIM loss at most.0001 and full manual review. V90 primary gates are contextual and are not V92 requirements. Matched effects are descriptive historical contrasts, not independently randomized training-repeat estimates.",
    }


def evaluate_analytic(summary, rows, historical, candidate):
    result = historical_keys(previous.evaluate_analytic(summary, rows, historical, candidate))
    result["comparison_kind"] = "Head-only candidate versus fixed historical global-head reference"
    return result


def main(plan_path, output):
    from compare_long_commons_scores import rows

    from demosaic.safety import writable_path

    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    boundary = read(root / "training-boundary.json")
    previous.shared.require(
        boundary["status"] == BOUNDARY and boundary["engineering_preflight"] is False,
        "Production head-only training boundary has not been verified",
    )
    checkpoints = boundary["checkpoints"]
    previous.shared.require(
        [c["label"] for c in checkpoints] == LABELS and all(c["step"] == 4000 for c in checkpoints),
        "Wrong study/boundary",
    )
    for checkpoint in checkpoints:
        previous.shared.require(
            ref(checkpoint["path"])["sha256"] == checkpoint["sha256"], "Checkpoint changed"
        )
    statistics = read(root / "primary-statistics.json")
    previous.shared.require(
        not statistics.get("preflight_only"), "Historical replay is not V92 quality evidence"
    )
    checked = set()
    for source in statistics["sources"]:
        for side in ["first", "second"]:
            for key in ["report", "cases"]:
                path = source[side][key]
                if path not in checked:
                    previous.shared.require(
                        ref(path)["sha256"] == source[side][key + "_sha256"], "Source changed"
                    )
                    checked.add(path)
    analytic = Path(plan["outputs"]["analytic"])
    result = {
        "status": "applied-head-only-original4000-criteria-manual-review-pending",
        "plan": ref(plan_path),
        "training_boundary": ref(root / "training-boundary.json"),
        "primary_statistics": ref(root / "primary-statistics.json"),
        "analytic_summary": ref(analytic / "summary.json"),
        "analytic_cases": ref(analytic / "per-case.jsonl"),
        "primary": evaluate_primary(
            statistics, *checkpoints, dict(plan["parent"], label="V63-parent")
        ),
        "analytic": evaluate_analytic(
            read(analytic / "summary.json"), rows(analytic / "per-case.jsonl"), *checkpoints
        ),
        "manual_native_color_detail_highlight_review": "required; not evaluated by this tool",
        "eligible_for_automatic_extension_or_promotion": False,
        "comparison": "V92 was chosen after V90 outcomes; historical contrasts do not establish independent confirmation or training-seed uncertainty.",
    }
    output = writable_path(output)
    previous.shared.require(not output.exists(), "Output exists; preserve previous criteria")
    save(output, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.plan, args.output)
