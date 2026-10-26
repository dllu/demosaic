"""Train matched learned-frequency scopes from one immutable Small parent."""

import argparse
import gc
import os
import shutil
import signal
import subprocess
import time
from collections import Counter
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO
from train_quality_recipes import prepare as prepare_recipes
from train_v43_quality_trial import live

PREFIX = "pretrained_rgb.raw_frequency."
ARM_SCOPES = {"V122": True, "V123": False}


def prepare(root):
    import yaml

    from demosaic.train import training_domain

    recipes = [
        REPO / f"configs/quality-v115-learned-frequency-{scope}-v{version}.yaml"
        for scope, version in (("only", 122), ("joint", 123))
    ]
    configs = [yaml.safe_load(p.read_text()) for p in recipes]
    ignored = {"run", "experiment_notes", "raw_frequency_only", "lr", "raw_frequency_lr_multiplier"}
    assert {k: v for k, v in configs[0].items() if k not in ignored} == {
        k: v for k, v in configs[1].items() if k not in ignored
    }
    for config, only in zip(configs, ARM_SCOPES.values(), strict=True):
        assert config["raw_frequency_only"] is only
        assert config["lr"] * config["raw_frequency_lr_multiplier"] == 2e-4
        assert config["model"]["raw_frequency_features"] is True
        assert config["seed"] == 66 and config["steps"] == 20000
        assert all(config[key] == 0 for key in ("workers", "paired_workers", "raw_clean_workers"))
    path = prepare_recipes(root, root / "work/artifacts", recipes)
    plan = read(path)
    work = Path(plan["work"])
    worker_script = work / "scripts/train_raw_frequency_trial.py"
    shutil.copyfile(__file__, worker_script)
    for arm in plan["arms"]:
        cpu = Path(plan["arms"][arm]["CPU"])
        config = yaml.safe_load(cpu.read_text())
        config["patch_size"] = 128
        cpu.write_text(yaml.safe_dump(config, sort_keys=False))
        for phase in ("CPU", "CUDA"):
            config = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
            config["raw_frequency_only"] = not ARM_SCOPES[arm]
            config["run"] += "-rejected-scope-resume"
            reject = work / "configs" / f"{phase}-{arm}-rejected-resume.yaml"
            reject.write_text(yaml.safe_dump(config, sort_keys=False))
            plan["arms"][arm][phase + "_rejected_resume"] = str(reject)
    plan.update(
        worker_script=ref(worker_script),
        smoke_updates=16,
        resume_new_updates=2,
        launch_available_RAM_GiB=56,
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=16,
        arm_scopes=ARM_SCOPES,
        scope=(
            "Matched fresh20000 V115 Small learned-frequency trials on90786 sources/14ROIs, "
            "seed66, correctedpaired32/native128. V122 trains only3264 new adapter parameters; "
            "V123 trains common restoration plus adapter. Both adapterLR2e-4. CPU128/B1/FP32 "
            "and CUDA256/B16/BF16 discarded16+2 resumed updates precede fresh production. "
            "No old evaluation inference or automatic retry/budget extension."
        ),
    )
    plan["prospective_domain_batches"] = dict(
        Counter(training_domain(s, 66, 0.25, 0.25) for s in range(1, 20001))
    )
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


