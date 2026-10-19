"""Bind the common full review to genuine native-data original20k checkpoints."""

import argparse
import json
import math
import os
import shutil
from pathlib import Path

import psutil
import review_directional_bank as panels
from train_directional_interval_trial import guard, read, ref, save, sha
from train_native_data_trial import compare_observations

TERMINAL = "completed-native-data-original20000-awaiting-full-quality-and-native-review"
ENGINEERING_TERMINAL = "completed-native-data-engineering-preflight"
BOUNDARY = "independently-verified-native-data-original20000-boundaries"


def require_completed(plan):
    status = read(plan["training_status"])
    engineering = plan.get("engineering_preflight", False)
    expected = ENGINEERING_TERMINAL if engineering else TERMINAL
    if status["status"] != expected:
        raise RuntimeError("Both original native-data budgets must complete before review")
    assert status["controller"] == plan["training_owner"]
    assert not panels.alive(status["controller"]) and not panels.alive(status["child"])
    assert status["plan"] == plan["training_plan"] == ref(plan["training_plan"]["path"])
    training = read(plan["training_plan"]["path"])
    assert training["engineering_only"] is engineering
    assert training["planned_updates"] == 20000
    assert training["boundary_updates"] == (16 if engineering else 20000)
    assert [
        (a["name"], a["version"], a["native_captures"], a["native_groups"])
        for a in training["arms"]
    ] == [("control", 84, 128, 106), ("expanded", 85, 150, 120)]
    assert status["final_RNG_states_match"] and status["logged_domains_LRs_match"]
    assert status["archived_source_differs_only_in_native_manifest"]
    if not engineering:
        assert status["paired_observation_audit"]["shared_pairs_exact"] > 0
        assert status["paired_observation_audit"]["native_pairs_changed"] > 0
    guard(training)
    return status, training


