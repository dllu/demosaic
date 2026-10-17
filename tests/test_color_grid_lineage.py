import importlib.util
import sys
from pathlib import Path

import pytest
import torch


def script():
    path = Path("scripts/evaluate_color_grid_cuda.py")
    spec = importlib.util.spec_from_file_location("color_lineage", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_verified_parent_can_have_its_actual_original20k_step():
    state = {"step": 20000, "config": {"initialized_from": {"sha256": "older-parent"}}}
    script().check_joint_lineage(state, "parent", "parent", 1000)


@pytest.mark.parametrize("initializer,step", [("parent", 1000), ("other", 1000), ("parent", 999)])
@pytest.mark.parametrize("expected_step", [1000, 4000])
def test_candidate_requires_the_declared_initializer_and_boundary(initializer, step, expected_step):
    step += expected_step - 1000
    state = {"step": step, "config": {"initialized_from": {"sha256": initializer}}}
    if initializer == "parent" and step == expected_step:
        script().check_joint_lineage(state, "candidate", "parent", expected_step)
    else:
        with pytest.raises(AssertionError):
            script().check_joint_lineage(state, "candidate", "parent", expected_step)


def test_library_entry_point_disables_gradients_and_restores_caller(monkeypatch):
    module = script()

    class StopBeforeInputLoading(Exception):
        pass

    def read_plan(path):
        assert torch.is_inference_mode_enabled()
        assert not torch.is_grad_enabled()
        raise StopBeforeInputLoading

    monkeypatch.setattr(module, "read", read_plan)
    with torch.enable_grad():
        with pytest.raises(StopBeforeInputLoading):
            module.evaluate_records("unused", "unused", "unused", [], "parent")
        assert torch.is_grad_enabled()
        assert not torch.is_inference_mode_enabled()


@pytest.mark.parametrize("step", [2000, 8000])
def test_explicit_fresh_candidate_requires_absent_initializer_and_exact_boundary(step):
    module = script()
    module.check_joint_lineage({"step": step, "config": {}}, "fresh", "parent", step, fresh=True)
    for state in [
        {"step": step - 1, "config": {}},
        {"step": step, "config": {"initialized_from": {"sha256": "parent"}}},
        {"step": step, "config": {"initialized_from": {"sha256": "timing-only-checkpoint"}}},
    ]:
        with pytest.raises(AssertionError):
            module.check_joint_lineage(state, "fresh", "parent", step, fresh=True)
    with pytest.raises(AssertionError):
        module.check_joint_lineage(
            {"step": step, "config": {}}, "parent", "parent", step, fresh=True
        )
