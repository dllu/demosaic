"""Apply the already frozen V78/V79 numerical criteria; never promote a model."""

import argparse
import math
from pathlib import Path

from close_camera_supervision_review import read, ref, save

STATUS = "completed-directional-interval-primary-numerical-review-awaiting-native-and-color-review"
PANELS = {"known": ("real", 4), "unseen": ("real", 5), "full427": ("photo", 427)}


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


def evaluate(statistics, control, interval, parent):
    """Pure threshold application after the separate coverage/arithmetic audits."""
    require(statistics["status"] == STATUS, "Primary numerical review incomplete")
    for panel, cases in [("known", 432), ("unseen", 540), ("full427", 74424)]:
        require(
            statistics["audits"][panel]["cases"] == cases
            and statistics["audits"][panel]["methods"] == 6,
            "Primary audit coverage differs",
        )
    arms = []
    for checkpoint in (control, interval):
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
        "known_CFA": comparison(statistics, interval, control, "known", "sensor_psnr"),
        "unseen_CFA": comparison(statistics, interval, control, "unseen", "sensor_psnr"),
        "photo_PSNR": comparison(statistics, interval, control, "full427", "srgb_psnr"),
        "photo_SSIM": comparison(statistics, interval, control, "full427", "srgb_ssim"),
        "canonical_camera_linear_PSNR": comparison(
            statistics, interval, control, "full427", "linear_psnr"
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
        "matched_interval_effect": {
            "comparisons": matched,
            "gates": matched_gates,
            "all_numerical_criteria_pass": all(matched_gates.values()),
        },
        "manual_native_color_detail_highlight_review": "required; not evaluated by this tool",
        "eligible_for_automatic_extension_or_promotion": False,
        "limits": "Threshold application only, using the separate primary coverage/arithmetic review. Does not recompute predictions, metrics or bootstrap intervals. Source/scene intervals do not estimate training-seed uncertainty. Canonical camera-linear scores retain the original target convention. Numerical passes alone cannot authorize full-frame integration, promotion or establish SOTA/100MP10s.",
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
        == "independently-verified-both-directional-interval-original4000-boundaries",
        "Final boundaries unverified",
    )
    control, interval = boundary["checkpoints"]
    require(
        [c["label"] for c in (control, interval)] == ["V78-original4000", "V79-original4000"]
        and all(c["step"] == 4000 for c in (control, interval)),
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
    result = evaluate(statistics, control, interval, {**plan["parent"], "label": "V63-parent"})
    result["inputs"] = {
        "review_plan": ref(review_path),
        "boundaries": ref(boundary_path),
        "primary_statistics": ref(statistics_path),
        "frozen_criteria": plan["quality_criteria"]["predeclared_snapshot"],
        "driver": ref(__file__),
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
