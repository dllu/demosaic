"""Recover a source-identical trajectory after a resource guard, with explicit bounds."""

import argparse
import ast
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


def prepare(previous_path, tests_path, output):
    previous = read(previous_path)
    guard(previous)
    status_path = Path(previous["root"]) / "status.json"
    status = read(status_path)
    assert (
        status["status"] == "failed-spectral-trial-no-automatic-retry" and not status["completed"]
    )
    assert "resource/runtime bound" in status["error"] and status["arm"] == "control"
    assert not alive(status["controller"]) and not alive(status["child"])
    consumed = math.ceil(status["updated_unix"] - status["child"]["created"])
    assert 0 < consumed < previous["arm_timeout_seconds"]["control"]
    assert previous["planned_updates"] == previous["boundary_updates"] == 4000
    old = ast.parse(Path(previous["worker"]["path"]).read_text())
    current = ast.parse((REPO / "scripts/train_spectral_trial.py").read_text())
    for name in ["worker", "retain_checkpoint", "prepare"]:
        a = next(n for n in old.body if isinstance(n, ast.FunctionDef) and n.name == name)
        b = next(n for n in current.body if isinstance(n, ast.FunctionDef) and n.name == name)
        assert ast.dump(a, include_attributes=False) == ast.dump(b, include_attributes=False), name
    tests = ET.parse(tests_path).getroot()
    cases = tests.findall(".//testcase")
    assert len(cases) == 12 and not any(
        tests.findall(".//" + k) for k in ["failure", "error", "skipped"]
    )
    assert {c.get("classname") for c in cases} == {
        "tests.test_spectral_resources",
        "tests.test_spectral_trial_retention",
    }
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    oldwork = Path(previous["work"])
    for path in previous["frozen_files"]:
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
    for arm in previous["arms"]:
        arm = copy.deepcopy(arm)
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        before = copy.deepcopy(cfg)
        cfg["run"] = str(work / "runs" / arm["name"])
        cfg["validation_protocol"] = str(work / "configs/evaluation.yaml")
        assert {k for k in cfg if cfg[k] != before[k]} == {"run", "validation_protocol"}
        path = work / "configs" / (arm["name"] + ".yaml")
        path.write_text(yaml.safe_dump(cfg, sort_keys=True))
        arm.update(config=str(path), run=cfg["run"])
        arms.append(arm)
    handoff = read(previous["handoff"]["path"])
    resume = previous["resume"]["control"]
    assert (
        handoff["checkpoint"] == resume["checkpoint"]
        and ref(resume["checkpoint"]["path"]) == resume["checkpoint"]
    )
    run = Path(arms[0]["run"])
    run.mkdir(parents=True)
    shutil.copyfile(handoff["metrics"]["path"], run / "metrics.jsonl")
    shutil.copyfile(resume["checkpoint"]["path"], run / "step-001000.pt")
    observations = read(Path(previous["root"]) / "control-observations.json")
    discarded = [r for r in observations if r["step"] > 1000]
    assert discarded and all(
        r["source_sha256"] == r["actual_loss_sha256"]
        and r["actual_forward_sha256"] == r["expected_forward_sha256"]
        for r in discarded
    )
    save(root / "discarded-post1000-observations.json", discarded)
    lines = [
        s
        for s in (Path(previous["arms"][0]["run"]) / "metrics.jsonl").read_text().splitlines()
        if read_line(s).get("event") == "train" and read_line(s)["step"] > 1000
    ]
    (root / "discarded-post1000-metrics.jsonl").write_text("\n".join(lines) + "\n")
    plan = copy.deepcopy(previous)
    plan.update(
        status="frozen-explicit-spectral-root-reserve-recovery-original4000",
        root=str(root),
        work=str(work),
        worker=ref(work / "scripts/train_spectral_trial.py"),
        arms=arms,
        root_disk_reserve_gib=64,
        resource_recovery_of=ref(previous_path),
        previous_failure=ref(status_path),
        discarded_observations=ref(root / "discarded-post1000-observations.json"),
        discarded_metrics=ref(root / "discarded-post1000-metrics.jsonl"),
        unchanged_worker_retention_recipe_AST=True,
        resource_guard_addendum=ref(REPO / "docs/spectral-root-reserve-addendum.md"),
        arm_timeout_seconds={
            **previous["arm_timeout_seconds"],
            "control": previous["arm_timeout_seconds"]["control"] - consumed,
        },
        scope="Explicit operational root reserve64GiB; unchanged worker/retainer/recipe AST and all46 model modules. Original1000 state resumes original4000 horizon; only remaining3000 retained-trajectory updates. Failed-worker active time deducted, unsaved work may repeat. All quality gates and other resource reserves preserved; no automatic retry or promotion.",
    )
    plan["inputs"] += [
        ref(previous_path),
        ref(status_path),
        plan["discarded_observations"],
        plan["discarded_metrics"],
        plan["resource_guard_addendum"],
        ref(tests_path),
        ref(REPO / "tests/test_spectral_resources.py"),
        ref(__file__),
    ]
    unique = {}
    for item in plan["inputs"]:
        if item["path"] in unique:
            assert unique[item["path"]] == item["sha256"]
        unique[item["path"]] = item["sha256"]
    plan["inputs"] = [{"path": p, "sha256": s} for p, s in sorted(unique.items())]
    plan["frozen_files"] = {
        str(p): ref(p)["sha256"]
        for p in work.rglob("*")
        if p.is_file() and p.relative_to(work).parts[0] != "runs"
    }
    core = {p.name: ref(p)["sha256"] for p in (oldwork / "src/demosaic").glob("*.py")}
    assert len(core) == 46
    assert all(ref(work / "src/demosaic" / p)["sha256"] == sha for p, sha in core.items())
    guard(plan)
    save(root / "plan.json", plan)
    print(
        {
            "plan": ref(root / "plan.json"),
            "root_reserve_GiB": 64,
            "remaining_control_timeout": plan["arm_timeout_seconds"]["control"],
            "discarded_observed_steps": [r["step"] for r in discarded],
            "frozen_files": len(plan["frozen_files"]),
            "inputs": len(plan["inputs"]),
        }
    )


def read_line(line):
    import json

    return json.loads(line)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--previous", type=Path, required=True)
    p.add_argument("--tests", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    prepare(a.previous.resolve(), a.tests.resolve(), a.output)
