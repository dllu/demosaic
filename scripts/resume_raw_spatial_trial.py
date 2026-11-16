"""Explicit new execution of the preserved V131/V132 comparison, without replay."""

import argparse
import copy
import json
import math
import os
import shutil
import signal
import subprocess
import time
from collections import Counter
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").is_file())
PREFIX = 14549
HORIZON = 20000


def validate_prefix(state, failure):
    """Reject partial clocks or input traces before admitting the saved state."""
    import torch

    assert state["step"] == PREFIX and state["config"]["steps"] == HORIZON
    assert state["config"]["seed"] == 70 and state["config"]["data_seed_per_step"]
    assert len(state["model"]) == len(state["ema"]) == 91
    adam = state["optimizer"]["state"]
    assert len(adam) == 89 and all(float(s["step"]) == PREFIX for s in adam.values())
    assert all(key in state for key in ("torch_rng", "python_rng", "cuda_rng"))
    assert len(state["cuda_rng"]) == 1
    assert all(torch.isfinite(v).all() for field in ("model", "ema") for v in state[field].values())
    assert all(
        torch.isfinite(v).all()
        for s in adam.values()
        for v in s.values()
        if isinstance(v, torch.Tensor)
    )
    assert "31.6 GB system memory available" in failure["error"]
    counts = failure["counts"]
    assert all(
        counts[k] == PREFIX
        for k in ("prepared_training_batches", "training_forwards", "optimizer_steps")
    )
    assert counts["validation_forwards"] == 448
    assert counts["encoder_forwards"] == PREFIX + 448
    assert counts["target_contexts"] == 16 * PREFIX
    assert [r["step"] for r in failure["observed_inputs"]] == list(range(1, PREFIX + 1))


def relocated_config(config, run):
    value = copy.deepcopy(config)
    assert value["steps"] == HORIZON and value["seed"] == 70
    assert value["data_seed_per_step"] and value["min_available_gb"] == 32
    value["run"] = str(run)
    return value


def equal_state(a, b):
    import torch

    if isinstance(a, torch.Tensor):
        return isinstance(b, torch.Tensor) and a.dtype == b.dtype and torch.equal(a.cpu(), b.cpu())
    if isinstance(a, dict):
        return (
            isinstance(b, dict)
            and a.keys() == b.keys()
            and all(equal_state(v, b[k]) for k, v in a.items())
        )
    if isinstance(a, (list, tuple)):
        return (
            type(a) is type(b)
            and len(a) == len(b)
            and all(equal_state(x, y) for x, y in zip(a, b, strict=True))
        )
    return a == b


