"""Audit V92 head-only training and run unchanged panels against historical V90."""

import argparse
import math
import shutil
from pathlib import Path

import psutil
import review_directional_bank as panels
from review_late_rgb_trial import scheduled_learning_rate
from train_directional_bank_trial import guard, read, ref, save

TERMINAL = "completed-original4000-head-only-awaiting-full-quality-and-native-review"
ENGINEERING_TERMINAL = "completed-genuine-head-only16-and-fresh-process8plus8"
BOUNDARY = "independently-verified-V92-and-historical-V90-original4000-boundaries"
ENGINEERING_BOUNDARY = "independently-verified-head-only-and-historical-engineering-boundaries"
LABELS = ["V90-historical-original4000", "V92-head-only-original4000"]


def require_completed(plan):
    engineering = plan.get("engineering_preflight", False)
    status = read(plan["training_status"])
    if status["status"] != (ENGINEERING_TERMINAL if engineering else TERMINAL):
        raise RuntimeError("Fixed head-only training must complete before quality review")
    assert status["controller"] == plan["training_owner"]
    assert not panels.alive(status["controller"]) and not panels.alive(status["child"])
    assert status["plan"] == plan["training_plan"] == ref(plan["training_plan"]["path"])
    training = read(plan["training_plan"]["path"])
    assert training["engineering_only"] is engineering
    assert training["boundary_updates"] == (16 if engineering else 4000)
    assert training["planned_updates"] == 4000 and training["late_rgb_only"] is True
    assert len(training["arms"]) == 1 and training["arms"][0]["late_rgb_mode"] == "global"
    assert not training.get("resume")
    assert engineering or training["device"] == "cuda"
    assert status["exact_common_model_and_EMA"] and status["matched_original_inputs_LRs_and_RNG"]
    if engineering:
        assert status["fresh_process_all_state_exact"]
    guard(training)
    return status, training


def same_bits(a, b):
    import torch

    assert a.shape == b.shape and a.dtype == b.dtype
    return torch.equal(
        a.detach().cpu().contiguous().reshape(-1).view(torch.uint8),
        b.detach().cpu().contiguous().reshape(-1).view(torch.uint8),
    )


