"""Apply the already frozen V80/V81 numerical criteria; never promote a model."""

import argparse
import json
import math
from pathlib import Path

from close_camera_supervision_review import read, ref, save

STATUS = "completed-directional-bank-primary-numerical-review-awaiting-native-and-color-review"
PANELS = {"known": ("real", 4), "unseen": ("real", 5), "full427": ("photo", 427)}
WEAK_CARRIERS = ((0.01, 0.1, 8), (0.18, 0.02, 16))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def comparison(statistics, first, second, panel, metric):
    kind, count = PANELS[panel]
    matches = [
        r
        for r in statistics["comparisons"]
        if (r["panel"], r["kind"], r["metric"], r["first"], r["second"])
        == (panel, kind, metric, first["label"], second["label"])
    ]
    require(len(matches) == 1, "Missing or duplicate complete-panel comparison")
    value = matches[0]
    require(value["sources"] == count, "Wrong source/scene count")
    require(
        value["first_checkpoint_sha256"] == first["sha256"]
        and value["second_checkpoint_sha256"] == second["sha256"],
        "Comparison checkpoint differs",
    )
    interval = value["source_bootstrap_95_interval"]
    require(isinstance(interval, list) and len(interval) == 2, "Invalid confidence interval")
    numbers = [
        value[k]
        for k in [
            "mean_first_minus_second",
            "first_source_balanced_mean",
            "second_source_balanced_mean",
        ]
    ] + interval
    require(
        all(type(v) in (int, float) and math.isfinite(v) for v in numbers),
        "Nonfinite or nonnumeric statistic",
    )
    require(interval[0] <= interval[1], "Reversed confidence interval")
    require(
        abs(numbers[1] - numbers[2] - numbers[0]) <= 2e-10, "Mean effect differs from paired means"
    )
    sources = [
        s
        for s in statistics["sources"]
        if s["panel"] == panel
        and s["first"]["label"] == first["label"]
        and s["second"]["label"] == second["label"]
    ]
    require(len(sources) == 1, "Missing or duplicate comparison source")
    source = sources[0]
    for side, checkpoint in [("first", first), ("second", second)]:
        require(
            source[side]["checkpoint_sha256"] == checkpoint["sha256"], "Source checkpoint differs"
        )
    for key in ["report", "report_sha256", "cases", "cases_sha256", "batch_size"]:
        require(
            source["first"][key] == source["second"][key],
            "Parent or control is not in the same fresh panel",
        )
    return value


