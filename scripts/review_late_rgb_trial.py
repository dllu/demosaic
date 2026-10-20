"""Bind unchanged quality panels to the genuine V90/V91 original4000 states."""

import argparse
import math
import shutil
from pathlib import Path

import psutil
import review_directional_bank as panels
from train_directional_bank_trial import guard, read, ref, save

TERMINAL = "completed-late-rgb-original4000-awaiting-full-quality-and-native-review"
ENGINEERING_TERMINAL = "completed-late-rgb-engineering-preflight"
BOUNDARY = "independently-verified-late-RGB-original4000-boundaries"
ENGINEERING_BOUNDARY = "independently-verified-late-RGB-engineering-boundaries"


def scheduled_learning_rate(step):
    progress = max(0, step - 100) / 3900
    return 1e-5 * min(1, step / 100) * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)


def require_completed(plan):
    status = read(plan["training_status"])
    engineering = plan.get("engineering_preflight", False)
    if status["status"] != (ENGINEERING_TERMINAL if engineering else TERMINAL):
        raise RuntimeError("Both fixed late RGB budgets must complete before review")
    assert status["controller"] == plan["training_owner"]
    assert not panels.alive(status["controller"]) and not panels.alive(status["child"])
    assert status["plan"] == plan["training_plan"] == ref(plan["training_plan"]["path"])
    training = read(plan["training_plan"]["path"])
    assert training["engineering_only"] is engineering and training["planned_updates"] == 4000
    assert training["boundary_updates"] == (16 if engineering else 4000)
    assert (
        training["training_photo_sources"],
        training["native_captures"],
        training["native_groups"],
        training["paired_scenes"],
    ) == (88508, 128, 106, 32)
    assert [(a["name"], a["late_rgb_mode"]) for a in training["arms"][:2]] == [
        ("control", "global"),
        ("spatial", "spatial"),
    ]
    assert not training.get("resume"), "A recovery requires its own explicit provenance adapter"
    assert status["matched_observations_and_final_RNG"] and status["source_archives_exact"]
    if engineering:
        assert status["restart_full_model_EMA_AdamW_RNG_exact"]
    else:
        assert training["device"] == "cuda"
        assert set(training["fresh_process_restart_preflights"]) == {"cpu", "cuda"}
        for proof in training["fresh_process_restart_preflights"].values():
            assert ref(proof["status"]["path"]) == proof["status"]
            certificate = read(proof["status"]["path"])
            assert certificate["plan"] == proof["plan"] == ref(proof["plan"]["path"])
            assert certificate["status"] == "completed-genuine-fresh-process-late-RGB-restart-audit"
            assert (
                certificate["exact_final_model_EMA_AdamW_RNG"]
                and certificate["matched_all16_observations"]
            )
            assert not panels.alive(certificate["controller"]) and not panels.alive(
                certificate["child"]
            )
    guard(training)
    return status, training


