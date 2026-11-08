"""Ordered FP32 closure and new replay/counter validation; no quality fixture."""

import copy

import numpy as np
import pytest
from audit_spatial_context_quality import native_addition, validate_stream
from train_spatial_context_trial import METHODS


def test_ordered_wave_addition_must_not_regroup_older_corrections():
    old = np.full((1, 3, 2, 2), np.float32(1))
    old_correction = np.full_like(old, -1)
    wave = np.full_like(old, 2**-25)
    inherited = old + old_correction
    value = inherited + wave
    assert not np.array_equal(value, old + (old_correction + wave))
    assert native_addition(value, inherited, wave) == 12
    with pytest.raises(AssertionError):
        native_addition(old + (old_correction + wave), inherited, wave)


@pytest.mark.parametrize("change", ["dtype", "shape", "nan"])
def test_invalid_native_arrays_are_rejected(change):
    inherited = np.zeros((1, 3, 2, 2), np.float32)
    wave = np.zeros_like(inherited)
    value = inherited.copy()
    if change == "dtype":
        wave = wave.astype(np.float64)
    if change == "shape":
        wave = wave[..., :1]
    if change == "nan":
        value[0, 0, 0, 0] = np.nan
    with pytest.raises(ValueError):
        native_addition(value, inherited, wave)


def schema_fixture(monkeypatch):
    # This stubs the independently tested legacy evidence validator. Every
    # input/prediction below is a labeled structural stand-in, not native quality.
    import audit_spatial_context_quality as audit

    monkeypatch.setattr(audit, "validate_evidence", lambda *args: None)
    monkeypatch.setattr(audit, "validate_support", lambda *args: None)
    counts = {"wrapper": 1644, "frozen": 1644, "network": 1500, "sampler": 7500, "projection": 1500}
    plan = {
        "processing_order": list(range(822)),
        "expected_quality_counts": counts,
        "module_config": {},
    }
    design = []
    inputs = {}
    baseline = {}
    frozen = {}
    events = []
    journal = []
    rows = []
    for index in range(822):
        cid = f"schema-fixture-{index}"
        case = {"id": cid, "arrays": {"fixture": index}, "parent": {"fixture_parent": index}}
        design.append(case)
        noisy = index < 750
        inputs[cid] = {
            "noisy": noisy,
            "fingerprints": {
                k: {"fixture": index, "kind": k} for k in ["packed", "variance", "colors", "wb"]
            },
            "packed_shape": [1, 4, 8, 8],
            "colors": [[0, 1, 1, 2]],
        }
        baseline[cid] = {"values": {"fixture_V183": index}}
        frozen[cid] = {"values": {"fixture_V169": index} if noisy else baseline[cid]["values"]}
    running = {k: 0 for k in counts}
    head = 0
    for method in METHODS.values():
        for index, case in enumerate(design):
            cid = case["id"]
            noisy = inputs[cid]["noisy"]
            row = {
                "id": cid,
                "method": method,
                "index": index,
                "values": {"fixture_new": index} if noisy else baseline[cid]["values"],
                "inherited_values": copy.deepcopy(baseline[cid]["values"]),
                "frozen_values": copy.deepcopy(frozen[cid]["values"]),
                "inherited_V183_EMA_replay_exact": True,
                "frozen_V169_replay_exact": True,
                "ADC_exact": not noisy,
                "wave_correction_RMS_DN16": 0.1 if noisy else 0.0,
            }
            record = {
                "method": method,
                "index": index,
                "id": cid,
                "arrays": case["arrays"],
                "parent": case["parent"],
                "inputs": copy.deepcopy(inputs[cid]["fingerprints"]),
                "row": row,
                "evidence": {"fixture_evidence": index} if noisy else None,
                "support": {"fixture_support": index} if noisy else None,
                "inherited_replay_exact": True,
                "frozen_replay_exact": True,
                "baseline_plus_wave_closure_exact": True,
            }
            for key in running:
                running[key] += (
                    5 * int(noisy)
                    if key == "sampler"
                    else (1 if key in ["wrapper", "frozen"] else int(noisy))
                )
            head += int(noisy)
            events.append(
                {
                    "method": method,
                    "index": index,
                    "ordinal": index,
                    "id": cid,
                    "matching_evaluated": noisy,
                    "counts": running.copy(),
                    "readout_calls": head,
                }
            )
            rows.append(row)
            journal.append(record)
    scores = {
        "rows": rows,
        "counts": counts,
        "readout_calls": 1500,
        "ADC_outputs_exact_V169": 144,
        "exact_V183_EMA_replays": 1644,
        "exact_V169_replays": 1644,
        "weights_unchanged": True,
        "RNG_unchanged": True,
    }
    return plan, scores, design, events, journal, inputs, baseline, frozen


def test_new_stream_schema_accepts_both_replays_and_all_head_calls(monkeypatch):
    check = validate_stream(*schema_fixture(monkeypatch))
    assert check["input_fingerprints"] == 6576 and check["readout_calls"] == 1500
    assert check["exact_input_only_raw_EMA_evidence_pairs"] == 750


@pytest.mark.parametrize(
    "change",
    [
        "baseline",
        "frozen",
        "input",
        "head_calls",
        "ADC",
        "closure",
        "evidence_pair",
        "support_pair",
    ],
)
def test_altered_new_stream_contract_is_rejected(monkeypatch, change):
    data = schema_fixture(monkeypatch)
    if change == "baseline":
        data[4][0]["row"]["inherited_values"] = {"wrong": 1}
    if change == "frozen":
        data[4][0]["row"]["frozen_values"] = {"wrong": 1}
    if change == "input":
        data[4][0]["inputs"]["packed"] = {"wrong": 1}
    if change == "head_calls":
        data[3][0]["readout_calls"] = 0
    if change == "ADC":
        data[4][750]["row"]["wave_correction_RMS_DN16"] = 0.1
    if change == "closure":
        data[4][0]["baseline_plus_wave_closure_exact"] = False
    if change == "support_pair":
        data[4][822]["support"] = {"different": 1}
    if change == "evidence_pair":
        data[4][822]["evidence"] = {"different": True}
    with pytest.raises(AssertionError):
        validate_stream(*data)
