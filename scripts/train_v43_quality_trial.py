"""Run matched V43 data-quality stages after a completed manual corpus freeze."""

import argparse
import json
import math
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
MODEL_SHA = "4a45d92210acaeca3d4189c78eb22aa1cbc33f28b971dbeb56d1f6f29d62ed9a"
DINO_SHA = "35035ba142eb119cd5980cf0d9809bfa28f622538c259ffb0fcf348ca6e68898"
RECIPES = {
    "V93": "dino-v43-curated-small-v93.yaml",
    "V94": "dino-v43-curated-large-v94.yaml",
    "V95": "dino-v43-curated-fine-detail-v95.yaml",
}


def live(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def resources(root, available=24, *, root_reserve_gib=64, external_reserve_gib=500):
    return (
        psutil.virtual_memory().available >= available * 2**30
        and shutil.disk_usage(root).free >= root_reserve_gib * 2**30
        and shutil.disk_usage("/mnt/external").free >= external_reserve_gib * 2**30
    )


def prepare(curation_path, root, *, cpu_only=False, validation_proof=False, artifact_root=None):
    import yaml

    assert not validation_proof or cpu_only
    curation = read(curation_path)
    assert curation["status"] == (
        "provisional-membership-for-CPU-launcher-proof"
        if cpu_only
        else "frozen-curated-matched-V43-cohorts"
    )
    assert curation["validation_and_test_IDs_unchanged"]
    inputs = curation["inputs"] + [ref(curation_path)]
    inputs += [v["manifest"] for v in curation["cohorts"].values()]
    for item in inputs:
        assert ref(item["path"]) == item
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    disk_reserves = {"root_reserve_gib": 64, "external_reserve_gib": 500}
    if artifact_root is None:
        artifact_root = work / "runs"
    else:
        artifact_root = Path(artifact_root).resolve()
        assert artifact_root.is_relative_to(Path("/mnt/external/demosaic"))
        artifact_root.mkdir(parents=True, exist_ok=False)
        marker = artifact_root / "artifact-owner.json"
        save(
            marker,
            {
                "plan_root": str(root),
                "scope": "Artifact namespace reserved for this matched V43 study; originals and datasets are elsewhere.",
            },
        )
        inputs.append(ref(marker))
        disk_reserves["external_reserve_gib"] = 384
    sources = list((REPO / "src/demosaic").glob("*.py")) + [
        REPO / name
        for name in (
            "scripts/train_v43_quality_trial.py",
            "scripts/train_directional_bank_trial.py",
            "scripts/profile_raw_kernel_inference.py",
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
            "third_party/dinov3/LICENSE.md",
        )
    ]
    for source in sources:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    configs, parent, treatments = {}, None, {}
    for arm, name in RECIPES.items():
        template = REPO / "configs" / name
        inputs.append(ref(template))
        config = yaml.safe_load(template.read_text())
        initializer = config["initialize_parent"]
        assert ref(initializer["checkpoint"])["sha256"] == initializer["sha256"]
        current_parent = ref(initializer["checkpoint"])
        assert parent is None or parent == current_parent
        parent = current_parent
        cohort = curation["cohorts"]["small" if arm == "V93" else "large"]
        if cpu_only:
            config["manifest"] = cohort["manifest"]["path"]
        assert ref(config["manifest"]) == cohort["manifest"]
        assert config["batch_size"] == 16 and config["patch_size"] == 256
        assert config["steps"] == 20000 and config["seed"] == 56
        assert config["paired_fraction"] == config["raw_clean_fraction"] == 0.25
        assert config["precision"] == "bfloat16" and config["data_seed_per_step"]
        treatments[arm] = dict(config)
        inputs += [
            ref(config[key])
            for key in ("validation_manifest", "paired_manifest", "raw_clean_manifest")
        ]
        config["validation_protocol"] = str(work / "configs/evaluation.yaml")
        config["experiment_notes"] = (
            "Frozen matched V43 quality stage; equal20k/B16/native256/seed56; fixed final EMA endpoint, no speed study. CPU/CUDA probes are discarded."
        )
        configs[arm] = {}
        for phase in ("CPU",) if cpu_only else ("CPU", "CUDA", "train"):
            actual = dict(config, run=str(artifact_root / phase / arm))
            if cpu_only:
                actual["experiment_notes"] = (
                    "Discarded CPU-only launcher proof on provisional pre-final-ranking data; no CUDA, production training, final curation or quality claim."
                )
            if phase == "CPU":
                actual.update(
                    device="cpu",
                    precision="float32",
                    amp=False,
                    batch_size=1,
                    patch_size=32,
                    workers=0,
                    paired_workers=0,
                    raw_clean_workers=0,
                    cpu_threads=2,
                    log_every=1,
                )
            elif phase == "CUDA":
                actual["log_every"] = 1
            if validation_proof:
                actual.update(checkpoint_every=12, validation_images=2)
                actual["experiment_notes"] = (
                    "Discarded CPU validation/checkpoint-boundary proof on provisional data; planned20k schedule, stop24, validation12/24. Not production training or quality evidence."
                )
            path = work / "configs" / f"{phase}-{arm}.yaml"
            path.parent.mkdir(exist_ok=True)
            path.write_text(yaml.safe_dump(actual, sort_keys=False))
            configs[arm][phase] = ref(path)

    def differences(a, b):
        return {key for key in a.keys() | b.keys() if a.get(key) != b.get(key)}

    assert differences(treatments["V93"], treatments["V94"]) == {"manifest", "run"}
    assert differences(treatments["V94"], treatments["V95"]) == {
        "run",
        "optical_blur_probability",
        "raw_clean_optical_blur_probability",
        "weak_texture_fraction",
        "photographic_low_contrast_fraction",
    }
    inputs.append(parent)
    plan = {
        "root": str(root),
        "work": str(work),
        "artifact_root": str(artifact_root),
        "disk_reserves": disk_reserves,
        "curation": ref(curation_path),
        "parent": parent,
        "configs": configs,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "python": str(REPO / ".venv/bin/python3"),
        "HF_HOME": str(REPO / ".cache/huggingface"),
        "cache_environment": {
            name: str(REPO / ".cache" / subdir)
            for name, subdir in {
                "UV_CACHE_DIR": "uv",
                "HF_HOME": "huggingface",
                "TORCH_HOME": "torch",
                "TORCHINDUCTOR_CACHE_DIR": "inductor",
                "TRITON_CACHE_DIR": "triton",
                "XDG_CACHE_HOME": "",
                "XDG_CONFIG_HOME": "config",
                "MPLCONFIGDIR": "matplotlib",
                "CUDA_CACHE_PATH": "cuda",
                "TMPDIR": "tmp",
            }.items()
        },
        "proof_updates": 24,
        "planned_updates": 20000,
        "phases": ["CPU"] if cpu_only else ["CPU", "CUDA", "train"],
        "engineering_only": cpu_only,
        "arms": ["V95"] if validation_proof else list(RECIPES),
        "validation_preflight": validation_proof,
        "retain_steps": [12, 24] if validation_proof else [4000, 8000, 12000, 16000],
        "timeouts_seconds": {"CPU": 900, "CUDA": 1800, "train": 172800},
        "wait_seconds": 7200,
        "stable_seconds": 2 if cpu_only else 60,
        "scope": "V43 architecture and original step2000 EMA, fresh optimizer/EMA, three matched20k stages. V94-V93 changes curated Commons membership; V95-V94 changes the optical/low-contrast augmentation package. CPU/native32/B1 and CUDA/native256/B16 preflights precede all production updates. Fixed last-step EMA is the primary endpoint; training validation best is retained separately. No speed or quality claim before independent full evaluation and native crop inspection.",
    }
    if cpu_only:
        plan["scope"] = (
            "Discarded CPU-only/B1/native32 launcher proof on explicitly provisional memberships, 24 updates per arm from original V43. Checks actual initialization, all-domain training, shared observation hashes, finite states, source archives and controller sequencing; never launches CUDA/production or qualifies final corpus curation."
        )
    if validation_proof:
        plan["scope"] = (
            "Discarded genuine V43 CPU/B1/native32 validation/EMA/checkpoint-boundary proof on provisional memberships.24 updates on original20k schedule, validation at12/24, all7 conditions/4CFAs on2 validation sources. One V95 engineering arm only; compare final model/EMA/Adam/RNG and all24 inputs to the no-validation CPU witness. Not final curation, CUDA, model quality or timing evidence."
        )
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def worker(plan_path, phase, arm):
    import torch
    import yaml
    from profile_raw_kernel_inference import model_hash

    import demosaic.train as training
    from demosaic.model import ModelConfig

    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    (root / f"{phase}-{arm}.claim").open("x").close()
    config_path = plan["configs"][arm][phase]["path"]
    config = yaml.safe_load(Path(config_path).read_text())
    assert resources(root, 32, **plan.get("disk_reserves", {}))
    if phase == "CPU":
        assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    else:
        device = torch.device("cuda", torch.cuda.current_device())
        quota = min(
            torch.cuda.get_per_process_memory_fraction(device),
            24 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
        )
        torch.cuda.set_per_process_memory_fraction(quota, device)
    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    for key in ("validation_manifest", "raw_clean_manifest", "paired_manifest"):
        assert ref(config[key])["sha256"] == parent["config"][key + "_sha256"]
    expected = ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
    assert json.dumps(ModelConfig(**config["model"]).to_dict(), sort_keys=True) == json.dumps(
        expected, sort_keys=True
    )
    constructor, batch_reader, writer = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.save_checkpoint,
    )
    optimizer_factory = training.make_optimizer
    capture, early = {}, []
    counts = {
        "training_forwards": 0,
        "validation_forwards": 0,
        "DINO_calls": 0,
        "optimizer_steps": 0,
    }

    def instrument(options):
        model = constructor(options)
        capture["model"] = model

        def before(module, args, kwargs):
            assert len(args) == 5 and set(kwargs) <= {"auxiliary"}
            assert not module.training or kwargs == {"auxiliary": True}
            assert args[0].shape[0] <= config["batch_size"]
            if counts["training_forwards"] == 0:
                capture["initial_model_sha256"] = model_hash(module)
                capture["DINO_sha256"] = model_hash(module.context.backbone)
                assert (
                    capture["initial_model_sha256"] == MODEL_SHA
                    and capture["DINO_sha256"] == DINO_SHA
                )
                actual = module.restoration_state_dict()
                assert actual.keys() == parent["ema"].keys()
                assert all(torch.equal(v.cpu(), parent["ema"][k]) for k, v in actual.items())
                assert all(not p.requires_grad for p in module.context.backbone.parameters())
            counts["training_forwards" if module.training else "validation_forwards"] += 1

        def dino(*_):
            counts["DINO_calls"] += 1

        model.register_forward_pre_hook(before, with_kwargs=True)
        model.context.backbone.register_forward_hook(dino)
        return model

    def observe(*args, **kwargs):
        batch = batch_reader(*args, **kwargs)
        if args[0] <= 24:
            early.append(
                {
                    "step": args[0],
                    "domain": args[1],
                    "batch_sha256": training.batch_fingerprint(batch),
                }
            )
        return batch

    def retained(path, model, optimizer, ema, step, cfg, best):
        writer(path, model, optimizer, ema, step, cfg, best)
        if (
            (phase == "train" or plan.get("validation_preflight", False))
            and Path(path).name == "last.pt"
            and step in plan["retain_steps"]
        ):
            destination = Path(path).with_name(f"step-{step:06d}.pt")
            if destination.exists():
                # stop_after may save the same boundary again after validation.
                assert ref(path)["sha256"] == ref(destination)["sha256"]
            else:
                shutil.copyfile(path, destination)

    def optimizer(model, options):
        result = optimizer_factory(model, options)
        assert not result.state
        capture["fresh_optimizer_empty"] = True

        def after(*_):
            counts["optimizer_steps"] += 1

        result.register_step_post_hook(after)
        return result

    training.JointDemosaic, training.prepare_training_batch = instrument, observe
    training.save_checkpoint, training.make_optimizer = retained, optimizer
    updates = plan["planned_updates"] if phase == "train" else plan["proof_updates"]
    checkpoint = training.train(
        config_path,
        initialize=plan["parent"]["path"],
        stop_after=None if phase == "train" else updates,
    )
    model = capture.pop("model")
    assert model_hash(model.context.backbone) == DINO_SHA
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    for key, value in config.items():
        if key != "validation_protocol":
            assert state["config"][key] == value, key
    assert state["step"] == counts["optimizer_steps"] == counts["training_forwards"] == updates
    assert counts["DINO_calls"] == counts["training_forwards"] + counts["validation_forwards"]
    assert state["config"]["initialized_from"] == {**plan["parent"], "step": 2000}
    assert json.dumps(
        ModelConfig.from_checkpoint(state["model_config"]).to_dict(), sort_keys=True
    ) == json.dumps(expected, sort_keys=True)
    for section in ("model", "ema"):
        assert all(torch.isfinite(v).all() for v in state[section].values())
        assert any(not torch.equal(v, parent["ema"][k]) for k, v in state[section].items())
    for value in state["optimizer"]["state"].values():
        assert int(value["step"]) == updates
        assert all(torch.isfinite(v).all() for v in value.values() if isinstance(v, torch.Tensor))
    for key in ("manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"):
        assert state["config"][key + "_sha256"] == ref(config[key])["sha256"]
    metrics_path = checkpoint.parent / "metrics.jsonl"
    metrics = [json.loads(line) for line in metrics_path.read_text().splitlines()]
    rows = [r for r in metrics if r["event"] == "train"]
    assert {r["domain"] for r in rows} == {"synthetic", "native-RAW-synthetic", "paired-RAW"}
    assert all(math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"]) for r in rows)
    if phase != "train":
        assert len(rows) == updates
        if plan.get("validation_preflight", False):
            assert counts["validation_forwards"] == 120
            assert [r["step"] for r in metrics if r["event"] == "validation"] == [12, 24]
            assert all((checkpoint.parent / f"step-{n:06d}.pt").exists() for n in (12, 24))
        else:
            assert counts["validation_forwards"] == 0
    else:
        assert [r["step"] for r in rows] == [1, *range(25, updates + 1, 25)]
        assert [r["step"] for r in metrics if r["event"] == "validation"] == [
            4000,
            8000,
            12000,
            16000,
            20000,
        ]
    if phase == "CPU":
        assert not torch.cuda.is_initialized()
    guard(plan)
    save(
        root / f"{phase}-{arm}-result.json",
        {
            "status": "completed-V43-quality-stage-awaiting-independent-evaluation"
            if phase == "train"
            else "completed-discarded-V43-training-preflight",
            "plan": ref(plan_path),
            "phase": phase,
            "arm": arm,
            "counts": counts,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "checkpoint": ref(checkpoint),
            "metrics": ref(metrics_path),
            **capture,
            "early_observations": early,
            "logged_training_observations": rows,
            "engineering_only": phase != "train",
            "CUDA_initialized": torch.cuda.is_initialized(),
            "source_sha256": state["config"]["source_sha256"],
            "scope": plan["scope"],
        },
    )


def compare_pair(first, second, exact_domains, *, require_changes):
    audit = {"identical_shared_observations": 0, "changed_treatment_observations": 0}
    for a, b in zip(first, second, strict=True):
        assert (a["step"], a["domain"]) == (b["step"], b["domain"])
        equal = a["batch_sha256"] == b["batch_sha256"]
        if a["domain"] in exact_domains:
            assert equal, (a["step"], a["domain"])
            audit["identical_shared_observations"] += 1
        else:
            audit["changed_treatment_observations"] += not equal
    assert audit["identical_shared_observations"] > 0
    if require_changes:
        assert audit["changed_treatment_observations"] > 0
    return audit


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child, identity = None, None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "status.json", state)

    def stop():
        if child is not None and child.poll() is None:
            assert psutil.Process(child.pid).create_time() == identity["created"]
            assert os.getsid(child.pid) == child.pid
            import signal

            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                assert psutil.Process(child.pid).create_time() == identity["created"]
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=10)

    try:
        curation = read(plan["curation"]["path"])
        if not plan["engineering_only"]:
            screen_ref = next(
                x
                for x in curation["inputs"]
                if Path(x["path"]).parent.name == "source-scores"
                and Path(x["path"]).name == "receipt.json"
            )
            assert ref(screen_ref["path"]) == screen_ref
            owner = read(screen_ref["path"])["owner"]
            record("waiting-for-original-corpus-screen-owner-exit", dependency=owner)
            deadline = time.monotonic() + plan["wait_seconds"]
            while live(owner):
                assert time.monotonic() < deadline
                time.sleep(2)
        for phase in plan["phases"]:
            for arm in plan["arms"]:
                guard(plan)
                record("waiting-for-stable-training-headroom", phase=phase, arm=arm)
                began, stable = time.monotonic(), None
                while True:
                    assert time.monotonic() - began < plan["wait_seconds"]
                    stable = (
                        (time.monotonic() if stable is None else stable)
                        if resources(root, 48, **plan.get("disk_reserves", {}))
                        else None
                    )
                    if stable is not None and time.monotonic() - stable >= plan["stable_seconds"]:
                        break
                    time.sleep(5)
                for directory in plan["cache_environment"].values():
                    Path(directory).mkdir(parents=True, exist_ok=True)
                env = dict(
                    os.environ,
                    PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
                    CUDA_VISIBLE_DEVICES="" if phase == "CPU" else "0",
                    HF_HOME=plan["HF_HOME"],
                    HF_HUB_OFFLINE="1",
                    TRANSFORMERS_OFFLINE="1",
                    OMP_NUM_THREADS="2" if phase == "CPU" else "4",
                    OPENBLAS_NUM_THREADS="2",
                    PYTHONDONTWRITEBYTECODE="1",
                )
                env.update(plan["cache_environment"])
                with (root / f"{phase}-{arm}.log").open("xb") as log:
                    child = subprocess.Popen(
                        [
                            plan["python"],
                            "-P",
                            str(work / "scripts/train_v43_quality_trial.py"),
                            "worker",
                            str(plan_path),
                            "--phase",
                            phase,
                            "--arm",
                            arm,
                        ],
                        cwd=work,
                        env=env,
                        stdin=subprocess.DEVNULL,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        start_new_session=True,
                    )
                    identity = {
                        "pid": child.pid,
                        "created": psutil.Process(child.pid).create_time(),
                    }
                    record("running-V43-quality-stage", phase=phase, arm=arm, child=identity)
                    deadline = time.monotonic() + plan["timeouts_seconds"][phase]
                    while child.poll() is None:
                        assert resources(root, **plan.get("disk_reserves", {})), (
                            "Training resource floor"
                        )
                        assert time.monotonic() < deadline, "Training stage runtime bound"
                        time.sleep(2)
                    assert child.wait() == 0, (phase, arm, child.returncode)
                path = root / f"{phase}-{arm}-result.json"
                result = read(path)
                assert result["owner"] == identity and result["plan"] == ref(plan_path)
                assert result["engineering_only"] is (phase != "train")
                state["completed"][f"{phase}-{arm}"] = ref(path)
                record("completed-V43-quality-stage", phase=phase, arm=arm)
            if plan.get("validation_preflight", False):
                record("completed-discarded-CPU-validation-checkpoint-boundary-proof")
                continue
            results = {
                arm: read(state["completed"][f"{phase}-{arm}"]["path"]) for arm in plan["arms"]
            }
            observed = {
                arm: value["early_observations"]
                if phase != "train"
                else value["logged_training_observations"]
                for arm, value in results.items()
            }
            native_domains = (
                {"native", "paired"} if phase != "train" else {"native-RAW-synthetic", "paired-RAW"}
            )
            paired_domains = {"paired"} if phase != "train" else {"paired-RAW"}
            paired = {
                "larger_data_shared_domains": compare_pair(
                    observed["V93"],
                    observed["V94"],
                    native_domains,
                    require_changes=phase == "train",
                ),
                "fine_detail_paired_domain": compare_pair(
                    observed["V94"],
                    observed["V95"],
                    paired_domains,
                    require_changes=phase == "train",
                ),
            }
            assert len({value["source_sha256"] for value in results.values()}) == 1
            record(
                "completed-V43-phase-matched-observation-audit",
                phase=phase,
                observation_audit=paired,
            )
        guard(plan)
        record(
            "completed-discarded-CPU-launcher-proof"
            if plan["engineering_only"]
            else "completed-matched-V43-training-awaiting-full-evaluation-and-native-review"
        )
    except BaseException as error:
        stop()
        record("failed-V43-quality-stage-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller", "worker"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--artifact-root",
        type=Path,
        help="Reserve a fresh /mnt/external/demosaic directory for run artifacts; plans/code stay local. Keeps 384 GiB external/64 GiB root free.",
    )
    parser.add_argument(
        "--cpu-only",
        action="store_true",
        help="Discarded launcher proof on explicitly provisional memberships; never launches CUDA or production training.",
    )
    parser.add_argument(
        "--validation-proof",
        action="store_true",
        help="CPU-only V95 checkpoint/validation boundary proof; keeps production schedules unchanged.",
    )
    parser.add_argument("--phase", choices=("CPU", "CUDA", "train"))
    parser.add_argument("--arm", choices=tuple(RECIPES))
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.output
        prepare(
            args.path.resolve(),
            args.output,
            cpu_only=args.cpu_only,
            validation_proof=args.validation_proof,
            artifact_root=args.artifact_root,
        )
    elif args.mode == "worker":
        assert args.phase and args.arm
        worker(args.path.resolve(), args.phase, args.arm)
    else:
        controller(args.path.resolve())
