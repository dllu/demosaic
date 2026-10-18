"""Run fresh matched directional-bank architectures through their fixed4000 updates."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).absolute()), "sha256": sha(path)}


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def guard(plan):
    for item in plan["inputs"]:
        assert sha(item["path"]) == item["sha256"], item["path"]
    for path, digest in plan["frozen_files"].items():
        assert sha(path) == digest, path


def worker(plan_path, arm_name):
    import torch
    from audit_flat_palette import train_rows
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training

    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    arm = next(a for a in plan["arms"] if a["name"] == arm_name)
    with (root / (arm_name + ".claim")).open("x") as stream:
        stream.write(str(os.getpid()))
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(root).free > 128 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 500 * 2**30
    device = torch.device("cuda", torch.cuda.current_device())
    quota = min(
        torch.cuda.get_per_process_memory_fraction(device),
        24 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
    )
    torch.cuda.set_per_process_memory_fraction(quota, device)
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    constructor = training.JointDemosaic
    prepare = training.prepare_training_batch
    capture, sampled = {}, []

    def instrument(options):
        model = constructor(options)
        capture["model"] = model

        def first_forward(module, args):
            actual = module.restoration_state_dict()
            extra = actual.keys() - parent["ema"].keys()
            assert len(extra) == 8 + 6 * arm["bank_context"] and all(
                k.startswith("pretrained_rgb.raw_directional.") for k in extra
            )
            for name, value in parent["ema"].items():
                assert torch.equal(actual[name].cpu(), value), name
            branch = module.pretrained_rgb.raw_directional
            assert all(
                p.count_nonzero() == 0
                for n, p in branch.named_parameters()
                if not n.startswith(("local.", "bank."))
            )
            capture["initial_EMA_exact"] = True
            capture["initial_branch_sha256"] = model_hash(branch)
            capture["initial_local_sha256"] = model_hash(branch.local)
            capture["bank_context"] = arm["bank_context"]
            if branch.bank is not None:
                assert all(p.count_nonzero() == 0 for p in branch.bank[-1].parameters())
            assert (
                torch.are_deterministic_algorithms_enabled() and not torch.backends.cudnn.benchmark
            )
            capture["DINO_sha256"] = model_hash(module.context.backbone)
            assert (
                capture["DINO_sha256"]
                == "370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd"
            )
            hook.remove()

        hook = model.register_forward_pre_hook(first_forward)
        return model

    def observe(*args, **kwargs):
        batch = prepare(*args, **kwargs)
        if args[0] <= 16 or args[0] % 25 == 0:
            sampled.append(
                {
                    "step": args[0],
                    "domain": args[1],
                    "legacy_batch_sha256": training.batch_fingerprint(
                        {k: v for k, v in batch.items() if k != "sensor_target"}
                    ),
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
                    "sensor_target_present": "sensor_target" in batch,
                }
            )
            save(root / (arm_name + "-sampled-observations.json"), sampled)
        return batch

    save_checkpoint = training.save_checkpoint

    def retain_boundary(path, model, optimizer, ema, step, config, best):
        save_checkpoint(path, model, optimizer, ema, step, config, best)
        if Path(path).name == "last.pt" and step in (1000, 2000, 3000):
            target = Path(path).parent / "checkpoints" / f"step-{step:06d}.pt"
            target.parent.mkdir(exist_ok=True)
            assert not target.exists()
            temporary = target.with_suffix(".tmp")
            shutil.copyfile(path, temporary)
            temporary.replace(target)

    training.JointDemosaic, training.prepare_training_batch = instrument, observe
    training.save_checkpoint = retain_boundary
    try:
        checkpoint = training.train(
            arm["config"], initialize=plan["parent"]["path"], stop_after=4000
        )
    finally:
        training.JointDemosaic, training.prepare_training_batch = constructor, prepare
        training.save_checkpoint = save_checkpoint
    model = capture.pop("model")
    assert capture["DINO_sha256"] == model_hash(model.context.backbone)
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    state = torch.load(checkpoint, weights_only=True, map_location="cpu", mmap=True)
    assert state["step"] == 4000 and state["config"]["steps"] == 4000
    assert state["config"]["reconstruction_objective"] == "charbonnier-v1"
    assert state["config"]["camera_supervision"] == "sensor-valid-v1"
    assert state["config"]["model"]["raw_directional_residual"] is True
    assert state["model_config"]["raw_directional_bank_context"] is arm["bank_context"]
    assert state["config"]["training_execution"] == "deterministic-v1"
    assert state["config"]["reference_interval_weight"] == arm["reference_interval_weight"]
    assert state["config"]["raw_directional_lr_multiplier"] == 20
    assert [g["lr_multiplier"] for g in state["optimizer"]["param_groups"]] == [1, 20]
    assert state["config"]["manifest_sha256"] == plan["training_manifest_sha256"]
    assert len(state["model"]) == len(state["ema"]) == 99 + 6 * arm["bank_context"]
    assert len(state["optimizer"]["state"]) == 97 + 6 * arm["bank_context"]
    for field in ["model", "ema"]:
        assert all(torch.isfinite(v).all() for v in state[field].values())
    for values in state["optimizer"]["state"].values():
        assert int(values["step"]) == 4000
        assert all(torch.isfinite(v).all() for v in values.values() if isinstance(v, torch.Tensor))
    rows = train_rows(Path(checkpoint).parent)
    assert [r["step"] for r in rows] == [1, *range(25, 4001, 25)]
    assert [r["step"] for r in sampled] == [*range(1, 17), *range(25, 4001, 25)]
    assert all(r["sensor_target_present"] == (r["domain"] != "paired") for r in sampled)
    guard(plan)
    result = {
        "status": "completed-one-directional-bank-original4000-awaiting-quality-review",
        "arm": arm_name,
        "checkpoint": ref(checkpoint),
        "capture": capture,
        "metrics": ref(Path(checkpoint).parent / "metrics.jsonl"),
        "sampled_observations": ref(root / (arm_name + "-sampled-observations.json")),
        "finite_states": {
            "model": 99 + 6 * arm["bank_context"],
            "EMA": 99 + 6 * arm["bank_context"],
            "AdamW": 97 + 6 * arm["bank_context"],
        },
        "logged_observations": rows,
        "source_sha256": state["config"]["source_sha256"],
        "actual_step": 4000,
        "planned_steps": 4000,
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
    }
    save(root / (arm_name + "-result.json"), result)


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": {},
    }

    def record(status, **values):
        info.update(status=status, updated_unix=time.time(), **values)
        save(root / "status.json", info)
        print(json.dumps({"status": status, "arm": info.get("arm")}), flush=True)

    try:
        record("starting-frozen-mature-directional-bank-original4000-trial")
        for arm in plan["arms"]:
            guard(plan)
            env = dict(os.environ)
            env.update(
                PYTHONPATH=os.pathsep.join(
                    [str(Path(plan["work"]) / p) for p in ["src", "scripts"]]
                ),
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
                identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-directional-bank-original4000", arm=arm["name"], child=identity)
                try:
                    code = child.wait(timeout=plan["per_arm_timeout_seconds"])
                except subprocess.TimeoutExpired:
                    # Terminate only this exact owned process group, including its data workers.
                    import signal

                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=30)
                    raise
            assert code == 0, f"{arm['name']} exited {code}"
            result_path = root / (arm["name"] + "-result.json")
            result = read(result_path)
            assert result["actual_step"] == 4000 and result["planned_steps"] == 4000
            info["completed"][arm["name"]] = ref(result_path)
            record("completed-one-directional-bank-original4000", arm=arm["name"])
        a, b = [read(info["completed"][a["name"]]["path"]) for a in plan["arms"]]
        for x, y in zip(
            read(a["sampled_observations"]["path"]),
            read(b["sampled_observations"]["path"]),
            strict=True,
        ):
            assert all(
                x[k] == y[k] for k in ["step", "domain", "legacy_batch_sha256", "input_sha256"]
            )
        assert all(
            a["capture"][k] == b["capture"][k]
            for k in ["initial_EMA_exact", "initial_local_sha256", "DINO_sha256"]
        )
        assert a["source_sha256"] == b["source_sha256"]
        import torch

        states = [
            torch.load(r["checkpoint"]["path"], map_location="cpu", weights_only=True, mmap=True)
            for r in [a, b]
        ]
        assert states[0]["python_rng"] == states[1]["python_rng"]
        assert torch.equal(states[0]["torch_rng"], states[1]["torch_rng"])
        assert len(states[0]["cuda_rng"]) == len(states[1]["cuda_rng"])
        assert all(
            torch.equal(x, y)
            for x, y in zip(states[0]["cuda_rng"], states[1]["cuda_rng"], strict=True)
        )
        for x, y in zip(a["logged_observations"], b["logged_observations"], strict=True):
            assert all(x[k] == y[k] for k in ["step", "domain", "lr"])
        guard(plan)
        record(
            "completed-matched-directional-bank-original4000-awaiting-full-quality-and-native-review",
            all176_sampled_legacy_and_input_observations_match=True,
            all161_logged_domains_and_LRs_match=True,
        )
    except BaseException as error:
        record("failed-directional-bank-trial-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "worker"])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--arm", choices=["control", "bank"])
    args = parser.parse_args()
    if args.mode == "controller":
        controller(args.plan)
    else:
        worker(args.plan, args.arm)
