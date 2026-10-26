"""Freeze a new native-camera comparison behind the original V119 job chain."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
from evaluate_native_camera_development import binding, checked, guard, local_time, read, write

REPO = Path(__file__).absolute().parents[1]
BASE = REPO / ".cache/current-quality-20261023-v1"
RAWNIND_WRAPPER_SHA = "3304b0c69ea2cb84b400597aa501bb6f2ed26ab0809e26068e10bc597605afc3"
REFERENCE_SHA = "3d8d5fab966f790f4adbaf1786ca1ee81cb027d9cd45220787247b0af99fd814"


def live(owner):
    try:
        process = psutil.Process(owner["pid"])
        return process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def immutable(item):
    path = checked(item)
    assert path.is_file() and not path.is_symlink() and not path.stat().st_mode & 0o222
    return path


def joint_method(invariant, label):
    record = invariant["checkpoint"]
    assert record["arm"] == label and record["expected_lineage"]["step"] == 20000
    checkpoint = {key: record[key] for key in ("path", "sha256")}
    immutable(checkpoint)
    return {"label": label, "kind": "joint", "checkpoint": checkpoint,
            "expected_lineage": record["expected_lineage"], "expected_backbone": record["expected_backbone"],
            "expected_full_model_sha256": invariant["before"]}


def dependency(root, owner_key, plan_key, plan_name, terminal):
    state = read(root / "status.json")
    plan = binding(root / plan_name)
    assert state[plan_key] == plan and live(state[owner_key]) and not state["status"].startswith("failed")
    return {"status_path": str(root / "status.json"), "owner_key": owner_key, "owner": state[owner_key],
            "plan_key": plan_key, "plan": plan, "terminal": terminal}


def prepare(root):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and "torch" not in sys.modules
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    os.nice(10)
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    assert psutil.virtual_memory().available >= 48 * 2**30
    assert shutil.disk_usage(root.parent).free >= 128 * 2**30
    assert shutil.disk_usage("/mnt/external").free >= 208 * 2**30
    training_root = BASE / "V115-cleaned-diverse-training-v1/run"
    training_ref = binding(training_root / "plan.json")
    training = read(training_ref["path"])
    dependencies = [
        dependency(training_root, "controller", "plan", "plan.json", "completed-training-awaiting-model-comparisons"),
        dependency(BASE / "V119-cleaned-diverse-quality-v1", "owner", "queue_plan", "queue-plan-v1.json",
                   "completed-matched-endpoint-evaluation-awaiting-independent-and-native-review"),
        dependency(BASE / "V119-cleaned-diverse-independent-audit-v1", "owner", "plan", "queue-plan-v1.json",
                   "completed-independent-primary-and-analytic-audit-native-viewing-pending"),
        dependency(BASE / "V119-cleaned-diverse-matched-review-v1", "owner", "plan", "queue-plan-v1.json",
                   "completed-V119-contrasts-and-local-detail-native-viewing-pending"),
    ]
    data_root = BASE / "native-camera-development-inputs-v1"
    dataset_ref = binding(data_root / "manifest.json")
    dataset = read(dataset_ref["path"])
    assert dataset["split"] == "development" and len(dataset["rows"]) == 20 and len(dataset["observations"]) == 240
    inputs = [dataset_ref, binding(data_root / "result-v1.json"), binding(data_root / "actual-input-readback-v1.json"),
              binding(REPO / "configs/native-camera-development-v1.json"), training_ref,
              binding(training_root / "execution-plan-v1.json"), *[d["plan"] for d in dependencies],
              binding(BASE / "native-camera-development-metric-proof-v1.json")]
    metric_proof = read(BASE / "native-camera-development-metric-proof-v1.json")
    assert metric_proof["new_neural_forwards"] == 0 and not metric_proof["Torch_imported"]
    assert metric_proof["driver"] == binding(REPO / "scripts/evaluate_native_camera_development.py")
    inputs += [r["reference_camera_FP32"] for r in dataset["rows"]]
    inputs += [r["arrays"] for r in dataset["observations"]]
    methods = []
    for label, path in [
        ("V114", Path("/mnt/external/demosaic/V112-continuations-quality-20261024-v3/photo/result.json")),
        ("V115", Path("/mnt/external/demosaic/V112-continuations-quality-20261024-v3/photo/result.json")),
        ("V117", BASE / "V117-V118-band-quality-v1/work/artifacts/photo/result.json"),
    ]:
        item = binding(path)
        result = read(path)
        invariant = next(v for v in result["invariants"] if v["checkpoint"]["arm"] == label)
        method = joint_method(invariant, label)
        methods.append(method)
        inputs += [item, method["checkpoint"]]
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    sources = list((Path(training["work"]) / "src/demosaic").glob("*.py"))
    for source in sources:
        destination = work / "src/demosaic" / source.name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        inputs.append(binding(source))
    for name in ["queue_native_camera_development.py", "evaluate_native_camera_development.py",
                 "profile_raw_kernel_inference.py", "frozen_backbone_identity.py", "diagnose_local_material_detail.py"]:
        destination = work / "scripts" / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "scripts" / name, destination)
    for name in ["pyproject.toml", "uv.lock", "third_party/dinov3/LICENSE.md"]:
        destination = work / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, destination)
    reference = Path("/mnt/external/demosaic/references/rawnind-preupsample-20261023-v1")
    reference_dir = work / "reference"
    reference_dir.mkdir()
    for name in ["utnet2-bayer.pt", "raw_denoiser.py", "LICENSE", "provenance.json"]:
        source, destination = reference / name, reference_dir / name
        inputs.append(binding(source))
        shutil.copyfile(source, destination)
        destination.chmod(0o444)
    # The frozen safety module treats work as its repository. Resolve the
    # archive into that workspace while retaining the controller's public path.
    (work / "artifacts").mkdir()
    (root / "archive").symlink_to(Path("work/artifacts/archive"), target_is_directory=True)
    checkpoint = binding(reference_dir / "utnet2-bayer.pt")
    assert checkpoint["sha256"] == REFERENCE_SHA
    methods.append({"label": "RawNIND-preup", "kind": "rawnind-preup", "checkpoint": checkpoint,
                    "directory": str(reference_dir), "expected_wrapper_sha256": RAWNIND_WRAPPER_SHA,
                    "gain_mode": "cfa-channel", "input_scale": None, "clip_input": False})
    inputs.append(checkpoint)
    frozen = {str(p): binding(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    for path in frozen:
        Path(path).chmod(0o444)
    plan = {"recorded_local": local_time(), "root": str(root), "work": str(work), "python": sys.executable,
            "dependencies": dependencies, "training_plan": training_ref,
            "training_execution": binding(training_root / "execution-plan-v1.json"),
            "training_source_sha256": "7edfbceae2e6363cd07e868720a3ea2ef7b386ffee7c2d6ad4b434bd629d429e",
            "dataset_manifest": dataset_ref, "methods_except_pending_V119": methods,
            "collector_source": binding(work / "scripts/evaluate_native_camera_development.py"),
            "controller_source": binding(work / "scripts/queue_native_camera_development.py"),
            "maximum_dependency_wait_seconds": 345600, "maximum_headroom_wait_seconds": 43200,
            "maximum_collection_seconds": 7200, "maximum_analysis_seconds": 3600,
            "phase_start_RAM_GiB": 48, "runtime_RAM_GiB": 24,
            "phase_start_internal_free_GiB": 128, "runtime_internal_reserve_GiB": 96,
            "external_free_reserve_GiB": 208, "CUDA_quota_GiB": 24,
            "planned_neural_root_calls": 1200, "planned_frozen_DINO_encoder_calls": 960,
            "planned_RawNIND_network_calls": 240, "new_noise_observations": 0, "optimizer_updates": 0, "RAW_decodes": 0,
            "inputs": list({item["path"]: item for item in inputs}.values()), "frozen_files": frozen,
            "scope": "New inputs only: V114/V115/V117/final V119/RawNIND preupsample on 240 previously unevaluated stored observations from 20 contexts/11 captures. Wait for the original complete training, eight-stage evaluation, independent audit and saved-output contrasts to release their exact owners. Resolve only the completed final V119 immutable checkpoint. Source-balanced NumPy64 metrics, reference-only local bands, 10 native triplets and 12 full comparison boards. Low-noise source estimates are not exact GT. No retraining, fresh noise, RAW decode, old-input control reruns, automatic retry or promotion; actual viewing and interpretation follow."}
    path = root / "queue-plan-v1.json"
    write(path, plan)
    guard(plan)
    return path


def observed_dependency(item, *, terminal=False):
    state = read(item["status_path"])
    assert state[item["owner_key"]] == item["owner"] and state[item["plan_key"]] == item["plan"]
    assert not state["status"].startswith("failed"), state["status"]
    if terminal:
        assert not live(item["owner"]) and state["status"] == item["terminal"]
        assert not state.get("child") or not live(state["child"])
    return state


def receipt_bindings(value):
    """Matched contrasts nest their two receipts under each control label."""
    if isinstance(value, dict):
        if set(value) == {"path", "sha256"}:
            yield value
        else:
            for child in value.values():
                yield from receipt_bindings(child)
    elif isinstance(value, list):
        for child in value:
            yield from receipt_bindings(child)


def execution_plan(plan, queue_path):
    states = [observed_dependency(d, terminal=True) for d in plan["dependencies"]]
    inputs = list(plan["inputs"]) + [binding(d["status_path"]) for d in plan["dependencies"]]
    training_root = Path(plan["training_plan"]["path"]).parent
    accounting = binding(training_root / "train-V119-accounting-v1.json")
    actual = read(accounting["path"])
    assert actual["worker_result"] == states[0]["completed"]["train-V119"]
    checked(actual["worker_result"])
    assert not live(actual["owner"]) and actual["execution_plan"] == plan["training_execution"]
    assert actual["all_AdamW_steps"] == 20000 and actual["fresh_AdamW_states"] == 89
    assert actual["counts"]["training_forwards"] == actual["counts"]["optimizer_steps"] == 20000
    assert actual["model_EMA_Adam_finite"] and actual["frozen_encoder_no_gradients"]
    assert actual["initial_all91_EMA_exact_to_explicit_parent"] and actual["source_sha256"] == plan["training_source_sha256"]
    quality = read(plan["dependencies"][1]["plan"]["path"])
    assert set(states[1]["completed"]) == set(quality["stages"])
    for state in states[1:]:
        for item in receipt_bindings({"completed": state.get("completed", {}), "result": state.get("result")}):
            checked(item)
            inputs.append(item)
    photo = read(states[1]["completed"]["photo"]["path"])
    assert len(photo["invariants"]) == 1
    method = joint_method(photo["invariants"][0], "V119")
    assert method["checkpoint"]["sha256"] == actual["checkpoint"]["sha256"]
    assert method["expected_backbone"] == read(plan["training_plan"]["path"])["parent_backbone"]
    methods = plan["methods_except_pending_V119"]
    assert [m["label"] for m in methods] == ["V114", "V115", "V117", "RawNIND-preup"]
    result = {**plan, "queue_plan": binding(queue_path), "methods": [*methods[:3], method, methods[3]],
              "inputs": [*inputs, accounting, actual["worker_result"], method["checkpoint"]]}
    path = Path(plan["root"]) / "execution-plan-v1.json"
    write(path, result)
    guard(result)
    return path


def controller(path):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and "torch" not in sys.modules
    plan = read(path)
    guard(plan)
    assert binding(__file__) == plan["controller_source"]
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    os.nice(10)
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {"owner": {"pid": os.getpid(), "created": process.create_time()}, "queue_plan": binding(path), "completed": {}}
    child = child_owner = None

    def record(status, **fields):
        state.update(status=status, recorded_local=local_time(), updated_unix=time.time(), **fields)
        temporary = root / "status.tmp"
        temporary.write_text(json.dumps(state, indent=2)+"\n")
        temporary.replace(root / "status.json")

    def headroom(start=False):
        return (psutil.virtual_memory().available >= plan["phase_start_RAM_GiB" if start else "runtime_RAM_GiB"]*2**30
                and shutil.disk_usage(root).free >= plan["phase_start_internal_free_GiB" if start else "runtime_internal_reserve_GiB"]*2**30
                and shutil.disk_usage("/mnt/external").free >= plan["external_free_reserve_GiB"]*2**30)

    try:
        began = time.monotonic()
        for index, item in enumerate(plan["dependencies"]):
            record("waiting-for-original-V119-job-chain", dependency_index=index, dependency=item["owner"], child=None)
            while live(item["owner"]):
                for observed in plan["dependencies"]:
                    observed_dependency(observed)
                assert time.monotonic()-began < plan["maximum_dependency_wait_seconds"]
                time.sleep(10)
            observed_dependency(item, terminal=True)
        guard(plan)
        execution = execution_plan(plan, path)
        for mode, timeout in [("collect", plan["maximum_collection_seconds"]), ("analyze", plan["maximum_analysis_seconds"])]:
            record("waiting-for-native-comparison-headroom", phase=mode, child=None)
            began, stable = time.monotonic(), None
            while True:
                enough = headroom(start=True)
                stable = (time.monotonic() if stable is None else stable) if enough else None
                if stable is not None and time.monotonic()-stable >= 15:
                    break
                assert time.monotonic()-began < plan["maximum_headroom_wait_seconds"]
                time.sleep(2)
            guard(read(execution))
            env = dict(os.environ, PYTHONPATH=f"{work/'src'}:{work/'scripts'}", CUDA_VISIBLE_DEVICES="0" if mode=="collect" else "",
                       HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", OPENBLAS_NUM_THREADS="1", OMP_NUM_THREADS="4" if mode=="collect" else "1")
            with (root / f"{mode}-v1.log").open("x") as log:
                child = subprocess.Popen([plan["python"], "-P", plan["collector_source"]["path"], mode, str(execution)],
                                         cwd=work, env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("running-new-native-comparison-phase", phase=mode, child=child_owner)
                began = time.monotonic()
                while child.poll() is None:
                    assert time.monotonic()-began < timeout and headroom()
                    time.sleep(2)
                assert child.wait() == 0, (mode, child.returncode)
            result_path = root / ("collection-result-v1.json" if mode=="collect" else "analysis-result-v1.json")
            result = read(result_path)
            assert result["owner"] == child_owner and not live(child_owner)
            assert result["execution_plan"] == binding(execution)
            state["completed"][mode] = binding(result_path)
            record("completed-native-comparison-phase", child=None)
        assert "torch" not in sys.modules
        guard(plan)
        write(root / "result-v1.json", {"recorded_local": local_time(), "owner": state["owner"],
              "queue_plan": binding(path), "execution_plan": binding(execution), "phases": state["completed"],
              "controller_Torch_imported": False, "scope": "New native development predictions and CPU scores/images complete. Actual native viewing, interpretation and documentation remain pending; no automatic promotion."})
        record("completed-native-camera-development-native-viewing-pending", result=binding(root / "result-v1.json"), child=None)
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(child_owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-native-camera-development-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    result = {"prepare": prepare, "controller": controller}[args.mode](args.path)
    if result is not None:
        print(result, flush=True)
