"""Reject damaged trace/evidence records; these are structural, not quality data."""

import copy
import json
import math

import audit_local_phase_evidence_trial as local_audit
import numpy as np
import pytest
from audit_local_phase_evidence_trial import (
    loss_from_terms,
    restore_on_CPU,
    validate_quality_stream,
    validate_summary,
    validate_training_trace,
)
from train_local_phase_evidence_trial import ARMS, METHODS


@pytest.mark.parametrize("damage", [None, "live", "owner", "failure", "observation"])
def test_actual_audit_requires_terminal_launch_owner(tmp_path, monkeypatch, damage):
    owner = {"pid": 123, "created": 4.0}
    (tmp_path / "review-launch-v1.json").write_text(json.dumps({"owner": owner}))
    result = {"owner": owner, "status": "completed-fixture"}
    if damage == "owner":
        result["owner"] = {"pid": 123, "created": 5.0}
    (tmp_path / "scores-v1.json").write_text(json.dumps(result))
    if damage == "failure":
        (tmp_path / "review-failure-v1.json").write_text("{}")

    def observed(_):
        if damage == "observation":
            raise PermissionError("fixture observation failure")
        return damage == "live"

    monkeypatch.setattr(local_audit, "owner_live", observed)
    if damage is None:
        assert local_audit.terminal(tmp_path / "scores-v1.json") == result
    else:
        with pytest.raises((AssertionError, PermissionError)):
            local_audit.terminal(tmp_path / "scores-v1.json")


def training_fixture(arm):
    plan = {
        "steps": 4,
        "warmup": 1,
        "lr": 1e-4,
        "initial_updates": 900,
        "EMA_decay": 0.999,
        "domain_weights": {"mesh": 4},
        "new_updates_per_arm": 3,
        "ADC_skips_per_arm": 1,
        "new_images_per_arm": 12,
    }
    cache, units, inherited, trace = [], [], [], []
    updates = 0
    for step in range(1, 5):
        batch, parent = (
            {"path": f"batch{step}", "sha256": str(step)},
            {"path": f"parent{step}", "sha256": str(step)},
        )
        cache.append(
            {
                "step": step,
                "arrays": batch,
                "parent": parent,
                "metadata": {"domain": "mesh"},
                "inputs": {"packed": {"shape": [4, 4, 8, 8]}},
            }
        )
        units.append({"step": step, "batch": batch})
        old = {
            "step": step,
            "batch": batch,
            "parent": parent,
            "domain": "mesh",
            "noisy": step != 2,
            "flat_mask": {"sha256": f"mask{step}"},
            "flat_eligible_pixels": 7,
        }
        inherited.append(old)
        row = {
            key: copy.deepcopy(value)
            for key, value in old.items()
            if key not in ["flat_mask", "flat_eligible_pixels"]
        }
        row["lr"] = 1e-4 * (0.1 + 0.9 * (1 + math.cos(math.pi * (step - 1) / 3)) / 2)
        if row["noisy"]:
            updates += 1
            row.update(
                terms={
                    "pixel": 1,
                    "gradient": 2,
                    "local_regret": 3,
                    "DC_regret": 4,
                    "flat_anchor": 5,
                    "pair_difference": 6,
                    "pair_common": 7,
                },
                loss=91.0,
                flat_mask=copy.deepcopy(old["flat_mask"]),
                flat_eligible_pixels=7,
                gradient_norm=0.1,
                correction_RMS_DN16=0.2,
                EMA_decay=min(0.999, (901 + updates) / (910 + updates)),
            )
        else:
            row["skipped"] = "zero variance;no matching,projection or optimizer call"
        row.update(
            updates=updates,
            total_network_updates=900 + updates,
            counts={
                "wrapper": updates,
                "frozen": updates,
                "network": updates,
                "sampler": 5 * updates,
                "projection": updates if arm == "evidence" else 0,
            },
        )
        trace.append(row)
    return trace, cache, units, inherited, plan, arm


@pytest.mark.parametrize("arm", ARMS)
def test_training_bindings_masks_fp32_totals_and_adapter_calls(arm):
    result = validate_training_trace(*training_fixture(arm))
    assert result["FP32_loss_totals"] == 3 and result["ADC_skips"] == 1 and result["images"] == 12


