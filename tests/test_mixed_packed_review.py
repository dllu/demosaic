import copy
import hashlib
import importlib.util
import json
import math
import os
import sys
from pathlib import Path

import psutil
import pytest
import torch

from demosaic.model import ModelConfig
from demosaic.train import training_domain


@pytest.fixture(scope="module")
def script():
    path = Path("scripts/review_mixed_packed_trial.py")
    spec = importlib.util.spec_from_file_location("mixed_review", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def state_fixture():
    config = {
        "steps": 40000,
        "batch_size": 4,
        "optimizer_batch_groups": 4,
        "optimizer_forward_groups": 1,
        "precision": "float32",
        "warmup_steps": 500,
        "ema_decay": 0.999**4,
        "lr": 2e-4,
        "seed": 51,
        "channels_last": True,
        "data_seed_per_step": True,
        "paired_fraction": 0.25,
        "raw_clean_fraction": 0.25,
        "source_sha256": "source",
        "manifest_sha256": "manifest",
    }
    model = ModelConfig(
        dino=False,
        restoration_backbone="packed-isotropic",
        isotropic_raw_gain=32,
        isotropic_residual_scale=1 / 32,
    ).to_dict()
    recipe = {**copy.deepcopy(config), "model": model}
    state = {
        "step": 12,
        "data_step": 48,
        "example_draws": 192,
        "config": config,
        "model_config": model,
        "model": {"v": torch.ones(1)},
        "ema": {"v": torch.ones(1)},
        "optimizer": {
            "state": {i: {"step": torch.tensor(12), "exp_avg": torch.ones(1)} for i in range(852)}
        },
        "torch_rng": torch.tensor([1]),
        "python_rng": (),
        "cuda_rng": [torch.tensor([1])],
    }
    return state, recipe, {"manifest_hashes": {"manifest_sha256": "manifest"}}


def test_prefix_state_accepts_the_recorded_example_units(script):
    state, recipe, plan = state_fixture()
    script.check_state(state, recipe, plan, 12, "source")


@pytest.mark.parametrize(
    "problem",
    [
        "step",
        "data_step",
        "example_draws",
        "initializer",
        "schedule",
        "precision",
        "grouping",
        "EMA",
        "source",
        "manifest",
        "Adam_step",
        "Adam_nonfinite",
        "EMA_nonfinite",
        "RNG",
        "units",
    ],
)
def test_boundary_rejects_recipe_counter_resume_and_finiteness_errors(script, problem):
    state, recipe, plan = state_fixture()
    if problem in ["step", "data_step", "example_draws"]:
        state[problem] += 1
    elif problem == "initializer":
        state["config"]["initialized_from"] = {"sha256": "diagnostic"}
    elif problem in ["schedule", "precision", "grouping", "EMA", "source", "manifest"]:
        key, value = {
            "schedule": ("steps", 2000),
            "precision": ("precision", "float16"),
            "grouping": ("optimizer_forward_groups", 4),
            "EMA": ("ema_decay", 0.999),
            "source": ("source_sha256", "other"),
            "manifest": ("manifest_sha256", "other"),
        }[problem]
        state["config"][key] = value
    elif problem == "Adam_step":
        state["optimizer"]["state"][0]["step"] = torch.tensor(11)
    elif problem == "Adam_nonfinite":
        state["optimizer"]["state"][0]["exp_avg"][:] = float("nan")
    elif problem == "EMA_nonfinite":
        state["ema"]["v"][:] = float("inf")
    elif problem == "RNG":
        del state["cuda_rng"]
    elif problem == "units":
        state["model_config"] = {**state["model_config"], "isotropic_raw_gain": 1}
    with pytest.raises((AssertionError, KeyError)):
        script.check_state(state, recipe, plan, 12, "source")


def observations():
    records = []
    for step in [1, 13, *range(25, 2001, 25)]:
        warm, progress = min(1, step / 500), max(0, step - 500) / 39500
        records.append(
            {
                "step": step,
                "data_step_start": 4 * step - 3,
                "data_step_end": 4 * step,
                "example_draws": 16 * step,
                "effective_batch_size": 16,
                "optimizer_batch_groups": 4,
                "optimizer_forward_groups": 1,
                "domain": "mixed",
                "loss": 0.01,
                "grad_norm": 0.1,
                "lr": 2e-4 * warm * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2),
                "source_groups": [
                    {
                        "data_step": n,
                        "domain": training_domain(n, 51, 0.25, 0.25),
                        "examples": 4,
                        "batch_sha256": "ab" * 32,
                    }
                    for n in range(4 * step - 3, 4 * step + 1)
                ],
            }
        )
    for row in records:
        row["batch_sha256"] = hashlib.sha256(
            json.dumps(row["source_groups"], sort_keys=True).encode()
        ).hexdigest()
    return records


def test_mixed_groups_use_original_data_steps_and_example_schedule(script):
    script.check_observations(observations())


def test_original_source_hash_comparison_is_bound_to_data_steps_and_domain(script):
    records = observations()
    domains = {"commons": "synthetic", "native": "native-RAW-synthetic", "paired": "paired-RAW"}
    original = [
        {
            "event": "train",
            "step": g["data_step"],
            "domain": domains[g["domain"]],
            "batch_sha256": g["batch_sha256"],
        }
        for row in records
        for g in row["source_groups"]
        if g["data_step"] == 1 or g["data_step"] % 25 == 0
    ]
    assert script.original_data_matches(records, original) == 82
    original[-1]["batch_sha256"] = "cd" * 32
    with pytest.raises(AssertionError):
        script.original_data_matches(records, original)


@pytest.mark.parametrize(
    "problem",
    [
        "missing_prefix",
        "duplicate",
        "data_gap",
        "wrong_domain",
        "partial_group",
        "short_schedule",
        "draws",
    ],
)
def test_training_observation_coverage_cannot_be_inferred_from_last_step(script, problem):
    records = observations()
    if problem == "missing_prefix":
        records.pop(1)
    elif problem == "duplicate":
        records.insert(0, records[0])
    elif problem == "data_gap":
        records[-1]["source_groups"][0]["data_step"] -= 1
    elif problem == "wrong_domain":
        records[-1]["source_groups"][0]["domain"] = "other"
    elif problem == "partial_group":
        records[-1]["source_groups"].pop()
    elif problem == "short_schedule":
        records[-1]["lr"] = 2e-5
    elif problem == "draws":
        records[-1]["example_draws"] = 8000
    with pytest.raises(AssertionError):
        script.check_observations(records)


def test_incomplete_or_still_live_training_cannot_release_inference(script, monkeypatch):
    monkeypatch.setattr(script, "read", lambda _: {"status": "running-mixed16-finish"})
    with pytest.raises(RuntimeError, match="must complete"):
        script.completed({"training_workflow": "unused"})
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    monkeypatch.setattr(script, "read", lambda _: {"status": script.TERMINAL, "controller": owner})
    with pytest.raises(AssertionError):
        script.completed({"training_workflow": "unused", "previous_owner": owner})
