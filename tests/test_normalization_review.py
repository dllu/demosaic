import importlib.util
import json
import sys
from pathlib import Path

import pytest


def script():
    path = Path("scripts/review_normalization_trial.py")
    spec = importlib.util.spec_from_file_location("normalization_review", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


@pytest.mark.parametrize(
    "status",
    [
        "training-original1000-to4000",
        "completed-one-original4000-arm-awaiting-other-or-review",
        "failed-no-automatic-restart",
        "completed-matched-first1000-awaiting-full-quality-and-native-review",
    ],
)
def test_review_does_not_release_for_live_failed_or_partial4000_boundary(tmp_path, status):
    workflow = tmp_path / "status.json"
    workflow.write_text(json.dumps({"status": status}))
    with pytest.raises(RuntimeError, match="original4000 training is incomplete"):
        script().completed(workflow, expected_step=4000)


def test_unknown_boundary_is_rejected_before_reading_any_state():
    with pytest.raises(ValueError, match="boundary1000 or4000"):
        script().completed("unused", expected_step=2000)
