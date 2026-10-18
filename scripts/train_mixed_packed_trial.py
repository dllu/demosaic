"""Run a frozen fresh mixed-domain trial through a checked prefix and quality gate."""

import argparse
import hashlib
import json
import os
import pickle
import random
import shutil
import subprocess
import time
from pathlib import Path

import psutil
import torch
import yaml
from probe_raw_feature_coordinates import alive, batch_fingerprint, guard, read, ref
from probe_raw_residual_units import digest

import demosaic.train as training
from demosaic.cfa import bilinear
from demosaic.inference import load_checkpoint
from demosaic.model import ModelConfig
from demosaic.precision import amp_context


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def rng_hash():
    return hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest()


def optimizer_hash(state):
    return digest(
        (f"{index}/{name}", value)
        for index, items in state["state"].items()
        for name, value in sorted(items.items())
        if torch.is_tensor(value)
    )


def worker(plan_path, arm_name, phase):
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    arm = next(arm for arm in plan["arms"] if arm["arm"] == arm_name)
    with (root / f"{phase}-{arm_name}.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    prefix = phase == "prefix"
    start = 0 if prefix else plan["prefix_updates"]
    end = plan["prefix_updates"] if prefix else plan["quality_gate_updates"]
    resume = None if prefix else arm["prefix_checkpoint"]
    prior = None if prefix else torch.load(resume, map_location="cpu", weights_only=True)
    capture = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "phase": phase,
        "arm": arm_name,
        "start_optimizer_step": start,
        "end_optimizer_step": end,
        "fresh": prefix,
        "resume": None if prefix else ref(resume),
    }
    selected, counted = [], 0
    original_constructor, original_prepare, original_optimizer = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )
    recipe = yaml.safe_load(Path(arm["config"]).read_text())

    def constructor(options):
        model = original_constructor(options)
        assert options.isotropic_raw_gain == 32 and options.isotropic_residual_scale == 1 / 32
        assert options.dino == (arm_name == "dino")
        capture["model"] = model
        initial = digest(
            ("packed_isotropic." + name, value)
            for name, value in model.packed_isotropic.state_dict().items()
        )
        assert initial == plan["initial_RAW_state_SHA256"]
        capture["initial_RAW_state_SHA256"] = initial
        capture["initial_Torch_RNG_SHA256"] = rng_hash()
        capture["initial_Python_RNG_SHA256"] = hashlib.sha256(
            pickle.dumps(random.getstate())
        ).hexdigest()
        if options.dino:
            capture["DINO_SHA256"] = digest(model.context.backbone.state_dict().items())
            assert capture["DINO_SHA256"] == plan["official_frozen_DINO_SHA256"]

        def first_forward(module, args, kwargs, output):
            if prefix:
                prediction = output[0] if isinstance(output, tuple) else output
                assert torch.equal(prediction, bilinear(args[0], args[2]))
                assert not capture["optimizer"].state
                capture["initial_physical_bilinear_equal"] = True
            else:
                assert digest(module.restoration_state_dict().items()) == digest(
                    prior["model"].items()
                )
                assert optimizer_hash(capture["optimizer"].state_dict()) == optimizer_hash(
                    prior["optimizer"]
                )
                assert torch.equal(torch.get_rng_state(), prior["torch_rng"])
                assert random.getstate() == prior["python_rng"]
                assert all(
                    torch.equal(a, b)
                    for a, b in zip(torch.cuda.get_rng_state_all(), prior["cuda_rng"], strict=True)
                )
                capture["actual_full_state_restore_verified_before_first_backward"] = True
            capture["first_physical_forward_batch"] = len(args[0])
            hook.remove()

        hook = model.register_forward_hook(first_forward, with_kwargs=True)
        return model

    def prepare(*args, **kwargs):
        nonlocal counted
        batch = original_prepare(*args, **kwargs)
        counted += 1
        data_step, domain = args[:2]
        if data_step <= 16:
            selected.append(
                {"data_step": data_step, "domain": domain, "batch_sha256": batch_fingerprint(batch)}
            )
            if len(selected) == 16:
                save(root / f"{arm_name}-first16.json", selected)
        return batch

    def make_optimizer(*args, **kwargs):
        optimizer = original_optimizer(*args, **kwargs)
        capture["optimizer"] = optimizer
        return optimizer

    training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
        constructor,
        prepare,
        make_optimizer,
    )
    try:
        path = training.train(arm["config"], resume=resume, stop_after=end - start)
    finally:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            original_constructor,
            original_prepare,
            original_optimizer,
        )
    model, optimizer = capture.pop("model"), capture.pop("optimizer")
    state = torch.load(path, map_location="cpu", weights_only=True)
    assert digest(model.restoration_state_dict().items()) == digest(state["model"].items())
    assert optimizer_hash(optimizer.state_dict()) == optimizer_hash(state["optimizer"])
    count = 863 if arm_name == "dino" else 852
    assert counted == (end - start) * 4
    assert state["step"] == end and state["data_step"] == end * 4
    assert state["example_draws"] == end * 16 and state["config"]["steps"] == 40000
    assert "initialized_from" not in state["config"]
    assert (
        ModelConfig.from_checkpoint(state["model_config"]).to_dict()
        == ModelConfig(**recipe["model"]).to_dict()
    )
    for key in [
        "manifest_sha256",
        "paired_manifest_sha256",
        "raw_clean_manifest_sha256",
        "validation_manifest_sha256",
        "validation_protocol_sha256",
    ]:
        assert state["config"][key] == plan["manifest_hashes"][key]
    assert all(
        torch.isfinite(value).all() for key in ["model", "ema"] for value in state[key].values()
    )
    assert len(state["optimizer"]["state"]) == count
    assert all(
        int(items["step"]) == end and all(torch.isfinite(value).all() for value in items.values())
        for items in state["optimizer"]["state"].values()
    )
    assert all(
        p.grad is not None and torch.isfinite(p.grad).all()
        for p in model.parameters()
        if p.requires_grad
    )
    if arm_name == "dino":
        assert not model.context.backbone.training
        assert capture["DINO_SHA256"] == digest(model.context.backbone.state_dict().items())
        assert all(
            not p.requires_grad and p.grad is None for p in model.context.backbone.parameters()
        )
        capture["genuine_DINO_unchanged_and_gradient_free"] = True
    model.load_state_dict(state["ema"], strict=False)
    model.eval()
    restored, metadata = load_checkpoint(path, "cuda")
    restored.eval().to(memory_format=torch.channels_last)
    assert digest(model.state_dict().items()) == digest(restored.state_dict().items())
    fixture = read(plan["portable_fixtures"]["path"])[0]
    with __import__("numpy").load(fixture["fixture"]["path"], allow_pickle=False) as arrays:
        batch = {key: torch.from_numpy(arrays[key].copy()).cuda() for key in arrays.files}
    with torch.inference_mode(), amp_context("cuda", dtype="float32"):
        args = [batch[key] for key in ["packed", "variance", "colors", "wb", "matrix"]]
        first, second = model(*args), restored(*args)
    error = (first - second).abs().max().item()
    assert error <= 1e-6
    capture.update(
        checkpoint=ref(path),
        source_bundle_SHA256=state["config"]["source_sha256"],
        finite_model_EMA_Adam_states=count,
        all_Adam_steps=end,
        data_steps=end * 4,
        example_draws=end * 16,
        actual_prepared_source_groups=counted,
        portable_FP32_max_abs=error,
        portable_FP32_bitwise_equal=torch.equal(first, second),
        portable_checkpoint_hash=metadata["loaded_sha256"],
    )
    assert capture["checkpoint"]["sha256"] == capture["portable_checkpoint_hash"]
    guard(plan)
    save(root / f"{phase}-{arm_name}-result.json", capture)


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root, status = Path(plan["root"]), Path(plan["status"])
    assert not status.exists() and not torch.cuda.is_initialized()
    previous = read(plan["execution_status"]["path"])
    assert previous["status"] == "completed-discarded-mixed-batch-execution-sweep"
    assert not alive(previous["controller"])
    with (root / "launch.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": {},
    }

    def record(stage, **values):
        info.update(status=stage, updated_unix=time.time(), **values)
        temporary = status.with_suffix(".tmp")
        save(temporary, info)
        temporary.replace(status)
        print(json.dumps(info), flush=True)

    try:
        record("starting-matched-mixed16-fresh-prefixes")
        for phase in ["prefix", "finish"]:
            for arm in plan["arms"]:
                guard(plan)
                assert psutil.virtual_memory().available > 24 * 2**30
                assert shutil.disk_usage(root).free > 512 * 2**30
                with (root / f"{phase}-{arm['arm']}.log").open("xb") as log:
                    child = subprocess.Popen(
                        [
                            plan["python"],
                            "-P",
                            plan["driver"],
                            "worker",
                            str(plan_path),
                            "--arm",
                            arm["arm"],
                            "--phase",
                            phase,
                        ],
                        cwd=plan["work"],
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-mixed16-" + phase, arm=arm["arm"], child=identity)
                assert child.wait() == 0
                assert not alive(identity)
                result = read(root / f"{phase}-{arm['arm']}-result.json")
                target = Path(arm["prefix_checkpoint"] if phase == "prefix" else arm["target"])
                assert not target.exists()
                shutil.copy2(result["checkpoint"]["path"], target)
                assert ref(target)["sha256"] == result["checkpoint"]["sha256"]
                info["completed"][phase + "-" + arm["arm"]] = {
                    "result": ref(root / f"{phase}-{arm['arm']}-result.json"),
                    "checkpoint": ref(target),
                }
                record("completed-mixed16-" + phase, arm=arm["arm"], child=identity)
            if phase == "prefix":
                values = [read(root / f"prefix-{arm['arm']}-result.json") for arm in plan["arms"]]
                for key in [
                    "initial_RAW_state_SHA256",
                    "initial_Torch_RNG_SHA256",
                    "initial_Python_RNG_SHA256",
                ]:
                    assert values[0][key] == values[1][key]
                assert read(root / "no-dino-first16.json") == read(root / "dino-first16.json")
                record("matched-mixed16-prefixes-and-initial-data-verified")
        logs = []
        for arm in plan["arms"]:
            recipe = yaml.safe_load(Path(arm["config"]).read_text())
            rows = [
                json.loads(line)
                for line in (Path(recipe["run"]) / "metrics.jsonl").read_text().splitlines()
                if json.loads(line).get("event") == "train"
            ]
            assert [r["step"] for r in rows] == [1, 13, *range(25, 2001, 25)]
            logs.append(rows)
        for a, b in zip(*logs, strict=True):
            assert all(
                a[key] == b[key]
                for key in ["step", "lr", "batch_sha256", "source_groups", "example_draws"]
            )
        guard(plan)
        record(
            "completed-matched-mixed16-first32000-examples-awaiting-full-quality-review",
            all_logged_groups_noise_LR_and_example_counts_equal=True,
        )
    except BaseException as error:
        record("failed-no-automatic-restart-or-promotion", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "worker"])
    parser.add_argument("plan", type=Path)
    parser.add_argument("--arm", choices=["no-dino", "dino"])
    parser.add_argument("--phase", choices=["prefix", "finish"])
    args = parser.parse_args()
    if args.mode == "controller":
        controller(args.plan)
    else:
        worker(args.plan, args.arm, args.phase)
