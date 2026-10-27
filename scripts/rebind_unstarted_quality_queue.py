"""Rebind failed, unstarted dependents to an explicitly recovered producer."""

import argparse
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
WAIT_FIELDS = (
    "maximum_training_wait_seconds",
    "maximum_wait_seconds",
    "maximum_dependency_wait_seconds",
)


def replace_dependencies(value, replacements, own_root, new_root):
    """Replace exact receipt/owner identities and directory prefixes, never arbitrary text."""
    if isinstance(value, dict):
        for item in replacements:
            if value == item["old_plan"]:
                return item["new_plan"]
            if value == item["old_owner"]:
                return item["new_owner"]
        return {
            replace_dependencies(k, replacements, own_root, new_root): replace_dependencies(
                v, replacements, own_root, new_root
            )
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [replace_dependencies(v, replacements, own_root, new_root) for v in value]
    if isinstance(value, str):
        for old, new in [
            (own_root, new_root),
            *[(r["old_root"], r["new_root"]) for r in replacements],
        ]:
            if value == old or value.startswith(old + "/"):
                return new + value[len(old) :]
    return value


def rebind(original_path, root, replacements):
    original_path, root = original_path.resolve(), root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    original = read(original_path)
    guard(original)
    old_root = Path(original["root"])
    status_path = old_root / "status.json"
    state = read(status_path)
    owner = state.get("owner", state.get("controller"))
    assert state["status"].startswith("failed") and not live(owner)
    assert state.get("child") is None
    claims = sorted(p.name for p in old_root.glob("*.claim"))
    assert claims == ["controller.claim"], claims
    assert not (old_root / "evaluation-plan-v1.json").exists()
    assert not (old_root / "execution-plan-v1.json").exists()
    completed = state.get("completed", {})
    if "arm_weights" in original:
        assert set(completed) == {"CPU-V124", "CPU-V125", "CUDA-V124", "CUDA-V125"}
        worker_root = Path(original["output_worker_root"])
        assert not any((worker_root / f"train-{arm}.claim").exists() for arm in original["arms"])
        for binding in completed.values():
            assert ref(binding["path"]) == binding and not live(read(binding["path"])["owner"])
    else:
        assert not completed, "A queue with computed stages needs explicit stage adoption"
    for item in replacements:
        assert ref(item["old_plan"]["path"]) == item["old_plan"]
        assert ref(item["new_plan"]["path"]) == item["new_plan"]
        observed = read(Path(item["new_root"]) / "status.json")
        assert observed.get("owner", observed.get("controller")) == item["new_owner"]
        assert observed.get("queue_plan", observed.get("plan")) == item["new_plan"]
        assert live(item["new_owner"]) and not observed["status"].startswith("failed")
    root.mkdir(parents=True, exist_ok=False)
    helper = root / "rebind-helper.py"
    shutil.copyfile(__file__, helper)
    copied_files = dict(original["frozen_files"])
    copied_files.update({item["path"]: item["sha256"] for item in original["inputs"]})
    for path, digest in copied_files.items():
        source = Path(path)
        if source.is_relative_to(old_root):
            target = root / source.relative_to(old_root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            assert ref(target)["sha256"] == digest
    plan = replace_dependencies(original, replacements, str(old_root), str(root))
    elapsed = time.time() - owner["created"]
    deadlines = {}
    for field in WAIT_FIELDS:
        if field in original:
            deadlines[field] = owner["created"] + original[field]
            plan[field] = deadlines[field] - time.time()
            assert plan[field] > 0, "Original dependency observation deadline has expired"
    if "arm_weights" in original:
        plan["adopted_phase_results"] = completed
        plan["replaced_controller"] = owner
    declaration = {
        "rebind_source": ref(helper),
        "original_plan": ref(original_path),
        "original_status": ref(status_path),
        "original_owner": owner,
        "original_root_claims": claims,
        "original_completed_phases_adopted": completed,
        "unstarted_production_or_inference_verified": True,
        "elapsed_since_original_owner_seconds": elapsed,
        "original_absolute_wait_deadlines": deadlines,
        "replacements": replacements,
        "created_unix": time.time(),
        "scope": "Explicit dependency repair after producer memory-guard failure. Frozen source bytes, all actual inputs, parent/configuration/step budgets and worker limits retained. No neural work repeated. Original failed receipts and observations remain unchanged; original dependency deadlines are not reset.",
    }
    save(root / "rebind-declaration-v1.json", declaration)
    plan["inputs"] += [
        ref(original_path),
        ref(status_path),
        ref(root / "rebind-declaration-v1.json"),
    ]
    plan["rebind_declaration"] = ref(root / "rebind-declaration-v1.json")
    plan["frozen_files"][str(helper)] = ref(helper)["sha256"]
    path = root / original_path.name
    save(path, plan)
    guard(plan)
    source = plan.get("controller_source", plan.get("controller_script", plan.get("worker_script")))
    assert source is not None
    work = Path(plan["work"])
    env = dict(
        os.environ,
        PYTHONPATH=f"{work}/src:{work}/scripts",
        CUDA_VISIBLE_DEVICES="",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
    )
    with (root / "controller.log").open("x") as log:
        child = subprocess.Popen(
            [plan["python"], "-P", source["path"], "controller", str(path)],
            cwd=work,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        new_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
    deadline = time.monotonic() + 30
    while not (root / "status.json").exists():
        assert child.poll() is None, (
            child.returncode,
            (root / "controller.log").read_text()[-2000:],
        )
        assert time.monotonic() < deadline
        time.sleep(0.05)
    observed = read(root / "status.json")
    assert observed.get("owner", observed.get("controller")) == new_owner
    assert not observed["status"].startswith("failed"), observed["status"]
    result = {
        "old_root": str(old_root),
        "new_root": str(root),
        "old_plan": ref(original_path),
        "new_plan": ref(path),
        "old_owner": owner,
        "new_owner": new_owner,
    }
    save(root / "launch-v1.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("root", type=Path)
    parser.add_argument("replacements", type=Path)
    args = parser.parse_args()
    print(rebind(args.original, args.root, read(args.replacements)))
