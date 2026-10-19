"""Resume a diagnosed memory stop at the original horizon using the frozen trainer.

The adapter reuses the frozen worker's recorders and full completion checks.
Its lexical recorder access is bound to the exact archived worker SHA; neural,
optimizer, sampler and checkpoint code are unchanged.
"""

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil


class ReplayComplete(Exception):
    pass


def read(path):
    return json.loads(Path(path).read_text())


def lexical(function, name):
    cells = dict(zip(function.__code__.co_freevars, function.__closure__ or (), strict=True))
    assert name in cells, (function.__qualname__, name)
    return cells[name].cell_contents


def run_worker(recovery_path, mode):
    import torch
    from audit_flat_palette import identical
    from profile_raw_kernel_inference import model_hash
    from train_directional_bank_detachment import guard, ref, save, worker

    import demosaic.train as training

    recovery = read(recovery_path)
    assert ref(__file__) == recovery["adapter"]
    plan_path = recovery["replay_plan"] if mode == "replay" else recovery["training_plan"]
    plan = read(plan_path)
    guard(plan)
    real_train = training.train
    reference_case = read(recovery["connected_result"]["path"])
    reference_samples = {
        row["step"]: row for row in read(reference_case["sampled_observations"]["path"])
    }

    def replay_train(config, **kwargs):
        recorder = lexical(training.JointDemosaic, "capture")
        kwargs["stop_after"] = recovery["probe_updates"]
        checkpoint = real_train(config, **kwargs)
        capture = {k: v for k, v in recorder.items() if k != "model"}
        for key in [
            "initial_EMA_exact",
            "initial_local_sha256",
            "initial_bank_sha256",
            "initial_model_sha256",
            "first_raw_gradient_sha256",
            "first_output_sha256",
            "DINO_sha256",
        ]:
            assert capture[key] == reference_case["capture"][key], key
        state = torch.load(checkpoint, weights_only=True, map_location="cpu", mmap=True)
        assert state["step"] == recovery["probe_updates"] and state["config"]["steps"] == 4000
        save(
            Path(recovery["root"]) / "initial-replay.json",
            {
                "status": "completed-discarded-genuine-parent-initialization-replay",
                "capture": capture,
                "checkpoint": ref(checkpoint),
                "actual_updates": recovery["probe_updates"],
                "planned_horizon": 4000,
                "samples": ref(Path(plan["root"]) / "detached-sampled-observations.json"),
                "source_sha256": state["config"]["source_sha256"],
                "scope": "Discarded initialization/gradient replay only; never resumed for production quality.",
            },
        )
        raise ReplayComplete

    def resume_train(config, **kwargs):
        checkpoint_ref = read(Path(recovery["root"]) / "resume-input.json")
        assert ref(checkpoint_ref["path"]) == checkpoint_ref
        initial = read(Path(recovery["root"]) / "initial-replay.json")
        emergency = torch.load(
            checkpoint_ref["path"], map_location="cpu", weights_only=True, mmap=True
        )
        instrument, observer = training.JointDemosaic, training.prepare_training_batch
        capture, sampled = lexical(instrument, "capture"), lexical(observer, "sampled")
        assert not capture and not sampled
        capture.update(initial["capture"])
        prefix = read(recovery["prefix_samples"]["path"])
        sampled.extend(row for row in prefix if row["step"] <= emergency["step"])

        def resumed_constructor(options):
            model = instrument(options)
            # Remove exactly the frozen worker's fresh-initialization hooks.
            # Replace them with a checkpoint-equality hook for this continuation.
            before, after = (
                list(model._forward_pre_hooks.values()),
                list(model._forward_hooks.values()),
            )
            assert len(before) == len(after) == 1
            assert before[0].__name__ == "first_forward" and after[0].__name__ == "first_output"
            lexical(before[0], "hook").remove()
            lexical(after[0], "output_hook").remove()

            def loaded_exact(module, args):
                actual = module.restoration_state_dict()
                assert actual.keys() == emergency["model"].keys()
                assert all(
                    torch.equal(value.cpu(), emergency["model"][name])
                    for name, value in actual.items()
                )
                assert model_hash(module.context.backbone) == capture["DINO_sha256"]
                capture["resume_first_forward_model_exact"] = True
                capture["resumed_from"] = checkpoint_ref
                handle.remove()

            handle = model.register_forward_pre_hook(loaded_exact)
            return model

        def checked_observer(*args, **kwargs):
            batch = observer(*args, **kwargs)
            step = args[0]
            if step in reference_samples:
                observed = sampled[-1]
                expected = reference_samples[step]
                assert observed["step"] == step
                assert all(
                    observed[key] == expected[key]
                    for key in [
                        "domain",
                        "legacy_batch_sha256",
                        "input_sha256",
                        "full_batch_sha256",
                    ]
                )
            return batch

        training.JointDemosaic, training.prepare_training_batch = (
            resumed_constructor,
            checked_observer,
        )
        kwargs.pop("initialize", None)
        kwargs.update(
            resume=checkpoint_ref["path"], stop_after=plan["boundary_updates"] - emergency["step"]
        )
        assert kwargs["stop_after"] > 0
        try:
            checkpoint = real_train(config, **kwargs)
        finally:
            training.JointDemosaic, training.prepare_training_batch = instrument, observer
        run = Path(checkpoint).parent
        grid = {1, *range(25, plan["boundary_updates"] + 1, 25)}
        metrics = run / "metrics.jsonl"
        rows = [json.loads(line) for line in metrics.read_text().splitlines()]
        extras = [row for row in rows if row.get("event") == "train" and row["step"] not in grid]
        if extras:
            # A short CPU 3+3 preflight logs its resumed first step4 as well.
            # Archive it, then expose the original fixed logging grid to the
            # unchanged worker's boundary checks. Production2999→4000 has none.
            assert recovery["engineering_only"]
            shutil.copyfile(metrics, run / "metrics-with-resume-start-row.jsonl")
            metrics.write_text("".join(json.dumps(row) + "\n" for row in rows if row not in extras))
        return checkpoint

    training.train = replay_train if mode == "replay" else resume_train
    try:
        try:
            worker(plan_path, "detached")
        except ReplayComplete:
            assert mode == "replay"
    finally:
        training.train = real_train
    if mode == "resume" and recovery["engineering_only"]:
        case = read(Path(plan["root"]) / "detached-result.json")
        resumed = torch.load(
            case["checkpoint"]["path"], map_location="cpu", weights_only=True, mmap=True
        )
        reference = torch.load(
            recovery["CPU_reference"]["path"], map_location="cpu", weights_only=True, mmap=True
        )
        for key in ["model", "ema", "optimizer", "python_rng", "torch_rng", "cuda_rng"]:
            identical(resumed[key], reference[key])
        save(
            Path(recovery["root"]) / "CPU-exact-resume.json",
            {
                "status": "passed-frozen-worker-CPU-emergency3-resume-to6-exact-state-and-RNG",
                "checkpoint": case["checkpoint"],
                "reference": recovery["CPU_reference"],
                "exact_fields": [
                    "model",
                    "ema",
                    "optimizer",
                    "python_rng",
                    "torch_rng",
                    "cuda_rng",
                ],
                "extra_step4_row_preserved": True,
                "quality_evidence": False,
            },
        )


