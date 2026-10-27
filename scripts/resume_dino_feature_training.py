"""Continue a memory-guard checkpoint once, preserving the original update/deadline budget."""

import argparse
import gc
import os
import random
import shutil
import signal
import subprocess
import time
from collections import Counter
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_quality_recipes import REPO
from train_v43_quality_trial import live


def remaining_budget(snapshot, failure, total):
    """The emergency checkpoint must contain every counted optimizer update."""
    first = snapshot["step"]
    counts = failure["counts"]
    if not 0 < first < total or any(
        counts[key] != first
        for key in ("optimizer_steps", "training_forwards", "prepared_training_batches")
    ):
        raise ValueError("Checkpoint and actual spent-update counters differ")
    if counts["encoder_forwards"] != first + counts.get("validation_forwards", 0):
        raise ValueError("Original encoder budget differs")
    states = snapshot["optimizer"]["state"]
    if len(states) != 89 or any(float(s["step"]) != first for s in states.values()):
        raise ValueError("Emergency AdamW state is incomplete")
    return total - first


def finite_state(state):
    import torch

    assert len(state["model"]) == len(state["ema"]) == 91
    assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in state[key].values())
    assert all(
        torch.isfinite(v).all()
        for s in state["optimizer"]["state"].values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    )


def prepare(root, original_root):
    import torch
    import yaml

    from demosaic.train import training_domain

    root, original_root = root.resolve(), original_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    original = read(original_root / "plan.json")
    guard(original)
    failed = read(original_root / "status.json")
    assert failed["status"] == "failed-training-preserved-no-automatic-retry"
    assert failed["arm"] == "V128" and failed["phase"] == "train"
    assert not live(failed["controller"]) and not live(failed["child"])
    failure_path = original_root / "train-V128-failure.json"
    failure = read(failure_path)
    assert failure["error"].startswith("RuntimeError('Stopping safely: only ")
    assert failure["current"] == "fresh"
    checkpoint = Path(original["artifact_root"]) / "train/V128/last.pt"
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    remaining = remaining_budget(state, failure, original["train_updates"])
    finite_state(state)
    assert state["torch_rng"].dtype == torch.uint8 and state["cuda_rng"]
    config = yaml.safe_load(Path(original["arms"]["V128"]["train"]).read_text())
    assert config["steps"] == 1000 and config["data_seed_per_step"] is True
    assert config["seed"] == 70 and config["dino_feature_weight"] == 0.1
    assert all(config[k] == 0 for k in ("workers", "paired_workers", "raw_clean_workers"))
    control_binding = original["matched_control_results"]["train"]
    assert ref(control_binding["path"]) == control_binding
    control = read(control_binding["path"])
    prefix_inputs = failure["observed_inputs"]
    assert len(prefix_inputs) == state["step"]
    for actual, expected in zip(prefix_inputs, control["observed_inputs"], strict=False):
        assert all(
            actual[k] == expected[k] for k in ("step", "domain", "clean_sha256", "batch_sha256")
        )
    deadline = failed["child"]["created"] + original["maximum_train_worker_seconds"]
    # Conservatively retain the original controller's first2h admission clock.
    headroom_deadline = min(failed["controller"]["created"] + 7200, deadline)
    assert time.time() < headroom_deadline < deadline
    root.mkdir(parents=True, exist_ok=False)
    script = root / "resume_dino_feature_training.py"
    shutil.copyfile(__file__, script)
    snapshot = root / f"saved-step{state['step']}-v1.pt"
    os.link(checkpoint, snapshot)
    config["run"] = str(Path(original["work"]) / "artifacts/recovery-V128-v1")
    assert not Path(config["run"]).exists()
    config_path = root / "continuation-V128.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    arms = {name: dict(spec) for name, spec in original["arms"].items()}
    arms["V128"]["train"] = str(config_path)
    prefix_domains = dict(
        Counter(training_domain(s, 70, 0.25, 0.25) for s in range(1, state["step"] + 1))
    )
    adopted = dict(failed["completed"])
    assert set(adopted) == {"CPU-V128", "CUDA-V128"}
    for binding in adopted.values():
        assert ref(binding["path"]) == binding and not live(read(binding["path"])["owner"])
    plan = {
        **original,
        "root": str(root),
        "arms": arms,
        "controller_source": ref(script),
        "original_plan": ref(original_root / "plan.json"),
        "original_failure": ref(failure_path),
        "original_status": ref(original_root / "status.json"),
        "resume_checkpoint": ref(snapshot),
        "resume_step": state["step"],
        "remaining_updates": remaining,
        "absolute_worker_deadline_unix": deadline,
        "headroom_deadline_unix": headroom_deadline,
        "prefix_counts": failure["counts"],
        "prefix_domain_counts": prefix_domains,
        "adopted_phase_results": adopted,
        "source_sha256": state["config"]["source_sha256"],
        "scope": "One explicit continuation of saved V128 memory-guard state. Preserve all399 original updates,601 remaining to1000, original8h absolute worker deadline and conservative original-controller+2h admission deadline. Same source/EMA/Adam/RNG/data/noise/LR horizon/feature objective. Adopt completed CPU/CUDA16+2 checks; no prefix or control or old inference repetition. Original52GiB launch/16GiB CUDAcap/32GB runtime floor. Failure terminates without automatic retry or reset; quality pending.",
    }
    extra = [
        plan[k]
        for k in ("original_plan", "original_failure", "original_status", "resume_checkpoint")
    ]
    extra += [ref(config_path), ref(script), *adopted.values(), control_binding]
    plan["inputs"] = original["inputs"] + extra
    plan["frozen_files"] = {
        **original["frozen_files"],
        str(script): ref(script)["sha256"],
        str(config_path): ref(config_path)["sha256"],
    }
    save(root / "plan.json", plan)
    guard(plan)
    return root / "plan.json"


