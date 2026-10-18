"""The quality operator must reject unfinished or still-running training owners."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import psutil
import pytest


def operator():
    scripts = str(Path("scripts").absolute())
    sys.path.insert(0, scripts)
    try:
        spec = importlib.util.spec_from_file_location(
            "objective_review", Path(scripts) / "review_reconstruction_objective.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(scripts)


def test_training_incomplete_is_rejected_before_checkpoint_or_source_access(tmp_path):
    review = operator()
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"status": "running-objective-first1000"}))
    with pytest.raises(RuntimeError, match="must complete before review"):
        review.require_completed({"training_status": str(status)})


def test_terminal_status_cannot_override_actual_live_owner(tmp_path):
    review = operator()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    status = tmp_path / "status.json"
    status.write_text(json.dumps({"status": review.TERMINAL, "controller": owner,
                                  "child": owner}))
    with pytest.raises(AssertionError):
        review.require_completed({"training_status": str(status), "training_owner": owner})


def test_pid_reuse_is_not_treated_as_the_original_owner():
    review = operator()
    assert not review.alive({"pid": os.getpid(), "created": 0})