@pytest.mark.parametrize(
    "damage",
    [
        "batch",
        "parent",
        "unit",
        "mask",
        "loss",
        "EMA",
        "lr",
        "clock",
        "samplers",
        "projection",
        "ADC_loss",
        "missing",
    ],
)
def test_damaged_training_record_rejects(damage):
    args = training_fixture("evidence")
    trace, _, units, _, _, _ = args
    if damage == "batch":
        trace[0]["batch"] = {"path": "other"}
    elif damage == "parent":
        trace[0]["parent"] = {"path": "other"}
    elif damage == "unit":
        units[0]["batch"] = {"path": "other"}
    elif damage == "mask":
        trace[0]["flat_mask"] = {"sha256": "wrong"}
    elif damage == "loss":
        trace[0]["loss"] = float(np.nextafter(np.float32(91), np.float32(100)))
    elif damage == "EMA":
        trace[0]["EMA_decay"] = 0.9
    elif damage == "lr":
        trace[0]["lr"] *= 2
    elif damage == "clock":
        trace[0]["total_network_updates"] = 1
    elif damage == "samplers":
        trace[0]["counts"]["sampler"] = 4
    elif damage == "projection":
        trace[0]["counts"]["projection"] = 0
    elif damage == "ADC_loss":
        trace[1]["loss"] = 0
    else:
        trace.pop()
    with pytest.raises(AssertionError):
        validate_training_trace(*args)


def test_loss_term_contract_rejects_missing_extra_and_nonfinite():
    terms = training_fixture("control")[0][0]["terms"]
    assert loss_from_terms(terms, 4) == 91
    for changed in [
        {**terms, "pixel": float("nan")},
        {**terms, "extra": 1},
        {k: v for k, v in terms.items() if k != "pixel"},
    ]:
        with pytest.raises(ValueError):
            loss_from_terms(changed, 4)


def quality_fixture():
    design = [
        {"id": name, "kind": kind, "arrays": {"path": name}, "parent": {"path": name + "-parent"}}
        for name, kind in [("mesh", "mesh"), ("ADC", "flat"), ("sky", "real")]
    ]
    design[0].update(present=True, seed=1)
    design[1]["noise"] = {"name": "ADC"}
    plan = {
        "processing_order": [2, 0, 1],
        "module_config": {"evidence_peaks": 1, "evidence_window": 5, "evidence_stride": 8},
        "expected_quality_counts": {
            "wrapper": 6,
            "frozen": 6,
            "network": 4,
            "sampler": 20,
            "projection": 4,
        },
    }
    inputs = {
        case["id"]: {
            "noisy": case["id"] != "ADC",
            "packed_shape": [1, 4, 16, 16],
            "colors": [[0, 1, 1, 2]],
            "fingerprints": {
                key: case["id"] + key for key in ["packed", "variance", "colors", "wb"]
            },
        }
        for case in design
    }
    frozen_rows = {case["id"]: {"values": {"sha256": "frozen-" + case["id"]}} for case in design}
    evidence = {
        "green_phase_indices": [[1, 2]],
        "bin_yx": [[[[3, 1]], [[4, 1]]]],
        "global_nominal_power": [[[[2.0, 0.2]], [[1.0, 0.1]]]],
        "local_center_power": np.ones((1, 2, 1, 2, 3, 3)).tolist(),
        "centers_y": [0, 8, 15],
        "centers_x": [0, 8, 15],
        "boxes_xywh": [
            [0, 0, 3, 3],
            [6, 0, 5, 3],
            [13, 0, 3, 3],
            [0, 6, 3, 5],
            [6, 6, 5, 5],
            [13, 6, 3, 5],
            [0, 13, 3, 3],
            [6, 13, 5, 3],
            [13, 13, 3, 3],
        ],
        "valid": [[[True], [True]]],
    }
    events, journal, rows = [], [], []
    counts = {key: 0 for key in plan["expected_quality_counts"]}
    for arm in ARMS:
        for endpoint in ["raw", "EMA"]:
            method = METHODS[arm][endpoint]
            for ordinal, index in enumerate(plan["processing_order"]):
                case = design[index]
                noisy = inputs[case["id"]]["noisy"]
                counts["wrapper"] += 1
                counts["frozen"] += 1
                counts["network"] += int(noisy)
                counts["sampler"] += 5 * int(noisy)
                counts["projection"] += int(noisy and arm == "evidence")
                values = (
                    {"sha256": method + case["id"]} if noisy else frozen_rows[case["id"]]["values"]
                )
                row = {
                    "id": case["id"],
                    "index": index,
                    "kind": case["kind"],
                    "cohort": None,
                    "method": method,
                    "values": values,
                    "frozen_values": frozen_rows[case["id"]]["values"],
                    "ADC_exact": not noisy,
                    "frozen_replay_exact": True,
                }
                if case["kind"] == "real":
                    row["reference_scored"] = False
                elif case["kind"] == "mesh":
                    row.update(present=case["present"], seed=case["seed"])
                else:
                    row["noise"] = case["noise"]["name"]
                rows.append(row)
                events.append(
                    {
                        "method": method,
                        "index": index,
                        "id": case["id"],
                        "ordinal": ordinal,
                        "counts": dict(counts),
                        "matching_evaluated": noisy,
                    }
                )
                journal.append(
                    {
                        "method": method,
                        "index": index,
                        "id": case["id"],
                        "row": copy.deepcopy(row),
                        "arrays": case["arrays"],
                        "parent": case["parent"],
                        "inputs": inputs[case["id"]]["fingerprints"],
                        "evidence": copy.deepcopy(evidence)
                        if noisy and arm == "evidence"
                        else None,
                        "frozen_replay_exact": True,
                        "closure_exact": True,
                    }
                )
    scores = {
        "rows": rows,
        "counts": dict(counts),
        "exact_V169_replays": 6,
        "ADC_outputs_exact_V169": 2,
        "weights_unchanged": True,
        "RNG_unchanged": True,
    }
    return plan, scores, design, events, journal, inputs, frozen_rows


