"""Bind the unchanged full quality panels to genuine V86/V87 context endpoints."""

import argparse
import json
import math
from pathlib import Path

import review_directional_bank as panels
from train_context_trial import compare_observations
from train_directional_interval_trial import guard, read, ref, save, sha

TERMINAL = "completed-context-original4000-awaiting-full-quality-and-native-review"
ENGINEERING_TERMINAL = "completed-context-engineering-preflight"
BOUNDARY = "independently-verified-context-original4000-boundaries"
ENGINEERING_BOUNDARY = "independently-verified-context-engineering-boundaries"


def require_completed(plan):
    status = read(plan["training_status"])
    engineering = plan.get("engineering_preflight", False)
    if status["status"] != (ENGINEERING_TERMINAL if engineering else TERMINAL):
        raise RuntimeError("Both fixed context budgets must complete before review")
    assert status["controller"] == plan["training_owner"]
    assert not panels.alive(status["controller"]) and not panels.alive(status["child"])
    assert status["plan"] == plan["training_plan"] == ref(plan["training_plan"]["path"])
    training = read(plan["training_plan"]["path"])
    assert training["engineering_only"] is engineering
    assert training["planned_updates"] == 4000
    assert training["boundary_updates"] == (16 if engineering else 4000)
    source, loss, forwards = (
        (64, 32, [32, 64]) if training["device"] == "cpu" else (320, 256, [256, 320])
    )
    assert engineering or training["device"] == "cuda"
    assert (training["source_size"], training["loss_size"]) == (source, loss)
    assert [(a["name"], a["version"], a["forward_size"]) for a in training["arms"]] == [
        ("control", 86, forwards[0]),
        ("context", 87, forwards[1]),
    ]
    assert status["final_RNG_states_match"] and status["archived_source_and_data_exact"]
    assert status["logged_domains_LRs_and_supervision_match"]
    assert status["paired_observation_audit"]["all_source_and_supervision_pairs_exact"]
    assert status["paired_observation_audit"]["all_actual_forward_fields_differ"]
    guard(training)
    return status, training