def boundaries(plan):
    import torch
    import yaml
    from audit_flat_palette import identical

    from demosaic.model import ModelConfig

    status, training = require_completed(plan)
    engineering = plan.get("engineering_preflight", False)
    step = training["boundary_updates"]
    parent = torch.load(
        training["parent"]["path"], weights_only=True, map_location="cpu", mmap=True
    )
    checkpoints, cases, states, configs, observations, logs = [], [], [], [], [], []
    for arm in training["arms"]:
        item = status["completed"][arm["name"]]
        assert ref(item["path"]) == item
        case = read(item["path"])
        assert case["arm"] == arm["name"] and not panels.alive(case["owner"])
        assert case["actual_step"] == step and case["planned_steps"] == 20000
        assert case["engineering_only"] is engineering
        checkpoint = case["checkpoint"]
        assert ref(checkpoint["path"]) == checkpoint
        state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        assert state["step"] == step and state["config"]["steps"] == 20000
        assert cfg["seed"] == 53 and cfg["warmup_steps"] == 200 and cfg["lr"] == 1e-5
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
        for field in ["model", "ema"]:
            assert all(torch.isfinite(v).all() for v in state[field].values())
            if not engineering:
                assert sorted(
                    k for k, v in state[field].items() if torch.equal(v, parent["ema"][k])
                ) == ["context.mean", "context.std"]
        for values in state["optimizer"]["state"].values():
            assert int(values["step"]) == step
            assert all(torch.isfinite(v).all() for v in values.values() if torch.is_tensor(v))
        for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]:
            assert state["config"][key + "_sha256"] == sha(cfg[key])
        assert ref(cfg["raw_clean_manifest"]) == arm["native_manifest"]
        assert case["capture"]["initial_EMA_exact"]
        assert case["capture"]["DINO_sha256"] == training["DINO_sha256"]
        assert case["metrics"] == ref(case["metrics"]["path"])
        rows = [
            json.loads(line)
            for line in Path(case["metrics"]["path"]).read_text().splitlines()
            if json.loads(line).get("event") == "train"
        ]
        assert rows == case["logged_observations"]
        assert [r["step"] for r in rows] == [1, *range(25, step + 1, 25)]
        for row in rows:
            progress = max(0, row["step"] - 200) / 19800
            expected_lr = (
                1e-5
                * min(1, row["step"] / 200)
                * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
            )
            assert row["lr"] == expected_lr
            assert math.isfinite(row["loss"]) and math.isfinite(row["grad_norm"])
        assert ref(case["observations"]["path"]) == case["observations"]
        samples = read(case["observations"]["path"])
        assert [r["step"] for r in samples] == [*range(1, 17), *range(25, step + 1, 25)]
        checkpoints.append(
            {
                **checkpoint,
                "arm": arm["name"],
                "step": step,
                "kind": "joint-checkpoint",
                "label": f"V{arm['version']}-CPU-or-CUDA-check16"
                if engineering
                else f"V{arm['version']}-original20000",
            }
        )
        cases.append(case)
        states.append(state)
        configs.append(cfg)
        observations.append(samples)
        logs.append(rows)
    assert {k for k in configs[0] if configs[0][k] != configs[1][k]} == {
        "raw_clean_manifest",
        "run",
    }
    assert cases[0]["capture"] == cases[1]["capture"]
    observed = compare_observations(*observations, require_native_change=not engineering)
    assert observed == status["paired_observation_audit"]
    for a, b in zip(*logs, strict=True):
        assert all(a[k] == b[k] for k in ["step", "domain", "lr"])
    for key in ["python_rng", "torch_rng", "cuda_rng"]:
        identical(states[0][key], states[1][key])
    archives = [
        {p.name: sha(p) for p in Path(c["source_snapshot"]).iterdir() if p.is_file()} for c in cases
    ]
    assert archives[0].keys() == archives[1].keys()
    assert {k for k in archives[0] if archives[0][k] != archives[1][k]} == {
        "raw-clean-manifest.json"
    }
    save(
        Path(plan["root"]) / "training-boundary.json",
        {
            "status": "independently-verified-native-data-engineering-boundaries"
            if engineering
            else BOUNDARY,
            "engineering_preflight": engineering,
            "training_status": ref(plan["training_status"]),
            "checkpoints": checkpoints,
            "paired_observation_audit": observed,
            "logged_domain_LR_pairs": len(logs[0]),
            "final_Python_CPU_CUDA_RNG_exact": True,
            "archived_source_differs_only_in_native_manifest": True,
            "evidence": [
                {
                    "result": status["completed"][c["arm"]],
                    "initialization": c["capture"],
                    "source_sha256": c["source_sha256"],
                    "finite_states": [91, 91, 89],
                }
                for c in cases
            ],
            "scope": "Independent original-horizon and matched-input boundary; no quality or promotion claim.",
        },
    )


def worker(plan_path, stage):
    if stage != "hue":
        return panels.worker(plan_path, stage)
    # The common hue worker binds original4000. Reuse its unchanged inference
    # function with this study's actual original20000 lineage instead.
    import torch
    from evaluate_color_grid_cuda import evaluate_records

    plan = read(plan_path)
    guard(plan)
    require_completed(plan)
    root = Path(plan["root"])
    with (root / "hue.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(root).free > 128 * 2**30
    torch.set_num_threads(4)
    device = torch.device("cuda", torch.cuda.current_device())
    torch.cuda.set_per_process_memory_fraction(
        min(
            torch.cuda.get_per_process_memory_fraction(device),
            24 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
        ),
        device,
    )
    torch.backends.cudnn.benchmark = False
    checkpoints = read(root / "training-boundary.json")["checkpoints"]
    records = [dict(c, kind="joint-checkpoint", arm=c["label"]) for c in checkpoints]
    records.append({**plan["parent"], "kind": "joint-checkpoint", "arm": "V63-parent"})
    evaluate_records(
        Path(plan["hue_inputs"]["path"]),
        Path(plan["training_status"]),
        Path(plan["outputs"]["hue"]),
        records,
        plan["parent"]["sha256"],
        expected_step=20000,
        precision="float32",
    )
    guard(plan)


def install():
    panels.require_completed = require_completed
    panels.boundaries = boundaries


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
    install()
    if args.mode == "controller":
        assert not read(args.plan).get("engineering_preflight", False)
        panels.controller(args.plan.resolve())
    else:
        assert not read(args.plan).get("engineering_preflight", False) or args.stage == "boundary"
        worker(args.plan.resolve(), args.stage)