def test_all_quality_endpoints_input_evidence_and_exact_adc():
    checked = validate_quality_stream(*quality_fixture())
    assert checked["events"] == 6 and checked["input_fingerprints"] == 24
    assert checked["exact_input_only_raw_EMA_evidence_pairs"] == 2
    assert checked["ADC_outputs"] == 2


@pytest.mark.parametrize(
    "damage",
    [
        "method",
        "parent",
        "fingerprints",
        "frozen",
        "counts",
        "ADC_evidence",
        "missing_evidence",
        "EMA_evidence",
        "green",
        "band",
        "negative_local_power",
        "nonfinite_local_power",
        "centers",
        "boxes",
        "local_shape",
        "valid",
        "ADC",
        "real_GT",
        "duplicate",
    ],
)
def test_damaged_local_quality_evidence_rejects(damage):
    args = quality_fixture()
    _, scores, _, events, journal, _, _ = args
    if damage == "method":
        events[0]["method"] = "V178-evidence-raw"
    elif damage == "parent":
        journal[0]["parent"] = {"path": "other"}
    elif damage == "fingerprints":
        journal[0]["inputs"] = {"packed": "wrong"}
    elif damage == "frozen":
        journal[0]["row"]["frozen_values"] = {"sha256": "wrong"}
    elif damage == "counts":
        events[0]["counts"]["projection"] = 0
    elif damage == "ADC_evidence":
        journal[2]["evidence"] = copy.deepcopy(journal[0]["evidence"])
    elif damage == "missing_evidence":
        journal[0]["evidence"] = None
    elif damage == "EMA_evidence":
        journal[3]["evidence"]["local_center_power"][0][0][0][0][0][0] += 0.1
    elif damage == "green":
        journal[0]["evidence"]["green_phase_indices"] = [[0, 3]]
    elif damage == "band":
        journal[0]["evidence"]["bin_yx"][0][0][0] = [0, 0]
    elif damage in ["negative_local_power", "nonfinite_local_power"]:
        journal[0]["evidence"]["local_center_power"][0][0][0][0][0][0] = (
            -1 if damage == "negative_local_power" else float("nan")
        )
    elif damage == "centers":
        journal[0]["evidence"]["centers_y"][-1] = 16
    elif damage == "boxes":
        journal[0]["evidence"]["boxes_xywh"][0][2] = 4
    elif damage == "local_shape":
        journal[0]["evidence"]["local_center_power"][0][0][0][0].pop()
    elif damage == "valid":
        journal[0]["evidence"]["valid"][0][0][0] = False
    elif damage == "ADC":
        journal[2]["row"]["values"] = {"sha256": "changed"}
    elif damage == "real_GT":
        journal[0]["row"]["reference_scored"] = True
    else:
        scores["rows"][-1] = copy.deepcopy(scores["rows"][0])
    with pytest.raises((AssertionError, TypeError, ValueError)):
        validate_quality_stream(*args)


