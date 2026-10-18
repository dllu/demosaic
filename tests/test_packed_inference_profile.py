import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
import torch
from torch import nn


@pytest.fixture(scope="module")
def script():
    path = Path("scripts/profile_packed_inference.py")
    spec = importlib.util.spec_from_file_location("packed_profile", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_nested_instrumentation_preserves_outputs_and_removes_hooks(script):
    model = nn.Sequential(nn.Linear(3, 4), nn.ReLU(), nn.Linear(4, 2))
    inputs = torch.arange(9, dtype=torch.float32).reshape(3, 3)
    expected = model(inputs)
    before = script.model_hash(model)
    rng = torch.get_rng_state().clone()
    modules = {"inclusive": model, "nested": model[0]}
    with script.instrument_modules(modules, torch.device("cpu")) as records:
        for _ in range(2):
            assert torch.equal(model(inputs), expected)
    result = script.collect(records, False)
    assert {k: v["calls"] for k, v in result.items()} == {"inclusive": 2, "nested": 2}
    assert result["inclusive"]["output"]["shape"] == [3, 2]
    assert result["nested"]["output"]["shape"] == [3, 4]
    assert result["inclusive"]["CUDA_interval_ms"] is None
    assert all(not m._forward_hooks and not m._forward_pre_hooks for m in modules.values())
    assert script.model_hash(model) == before and torch.equal(torch.get_rng_state(), rng)


def test_instrumentation_cleans_up_after_model_failure(script):
    class Failing(nn.Module):
        def forward(self, _value):
            raise ValueError("original failure")

    model = Failing()
    with (
        pytest.raises(ValueError, match="original failure"),
        script.instrument_modules({"failing": model}, torch.device("cpu")),
    ):
        model(torch.ones(1))
    assert not model._forward_hooks and not model._forward_pre_hooks


@pytest.mark.parametrize("dino", [False, True])
def test_branch_selection_includes_actual_groups_and_optional_foundation(script, dino):
    from types import SimpleNamespace

    core = SimpleNamespace(
        **{
            name: nn.Identity()
            for name in ["local_stem", "stem", "local_blocks", "up", "decoder", "head"]
        },
        groups=nn.ModuleList([nn.Identity() for _ in range(6)]),
    )
    # The core is a real module in production. This selection check needs only
    # field identities, and does not call the instrumentation validator.
    context = SimpleNamespace(backbone=nn.Identity()) if dino else None
    model = SimpleNamespace(packed_isotropic=core, context=context)
    modules = script.modules_for(model)
    assert len(modules) == (15 if dino else 13)
    assert modules["RAW-group5-nested"] is core.groups[5]
    assert modules["RAW-core-inclusive"] is core
    assert ("DINO-context-nested" in modules) is dino
    if dino:
        assert modules["DINO-backbone-nested"] is context.backbone


@pytest.fixture(scope="module")
def queue():
    path = Path("scripts/queue_packed_inference_profile.py")
    spec = importlib.util.spec_from_file_location("packed_profile_queue", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "status", ["waiting-for-training", "profiling", "failed-no-automatic-restart-or-promotion"]
)
def test_unfinished_quality_cannot_release_gpu_profile(queue, tmp_path, status):
    path = tmp_path / "review.json"
    path.write_text(json.dumps({"status": status}))
    with pytest.raises(RuntimeError, match="Complete quarter quality"):
        queue.gate({"review_status": str(path)})


def test_terminal_text_cannot_release_a_live_owner(queue, tmp_path):
    import psutil

    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    path = tmp_path / "review.json"
    path.write_text(json.dumps({"status": queue.TERMINAL, "controller": owner, "child": owner}))
    with pytest.raises(AssertionError):
        queue.gate({"review_status": str(path), "review_owner": owner})


def test_same_pid_with_different_creation_time_is_not_the_owner(queue):
    import psutil

    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    assert queue.alive(owner)
    assert not queue.alive({**owner, "created": owner["created"] - 1})
