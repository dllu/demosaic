"""Freeze an explicit wrapper repair with the original model/data/horizon intact."""

import argparse
import copy
import math
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from train_context_trial import alive
from train_directional_bank_trial import guard, read, ref, save

from demosaic.safety import writable_path

REPO = Path(__file__).resolve().parents[1]


def prepare(
    original_path,
    handoff_path,
    cpu_path,
    cuda_path,
    external_path,
    test_path,
    retention_path,
    output,
):
    original = read(original_path)
    guard(original)
    assert original["planned_updates"] == original["boundary_updates"] == 4000
    handoff = read(handoff_path)
    assert handoff["status"] == "completed-verified-checkpoint-handoff-original-owners-exited"
    assert handoff["training_plan"] == ref(original_path)
    assert not alive(handoff["controller"])
    assert all(not alive(owner) for owner in handoff["training_owners"].values())
    for item in [
        handoff["checkpoint"],
        handoff["original_checkpoint"],
        handoff["observations"],
        handoff["metrics"],
    ]:
        assert ref(item["path"]) == item
    external = read(external_path)
    assert external["status"] == "completed-genuine-external8plus8-recovery-exact-no-quality-result"
    assert external["model_EMA_AdamW_RNG_best_exact"] and external["all16_observations_exact"]
    assert not alive(external["controller"]) and not alive(external["child"])
    assert not external["CUDA_initialized"]
    retention = read(retention_path)
    assert (
        retention["status"]
        == "completed-real-CUDA-checkpoint-writer-repeat-and-different-state-rejection"
    )
    assert retention["identical_repeat_with_interleaved_best_save"]
    assert retention["changed_state_rejected_and_retained_unchanged"]
    for item in [
        retention["source"],
        retention["fixed_driver"],
        retention["completed_GPU_preflight"],
        retention["retained"],
    ]:
        assert ref(item["path"]) == item
    tests = ET.parse(test_path).getroot()
    assert (
        len(tests.findall(".//testcase")) == 1
        and not tests.findall(".//failure")
        and not tests.findall(".//error")
    )
    assert tests.find(".//testcase").get("classname") == "tests.test_spectral_trial_retention"
    preflights, added = [], []
    for status_path, device in [(cpu_path, "cpu"), (cuda_path, "cuda")]:
        status = read(status_path)
        assert status["status"] == "completed-spectral-engineering-preflight"
        assert (
            status["restart_full_model_EMA_AdamW_RNG_exact"]
            and status["matched_observations_and_final_RNG"]
        )
        assert not alive(status["controller"]) and not alive(status["child"])
        assert ref(status["plan"]["path"]) == status["plan"]
        previous = read(status["plan"]["path"])
        guard(previous)
        assert previous["device"] == device and previous["engineering_only"]
        assert (
            ref(REPO / "scripts/train_spectral_trial.py")["sha256"] == previous["worker"]["sha256"]
        )
        for source in (Path(original["work"]) / "src/demosaic").glob("*.py"):
            assert (
                ref(source)["sha256"]
                == ref(Path(previous["work"]) / "src/demosaic" / source.name)["sha256"]
            )
        added += [ref(status_path), status["plan"]]
        preflights.append(previous)
    assert external["preflight"] == ref(cpu_path.parent / "plan.json")
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    oldwork = Path(original["work"])
    for path in original["frozen_files"]:
        source = Path(path)
        if source.relative_to(oldwork).parts[0] == "scripts":
            continue
        target = work / source.relative_to(oldwork)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for source in (REPO / "scripts").glob("*.py"):
        target = work / "scripts" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    arms = []
    for arm in original["arms"]:
        arm = copy.deepcopy(arm)
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        old_cfg = copy.deepcopy(cfg)
        cfg["run"] = str(work / "runs" / arm["name"])
        cfg["validation_protocol"] = str(work / "configs/evaluation.yaml")
        assert {k for k in cfg if cfg[k] != old_cfg[k]} == {"run", "validation_protocol"}
        path = work / "configs" / (arm["name"] + ".yaml")
        path.write_text(yaml.safe_dump(cfg, sort_keys=True))
        arm.update(config=str(path), run=cfg["run"])
        arms.append(arm)
    run = Path(arms[0]["run"])
    run.mkdir(parents=True)
    shutil.copyfile(handoff["metrics"]["path"], run / "metrics.jsonl")
    shutil.copyfile(handoff["checkpoint"]["path"], run / "step-001000.pt")
    plan = copy.deepcopy(original)
    consumed = math.ceil(handoff["original_active_seconds_consumed"])
    assert 0 < consumed < original["timeout_seconds"]
    plan.update(
        status="frozen-explicit-spectral-retention-recovery-original4000",
        root=str(root),
        work=str(work),
        worker=ref(work / "scripts/train_spectral_trial.py"),
        arms=arms,
        recovery_of=ref(original_path),
        handoff=ref(handoff_path),
        resume={
            "control": {
                "step": 1000,
                "checkpoint": handoff["checkpoint"],
                "observations": handoff["observations"],
            }
        },
        arm_timeout_seconds={
            "control": original["timeout_seconds"] - consumed,
            "spectral": original["timeout_seconds"],
        },
        scope="Explicit retention-wrapper repair. Control resumes verified1000 and performs only remaining3000 original updates; spectral starts from original V63 EMA and performs original4000. All46 model modules/data/loss/noise/seed/B16/BF16/source RNG and original4000 LR horizon/criteria unchanged. No automatic retry, extension or promotion.",
    )
    plan["inputs"] += [
        ref(original_path),
        ref(handoff_path),
        handoff["checkpoint"],
        handoff["observations"],
        handoff["metrics"],
        ref(external_path),
        external["plan"],
        external["result"],
        ref(test_path),
        ref(retention_path),
        ref(REPO / "tests/test_spectral_trial_retention.py"),
        ref(__file__),
        *added,
    ]
    unique = {}
    for item in plan["inputs"]:
        if item["path"] in unique:
            assert unique[item["path"]] == item["sha256"]
        unique[item["path"]] = item["sha256"]
    plan["inputs"] = [{"path": path, "sha256": sha} for path, sha in sorted(unique.items())]
    plan["frozen_files"] = {
        str(p): ref(p)["sha256"]
        for p in work.rglob("*")
        if p.is_file() and p.relative_to(work).parts[0] != "runs"
    }
    assert (
        plan["worker"]["sha256"]
        == preflights[0]["worker"]["sha256"]
        == preflights[1]["worker"]["sha256"]
    )
    guard(plan)
    save(root / "plan.json", plan)
    print(
        {
            "plan": ref(root / "plan.json"),
            "frozen_files": len(plan["frozen_files"]),
            "inputs": len(plan["inputs"]),
            "original_control_timeout_remaining": plan["arm_timeout_seconds"]["control"],
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["original", "handoff", "cpu", "cuda", "external", "test", "retention", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    prepare(
        a.original.resolve(),
        a.handoff.resolve(),
        a.cpu.resolve(),
        a.cuda.resolve(),
        a.external.resolve(),
        a.test.resolve(),
        a.retention.resolve(),
        a.output,
    )
