"""Train a source-frozen128/150 native-data comparison at its original horizon."""

import argparse
import json
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
        process = psutil.Process(owner["pid"])
        return (
            process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def compare_observations(first, second, *, require_native_change):
    common, native, changed = 0, 0, 0
    for a, b in zip(first, second, strict=True):
        if (a["step"], a["domain"]) != (b["step"], b["domain"]):
            raise ValueError("Matched domain/step differs")
        keys = ["full_batch_sha256", "input_sha256"]
        equal = all(a[key] == b[key] for key in keys)
        if a["domain"] == "native":
            native += 1
            changed += not equal
        else:
            common += 1
            if not equal:
                raise ValueError("Shared Commons/paired observations differ")
    if require_native_change and (not common or not native or not changed):
        raise ValueError("Missing shared-domain or actual native-treatment coverage")
    return {"shared_pairs_exact": common, "native_pairs": native, "native_pairs_changed": changed}


def worker(plan_path, arm_name):
    import torch
    import yaml
    from audit_flat_palette import train_rows
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training
    from demosaic.model import ModelConfig

    plan = read(plan_path)
    guard(plan)
    root, boundary = Path(plan["root"]), plan["boundary_updates"]
    assert plan["planned_updates"] == 20000 and 1 <= boundary <= 20000
    assert plan["engineering_only"] is (boundary < 20000)
    arm = next(a for a in plan["arms"] if a["name"] == arm_name)
    config = yaml.safe_load(Path(arm["config"]).read_text())
    assert config["steps"] == 20000 and config["seed"] == 53
    assert ref(config["raw_clean_manifest"]) == arm["native_manifest"]
    assert ModelConfig.from_checkpoint(config["model"]).raw_directional_residual is False
    with (root / (arm_name + ".claim")).open("x") as stream:
        stream.write(str(os.getpid()))
    assert psutil.virtual_memory().available >= plan["minimum_worker_available_gib"] * 2**30
    assert shutil.disk_usage(root).free > 128 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 500 * 2**30
    if config["device"] == "cpu":
        assert plan["engineering_only"] and os.environ.get("CUDA_VISIBLE_DEVICES") == ""
        assert config["batch_size"] == 1 and config["patch_size"] == 64
        assert config["precision"] == "float32" and not torch.cuda.is_initialized()
    else:
        assert config["device"] == "cuda" and config["batch_size"] == 16
        assert config["patch_size"] == 256 and config["precision"] == "bfloat16"
        device = torch.device("cuda", torch.cuda.current_device())
        quota = min(
            torch.cuda.get_per_process_memory_fraction(device),
            24 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
        )
        torch.cuda.set_per_process_memory_fraction(quota, device)
    parent = torch.load(plan["parent"]["path"], weights_only=True, map_location="cpu", mmap=True)
    constructor, prepare, checkpoint_writer = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.save_checkpoint,
    )
    capture, samples = {}, []

    def instrument(options):
        model = constructor(options)
        capture["model"] = model

        def initial(module, args):
            values = module.restoration_state_dict()
            assert values.keys() == parent["ema"].keys()
            assert all(torch.equal(v.cpu(), parent["ema"][k]) for k, v in values.items())
            capture["initial_EMA_exact"] = True
            capture["initial_model_sha256"] = model_hash(module)
            capture["DINO_sha256"] = model_hash(module.context.backbone)
            assert capture["DINO_sha256"] == plan["DINO_sha256"]
            hook.remove()

        hook = model.register_forward_pre_hook(initial)
        return model

    def observe(*args, **kwargs):
        batch = prepare(*args, **kwargs)
        if args[0] <= 16 or args[0] % 25 == 0:
            samples.append(
                {
                    "step": args[0],
                    "domain": args[1],
                    "full_batch_sha256": training.batch_fingerprint(batch),
                    "input_sha256": training.batch_fingerprint(
                        {
                            k: batch[k]
                            for k in [
                                "packed",
                                "variance",
                                "colors",
                                "wb",
                                "matrix",
                                "shot",
                                "read",
                            ]
                        }
                    ),
                }
            )
            save(root / (arm_name + "-observations.json"), samples)
        return batch

    def retained(path, model, optimizer, ema, step, cfg, best):
        checkpoint_writer(path, model, optimizer, ema, step, cfg, best)
        if Path(path).name == "last.pt" and step in plan["retain_steps"]:
            destination = Path(path).with_name(f"step-{step:06d}.pt")
            if not destination.exists():
                shutil.copyfile(path, destination)

    training.JointDemosaic, training.prepare_training_batch, training.save_checkpoint = (
        instrument,
        observe,
        retained,
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
    model = capture.pop("model")
    assert model_hash(model.context.backbone) == plan["DINO_sha256"]
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    state = torch.load(checkpoint, weights_only=True, map_location="cpu", mmap=True)
    assert state["step"] == boundary and state["config"]["steps"] == 20000
    assert (
        ModelConfig.from_checkpoint(state["model_config"]).to_dict()
        == ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
    )
    for key, value in config.items():
        if key != "validation_protocol":
            assert state["config"][key] == value, key
    assert state["config"]["initialized_from"] == {**plan["parent"], "step": 20000}
    assert state["config"]["training_execution_runtime"]["deterministic_algorithms"] is True
    assert len(state["model"]) == len(state["ema"]) == 91
    assert len(state["optimizer"]["state"]) == 89
    for key in ["model", "ema"]:
        assert all(torch.isfinite(v).all() for v in state[key].values())
    for item in state["optimizer"]["state"].values():
        assert int(item["step"]) == boundary
        assert all(torch.isfinite(v).all() for v in item.values() if isinstance(v, torch.Tensor))
    for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]:
        assert state["config"][key + "_sha256"] == ref(config[key])["sha256"]
    rows = train_rows(Path(checkpoint).parent)
    assert [r["step"] for r in rows] == [1, *range(25, boundary + 1, 25)]
    assert [r["step"] for r in samples] == sorted(
        {*range(1, min(16, boundary) + 1), *range(25, boundary + 1, 25)}
    )
    assert all(math_finite(r["loss"]) and math_finite(r["grad_norm"]) for r in rows)
    guard(plan)
    result = {
        "status": "completed-native-data-arm-awaiting-matched-comparison",
        "arm": arm_name,
        "checkpoint": ref(checkpoint),
        "capture": capture,
        "observations": ref(root / (arm_name + "-observations.json")),
        "metrics": ref(Path(checkpoint).parent / "metrics.jsonl"),
        "logged_observations": rows,
        "actual_step": boundary,
        "planned_steps": 20000,
        "engineering_only": plan["engineering_only"],
        "source_sha256": state["config"]["source_sha256"],
        "source_snapshot": state["config"]["source_snapshot"],
        "finite_states": {"model": 91, "EMA": 91, "AdamW": 89},
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
    }
    save(root / (arm_name + "-result.json"), result)