def boundaries(plan):
    import torch
    import yaml
    from audit_flat_palette import identical, train_rows

    from demosaic.late_rgb import LateRgbRefinement
    from demosaic.model import ModelConfig

    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    status, training = require_completed(plan)
    engineering, step = plan.get("engineering_preflight", False), training["boundary_updates"]
    parent = torch.load(
        training["parent"]["path"], weights_only=True, map_location="cpu", mmap=True
    )
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    core = {
        p.name: ref(p)["sha256"] for p in (Path(training["work"]) / "src/demosaic").glob("*.py")
    }
    assert len(core) == 47 and "late_rgb.py" in core
    checkpoints, evidence, cases, states, configs, observations, logs = [], [], [], [], [], [], []
    for index, arm in enumerate(training["arms"][:2]):
        item = status["completed"][arm["name"]]
        assert ref(item["path"]) == item
        case = read(item["path"])
        assert case["arm"] == arm["name"] and not panels.alive(case["owner"])
        assert case["actual_step"] == step and case["planned_steps"] == 4000
        assert case["engineering_only"] is engineering and case["resume"] is None
        checkpoint = case["checkpoint"]
        assert ref(checkpoint["path"]) == checkpoint
        state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        native, batch = (64, 1) if training["device"] == "cpu" else (256, 16)
        assert (cfg["patch_size"], cfg["validation_patch_size"], cfg["batch_size"]) == (
            native,
            native,
            batch,
        )
        assert state["step"] == step and state["config"]["steps"] == 4000
        assert cfg["seed"] == 55 and cfg["warmup_steps"] == 100 and cfg["lr"] == 1e-5
        assert cfg["late_rgb_lr_multiplier"] == 20
        for key, value in cfg.items():
            if key != "validation_protocol":
                assert state["config"][key] == value, key
        assert state["config"]["initialized_from"] == {**training["parent"], "step": 20000}
        assert cfg["manifest"] == training["training_manifest"]["path"]
        expected = ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
        expected["late_rgb_refinement"] = arm["late_rgb_mode"]
        assert ModelConfig.from_checkpoint(state["model_config"]).to_dict() == expected
        assert state["config"]["camera_supervision"] == "sensor-valid-v1"
        assert state["config"]["training_execution"] == "deterministic-v1"
        assert state["config"]["training_execution_runtime"]["deterministic_algorithms"]
        with torch.random.fork_rng(devices=[]):
            head = LateRgbRefinement((96, 192, 384, 768), arm["late_rgb_mode"])
        assert sum(p.numel() for p in head.parameters()) == 100547
        additions = {
            "pretrained_rgb.rgb_refinement." + key: value.shape
            for key, value in head.state_dict().items()
        }
        assert len(additions) == 24
        unchanged = {}
        for field in ["model", "ema"]:
            assert set(state[field]) == set(parent["ema"]) | set(additions)
            assert len(state[field]) == 115 and all(
                torch.isfinite(v).all() for v in state[field].values()
            )
            assert all(state[field][k].shape == shape for k, shape in additions.items())
            assert all(state[field][k].dtype == value.dtype for k, value in parent["ema"].items())
            assert all(state[field][k].dtype == torch.float32 for k in additions)
            unchanged[field] = sorted(
                k
                for k, v in state[field].items()
                if k in parent["ema"] and torch.equal(v, parent["ema"][k])
            )
            assert all(
                torch.equal(state[field][k], parent["ema"][k])
                for k in ["context.mean", "context.std"]
            )
            assert state[field]["pretrained_rgb.rgb_refinement.output.weight"].count_nonzero()
            assert any(
                state[field][
                    f"pretrained_rgb.rgb_refinement.modulations.{i}.weight"
                ].count_nonzero()
                for i in range(4)
            )
        assert len(state["optimizer"]["state"]) == 113
        for values in state["optimizer"]["state"].values():
            assert int(values["step"]) == step and values["exp_avg_sq"].min() >= 0
            assert all(torch.isfinite(v).all() for v in values.values() if torch.is_tensor(v))
        groups = state["optimizer"]["param_groups"]
        assert [g.get("lr_multiplier", 1) for g in groups] == [1, 20]
        assert [len(g["params"]) for g in groups] == [89, 24]
        assert groups[1]["lr"] == groups[0]["lr"] * 20
        retained = first1000 = None
        if not engineering:
            retained = ref(Path(checkpoint["path"]).with_name("step-004000.pt"))
            assert retained["sha256"] == checkpoint["sha256"]
            first1000 = ref(Path(checkpoint["path"]).with_name("step-001000.pt"))
            assert groups[0]["lr"] == cfg["lr"] * 0.1
        for key in [
            "manifest",
            "validation_manifest",
            "paired_manifest",
            "raw_clean_manifest",
            "validation_protocol",
        ]:
            assert state["config"][key + "_sha256"] == ref(cfg[key])["sha256"]
        assert case["initializations"] == ref(case["initializations"]["path"])
        assert (
            case["captures"] == read(case["initializations"]["path"]) and len(case["captures"]) == 1
        )
        capture = case["captures"][0]
        assert (
            capture["common_initial_state_exact"]
            and capture["DINO_sha256"] == training["DINO_sha256"]
        )
        assert capture["initial_output_exact_parent"] and not capture["resuming"]
        assert (capture["new_head_tensors"], capture["new_head_parameters"]) == (24, 100547)
        assert case["source_sha256"] == state["config"]["source_sha256"]
        archive = Path(case["source_snapshot"])
        assert {p.name for p in archive.glob("*.py")} == set(core)
        assert all(ref(archive / name)["sha256"] == digest for name, digest in core.items())
        assert ref(case["metrics"]["path"]) == case["metrics"]
        rows = train_rows(Path(checkpoint["path"]).parent)
        assert rows == case["logged_observations"]
        assert [r["step"] for r in rows] == (
            list(range(1, 17)) if engineering else [1, *range(25, 4001, 25)]
        )
        assert ref(case["observations"]["path"]) == case["observations"]
        samples = read(case["observations"]["path"])
        assert [r["step"] for r in samples] == (
            list(range(1, 17)) if engineering else [*range(1, 17), *range(25, 4001, 25)]
        )
        assert all(
            r["actual_forward_sha256"] == r["expected_forward_sha256"]
            and r["source_sha256"] == r["actual_loss_sha256"]
            for r in samples
        )
        by_step = {r["step"]: r for r in samples}
        for row in rows:
            lr = scheduled_learning_rate(row["step"])
            assert (
                row["lr"] == lr and math.isfinite(row["loss"]) and math.isfinite(row["grad_norm"])
            )
            assert row["batch_sha256"] == by_step[row["step"]]["source_sha256"]
            assert row["context_supervision_sha256"] == by_step[row["step"]]["actual_loss_sha256"]
            assert (
                row["context_source_size"],
                row["context_forward_size"],
                row["context_loss_size"],
            ) == (native,) * 3
        checkpoints.append(
            {
                **checkpoint,
                "arm": arm["name"],
                "step": step,
                "kind": "joint-checkpoint",
                "label": f"V{90 + index}-engineering-check16"
                if engineering
                else f"V{90 + index}-original4000",
            }
        )
        evidence.append(
            {
                "result": item,
                "initializations": case["initializations"],
                "captures": case["captures"],
                "retained": retained,
                "retained1000": first1000,
                "finite_states": [115, 115, 113],
                "new_head_shapes_exact": additions.keys()
                == {k for k in state["model"] if k.startswith("pretrained_rgb.rgb_refinement.")},
                "unchanged_from_parent_EMA": unchanged,
                "actual_training_package_files_exact": 47,
            }
        )
        cases.append(case)
        states.append(state)
        configs.append(cfg)
        observations.append(samples)
        logs.append(rows)
    assert configs[0].keys() == configs[1].keys()
    assert {k for k in configs[0] if configs[0][k] != configs[1][k]} == {"run", "model"}
    assert {k for k in configs[0]["model"] if configs[0]["model"][k] != configs[1]["model"][k]} == {
        "late_rgb_refinement"
    }
    for key in ["initial_model_sha256", "first_gradient_sha256_zero_sign_canonicalized"]:
        assert cases[0]["captures"][0][key] == cases[1]["captures"][0][key]
    assert observations[0] == observations[1] and len(observations[0]) == status["recorded_pairs"]
    for first, second in zip(*logs, strict=True):
        assert all(
            first[k] == second[k]
            for k in ["step", "domain", "lr", "batch_sha256", "context_supervision_sha256"]
        )
    for key in ["python_rng", "torch_rng", "cuda_rng"]:
        identical(states[0][key], states[1][key])
    assert cases[0]["source_sha256"] == cases[1]["source_sha256"]
    save(
        Path(plan["root"]) / "training-boundary.json",
        {
            "status": ENGINEERING_BOUNDARY if engineering else BOUNDARY,
            "engineering_preflight": engineering,
            "training_geometry": {
                "device": training["device"],
                "native_size": native,
                "batch_size": batch,
            },
            "training_status": ref(plan["training_status"]),
            "checkpoints": checkpoints,
            "evidence": evidence,
            "paired_observation_audit": {
                "recorded_pairs": len(observations[0]),
                "all_actual_source_forward_loss_pairs_exact": True,
            },
            "logged_source_domain_LR_pairs": len(logs[0]),
            "final_Python_CPU_CUDA_RNG_exact": True,
            "archived_source_and_data_exact": True,
            "scope": "Independent full-state/source/horizon/RNG audit only. Engineering states cannot enter quality panels. No quality, extension or promotion claim.",
        },
    )


def run(plan_path, stage=None):
    plan = read(plan_path)
    if plan.get("engineering_preflight", False) and stage != "boundary":
        raise ValueError("Discarded engineering checkpoints cannot produce quality evidence")
    if stage is not None:
        assert psutil.virtual_memory().available > 24 * 2**30
        assert shutil.disk_usage(plan["root"]).free > 500 * 2**30
        assert shutil.disk_usage("/home/dllu/proj/demosaic").free > 64 * 2**30
    panels.require_completed = require_completed
    panels.boundaries = boundaries
    if stage is None:
        panels.controller(plan_path)
    else:
        panels.worker(plan_path, stage)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "worker"])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--stage")
    args = parser.parse_args()
    if args.mode == "worker" and args.stage is None:
        parser.error("worker requires --stage")
    run(args.plan.resolve(), args.stage if args.mode == "worker" else None)