def worker(path, phase, arm):
    import numpy as np
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training

    plan = read(path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    assert arm in ARM_SCOPES and phase in ("CPU", "CUDA", "train")
    assert Path(training.__file__).absolute().is_relative_to(work / "src")
    assert ref(__file__) == plan["worker_script"]
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ("" if phase == "CPU" else "0")
    (root / f"{phase}-{arm}.claim").open("x").close()
    if phase == "CPU":
        psutil.Process().cpu_affinity(psutil.Process().cpu_affinity()[:2])
        assert not torch.cuda.is_initialized()
    else:
        torch.cuda.set_per_process_memory_fraction(
            plan["CUDA_allocator_cap_GiB"]
            * 2**30
            / torch.cuda.get_device_properties(0).total_memory
        )
    config = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
    only = ARM_SCOPES[arm]
    assert config["raw_frequency_only"] is only
    assert config["min_available_gb"] == plan["runtime_available_RAM_GB"]
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    expected_states = 5 if only else 94
    counts, domains, inputs, initials, gradients = Counter(), Counter(), [], [], {}
    captured, current, step16 = {}, "fresh", None
    constructor, batch_factory, optimizer_factory = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )
    output_dir = root / "retained" / phase / arm
    output_dir.mkdir(parents=True, exist_ok=False)
    matched = None
    if arm == "V123" and phase != "train":
        matched = read(root / f"{phase}-V122-result.json")
    if phase == "train":
        matched = read(root / f"CUDA-{arm}-result.json")
    expected_inputs = (
        {r["step"]: r["batch_sha256"] for r in matched["observed_inputs"]} if matched else {}
    )

    def construct(options):
        model = constructor(options)
        captured["model"] = model

        def before(module, args):
            counts["training_forwards" if module.training else "validation_forwards"] += 1

        def encoder(*args):
            counts["encoder_forwards"] += 1

        def initial(module, args):
            assert current != "rejected-resume"
            state = module.restoration_state_dict()
            extra = state.keys() - parent["ema"].keys()
            assert len(state) == 96 and len(extra) == 5 and all(k.startswith(PREFIX) for k in extra)
            assert model_hash(module.context.backbone) == config["expected_dino_sha256"]
            assert all(
                not p.requires_grad and p.grad is None for p in module.context.backbone.parameters()
            )
            if current == "fresh":
                assert all(torch.equal(state[k].cpu(), v) for k, v in parent["ema"].items())
                assert module.pretrained_rgb.raw_frequency.project.weight.count_nonzero() == 0
                assert not captured["optimizer"].state
            else:
                assert step16 is not None
                assert all(torch.equal(state[k].cpu(), v) for k, v in step16["model"].items())
                assert len(captured["optimizer"].state) == expected_states
                assert all(float(s["step"]) == 16 for s in captured["optimizer"].state.values())
            selected = [n for n, p in module.named_parameters() if p.requires_grad]
            assert len(selected) == expected_states
            if only:
                assert all(n.startswith(PREFIX) for n in selected)
                assert sum(p.numel() for p in module.parameters() if p.requires_grad) == 3264
            initials.append(
                {
                    "phase": current,
                    "common91_or_resumed96_exact": True,
                    "trainable_tensors": len(selected),
                    "official_encoder_exact": True,
                }
            )
            first_hook.remove()

        def first_output(module, args, result):
            if current == "fresh" and counts["training_forwards"] == 1:
                arrays = {f"output_{i}": v.detach().cpu().numpy() for i, v in enumerate(result)}
                with (output_dir / "first-outputs.npz").open("xb") as stream:
                    np.savez(stream, **arrays)
                assert all(v.dtype == np.float32 and np.isfinite(v).all() for v in arrays.values())

        model.register_forward_pre_hook(before)
        first_hook = model.register_forward_pre_hook(initial)
        model.register_forward_hook(first_output)
        model.context.backbone.register_forward_hook(encoder)
        return model

    def batch(step, domain, clean, **kwargs):
        assert current != "rejected-resume"
        assert domain == training.training_domain(step, 66, 0.25, 0.25)
        value = batch_factory(step, domain, clean, **kwargs)
        counts["prepared_training_batches"] += 1
        domains[domain] += 1
        if step <= 18:
            digest = training.batch_fingerprint(value)
            if step in expected_inputs:
                assert digest == expected_inputs[step], (phase, arm, step)
            row = {"step": step, "domain": domain, "batch_sha256": digest}
            if arm == "V122" and phase != "train":
                pixels = output_dir / f"step-{step:02d}.npz"
                with pixels.open("xb") as stream:
                    np.savez(
                        stream,
                        **{
                            k: v.detach().cpu().contiguous().numpy()
                            for k, v in value.items()
                            if isinstance(v, torch.Tensor)
                        },
                    )
                row["prepared_tensors"] = ref(pixels)
            inputs.append(row)
        return value

    def optimizer(model, options):
        result = optimizer_factory(model, options)
        captured["optimizer"] = result
        assert not result.state
        assert sum(len(g["params"]) for g in result.param_groups) == expected_states
        branch_group = next(
            g
            for g in result.param_groups
            if any(p is model.pretrained_rgb.raw_frequency.project.weight for p in g["params"])
        )
        assert branch_group["lr"] == 2e-4

        def before_step(*args):
            assert current != "rejected-resume"
            if only:
                assert all(
                    p.grad is None for n, p in model.named_parameters() if not n.startswith(PREFIX)
                )
            if phase != "train" or counts["optimizer_steps"] < 16:
                for name, parameter in model.pretrained_rgb.raw_frequency.named_parameters():
                    assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
                    gradients[name] = max(
                        gradients.get(name, 0.0), float(parameter.grad.abs().max())
                    )

        result.register_step_pre_hook(before_step)
        result.register_step_post_hook(lambda *args: counts.update(optimizer_steps=1))
        return result

    try:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            construct,
            batch,
            optimizer,
        )
        expected = plan["train_updates"] if phase == "train" else plan["smoke_updates"]
        last = Path(
            training.train(
                plan["arms"][arm][phase], initialize=plan["parent"]["path"], stop_after=expected
            )
        )
        rejected = None
        if phase != "train":
            preserved = root / f"{phase}-{arm}-step16.pt"
            os.link(last, preserved)
            step16 = torch.load(preserved, map_location="cpu", weights_only=True, mmap=True)
            assert step16["step"] == 16
            current = "rejected-resume"
            before_counts = dict(counts)
            try:
                training.train(
                    plan["arms"][arm][phase + "_rejected_resume"], resume=preserved, stop_after=1
                )
            except ValueError as error:
                assert "Resume RAW frequency training scope differs" in str(error)
                rejected = str(error)
            else:
                raise AssertionError("Changed trainable scope accepted on resume")
            assert dict(counts) == before_counts
            current = "resume"
            last = Path(training.train(plan["arms"][arm][phase], resume=preserved, stop_after=2))
            expected += 2
        final = torch.load(last, map_location="cpu", weights_only=True, mmap=True)
        assert final["step"] == expected and len(final["model"]) == len(final["ema"]) == 96
        assert len(final["optimizer"]["state"]) == expected_states
        assert all(float(s["step"]) == expected for s in final["optimizer"]["state"].values())
        assert all(torch.isfinite(v).all() for k in ("model", "ema") for v in final[k].values())
        assert all(
            torch.isfinite(v).all()
            for s in final["optimizer"]["state"].values()
            for v in s.values()
            if isinstance(v, torch.Tensor)
        )
        if only:
            for key, value in parent["ema"].items():
                assert torch.equal(final["model"][key], value) and torch.equal(
                    final["ema"][key], value
                ), key
        assert all(v > 0 for v in gradients.values()) and len(gradients) == 5
        assert (
            counts["training_forwards"]
            == counts["optimizer_steps"]
            == counts["prepared_training_batches"]
            == expected
        )
        assert counts["validation_forwards"] == (640 if phase == "train" else 0)
        assert (
            counts["encoder_forwards"]
            == counts["training_forwards"] + counts["validation_forwards"]
        )
        if phase == "train":
            assert dict(domains) == plan["prospective_domain_batches"]
        if matched:
            with (
                np.load(output_dir / "first-outputs.npz", allow_pickle=False) as current_outputs,
                np.load(
                    Path(matched["first_outputs"]["path"]), allow_pickle=False
                ) as previous_outputs,
            ):
                assert all(
                    np.array_equal(current_outputs[k], previous_outputs[k])
                    for k in current_outputs.files
                )
        assert model_hash(captured["model"].context.backbone) == config["expected_dino_sha256"]
        guard(plan)
        save(
            root / f"{phase}-{arm}-result.json",
            {
                "status": "completed-frequency-training-phase",
                "phase": phase,
                "arm": arm,
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                "updates": expected,
                "checkpoint": ref(last),
                "first_outputs": ref(output_dir / "first-outputs.npz"),
                "source_sha256": final["config"]["source_sha256"],
                "counts": dict(counts),
                "domain_counts": dict(domains),
                "observed_inputs": inputs,
                "initial_checks": initials,
                "new_parameter_maximum_absolute_gradients": gradients,
                "common91_model_and_EMA_exact_to_parent": only,
                "changed_scope_resume_rejection": rejected,
                "optimizer_state_count": expected_states,
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated()
                if phase != "CPU"
                else 0,
                "CUDA_peak_reserved_bytes": torch.cuda.max_memory_reserved()
                if phase != "CPU"
                else 0,
                "scope": "Discarded implementation check"
                if phase != "train"
                else "Full endpoint; image-quality review remains required",
            },
        )
    except BaseException as error:
        save(
            root / f"{phase}-{arm}-failure.json",
            {
                "error": repr(error),
                "counts": dict(counts),
                "current": current,
                "observed_inputs": inputs,
                "status": "failed-preserved-no-automatic-retry",
            },
        )
        raise
    finally:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            constructor,
            batch_factory,
            optimizer_factory,
        )
        captured.clear()
        gc.collect()


