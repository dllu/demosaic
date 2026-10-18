import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def script():
    spec = importlib.util.spec_from_file_location(
        "mixed_continuation", "scripts/continue_mixed_packed_trial.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def recipe():
    return {
        "run": "original",
        "experiment_notes": "original",
        "steps": 40000,
        "lr": 2e-4,
        "precision": "float32",
        "optimizer_batch_groups": 4,
        "manifest": "frozen",
        "model": {"isotropic_raw_gain": 32},
    }


def test_only_run_and_notes_may_change(script):
    first = recipe()
    second = {**first, "run": "isolated", "experiment_notes": "continuation"}
    script.same_recipe(first, second)
    with pytest.raises(AssertionError):
        script.same_recipe(first, first)


@pytest.mark.parametrize(
    "key,value",
    [
        ("steps", 10000),
        ("lr", 8e-4),
        ("precision", "float16"),
        ("optimizer_batch_groups", 1),
        ("manifest", "expanded"),
        ("model", {"isotropic_raw_gain": 1}),
        ("extra_option", True),
    ],
)
def test_reject_recipe_drift(script, key, value):
    first = recipe()
    second = {**copy.deepcopy(first), "run": "isolated", key: value}
    with pytest.raises(AssertionError):
        script.same_recipe(first, second)


def test_input_guard_rejects_changed_parent_bytes(script, tmp_path):
    path = tmp_path / "parent"
    path.write_bytes(b"original")
    plan = {"inputs": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()}, "guards": {}}
    script.guard(plan)
    path.write_bytes(b"changed")
    with pytest.raises(AssertionError):
        script.guard(plan)


def logs(tmp_path):
    original = tmp_path / "original.jsonl"
    original.write_text(
        "".join(
            json.dumps(
                {
                    "event": "train",
                    "step": step,
                    "domain": "synthetic",
                    "batch_sha256": format(step, "064x"),
                }
            )
            + "\n"
            for step in [1, *range(25, 40001, 25), 8001]
        )
    )
    rows = []
    for step in [1, 13, *range(25, 2001, 25), 2001, *range(2025, 10001, 25)]:
        progress = max(0, step - 500) / (40000 - 500)
        groups = [
            {
                "data_step": data_step,
                "domain": "commons",
                "examples": 4,
                "batch_sha256": format(data_step, "064x"),
            }
            for data_step in range(4 * step - 3, 4 * step + 1)
        ]
        rows.append(
            {
                "event": "train",
                "step": step,
                "lr": 2e-4
                * min(1, step / 500)
                * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2),
                "source_groups": groups,
                "example_draws": step * 16,
                "batch_sha256": format(step, "064x"),
            }
        )
    prefix = tmp_path / "prefix.jsonl"
    prefix.write_text("".join(json.dumps(row) + "\n" for row in rows[:82]))
    arms = []
    for name in ("no-dino", "dino"):
        run = tmp_path / name
        run.mkdir()
        (run / "metrics.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
        arms.append({"run": str(run), "prefix_metrics": {"path": str(prefix)}})
    return {"arms": arms, "original_metrics": {"path": str(original)}}


def test_full_403_row_source_accounting(script, tmp_path):
    result = script.audit_logs(logs(tmp_path))
    assert result["logged_macro_rows_per_arm"] == 403
    assert result["original_source_overlaps_per_arm"] == [403, 403]


@pytest.mark.parametrize("field", ["lr", "source_groups"])
def test_final_audit_rejects_resumed_drift(script, tmp_path, field):
    plan = logs(tmp_path)
    path = Path(plan["arms"][1]["run"]) / "metrics.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    if field == "lr":
        rows[82][field] *= 2
    else:
        rows[82][field][0]["batch_sha256"] = "0" * 64
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    with pytest.raises(AssertionError):
        script.audit_logs(plan)