def worker(path):
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert ref(__file__) == plan["controller_source"]
    assert Path(training.__file__).resolve().is_relative_to(Path(plan["work"]) / "src")
    (root / "continuation-V128.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    torch.cuda.set_per_process_memory_fraction(
        plan["CUDA_allocator_cap_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    initial = torch.load(
        plan["resume_checkpoint"]["path"], map_location="cpu", weights_only=True, mmap=True
    )
    assert (
        remaining_budget(initial, read(plan["original_failure"]["path"]), plan["train_updates"])
        == plan["remaining_updates"]
    )
    config = yaml.safe_load(Path(plan["arms"]["V128"]["train"]).read_text())
    counts, domains, captured, initials, observed = Counter(), Counter(), {}, [], []
    constructor, factory, optimizer_factory = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )

    control = read(plan["matched_control_results"]["train"]["path"])
    control_inputs = {r["step"]: r for r in control["observed_inputs"]}
    prefix_inputs = read(plan["original_failure"]["path"])["observed_inputs"]
    gradients = {}

    def construct(options):
        model = constructor(options)
        captured["model"] = model

        def before(module, args):
            assert time.time() < plan["absolute_worker_deadline_unix"]
            counts["training_forwards" if module.training else "validation_forwards"] += 1

        def first(module, args):
            assert all(
                torch.equal(v.cpu(), initial["model"][k])
                for k, v in module.restoration_state_dict().items()
            )
            assert model_hash(module.context.backbone) == config["expected_dino_sha256"]
            restored = captured["optimizer"].state_dict()
            assert [
                {k: v for k, v in g.items() if k != "lr"} for g in restored["param_groups"]
            ] == [
                {k: v for k, v in g.items() if k != "lr"}
                for g in initial["optimizer"]["param_groups"]
            ]
            for key, values in restored["state"].items():
                assert all(
                    torch.equal(v.cpu(), initial["optimizer"]["state"][key][name])
                    if isinstance(v, torch.Tensor)
                    else v == initial["optimizer"]["state"][key][name]
                    for name, v in values.items()
                )
            initials.append(
                {
                    "official_encoder_exact": True,
                    "resumed91_model_tensors_exact": True,
                    "resumed89_AdamW_states_exact": True,
                    "first_step": plan["resume_step"] + 1,
                }
            )
            save(
                root / "first-resumed-state-verification-v1.json",
                {
                    **initials[-1],
                    "Python_Torch_CPU_CUDA_RNG_exact_before_preparation": True,
                    "resume_checkpoint": plan["resume_checkpoint"],
                    "source_sha256": plan["source_sha256"],
                    "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                    "new_optimizer_updates_at_check": counts["optimizer_steps"],
                },
            )
            hook.remove()

        model.register_forward_pre_hook(before)
        hook = model.register_forward_pre_hook(first)
        model.context.backbone.register_forward_hook(
            lambda *args: counts.update(encoder_forwards=1)
        )
        model.context.backbone.stages[0].register_forward_hook(
            lambda *args: counts.update(stage0_forwards=1)
        )
        return model

    def batch(step, domain, clean, **kwargs):
        assert step == plan["resume_step"] + counts["prepared_training_batches"] + 1
        assert domain == training.training_domain(step, 70, 0.25, 0.25)
        if not counts["prepared_training_batches"]:
            assert torch.equal(torch.get_rng_state(), initial["torch_rng"])
            assert random.getstate() == initial["python_rng"]
            assert all(
                torch.equal(a, b)
                for a, b in zip(torch.cuda.get_rng_state_all(), initial["cuda_rng"], strict=True)
            )
        clean_hash = training.batch_fingerprint(
            {k: v for k, v in clean.items() if isinstance(v, torch.Tensor)}
        )
        result = factory(step, domain, clean, **kwargs)
        expected = control_inputs[step]
        digest = training.batch_fingerprint(result)
        assert (
            clean_hash == expected["clean_sha256"]
            and digest == expected["batch_sha256"]
            and domain == expected["domain"]
        )
        counts.update(prepared_training_batches=1, target_contexts=len(result["packed"]))
        domains[domain] += 1
        observed.append(
            {
                "step": step,
                "domain": domain,
                "clean_sha256": clean_hash,
                "batch_sha256": digest,
                "selected_shadow_targets": 0,
            }
        )
        return result

    def optimizer(model, options):
        result = optimizer_factory(model, options)
        captured["optimizer"] = result

        def check_gradients(*args):
            if counts["optimizer_steps"] < 16:
                for name, parameter in model.named_parameters():
                    if parameter.requires_grad:
                        assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
                        gradients[name] = max(
                            gradients.get(name, 0), float(parameter.grad.abs().max())
                        )

        result.register_step_pre_hook(check_gradients)
        result.register_step_post_hook(lambda *args: counts.update(optimizer_steps=1))
        return result

    try:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            construct,
            batch,
            optimizer,
        )
        last = Path(
            training.train(
                plan["arms"]["V128"]["train"],
                resume=plan["resume_checkpoint"]["path"],
                stop_after=plan["remaining_updates"],
            )
        )
        final = torch.load(last, map_location="cpu", weights_only=True, mmap=True)
        assert final["step"] == plan["train_updates"] == 1000
        finite_state(final)
        assert all(float(s["step"]) == 1000 for s in final["optimizer"]["state"].values())
        assert all(
            counts[k] == plan["remaining_updates"]
            for k in ("training_forwards", "optimizer_steps", "prepared_training_batches")
        )
        aggregate = Counter(plan["prefix_counts"]) + counts
        assert aggregate["validation_forwards"] == 64 and aggregate["encoder_forwards"] == 1064
        domain_counts = Counter(plan["prefix_domain_counts"]) + domains
        assert dict(domain_counts) == plan["prospective_domain_batches"]
        assert aggregate["target_contexts"] == 16000 and aggregate["stage0_forwards"] == 2542
        assert len(gradients) == 89 and any(v > 0 for v in gradients.values())
        combined_inputs = prefix_inputs + observed
        assert len(combined_inputs) == 1000 and [r["step"] for r in combined_inputs] == list(
            range(1, 1001)
        )

        assert final["config"]["source_sha256"] == plan["source_sha256"]
        assert model_hash(captured["model"].context.backbone) == config["expected_dino_sha256"]
        assert all(
            not p.requires_grad and p.grad is None
            for p in captured["model"].context.backbone.parameters()
        )
        guard(plan)
        save(
            root / "train-V128-result.json",
            {
                "status": "completed-dino-feature-training-phase",
                "phase": "train",
                "arm": "V128",
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                "updates": 1000,
                "checkpoint": ref(last),
                "counts": dict(aggregate),
                "domain_counts": dict(domain_counts),
                "continuation_counts": dict(counts),
                "continuation_domain_counts": dict(domains),
                "original_failure": plan["original_failure"],
                "resume_checkpoint": plan["resume_checkpoint"],
                "original_checkpoint_step": plan["resume_step"],
                "initial_checks": initials,
                "observed_inputs": combined_inputs,
                "continuation_inputs": observed,
                "gradient_maxima": gradients,
                "all_AdamW_steps": 1000,
                "optimizer_state_count": 89,
                "all_observed_inputs_match_saved_control": True,
                "dino_feature_weight": 0.1,
                "dino_feature_policy": config["dino_feature_policy"],
                "continued_from_exact_saved_model_EMA_Adam_RNG": True,
                "model_EMA_Adam_finite": True,
                "source_sha256": final["config"]["source_sha256"],
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "CUDA_peak_reserved_bytes": torch.cuda.max_memory_reserved(),
                "scope": "Combined original prefix and exact saved-state continuation; no repeated optimizer updates. Image quality pending.",
            },
        )
    except BaseException as error:
        save(
            root / "continuation-failure.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "counts": dict(counts),
                "domain_counts": dict(domains),
                "observed_inputs": observed,
                "initial_checks": initials,
            },
        )
        raise
    finally:
        training.JointDemosaic, training.prepare_training_batch, training.make_optimizer = (
            constructor,
            factory,
            optimizer_factory,
        )
        captured.clear()
        gc.collect()


