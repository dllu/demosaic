"""Reject altered loss, mask, state clocks and premature terminal audit."""

import copy
import json
import math

import pytest
from audit_spatial_context_training import terminal, validate_trace


def fixture():
    plan = {"steps": 6, "warmup": 2, "lr": 0.001, "domain_weights": {"mesh": 1}}
    trace = []
    cache = []
    units = []
    old = []
    updates = 0
    names = [
        "pixel",
        "gradient",
        "local_regret",
        "DC_regret",
        "flat_anchor",
        "pair_difference",
        "pair_common",
        "flat_spatial",
        "coherent_response",
    ]
    for step in range(1, 7):
        noisy = step != 3
        updates += int(noisy)
        phase = max(0, step - 2) / 4
        lr = 0.001 * min(1, step / 2) * (0.1 + 0.9 * (1 + math.cos(math.pi * phase)) / 2)
        binding = {"path": f"fixture-batch-{step}", "sha256": f"fixture-{step}"}
        row = {
            "step": step,
            "batch": binding,
            "parent": {"fixture": step},
            "domain": "mesh",
            "noisy": noisy,
            "lr": lr,
            "counts": {
                k: (5 * updates if k == "sampler" else updates)
                for k in ["wrapper", "frozen", "network", "sampler", "projection"]
            },
            "updates": updates,
        }
        if noisy:
            row.update(
                loss=27.0,
                terms=dict(zip(names, map(float, range(1, 10)), strict=True)),
                flat_mask={"fixture": step},
                flat_eligible_pixels=17,
                EMA_decay=min(0.999, (1 + updates) / (10 + updates)),
                gradient_norm=1.0,
                wave_RMS_DN16=0.1,
                zero_gradient_tensors=[],
            )
        else:
            row["skipped"] = "zero variance;no matching,readout or optimizer call"
        trace.append(row)
        old.append(copy.deepcopy(row))
        cache.append(
            {
                "step": step,
                "arrays": binding,
                "parent": row["parent"],
                "metadata": {"domain": "mesh"},
                "inputs": {"packed": {"shape": [4, 4, 8, 8]}},
            }
        )
        units.append({"step": step, "batch": binding})
    return trace, cache, units, old, plan


def test_structural_fixture_accepts_complete_head_clock_and_nine_term_total():
    result = validate_trace(*fixture())
    assert result["updates"] == 5 and result["images"] == 20 and result["ADC_skips"] == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("loss", 27.000001),
        ("flat_mask", {"wrong": 1}),
        ("EMA_decay", 0.99),
        ("gradient_norm", math.inf),
        ("wave_RMS_DN16", -1.0),
        ("lr", 0.123),
        ("updates", 5),
        ("counts", {}),
        ("noisy", 0),
        ("zero_gradient_tensors", ["network.tail.weight"]),
    ],
)
def test_tampered_first_row_is_rejected(field, value):
    data = fixture()
    data[0][0][field] = value
    with pytest.raises((AssertionError, ValueError)):
        validate_trace(*data)


def test_missing_new_loss_is_rejected():
    data = fixture()
    del data[0][0]["terms"]["coherent_response"]
    with pytest.raises(ValueError):
        validate_trace(*data)


def test_live_owner_rejects_before_result_or_torch_access(tmp_path, monkeypatch):
    import audit_spatial_context_training as audit

    (tmp_path / "wave-train-launch-v1.json").write_text(
        json.dumps({"owner": {"pid": 123, "created": 1.0}})
    )
    monkeypatch.setattr(audit, "owner_live", lambda owner: True)
    with pytest.raises(RuntimeError, match="still live"):
        terminal(tmp_path)
    assert not (tmp_path / "wave-train-result-v1.json").exists()


def test_incomplete_prefix_cannot_pass_as_complete_training():
    data = fixture()
    data[0].pop()
    with pytest.raises(AssertionError):
        validate_trace(*data)
