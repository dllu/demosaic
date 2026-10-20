"""Freeze and run discarded preflights or the fixed V88/V89 spectral trial."""

import argparse
import gc
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
import yaml
from train_context_trial import alive
from train_directional_bank_trial import guard, read, ref, save

from demosaic.safety import writable_path

REPO = Path(__file__).resolve().parents[1]
PRIOR = Path("/mnt/external/demosaic/experiments/context-v86-v87-original4k-v1/plan.json")
FUTURE = Path("/mnt/external/demosaic/commons-post4557-reviewed-20261020-v1")


def prepare(root, device, full=False, cpu_preflight=None, cuda_preflight=None):
    previous = read(PRIOR)
    assert (
        ref(PRIOR)["sha256"] == "f2de4316d207d960c9cb84c1555fc1b8fdb83fbeedba0735ad1d216acbd91206"
    )
    assert not full or device == "cuda"
    root = writable_path(root).resolve()
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    work.mkdir()
    paths = [
        *sorted((REPO / "src/demosaic").glob("*.py")),
        *sorted((REPO / "scripts").glob("*.py")),
    ]
    paths += [
        REPO / p
        for p in [
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
            "third_party/dinov3/LICENSE.md",
            "docs/spectral-v88-v89.md",
            "tests/test_raw_spectral.py",
        ]
    ]
    for source in paths:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    evidence = [
        ref(PRIOR),
        ref(FUTURE / "receipt.json"),
        ref(FUTURE / "independent-coupled-audit-v1.json"),
        ref(REPO / "docs/results/commons-post4557-preparation-complete-v1.json"),
        ref(REPO / "docs/results/commons-post4557-reviewed-v1.json"),
    ]
    future = read(FUTURE / "receipt.json")
    assert future["counts4"]["train"] == 88508 and not future["engineering_only"]
    evidence += [*future["inputs"], *future["manifests"].values()]
    preflights = []
    for supplied, expected in [(cpu_preflight, "cpu"), (cuda_preflight, "cuda")]:
        if supplied is None:
            continue
        status = read(supplied)
        assert status["status"] == "completed-spectral-engineering-preflight"
        assert not alive(status["controller"]) and not alive(status["child"])
        old = read(status["plan"]["path"])
        assert old["device"] == expected and old["boundary_updates"] == 16
        assert ref(status["plan"]["path"]) == status["plan"]
        guard(old)
        for source in (REPO / "src/demosaic").glob("*.py"):
            assert (
                ref(source)["sha256"]
                == ref(Path(old["work"]) / "src/demosaic" / source.name)["sha256"]
            )
        assert ref(work / "scripts/train_spectral_trial.py")["sha256"] == old["worker"]["sha256"]
        assert status["restart_full_model_EMA_AdamW_RNG_exact"]
        assert status["matched_observations_and_final_RNG"]
        evidence += [ref(supplied), status["plan"]]
        preflights.append(expected)
    assert device != "cuda" or "cpu" in preflights
    assert not full or preflights == ["cpu", "cuda"]
    arms = []
    cases = [("control", 88, False), ("spectral", 89, True)]
    if not full:
        cases.append(("restart", 89, True))
    for name, version, enabled in cases:
        source = (
            REPO
            / f"configs/dino-convnext-spectral-{'spectral' if enabled else 'control'}-v{version}.yaml"
        )
        cfg = yaml.safe_load(source.read_text())
        assert (cfg["steps"], cfg["seed"], cfg["patch_size"], cfg["batch_size"]) == (
            4000,
            55,
            256,
            16,
        )
        assert cfg["manifest"] == future["manifests"]["4"]["path"]
        cfg["run"] = str(work / "runs" / name)
        cfg["validation_protocol"] = str(work / "configs/evaluation.yaml")
        if not full:
            cfg.update(log_every=1, checkpoint_every=16, val_batches=1, validation_images=1)
        if device == "cpu":
            cfg.update(
                device="cpu",
                batch_size=1,
                patch_size=64,
                validation_patch_size=64,
                precision="float32",
                amp=False,
                channels_last=False,
                cpu_threads=2,
                workers=0,
                paired_workers=0,
                raw_clean_workers=0,
            )
        target = work / "configs" / f"{name}.yaml"
        target.write_text(yaml.safe_dump(cfg, sort_keys=True))
        evidence.append(ref(source))
        arms.append({"name": name, "spectral": enabled, "config": str(target), "run": cfg["run"]})
    inputs = {}
    for item in [*previous["inputs"], *evidence]:
        if item["path"] in inputs:
            assert inputs[item["path"]] == item["sha256"]
        inputs[item["path"]] = item["sha256"]
    plan = {
        "status": "frozen-spectral-original4000" if full else "frozen-discarded-spectral16",
        "repository": str(REPO),
        "root": str(root),
        "work": str(work),
        "device": device,
        "parent": previous["parent"],
        "DINO_sha256": previous["DINO_sha256"],
        "python": previous["python"],
        "cache_environment": previous["cache_environment"],
        "worker": ref(work / "scripts/train_spectral_trial.py"),
        "arms": arms,
        "boundary_updates": 4000 if full else 16,
        "planned_updates": 4000,
        "engineering_only": not full,
        "training_photo_sources": 88508,
        "native_captures": 128,
        "native_groups": 106,
        "paired_scenes": 32,
        "protocol": ref(work / "docs/spectral-v88-v89.md"),
        "training_manifest": future["manifests"]["4"],
        "inputs": [{"path": p, "sha256": s} for p, s in sorted(inputs.items())],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "stable_seconds": 60 if full else 0,
        "timeout_seconds": 14400 if full else 3600,
        "scope": "Fixed source-frozen matched spectral gate study; no automatic retry, extension or promotion.",
    }
    guard(plan)
    save(root / "plan.json", plan)
    print(
        json.dumps(
            {
                "plan": ref(root / "plan.json"),
                "source_files": len(plan["frozen_files"]),
                "inputs": len(inputs),
            }
        )
    )