def test_decimal_summary_covers_all_numeric_columns_and_unique_groups():
    rows = [
        {
            "kind": "flat",
            "noise": "test",
            "cohort": None,
            "method": "candidate",
            "full_error_RMS_DN16": value,
            "changed": True,
        }
        for value in [0.1, 0.2, 0.3]
    ]
    summary = [
        {
            "kind": "flat",
            "condition": "test",
            "cohort": None,
            "method": "candidate",
            "cases": 3,
            "full_error_RMS_DN16": 0.2,
        }
    ]
    assert validate_summary(rows, summary) == 1
    for damaged in [
        [],
        summary + copy.deepcopy(summary),
        [{**summary[0], "full_error_RMS_DN16": 0.3}],
        [{k: v for k, v in summary[0].items() if k != "full_error_RMS_DN16"}],
    ]:
        with pytest.raises(AssertionError):
            validate_summary(rows, damaged)


@pytest.mark.parametrize("candidate", [False, True])
def test_cpu_checkpoint_audit_never_calls_cuda_rng(monkeypatch, candidate):
    import torch
    from phase_evidence_training_state import adam_clocks, update_matching_ema, warm_start_matching
    from torch import nn

    class Fixture(nn.Module):
        def __init__(self, adapter=False):
            super().__init__()
            self.frozen = nn.Linear(2, 2).requires_grad_(False)
            self.network = nn.Linear(2, 1)
            if adapter:
                self.phase_evidence_in = nn.Linear(1, 2, bias=False)
                nn.init.zeros_(self.phase_evidence_in.weight)

        def initialize_from_local_matching(self, weights):
            self.load_state_dict(
                {
                    **weights,
                    "phase_evidence_in.weight": self.phase_evidence_in.weight.detach().clone(),
                },
                strict=True,
            )

        def forward(self):
            x = torch.ones(2, 2)
            if hasattr(self, "phase_evidence_in"):
                x = x + self.phase_evidence_in(torch.ones(2, 1))
            return self.network(x).square().mean()

    module = Fixture()
    optimizer = torch.optim.AdamW(module.network.parameters(), lr=0.001, weight_decay=0.01)
    for _ in range(4):
        optimizer.zero_grad(set_to_none=True)
        module().backward()
        optimizer.step()
    old = {
        "models": copy.deepcopy(module.state_dict()),
        "optimizer": copy.deepcopy(optimizer.state_dict()),
        "updates": 4,
        "ema": copy.deepcopy(module.network.state_dict()),
    }
    module = Fixture(candidate)
    optimizer, ema, _ = warm_start_matching(module, old, lr=0.001, weight_decay=0.01)
    for step in range(3):
        optimizer.zero_grad(set_to_none=True)
        module().backward()
        optimizer.step()
        update_matching_ema(module, ema, total_updates=5 + step, maximum_decay=0.999)
    state = {
        "models": copy.deepcopy(module.state_dict()),
        "optimizer": copy.deepcopy(optimizer.state_dict()),
        "ema": copy.deepcopy(ema),
        "initial_updates": 4,
        "updates": 3,
        "CPU_RNG": torch.get_rng_state().clone(),
        "CUDA_RNG": torch.tensor([1, 2, 3], dtype=torch.uint8),
    }

    def forbidden(*args, **kwargs):
        raise AssertionError("CPU audit called a CUDA RNG API")

    monkeypatch.setattr(torch.cuda, "set_rng_state", forbidden)
    monkeypatch.setattr(torch.cuda, "get_rng_state", forbidden)
    restored = Fixture(candidate)
    actual_opt, actual_ema, proof = restore_on_CPU(restored, state, lr=0.001, weight_decay=0.01)
    assert proof["CPU_RNG_exact"] and proof["CUDA_RNG_exact"] is None
    assert adam_clocks(restored, actual_opt)["network"]["steps"] == [7.0]
    assert adam_clocks(restored, actual_opt)["adapter"]["steps"] == ([3.0] if candidate else [])
    assert all(torch.equal(actual_ema[key], value) for key, value in ema.items())
    assert not torch.cuda.is_initialized()
