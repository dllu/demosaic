import importlib.util
import sys
from pathlib import Path

import pytest


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
def test_candidate_requires_the_declared_initializer_and_boundary(initializer, step):
    state = {"step": step, "config": {"initialized_from": {"sha256": initializer}}}
    if initializer == "parent" and step == 1000:
        script().check_joint_lineage(state, "candidate", "parent", 1000)
    else:
        with pytest.raises(AssertionError):
            script().check_joint_lineage(state, "candidate", "parent", 1000)