def emergency_cpu_proof(recovery_path):
    import torch
    import yaml
    from audit_flat_palette import identical
    from train_directional_bank_detachment import ref, save

    import demosaic.train as training

    recovery = read(recovery_path)
    assert recovery["engineering_only"] and os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    probe = read(Path(recovery["root"]) / "initial-replay.json")
    checkpoint = probe["checkpoint"]
    cfg = yaml.safe_load(Path(read(recovery["training_plan"])["arms"][1]["config"]).read_text())
    cfg["run"] = str(Path(recovery["work"]) / "runs/CPU-emergency-guard")
    path = Path(recovery["root"]) / "CPU-emergency-config.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    original = training.psutil.virtual_memory
    try:
        from types import SimpleNamespace

        training.psutil.virtual_memory = lambda: SimpleNamespace(available=6_700_000_000)
        try:
            training.train(path, resume=checkpoint["path"])
        except RuntimeError as error:
            assert "Stopping safely: only 6.7 GB" in str(error)
        else:
            raise AssertionError("CPU emergency guard was not exercised")
    finally:
        training.psutil.virtual_memory = original
    emergency = Path(cfg["run"]) / "last.pt"
    a, b = [
        torch.load(p, map_location="cpu", weights_only=True, mmap=True)
        for p in [checkpoint["path"], emergency]
    ]
    assert a["step"] == b["step"] == 3
    for key in ["model", "ema", "optimizer", "python_rng", "torch_rng", "cuda_rng", "best"]:
        identical(a[key], b[key])
    assert not torch.cuda.is_initialized()
    save(
        Path(recovery["root"]) / "CPU-emergency-proof.json",
        {
            "status": "passed-actual-emergency-guard-before-update-preserves-all-states-and-RNG",
            "input": checkpoint,
            "emergency_checkpoint": ref(emergency),
            "step": 3,
            "exact_fields": [
                "model",
                "ema",
                "optimizer",
                "python_rng",
                "torch_rng",
                "cuda_rng",
                "best",
            ],
            "CUDA_initialized": False,
        },
    )
    save(Path(recovery["root"]) / "resume-input.json", ref(emergency))


