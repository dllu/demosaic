"""Completed-state gates for new spatial endpoints, without model construction."""

import copy
from types import SimpleNamespace

import numpy as np
import pytest
import torch
from collect_quality_predictions import common_grid_mosaic
from queue_matched_quality_predictions import execution_arms, verify_spatial_training_state

from demosaic.cfa import color_indices, unpack
from demosaic.inference import positions, restore_tiled


def fixture(spatial):
    values = {f"common.{i}": torch.zeros(1) for i in range(91)}
    if spatial:
        values.update({f"pretrained_rgb.raw_spatial.{i}": torch.ones(1) for i in range(23)})
    snapshot = {
        "step": 20000,
        "config": {"steps": 20000},
        "model_config": {"raw_spatial_features": spatial},
        "model": values,
        "ema": copy.deepcopy(values),
        "optimizer": {
            "state": {
                i: {"step": torch.tensor(20000.0), "exp_avg": torch.zeros(1)}
                for i in range(112 if spatial else 89)
            }
        },
    }
    actual = {
        "status": "completed-raw-spatial-training-phase",
        "phase": "train",
        "updates": 20000,
        "counts": {
            "training_forwards": 20000,
            "optimizer_steps": 20000,
            "prepared_training_batches": 20000,
            "validation_forwards": 640,
            "encoder_forwards": 20640,
            "target_contexts": 320000,
        },
        "initial_checks": [
            {
                "official_encoder_exact": True,
                "91_parent_or_resume_tensors_exact": True,
            }
        ],
        "model_EMA_Adam_finite": True,
        "frozen_encoder_no_gradients": True,
        "model_EMA_tensor_count": len(values),
        "observed_inputs": [{"step": i} for i in range(1, 20001)],
        "all_observed_inputs_match_saved_control": spatial,
    }
    return actual, snapshot


@pytest.mark.parametrize("spatial", [False, True])
def test_completed_91_and_114_tensor_endpoints_are_accepted(spatial):
    actual, snapshot = fixture(spatial)
    verify_spatial_training_state(actual, snapshot, spatial)


@pytest.mark.parametrize("change", ["partial", "adam", "branch", "inputs", "finite", "budget"])
def test_partial_changed_or_unmatched_endpoint_is_rejected(change):
    actual, snapshot = fixture(True)
    if change == "partial":
        snapshot["step"] = 1000
    elif change == "adam":
        snapshot["optimizer"]["state"][111]["step"] = torch.tensor(19999)
    elif change == "branch":
        snapshot["model"]["wrong.key"] = snapshot["model"].pop("pretrained_rgb.raw_spatial.22")
        snapshot["ema"] = copy.deepcopy(snapshot["model"])
    elif change == "inputs":
        actual["all_observed_inputs_match_saved_control"] = False
    elif change == "finite":
        snapshot["ema"]["common.90"].fill_(float("nan"))
    else:
        actual["counts"]["encoder_forwards"] += 1
    with pytest.raises(AssertionError):
        verify_spatial_training_state(actual, snapshot, True)


def test_explicit_architecture_counts_and_order_are_required():
    execution = {
        "restoration_tensors_by_arm": {"V131": 91, "V132": 114},
        "arms": {"V131": {}, "V132": {}},
        "paired_control_arm": "V131",
    }
    binding = {"path": "not-read", "sha256": "fixture"}
    assert execution_arms(execution, binding, "matched-raw-spatial-v1") == [
        {"arm": arm, "training_plan": binding} for arm in ("V131", "V132")
    ]
    execution["restoration_tensors_by_arm"]["V132"] = 91
    with pytest.raises(AssertionError):
        execution_arms(execution, binding, "matched-raw-spatial-v1")


@pytest.mark.parametrize("shape", [(69, 73), (70, 74), (64, 96)])
def test_real_tiler_delivers_identical_inputs_to_control_and_spatial_grid(shape):
    class Echo(torch.nn.Module):
        def __init__(self, spatial):
            super().__init__()
            self.config = SimpleNamespace(
                restoration_backbone="pretrained-rgb", dino=True, raw_spatial_features=spatial
            )
            self.inputs = []

        def forward(self, packed, *_args):
            self.inputs.append(packed.clone())
            return unpack(packed).expand(-1, 3, -1, -1)

    raw = np.linspace(0.1, 0.2, np.prod(shape), dtype=np.float32).reshape(shape)
    padded = common_grid_mosaic(raw, 32)
    assert np.array_equal(padded[: shape[0], : shape[1]], raw)
    outputs, models = [], [Echo(False), Echo(True)]
    for model in models:
        output, _ = restore_tiled(
            model,
            padded,
            color_indices("RGGB"),
            shot=0,
            read=0,
            tile=64,
            overlap=32,
            batch_size=1,
            device="cpu",
        )
        outputs.append(output[:, : shape[0], : shape[1]])
    assert len(models[0].inputs) == len(models[1].inputs) > 0
    assert all(torch.equal(a, b) for a, b in zip(models[0].inputs, models[1].inputs, strict=True))
    torch.testing.assert_close(outputs[0], outputs[1], rtol=0, atol=0)
    np.testing.assert_allclose(outputs[0][0].numpy(), raw, rtol=0, atol=5e-8)


def test_declared_100MP_common_grid_stays_within_original_forward_budget():
    # Coordinates only; no original RAW allocation/reading or model calls.
    shape = tuple((value + 31) // 32 * 32 for value in (8746, 11662))
    coords = [(y, x) for y in positions(shape[0], 512, 448) for x in positions(shape[1], 512, 448)]
    assert len(coords) == 520 and len(coords) // 4 == 130
    assert all(y % 32 == x % 32 == 0 for y, x in coords)
