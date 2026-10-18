import copy
import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def script():
    path = Path("scripts/review_mixed_packed_quarter.py")
    spec = importlib.util.spec_from_file_location("quarter_review", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def test_inference_refuses_running_or_partial_training(script, tmp_path):
    status = tmp_path / "training.json"
    for value in [
        "training-mixed16-quarter",
        "completed-mixed16-quarter-arm",
        "failed-no-automatic-restart-or-promotion",
    ]:
        status.write_text(json.dumps({"status": value}))
        with pytest.raises(RuntimeError, match="Both isolated"):
            script.completed({"training_workflow": str(status)})


def test_hue_uses_fresh_lineage_and_actual_10k_boundary(script, monkeypatch):
    seen = {}

    def evaluate(*args, **kwargs):
        seen.update(args=args, kwargs=kwargs)

    monkeypatch.setattr(script, "evaluate_records", evaluate)
    checkpoints = [
        {"label": arm, "initialization": "fresh", "step": 10000} for arm in ["no-dino", "dino"]
    ]
    plan = {
        "references": [{"label": "V63-original20k", "sha256": "mature"}],
        "nonlocal_reference": {"path": "released"},
        "grid_inputs": "fixed",
    }
    script.hue(plan, checkpoints, "workflow", "output")
    records = seen["args"][3]
    assert [c["initialization"] for c in records[:2]] == ["fresh", "fresh"]
    assert seen["kwargs"] == {"expected_step": 10000, "precision": "float32"}
    assert len(records) == 4 and seen["args"][4] == "mature"


def startup(tmp_path):
    parent = tmp_path / "parent.pt"
    parent.write_bytes(b"preserved original")
    fixtures = [
        {"production_step": step, "domain": "commons", "batch_fingerprint": format(step, "064x")}
        for step in range(8001, 8017)
    ]
    values = {
        "parent": {"path": str(parent), "sha256": hashlib.sha256(parent.read_bytes()).hexdigest()},
        "first_optimizer_step": 2001,
        "completed_continuation": True,
        "model_Adam_global_RNG_restored_before_first_update": True,
        "Adam_param_groups_restored": True,
        "first16_original_training_inputs_verified": True,
        "EMA_restored_before_first_EMA_update": True,
        "first16": [
            {
                "data_step": v["production_step"],
                "domain": v["domain"],
                "batch_sha256": v["batch_fingerprint"],
            }
            for v in fixtures
        ],
    }
    return values, {"prefix_checkpoint": str(parent)}, fixtures


@pytest.mark.parametrize(
    "problem", ["parent", "EMA", "Adam", "RNG", "unfinished", "step", "input", "missing_input"]
)
def test_actual_restore_and_input_drift_are_rejected(script, tmp_path, problem):
    checks, arm, fixtures = startup(tmp_path)
    script.startup_checks(checks, arm, fixtures)
    if problem == "parent":
        Path(arm["prefix_checkpoint"]).write_bytes(b"different")
    elif problem in ["EMA", "Adam", "RNG", "unfinished"]:
        key = {
            "EMA": "EMA_restored_before_first_EMA_update",
            "Adam": "Adam_param_groups_restored",
            "RNG": "model_Adam_global_RNG_restored_before_first_update",
            "unfinished": "completed_continuation",
        }[problem]
        checks[key] = False
    elif problem == "step":
        checks["first_optimizer_step"] = 1
    elif problem == "input":
        checks["first16"][0]["batch_sha256"] = "0" * 64
    else:
        checks["first16"].pop()
    with pytest.raises(AssertionError):
        script.startup_checks(checks, arm, fixtures)


def observations(script):
    rows = []
    for step in [1, 13, *range(25, 2001, 25), 2001, *range(2025, 10001, 25)]:
        groups = [
            {
                "data_step": data_step,
                "domain": script.initial.training_domain(data_step, 51, 0.25, 0.25),
                "examples": 4,
                "batch_sha256": format(data_step, "064x"),
            }
            for data_step in range(4 * step - 3, 4 * step + 1)
        ]
        progress = max(0, step - 500) / 39500
        rows.append(
            {
                "step": step,
                "data_step_start": 4 * step - 3,
                "data_step_end": 4 * step,
                "example_draws": 16 * step,
                "effective_batch_size": 16,
                "optimizer_batch_groups": 4,
                "optimizer_forward_groups": 1,
                "domain": "mixed",
                "loss": 0.1,
                "grad_norm": 0.1,
                "lr": 2e-4
                * min(1, step / 500)
                * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2),
                "source_groups": groups,
                "batch_sha256": hashlib.sha256(
                    json.dumps(groups, sort_keys=True).encode()
                ).hexdigest(),
            }
        )
    return rows


def test_complete_403_row_schedule_is_accepted(script):
    script.check_observations(observations(script))


@pytest.mark.parametrize(
    "problem", ["LR", "examples", "source", "hash", "nonfinite", "missing_resume_row"]
)
def test_resumed_schedule_and_trace_corruption_are_rejected(script, problem):
    rows = copy.deepcopy(observations(script))
    if problem == "LR":
        rows[82]["lr"] *= 2
    elif problem == "examples":
        rows[82]["example_draws"] -= 16
    elif problem == "source":
        rows[82]["source_groups"][0]["domain"] = "not-the-original-domain"
        rows[82]["batch_sha256"] = hashlib.sha256(
            json.dumps(rows[82]["source_groups"], sort_keys=True).encode()
        ).hexdigest()
    elif problem == "hash":
        rows[-1]["batch_sha256"] = "0" * 64
    elif problem == "nonfinite":
        rows[-1]["loss"] = float("nan")
    else:
        del rows[82]
    with pytest.raises(AssertionError):
        script.check_observations(rows)
