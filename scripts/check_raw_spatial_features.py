"""Discarded16+2 checks of the optional RAW spatial branch from genuine V120.

This never schedules production training. It freezes the executed
source and prepared90781/29 cohort, then runs the ordinary training/resume and
portable loading paths under a separate fixed engineering budget.
"""

import argparse
import hashlib
import json
import os
import resource
import shutil
import signal
import time
from collections import Counter
from pathlib import Path

import psutil

REPO = Path(__file__).resolve().parents[1]
PREFIX = "pretrained_rgb.raw_spatial."


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def read(path):
    return json.loads(Path(path).read_text())


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def guard(plan):
    for binding in plan["inputs"] + plan["frozen_files"]:
        if ref(binding["path"]) != binding:
            raise ValueError(f"Changed implementation-check input: {binding['path']}")


def prepare(root, *, cpu_result=None, failed_cuda_plan=None):
    import yaml

    root = root.resolve()
    if not root.is_relative_to(REPO / ".cache"):
        raise ValueError("Implementation workspace must be in the repository cache")
    catalogue = REPO / "configs/low-contrast-training-rois-cleaned90781-v1.json"
    bank = read(catalogue)
    recipe = REPO / "configs/quality-v120-fp32-pilot-v130.yaml"
    config = yaml.safe_load(recipe.read_text())
    phase = "CUDA" if cpu_result is not None else "CPU"
    recovery = None
    if failed_cuda_plan is not None:
        assert phase == "CUDA"
        failed_plan = read(failed_cuda_plan)
        guard(failed_plan)
        failed_root = Path(failed_plan["root"])
        failure, launch = (
            read(failed_root / "failure-v1.json"),
            read(failed_root / "launch-v1.json"),
        )
        assert failure["counts"] == {} and failure["inputs"] == [] and failure["stage"] == "fresh"
        assert "CUBLAS_WORKSPACE_CONFIG=:4096:8" in failure["error"]
        owner = launch["owner"]
        assert (
            not psutil.pid_exists(owner["pid"])
            or abs(psutil.Process(owner["pid"]).create_time() - owner["created"]) > 0.01
        )
        assert not list(failed_root.rglob("*.pt")) and not list(failed_root.rglob("*.npz"))
        deadline = launch["start_unix"] + failed_plan["maximum_worker_seconds"]
        assert time.time() < deadline
        for source in (REPO / "src/demosaic").glob("*.py"):
            assert (
                source.read_bytes()
                == (Path(failed_plan["work"]) / "src/demosaic" / source.name).read_bytes()
            )
        recovery = {
            "failed_plan": ref(failed_cuda_plan),
            "failure": ref(failed_root / "failure-v1.json"),
            "original_launch": ref(failed_root / "launch-v1.json"),
            "zero_model_and_data_work": True,
            "all_neural_source_bytes_unchanged": True,
            "original_absolute_worker_deadline_unix": deadline,
            "change": "Set required deterministic cuBLAS environment before process startup; add an early environment guard. No automatic retry or budget reset.",
        }
    if cpu_result is not None:
        previous = read(cpu_result)
        assert previous["status"] == "completed-discarded-CPU-spatial-implementation-check"
        assert previous["all_Adam_steps"] == previous["counts"]["optimizer_steps"] == 18
        assert ref(previous["checkpoint"]["path"]) == previous["checkpoint"]
        guard(read(previous["plan"]["path"]))
        previous_work = Path(read(previous["plan"]["path"])["work"])
        # The only subsequent model-source edit is a new-flag-only tiling grid.
        # It is not used by the discarded training/direct-portable check.
        import ast

        for source in (REPO / "src/demosaic").glob("*.py"):
            old = previous_work / "src/demosaic" / source.name
            if source.name == "inference.py":

                def functions(path):
                    return {
                        node.name: ast.dump(node, include_attributes=False)
                        for node in ast.parse(path.read_text()).body
                        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    }

                old_functions, new_functions = functions(old), functions(source)
                assert old_functions.keys() == new_functions.keys()
                assert all(
                    old_functions[k] == new_functions[k]
                    for k in old_functions
                    if k != "restore_tiled"
                )
            else:
                assert source.read_bytes() == old.read_bytes(), source
    parent = {k: config["initialize_parent"][k] for k in ("path", "sha256")}
    assert ref(parent["path"]) == parent
    assert ref(bank["source_manifest"]["path"]) == bank["source_manifest"]
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = list((REPO / "src/demosaic").glob("*.py")) + [
        REPO / name
        for name in [
            "scripts/check_raw_spatial_features.py",
            "scripts/profile_raw_kernel_inference.py",
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/dinov3/LICENSE.md",
            "third_party/gaussian/KAIR-LICENSE",
            "third_party/gaussian/Noise2VST-LICENSE",
        ]
    ]
    frozen = []
    for source in files:
        destination = work / source.relative_to(REPO)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        frozen.append(ref(destination))
    config.update(
        device="cpu" if phase == "CPU" else "cuda",
        precision="float32" if phase == "CPU" else "bfloat16",
        amp=phase == "CUDA",
        batch_size=1 if phase == "CPU" else 16,
        patch_size=128 if phase == "CPU" else 256,
        seed=71,
        cpu_threads=2,
        workers=0,
        paired_workers=0,
        raw_clean_workers=0,
        steps=1000,
        log_every=1,
        checkpoint_every=500,
        min_available_gb=32,
        manifest=bank["source_manifest"]["path"],
        reviewed_roi_catalogue=str(catalogue),
        validation_protocol=str(work / "configs/evaluation.yaml"),
        run=str(work / "artifacts/implementation"),
        source_loss_every=0,
        experiment_notes=f"Discarded {phase} spatial-feature implementation check only:16 fresh+2 resumed updates, one zero-adapter witness and one CPU portable-forward check. Not production or trained-quality evidence.",
    )
    config["model"]["raw_spatial_features"] = True
    config_path = work / "configs" / (phase + "-spatial.yaml")
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    frozen.append(ref(config_path))
    rejected = dict(config, model=dict(config["model"], raw_spatial_features=False))
    rejected["run"] += "-rejected"
    reject_path = work / "configs" / (phase + "-rejected-model.yaml")
    reject_path.write_text(yaml.safe_dump(rejected, sort_keys=False))
    frozen.append(ref(reject_path))
    inputs = [parent, ref(recipe), ref(catalogue)]
    inputs += [
        ref(config[k])
        for k in [
            "manifest",
            "paired_manifest",
            "raw_clean_manifest",
            "validation_manifest",
            "photo_sampling_reference_manifest",
        ]
    ]
    if cpu_result is not None:
        inputs.append(ref(cpu_result))
    if recovery is not None:
        inputs.extend(recovery[k] for k in ["failed_plan", "failure", "original_launch"])
    plan = {
        "root": str(root),
        "phase": phase,
        "work": str(work),
        "config": ref(config_path),
        "rejected_config": ref(reject_path),
        "parent": parent,
        "inputs": inputs,
        "frozen_files": frozen,
        "worker": ref(work / "scripts/check_raw_spatial_features.py"),
        "initial_parent_tensors": 91,
        "new_tensors": 23,
        "actual_train_updates": 18,
        "fresh_updates": 16,
        "resume_updates": 2,
        "maximum_root_and_encoder_forwards": 20,
        "minimum_launch_available_RAM_GiB": 40 if phase == "CPU" else 52,
        "CUDA_allocator_cap_GiB": 16,
        "runtime_RAM_floor_GB": 32,
        "minimum_internal_free_GiB": 104,
        "maximum_worker_seconds": 1800,
        "completed_CPU_result": None if cpu_result is None else ref(cpu_result),
        "zero_work_CUDA_recovery": recovery,
        "scope": f"New {phase} implementation check on90781/29 data, seed71/native{'128/B1/FP32' if phase == 'CPU' else '256/B16/BF16'}, actual ordinary training loss and optimizer. Preserve16-step checkpoint, reject changed architecture before forwards, resume two new steps, verify finite state and learned CPU portable loading. One actual new first-batch disabled witness; no completed quality observations repeated. No production/quality/speed qualification, automatic retry or budget reset. CUDA check requires the completed CPU receipt and unchanged neural mathematics; only new-flag tile-grid handling differs from the old CPU loader source.",
    }
    path = root / "plan-v1.json"
    save(path, plan)
    return path