def math_finite(value):
    import math

    return isinstance(value, (int, float)) and math.isfinite(value)


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

    def record(state, **values):
        status.update(status=state, updated_unix=time.time(), **values)
        save(root / "status.json", status)
        print(json.dumps({"status": state, "arm": status.get("arm")}), flush=True)

    try:
        dependency = plan.get("preparation_dependency")
        if dependency is not None:
            record("waiting-for-exact-cache-preparation-owner-exit")
            deadline = time.monotonic() + plan["wait_seconds"]
            while alive(dependency["owner"]):
                assert time.monotonic() < deadline, "Preparation wait exhausted"
                time.sleep(10)
            state = read(dependency["status_path"])
            assert state["owner"] == dependency["owner"] and state["plan"] == dependency["plan"]
            assert state["status"] == "prepared-and-screened-quarantine-awaiting-independent-review"
        for arm in plan["arms"]:
            guard(plan)
            record("waiting-for-stable-memory-before-native-data-arm", arm=arm["name"])
            since, deadline = None, time.monotonic() + plan["wait_seconds"]
            while True:
                assert time.monotonic() < deadline, "Stable-memory wait exhausted"
                if psutil.virtual_memory().available >= plan["stable_available_gib"] * 2**30:
                    since = time.monotonic() if since is None else since
                    if time.monotonic() - since >= plan["stable_memory_seconds"]:
                        break
                else:
                    since = None
                time.sleep(10)
            env = dict(
                os.environ,
                PYTHONPATH=str(Path(plan["work"]) / "src")
                + ":"
                + str(Path(plan["work"]) / "scripts"),
                HF_HOME=plan["HF_HOME"],
                HF_HUB_OFFLINE="1",
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
                record("running-native-data-original20000-arm", arm=arm["name"], child=owner)
                try:
                    code = child.wait(timeout=plan["per_arm_timeout_seconds"])
                except subprocess.TimeoutExpired:
                    assert psutil.Process(child.pid).create_time() == owner["created"]
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=30)
                    raise
            assert code == 0, (arm["name"], code)
            status["completed"][arm["name"]] = ref(root / (arm["name"] + "-result.json"))
        a, b = [read(status["completed"][arm["name"]]["path"]) for arm in plan["arms"]]
        paired = compare_observations(
            read(a["observations"]["path"]),
            read(b["observations"]["path"]),
            require_native_change=not plan["engineering_only"],
        )
        assert a["capture"] == b["capture"]
        # The trainer's archive hash includes native-manifest bytes. Verify
        # that this is the sole archive difference rather than demanding a
        # falsely identical combined code/data hash for a data intervention.
        archives = [
            {p.name: ref(p)["sha256"] for p in Path(r["source_snapshot"]).iterdir() if p.is_file()}
            for r in [a, b]
        ]
        assert archives[0].keys() == archives[1].keys()
        assert {k for k in archives[0] if archives[0][k] != archives[1][k]} == {
            "raw-clean-manifest.json"
        }
        for x, y in zip(a["logged_observations"], b["logged_observations"], strict=True):
            assert all(x[key] == y[key] for key in ["step", "domain", "lr"])
        import torch
        from audit_flat_palette import identical

        states = [
            torch.load(r["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
            for r in [a, b]
        ]
        for key in ["python_rng", "torch_rng", "cuda_rng"]:
            identical(states[0][key], states[1][key])
        guard(plan)
        record(
            "completed-native-data-engineering-preflight"
            if plan["engineering_only"]
            else "completed-native-data-original20000-awaiting-full-quality-and-native-review",
            paired_observation_audit=paired,
            final_RNG_states_match=True,
            logged_domains_LRs_match=True,
            archived_source_differs_only_in_native_manifest=True,
        )
    except BaseException as error:
        record("failed-native-data-trial-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "worker"])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--arm", choices=["control", "expanded"])
    args = parser.parse_args()
    if args.mode == "controller":
        controller(args.plan)
    else:
        worker(args.plan, args.arm)
