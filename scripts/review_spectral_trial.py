"""Bind unchanged full quality panels to genuine V88/V89 original4000 endpoints."""

import argparse
import ast
import math
from pathlib import Path

import review_directional_bank as panels
from train_directional_bank_trial import guard, read, ref, save

TERMINAL = "completed-spectral-original4000-awaiting-full-quality-and-native-review"
ENGINEERING_TERMINAL = "completed-spectral-engineering-preflight"
BOUNDARY = "independently-verified-spectral-original4000-boundaries"
ENGINEERING_BOUNDARY = "independently-verified-spectral-engineering-boundaries"


def canonical_training_rows(rows, *, engineering=False, resume_step=None):
    """Keep the additional real first-resume log and match shared scheduled rows."""
    expected = list(range(1, 17)) if engineering else [1, *range(25, 4001, 25)]
    extras = [] if resume_step is None or resume_step + 1 in expected else [resume_step + 1]
    assert [r["step"] for r in rows] == sorted(expected + extras)
    return [r for r in rows if r["step"] in expected], [r for r in rows if r["step"] in extras]


def require_completed(plan):
    status = read(plan["training_status"])
    engineering = plan.get("engineering_preflight", False)
    if status["status"] != (ENGINEERING_TERMINAL if engineering else TERMINAL):
        raise RuntimeError("Both fixed spectral budgets must complete before review")
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
    assert [(a["name"], a["spectral"]) for a in training["arms"][:2]] == [
        ("control", False),
        ("spectral", True),
    ]
    assert status["matched_observations_and_final_RNG"] and status["source_archives_exact"]
    if engineering:
        assert status["restart_full_model_EMA_AdamW_RNG_exact"]
    else:
        assert training["device"] == "cuda"
    guard(training)
    return status, training


def check_recovery(training, arm, case, samples, rows=None):
    """Verify explicit recovery provenance rather than claiming a fresh start."""
    resume = training.get("resume", {}).get(arm["name"])
    assert case.get("resume") == resume
    if resume is None:
        assert all(not c["resuming"] and c["initial_output_exact_parent"] for c in case["captures"])
        return None
    assert arm["name"] == "control" and resume["step"] == 1000
    handoff = read(training["handoff"]["path"])
    assert ref(training["handoff"]["path"]) == training["handoff"]
    assert handoff["status"] == "completed-verified-checkpoint-handoff-original-owners-exited"
    assert not panels.alive(handoff["controller"])
    assert all(not panels.alive(o) for o in handoff["training_owners"].values())
    assert handoff["training_plan"] == training["recovery_of"]
    assert (
        handoff["checkpoint"] == resume["checkpoint"]
        and handoff["observations"] == resume["observations"]
    )
    for item in [resume["checkpoint"], resume["observations"], handoff["metrics"]]:
        assert ref(item["path"]) == item
    prefix = read(resume["observations"]["path"])
    assert len(prefix) == 56 and samples[:56] == prefix
    assert all(c["resuming"] and not c["initial_output_exact_parent"] for c in case["captures"])
    assert training["arm_timeout_seconds"]["control"] < 14400
    assert training["planned_updates"] == training["boundary_updates"] == 4000
    resource = None
    if "resource_recovery_of" in training:
        previous = read(training["resource_recovery_of"]["path"])
        failure = read(training["previous_failure"]["path"])
        for item in [
            training["resource_recovery_of"],
            training["previous_failure"],
            training["resource_guard_addendum"],
        ]:
            assert ref(item["path"]) == item
        assert failure["status"] == "failed-spectral-trial-no-automatic-retry"
        assert not panels.alive(failure["controller"]) and not panels.alive(failure["child"])
        assert (
            previous["recovery_of"] == training["recovery_of"]
            and previous["resume"] == training["resume"]
        )
        assert training["root_disk_reserve_gib"] == 64
        consumed = math.ceil(failure["updated_unix"] - failure["child"]["created"])
        assert (
            training["arm_timeout_seconds"]["control"]
            == previous["arm_timeout_seconds"]["control"] - consumed
        )
        before, after = (
            ast.parse(Path(p["worker"]["path"]).read_text()) for p in [previous, training]
        )
        for name in ["worker", "retain_checkpoint", "prepare"]:
            a, b = (
                next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
                for tree in [before, after]
            )
            assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False)
        resource = check_replayed_work(training, samples, rows)
    return {
        "handoff": training["handoff"],
        "checkpoint": resume["checkpoint"],
        "preserved_observations": 56,
        "remaining_updates_at_handoff": 3000,
        "resource_recovery": resource,
        "scope": "Exact saved-model initialization at resumed forward; original startup assertions precede the preserved first update. No new direct measurement of the interrupted process's unsaved initial tensors is claimed.",
    }


