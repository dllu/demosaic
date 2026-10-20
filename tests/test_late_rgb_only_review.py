"""Keep head-only quality separate from engineering and historical-arm success."""

import json

import pytest
import review_late_rgb_only as review
import score_late_rgb_only_eligibility as score
import torch
from prepare_late_rgb_only_report_assets import main as package
from test_late_rgb_review import primary_statistics


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
def test_engineering_endpoints_cannot_enter_quality(tmp_path, stage):
    path = tmp_path / "plan.json"
    path.write_text('{"engineering_preflight":true}')
    with pytest.raises(ValueError, match="cannot produce quality evidence"):
        review.run(path, stage)


@pytest.mark.parametrize(
    "status",
    [
        "running-source-frozen-head-only-worker",
        "waiting-for-head-only-resources",
        "failed-head-only-study-preserved-no-automatic-retry",
        review.ENGINEERING_TERMINAL,
    ],
)
def test_incomplete_or_engineering_status_cannot_be_production(tmp_path, status):
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"status": status}))
    with pytest.raises(RuntimeError, match="must complete"):
        review.require_completed({"training_status": str(path)})


def test_terminal_record_cannot_override_live_owner(tmp_path, monkeypatch):
    owner = {"pid": 123, "created": 456}
    path = tmp_path / "status.json"
    path.write_text(json.dumps({"status": review.TERMINAL, "controller": owner, "child": owner}))
    monkeypatch.setattr(review.panels, "alive", lambda _: True)
    with pytest.raises(AssertionError):
        review.require_completed({"training_status": str(path), "training_owner": owner})


@pytest.mark.parametrize("delta,passes", [(-0.00009, True), (-0.0001, True), (-0.00011, False)])
def test_candidate_own_SSIM_limit_is_enforced(delta, passes):
    statistics, historical, candidate, parent = primary_statistics(0)
    row = next(
        r
        for r in statistics["comparisons"]
        if r["first"] == candidate["label"]
        and r["second"] == parent["label"]
        and r["metric"] == "srgb_ssim"
    )
    row.update(
        mean_first_minus_second=delta,
        first_source_balanced_mean=0.9 + delta,
        second_source_balanced_mean=0.9,
        source_bootstrap_95_interval=[delta - 0.00001, delta + 0.00001],
    )
    result = score.evaluate_primary(statistics, historical, candidate, parent)
    assert result["candidate_vs_parent"]["gates"]["photo_SSIM_loss_at_most_.0001"] is passes
    assert result["candidate_primary_criteria_pass"] is passes
    assert result["eligible_for_automatic_extension_or_promotion"] is False


def test_historical_arm_failure_does_not_veto_qualified_candidate():
    statistics, historical, candidate, parent = primary_statistics(0)
    for row in statistics["comparisons"]:
        if row["metric"] != "srgb_ssim" and row["second"] == historical["label"]:
            row["second_source_balanced_mean"] = 30.01
            delta = row["first_source_balanced_mean"] - 30.01
            row.update(
                mean_first_minus_second=delta,
                source_bootstrap_95_interval=[delta - 0.00001, delta + 0.00001],
            )
        elif row["metric"] != "srgb_ssim" and row["first"] == historical["label"]:
            row.update(
                first_source_balanced_mean=30.01,
                mean_first_minus_second=0.01,
                source_bootstrap_95_interval=[0.00999, 0.01001],
            )
    result = score.evaluate_primary(statistics, historical, candidate, parent)
    assert result["historical_reference_vs_parent"]["all_numerical_criteria_pass"] is False
    assert result["candidate_primary_criteria_pass"] is True


def test_historical_success_cannot_hide_candidate_camera_failure():
    statistics, historical, candidate, parent = primary_statistics(0)
    row = next(
        r
        for r in statistics["comparisons"]
        if r["first"] == candidate["label"]
        and r["second"] == parent["label"]
        and r["panel"] == "known"
    )
    row.update(
        first_source_balanced_mean=29.99,
        mean_first_minus_second=-0.01,
        source_bootstrap_95_interval=[-0.01001, -0.00999],
    )
    result = score.evaluate_primary(statistics, historical, candidate, parent)
    assert result["historical_reference_vs_parent"]["all_numerical_criteria_pass"] is True
    assert result["candidate_primary_criteria_pass"] is False


def test_engineering_states_cannot_enter_report_package(tmp_path, monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    path = tmp_path / "plan.json"
    path.write_text('{"engineering_preflight":true}')
    with pytest.raises(ValueError, match="cannot produce quality evidence"):
        package(path, tmp_path / "forbidden")
    assert not (tmp_path / "forbidden").exists()


def test_protected_byte_comparison_keeps_signed_zero_distinct():
    assert review.same_bits(torch.tensor([-0.0]), torch.tensor([-0.0]))
    assert not review.same_bits(torch.tensor([-0.0]), torch.tensor([0.0]))