def evaluate_primary(statistics, control, bank, parent):
    """Pure threshold application after the separate coverage/arithmetic audits."""
    require(statistics["status"] == STATUS, "Primary numerical review incomplete")
    for panel, cases in [("known", 432), ("unseen", 540), ("full427", 74424)]:
        require(
            statistics["audits"][panel]["cases"] == cases
            and statistics["audits"][panel]["methods"] == 6,
            "Primary audit coverage differs",
        )
    arms = []
    for checkpoint in (control, bank):
        rows = {
            "known_CFA": comparison(statistics, checkpoint, parent, "known", "sensor_psnr"),
            "unseen_CFA": comparison(statistics, checkpoint, parent, "unseen", "sensor_psnr"),
            "photo_PSNR": comparison(statistics, checkpoint, parent, "full427", "srgb_psnr"),
            "photo_SSIM": comparison(statistics, checkpoint, parent, "full427", "srgb_ssim"),
            "canonical_camera_linear_PSNR": comparison(
                statistics, checkpoint, parent, "full427", "linear_psnr"
            ),
        }
        gates = {}
        for key in ("known_CFA", "unseen_CFA", "photo_PSNR"):
            gates[key + "_mean_at_least_.05dB"] = rows[key]["mean_first_minus_second"] >= 0.05
            gates[key + "_positive_95pct_lower_bound"] = (
                rows[key]["source_bootstrap_95_interval"][0] > 0
            )
        gates["photo_SSIM_loss_at_most_.0001"] = (
            rows["photo_SSIM"]["mean_first_minus_second"] >= -0.0001
        )
        arms.append(
            {
                "checkpoint": checkpoint,
                "comparisons": rows,
                "gates": gates,
                "all_numerical_criteria_pass": all(gates.values()),
            }
        )
    matched = {
        "known_CFA": comparison(statistics, bank, control, "known", "sensor_psnr"),
        "unseen_CFA": comparison(statistics, bank, control, "unseen", "sensor_psnr"),
        "photo_PSNR": comparison(statistics, bank, control, "full427", "srgb_psnr"),
        "photo_SSIM": comparison(statistics, bank, control, "full427", "srgb_ssim"),
        "canonical_camera_linear_PSNR": comparison(
            statistics, bank, control, "full427", "linear_psnr"
        ),
    }
    matched_gates = {
        "positive_photo_PSNR_95pct_lower_bound": matched["photo_PSNR"][
            "source_bootstrap_95_interval"
        ][0]
        > 0,
        "known_CFA_loss_at_most_.03dB": matched["known_CFA"]["mean_first_minus_second"] >= -0.03,
        "unseen_CFA_loss_at_most_.03dB": matched["unseen_CFA"]["mean_first_minus_second"] >= -0.03,
    }
    return {
        "status": "applied-predeclared-directional-numerical-criteria-manual-review-pending",
        "arms": arms,
        "matched_bank_effect": {
            "comparisons": matched,
            "gates": matched_gates,
            "all_numerical_criteria_pass": all(matched_gates.values()),
        },
        "manual_native_color_detail_highlight_review": "required; not evaluated by this tool",
        "eligible_for_automatic_extension_or_promotion": False,
        "limits": "Threshold application only, using the separate primary coverage/arithmetic review. Does not recompute predictions, metrics or bootstrap intervals. Source/scene intervals do not estimate training-seed uncertainty. Canonical camera-linear scores retain the original target convention. Numerical passes alone cannot authorize full-frame integration, promotion or establish SOTA/100MP10s.",
    }


def evaluate_analytic(summary, rows, control, bank):
    """Audit the complete panel before testing the two frozen signal/noise gates."""
    from audit_analytic_summary import audit

    coverage = audit(summary, rows, candidates=2)
    require(summary["precision"] == "float32", "Analytic review must use float32")
    require(control["sha256"] != bank["sha256"], "Expected two distinct checkpoints")
    models = {}
    for role, checkpoint in (("control", control), ("bank", bank)):
        candidates = [m for m in summary["models"] if m["sha256"] == checkpoint["sha256"]]
        require(len(candidates) == 1, "Missing or duplicate analytic checkpoint binding")
        models[role] = candidates[0]["label"]
    comparisons = []
    for level, contrast, period in WEAK_CARRIERS:
        measurements = {}
        for role, label in models.items():
            chosen = [
                r
                for r in rows
                if r["model"] == label
                and r["condition"] == "iso12800-prior"
                and r["level"] == level
                and r["contrast"] == contrast
                and r["period"] == period
            ]
            flat = [
                r
                for r in rows
                if r["model"] == label
                and r["condition"] == "iso12800-prior"
                and r["kind"] == "flat"
                and r["level"] == level
            ]
            require(len(chosen) == len(flat) == 16, "Fixed carrier/flat coverage differs")
            measurements[role] = {
                "mean_in_phase_gain": math.fsum(r["metrics"]["in_phase_gain"] for r in chosen) / 16,
                "mean_quadrature_gain": math.fsum(r["metrics"]["quadrature_gain"] for r in chosen)
                / 16,
                "mean_noncarrier_rms": math.fsum(r["metrics"]["noncarrier_rms"] for r in chosen)
                / 16,
                "mean_flat_spatial_luma_rms": math.fsum(
                    r["metrics"]["spatial_luma_rms"] for r in flat
                )
                / 16,
            }
            require(all(r["metrics"]["spatial_luma_rms"] >= 0 for r in flat), "Negative flat RMS")
        gain = (
            measurements["bank"]["mean_in_phase_gain"]
            - measurements["control"]["mean_in_phase_gain"]
        )
        original = measurements["control"]["mean_flat_spatial_luma_rms"]
        updated = measurements["bank"]["mean_flat_spatial_luma_rms"]
        comparisons.append(
            {
                "level": level,
                "contrast": contrast,
                "period": period,
                "condition": "iso12800-prior",
                "layout_draw_cases": 16,
                "measurements": measurements,
                "bank_minus_control_gain": gain,
                "flat_rms_ratio": updated / original if original else None,
                "gates": {
                    "signed_gain_improves_at_least_.05": gain >= 0.05,
                    "flat_RMS_at_most_1.25x_control": updated <= 1.25 * original,
                },
            }
        )
    return {
        "coverage_arithmetic_audit": coverage,
        "checkpoint_bindings": {
            role: dict(checkpoint, analytic_label=models[role])
            for role, checkpoint in (("control", control), ("bank", bank))
        },
        "comparisons": comparisons,
        "all_criteria_pass": all(all(r["gates"].values()) for r in comparisons),
        "scope": "Two predeclared carrier/flat contrasts after full1344-case scalar coverage/arithmetic audit. Signed coherent gain and unrelated error remain separate. Descriptive analytic means are not photographic or training-seed uncertainty; manual native review remains required.",
    }


