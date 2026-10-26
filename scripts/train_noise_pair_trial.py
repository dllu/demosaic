"""Train matched independent-noise mean-loss arms from one immutable Small parent."""

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

ARM_WEIGHTS = {"V124": 0.0, "V125": 0.25}


def prepare(root, dependencies):
    import yaml

    from demosaic.noise_pairs import POLICY, noise_pair_options
    from demosaic.train import training_domain

    recipes = [REPO / f"configs/quality-v120-independent-noise-mean-v{v}.yaml" for v in (124, 125)]
    configs = [yaml.safe_load(p.read_text()) for p in recipes]
    ignored = {"run", "experiment_notes", "conditional_mean_weight"}
    assert {k: v for k, v in configs[0].items() if k not in ignored} == {
        k: v for k, v in configs[1].items() if k not in ignored
    }
    for config, weight in zip(configs, ARM_WEIGHTS.values(), strict=True):
        assert noise_pair_options(config) == (2, weight)
        assert config["seed"] == 67 and config["steps"] == 20000
        assert all(config[key] == 0 for key in ("workers", "paired_workers", "raw_clean_workers"))
    dependency_bindings = []
    for item in dependencies:
        status = read(item["status_path"])
        binding = ref(item["plan_path"])
        assert status[item["plan_field"]] == binding and live(status[item["owner_field"]])
        assert not status["status"].startswith("failed")
        dependency_bindings.append({**item, "plan": binding, "owner": status[item["owner_field"]]})
    assert dependency_bindings, "Production must follow the already-running quality chain"
    path = prepare_recipes(root, root / "work/artifacts", recipes)
    plan = read(path)
    work = Path(plan["work"])
    worker_script = work / "scripts/train_noise_pair_trial.py"
    shutil.copyfile(__file__, worker_script)
    for arm in plan["arms"]:
        cpu = Path(plan["arms"][arm]["CPU"])
        config = yaml.safe_load(cpu.read_text())
        config["patch_size"] = 128
        cpu.write_text(yaml.safe_dump(config, sort_keys=False))
        for phase in ("CPU", "CUDA"):
            original = yaml.safe_load(Path(plan["arms"][arm][phase]).read_text())
            for change in ("weight", "draws"):
                config = dict(original)
                if change == "weight":
                    config["conditional_mean_weight"] = 0.25 if ARM_WEIGHTS[arm] == 0 else 0.0
                else:
                    config.update(
                        noise_pair_draws=1, noise_pair_policy=None, conditional_mean_weight=0.0
                    )
                config["run"] += f"-rejected-{change}-resume"
                reject = work / "configs" / f"{phase}-{arm}-rejected-{change}-resume.yaml"
                reject.write_text(yaml.safe_dump(config, sort_keys=False))
                plan["arms"][arm][f"{phase}_rejected_{change}_resume"] = str(reject)
    plan.update(
        training_format="independent-noise-mean-v1",
        worker_script=ref(worker_script),
        smoke_updates=16,
        resume_new_updates=2,
        launch_available_RAM_GiB=64,
        runtime_available_RAM_GB=32,
        CUDA_allocator_cap_GiB=24,
        arm_weights=ARM_WEIGHTS,
        noise_pair_policy=POLICY,
        dependencies=dependency_bindings,
        maximum_dependency_wait_seconds=604800,
        maximum_headroom_wait_seconds=7200,
        maximum_smoke_worker_seconds=1800,
        maximum_train_worker_seconds=172800,
        scope="Matched fresh20000 V120 Small continuations on90784 sources/20ROIs, seed67. Both load16 unique targets once and simulate two independent views (physical32) for Commons/native; real paired stays16. V124 per-view loss; V125 .75 per-view+.25 mean-prediction loss. CPU128/B1 FP32 and CUDA256/B16 BF16 discarded16+2 resume precede fresh production. Production waits for exact original V122/V123 training/quality/audit/report/mesh owners. No old inference repetition, automatic retry or budget extension.",
    )
    plan["prospective_domain_batches"] = dict(
        Counter(training_domain(s, 67, 0.25, 0.25) for s in range(1, 20001))
    )
    plan["inputs"].extend(d["plan"] for d in dependency_bindings)
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    save(path, plan)
    guard(plan)
    return path