def prepare(root, original, preserved_attempt=None):
    import torch
    import yaml

    original = original.resolve()
    old = read(original)
    guard(old)
    previous = Path(old["root"])
    status = read(previous / "status.json")
    assert status["status"] == "failed-training-preserved-no-automatic-retry"
    assert not live(status["child"])
    assert not (previous / "train-V132.claim").exists()
    failure_path = previous / "train-V131-failure.json"
    failure = read(failure_path)
    checkpoint = Path(old["arms"]["V131"]["train"]).parent.parent / "artifacts/train/V131/last.pt"
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    validate_prefix(state, failure)
    assert str(torch.__version__) == state["torch_version"]
    assert (
        ref(checkpoint)["sha256"]
        == "ddbb4d6fbec2f76c2b79abb60c9afcbb1cf7ca32380b9ee73e51e94ee8983716"
    )
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    root.mkdir(parents=True)
    work = root / "work"
    work.mkdir()
    previous_work = Path(old["work"])
    for directory in ("src", "scripts", "third_party"):
        shutil.copytree(previous_work / directory, work / directory)
    for filename in ("pyproject.toml", "uv.lock"):
        shutil.copyfile(previous_work / filename, work / filename)
    copied_sources = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    assert all(
        ref(previous_work / Path(p).relative_to(work))["sha256"] == digest
        for p, digest in copied_sources.items()
    )
    retained = root / "V131-step14549.pt"
    shutil.copyfile(checkpoint, retained)
    assert ref(retained)["sha256"] == ref(checkpoint)["sha256"]
    source = root / "continuation.py"
    shutil.copyfile(__file__, source)
    arms = copy.deepcopy(old["arms"])
    for arm in ("V131", "V132"):
        config = yaml.safe_load(Path(arms[arm]["train"]).read_text())
        target = root / f"train-{arm}.yaml"
        target.write_text(
            yaml.safe_dump(
                relocated_config(config, work / "artifacts/train" / arm), sort_keys=False
            )
        )
        arms[arm]["train"] = str(target)
    completed = []
    for phase in ("CPU", "CUDA"):
        for arm in ("V131", "V132"):
            p = previous / f"{phase}-{arm}-result.json"
            s = read(p)
            assert s["updates"] == s["all_AdamW_steps"] == 18 and s["model_EMA_Adam_finite"]
            assert s["source_sha256"] == state["config"]["source_sha256"]
            assert not live(s["owner"]) and ref(s["checkpoint"]["path"]) == s["checkpoint"]
            if arm == "V132":
                assert s["all_observed_inputs_match_saved_control"]
            shutil.copyfile(p, root / p.name)
            completed.append(ref(p))
    first = previous / "retained/train/V131/first-outputs.npz"
    assert first.exists()
    plan = {
        **old,
        "root": str(root),
        "work": str(work),
        "arms": arms,
        "after_run": None,
        "artifact_root": str(work / "artifacts"),
        "worker_script": ref(source),
        "core_worker_script": ref(work / "scripts/train_reviewed_shadow_trial.py"),
        "original_plan": ref(original),
        "prefix_failure": ref(failure_path),
        "prefix_checkpoint": ref(retained),
        "prefix_first_outputs": ref(first),
        "prefix_source_sha256": state["config"]["source_sha256"],
        "adopted_checks": completed,
        "old_controller_and_child": {k: status.get(k) for k in ("controller", "child")},
        "phase_start_external_free_GiB": 96,
        "runtime_external_reserve_GiB": 64,
        "phase_start_internal_free_GiB": 128,
        "runtime_internal_reserve_GiB": 96,
        "inputs": [
            *old["inputs"],
            ref(original),
            ref(previous / "status.json"),
            ref(failure_path),
            ref(retained),
            ref(first),
            *completed,
        ],
        "frozen_files": {
            **old["frozen_files"],
            **copied_sources,
            str(source): ref(source)["sha256"],
            **{
                str(root / f"train-{a}.yaml"): ref(root / f"train-{a}.yaml")["sha256"]
                for a in ("V131", "V132")
            },
        },
        "new_updates": {"V131": HORIZON - PREFIX, "V132": HORIZON},
        "scope": "Explicit November16 execution after audited RAM-stop. Original failed execution and sources remain immutable. Adopt all four original16+2 checks, resume V131 at14549 with model/EMA/Adam/RNG and original20k LR horizon, then fresh V132 from V120EMA for20k. Only output run paths differ from original recipes. All20k clean/noisy inputs and first initial outputs must match. All writes internal; external media/manifests read only, so new external96GiB admission/64GiB runtime reserve replaces historical208GiB write reserve.52GiB RAM admission,16GiB allocator cap,32GB training floor,48h per newly launched worker. No automatic retry or reset. Quality remains unmeasured.",
    }
    if preserved_attempt is not None:
        attempt = preserved_attempt.resolve()
        prior = read(attempt / "train-V131-failure.json")
        assert prior["counts"] == failure["counts"] and prior["checks"] == {}
        assert "Output must be inside" in prior["error"]
        plan["preserved_zero_update_attempt"] = {
            "status": ref(attempt / "status.json"),
            "failure": ref(attempt / "train-V131-failure.json"),
            "log": ref(attempt / "train-V131.log"),
            "new_updates": 0,
        }
        plan["inputs"].extend(
            value
            for value in plan["preserved_zero_update_attempt"].values()
            if isinstance(value, dict)
        )
    save(root / "plan.json", plan)
    guard(plan)
    save(
        root / "adoption.json",
        {
            "status": "prefix-and-original-checks-validated-no-new-updates",
            "plan": ref(root / "plan.json"),
            "checkpoint": ref(retained),
            "step": PREFIX,
            "remaining_control_updates": HORIZON - PREFIX,
            "spatial_updates": HORIZON,
            "all_AdamW_steps": PREFIX,
            "source_sha256": state["config"]["source_sha256"],
            "torch_version": str(torch.__version__),
            "runtime": state["config"]["training_execution_runtime"],
            "old_owners_dead": True,
            "old_prefix_not_modified": ref(checkpoint)["sha256"] == ref(retained)["sha256"],
            "adopted_checks": completed,
        },
    )
    return root / "plan.json"