def worker(path):
    import numpy as np
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training
    from demosaic.inference import load_checkpoint
    from demosaic.raw_spatial_features import RawSpatialFeatures

    plan = read(path)
    phase = plan.get("phase", "CPU")
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    assert ref(__file__) == plan["worker"]
    assert Path(training.__file__).resolve().is_relative_to(work / "src")
    assert os.environ["CUDA_VISIBLE_DEVICES"] == ("" if phase == "CPU" else "0")
    if phase == "CPU":
        assert not torch.cuda.is_initialized()
    else:
        if os.environ.get("CUBLAS_WORKSPACE_CONFIG") != ":4096:8":
            raise ValueError("Set CUBLAS_WORKSPACE_CONFIG=:4096:8 before starting a CUDA check")
        torch.cuda.set_per_process_memory_fraction(
            plan["CUDA_allocator_cap_GiB"]
            * 2**30
            / torch.cuda.get_device_properties(0).total_memory
        )
    (root / "worker.claim").open("x").close()
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    assert psutil.virtual_memory().available >= plan["minimum_launch_available_RAM_GiB"] * 2**30
    assert shutil.disk_usage(root).free >= plan["minimum_internal_free_GiB"] * 2**30
    owner = {"pid": process.pid, "created": process.create_time()}
    save(root / "launch-v1.json", {"owner": owner, "plan": ref(path), "start_unix": time.time()})

    def deadline(*args):
        raise TimeoutError("Original implementation deadline exhausted")

    signal.signal(signal.SIGALRM, deadline)
    recovery = plan.get("zero_work_CUDA_recovery")
    deadline_unix = (
        recovery["original_absolute_worker_deadline_unix"]
        if recovery
        else time.time() + plan["maximum_worker_seconds"]
    )
    remaining = int(deadline_unix - time.time())
    if remaining <= 0:
        raise TimeoutError("Original implementation deadline already exhausted")
    signal.alarm(min(plan["maximum_worker_seconds"], remaining))
    config = yaml.safe_load(Path(plan["config"]["path"]).read_text())
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    counts, domains, gradients = Counter(), Counter(), {}
    inputs, initial_checks, captured = [], [], {}
    construction_rng_checks = []
    spatial_constructor = RawSpatialFeatures.__init__

    def construct_branch(module, *args, **kwargs):
        cpu_rng = torch.get_rng_state()
        cuda_rng = torch.cuda.get_rng_state_all() if phase == "CUDA" else []
        spatial_constructor(module, *args, **kwargs)
        assert torch.equal(cpu_rng, torch.get_rng_state())
        if phase == "CUDA":
            assert all(
                torch.equal(a, b)
                for a, b in zip(cuda_rng, torch.cuda.get_rng_state_all(), strict=True)
            )
        construction_rng_checks.append({"CPU_unchanged": True, "CUDA_unchanged": phase == "CUDA"})

    RawSpatialFeatures.__init__ = construct_branch
    stage, first_baseline, prefix = "fresh", None, None
    constructor, batch_factory, optimizer_factory = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )
    retained = root / "retained"
    retained.mkdir()

    def count_root(module, args):
        key = (
            "witness_forwards"
            if stage == "witness"
            else "training_forwards"
            if module.training
            else "validation_forwards"
        )
        counts[key] += 1

    def construct(options):
        nonlocal first_baseline
        module = constructor(options)
        captured["model"] = module
        module.register_forward_pre_hook(count_root)
        module.context.backbone.register_forward_hook(
            lambda *args: counts.update(encoder_forwards=1)
        )

        def initial(model, args):
            nonlocal stage, first_baseline
            handle.remove()
            assert stage != "rejected"
            state = model.restoration_state_dict()
            expected = parent["ema"] if stage == "fresh" else prefix["model"]
            assert len(state) == 114
            assert all(torch.equal(state[k].cpu(), v) for k, v in expected.items())
            assert model_hash(model.context.backbone) == config["expected_dino_sha256"]
            initial_checks.append(
                {
                    "stage": stage,
                    "parent91_or_prefix114_exact": True,
                    "official_encoder_exact": True,
                }
            )
            if stage == "fresh":
                branch = model.pretrained_rgb.raw_spatial
                assert branch.project.weight.count_nonzero() == 0
                # CPU portable execution uses one member of the new batch.
                captured["first_args"] = tuple(x[:1].detach().cpu().clone() for x in args)
                rng = torch.get_rng_state()
                stage = "witness"
                model.pretrained_rgb.raw_spatial = None
                try:
                    with torch.no_grad():
                        first_baseline = tuple(
                            x.detach().clone() for x in model(*args, auxiliary=True)
                        )
                finally:
                    model.pretrained_rgb.raw_spatial = branch
                    stage = "fresh"
                assert torch.equal(rng, torch.get_rng_state())

        def output(model, args, result):
            if stage == "fresh" and counts["training_forwards"] == 1 and first_baseline is not None:
                assert all(torch.equal(x, y) for x, y in zip(result, first_baseline, strict=True))
                captured["first_full_output_values_exact"] = sum(x.numel() for x in result)

        handle = module.register_forward_pre_hook(initial)
        module.register_forward_hook(output)
        return module

    def batch(step, domain, clean, **kwargs):
        assert stage != "rejected"
        value = batch_factory(step, domain, clean, **kwargs)
        counts["prepared_batches"] += 1
        domains[domain] += 1
        inputs.append(
            {"step": step, "domain": domain, "batch_sha256": training.batch_fingerprint(value)}
        )
        if step == 1:
            captured["first_noise"] = (
                value["shot"][:1].detach().cpu(),
                value["read"][:1].detach().cpu(),
            )
            target = retained / "first-training-batch.npz"
            with target.open("xb") as stream:
                np.savez(
                    stream,
                    **{
                        k: v.detach().cpu().numpy()
                        for k, v in value.items()
                        if isinstance(v, torch.Tensor)
                    },
                )
        return value

    def optimizer(model, options):
        result = optimizer_factory(model, options)
        assert sum(len(g["params"]) for g in result.param_groups) == (
            89 if stage == "rejected" else 112
        )

        def before_step(*args):
            for name, parameter in model.pretrained_rgb.raw_spatial.named_parameters():
                assert parameter.grad is not None and torch.isfinite(parameter.grad).all(), name
                gradients[name] = max(gradients.get(name, 0.0), float(parameter.grad.abs().max()))

        result.register_step_pre_hook(before_step)
        result.register_step_post_hook(lambda *args: counts.update(optimizer_steps=1))
        return result

    try:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            construct,
            batch,
            optimizer,
        )
        checkpoint = Path(
            training.train(plan["config"]["path"], initialize=plan["parent"]["path"], stop_after=16)
        )
        preserved = root / "step16.pt"
        os.link(checkpoint, preserved)
        prefix = torch.load(preserved, map_location="cpu", weights_only=True, mmap=True)
        assert prefix["step"] == 16
        stage = "rejected"
        before_counts = dict(counts)
        try:
            training.train(plan["rejected_config"]["path"], resume=preserved, stop_after=1)
        except ValueError as error:
            assert "model configuration differs" in str(error), str(error)
            rejected = str(error)
        else:
            raise AssertionError("Changed model accepted on resume")
        assert dict(counts) == before_counts
        stage = "resume"
        checkpoint = Path(training.train(plan["config"]["path"], resume=preserved, stop_after=2))
        final = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
        assert final["step"] == 18 and len(final["model"]) == len(final["ema"]) == 114
        states = final["optimizer"]["state"]
        assert len(states) == 112 and all(float(x["step"]) == 18 for x in states.values())
        assert all(torch.isfinite(v).all() for key in ["model", "ema"] for v in final[key].values())
        assert all(
            torch.isfinite(v).all()
            for state in states.values()
            for v in state.values()
            if isinstance(v, torch.Tensor)
        )
        assert len(gradients) == 23 and all(v > 0 for v in gradients.values())
        portable, _ = load_checkpoint(checkpoint, device="cpu")
        assert all(
            torch.equal(portable.restoration_state_dict()[k], v) for k, v in final["ema"].items()
        )
        assert model_hash(portable.context.backbone) == config["expected_dino_sha256"]
        portable.register_forward_pre_hook(lambda *args: counts.update(portable_forwards=1))
        portable.context.backbone.register_forward_hook(
            lambda *args: counts.update(encoder_forwards=1)
        )
        portable.set_noise(*captured["first_noise"])
        with torch.no_grad():
            value = portable(*captured["first_args"])
        assert torch.isfinite(value).all()
        assert counts == Counter(
            training_forwards=18,
            witness_forwards=1,
            portable_forwards=1,
            encoder_forwards=20,
            prepared_batches=18,
            optimizer_steps=18,
        )
        guard(plan)
        assert torch.cuda.is_initialized() == (phase == "CUDA")
        assert len(construction_rng_checks) == 3
        save(
            root / "result-v1.json",
            {
                "status": f"completed-discarded-{phase}-spatial-implementation-check",
                "phase": phase,
                "plan": ref(path),
                "owner": owner,
                "checkpoint": ref(checkpoint),
                "preserved_step16": ref(preserved),
                "counts": dict(counts),
                "domains": dict(domains),
                "initial_checks": initial_checks,
                "branch_construction_RNG_checks": construction_rng_checks,
                "forward_devices": {"cpu": 20} if phase == "CPU" else {"cuda": 19, "cpu": 1},
                "model_EMA_Adam_finite": True,
                "all_Adam_steps": 18,
                "new_parameter_tensors": 23,
                "new_parameters": sum(
                    p.numel() for p in portable.pretrained_rgb.raw_spatial.parameters()
                ),
                "model_and_EMA_tensors": 114,
                "optimizer_states": 112,
                "gradient_maxima": gradients,
                "inputs": inputs,
                "first_full_output_values_exact": captured["first_full_output_values_exact"],
                "portable_EMA114_exact": True,
                "rejected_resume": rejected,
                "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
                "CUDA_initialized": phase == "CUDA",
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated()
                if phase == "CUDA"
                else 0,
                "scope": plan["scope"],
            },
        )
    except BaseException as error:
        save(
            root / "failure-v1.json",
            {
                "error": repr(error),
                "stage": stage,
                "counts": dict(counts),
                "inputs": inputs,
                "owner": owner,
                "no_automatic_retry": True,
            },
        )
        raise
    finally:
        signal.alarm(0)
        RawSpatialFeatures.__init__ = spatial_constructor
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            constructor,
            batch_factory,
            optimizer_factory,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "worker"])
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--cpu-result", type=Path, help="Prepare a new CUDA check after this completed CPU result"
    )
    parser.add_argument(
        "--failed-cuda-plan",
        type=Path,
        help="Explicitly recover the zero-work cuBLAS-environment failure within its original deadline",
    )
    args = parser.parse_args()
    if args.mode == "prepare":
        print(
            prepare(args.path, cpu_result=args.cpu_result, failed_cuda_plan=args.failed_cuda_plan)
        )
    else:
        worker(args.path.resolve())
