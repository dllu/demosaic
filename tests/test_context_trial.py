"""Protocol fixtures only; physical CFA/core/loss checks are in test_training_context."""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/train_context_trial.py"
spec = importlib.util.spec_from_file_location("context_trial", SCRIPT)
trial = importlib.util.module_from_spec(spec)
original_path = list(sys.path)
try:
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(trial)
finally:
    sys.path[:] = original_path


def observations():
    first, second = [], []
    for step, domain in enumerate(("commons", "native", "paired"), 1):
        common = {
            "step": step,
            "domain": domain,
            "source_batch_sha256": f"source-{step}",
            "supervision_batch_sha256": f"loss-{step}",
            "actual_loss_batch_sha256": f"loss-{step}",
        }
        first.append(
            {
                **common,
                "forward_native_size": 256,
                "expected_forward_inputs_sha256": f"small-{step}",
                "actual_forward_inputs_sha256": f"small-{step}",
            }
        )
        second.append(
            {
                **common,
                "forward_native_size": 320,
                "expected_forward_inputs_sha256": f"large-{step}",
                "actual_forward_inputs_sha256": f"large-{step}",
            }
        )
    return first, second


def test_context_comparison_requires_identical_source_and_actual_supervision():
    first, second = observations()
    result = trial.compare_observations(first, second)
    assert result["recorded_pairs"] == 3
    assert result["domains"] == {"commons": 1, "native": 1, "paired": 1}


@pytest.mark.parametrize(
    "key,value",
    [
        ("source_batch_sha256", "changed"),
        ("supervision_batch_sha256", "changed"),
        ("actual_loss_batch_sha256", "changed"),
        ("actual_forward_inputs_sha256", "wrong-field"),
        ("step", 77),
        ("domain", "paired"),
        ("forward_native_size", 256),
    ],
)
def test_context_guard_rejects_observed_drift_or_a_missing_extra_field(key, value):
    first, second = observations()
    second[0][key] = value
    with pytest.raises(ValueError):
        trial.compare_observations(first, second)


def test_context_guard_rejects_a_forward_claim_not_seen_by_the_hook():
    first, second = observations()
    second[0]["expected_forward_inputs_sha256"] = first[0]["actual_forward_inputs_sha256"]
    with pytest.raises(ValueError, match="Actual forward"):
        trial.compare_observations(first, second)


def test_identical_wrong_loss_fields_cannot_pass_by_cross_arm_equality():
    first, second = observations()
    for rows in (first, second):
        rows[0]["actual_loss_batch_sha256"] = "same-wrong-loss"
    with pytest.raises(ValueError, match="Actual loss"):
        trial.compare_observations(first, second)


def test_context_guard_rejects_identical_forwards_and_incomplete_domains():
    first, second = observations()
    same = copy.deepcopy(second)
    for a, b in zip(first, same, strict=True):
        b["actual_forward_inputs_sha256"] = a["actual_forward_inputs_sha256"]
        b["expected_forward_inputs_sha256"] = a["actual_forward_inputs_sha256"]
    with pytest.raises(ValueError, match="extra context"):
        trial.compare_observations(first, same)
    with pytest.raises(ValueError, match="three source domains"):
        trial.compare_observations(first[:2], second[:2])
