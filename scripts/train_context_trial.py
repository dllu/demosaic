"""Frozen matched input-context training with identical central supervision."""

import argparse
import json
import math
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_interval_trial import guard, read, ref, save


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def compare_observations(first, second):
    counts = {}
    for a, b in zip(first, second, strict=True):
        if (a["step"], a["domain"]) != (b["step"], b["domain"]):
            raise ValueError("Matched context step/domain differs")
        for key in ("source_batch_sha256", "supervision_batch_sha256", "actual_loss_batch_sha256"):
            if a[key] != b[key]:
                raise ValueError(f"Shared context source/supervision differs: {key}")
        for row in (a, b):
            if row["actual_forward_inputs_sha256"] != row["expected_forward_inputs_sha256"]:
                raise ValueError("Actual forward differs from its declared field")
            if row["actual_loss_batch_sha256"] != row["supervision_batch_sha256"]:
                raise ValueError("Actual loss differs from its declared supervised field")
        if (
            a["actual_forward_inputs_sha256"] == b["actual_forward_inputs_sha256"]
            or a["forward_native_size"] >= b["forward_native_size"]
        ):
            raise ValueError("Missing intended extra context in the actual forward")
        counts[a["domain"]] = counts.get(a["domain"], 0) + 1
    if set(counts) != {"commons", "native", "paired"}:
        raise ValueError("Context comparison requires all three source domains")
    return {
        "recorded_pairs": sum(counts.values()),
        "domains": counts,
        "all_source_and_supervision_pairs_exact": True,
        "all_actual_forward_fields_differ": True,
    }


