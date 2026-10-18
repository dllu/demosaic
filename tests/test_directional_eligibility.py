"""Reject rounded gains, zero CI bounds, wrong references and incomplete panels."""

import copy
import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def gate(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").absolute()))
    spec = importlib.util.spec_from_file_location(
        "directional_gate", Path("scripts/score_directional_eligibility.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def fixture(gate):
    control, candidate, parent = [
        {"label": name, "sha256": sha * 64}
        for name, sha in [("control", "a"), ("interval", "b"), ("parent", "c")]
    ]
    stats = {
        "status": gate.STATUS,
        "audits": {
            p: {"cases": n, "methods": 6}
            for p, n in [("known", 432), ("unseen", 540), ("full427", 74424)]
        },
        "comparisons": [],
        "sources": [],
    }
    for first, second in [(control, parent), (candidate, parent), (candidate, control)]:
        for panel, (kind, sources) in gate.PANELS.items():
            descriptor = lambda c, panel=panel: {
                "label": c["label"],
                "checkpoint_sha256": c["sha256"],
                "report": panel + "/summary.json",
                "report_sha256": "d" * 64,
                "cases": panel + "/cases.jsonl",
                "cases_sha256": "e" * 64,
                "batch_size": 2,
            }
            stats["sources"].append(
                {"panel": panel, "first": descriptor(first), "second": descriptor(second)}
            )
            for metric in (
                ["sensor_psnr"] if panel != "full427" else ["srgb_psnr", "srgb_ssim", "linear_psnr"]
            ):
                gains = {"control": 0.05, "interval": 0.1, "parent": 0.0}
                if metric == "srgb_ssim":
                    gains = {name: 0.0 for name in gains}
                elif metric == "linear_psnr":
                    # Retain these unfavorable, convention-dependent scores.
                    gains = {"control": -2.0, "interval": -2.0, "parent": 0.0}
                mean = gains[first["label"]] - gains[second["label"]]
                base = 0.95 if metric == "srgb_ssim" else 50.0
                stats["comparisons"].append(
                    {
                        "panel": panel,
                        "kind": kind,
                        "metric": metric,
                        "first": first["label"],
                        "second": second["label"],
                        "first_checkpoint_sha256": first["sha256"],
                        "second_checkpoint_sha256": second["sha256"],
                        "sources": sources,
                        "mean_first_minus_second": mean,
                        "first_source_balanced_mean": base + gains[first["label"]],
                        "second_source_balanced_mean": base + gains[second["label"]],
                        "source_bootstrap_95_interval": [mean - 0.01, mean + 0.01],
                    }
                )
    return stats, control, candidate, parent


def selected(stats, *, first="control", panel="known", metric="sensor_psnr"):
    return next(
        r
        for r in stats["comparisons"]
        if r["first"] == first
        and r["panel"] == panel
        and r["metric"] == metric
        and r["second"] == "parent"
    )


def test_exact_minimums_pass_only_numerical_criteria_and_keep_unfavorable_scores(gate, fixture):
    result = gate.evaluate(*fixture)
    assert all(a["all_numerical_criteria_pass"] for a in result["arms"])
    assert (
        result["arms"][0]["comparisons"]["canonical_camera_linear_PSNR"]["mean_first_minus_second"]
        == -2
    )
    assert result["eligible_for_automatic_extension_or_promotion"] is False
    assert "required" in result["manual_native_color_detail_highlight_review"]


@pytest.mark.parametrize(
    "field,value",
    [("mean_first_minus_second", 0.0499999999999), ("source_bootstrap_95_interval", [0.0, 0.1])],
)
def test_rounded_gain_or_zero_confidence_bound_cannot_pass(gate, fixture, field, value):
    stats, *checkpoints = fixture
    row = selected(stats)
    row[field] = value
    if field == "mean_first_minus_second":
        row["first_source_balanced_mean"] = 50 + value
    result = gate.evaluate(stats, *checkpoints)
    assert not result["arms"][0]["all_numerical_criteria_pass"]


@pytest.mark.parametrize("ssim,expected", [(-0.0001, True), (-0.000100000001, False)])
def test_ssim_loss_limit_is_applied_without_display_rounding(gate, fixture, ssim, expected):
    stats, *checkpoints = fixture
    row = selected(stats, panel="full427", metric="srgb_ssim")
    row.update(mean_first_minus_second=ssim, first_source_balanced_mean=0.95 + ssim)
    matched = next(
        r for r in stats["comparisons"] if r["second"] == "control" and r["metric"] == "srgb_ssim"
    )
    matched.update(mean_first_minus_second=-ssim, second_source_balanced_mean=0.95 + ssim)
    assert gate.evaluate(stats, *checkpoints)["arms"][0]["all_numerical_criteria_pass"] is expected


@pytest.mark.parametrize(
    "problem",
    [
        "duplicate",
        "missing",
        "kind",
        "count",
        "checkpoint",
        "NaN",
        "interval",
        "source",
        "old-parent",
        "coverage",
    ],
)
def test_incomplete_or_misbound_evidence_is_rejected(gate, fixture, problem):
    stats, *checkpoints = copy.deepcopy(fixture)
    row = selected(stats)
    if problem == "duplicate":
        stats["comparisons"].append(row)
    elif problem == "missing":
        stats["comparisons"].remove(row)
    elif problem == "kind":
        row["kind"] = "synthetic"
    elif problem == "count":
        row["sources"] = 72
    elif problem == "checkpoint":
        row["second_checkpoint_sha256"] = "f" * 64
    elif problem == "NaN":
        row["source_bootstrap_95_interval"][0] = float("nan")
    elif problem == "interval":
        row["source_bootstrap_95_interval"] = [1.0, -1.0]
    elif problem == "source":
        stats["sources"][0]["second"]["checkpoint_sha256"] = "f" * 64
    elif problem == "old-parent":
        stats["sources"][0]["second"]["report"] = "old/summary.json"
    else:
        stats["audits"]["full427"]["cases"] = 62020
    with pytest.raises(ValueError):
        gate.evaluate(stats, *checkpoints)


@pytest.mark.parametrize("loss,expected", [(-0.03, True), (-0.030000000001, False)])
def test_matched_interval_primary_loss_limit_stays_separate_from_parent_gates(
    gate, fixture, loss, expected
):
    stats, *checkpoints = fixture
    row = next(
        r
        for r in stats["comparisons"]
        if (r["first"], r["second"], r["panel"], r["metric"])
        == ("interval", "control", "known", "sensor_psnr")
    )
    for name, gain in [("control", 0.1), ("interval", 0.1 + loss)]:
        parent_row = selected(stats, first=name)
        parent_row.update(
            mean_first_minus_second=gain,
            first_source_balanced_mean=50 + gain,
            source_bootstrap_95_interval=[gain - 0.01, gain + 0.01],
        )
    row.update(
        mean_first_minus_second=loss,
        first_source_balanced_mean=50.1 + loss,
        second_source_balanced_mean=50.1,
    )
    result = gate.evaluate(stats, *checkpoints)
    assert all(a["all_numerical_criteria_pass"] for a in result["arms"])
    assert result["matched_interval_effect"]["all_numerical_criteria_pass"] is expected
