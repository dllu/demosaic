"""Match 0/8-stop smooth palettes from V95 without changing V43's architecture."""

import argparse
import collections
import json
import os
import random
import shutil
import subprocess
import time
from pathlib import Path

import psutil
import yaml
from evaluate_v43_quality_trial import monitor_child
from recover_v43_quality_trial import headroom, resource_snapshot, stop_owned_child
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import compare_pair, live

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / ".cache/quality-first-20261020"
PARENT_SHA = "189f5530ef8be6384e101e00fe50ece19297436b0c65b5bb3cabbb2f327e2bb6"
MODEL_SHA = "8c8646e5e984148338748423fbb97b36143b9d14b494b8f7844520c282c826f3"
ARMS = ("V96", "V97")


def sample_kind(seed, index):
    rng = random.Random(seed + index)
    draw = rng.random()
    if draw < 0.1:
        rng.uniform(-13, -1)
        return "neutral-flat" if rng.random() < 0.5 else "colored-flat"
    return "weak" if draw < 0.1 + 0.15 else "strong" if draw < 0.1 + 0.2 else "photo"


def audit_data(config, output):
    import torch

    from demosaic.data import CleanDataset, smooth_scene
    from demosaic.train import domain_indices, training_domain

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    records = [json.loads(line) for line in Path(config["manifest"]).read_text().splitlines()]
    assert sum(r["split"] == "train" for r in records) == 88484
    options = {
        key: config[key]
        for key in (
            "seed",
            "synthetic_fraction",
            "flat_fraction",
            "weak_texture_fraction",
            "augmentation_downsample",
            "optical_blur_probability",
            "photographic_low_contrast_fraction",
        )
    }
    options.update(patch_size=64, records=records)
    control, wide = [
        CleanDataset(config["manifest"], **options, flat_chroma_stops=stops) for stops in (0, 8)
    ]
    indices = list(domain_indices("commons", 0, 64, 16, 57, 0.25, 0.25))[:256]
    coverage = collections.Counter()
    changed = 0
    for index in indices:
        kind = sample_kind(57, index)
        before, after = control[index]["rgb"], wide[index]["rgb"]
        assert all(
            x.shape == (3, 64, 64)
            and x.dtype == torch.float32
            and torch.isfinite(x).all()
            and x.min() >= 0
            and x.max() <= 1
            for x in (before, after)
        )
        equal = torch.equal(before, after)
        assert equal == (kind != "colored-flat"), (index, kind)
        coverage[kind] += 1
        changed += not equal
    assert set(coverage) == {"neutral-flat", "colored-flat", "weak", "strong", "photo"}
    neutral, largest = 0, 0.0
    for index in range(1000):
        a, b = random.Random(20261021 + index), random.Random(20261021 + index)
        before, after = smooth_scene(8, a), smooth_scene(8, b, chroma_stops=8)
        assert a.getstate() == b.getstate()
        if torch.equal(before[0], before[1]) and torch.equal(before[1], before[2]):
            assert torch.equal(before, after)
            neutral += 1
        else:
            means = after.mean((1, 2))
            largest = max(largest, float(means.max() / means.min()))
    domains = collections.Counter(training_domain(s, 57, 0.25, 0.25) for s in range(1, 4001))
    kinds = collections.Counter(
        sample_kind(57, i) for i in domain_indices("commons", 0, 4000, 16, 57, 0.25, 0.25)
    )
    assert domains == {"commons": 2026, "native": 990, "paired": 984}
    assert kinds["colored-flat"] == 1618 and largest > 32 and not torch.cuda.is_initialized()
    result = {
        "status": "current-V95-data-route-and-wider-flat-palette-audit-passed",
        "manifest": ref(config["manifest"]),
        "actual_native64_clean_samples": len(indices),
        "kind_counts": dict(coverage),
        "changed_clean_samples": changed,
        "only_colored_smooth_clean_targets_changed": True,
        "smooth_generator_RNG_pairs": 1000,
        "neutral_fields_exact": neutral,
        "maximum_observed_wide_channel_ratio": largest,
        "planned4000_domain_batches": dict(domains),
        "planned4000_Commons_clean_draws": dict(kinds),
        "CUDA_initialized": False,
        "scope": "Actual current-recipe native64 clean data, with real curated cache reads, plus seeded generator/schedule checks. No model forward or quality claim. Affected mixed batches need not retain identical Poisson draws; per-step seeding isolates later steps. Actual CPU/native32/B1 and CUDA/native256/B16 worker proofs remain separate.",
    }
    save(output, result)
    return ref(output)


