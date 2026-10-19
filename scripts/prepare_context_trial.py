"""Freeze the actual source and recipe for discarded or full context comparisons."""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

import yaml
from train_context_trial import alive
from train_directional_interval_trial import guard, read, ref, save

from demosaic.safety import writable_path

REPO = Path(__file__).resolve().parents[1]
NATIVE_PLAN = REPO / ".cache/experiments/native-data-v84-v85-original20k-v1/plan.json"
COHORT = Path("/mnt/external/demosaic/commons-context320-cohort-20261019-v1/receipt.json")


def prepare(root, device, boundary, cpu_preflight=None, cuda_preflight=None):
    if device == "cpu" and boundary != 16:
        raise ValueError("CPU execution is a discarded16-update engineering check")
    original = read(NATIVE_PLAN)
    assert (
        ref(NATIVE_PLAN)["sha256"]
        == "5dd3250ebda9c16cceb295f5d4788bedc81f54a2e78f03f475141ce4b35f24d1"
    )
    cohort = read(COHORT)
    assert cohort["selected_train_sources"] == 50912
    assert ref(cohort["manifest"]["path"]) == cohort["manifest"]
    engineering = boundary < 4000
    root = writable_path(root)
    if root.exists():
        raise ValueError("Choose a fresh context experiment root")
    root.mkdir(parents=True)
    work = root / "work"
    work.mkdir()
    files = [
        *sorted((REPO / "src/demosaic").glob("*.py")),
        *sorted((REPO / "scripts").glob("*.py")),
    ]
    files += [
        REPO / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
            "third_party/dinov3/LICENSE.md",
            "docs/training-context-v86-v87.md",
        )
    ]
    for source in files:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    arms, configs, input_configs = [], [], []
    for name, version in (("control", 86), ("context", 87)):
        source = REPO / f"configs/dino-convnext-training-context-{name}-v{version}.yaml"
        cfg = yaml.safe_load(source.read_text())
        assert cfg["manifest"] == cohort["manifest"]["path"]
        assert cfg["steps"] == 4000 and cfg["seed"] == 54
        cfg["run"] = str(work / f"runs/{name}-v{version}")
        if device == "cpu":
            cfg.update(
                device="cpu",
                batch_size=1,
                patch_size=64,
                loss_patch_size=32,
                validation_patch_size=32,
                forward_patch_size=32 if name == "control" else 64,
                precision="float32",
                amp=False,
                workers=0,
                paired_workers=0,
                raw_clean_workers=0,
                cpu_threads=2,
            )
        target = work / source.relative_to(REPO)
        target.write_text(yaml.safe_dump(cfg, sort_keys=True))
        arms.append(
            {
                "name": name,
                "version": version,
                "config": str(target),
                "forward_size": cfg["forward_patch_size"],
                "run": cfg["run"],
            }
        )
        configs.append(cfg)
        input_configs.append(ref(source))
    assert configs[0].keys() == configs[1].keys()
    assert {k for k in configs[0] if configs[0][k] != configs[1][k]} == {
        "run",
        "forward_patch_size",
    }
    assert (
        original["parent"]["sha256"]
        == "ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5"
    )
    assert ref(original["parent"]["path"]) == original["parent"]
    extra = [
        ref(NATIVE_PLAN),
        ref(COHORT),
        cohort["manifest"],
        *input_configs,
        ref(REPO / "docs/training-context-v86-v87.md"),
    ]
    if not engineering:
        if cpu_preflight is None or cuda_preflight is None:
            raise ValueError("Actual completed CPU and intended CUDA preflights are required")
        for path, expected_device in ((cpu_preflight, "cpu"), (cuda_preflight, "cuda")):
            status = read(path)
            assert status["status"] == "completed-context-engineering-preflight"
            assert not alive(status["controller"]) and not alive(status["child"])
            previous = read(status["plan"]["path"])
            assert ref(status["plan"]["path"]) == status["plan"]
            assert previous["device"] == expected_device and previous["boundary_updates"] == 16
            guard(previous)
            for p in (REPO / "src/demosaic").glob("*.py"):
                assert (
                    ref(p)["sha256"]
                    == ref(Path(previous["work"]) / "src/demosaic" / p.name)["sha256"]
                )
            assert (
                ref(work / "scripts/train_context_trial.py")["sha256"]
                == previous["worker"]["sha256"]
            )
            assert status["final_RNG_states_match"] and status["archived_source_and_data_exact"]
            assert status["paired_observation_audit"]["all_source_and_supervision_pairs_exact"]
            for arm in previous["arms"]:
                result = status["completed"][arm["name"]]
                assert ref(result["path"]) == result
                case = read(result["path"])
                assert (
                    case["actual_step"] == 16
                    and case["planned_steps"] == 4000
                    and case["engineering_only"]
                )
                assert case["finite_states"] == {"model": 91, "EMA": 91, "AdamW": 89}
                assert case["capture"]["DINO_sha256"] == original["DINO_sha256"]
            extra += [ref(path), status["plan"]]
    bindings = {}
    for item in [*original["inputs"], *extra]:
        if item["path"] in bindings:
            assert bindings[item["path"]] == item["sha256"]
        bindings[item["path"]] = item["sha256"]
    cache_environment = {
        "HF_HOME": str(REPO / ".cache/huggingface"),
        "TORCH_HOME": str(REPO / ".cache/torch"),
        "XDG_CACHE_HOME": str(REPO / ".cache"),
        "TRITON_CACHE_DIR": str(REPO / ".cache/triton"),
        "TORCHINDUCTOR_CACHE_DIR": str(REPO / ".cache/torchinductor"),
        "CUDA_CACHE_PATH": str(REPO / ".cache/cuda"),
        "TMPDIR": str(REPO / ".cache/tmp"),
    }
    for value in cache_environment.values():
        Path(value).mkdir(parents=True, exist_ok=True)
    plan = {
        "status": "frozen-context-engineering-check"
        if engineering
        else "frozen-context-original4000-no-automatic-extension",
        "repository": str(REPO),
        "root": str(root),
        "work": str(work),
        "device": device,
        "python": str(REPO / ".venv/bin/python3"),
        "cache_environment": cache_environment,
        "parent": original["parent"],
        "DINO_sha256": original["DINO_sha256"],
        "worker": ref(work / "scripts/train_context_trial.py"),
        "arms": arms,
        "planned_updates": 4000,
        "boundary_updates": boundary,
        "engineering_only": engineering,
        "source_size": configs[0]["patch_size"],
        "loss_size": configs[0]["loss_patch_size"],
        "source_cohort": ref(COHORT),
        "training_photo_sources": 50912,
        "native_captures": 128,
        "native_groups": 106,
        "paired_scenes": 32,
        "retain_steps": [16] if engineering else [1000, 4000],
        "minimum_worker_available_gib": 48,
        "stable_available_gib": 48,
        "stable_memory_seconds": 10 if engineering else 60,
        "wait_seconds": 900 if engineering else 14400,
        "per_arm_timeout_seconds": (900 if device == "cpu" else 600) if engineering else 14400,
        "inputs": [{"path": p, "sha256": s} for p, s in sorted(bindings.items())],
        "frozen_files": {str(p): ref(p)["sha256"] for p in sorted(work.rglob("*")) if p.is_file()},
        "criteria": ref(work / "docs/training-context-v86-v87.md"),
        "git_head_at_freeze": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
        ).strip(),
        "scope": "Identical observed source/noise and central supervised fields; only actual forward extent and output path differ. Discard engineering weights. Full original4000 endpoints require complete fixed quality/native review before eligibility, with no automatic extension, retry, integration or promotion. Root128GiB/external500GiB, active24GiB available RAM,24GiB CUDA quota and exact owned child bounds; controller SIGTERM has no new-checkpoint promise.",
    }
    save(root / "plan.json", plan)
    guard(plan)
    print(
        json.dumps(
            {
                "plan": ref(root / "plan.json"),
                "frozen_files": len(plan["frozen_files"]),
                "bound_inputs": len(plan["inputs"]),
                "engineering_only": engineering,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], required=True)
    parser.add_argument("--boundary-updates", type=int, choices=[16, 4000], default=16)
    parser.add_argument("--cpu-preflight", type=Path)
    parser.add_argument("--cuda-preflight", type=Path)
    args = parser.parse_args()
    prepare(
        args.output, args.device, args.boundary_updates, args.cpu_preflight, args.cuda_preflight
    )
