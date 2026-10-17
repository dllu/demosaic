import importlib.util
import json
import sys
from pathlib import Path

import psutil
import pytest
import torch


def script():
    path = Path("scripts/review_packed_isotropic_quarter.py")
    spec = importlib.util.spec_from_file_location("packed_quarter_review", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_resume_observations_include_first_resumed_step_and_exclude_validation(tmp_path):
    module = script()
    steps = [1, *range(25, 8001, 25), 8001, *range(8025, 40001, 25)]
    train = [{"event": "train", "step": step} for step in steps]
    validation = [{"event": "validation", "step": step} for step in range(8000, 40001, 8000)]
    path = tmp_path / "metrics.jsonl"
    records = sorted([*train, *validation], key=lambda r: r["step"])
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n")
    assert module.training_observations(path) == train
    # Missing the special resume row and an undeclared extra restart are both
    # different training histories, even when every interval row is present.
    for broken in [
        [r for r in records if r.get("event") != "train" or r["step"] != 8001],
        [*records, {"event": "train", "step": 40000}],
        sorted([*records, {"event": "train", "step": 16001}], key=lambda r: r["step"]),
    ]:
        path.write_text("\n".join(json.dumps(r) for r in broken) + "\n")
        with pytest.raises(AssertionError):
            module.training_observations(path)


def test_training_must_be_complete_and_owner_gone_before_any_review(tmp_path):
    module = script()
    path = tmp_path / "training.json"
    path.write_text(json.dumps({"status": "training-original-recipe-to-quarter-review"}))
    with pytest.raises(RuntimeError, match="incomplete"):
        module.completed({"training_workflow": str(path)})
    owner = psutil.Process()
    path.write_text(
        json.dumps(
            {
                "status": module.TERMINAL,
                "controller": {"pid": owner.pid, "created": owner.create_time()},
            }
        )
    )
    with pytest.raises(AssertionError):
        module.completed({"training_workflow": str(path)})
    assert not torch.cuda.is_initialized()


def test_own_progress_cannot_swap_arms_or_reuse_the_same_weights():
    module = script()
    current = [{"arm": "no-dino", "sha256": "new-a"}, {"arm": "dino", "sha256": "new-b"}]
    parents = [{"arm": "no-dino", "sha256": "old-a"}, {"arm": "dino", "sha256": "old-b"}]
    assert module.progress_pairs(current, parents) == list(zip(current, parents, strict=True))
    for broken in [parents[::-1], parents[:1], [{**parents[0], "sha256": "new-a"}, parents[1]]]:
        with pytest.raises(AssertionError):
            module.progress_pairs(current, broken)