def main(review_path, output):
    from demosaic.safety import writable_path

    plan = read(review_path)
    root = Path(plan["root"])
    boundary_path, statistics_path = (
        root / "training-boundary.json",
        root / "primary-statistics.json",
    )
    boundary, statistics = read(boundary_path), read(statistics_path)
    require(
        boundary["status"]
        == "independently-verified-both-directional-bank-original4000-boundaries",
        "Final boundaries unverified",
    )
    control, bank = boundary["checkpoints"]
    require(
        [c["label"] for c in (control, bank)] == ["V80-original4000", "V81-original4000"]
        and all(c["step"] == 4000 for c in (control, bank)),
        "Wrong study/boundary",
    )
    require(not statistics.get("preflight_only"), "Historical replay is not new model evidence")
    checked = {}
    for source in statistics["sources"]:
        for side in ("first", "second"):
            for key in ("report", "cases"):
                path = source[side][key]
                if path not in checked:
                    checked[path] = ref(path)["sha256"]
                require(checked[path] == source[side][key + "_sha256"], "Source file changed")
    result = evaluate_primary(statistics, control, bank, {**plan["parent"], "label": "V63-parent"})
    analytic_path = Path(plan["outputs"]["analytic"])
    summary_path, rows_path = analytic_path / "summary.json", analytic_path / "per-case.jsonl"
    result["weak_texture_hypothesis"] = evaluate_analytic(
        read(summary_path),
        [json.loads(line) for line in rows_path.read_text().splitlines()],
        control,
        bank,
    )
    result["matched_bank_effect"]["all_numerical_and_analytic_criteria_pass"] = (
        result["matched_bank_effect"]["all_numerical_criteria_pass"]
        and result["weak_texture_hypothesis"]["all_criteria_pass"]
    )
    result["inputs"] = {
        "review_plan": ref(review_path),
        "boundaries": ref(boundary_path),
        "primary_statistics": ref(statistics_path),
        "frozen_criteria": plan["quality_criteria"]["predeclared_snapshot"],
        "driver": ref(__file__),
        "analytic_summary": ref(summary_path),
        "analytic_cases": ref(rows_path),
    }
    require(
        ref(result["inputs"]["frozen_criteria"]["path"]) == result["inputs"]["frozen_criteria"],
        "Frozen criteria changed",
    )
    output = writable_path(output)
    require(not output.exists(), "Choose a new output; keep prior decisions immutable")
    output.parent.mkdir(parents=True, exist_ok=True)
    save(output, result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.review_plan, args.output)