def check_replayed_work(training, samples, rows):
    """All saved observations/losses of discarded work must replay exactly."""
    for key in ["discarded_observations", "discarded_metrics"]:
        assert ref(training[key]["path"]) == training[key]
    earlier = read(training["discarded_observations"]["path"])
    assert earlier and all(r["step"] > 1000 for r in earlier)
    current = {r["step"]: r for r in samples}
    assert all(current[r["step"]] == r for r in earlier)
    import json

    oldrows = [
        json.loads(line)
        for line in Path(training["discarded_metrics"]["path"]).read_text().splitlines()
    ]
    bystep = {r["step"]: r for r in rows}
    for row in oldrows:
        assert all(
            bystep[row["step"]][key] == row[key]
            for key in ["step", "domain", "lr", "batch_sha256", "loss", "grad_norm"]
        )
    return {
        "prior_failure": training.get("previous_failure"),
        "replayed_recorded_observations": len(earlier),
        "replayed_training_metric_rows": len(oldrows),
        "all_recorded_input_loss_gradient_values_exact": True,
    }


def boundaries(plan):
    import torch
    import yaml
    from audit_flat_palette import identical

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
    assert len(core) == 46
    checkpoints, cases, states, configs, observations, logs, evidence = [], [], [], [], [], [], []
    for index, arm in enumerate(training["arms"][:2]):
        item = status["completed"][arm["name"]]
        assert ref(item["path"]) == item
        case = read(item["path"])
        assert case["arm"] == arm["name"] and not panels.alive(case["owner"])
        assert case["actual_step"] == step and case["planned_steps"] == 4000
        assert case["engineering_only"] is engineering
        checkpoint = case["checkpoint"]
        assert ref(checkpoint["path"]) == checkpoint
        state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        native = 64 if training["device"] == "cpu" else 256
        assert (cfg["patch_size"], cfg["validation_patch_size"]) == (native, native)
        assert cfg["batch_size"] == (1 if training["device"] == "cpu" else 16)
        assert state["step"] == step and state["config"]["steps"] == 4000
        assert cfg["seed"] == 55 and cfg["warmup_steps"] == 100 and cfg["lr"] == 1e-5
        for key, value in cfg.items():
            if key != "validation_protocol":
                assert state["config"][key] == value, key
        assert state["config"]["initialized_from"] == {**training["parent"], "step": 20000}
        assert cfg["manifest"] == training["training_manifest"]["path"]
        assert state["config"]["manifest_sha256"] == training["training_manifest"]["sha256"]
        expected = ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
        expected["raw_spectral_residual"] = arm["spectral"]
        assert ModelConfig.from_checkpoint(state["model_config"]).to_dict() == expected
        assert state["config"]["camera_supervision"] == "sensor-valid-v1"
        assert state["config"]["training_execution"] == "deterministic-v1"
        assert state["config"]["training_execution_runtime"]["deterministic_algorithms"]
        size = 91 + 2 * arm["spectral"]
        unchanged = {}
        for field in ["model", "ema"]:
            assert len(state[field]) == size and all(
                torch.isfinite(v).all() for v in state[field].values()
            )
            unchanged[field] = sorted(
                k
                for k, v in state[field].items()
                if k in parent["ema"] and torch.equal(v, parent["ema"][k])
            )
            if not engineering:
                assert unchanged[field] == ["context.mean", "context.std"]
        assert len(state["optimizer"]["state"]) == size - 2
        for values in state["optimizer"]["state"].values():
            assert int(values["step"]) == step and values["exp_avg_sq"].min() >= 0
            assert all(torch.isfinite(v).all() for v in values.values() if torch.is_tensor(v))
        groups = state["optimizer"]["param_groups"]
        assert [g.get("lr_multiplier", 1) for g in groups] == ([1, 20] if arm["spectral"] else [1])
        retained = None
        if not engineering:
            retained = ref(Path(checkpoint["path"]).with_name("step-004000.pt"))
            assert retained["sha256"] == checkpoint["sha256"]
            first1000 = ref(Path(checkpoint["path"]).with_name("step-001000.pt"))
            assert groups[0]["lr"] == cfg["lr"] * 0.1
        for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]:
            assert state["config"][key + "_sha256"] == ref(cfg[key])["sha256"]
        assert case["initializations"] == ref(case["initializations"]["path"])
        assert case["captures"] == read(case["initializations"]["path"])
        assert len(case["captures"]) == 1
        assert all(
            c["common_initial_state_exact"] and c["DINO_sha256"] == training["DINO_sha256"]
            for c in case["captures"]
        )
        assert case["source_sha256"] == state["config"]["source_sha256"]
        archive = Path(case["source_snapshot"])
        assert all(ref(archive / name)["sha256"] == digest for name, digest in core.items())
        assert ref(case["metrics"]["path"]) == case["metrics"]
        from audit_flat_palette import train_rows

        rows = train_rows(Path(checkpoint["path"]).parent)
        assert rows == case["logged_observations"]
        resume_step = training.get("resume", {}).get(arm["name"], {}).get("step")
        scheduled_rows, extra_resume_rows = canonical_training_rows(
            rows, engineering=engineering, resume_step=resume_step
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
        recovery = check_recovery(training, arm, case, samples, rows)
        by_step = {r["step"]: r for r in samples}
        for row in rows:
            progress = max(0, row["step"] - 100) / 3900
            lr = (
                1e-5
                * min(1, row["step"] / 100)
                * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
            )
            assert (
                row["lr"] == lr and math.isfinite(row["loss"]) and math.isfinite(row["grad_norm"])
            )
            if row["step"] in by_step:
                assert row["batch_sha256"] == by_step[row["step"]]["source_sha256"]
                assert (
                    row["context_supervision_sha256"] == by_step[row["step"]]["actual_loss_sha256"]
                )
            else:
                assert row["step"] == resume_step + 1
                assert (
                    row["batch_sha256"]
                    == row["context_forward_sha256"]
                    == row["context_supervision_sha256"]
                )
        checkpoints.append(
            {
                **checkpoint,
                "arm": arm["name"],
                "step": step,
                "kind": "joint-checkpoint",
                "label": f"V{88 + index}-engineering-check16"
                if engineering
                else f"V{88 + index}-original4000",
            }
        )
        evidence.append(
            {
                "result": item,
                "initializations": case["initializations"],
                "captures": case["captures"],
                "retained": retained,
                "finite_states": [size, size, size - 2],
                "unchanged_from_parent_EMA": unchanged,
                "actual_training_package_files_exact": 46,
                "recovery": recovery,
                "retained1000": None if engineering else first1000,
                "additional_first_resume_logs": extra_resume_rows,
            }
        )
        cases.append(case)
        states.append(state)
        configs.append(cfg)
        observations.append(samples)
        logs.append(scheduled_rows)
    assert configs[0].keys() == configs[1].keys()
    assert {k for k in configs[0] if configs[0][k] != configs[1][k]} == {
        "run",
        "model",
        "raw_spectral_lr_multiplier",
    }
    assert {k for k in configs[0]["model"] if configs[0]["model"][k] != configs[1]["model"][k]} == {
        "raw_spectral_residual"
    }
    assert observations[0] == observations[1] and len(observations[0]) == status["recorded_pairs"]
    for first, second in zip(*logs, strict=True):
        assert all(
            first[k] == second[k]
            for k in ["step", "domain", "lr", "batch_sha256", "context_supervision_sha256"]
        )
    for key in ["python_rng", "torch_rng", "cuda_rng"]:
        identical(states[0][key], states[1][key])
    archives = [
        {p.name: ref(p)["sha256"] for p in Path(c["source_snapshot"]).iterdir() if p.is_file()}
        for c in cases
    ]
    assert archives[0] == archives[1] and cases[0]["source_sha256"] == cases[1]["source_sha256"]
    save(
        Path(plan["root"]) / "training-boundary.json",
        {
            "status": ENGINEERING_BOUNDARY if engineering else BOUNDARY,
            "engineering_preflight": engineering,
            "training_geometry": {"device": training["device"], "native_size": native},
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
            "scope": "Full-state/fixed-horizon/source/RNG audit only. No quality evidence, automatic promotion or extension.",
        },
    )


def run(plan_path, stage=None):
    if read(plan_path).get("engineering_preflight", False) and stage != "boundary":
        raise ValueError("Discarded engineering checkpoints cannot produce quality evidence")
    panels.require_completed = require_completed
    panels.boundaries = boundaries
    if stage is None:
        panels.controller(plan_path)
    else:
        panels.worker(plan_path, stage)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["controller", "worker"])
    p.add_argument("plan", type=Path)
    p.add_argument("--stage")
    a = p.parse_args()
    if a.mode == "worker" and a.stage is None:
        p.error("worker requires --stage")
    run(a.plan.resolve(), a.stage if a.mode == "worker" else None)