def controller(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert ref(__file__) == plan["controller_source"]
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": dict(plan["adopted_phase_results"]),
        "child": None,
    }
    child = owner = None

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        save(root / "status.json", state)

    try:
        record("waiting-for-original-feature-pilot-headroom")
        stable = None
        while True:
            assert time.time() < min(
                plan["headroom_deadline_unix"], plan["absolute_worker_deadline_unix"]
            )
            enough = (
                psutil.virtual_memory().available >= plan["launch_available_RAM_GiB"] * 2**30
                and shutil.disk_usage(root).free >= plan["phase_start_internal_free_GiB"] * 2**30
                and shutil.disk_usage("/mnt/external").free
                >= plan["phase_start_external_free_GiB"] * 2**30
            )
            stable = (time.monotonic() if stable is None else stable) if enough else None
            if stable is not None and time.monotonic() - stable >= 15:
                break
            time.sleep(2)
        guard(plan)
        env = dict(
            os.environ,
            PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
            CUDA_VISIBLE_DEVICES="0",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            OMP_NUM_THREADS="2",
            OPENBLAS_NUM_THREADS="1",
            CUBLAS_WORKSPACE_CONFIG=":4096:8",
        )
        with (root / "continuation-V128.log").open("x") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", plan["controller_source"]["path"], "worker", str(path)],
                cwd=plan["work"],
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-feature-training-continuation", child=owner)
            while child.poll() is None:
                assert time.time() < plan["absolute_worker_deadline_unix"]
                assert shutil.disk_usage(root).free >= plan["runtime_internal_reserve_GiB"] * 2**30
                assert (
                    shutil.disk_usage("/mnt/external").free
                    >= plan["runtime_external_reserve_GiB"] * 2**30
                )
                time.sleep(2)
            assert child.wait() == 0, child.returncode
        result = ref(root / "train-V128-result.json")
        assert read(result["path"])["owner"] == owner and not live(owner)
        state["completed"]["train-V128"] = result
        record("completed-training-awaiting-model-comparisons", child=None)
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-feature-continuation-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--original-root", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.original_root))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve())