def worker(plan_path, arm_name):
    import torch
    import yaml
    from audit_flat_palette import train_rows
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training
    from demosaic.model import ModelConfig
    from demosaic.training_context import TrainingContext, crop_training_batch

    plan = read(plan_path)
    guard(plan)
    root, boundary = Path(plan["root"]), plan["boundary_updates"]
    assert plan["planned_updates"] == 4000 and 1 <= boundary <= 4000
    assert plan["engineering_only"] is (boundary < 4000)
    arm = next(a for a in plan["arms"] if a["name"] == arm_name)
    config = yaml.safe_load(Path(arm["config"]).read_text())
    context = TrainingContext.from_config(config)
    assert config["steps"] == 4000 and config["seed"] == 54
    assert (context.source_size, context.forward_size, context.loss_size) == (
        plan["source_size"],
        arm["forward_size"],
        plan["loss_size"],
    )
    assert ModelConfig.from_checkpoint(config["model"]).raw_directional_residual is False
    with (root / (arm_name + ".claim")).open("x") as stream:
        stream.write(str(os.getpid()))
    assert psutil.virtual_memory().available >= plan["minimum_worker_available_gib"] * 2**30
    assert shutil.disk_usage(plan["repository"]).free > 128 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 500 * 2**30
    if config["device"] == "cpu":
        assert plan["engineering_only"] and os.environ.get("CUDA_VISIBLE_DEVICES") == ""
        assert config["batch_size"] == 1 and config["precision"] == "float32"
        assert (context.source_size, context.loss_size, context.validation_size) == (64, 32, 32)
        assert not torch.cuda.is_initialized()
    else:
        assert config["device"] == "cuda" and config["batch_size"] == 16
        assert (context.source_size, context.loss_size, context.validation_size) == (320, 256, 256)
        assert config["precision"] == "bfloat16"
        device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(
            min(
                torch.cuda.get_per_process_memory_fraction(device),
                24 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
            ),
            device,
        )
    parent = torch.load(plan["parent"]["path"], weights_only=True, map_location="cpu", mmap=True)
    constructor, prepare, checkpoint_writer = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.save_checkpoint,
    )
    original_losses = training.reconstruction_loss, training.paired_reconstruction_loss
    capture, observations = {}, []
    tracking = {"current": None, "step": 0}
    forward_keys = ["packed", "variance", "colors", "wb", "matrix"]

    def instrument(options):
        model = constructor(options)
        capture["model"] = model

        def actual_forward(module, args):
            if not module.training:
                return
            if "initial_model_exact_parent_EMA" not in capture:
                values = module.restoration_state_dict()
                assert values.keys() == parent["ema"].keys()
                assert all(torch.equal(v.cpu(), parent["ema"][k]) for k, v in values.items())
                capture["initial_model_exact_parent_EMA"] = True
                capture["initial_model_sha256"] = model_hash(module)
                capture["DINO_sha256"] = model_hash(module.context.backbone)
                assert capture["DINO_sha256"] == plan["DINO_sha256"]
            assert tuple(args[0].shape[-2:]) == (context.forward_size // 2,) * 2
            current = tracking["current"]
            if current is not None:
                value = training.batch_fingerprint(dict(zip(forward_keys, args, strict=True)))
                assert value == current["expected_forward_inputs_sha256"]
                current["actual_forward_inputs_sha256"] = value

        model.register_forward_pre_hook(actual_forward)
        return model

    def observe(*args, **kwargs):
        batch = prepare(*args, **kwargs)
        tracking.update(step=args[0], current=None)
        if args[0] <= 16 or args[0] % 25 == 0:
            forward = context.forward_batch(batch)
            supervised = crop_training_batch(batch, context.loss_size)
            sample = {
                "step": args[0],
                "domain": args[1],
                "source_batch_sha256": training.batch_fingerprint(batch),
                "supervision_batch_sha256": training.batch_fingerprint(supervised),
                "expected_forward_inputs_sha256": training.batch_fingerprint(
                    {key: forward[key] for key in forward_keys}
                ),
                "forward_native_size": context.forward_size,
            }
            observations.append(sample)
            tracking["current"] = sample
        return batch

    def loss_wrapper(original):
        def observed(prediction, batch, auxiliary=None, **options):
            assert tuple(prediction.shape[-2:]) == (context.loss_size,) * 2
            assert tuple(batch["packed"].shape[-2:]) == (context.loss_size // 2,) * 2
            current = tracking["current"]
            if current is not None:
                current["actual_loss_batch_sha256"] = training.batch_fingerprint(batch)
                assert current["actual_loss_batch_sha256"] == current["supervision_batch_sha256"]
                assert "actual_forward_inputs_sha256" in current
                save(root / (arm_name + "-observations.json"), observations)
                tracking["current"] = None
            return original(prediction, batch, auxiliary, **options)

        return observed

    def retained(path, model, optimizer, ema, step, cfg, best):
        checkpoint_writer(path, model, optimizer, ema, step, cfg, best)
        if Path(path).name == "last.pt" and step in plan["retain_steps"]:
            target = Path(path).with_name(f"step-{step:06d}.pt")
            if not target.exists():
                shutil.copyfile(path, target)

    training.JointDemosaic, training.prepare_training_batch, training.save_checkpoint = (
        instrument,
        observe,
        retained,
    )
    training.reconstruction_loss, training.paired_reconstruction_loss = map(
        loss_wrapper, original_losses
    )
    try:
        checkpoint = training.train(
            arm["config"], initialize=plan["parent"]["path"], stop_after=boundary
        )
    finally:
        training.JointDemosaic, training.prepare_training_batch, training.save_checkpoint = (
            constructor,
            prepare,
            checkpoint_writer,
        )
        training.reconstruction_loss, training.paired_reconstruction_loss = original_losses
    model = capture.pop("model")
    assert model_hash(model.context.backbone) == plan["DINO_sha256"]
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    state = torch.load(checkpoint, weights_only=True, map_location="cpu", mmap=True)
    assert state["step"] == boundary and state["config"]["steps"] == 4000
    assert (
        ModelConfig.from_checkpoint(state["model_config"]).to_dict()
        == ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
    )
    for key, value in config.items():
        if key != "validation_protocol":
            assert state["config"][key] == value, key
    assert state["config"]["initialized_from"] == {**plan["parent"], "step": 20000}
    assert state["config"]["training_execution_runtime"]["deterministic_algorithms"] is True
    assert len(state["model"]) == len(state["ema"]) == 91 and len(state["optimizer"]["state"]) == 89
    for field in ("model", "ema"):
        assert all(torch.isfinite(v).all() for v in state[field].values())
    for item in state["optimizer"]["state"].values():
        assert int(item["step"]) == boundary
        assert all(torch.isfinite(v).all() for v in item.values() if torch.is_tensor(v))
    rows = train_rows(Path(checkpoint).parent)
    assert [r["step"] for r in rows] == [1, *range(25, boundary + 1, 25)]
    assert [r["step"] for r in observations] == [
        *range(1, min(16, boundary) + 1),
        *range(25, boundary + 1, 25),
    ]
    by_step = {r["step"]: r for r in observations}
    for row in rows:
        assert math.isfinite(row["loss"]) and math.isfinite(row["grad_norm"])
        assert row["batch_sha256"] == by_step[row["step"]]["source_batch_sha256"]
        assert row["context_supervision_sha256"] == by_step[row["step"]]["supervision_batch_sha256"]
    guard(plan)
    save(
        root / (arm_name + "-result.json"),
        {
            "status": "completed-context-arm-awaiting-matched-comparison",
            "arm": arm_name,
            "checkpoint": ref(checkpoint),
            "capture": capture,
            "observations": ref(root / (arm_name + "-observations.json")),
            "metrics": ref(Path(checkpoint).parent / "metrics.jsonl"),
            "logged_observations": rows,
            "actual_step": boundary,
            "planned_steps": 4000,
            "engineering_only": plan["engineering_only"],
            "source_sha256": state["config"]["source_sha256"],
            "source_snapshot": state["config"]["source_snapshot"],
            "finite_states": {"model": 91, "EMA": 91, "AdamW": 89},
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        },
    )


def controller(plan_path):
    plan_path = Path(plan_path).resolve()
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": {},
    }

    def record(value, **fields):
        status.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", status)
        print(json.dumps({"status": value, "arm": status.get("arm")}), flush=True)

    def resources():
        return (
            psutil.virtual_memory().available / 2**30,
            shutil.disk_usage(plan["repository"]).free / 2**30,
            shutil.disk_usage("/mnt/external").free / 2**30,
        )

    try:
        for arm in plan["arms"]:
            guard(plan)
            record("waiting-for-stable-context-training-resources", arm=arm["name"])
            since, deadline = None, time.monotonic() + plan["wait_seconds"]
            while True:
                assert time.monotonic() < deadline, "Stable-resource wait exhausted"
                ram, disk, external = resources()
                if ram >= plan["stable_available_gib"] and disk > 128 and external > 500:
                    since = time.monotonic() if since is None else since
                    if time.monotonic() - since >= plan["stable_memory_seconds"]:
                        break
                else:
                    since = None
                time.sleep(5)
            env = dict(os.environ, **plan["cache_environment"])
            env.update(
                PYTHONPATH=str(Path(plan["work"]) / "src")
                + ":"
                + str(Path(plan["work"]) / "scripts"),
                HF_HUB_OFFLINE="1",
                CUDA_VISIBLE_DEVICES="" if plan["device"] == "cpu" else "0",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
            )
            with (root / (arm["name"] + ".log")).open("xb") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        plan["worker"]["path"],
                        "worker",
                        str(plan_path),
                        "--arm",
                        arm["name"],
                    ],
                    cwd=plan["work"],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-source-frozen-context-training-arm", child=owner)
                deadline = time.monotonic() + plan["per_arm_timeout_seconds"]
                while child.poll() is None:
                    ram, disk, external = resources()
                    reason = (
                        "runtime"
                        if time.monotonic() > deadline
                        else "resources"
                        if ram < 24 or disk < 128 or external < 500
                        else None
                    )
                    if reason is not None:
                        # This is only the exact new session created immediately above.
                        # SIGTERM has no checkpoint promise; preserve existing files.
                        if child.poll() is not None:
                            break
                        assert alive(owner) and os.getpgid(child.pid) == child.pid
                        os.killpg(child.pid, signal.SIGTERM)
                        child.wait(timeout=30)
                        raise RuntimeError(
                            f"Owned context worker stopped at {reason} bound; no retry"
                        )
                    time.sleep(5)
                code = child.wait()
            assert code == 0, (arm["name"], code)
            status["completed"][arm["name"]] = ref(root / (arm["name"] + "-result.json"))
        a, b = [read(status["completed"][arm["name"]]["path"]) for arm in plan["arms"]]
        paired = compare_observations(
            read(a["observations"]["path"]), read(b["observations"]["path"])
        )
        assert a["capture"] == b["capture"] and a["source_sha256"] == b["source_sha256"]
        archives = [
            {p.name: ref(p)["sha256"] for p in Path(r["source_snapshot"]).iterdir() if p.is_file()}
            for r in (a, b)
        ]
        assert archives[0] == archives[1]
        for x, y in zip(a["logged_observations"], b["logged_observations"], strict=True):
            assert all(
                x[k] == y[k]
                for k in ("step", "domain", "lr", "batch_sha256", "context_supervision_sha256")
            )
        import torch
        from audit_flat_palette import identical

        states = [
            torch.load(r["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
            for r in (a, b)
        ]
        for key in ("python_rng", "torch_rng", "cuda_rng"):
            identical(states[0][key], states[1][key])
        import yaml

        first, second = (yaml.safe_load(Path(arm["config"]).read_text()) for arm in plan["arms"])
        assert first.keys() == second.keys()
        assert {k for k in first if first[k] != second[k]} == {"forward_patch_size", "run"}
        guard(plan)
        record(
            "completed-context-engineering-preflight"
            if plan["engineering_only"]
            else "completed-context-original4000-awaiting-full-quality-and-native-review",
            paired_observation_audit=paired,
            final_RNG_states_match=True,
            archived_source_and_data_exact=True,
            logged_domains_LRs_and_supervision_match=True,
        )
    except BaseException as error:
        record("failed-context-trial-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "worker"])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--arm", choices=["control", "context"])
    args = parser.parse_args()
    if args.mode == "controller":
        controller(args.plan)
    else:
        worker(args.plan, args.arm)