def adopt_prepared_checks(root, previous):
    """Rebind unstarted phases, preserving the original plan and worker bytes."""
    old = read(previous)
    guard(old)
    old_root = Path(old["root"])
    status = read(old_root / "status.json")
    assert status["plan"] == ref(previous) and live(status["controller"])
    assert (status["status"], status["phase"], status["arm"]) == (
        "waiting-for-noise-pair-training-headroom",
        "CUDA",
        "V125",
    )
    expected = {"CPU-V124", "CPU-V125", "CUDA-V124"}
    assert set(status["completed"]) == expected
    assert not (old_root / "CUDA-V125.claim").exists()
    inputs = [ref(previous)]
    for binding in status["completed"].values():
        assert ref(binding["path"]) == binding
        receipt = read(binding["path"])
        assert not live(receipt["owner"]) and receipt["updates"] == 18
        assert receipt["status"] == "completed-noise-pair-training-phase"
        assert receipt["model_EMA_Adam_finite"] and receipt["all_AdamW_steps"] == 18
        inputs.append(binding)
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    controller_source = root / "controller-source-v1.py"
    shutil.copyfile(__file__, controller_source)
    snapshot = root / "adopted-status-v1.json"
    save(snapshot, status)
    plan = {
        **old,
        "root": str(root),
        "adopted_worker_plan": ref(previous),
        "output_worker_root": str(old_root),
        "replaced_controller": status["controller"],
        "adopted_phase_results": status["completed"],
        "phase_launch_available_RAM_GiB": {"CUDA": 56},
        "controller_script": ref(controller_source),
        "inputs": [*old["inputs"], *inputs, ref(snapshot)],
        "frozen_files": {
            **old["frozen_files"],
            str(controller_source): ref(controller_source)["sha256"],
        },
        "adoption_scope": (
            "Reuse three completed checks, with no repeated training or inference. "
            "Only the unstarted CUDA-V125 launch floor changes from64 to56GiB. "
            "Original worker/source/config/data,24GiB allocator cap,32GB runtime floor, "
            "full-run64GiB launch floor and all worker wall budgets remain unchanged."
        ),
    }
    path = root / "plan.json"
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
    assert arm in ARM_WEIGHTS and phase in ("CPU", "CUDA", "train")
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
    weight = ARM_WEIGHTS[arm]
    assert config["conditional_mean_weight"] == weight and config["noise_pair_draws"] == 2
    assert config["min_available_gb"] == plan["runtime_available_RAM_GB"]
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    expected_states = 89
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
    if arm == "V125" and phase != "train":
        matched = read(root / f"{phase}-V124-result.json")
    if phase == "train":
        matched = read(root / f"CUDA-{arm}-result.json")
    expected_inputs = (
        {r["step"]: r["batch_sha256"] for r in matched["observed_inputs"]} if matched else {}
    )

    def construct(options):
        assert current != "rejected-resume", "Resume must be rejected before model construction"
        model = constructor(options)
        captured["model"] = model

        def before(module, args):
            counts["training_forwards" if module.training else "validation_forwards"] += 1

        def encoder(*args):
            counts["encoder_forwards"] += 1

        def initial(module, args):
            assert current != "rejected-resume"
            state = module.restoration_state_dict()
            assert len(state) == 91 and state.keys() == parent["ema"].keys()
            assert model_hash(module.context.backbone) == config["expected_dino_sha256"]
            assert all(
                not p.requires_grad and p.grad is None for p in module.context.backbone.parameters()
            )
            if current == "fresh":
                assert all(torch.equal(state[k].cpu(), v) for k, v in parent["ema"].items())
                assert not captured["optimizer"].state
            else:
                assert step16 is not None
                assert all(torch.equal(state[k].cpu(), v) for k, v in step16["model"].items())
                assert len(captured["optimizer"].state) == expected_states
                assert all(float(s["step"]) == 16 for s in captured["optimizer"].state.values())
            selected = [n for n, p in module.named_parameters() if p.requires_grad]
            assert len(selected) == expected_states
            initials.append(
                {
                    "phase": current,
                    "parent_or_resumed91_exact": True,
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
        assert domain == training.training_domain(step, 67, 0.25, 0.25)
        value = batch_factory(step, domain, clean, **kwargs)
        counts["prepared_training_batches"] += 1
        size = len(
            clean[
                "rgb" if domain == "commons" else "camera_rgb" if domain == "native" else "packed"
            ]
        )
        assert size == config["batch_size"]
        assert len(value["packed"]) == size * (1 if domain == "paired" else 2)
        if domain != "paired":
            from demosaic.noise_pairs import validate_noise_pair_batch

            assert validate_noise_pair_batch(value) == size
        else:
            assert "noise_pair_id" not in value and "noise_view" not in value
        counts["unique_target_contexts"] += size
        counts["sensor_observations"] += len(value["packed"])
        domains[domain] += 1
        if step <= 18:
            digest = training.batch_fingerprint(value)
            if step in expected_inputs:
                assert digest == expected_inputs[step], (phase, arm, step)
            row = {"step": step, "domain": domain, "batch_sha256": digest}
            if arm == "V124" and phase != "train":
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
        assert all(group["lr"] == 1e-5 for group in result.param_groups)

        def before_step(*args):
            assert current != "rejected-resume"
            if phase != "train" or counts["optimizer_steps"] < 16:
                for name, parameter in model.named_parameters():
                    if parameter.requires_grad:
                        assert (
                            parameter.grad is not None and torch.isfinite(parameter.grad).all()
                        ), name
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
            rejected = {}
            for change in ("weight", "draws"):
                try:
                    training.train(
                        plan["arms"][arm][f"{phase}_rejected_{change}_resume"],
                        resume=preserved,
                        stop_after=1,
                    )
                except ValueError as error:
                    assert "Resume independent-noise policy or mean weight differs" in str(error)
                    rejected[change] = str(error)
                else:
                    raise AssertionError(f"Changed independent-noise {change} accepted on resume")
                assert dict(counts) == before_counts
            current = "resume"
            last = Path(training.train(plan["arms"][arm][phase], resume=preserved, stop_after=2))
            expected += 2
        final = torch.load(last, map_location="cpu", weights_only=True, mmap=True)
        assert final["step"] == expected and len(final["model"]) == len(final["ema"]) == 91
        assert len(final["optimizer"]["state"]) == expected_states
        assert all(float(s["step"]) == expected for s in final["optimizer"]["state"].values())
        assert all(torch.isfinite(v).all() for k in ("model", "ema") for v in final[k].values())
        assert all(
            torch.isfinite(v).all()
            for s in final["optimizer"]["state"].values()
            for v in s.values()
            if isinstance(v, torch.Tensor)
        )
        assert len(gradients) == expected_states and any(v > 0 for v in gradients.values())
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
                "status": "completed-noise-pair-training-phase",
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
                "conditional_mean_weight": weight,
                "noise_pair_draws": 2,
                "changed_noise_policy_resume_rejections": rejected,
                "model_EMA_Adam_finite": True,
                "frozen_encoder_no_gradients": True,
                "all_AdamW_steps": expected,
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
        "completed": dict(plan.get("adopted_phase_results", {})),
    }
    child = owner = None

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    try:
        if plan.get("replaced_controller"):
            assert not live(plan["replaced_controller"])
        for phase in ("CPU", "CUDA", "train"):
            if phase == "train":
                began_wait = time.monotonic()
                record("waiting-for-original-quality-chain", phase=phase, child=None)
                while True:
                    assert time.monotonic() - began_wait < plan["maximum_dependency_wait_seconds"]
                    complete = True
                    for dep in plan["dependencies"]:
                        assert ref(dep["plan"]["path"]) == dep["plan"]
                        status = read(dep["status_path"])
                        assert status[dep["plan_field"]] == dep["plan"]
                        assert status[dep["owner_field"]] == dep["owner"]
                        assert not status["status"].startswith("failed"), status
                        if live(dep["owner"]):
                            complete = False
                        else:
                            assert status["status"] == dep["terminal_status"], status
                    if complete:
                        record("original-quality-chain-completed", dependencies_checked=True)
                        break
                    time.sleep(15)
            for arm in ARM_WEIGHTS:
                guard(plan)
                if binding := state["completed"].get(f"{phase}-{arm}"):
                    assert ref(binding["path"]) == binding
                    assert not live(read(binding["path"])["owner"])
                    record("adopted-completed-noise-pair-check", phase=phase, arm=arm)
                    continue
                record("waiting-for-noise-pair-training-headroom", phase=phase, arm=arm)
                began, stable = time.monotonic(), None
                while True:
                    assert time.monotonic() - began < plan["maximum_headroom_wait_seconds"]
                    enough = (
                        psutil.virtual_memory().available
                        >= plan.get("phase_launch_available_RAM_GiB", {}).get(
                            phase, plan["launch_available_RAM_GiB"]
                        )
                        * 2**30
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
                            plan.get("adopted_worker_plan", {"path": str(path)})["path"],
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
                    record("running-noise-pair-training", phase=phase, arm=arm, child=owner)
                    started = time.monotonic()
                    while child.poll() is None:
                        assert (
                            time.monotonic() - started
                            < plan[
                                "maximum_train_worker_seconds"
                                if phase == "train"
                                else "maximum_smoke_worker_seconds"
                            ]
                        )
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
                result = Path(plan.get("output_worker_root", root)) / f"{phase}-{arm}-result.json"
                assert read(result)["owner"] == owner and not live(owner)
                state["completed"][f"{phase}-{arm}"] = ref(result)
                record("completed-noise-pair-training-phase")
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
        record("failed-noise-pair-training-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "adopt", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--dependencies", type=Path)
    parser.add_argument("--previous-plan", type=Path)
    parser.add_argument("--arm", choices=tuple(ARM_WEIGHTS))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve(), read(args.dependencies)))
    elif args.mode == "adopt":
        print(adopt_prepared_checks(args.path.resolve(), args.previous_plan.resolve()))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve(), args.phase, args.arm)