def worker(plan_path, name):
    import torch
    from audit_flat_palette import train_rows
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training

    plan = read(plan_path)
    guard(plan)
    root, boundary = Path(plan["root"]), plan["boundary_updates"]
    arm = next(a for a in plan["arms"] if a["name"] == name)
    cfg = yaml.safe_load(Path(arm["config"]).read_text())
    with (root / (name + ".claim")).open("x") as stream:
        stream.write(str(os.getpid()))
    assert psutil.virtual_memory().available > 40 * 2**30
    if plan["device"] == "cpu":
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    else:
        device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(
            min(
                torch.cuda.get_per_process_memory_fraction(device),
                24 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
            ),
            device,
        )
    parent = torch.load(plan["parent"]["path"], weights_only=True, map_location="cpu", mmap=True)
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    constructor, prepare_batch, writer = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.save_checkpoint,
    )
    originals = training.reconstruction_loss, training.paired_reconstruction_loss
    observations, captures, tracking = [], [], {"current": None, "resume": None}

    def instrument(options):
        net = constructor(options)
        tracking["model"] = net

        def first_forward(module, args, kwargs, output):
            hook.remove()
            expected = parent["ema"] if tracking["resume"] is None else tracking["resume"]["model"]
            actual = module.restoration_state_dict()
            assert all(torch.equal(actual[k].cpu(), v) for k, v in expected.items())
            extra = actual.keys() - expected.keys()
            assert extra == (
                {"pretrained_rgb.raw_spectral.weight", "pretrained_rgb.raw_spectral.bias"}
                if arm["spectral"] and tracking["resume"] is None
                else set()
            )
            assert (
                torch.are_deterministic_algorithms_enabled() and not torch.backends.cudnn.benchmark
            )
            branch = module.pretrained_rgb.raw_spectral
            if branch is not None and tracking["resume"] is None:
                assert all(p.count_nonzero() == 0 for p in branch.parameters())
                module.pretrained_rgb.raw_spectral = None
                try:
                    with torch.no_grad():
                        baseline = module(*args, **kwargs)
                finally:
                    module.pretrained_rgb.raw_spectral = branch
                for a, b in zip(output, baseline, strict=True):
                    assert torch.equal(a, b), (
                        "Initial spectral output differs from actual parent replay"
                    )
            digest = model_hash(module.context.backbone)
            assert digest == plan["DINO_sha256"]
            captures.append(
                {
                    "common_initial_state_exact": True,
                    "DINO_sha256": digest,
                    "initial_output_exact_parent": tracking["resume"] is None,
                    "resuming": tracking["resume"] is not None,
                }
            )

        hook = net.register_forward_hook(first_forward, with_kwargs=True)

        def observe_forward(module, args):
            if module.training and tracking["current"] is not None:
                row = tracking["current"]
                row["actual_forward_sha256"] = training.batch_fingerprint(
                    dict(zip(["packed", "variance", "colors", "wb", "matrix"], args, strict=True))
                )
                assert row["actual_forward_sha256"] == row["expected_forward_sha256"]

        net.register_forward_pre_hook(observe_forward)
        return net

    def observed_batch(*args, **kwargs):
        batch = prepare_batch(*args, **kwargs)
        step = args[0]
        tracking["current"] = None
        if plan["engineering_only"] or step <= 16 or step % 25 == 0:
            row = {
                "step": step,
                "domain": args[1],
                "source_sha256": training.batch_fingerprint(batch),
                "expected_forward_sha256": training.batch_fingerprint(
                    {k: batch[k] for k in ["packed", "variance", "colors", "wb", "matrix"]}
                ),
            }
            observations.append(row)
            tracking["current"] = row
        return batch

    def loss_wrapper(original):
        def observe(prediction, batch, auxiliary=None, **kwargs):
            if tracking["current"] is not None:
                row = tracking["current"]
                row["actual_loss_sha256"] = training.batch_fingerprint(batch)
                assert row["actual_loss_sha256"] == row["source_sha256"]
                assert "actual_forward_sha256" in row
                assert prediction.shape[-2:] == (cfg["patch_size"],) * 2
                save(root / (name + "-observations.json"), observations)
                tracking["current"] = None
            return original(prediction, batch, auxiliary, **kwargs)

        return observe

    def retain(path, model, optimizer, ema, step, config, best):
        writer(path, model, optimizer, ema, step, config, best)
        if Path(path).name == "last.pt" and step in (1000, 4000):
            target = Path(path).with_name(f"step-{step:06d}.pt")
            assert not target.exists()
            shutil.copyfile(path, target)

    training.JointDemosaic, training.prepare_training_batch = instrument, observed_batch
    training.save_checkpoint = retain
    training.reconstruction_loss, training.paired_reconstruction_loss = map(loss_wrapper, originals)
    try:
        checkpoint = training.train(
            arm["config"],
            initialize=plan["parent"]["path"],
            stop_after=8 if name == "restart" else boundary,
        )
        if name == "restart":
            assert plan["engineering_only"]
            middle = root / "restart-step8.pt"
            shutil.copyfile(checkpoint, middle)
            tracking.pop("model")
            gc.collect()
            tracking["resume"] = torch.load(
                middle, weights_only=True, map_location="cpu", mmap=True
            )
            checkpoint = training.train(arm["config"], resume=middle, stop_after=8)
    finally:
        training.JointDemosaic, training.prepare_training_batch, training.save_checkpoint = (
            constructor,
            prepare_batch,
            writer,
        )
        training.reconstruction_loss, training.paired_reconstruction_loss = originals
    model = tracking.pop("model")
    assert model_hash(model.context.backbone) == plan["DINO_sha256"]
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    state = torch.load(checkpoint, weights_only=True, map_location="cpu", mmap=True)
    assert state["step"] == boundary and state["config"]["steps"] == 4000
    assert state["config"]["manifest_sha256"] == plan["training_manifest"]["sha256"]
    assert state["model_config"]["raw_spectral_residual"] is arm["spectral"]
    assert state["config"]["camera_supervision"] == "sensor-valid-v1"
    assert state["config"]["training_execution"] == "deterministic-v1"
    for key in cfg:
        if key != "validation_protocol":
            assert state["config"][key] == cfg[key], key
    for field in ("model", "ema"):
        assert len(state[field]) == 91 + 2 * arm["spectral"]
        assert all(torch.isfinite(x).all() for x in state[field].values())
    assert len(state["optimizer"]["state"]) == 89 + 2 * arm["spectral"]
    for item in state["optimizer"]["state"].values():
        assert int(item["step"]) == boundary
        assert all(torch.isfinite(x).all() for x in item.values() if torch.is_tensor(x))
        assert item["exp_avg_sq"].min() >= 0
    if arm["spectral"]:
        assert [g["lr_multiplier"] for g in state["optimizer"]["param_groups"]] == [1, 20]
        assert state["model"]["pretrained_rgb.raw_spectral.weight"].count_nonzero()
        assert state["ema"]["pretrained_rgb.raw_spectral.weight"].count_nonzero()
    if boundary == 4000:
        assert state["optimizer"]["param_groups"][0]["lr"] == cfg["lr"] * 0.1
        assert (
            ref(checkpoint)["sha256"] == ref(Path(checkpoint).with_name("step-004000.pt"))["sha256"]
        )
    rows = train_rows(Path(checkpoint).parent)
    assert [r["step"] for r in rows] == (
        list(range(1, 17)) if plan["engineering_only"] else [1, *range(25, 4001, 25)]
    )
    for row in rows:
        witness = next(x for x in observations if x["step"] == row["step"])
        assert witness["source_sha256"] == row["batch_sha256"]
    guard(plan)
    save(
        root / (name + "-result.json"),
        {
            "status": "completed-one-spectral-training-arm-awaiting-comparison",
            "checkpoint": ref(checkpoint),
            "captures": captures,
            "observations": ref(root / (name + "-observations.json")),
            "metrics": ref(Path(checkpoint).parent / "metrics.jsonl"),
            "logged_observations": rows,
            "actual_step": boundary,
            "planned_steps": 4000,
            "engineering_only": plan["engineering_only"],
            "source_sha256": state["config"]["source_sha256"],
            "source_snapshot": state["config"]["source_snapshot"],
            "finite_states": {
                "model": len(state["model"]),
                "EMA": len(state["ema"]),
                "AdamW": len(state["optimizer"]["state"]),
            },
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        },
    )


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

    def record(value, **fields):
        status.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", status)
        print(json.dumps({"status": value, "arm": status.get("arm")}), flush=True)

    def resources():
        return (
            psutil.virtual_memory().available / 2**30,
            shutil.disk_usage(plan["repository"]).free / 2**30,
            shutil.disk_usage("/mnt/external").free / 2**30,
        )

    try:
        for arm in plan["arms"]:
            guard(plan)
            record("waiting-for-spectral-resources", arm=arm["name"])
            since, deadline = None, time.monotonic() + plan["timeout_seconds"]
            while True:
                assert time.monotonic() < deadline, "Spectral resource-wait bound exhausted"
                ram, disk, external = resources()
                if ram >= 48 and disk > 128 and external > 500:
                    since = time.monotonic() if since is None else since
                    if time.monotonic() - since >= plan["stable_seconds"]:
                        break
                else:
                    since = None
                time.sleep(5)
            env = dict(os.environ, **plan["cache_environment"])
            env.update(
                PYTHONPATH=str(Path(plan["work"]) / "src")
                + ":"
                + str(Path(plan["work"]) / "scripts"),
                HF_HUB_OFFLINE="1",
                CUDA_VISIBLE_DEVICES="" if plan["device"] == "cpu" else "0",
                CUBLAS_WORKSPACE_CONFIG=":4096:8",
                OMP_NUM_THREADS="2",
                OPENBLAS_NUM_THREADS="2",
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
                record("running-source-frozen-spectral-arm", child=owner)
                deadline = time.monotonic() + plan["timeout_seconds"]
                while child.poll() is None:
                    ram, disk, external = resources()
                    if time.monotonic() > deadline or ram < 24 or disk < 128 or external < 500:
                        if child.poll() is not None:
                            break
                        assert alive(owner) and os.getpgid(child.pid) == child.pid
                        os.killpg(child.pid, signal.SIGTERM)
                        child.wait(timeout=30)
                        raise RuntimeError(
                            "Owned spectral worker stopped at resource/runtime bound; no retry"
                        )
                    time.sleep(5)
                assert child.wait() == 0, arm["name"]
            status["completed"][arm["name"]] = ref(root / (arm["name"] + "-result.json"))
        import torch
        from audit_flat_palette import identical

        a, b = (read(status["completed"][k]["path"]) for k in ["control", "spectral"])
        first, second = read(a["observations"]["path"]), read(b["observations"]["path"])
        assert first == second and {x["domain"] for x in first} == {
            "commons",
            "native",
            "paired",
        }
        assert a["source_sha256"] == b["source_sha256"]
        archives = [
            {p.name: ref(p)["sha256"] for p in Path(r["source_snapshot"]).iterdir() if p.is_file()}
            for r in [a, b]
        ]
        assert archives[0] == archives[1]
        for x, y in zip(a["logged_observations"], b["logged_observations"], strict=True):
            assert all(x[k] == y[k] for k in ["step", "domain", "lr", "batch_sha256"])
        states = [
            torch.load(r["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
            for r in [a, b]
        ]
        for key in ["python_rng", "torch_rng", "cuda_rng"]:
            identical(states[0][key], states[1][key])
        if plan["engineering_only"]:
            restarted = read(status["completed"]["restart"]["path"])
            state = torch.load(
                restarted["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True
            )
            for key in [
                "model",
                "ema",
                "optimizer",
                "python_rng",
                "torch_rng",
                "cuda_rng",
                "best",
                "step",
                "model_config",
            ]:
                identical(states[1][key], state[key])
            assert read(restarted["observations"]["path"]) == second
        guard(plan)
        record(
            "completed-spectral-engineering-preflight"
            if plan["engineering_only"]
            else "completed-spectral-original4000-awaiting-full-quality-and-native-review",
            matched_observations_and_final_RNG=True,
            recorded_pairs=len(first),
            source_archives_exact=True,
            restart_full_model_EMA_AdamW_RNG_exact=True if plan["engineering_only"] else None,
        )
    except BaseException as error:
        record("failed-spectral-trial-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("root", type=Path)
    p.add_argument("--device", choices=["cpu", "cuda"], required=True)
    p.add_argument("--full", action="store_true")
    p.add_argument("--cpu-preflight", type=Path)
    p.add_argument("--cuda-preflight", type=Path)
    for mode in ["controller", "worker"]:
        p = sub.add_parser(mode)
        p.add_argument("plan", type=Path)
        if mode == "worker":
            p.add_argument("--arm", choices=["control", "spectral", "restart"], required=True)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root, args.device, args.full, args.cpu_preflight, args.cuda_preflight)
    elif args.mode == "controller":
        controller(args.plan)
    else:
        worker(args.plan, args.arm)