def boundaries(plan):
    import torch
    import yaml
    from audit_flat_palette import identical

    from demosaic.model import ModelConfig
    from demosaic.training_context import TrainingContext

    status, training = require_completed(plan)
    engineering, step = plan.get("engineering_preflight", False), training["boundary_updates"]
    parent = torch.load(
        training["parent"]["path"], weights_only=True, map_location="cpu", mmap=True
    )
    assert parent["step"] == 20000
    core = {p.name: sha(p) for p in (Path(training["work"]) / "src/demosaic").glob("*.py")}
    assert len(core) == 45
    checkpoints, cases, states, configs, observations, logs, evidence = [], [], [], [], [], [], []
    for arm in training["arms"]:
        item = status["completed"][arm["name"]]
        assert ref(item["path"]) == item
        case = read(item["path"])
        assert case["arm"] == arm["name"] and not panels.alive(case["owner"])
        assert case["actual_step"] == step and case["planned_steps"] == 4000
        assert case["engineering_only"] is engineering
        checkpoint = case["checkpoint"]
        assert ref(checkpoint["path"]) == checkpoint
        retained = ref(Path(checkpoint["path"]).with_name(f"step-{step:06d}.pt"))
        assert retained["sha256"] == checkpoint["sha256"]
        state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        geometry = TrainingContext.from_config(cfg)
        assert (geometry.source_size, geometry.forward_size, geometry.loss_size) == (
            training["source_size"],
            arm["forward_size"],
            training["loss_size"],
        )
        assert state["step"] == step and state["config"]["steps"] == 4000
        assert cfg["seed"] == 54 and cfg["warmup_steps"] == 100 and cfg["lr"] == 1e-5
        for key, value in cfg.items():
            if key != "validation_protocol":
                assert state["config"][key] == value, key
        assert state["config"]["initialized_from"] == {**training["parent"], "step": 20000}
        assert ModelConfig.from_checkpoint(state["model_config"]).to_dict() == (
            ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
        )
        assert state["config"]["training_execution"] == "deterministic-v1"
        assert state["config"]["training_execution_runtime"]["deterministic_algorithms"] is True
        assert len(state["model"]) == len(state["ema"]) == 91
        assert len(state["optimizer"]["state"]) == 89
        unchanged = {}
        for field in ["model", "ema"]:
            assert all(torch.isfinite(v).all() for v in state[field].values())
            unchanged[field] = sorted(
                k for k, v in state[field].items() if torch.equal(v, parent["ema"][k])
            )
            assert len(unchanged[field]) < 91
        for values in state["optimizer"]["state"].values():
            assert int(values["step"]) == step
            assert all(torch.isfinite(v).all() for v in values.values() if torch.is_tensor(v))
            assert (values["exp_avg_sq"] >= 0).all()
        for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]:
            assert state["config"][key + "_sha256"] == sha(cfg[key])
        assert case["capture"]["initial_model_exact_parent_EMA"]
        assert case["capture"]["DINO_sha256"] == training["DINO_sha256"]
        assert case["source_sha256"] == state["config"]["source_sha256"]
        archive = Path(case["source_snapshot"])
        assert all(sha(archive / name) == digest for name, digest in core.items())
        assert case["metrics"] == ref(case["metrics"]["path"])
        rows = [
            json.loads(line)
            for line in Path(case["metrics"]["path"]).read_text().splitlines()
            if json.loads(line).get("event") == "train"
        ]
        assert rows == case["logged_observations"]
        assert [r["step"] for r in rows] == [1, *range(25, step + 1, 25)]
        assert ref(case["observations"]["path"]) == case["observations"]
        samples = read(case["observations"]["path"])
        assert [r["step"] for r in samples] == [*range(1, 17), *range(25, step + 1, 25)]
        by_step = {r["step"]: r for r in samples}
        assert all(r["forward_native_size"] == geometry.forward_size for r in samples)
        for row in rows:
            progress = max(0, row["step"] - 100) / 3900
            expected_lr = (
                1e-5
                * min(1, row["step"] / 100)
                * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
            )
            assert row["lr"] == expected_lr
            assert math.isfinite(row["loss"]) and math.isfinite(row["grad_norm"])
            assert (
                row["context_source_size"],
                row["context_forward_size"],
                row["context_loss_size"],
            ) == (geometry.source_size, geometry.forward_size, geometry.loss_size)
            assert row["batch_sha256"] == by_step[row["step"]]["source_batch_sha256"]
            assert (
                row["context_supervision_sha256"]
                == by_step[row["step"]]["actual_loss_batch_sha256"]
            )
        checkpoints.append(
            {
                **checkpoint,
                "arm": arm["name"],
                "step": step,
                "kind": "joint-checkpoint",
                "label": f"V{arm['version']}-engineering-check16"
                if engineering
                else f"V{arm['version']}-original4000",
            }
        )
        evidence.append(
            {
                "result": item,
                "initialization": case["capture"],
                "source_sha256": case["source_sha256"],
                "retained": retained,
                "finite_states": [91, 91, 89],
                "unchanged_from_parent_EMA": unchanged,
                "actual_training_package_files_exact": len(core),
            }
        )
        cases.append(case)
        states.append(state)
        configs.append(cfg)
        observations.append(samples)
        logs.append(rows)
    assert configs[0].keys() == configs[1].keys()
    assert {k for k in configs[0] if configs[0][k] != configs[1][k]} == {
        "run",
        "forward_patch_size",
    }
    assert cases[0]["capture"] == cases[1]["capture"]
    assert cases[0]["source_sha256"] == cases[1]["source_sha256"]
    observed = compare_observations(*observations)
    assert observed == status["paired_observation_audit"]
    for a, b in zip(*logs, strict=True):
        assert all(
            a[k] == b[k]
            for k in ["step", "domain", "lr", "batch_sha256", "context_supervision_sha256"]
        )
    for key in ["python_rng", "torch_rng", "cuda_rng"]:
        identical(states[0][key], states[1][key])
    archives = [
        {p.name: sha(p) for p in Path(c["source_snapshot"]).iterdir() if p.is_file()} for c in cases
    ]
    assert archives[0] == archives[1]
    save(
        Path(plan["root"]) / "training-boundary.json",
        {
            "status": ENGINEERING_BOUNDARY if engineering else BOUNDARY,
            "engineering_preflight": engineering,
            "training_geometry": {
                "device": training["device"],
                "source_size": training["source_size"],
                "loss_size": training["loss_size"],
                "forward_sizes": [a["forward_size"] for a in training["arms"]],
            },
            "training_status": ref(plan["training_status"]),
            "checkpoints": checkpoints,
            "paired_observation_audit": observed,
            "logged_source_core_domain_LR_pairs": len(logs[0]),
            "final_Python_CPU_CUDA_RNG_exact": True,
            "archived_source_and_data_exact": True,
            "evidence": evidence,
            "scope": "Independent fixed-horizon/source/core/RNG audit only; no quality or promotion claim.",
        },
    )


def install():
    panels.require_completed = require_completed
    panels.boundaries = boundaries


def run(plan_path, stage=None):
    engineering = read(plan_path).get("engineering_preflight", False)
    if engineering and stage != "boundary":
        raise ValueError("Discarded engineering checkpoints cannot produce quality evidence")
    install()
    if stage is None:
        panels.controller(plan_path)
    else:
        panels.worker(plan_path, stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "worker"])
    parser.add_argument("plan", type=Path)
    parser.add_argument(
        "--stage",
        choices=[
            "boundary",
            "known",
            "unseen",
            "full427",
            "statistics",
            "sensitivity",
            "gfx",
            "analytic",
            "hue",
            "highlights",
        ],
    )
    args = parser.parse_args()
    if args.mode == "worker" and args.stage is None:
        parser.error("worker requires --stage")
    run(args.plan.resolve(), args.stage if args.mode == "worker" else None)
