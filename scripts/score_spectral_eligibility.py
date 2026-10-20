"""Apply unchanged predeclared V88/V89 criteria, retaining every ADC contrast."""

import argparse
from pathlib import Path

import score_context_eligibility as previous
import score_directional_bank_eligibility as shared
from review_spectral_trial import BOUNDARY
from train_directional_bank_trial import guard, read, ref, save


def spectral_keys(value):
    """Rename only positional role keys; numeric values/model labels stay intact."""
    if isinstance(value, dict):
        return {k.replace("context", "spectral"): spectral_keys(v) for k, v in value.items()}
    if isinstance(value, list):
        return [spectral_keys(v) for v in value]
    return value


def evaluate_primary(statistics, control, spectral, parent):
    return spectral_keys(previous.evaluate_primary(statistics, control, spectral, parent))


def evaluate_analytic(summary, rows, control, spectral):
    return spectral_keys(previous.evaluate_analytic(summary, rows, control, spectral))


def adc_detail(rows, models):
    return spectral_keys(
        previous.adc_detail(rows, {"control": models["control"], "context": models["spectral"]})
    )


def main(plan_path, output):
    from compare_long_commons_scores import rows

    from demosaic.safety import writable_path

    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    boundary = read(root / "training-boundary.json")
    shared.require(
        boundary["status"] == BOUNDARY and boundary["engineering_preflight"] is False,
        "Production spectral training boundary has not been verified",
    )
    control, spectral = boundary["checkpoints"]
    shared.require(
        [c["label"] for c in [control, spectral]] == ["V88-original4000", "V89-original4000"]
        and all(c["step"] == 4000 for c in [control, spectral]),
        "Wrong study/boundary",
    )
    for c in [control, spectral]:
        shared.require(ref(c["path"])["sha256"] == c["sha256"], "Checkpoint changed")
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
        "status": "applied-predeclared-spectral-numerical-criteria-manual-review-pending",
        "plan": ref(plan_path),
        "training_boundary": ref(root / "training-boundary.json"),
        "primary_statistics": ref(root / "primary-statistics.json"),
        "analytic_summary": ref(analytic / "summary.json"),
        "analytic_cases": ref(analytic / "per-case.jsonl"),
        "primary": evaluate_primary(
            statistics, control, spectral, dict(plan["parent"], label="V63-parent")
        ),
        "analytic": evaluate_analytic(
            read(analytic / "summary.json"), rows(analytic / "per-case.jsonl"), control, spectral
        ),
        "manual_native_color_detail_highlight_review": "required; not evaluated by this tool",
        "eligible_for_automatic_extension_or_promotion": False,
    }
    output = writable_path(output)
    shared.require(not output.exists(), "Output exists; preserve prior criteria")
    save(output, result)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    main(a.plan, a.output)
