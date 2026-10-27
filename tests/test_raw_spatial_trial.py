"""State and continuation contracts; no neural forward or original-media reads."""

import copy
import os
from pathlib import Path

import pytest
import torch
import yaml
from train_directional_bank_trial import read, ref
from train_raw_spatial_trial import validate_recipes
from train_reviewed_shadow_trial import capture_progress, verify_initial_restoration


def states():
    parent = {f"common.{i}": torch.tensor([float(i)]) for i in range(91)}
    actual = {k: v.clone() for k, v in parent.items()}
    actual.update({f"pretrained_rgb.raw_spatial.block.{i}": torch.ones(1) for i in range(22)})
    actual["pretrained_rgb.raw_spatial.project.weight"] = torch.zeros(1)
    return parent, actual


def test_checks_all_common_weights_added_branch_and_learned_resume():
    parent, actual = states()
    verify_initial_restoration(parent, parent, spatial=False, fresh=True)
    verify_initial_restoration(actual, parent, spatial=True, fresh=True)
    actual["pretrained_rgb.raw_spatial.project.weight"].fill_(0.25)
    verify_initial_restoration(actual, actual, spatial=True, fresh=False)
    with pytest.raises(AssertionError):
        verify_initial_restoration(actual, parent, spatial=True, fresh=True)


@pytest.mark.parametrize("corruption", ["missing", "unknown", "common", "resume"])
def test_wrong_initial_state_is_rejected(corruption):
    parent, actual = states()
    expected, fresh = parent, True
    if corruption == "missing":
        del actual["common.90"]
    elif corruption == "unknown":
        actual["wrong.branch"] = actual.pop("pretrained_rgb.raw_spatial.block.21")
    elif corruption == "common":
        actual["common.90"].add_(1)
    else:
        expected, fresh = copy.deepcopy(actual), False
        actual["pretrained_rgb.raw_spatial.block.21"].add_(1)
    with pytest.raises(AssertionError):
        verify_initial_restoration(actual, expected, spatial=True, fresh=fresh)


def progress_fixture(tmp_path):
    checkpoint = tmp_path / "last.pt"
    parent, _ = states()
    state = {"step": 1000, "config": {"steps": 20000}, "model": parent, "ema": parent}
    torch.save(state, checkpoint)
    options = {
        "step": 1000,
        "horizon": 20000,
        "counts": {"optimizer_steps": 1000, "training_forwards": 1000},
        "inputs": [{"step": i} for i in range(1, 1001)],
        "tensor_count": 91,
    }
    return checkpoint, options


def test_progress_hardlink_survives_atomic_last_checkpoint_replacement(tmp_path):
    checkpoint, options = progress_fixture(tmp_path)
    original = ref(checkpoint)
    receipt = capture_progress(tmp_path, "V131", checkpoint, **options)
    snapshot = Path(receipt["checkpoint"]["path"])
    assert snapshot.stat().st_ino == checkpoint.stat().st_ino
    replacement = tmp_path / "next.tmp"
    torch.save({"step": 2000}, replacement)
    os.replace(replacement, checkpoint)
    assert ref(snapshot)["sha256"] == original["sha256"]
    assert snapshot.stat().st_ino != checkpoint.stat().st_ino
    saved = read(tmp_path / "train-V131-progress1000.json")
    assert saved["declared_training_horizon"] == 20000 and saved["step"] == 1000
    assert saved["observed_inputs"] == options["inputs"]
    with pytest.raises(AssertionError):
        capture_progress(tmp_path, "V131", snapshot, **options)


@pytest.mark.parametrize("change", ["endpoint", "count", "input", "checkpoint"])
def test_invalid_progress_never_publishes_a_snapshot(tmp_path, change):
    checkpoint, options = progress_fixture(tmp_path)
    if change == "endpoint":
        options["horizon"] = 1000
    elif change == "count":
        options["counts"]["optimizer_steps"] = 999
    elif change == "input":
        options["inputs"][-1]["step"] = 999
    else:
        options["step"] = 999
        options["counts"] = {"optimizer_steps": 999, "training_forwards": 999}
        options["inputs"] = options["inputs"][:999]
    with pytest.raises(AssertionError):
        capture_progress(tmp_path, "V131", checkpoint, **options)
    assert not list(tmp_path.glob("*progress*"))


def test_actual_recipes_differ_only_on_spatial_architecture():
    repo = Path(__file__).resolve().parents[1]
    configs = [
        yaml.safe_load((repo / f"configs/quality-v120-raw-spatial-v{v}.yaml").read_text())
        for v in (131, 132)
    ]
    validate_recipes(configs)
    for change in ("manifest", "steps", "lr", "noise_pair_draws"):
        changed = copy.deepcopy(configs)
        changed[1][change] = "different"
        with pytest.raises(AssertionError, match="recipes differ"):
            validate_recipes(changed)
