"""Fixed signed-carrier/noise criteria and exact-owner review sequencing."""

import importlib.util
import json
import math
from collections import defaultdict
from pathlib import Path

import psutil
import pytest


def script(name, monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").absolute()))
    path = Path("scripts") / (name + ".py")
    spec = importlib.util.spec_from_file_location(name + "_test", path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def summarize(summary, rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[tuple(r[k] for k in ("level", "contrast", "period", "condition", "model"))].append(
            r
        )
    summary["carrier_summary"], summary["flat_summary"] = [], []
    for key, group in grouped.items():
        metrics = {}
        for name in group[0]["metrics"]:
            values = [r["metrics"][name] for r in group]
            mean = sum(values) / len(values)
            metrics[name] = {
                "mean": mean,
                "std": math.sqrt(sum((v - mean) ** 2 for v in values) / len(values)),
                "min": min(values),
                "max": max(values),
            }
        result = dict(zip(("level", "contrast", "period", "condition", "model"), key, strict=True))
        result.update(cases=len(group), metrics=metrics)
        summary[group[0]["kind"] + "_summary"].append(result)


@pytest.fixture
def analytic():
    control, bank = {"label": "control", "sha256": "a" * 64}, {"label": "bank", "sha256": "b" * 64}
    summary = {
        "precision": "float32",
        "roi_xywh": [48, 48, 160, 160],
        "flat_frequency_band_cycles_per_pixel": [1 / 48, 0.22],
        "models": [control, bank],
    }
    rows = []
    signals = [("carrier", l, c, p) for l in (0.01, 0.18) for c in (0.02, 0.1) for p in (4, 8, 16)]
    signals += [("flat", l, 0, None) for l in (0.01, 0.18)]
    for kind, level, contrast, period in signals:
        for condition in ("adc-only", "iso12800-prior"):
            for pattern in ("RGGB", "BGGR", "GRBG", "GBRG"):
                for draw in range(4):
                    for model in ("control", "bank", "malvar"):
                        fields = (
                            (
                                "in_phase_gain",
                                "gain_channel_std",
                                "quadrature_gain",
                                "amplitude_ratio",
                                "dc_bias_abs",
                                "noncarrier_rms",
                                "linear_srgb_rmse",
                            )
                            if kind == "carrier"
                            else (
                                "dc_bias_abs_rgb",
                                "linear_srgb_rmse",
                                "spatial_luma_rms",
                                "relative_band_rms",
                                "relative_peak_band_contrast",
                            )
                        )
                        metrics = dict.fromkeys(fields, 0.0)
                        if kind == "carrier":
                            metrics.update(
                                in_phase_gain=0.05 if model == "bank" else 0.0, amplitude_ratio=1.0
                            )
                        else:
                            metrics["spatial_luma_rms"] = 0.005 if model == "bank" else 0.004
                        rows.append(
                            {
                                "kind": kind,
                                "level": level,
                                "contrast": contrast,
                                "period": period,
                                "condition": condition,
                                "pattern": pattern,
                                "draw": draw,
                                "model": model,
                                "metrics": metrics,
                            }
                        )
    summarize(summary, rows)
    return summary, rows, control, bank


def test_exact_frozen_limits_pass_without_claiming_photographic_uncertainty(monkeypatch, analytic):
    gate = script("score_directional_bank_eligibility", monkeypatch)
    result = gate.evaluate_analytic(*analytic)
    assert result["coverage_arithmetic_audit"]["cases"] == 1344
    assert result["all_criteria_pass"]
    assert all(
        x["bank_minus_control_gain"] == 0.05 and x["flat_rms_ratio"] == 1.25
        for x in result["comparisons"]
    )
    assert "manual native review remains required" in result["scope"]


@pytest.mark.parametrize("failure", ["signed_gain", "one_carrier", "flat_noise"])
def test_extra_noise_amplitude_and_one_good_carrier_cannot_pass(monkeypatch, analytic, failure):
    summary, rows, *checkpoints = analytic
    for r in rows:
        if r["model"] != "bank" or r["condition"] != "iso12800-prior":
            continue
        if failure == "signed_gain" and r["kind"] == "carrier":
            r["metrics"].update(in_phase_gain=0.0499999999999, amplitude_ratio=2.0)
        elif failure == "one_carrier" and (r["level"], r["contrast"], r["period"]) == (
            0.01,
            0.1,
            8,
        ):
            r["metrics"]["in_phase_gain"] = -0.1
        elif failure == "flat_noise" and r["kind"] == "flat":
            r["metrics"]["spatial_luma_rms"] = 0.0050000000001
    summarize(summary, rows)
    assert not script("score_directional_bank_eligibility", monkeypatch).evaluate_analytic(
        summary, rows, *checkpoints
    )["all_criteria_pass"]


@pytest.mark.parametrize("failure", ["missing", "duplicate", "SHA", "half", "summary"])
def test_incomplete_misbound_or_changed_analytic_evidence_is_rejected(
    monkeypatch, analytic, failure
):
    summary, rows, control, bank = analytic
    if failure == "missing":
        rows.pop()
    elif failure == "duplicate":
        rows[-1] = rows[0]
    elif failure == "SHA":
        bank = {**bank, "sha256": "c" * 64}
    elif failure == "half":
        summary["precision"] = "float16"
    else:
        summary["carrier_summary"][0]["metrics"]["in_phase_gain"]["mean"] += 0.01
    with pytest.raises((ValueError, AssertionError)):
        script("score_directional_bank_eligibility", monkeypatch).evaluate_analytic(
            summary, rows, control, bank
        )


def test_terminal_status_cannot_start_review_while_actual_owner_is_live(tmp_path, monkeypatch):
    review = script("review_directional_bank", monkeypatch)
    owner = {"pid": psutil.Process().pid, "created": psutil.Process().create_time()}
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"status": review.TERMINAL, "controller": owner, "child": owner}))
    with pytest.raises(AssertionError):
        review.require_completed({"training_status": str(status), "training_owner": owner})
    with pytest.raises(AssertionError):
        review.require_completed(
            {
                "training_status": str(status),
                "training_owner": {**owner, "created": owner["created"] - 1},
            }
        )


def test_closure_waits_for_live_owner_and_rejects_missing_stages(monkeypatch):
    closure = script("close_directional_bank_review", monkeypatch)
    owner = {"pid": psutil.Process().pid, "created": psutil.Process().create_time()}
    status = {
        "status": closure.TERMINAL,
        "controller": owner,
        "child": owner,
        "completed": list(closure.STAGES),
    }
    assert not closure.ready(status, owner)
    monkeypatch.setattr(closure, "alive", lambda _: False)
    assert closure.ready(status, owner)
    status["completed"].pop()
    with pytest.raises(RuntimeError, match="stages are incomplete"):
        closure.ready(status, owner)