def controller(path):
    plan = read(path)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    try:
        for phase in ("CPU", "CUDA", "train"):
            for arm in ARM_SCOPES:
                guard(plan)
                record("waiting-for-frequency-training-headroom", phase=phase, arm=arm)
                began, stable = time.monotonic(), None
                while True:
                    assert time.monotonic() - began < 7200
                    enough = (
                        psutil.virtual_memory().available
                        >= plan["launch_available_RAM_GiB"] * 2**30
                        and shutil.disk_usage(root).free
                        >= plan["phase_start_internal_free_GiB"] * 2**30
                        and shutil.disk_usage("/mnt/external").free
                        >= plan["phase_start_external_free_GiB"] * 2**30
                    )
                    stable = (time.monotonic() if stable is None else stable) if enough else None
                    if stable is not None and time.monotonic() - stable >= 15:
                        break
                    time.sleep(2)
                work = Path(plan["work"])
                env = dict(
                    os.environ,
                    PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
                    CUDA_VISIBLE_DEVICES="" if phase == "CPU" else "0",
                    HF_HUB_OFFLINE="1",
                    TRANSFORMERS_OFFLINE="1",
                    OMP_NUM_THREADS="2",
                    OPENBLAS_NUM_THREADS="1",
                    CUBLAS_WORKSPACE_CONFIG=":4096:8",
                )
                with (root / f"{phase}-{arm}.log").open("x") as log:
                    child = subprocess.Popen(
                        [
                            plan["python"],
                            "-P",
                            plan["worker_script"]["path"],
                            "worker",
                            str(path),
                            "--phase",
                            phase,
                            "--arm",
                            arm,
                        ],
                        cwd=work,
                        env=env,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                    record("running-frequency-training", phase=phase, arm=arm, child=owner)
                    started = time.monotonic()
                    while child.poll() is None:
                        assert time.monotonic() - started < (86400 if phase == "train" else 1200)
                        assert (
                            shutil.disk_usage(root).free
                            > plan["runtime_internal_reserve_GiB"] * 2**30
                        )
                        assert (
                            shutil.disk_usage("/mnt/external").free
                            > plan["runtime_external_reserve_GiB"] * 2**30
                        )
                        time.sleep(2)
                    assert child.wait() == 0, (phase, arm, child.returncode)
                result = root / f"{phase}-{arm}-result.json"
                assert read(result)["owner"] == owner and not live(owner)
                state["completed"][f"{phase}-{arm}"] = ref(result)
                record("completed-frequency-training-phase")
        record("completed-training-awaiting-model-comparisons")
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-frequency-training-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=tuple(ARM_SCOPES))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
