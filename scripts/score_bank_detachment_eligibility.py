"""Apply the frozen V82/V83 requirements, including the ADC-detail contrast."""

import argparse
import math
from pathlib import Path

import score_directional_bank_eligibility as previous
from train_directional_interval_trial import read, ref, save


def evaluate_primary(statistics, connected, detached, parent):
    result = previous.evaluate_primary(statistics, connected, detached, parent)
    result["matched_detachment_effect"] = result.pop("matched_bank_effect")
    return result


def evaluate_analytic(summary, rows, connected, detached):
    # Reuse the complete 1344-row coverage/arithmetic audit and retain both
    # original high-noise/flat requirements before adding the ADC criterion.
    weak = previous.evaluate_analytic(summary, rows, connected, detached)
    for item in weak["comparisons"]:
        item["measurements"] = {
            "connected": item["measurements"]["control"],
            "detached": item["measurements"]["bank"],
        }
        item["detached_minus_connected_gain"] = item.pop("bank_minus_control_gain")
        item["gates"]["flat_RMS_at_most_1.25x_connected"] = item["gates"].pop(
            "flat_RMS_at_most_1.25x_control"
        )
    weak["checkpoint_bindings"] = {
        "connected": weak["checkpoint_bindings"]["control"],
        "detached": weak["checkpoint_bindings"]["bank"],
    }
    measurements = {}
    for role, checkpoint in [("connected", connected), ("detached", detached)]:
        label = weak["checkpoint_bindings"][role]["analytic_label"]
        selected = [
            r
            for r in rows
            if (r["model"], r["kind"], r["condition"], r["level"], r["contrast"], r["period"])
            == (label, "carrier", "adc-only", 0.01, 0.02, 4)
        ]
        previous.require(len(selected) == 16, "ADC-detail coverage differs")
        measurements[role] = {
            name: math.fsum(r["metrics"][name] for r in selected) / 16
            for name in ("in_phase_gain", "quadrature_gain", "noncarrier_rms", "linear_srgb_rmse")
        }
    delta = measurements["detached"]["in_phase_gain"] - measurements["connected"]["in_phase_gain"]
    adc = {
        "level": 0.01,
        "contrast": 0.02,
        "period": 4,
        "condition": "adc-only",
        "layout_draw_cases": 16,
        "measurements": measurements,
        "detached_minus_connected_gain": delta,
        "signed_gain_improves_at_least_.05": delta >= 0.05,
    }
    return {
        "high_noise_weak_carriers": weak,
        "ADC_detail": adc,
        "all_criteria_pass": weak["all_criteria_pass"] and adc["signed_gain_improves_at_least_.05"],
        "scope": "Unchanged high-noise/flat gates plus the predeclared ADC signed-gain contrast, after full scalar coverage/arithmetic audit. Descriptive fixtures only; no scene/training confidence or automatic promotion.",
    }


def main(plan_path, output):
    from compare_long_commons_scores import rows

    from demosaic.safety import writable_path

    plan = read(plan_path)
    root = Path(plan["root"])
    boundary = read(root / "training-boundary.json")
    previous.require(
        boundary["status"] == "independently-verified-both-directional-bank-original4000-boundaries"
        and boundary["engineering_preflight"] is False,
        "Production training boundary has not been verified",
    )
    connected, detached = boundary["checkpoints"]
    previous.require(
        [c["label"] for c in [connected, detached]] == ["V82-original4000", "V83-original4000"],
        "Unexpected study checkpoints",
    )
    for checkpoint in [connected, detached]:
        previous.require(
            ref(checkpoint["path"])["sha256"] == checkpoint["sha256"], "Checkpoint changed"
        )
    primary = read(root / "primary-statistics.json")
    analytic_root = Path(plan["outputs"]["analytic"])
    analytic = read(analytic_root / "summary.json")
    result = {
        "status": "applied-predeclared-bank-detachment-numerical-criteria-manual-review-pending",
        "plan": ref(plan_path),
        "training_boundary": ref(root / "training-boundary.json"),
        "primary_statistics": ref(root / "primary-statistics.json"),
        "analytic_summary": ref(analytic_root / "summary.json"),
        "analytic_cases": ref(analytic_root / "per-case.jsonl"),
        "primary": evaluate_primary(
            primary, connected, detached, dict(plan["parent"], label="V63-parent")
        ),
        "analytic": evaluate_analytic(
            analytic, rows(analytic_root / "per-case.jsonl"), connected, detached
        ),
        "manual_native_color_detail_highlight_review": "required; not evaluated by this tool",
        "eligible_for_automatic_extension_or_promotion": False,
    }
    output = writable_path(output)
    if output.exists():
        raise ValueError("Output exists; preserve previous criteria applications")
    save(output, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.plan, args.output)
