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
    if counts["encoder_forwards"] != first + counts["validation_forwards"]:
        raise ValueError("Original encoder budget differs")
    states = snapshot["optimizer"]["state"]
    if len(states) != 94 or any(float(s["step"]) != first for s in states.values()):
        raise ValueError("Emergency AdamW state is incomplete")
    return total - first


def finite_state(state):
    import torch

    assert len(state["model"]) == len(state["ema"]) == 96
    assert all(torch.isfinite(v).all() for key in ("model", "ema") for v in state[key].values())
    assert all(
        torch.isfinite(v).all()
        for s in state["optimizer"]["state"].values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    )


def prepare(root, original_root, dependency_path):
    import torch
    import yaml

    from demosaic.train import training_domain

    root, original_root = root.resolve(), original_root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    original = read(original_root / "plan.json")
    guard(original)
    failed = read(original_root / "status.json")
    assert failed["status"] == "failed-frequency-training-preserved-no-automatic-retry"
    assert failed["arm"] == "V123" and failed["phase"] == "train"
    assert not live(failed["controller"]) and not live(failed["child"])
    failure_path = original_root / "train-V123-failure.json"
    failure = read(failure_path)
    assert failure["error"].startswith("RuntimeError('Stopping safely: only ")
    assert failure["current"] == "fresh"
    checkpoint = Path(original["artifact_root"]) / "train/V123/last.pt"
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    total = original["train_updates"]
    remaining = remaining_budget(state, failure, total)
    finite_state(state)
    assert state["torch_rng"].dtype == torch.uint8 and state["cuda_rng"]
    config = yaml.safe_load(Path(original["arms"]["V123"]["train"]).read_text())
    assert config["steps"] == total and config["data_seed_per_step"] is True
    assert all(config[k] == 0 for k in ("workers", "paired_workers", "raw_clean_workers"))
    dependency_plan = read(dependency_path)
    guard(dependency_plan)
    dependency_root = Path(dependency_plan["root"])
    dependency_status = read(dependency_root / "status.json")
    assert dependency_status["plan"] == ref(dependency_path)
    assert live(dependency_status["owner"]) and not dependency_status["status"].startswith("failed")
    deadline = failed["child"]["created"] + 86400
    assert time.time() < deadline
    root.mkdir(parents=True, exist_ok=False)
    script = root / "resume_frequency_training.py"
    shutil.copyfile(__file__, script)
    # Keep the entire failed run immutable; frozen train.py permits this sibling output.
    config["run"] = str(Path(original["work"]) / "artifacts/recovery-V123-v1")
    assert not Path(config["run"]).exists()
    config_path = root / "continuation-V123.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False))
    arms = {name: dict(spec) for name, spec in original["arms"].items()}
    arms["V123"]["train"] = str(config_path)
    dependency = {
        "status": str(dependency_root / "status.json"),
        "plan": ref(dependency_path),
        "owner": dependency_status["owner"],
        "terminal": "completed-pilot-predictions-awaiting-independent-and-native-review",
    }
    prefix_domains = dict(
        Counter(training_domain(s, 66, 0.25, 0.25) for s in range(1, state["step"] + 1))
    )
    adopted = dict(failed["completed"])
    assert set(adopted) == {"CPU-V122", "CPU-V123", "CUDA-V122", "CUDA-V123", "train-V122"}
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
        "resume_checkpoint": ref(checkpoint),
        "resume_step": state["step"],
        "remaining_updates": remaining,
        "absolute_worker_deadline_unix": deadline,
        "headroom_deadline_unix": min(time.time() + 7200, deadline),
        "dependency": dependency,
        "prefix_counts": failure["counts"],
        "prefix_domain_counts": prefix_domains,
        "adopted_phase_results": adopted,
        "source_sha256": state["config"]["source_sha256"],
        "scope": "One explicit continuation of the safely saved V123 memory-guard state. No prefix, smoke, V122 or old inference repetition; original 20000-update horizon and original worker start+24h deadline retained. Wait for the new shadow pilot to release memory, then require original56GiB launch headroom. Failure ends this attempt without automatic retry.",
    }
    extra = [
        plan[k]
        for k in ("original_plan", "original_failure", "original_status", "resume_checkpoint")
    ]
    extra += [ref(config_path), ref(script), ref(dependency_path), *adopted.values()]
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
    (root / "continuation-V123.claim").open("x").close()
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
    config = yaml.safe_load(Path(plan["arms"]["V123"]["train"]).read_text())
    counts, domains, captured, initials, observed = Counter(), Counter(), {}, [], []
    constructor, factory, optimizer_factory = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )

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
                    "resumed96_model_tensors_exact": True,
                    "resumed94_AdamW_states_exact": True,
                    "first_step": plan["resume_step"] + 1,
                }
            )
            hook.remove()

        model.register_forward_pre_hook(before)
        hook = model.register_forward_pre_hook(first)
        model.context.backbone.register_forward_hook(
            lambda *args: counts.update(encoder_forwards=1)
        )
        return model

    def batch(step, domain, clean, **kwargs):
        assert step == plan["resume_step"] + counts["prepared_training_batches"] + 1
        assert domain == training.training_domain(step, 66, 0.25, 0.25)
        if not counts["prepared_training_batches"]:
            assert torch.equal(torch.get_rng_state(), initial["torch_rng"])
            assert random.getstate() == initial["python_rng"]
            assert all(
                torch.equal(a, b)
                for a, b in zip(torch.cuda.get_rng_state_all(), initial["cuda_rng"], strict=True)
            )
        result = factory(step, domain, clean, **kwargs)
        counts["prepared_training_batches"] += 1
        domains[domain] += 1
        if len(observed) < 2:
            observed.append(
                {"step": step, "domain": domain, "batch_sha256": training.batch_fingerprint(result)}
            )
        return result

    def optimizer(model, options):
        result = optimizer_factory(model, options)
        captured["optimizer"] = result
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
                plan["arms"]["V123"]["train"],
                resume=plan["resume_checkpoint"]["path"],
                stop_after=plan["remaining_updates"],
            )
        )
        final = torch.load(last, map_location="cpu", weights_only=True, mmap=True)
        assert final["step"] == plan["train_updates"] == 20000
        finite_state(final)
        assert all(float(s["step"]) == 20000 for s in final["optimizer"]["state"].values())
        assert all(
            counts[k] == plan["remaining_updates"]
            for k in ("training_forwards", "optimizer_steps", "prepared_training_batches")
        )
        aggregate = Counter(plan["prefix_counts"]) + counts
        assert aggregate["validation_forwards"] == 640 and aggregate["encoder_forwards"] == 20640
        domain_counts = Counter(plan["prefix_domain_counts"]) + domains
        assert dict(domain_counts) == plan["prospective_domain_batches"]
        assert final["config"]["source_sha256"] == plan["source_sha256"]
        assert model_hash(captured["model"].context.backbone) == config["expected_dino_sha256"]
        assert all(
            not p.requires_grad and p.grad is None
            for p in captured["model"].context.backbone.parameters()
        )
        guard(plan)
        save(
            root / "train-V123-result.json",
            {
                "status": "completed-frequency-training-phase",
                "phase": "train",
                "arm": "V123",
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                "updates": 20000,
                "checkpoint": ref(last),
                "counts": dict(aggregate),
                "domain_counts": dict(domain_counts),
                "continuation_counts": dict(counts),
                "continuation_domain_counts": dict(domains),
                "original_failure": plan["original_failure"],
                "resume_checkpoint": plan["resume_checkpoint"],
                "original_checkpoint_step": plan["resume_step"],
                "initial_checks": initials,
                "observed_inputs": observed,
                "common91_model_and_EMA_exact_to_parent": False,
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
        dep = plan["dependency"]
        record("waiting-for-shadow-pilot-memory-release", dependency=dep)
        while True:
            assert time.time() < plan["absolute_worker_deadline_unix"]
            observed = read(dep["status"])
            assert observed["owner"] == dep["owner"] and observed["plan"] == dep["plan"]
            if not live(dep["owner"]):
                assert observed["status"] == dep["terminal"]
                assert observed.get("child") is None or not live(observed["child"])
                break
            assert not observed["status"].startswith("failed")
            time.sleep(5)
        record("waiting-for-original-frequency-headroom")
        stable = None
        while True:
            assert time.time() < plan["headroom_deadline_unix"]
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
        with (root / "continuation-V123.log").open("x") as log:
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
            record("running-frequency-training-continuation", child=owner)
            while child.poll() is None:
                assert time.time() < plan["absolute_worker_deadline_unix"]
                assert shutil.disk_usage(root).free >= plan["runtime_internal_reserve_GiB"] * 2**30
                assert (
                    shutil.disk_usage("/mnt/external").free
                    >= plan["runtime_external_reserve_GiB"] * 2**30
                )
                time.sleep(2)
            assert child.wait() == 0, child.returncode
        result = ref(root / "train-V123-result.json")
        assert read(result["path"])["owner"] == owner and not live(owner)
        state["completed"]["train-V123"] = result
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
        record("failed-frequency-continuation-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--original-root", type=Path)
    parser.add_argument("--dependency", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.original_root, args.dependency))
    elif args.mode == "controller":
        controller(args.path.resolve())
    else:
        worker(args.path.resolve())