def controller(recovery_path):
    from train_directional_bank_detachment import guard, ref, save

    recovery = read(recovery_path)
    root = Path(recovery["root"])
    assert ref(__file__) == recovery["adapter"]
    plan = read(recovery["training_plan"])
    guard(plan)
    with (root / "controller.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(recovery["training_plan"]),
        "completed": {"connected": recovery["connected_result"]},
        "boundary_updates": plan["boundary_updates"],
        "engineering_only": recovery["engineering_only"],
    }

    def record(state, **values):
        info.update(status=state, updated_unix=time.time(), **values)
        save(root / "status.json", info)
        print(json.dumps({"status": state}), flush=True)

    try:
        record("waiting-for-stable-memory-before-exact-horizon-recovery")
        since = None
        while True:
            available = psutil.virtual_memory().available
            with (root / "memory-observations.jsonl").open("a") as stream:
                stream.write(json.dumps({"unix": time.time(), "available_bytes": available}) + "\n")
            if available >= recovery["minimum_stable_available_GiB"] * 2**30:
                since = time.monotonic() if since is None else since
                if time.monotonic() - since >= recovery["stable_memory_seconds"]:
                    break
            else:
                since = None
            time.sleep(10)
        modes = (
            ["replay", "emergency-proof", "resume"]
            if recovery["engineering_only"]
            else ["replay", "resume"]
        )
        for mode in modes:
            guard(plan)
            if mode == "resume":
                checkpoint = read(root / "resume-input.json")
                prefix = (
                    read(recovery["prefix_samples"]["path"])
                    if not recovery["engineering_only"]
                    else read(read(root / "initial-replay.json")["samples"]["path"])
                )
                if recovery["engineering_only"]:
                    recovery["prefix_samples"] = read(root / "initial-replay.json")["samples"]
                    save(recovery_path, recovery)
                import torch

                state = torch.load(
                    checkpoint["path"], map_location="cpu", weights_only=True, mmap=True
                )
                source_metrics = Path(recovery["prefix_metrics"])
                if recovery["engineering_only"]:
                    source_metrics = (
                        Path(read(root / "initial-replay.json")["checkpoint"]["path"]).parent
                        / "metrics.jsonl"
                    )
                target = Path(plan["arms"][1]["run"])
                target.mkdir(parents=True, exist_ok=True)
                rows = [json.loads(line) for line in source_metrics.read_text().splitlines()]
                (target / "metrics.jsonl").write_text(
                    "".join(
                        json.dumps(row) + "\n"
                        for row in rows
                        if row.get("step", 0) <= state["step"]
                    )
                )
                save(
                    root / "detached-sampled-observations.json",
                    [row for row in prefix if row["step"] <= state["step"]],
                )
                del state
            with (root / (mode + ".log")).open("x") as log:
                child = subprocess.Popen(
                    [
                        recovery["python"],
                        "-P",
                        recovery["adapter"]["path"],
                        mode,
                        str(recovery_path),
                    ],
                    cwd=recovery["work"],
                    env=dict(os.environ),
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-bank-detachment-memory-recovery-" + mode, child=owner, mode=mode)
                try:
                    code = child.wait(
                        timeout=recovery["resume_timeout_seconds"] if mode == "resume" else 900
                    )
                except subprocess.TimeoutExpired:
                    assert psutil.Process(child.pid).create_time() == owner["created"]
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=30)
                    raise
            assert code == 0, (mode, code)
        case_ref = ref(root / "detached-result.json")
        info["completed"]["detached"] = case_ref
        a, b = read(recovery["connected_result"]["path"]), read(case_ref["path"])
        samples = [read(case["sampled_observations"]["path"]) for case in (a, b)]
        for x, y in zip(*samples, strict=True):
            assert all(
                x[key] == y[key]
                for key in [
                    "step",
                    "domain",
                    "legacy_batch_sha256",
                    "input_sha256",
                    "full_batch_sha256",
                ]
            )
        for key in [
            "initial_EMA_exact",
            "initial_local_sha256",
            "initial_bank_sha256",
            "initial_model_sha256",
            "first_raw_gradient_sha256",
            "first_output_sha256",
            "DINO_sha256",
        ]:
            assert a["capture"][key] == b["capture"][key]
        assert a["source_sha256"] == b["source_sha256"]
        import torch

        states = [
            torch.load(case["checkpoint"]["path"], map_location="cpu", weights_only=True, mmap=True)
            for case in (a, b)
        ]
        from audit_flat_palette import identical

        for key in ["python_rng", "torch_rng", "cuda_rng"]:
            identical(states[0][key], states[1][key])
        for x, y in zip(a["logged_observations"], b["logged_observations"], strict=True):
            assert all(x[key] == y[key] for key in ["step", "domain", "lr"])
        guard(plan)
        record(
            "completed-matched-bank-detachment-CPU-six-update-preflight"
            if recovery["engineering_only"]
            else "completed-matched-bank-detachment-original4000-awaiting-full-quality-and-native-review",
            all_sampled_full_legacy_and_input_observations_match=True,
            all_logged_domains_and_LRs_match=True,
            sampled_observation_pairs=len(samples[0]),
            logged_domain_LR_pairs=len(a["logged_observations"]),
        )
    except BaseException as error:
        record("failed-bank-detachment-memory-recovery-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "replay", "emergency-proof", "resume"])
    parser.add_argument("recovery_plan", type=Path)
    args = parser.parse_args()
    if args.mode == "controller":
        controller(args.recovery_plan)
    elif args.mode == "emergency-proof":
        emergency_cpu_proof(args.recovery_plan)
    else:
        run_worker(args.recovery_plan, args.mode)
