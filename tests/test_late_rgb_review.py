"""Refuse premature quality and retain the fixed matched SSIM/ADC requirements."""

import itertools
import json

import pytest
import review_late_rgb_trial as review
import score_late_rgb_eligibility as score


@pytest.mark.parametrize(
    "stage",
    [
        None,
        "known",
        "unseen",
        "full427",
        "statistics",
        "sensitivity",
        "gfx",
        "analytic",
        "hue",
        "highlights",
    ],
)
def test_engineering_endpoints_cannot_enter_any_quality_stage(tmp_path, stage):
    plan = tmp_path / "plan.json"
    plan.write_text('{"engineering_preflight":true}')
    with pytest.raises(ValueError, match="cannot produce quality evidence"):
        review.run(plan, stage)


@pytest.mark.parametrize(
    "status",
    [
        "running-source-frozen-late-rgb-arm",
        "waiting-for-late-rgb-resources",
        "failed-late-rgb-trial-no-automatic-retry",
        review.ENGINEERING_TERMINAL,
    ],
)
def test_incomplete_or_engineering_status_is_not_production(tmp_path, status):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"status": status}))
    with pytest.raises(RuntimeError, match="Both fixed late RGB budgets"):
        review.require_completed({"training_status": str(path)})


def test_terminal_file_cannot_override_a_live_owner(tmp_path, monkeypatch):
    owner = {"pid": 12, "created": 34}
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"status": review.TERMINAL, "controller": owner, "child": owner}))
    monkeypatch.setattr(review.panels, "alive", lambda _: True)
    with pytest.raises(AssertionError):
        review.require_completed({"training_status": str(path), "training_owner": owner})


def primary_statistics(ssim_delta):
    control = {"label": "V90-original4000", "sha256": "a" * 64}
    spatial = {"label": "V91-original4000", "sha256": "b" * 64}
    parent = {"label": "V63-parent", "sha256": "c" * 64}
    specs = [
        ("known", "real", 4, "sensor_psnr"),
        ("unseen", "real", 5, "sensor_psnr"),
        ("full427", "photo", 427, "srgb_psnr"),
        ("full427", "photo", 427, "srgb_ssim"),
        ("full427", "photo", 427, "linear_psnr"),
    ]
    result = {
        "status": score.shared.STATUS,
        "audits": {
            panel: {"cases": count, "methods": 6}
            for panel, count in [("known", 432), ("unseen", 540), ("full427", 74424)]
        },
        "sources": [],
        "comparisons": [],
    }
    for first, second in [(control, parent), (spatial, parent), (spatial, control)]:
        for panel, kind, count, metric in specs:
            is_ssim = metric == "srgb_ssim"
            values = {
                parent["label"]: 0.9 if is_ssim else 30.0,
                control["label"]: 0.91 if is_ssim else 30.1,
                spatial["label"]: 0.91 + ssim_delta if is_ssim else 30.2,
            }
            delta = values[first["label"]] - values[second["label"]]
            if is_ssim and first == spatial and second == control:
                delta = ssim_delta
            result["comparisons"].append(
                {
                    "panel": panel,
                    "kind": kind,
                    "metric": metric,
                    "first": first["label"],
                    "second": second["label"],
                    "sources": count,
                    "first_checkpoint_sha256": first["sha256"],
                    "second_checkpoint_sha256": second["sha256"],
                    "mean_first_minus_second": delta,
                    "first_source_balanced_mean": values[first["label"]],
                    "second_source_balanced_mean": values[second["label"]],
                    "source_bootstrap_95_interval": [delta - 0.00001, delta + 0.00001],
                }
            )
        for panel in ["known", "unseen", "full427"]:
            sides = {}
            for name, item in [("first", first), ("second", second)]:
                sides[name] = {
                    "label": item["label"],
                    "checkpoint_sha256": item["sha256"],
                    "report": panel + "/summary.json",
                    "report_sha256": "d" * 64,
                    "cases": panel + "/cases.jsonl",
                    "cases_sha256": "e" * 64,
                    "batch_size": 2,
                }
            result["sources"].append({"panel": panel, **sides})
    return result, control, spatial, parent


@pytest.mark.parametrize(
    ("ssim_delta", "passes"), [(-0.00009, True), (-0.0001, True), (-0.00011, False)]
)
def test_matched_SSIM_loss_limit_is_enforced_even_when_other_gates_pass(ssim_delta, passes):
    result = score.evaluate_primary(*primary_statistics(ssim_delta))
    assert all(arm["all_numerical_criteria_pass"] for arm in result["arms"])
    matched = result["matched_spatial_effect"]
    gate = "photo_SSIM_loss_at_most_.0001"
    assert all(v for k, v in matched["gates"].items() if k != gate)
    assert matched["gates"][gate] is passes
    assert matched["all_numerical_criteria_pass"] is passes
    assert result["eligible_for_automatic_extension_or_promotion"] is False


def adc_rows():
    return [
        {
            "model": model,
            "kind": "carrier",
            "condition": "adc-only",
            "level": level,
            "contrast": contrast,
            "period": period,
            "pattern": pattern,
            "draw": draw,
            "metrics": {"in_phase_gain": 0.5},
        }
        for model, level, contrast, period, pattern, draw in itertools.product(
            ["global", "spatial"],
            [0.01, 0.18],
            [0.02, 0.1],
            [4, 8, 16],
            ["RGGB", "BGGR", "GRBG", "GBRG"],
            range(4),
        )
    ]


def test_ADC_group_mean_cannot_hide_one_failed_layout_draw():
    rows = adc_rows()
    rows[-1]["metrics"]["in_phase_gain"] = 0.44
    result = score.adc_detail(rows, {"control": "global", "spatial": "spatial"})
    assert len(result["cases"]) == 192 and len(result["group_means"]) == 12
    assert all(row["spatial_minus_control_gain"] > -0.05 for row in result["group_means"])
    assert result["no_ADC_case_loses_more_than_.05"] is False
    assert sum(not row["gain_loss_at_most_.05"] for row in result["cases"]) == 1


@pytest.mark.parametrize("mutation", ["missing", "duplicate"])
def test_ADC_coverage_defects_are_refused(mutation):
    rows = adc_rows()
    if mutation == "missing":
        rows.pop()
    else:
        rows[-1] = rows[-2]
    with pytest.raises(ValueError, match="Incomplete or duplicate ADC cases"):
        score.adc_detail(rows, {"control": "global", "spatial": "spatial"})
