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


@pytest.mark.parametrize("step", [2000, 8000, 40000])
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


def test_fp32_color_grid_cannot_silently_reuse_half_precision_predictions():
    module = script()
    for options in [{"reuse_report": "old"}, {"reuse_audit": "old"}, {"reuse_only": True}]:
        with pytest.raises(ValueError, match="requires float16"):
            module.evaluate_records(
                "unused", "unused", "unused", [], "parent", precision="float32", **options
            )


def test_explicit_fp32_grid_preserves_inference_scope_before_input_loading(monkeypatch):
    module = script()

    def stop(path):
        assert torch.is_inference_mode_enabled() and not torch.is_grad_enabled()
        raise RuntimeError("input boundary")

    monkeypatch.setattr(module, "read", stop)
    with torch.enable_grad():
        with pytest.raises(RuntimeError, match="input boundary"):
            module.evaluate_records("unused", "unused", "unused", [], "parent", precision="float32")
        assert torch.is_grad_enabled() and not torch.is_inference_mode_enabled()


def test_multistage_lineage_keeps_exact_parent_identity_and_stage_boundary():
    module = script()
    original = {"path": "original-V43.pt", "sha256": "original", "step": 2000}
    parent = {"path": "final-V95.pt", "sha256": "parent", "step": 20000}
    for checkpoint, step, initializer in [("parent", 20000, original), ("candidate", 4000, parent)]:
        expected = {"step": step, "initialized_from": initializer}
        state = {"step": step, "config": {"initialized_from": initializer}}
        module.check_joint_lineage(state, checkpoint, "original", 20000, lineage=expected)
        for bad in [
            {"step": step - 1, "config": state["config"]},
            {"step": step, "config": {"initialized_from": {**initializer, "step": 999}}},
            {"step": step, "config": {"initialized_from": {**initializer, "sha256": "other"}}},
            {"step": step, "config": {"initialized_from": {**initializer, "path": "other"}}},
            {"step": step, "config": {}},
        ]:
            with pytest.raises(AssertionError):
                module.check_joint_lineage(bad, checkpoint, "original", 20000, lineage=expected)
    # An independently initialized original still has an exact, explicit boundary.
    module.check_joint_lineage(
        {"step": 2000, "config": {}}, "original", "original", 20000, lineage={"step": 2000}
    )
    with pytest.raises(AssertionError):
        module.check_joint_lineage(
            {"step": 1999, "config": {}}, "original", "original", 20000, lineage={"step": 2000}
        )
    with pytest.raises(AssertionError):
        module.check_joint_lineage(
            {"step": 2000, "config": {}},
            "original",
            "original",
            2000,
            fresh=True,
            lineage={"step": 2000},
        )