def prepare(root, artifact_root):
    original_root = BASE / "V43-curated-matched-training-v1"
    original = read(original_root / "plan.json")
    guard(original)
    completed = read(original_root / "status.json")
    assert not live(completed["controller"]) and not live(completed["child"])
    previous = BASE / "V43-curated-matched-evaluation-v1/status.json"
    status = read(previous)
    assert status["status"] == "completed-V43-quality-panels-awaiting-independent-and-native-review"
    assert not live(status["controller"]) and not live(status["child"])
    parent = read(original_root / "train-V95-result.json")["checkpoint"]
    assert parent["sha256"] == PARENT_SHA and ref(parent["path"]) == parent
    review = REPO / "docs/results/v43-curated-original20k-complete-review-v1.json"
    reviewed = read(review)
    assert reviewed["panels"]["photo"]["invariants"][3]["model_SHA256"] == MODEL_SHA
    templates = {arm: REPO / f"configs/dino-v43-v95-palette-{arm.lower()}.yaml" for arm in ARMS}
    recipes = {a: yaml.safe_load(p.read_text()) for a, p in templates.items()}
    prior_recipe = REPO / "configs/dino-v43-curated-fine-detail-v95.yaml"
    prior = yaml.safe_load(prior_recipe.read_text())
    allowed = {
        "run",
        "initialize_parent",
        "experiment_notes",
        "seed",
        "steps",
        "checkpoint_every",
        "flat_chroma_stops",
    }
    assert {
        k for k in prior.keys() | recipes["V96"].keys() if prior.get(k) != recipes["V96"].get(k)
    } <= allowed
    assert {k for k in recipes["V96"] if recipes["V96"][k] != recipes["V97"][k]} == {
        "run",
        "flat_chroma_stops",
    }
    assert [recipes[a]["flat_chroma_stops"] for a in ARMS] == [0, 8]
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    artifact_root = artifact_root.resolve()
    assert artifact_root.is_relative_to(Path("/mnt/external/demosaic"))
    assert os.path.ismount("/mnt/external")
    assert shutil.disk_usage(REPO).free >= 64 * 2**30
    assert shutil.disk_usage("/mnt/external").free >= 384 * 2**30
    root.mkdir(parents=True, exist_ok=False)
    artifact_root.mkdir(parents=True, exist_ok=False)
    marker = artifact_root / "artifact-owner.json"
    save(marker, {"plan_root": str(root), "scope": "V96/V97 matched palette training only"})
    work = root / "work"
    sources = list((REPO / "src/demosaic").glob("*.py"))
    for source in sources:
        assert (
            ref(source)["sha256"]
            == ref(Path(original["work"]) / "src/demosaic" / source.name)["sha256"]
        )
    sources += [
        REPO / p
        for p in (
            "scripts/train_v95_palette_trial.py",
            "scripts/train_v43_quality_trial.py",
            "scripts/evaluate_v43_quality_trial.py",
            "scripts/recover_v43_quality_trial.py",
            "scripts/train_directional_bank_trial.py",
            "scripts/profile_raw_kernel_inference.py",
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/dinov3/LICENSE.md",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
        )
    ]
    for source in sources:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    inputs = [
        ref(original_root / "plan.json"),
        ref(original_root / "status.json"),
        ref(previous),
        ref(review),
        ref(marker),
        parent,
        *original["inputs"],
        *[ref(p) for p in templates.values()],
        ref(prior_recipe),
    ]
    data_audit = audit_data(recipes["V96"], root / "data-audit.json")
    inputs.append(data_audit)
    configs = {}
    for arm in ARMS:
        cfg = recipes[arm]
        assert cfg["seed"] == 57 and cfg["steps"] == 4000 and cfg["checkpoint_every"] == 1000
        assert cfg["batch_size"] == 16 and cfg["patch_size"] == 256
        assert cfg["optical_blur_probability"] == cfg["raw_clean_optical_blur_probability"] == 0
        assert cfg["weak_texture_fraction"] == 0.15
        assert cfg["photographic_low_contrast_fraction"] == 0.25
        assert cfg["initialize_parent"]["sha256"] == PARENT_SHA
        configs[arm] = {}
        for phase in ("CPU", "CUDA", "train"):
            actual = dict(cfg, run=str(artifact_root / phase / arm))
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
            path = work / "configs" / f"{phase}-{arm}.yaml"
            path.write_text(yaml.safe_dump(actual, sort_keys=False))
            configs[arm][phase] = ref(path)
    inputs = list({(i["path"], i["sha256"]): i for i in inputs}.values())
    plan = {
        "root": str(root),
        "work": str(work),
        "artifact_root": str(artifact_root),
        "parent": parent,
        "parent_step": 20000,
        "initial_model_sha256": MODEL_SHA,
        "original_training_plan": ref(original_root / "plan.json"),
        "curation": original["curation"],
        "engineering_only": False,
        "arms": list(ARMS),
        "phases": ["CPU", "CUDA", "train"],
        "proof_updates": 24,
        "planned_updates": 4000,
        "validation_steps": [1000, 2000, 3000, 4000],
        "retain_steps": [1000, 2000, 3000],
        "configs": configs,
        "python": original["python"],
        "cache_environment": original["cache_environment"],
        "disk_reserves": {"root_reserve_gib": 64, "external_reserve_gib": 384},
        "external_device": Path("/mnt/external").stat().st_dev,
        "wait_seconds": 7200,
        "stable_seconds": 60,
        "timeouts_seconds": {"CPU": 900, "CUDA": 1800, "train": 43200},
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "V96/V97 matched4000-update stages from final V95 EMA with fresh optimizer/EMA, same V43 architecture and exact numerical package, seed57/B16/native256/BF16/lr1e-5/warmup100. Only flat_chroma_stops0/8 differs; same data/weak-detail/zero-PSF recipe, 1618 affected colored-flat draws among64000 planned patches. Discarded actual24-update CPU and CUDA proofs precede production. Final4000 EMAs primary; no automatic retry, model promotion or speed work. Full primary/color/carrier/GFX evaluation and native review required.",
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(ref(root / "plan.json"))


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(plan_path),
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
        "observation_audits": {},
    }
    child, owner, snapshot = None, None, None

    def record(status, **extra):
        state.update(status=status, updated_unix=time.time(), **extra)
        save(root / "status.json", state)

    def observe():
        nonlocal snapshot
        snapshot = resource_snapshot(root)
        with (root / "resource-history.jsonl").open("a") as stream:
            stream.write(json.dumps(snapshot) + "\n")
        return snapshot

    def record_monitor(status, **extra):
        names = {
            "paused-V43-evaluation-disk-reserve": "paused-palette-training-disk-reserve",
            "running-V43-quality-evaluation": "running-palette-training-stage",
        }
        record(names[status], **extra)

    try:
        for phase in plan["phases"]:
            for arm in plan["arms"]:
                guard(plan)
                record("waiting-for-palette-training-headroom", phase=phase, arm=arm)
                began, stable = time.monotonic(), None
                while True:
                    assert time.monotonic() - began < plan["wait_seconds"]
                    stable = (
                        (time.monotonic() if stable is None else stable)
                        if headroom(observe(), plan, 48)
                        else None
                    )
                    if stable is not None and time.monotonic() - stable >= plan["stable_seconds"]:
                        break
                    time.sleep(2)
                env = dict(
                    os.environ,
                    PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
                    CUDA_VISIBLE_DEVICES="" if phase == "CPU" else "0",
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
                    owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                    record("running-palette-training-stage", child=owner)
                    monitor_child(
                        child,
                        owner,
                        plan=plan,
                        observe=observe,
                        record=record_monitor,
                        deadline=time.monotonic() + plan["timeouts_seconds"][phase],
                    )
                    assert child.wait() == 0, (phase, arm, child.returncode)
                path = root / f"{phase}-{arm}-result.json"
                result = read(path)
                assert result["owner"] == owner and result["plan"] == ref(plan_path)
                assert result["engineering_only"] == (phase != "train")
                state["completed"][f"{phase}-{arm}"] = ref(path)
            results = [read(state["completed"][f"{phase}-{a}"]["path"]) for a in plan["arms"]]
            key = "logged_training_observations" if phase == "train" else "early_observations"
            domains = (
                {"native-RAW-synthetic", "paired-RAW"} if phase == "train" else {"native", "paired"}
            )
            assert len({r["source_sha256"] for r in results}) == 1
            state["observation_audits"][phase] = compare_pair(
                *[r[key] for r in results], domains, require_changes=True
            )
            if phase == "train":
                for result in results:
                    probe = read(root / f"CUDA-{result['arm']}-result.json")
                    assert result["early_observations"] == probe["early_observations"]
            record("completed-matched-palette-phase", phase=phase)
        guard(plan)
        record("completed-matched-V95-palette-training-awaiting-full-quality-and-native-review")
    except BaseException as error:
        if child is not None and child.poll() is None:
            stop_owned_child(child, owner)
        record(
            "failed-palette-stage-preserved-no-automatic-retry",
            error=repr(error),
            last_resource_snapshot=snapshot,
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--artifact-root", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        assert args.artifact_root
        prepare(args.path, args.artifact_root)
    else:
        controller(args.path.resolve())