def resume_control(path):
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert Path(training.__file__).resolve().is_relative_to(Path(plan["work"]) / "src")
    (root / "train-V131.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.cuda.set_per_process_memory_fraction(
        16 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    config = yaml.safe_load(Path(plan["arms"]["V131"]["train"]).read_text())
    prefix = torch.load(
        plan["prefix_checkpoint"]["path"], map_location="cpu", weights_only=True, mmap=True
    )
    failure = read(plan["prefix_failure"]["path"])
    validate_prefix(prefix, failure)
    counts = Counter(failure["counts"])
    inputs = list(failure["observed_inputs"])
    domains = Counter(r["domain"] for r in inputs)
    checks, captured, gradients = {}, {}, {}
    constructor, batch_factory, optimizer_factory = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.make_optimizer,
    )

    def construct(options):
        model = constructor(options)
        captured["model"] = model

        def initial(module, args):
            assert equal_state(module.restoration_state_dict(), prefix["model"])
            assert model_hash(module.context.backbone) == config["expected_dino_sha256"]
            checks["all91_resumed_model_tensors_exact_before_forward"] = True
            first.remove()

        def count(module, args):
            counts["training_forwards" if module.training else "validation_forwards"] += 1

        first = model.register_forward_pre_hook(initial)
        model.register_forward_pre_hook(count)
        model.context.backbone.register_forward_hook(
            lambda *args: counts.update(encoder_forwards=1)
        )
        return model

    def optimizer(model, options):
        result = optimizer_factory(model, options)
        original_load = result.load_state_dict

        def load(value):
            assert equal_state(value, prefix["optimizer"])
            original_load(value)
            assert equal_state(result.state_dict(), prefix["optimizer"])
            checks["all89_Adam_states_and_parameter_groups_exact_on_load"] = True

        result.load_state_dict = load

        def before(*args):
            if counts["optimizer_steps"] == PREFIX:
                progress = (PREFIX + 1 - 100) / (HORIZON - 100)
                expected_lr = 1e-5 * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
                assert all(g["lr"] == expected_lr for g in result.param_groups)
                checks["first_new_LR_on_original20000_horizon"] = expected_lr
            if counts["optimizer_steps"] < PREFIX + 16:
                for name, parameter in model.named_parameters():
                    if parameter.requires_grad:
                        assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
                        gradients[name] = max(
                            gradients.get(name, 0), float(parameter.grad.abs().max())
                        )

        result.register_step_pre_hook(before)
        result.register_step_post_hook(lambda *args: counts.update(optimizer_steps=1))
        return result

    def batch(step, domain, clean, **kwargs):
        assert step == len(inputs) + 1
        assert domain == training.training_domain(step, 70, 0.25, 0.25)
        if step == PREFIX + 1:
            assert equal_state(torch.get_rng_state(), prefix["torch_rng"])
            assert training.random.getstate() == prefix["python_rng"]
            assert equal_state(torch.cuda.get_rng_state_all(), prefix["cuda_rng"])
            checks["Torch_Python_CUDA_RNG_exact_before_first_new_noise_draw"] = True
            checks["first_new_step"] = step
        clean_hash = training.batch_fingerprint(
            {k: v for k, v in clean.items() if isinstance(v, torch.Tensor)}
        )
        value = batch_factory(step, domain, clean, **kwargs)
        assert len(value["packed"]) == 16
        row = {
            "step": step,
            "domain": domain,
            "clean_sha256": clean_hash,
            "batch_sha256": training.batch_fingerprint(value),
            "selected_shadow_targets": 0,
        }
        inputs.append(row)
        domains[domain] += 1
        counts.update(prepared_training_batches=1, target_contexts=16)
        with (root / "V131-new-inputs.jsonl").open("a") as stream:
            stream.write(json.dumps(row) + "\n")
        if step == PREFIX + 1 or step % 25 == 0:
            save(
                root / "progress-V131.json",
                {
                    "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                    "step_prepared": step,
                    "counts": dict(counts),
                    "checks": checks,
                },
            )
        return value

    training.JointDemosaic, training.make_optimizer, training.prepare_training_batch = (
        construct,
        optimizer,
        batch,
    )
    try:
        last = Path(
            training.train(plan["arms"]["V131"]["train"], resume=plan["prefix_checkpoint"]["path"])
        )
        state = torch.load(last, map_location="cpu", weights_only=True, mmap=True)
        assert (
            state["step"] == HORIZON
            and state["config"]["source_sha256"] == plan["prefix_source_sha256"]
        )
        assert (
            len(state["model"]) == len(state["ema"]) == 91
            and len(state["optimizer"]["state"]) == 89
        )
        assert all(float(s["step"]) == HORIZON for s in state["optimizer"]["state"].values())
        assert (
            counts["optimizer_steps"]
            == counts["prepared_training_batches"]
            == counts["training_forwards"]
            == HORIZON
        )
        assert counts["validation_forwards"] == 640 and counts["encoder_forwards"] == HORIZON + 640
        assert (
            counts["target_contexts"] == HORIZON * 16
            and dict(domains) == plan["prospective_domain_batches"]
        )
        assert len(gradients) == 89 and any(v > 0 for v in gradients.values())
        assert all(
            torch.isfinite(v).all() for field in ("model", "ema") for v in state[field].values()
        )
        assert all(
            torch.isfinite(v).all()
            for s in state["optimizer"]["state"].values()
            for v in s.values()
            if isinstance(v, torch.Tensor)
        )
        assert model_hash(captured["model"].context.backbone) == config["expected_dino_sha256"]
        assert all(
            not p.requires_grad and p.grad is None
            for p in captured["model"].context.backbone.parameters()
        )
        guard(plan)
        save(
            root / "train-V131-result.json",
            {
                "status": "completed-raw-spatial-training-phase",
                "phase": "train",
                "arm": "V131",
                "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                "checkpoint": ref(last),
                "updates": HORIZON,
                "new_updates": HORIZON - PREFIX,
                "counts": dict(counts),
                "domain_counts": dict(domains),
                "observed_inputs": inputs,
                "first_outputs": plan["prefix_first_outputs"],
                "checks": checks,
                "gradient_maxima_first16_new_updates": gradients,
                "source_sha256": state["config"]["source_sha256"],
                "model_EMA_Adam_finite": True,
                "all_AdamW_steps": HORIZON,
                "optimizer_state_count": 89,
                "model_EMA_tensor_count": 91,
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "scope": "Original14549 prefix plus5451 updates, no replay. Original source/horizon/model/EMA/Adam/RNG retained. Quality review pending.",
            },
        )
    except BaseException as error:
        save(
            root / "train-V131-failure.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "counts": dict(counts),
                "checks": checks,
                "observed_inputs": inputs,
            },
        )
        raise