def inspect_case(case_ref, config_path, training, *, head_only, step, engineering):
    import torch
    import yaml
    from audit_flat_palette import train_rows

    from demosaic.late_rgb import LateRgbRefinement
    from demosaic.model import ModelConfig

    assert ref(case_ref["path"]) == case_ref
    case = read(case_ref["path"])
    assert not panels.alive(case["owner"]) and case["resume"] is None
    assert case["actual_step"] == step and case["planned_steps"] == 4000
    assert case["engineering_only"] is engineering
    checkpoint = case["checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
    parent = torch.load(
        training["parent"]["path"], weights_only=True, map_location="cpu", mmap=True
    )
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    cfg = yaml.safe_load(Path(config_path).read_text())
    native, batch = (64, 1) if training["device"] == "cpu" else (256, 16)
    assert (cfg["patch_size"], cfg["validation_patch_size"], cfg["batch_size"]) == (
        native,
        native,
        batch,
    )
    assert cfg.get("late_rgb_only", False) is head_only
    assert state["config"].get("late_rgb_only", False) is head_only
    assert state["step"] == step and state["config"]["steps"] == 4000
    assert (cfg["seed"], cfg["warmup_steps"], cfg["lr"], cfg["late_rgb_lr_multiplier"]) == (
        55,
        100,
        1e-5,
        20,
    )
    for key, value in cfg.items():
        if key != "validation_protocol":
            assert state["config"][key] == value, key
    assert state["config"]["initialized_from"] == {**training["parent"], "step": 20000}
    expected = ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
    expected["late_rgb_refinement"] = "global"
    assert ModelConfig.from_checkpoint(state["model_config"]).to_dict() == expected
    assert state["config"]["camera_supervision"] == "sensor-valid-v1"
    assert state["config"]["training_execution"] == "deterministic-v1"
    assert state["config"]["training_execution_runtime"]["deterministic_algorithms"]
    with torch.random.fork_rng(devices=[]):
        head = LateRgbRefinement((96, 192, 384, 768), "global")
    assert sum(p.numel() for p in head.parameters()) == 100547
    additions = {
        "pretrained_rgb.rgb_refinement." + k: v.shape for k, v in head.state_dict().items()
    }
    assert len(additions) == 24
    for field in ["model", "ema"]:
        assert set(state[field]) == set(parent["ema"]) | additions.keys()
        assert len(state[field]) == 115 and all(
            torch.isfinite(v).all() for v in state[field].values()
        )
        assert all(
            state[field][k].shape == shape and state[field][k].dtype == torch.float32
            for k, shape in additions.items()
        )
        if head_only:
            assert all(same_bits(state[field][k], v) for k, v in parent["ema"].items())
        assert state[field]["pretrained_rgb.rgb_refinement.output.weight"].count_nonzero()
        assert any(
            state[field][f"pretrained_rgb.rgb_refinement.modulations.{i}.weight"].count_nonzero()
            for i in range(4)
        )
    opt = state["optimizer"]
    assert len(opt["state"]) == (24 if head_only else 113)
    assert [len(g["params"]) for g in opt["param_groups"]] == ([0, 24] if head_only else [89, 24])
    assert [g["lr_multiplier"] for g in opt["param_groups"]] == [1, 20]
    assert opt["param_groups"][1]["lr"] == opt["param_groups"][0]["lr"] * 20
    for values in opt["state"].values():
        assert int(values["step"]) == step and values["exp_avg_sq"].min() >= 0
        assert all(torch.isfinite(v).all() for v in values.values() if torch.is_tensor(v))
    for parameter_id, shape in zip(
        opt["param_groups"][1]["params"], additions.values(), strict=True
    ):
        assert opt["state"][parameter_id]["exp_avg"].shape == shape
        assert opt["state"][parameter_id]["exp_avg_sq"].shape == shape
    retained = first1000 = None
    if not engineering:
        retained = ref(Path(checkpoint["path"]).with_name("step-004000.pt"))
        first1000 = ref(Path(checkpoint["path"]).with_name("step-001000.pt"))
        assert retained["sha256"] == checkpoint["sha256"]
        assert opt["param_groups"][0]["lr"] == cfg["lr"] * 0.1
    for key in [
        "manifest",
        "validation_manifest",
        "paired_manifest",
        "raw_clean_manifest",
        "validation_protocol",
    ]:
        assert state["config"][key + "_sha256"] == ref(cfg[key])["sha256"]
    assert cfg["manifest"] == training["training_manifest"]["path"]
    capture = case["captures"][0]
    assert case["captures"] == read(case["initializations"]["path"]) and len(case["captures"]) == 1
    assert ref(case["initializations"]["path"]) == case["initializations"]
    assert capture["common_initial_state_exact"] and capture["initial_output_exact_parent"]
    assert capture["DINO_sha256"] == training["DINO_sha256"] and not capture["resuming"]
    assert (capture["new_head_tensors"], capture["new_head_parameters"]) == (24, 100547)
    if head_only:
        assert (
            capture["late_rgb_only"]
            and case["common_model_and_EMA_exact_parent"]
            and case["common_backward_absent"]
        )
    assert case["source_sha256"] == state["config"]["source_sha256"]
    archive = Path(case["source_snapshot"])
    core = {p.name: ref(p)["sha256"] for p in archive.glob("*.py")}
    assert len(core) == 47
    assert ref(case["metrics"]["path"]) == case["metrics"]
    logs = train_rows(Path(checkpoint["path"]).parent)
    assert logs == case["logged_observations"]
    assert [r["step"] for r in logs] == (
        list(range(1, 17)) if engineering else [1, *range(25, 4001, 25)]
    )
    assert ref(case["observations"]["path"]) == case["observations"]
    observations = read(case["observations"]["path"])
    assert [r["step"] for r in observations] == (
        list(range(1, 17)) if engineering else [*range(1, 17), *range(25, 4001, 25)]
    )
    assert all(
        r["actual_forward_sha256"] == r["expected_forward_sha256"]
        and r["source_sha256"] == r["actual_loss_sha256"]
        for r in observations
    )
    by_step = {r["step"]: r for r in observations}
    for row in logs:
        assert row["lr"] == scheduled_learning_rate(row["step"])
        assert math.isfinite(row["loss"]) and math.isfinite(row["grad_norm"])
        assert row["batch_sha256"] == by_step[row["step"]]["source_sha256"]
        assert row["context_supervision_sha256"] == by_step[row["step"]]["actual_loss_sha256"]
        assert (
            row["context_source_size"],
            row["context_forward_size"],
            row["context_loss_size"],
        ) == (native,) * 3
    return (
        case,
        state,
        cfg,
        observations,
        logs,
        core,
        {
            "result": case_ref,
            "checkpoint": checkpoint,
            "retained4000": retained,
            "retained1000": first1000,
            "finite_states": [115, 115, len(opt["state"])],
            "head_only": head_only,
            "common_model_and_EMA_byte_exact_V63": head_only,
            "source_archive": str(archive),
        },
    )


def boundaries(plan):
    import torch
    from audit_flat_palette import identical

    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    status, training = require_completed(plan)
    engineering, step = training["engineering_only"], training["boundary_updates"]
    old_ref = training["historical_preflight" if engineering else "historical_control"]
    old_case = read(old_ref["path"])
    # Historical config is the archived trainer-written config beside its weights.
    old_config = Path(old_case["checkpoint"]["path"]).parent / "config.yaml"
    new_config = training["arms"][0]["config"]
    records = [
        inspect_case(
            old_ref, old_config, training, head_only=False, step=step, engineering=engineering
        ),
        inspect_case(
            status["result"],
            new_config,
            training,
            head_only=True,
            step=step,
            engineering=engineering,
        ),
    ]
    first, second = records
    assert first[2]["model"] == second[2]["model"]
    ignored = {"late_rgb_only", "run", "experiment_notes", "validation_protocol"}
    # Trainer-written historical configs also contain derived provenance fields.
    for key, value in second[2].items():
        if key not in ignored:
            assert first[2][key] == value, key
    assert first[3] == second[3]
    for a, b in zip(first[4], second[4], strict=True):
        assert all(
            a[k] == b[k]
            for k in ["step", "domain", "lr", "batch_sha256", "context_supervision_sha256"]
        )
    for key in ["python_rng", "torch_rng", "cuda_rng"]:
        identical(first[1][key], second[1][key])
    assert (
        first[0]["captures"][0]["initial_model_sha256"]
        == second[0]["captures"][0]["initial_model_sha256"]
    )
    assert first[5].keys() == second[5].keys()
    differences = [name for name in sorted(first[5]) if first[5][name] != second[5][name]]
    assert differences == ["train.py"]
    actual = {
        p.name: ref(p)["sha256"] for p in (Path(training["work"]) / "src/demosaic").glob("*.py")
    }
    assert second[5] == actual
    checkpoints = [
        {
            **r[6]["checkpoint"],
            "arm": arm,
            "step": step,
            "kind": "joint-checkpoint",
            "label": label if not engineering else label + ":engineering16",
        }
        for r, arm, label in zip(records, ["historical", "head-only"], LABELS, strict=True)
    ]
    if not engineering:
        previous_boundary = read(plan["historical_boundary"]["path"])
        assert ref(plan["historical_boundary"]["path"]) == plan["historical_boundary"]
        assert previous_boundary["checkpoints"][0]["sha256"] == checkpoints[0]["sha256"]
    save(
        Path(plan["root"]) / "training-boundary.json",
        {
            "status": ENGINEERING_BOUNDARY if engineering else BOUNDARY,
            "engineering_preflight": engineering,
            "training_status": ref(plan["training_status"]),
            "checkpoints": checkpoints,
            "evidence": [r[6] for r in records],
            "recorded_observation_pairs": len(first[3]),
            "logged_source_domain_LR_pairs": len(first[4]),
            "final_Python_CPU_CUDA_RNG_exact": True,
            "inference_modules_byte_identical": 46,
            "training_module_differences": differences,
            "comparison": "Exploratory V92 against fixed historical V90, not independent two-arm randomization.",
            "scope": "Boundary/source/data/horizon/state proof only; no quality or promotion claim.",
        },
    )


def run(plan_path, stage=None):
    plan = read(plan_path)
    if plan.get("engineering_preflight", False) and stage != "boundary":
        raise ValueError("Discarded engineering checkpoints cannot produce quality evidence")
    if stage is not None:
        assert psutil.virtual_memory().available > 24 * 2**30
        assert shutil.disk_usage("/mnt/external").free > 500 * 2**30
        assert shutil.disk_usage("/home/dllu/proj/demosaic").free > 64 * 2**30
    panels.require_completed, panels.boundaries = require_completed, boundaries
    if stage is None:
        panels.controller(plan_path)
    elif stage == "highlights":
        from evaluate_gfx_highlight_inputs import main

        guard(plan)
        require_completed(plan)
        root = Path(plan["root"])
        with (root / (stage + ".claim")).open("x") as stream:
            stream.write(str(psutil.Process().pid))
        checkpoints = read(root / "training-boundary.json")["checkpoints"] + [
            {**plan["parent"], "label": "V63-parent"}
        ]
        main(
            Path(plan["highlight_inputs"]["path"]),
            Path(plan["highlight_audit"]["path"]),
            [Path(c["path"]) for c in checkpoints],
            Path(plan["outputs"][stage]),
            checkpoint_labels={c["sha256"]: c["label"] for c in checkpoints},
        )
        guard(plan)
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