def controller(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    child = None
    child_owner = None
    try:
        for arm in ("V131", "V132"):
            deadline = time.time() + 48 * 3600
            while True:
                assert time.time() < deadline, "Admission deadline expired; no retry"
                blocked = plan.get("wait_for_owner")
                if (
                    (not blocked or not live(blocked))
                    and psutil.virtual_memory().available >= 52 * 2**30
                    and shutil.disk_usage(root).free >= 128 * 2**30
                    and shutil.disk_usage("/mnt/external").free >= 96 * 2**30
                ):
                    break
                save(
                    root / "status.json",
                    {
                        "status": "waiting-for-admission",
                        "arm": arm,
                        "owner": owner,
                        "deadline": deadline,
                        "plan": ref(path),
                    },
                )
                time.sleep(10)
            guard(plan)
            env = dict(
                os.environ,
                CUDA_VISIBLE_DEVICES="0",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
                PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
                PYTHONDONTWRITEBYTECODE="1",
            )
            with (root / f"train-{arm}.log").open("x") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        plan["worker_script"]["path"],
                        "worker",
                        str(path),
                        "--arm",
                        arm,
                    ],
                    env=env,
                    cwd=REPO,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                worker_deadline = child_owner["created"] + 48 * 3600
                save(
                    root / "status.json",
                    {
                        "status": "running-explicit-raw-spatial-continuation",
                        "arm": arm,
                        "owner": owner,
                        "child": child_owner,
                        "worker_deadline": worker_deadline,
                        "plan": ref(path),
                    },
                )
                while child.poll() is None:
                    assert time.time() < worker_deadline, "Worker deadline exceeded"
                    assert shutil.disk_usage(root).free >= 96 * 2**30, "Internal reserve crossed"
                    assert shutil.disk_usage("/mnt/external").free >= 64 * 2**30, (
                        "External reserve crossed"
                    )
                    time.sleep(10)
                assert child.returncode == 0, f"{arm} failed; prefix preserved, no retry"
                result = read(root / f"train-{arm}-result.json")
                assert result["updates"] == HORIZON and result["owner"] == child_owner
                assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
        save(
            root / "status.json",
            {
                "status": "completed-both-arms-quality-review-pending",
                "owner": owner,
                "plan": ref(path),
                "results": [ref(root / f"train-{a}-result.json") for a in ("V131", "V132")],
            },
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(child_owner):
                    os.killpg(child.pid, signal.SIGTERM)
        save(
            root / "status.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "owner": owner,
                "child": child_owner,
                "plan": ref(path),
            },
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--original-plan", type=Path)
    parser.add_argument("--preserved-attempt", type=Path)
    parser.add_argument("--arm", choices=("V131", "V132"))
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve(), args.original_plan, args.preserved_attempt))
    elif args.mode == "controller":
        controller(args.path.resolve())
    elif args.arm == "V131":
        resume_control(args.path.resolve())
    else:
        from train_reviewed_shadow_trial import worker

        worker(args.path.resolve(), "train", "V132")
