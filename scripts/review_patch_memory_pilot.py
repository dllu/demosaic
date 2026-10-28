"""Freeze and queue V140's matched native review after its original1000-update training."""

import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
METHODS = [
    "V120",
    "V129 1k EMA",
    "V136 1k EMA",
    "V137 1k EMA",
    "V138 1k EMA",
    "V139 1k EMA",
    "V140 1k EMA",
]


def prepare(root):
    base = REPO / ".cache/current-quality-20261023-v1"
    previous = base / "raw-global-memory-only-quality-v1"
    train = base / "raw-patch-memory-training-v1/run"
    old = read(previous / "queue-plan-v1.json")
    training = read(train / "plan.json")
    guard(old)
    guard(training)
    support_path = train / "native-review-support-v1.json"
    support = read(support_path)
    assert support["observations"] == old["observations"]
    training_owner = read(train / "launch-v1.json")["owner"]
    assert live(training_owner) and read(train / "status.json")["controller"] == training_owner
    previous_owner = read(previous / "status.json")["owner"]
    assert previous_owner == training["quality_dependency"]["owner"] and live(previous_owner)
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    shutil.copytree(
        Path(training["work"]) / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__")
    )
    shutil.copytree(
        Path(old["work"]) / "scripts",
        work / "scripts",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    for name in ("train_patch_memory_pilot.py",):
        shutil.copyfile(Path(training["work"]) / "scripts" / name, work / "scripts" / name)
    controller = root / "controller-v1.py"
    binder = root / "bind-endpoint-v1.py"
    shutil.copyfile(__file__, controller)
    shutil.copyfile(REPO / "scripts/bind_patch_memory_review.py", binder)
    for name in ("analyze_retained_faint_detail.py", "audit_retained_faint_detail.py"):
        shutil.copyfile(Path(old["work"]) / "scripts" / name, work / "scripts" / name)
    (work / "configs").mkdir()
    shutil.copyfile(
        REPO / "configs/gfx-green-mesh-20231231.json", work / "configs/gfx-green-mesh-20231231.json"
    )
    assert len(list((work / "src/demosaic").glob("*.py"))) == 69
    # Only the two model labels change in the already checked scalar-LUT renderer.
    camera_source = Path(old["camera_operator"]["path"]).read_text()
    assert ref(old["camera_operator"]["path"]) == old["camera_operator"]
    camera_source = camera_source.replace("V139", "V140").replace("V138", "V139")
    camera = root / "render-mesh-JPEG-v1.py"
    camera.write_text(camera_source)
    old_faint = read(old["faint_template"]["path"])
    faint = {
        **old_faint,
        "root": str(root),
        "quality_root": str(root),
        "quality_owner": None,
        "output": str(root / "faint-detail-v1"),
        "methods": METHODS,
        "operator": ref(work / "scripts/analyze_retained_faint_detail.py"),
        "auditor": ref(work / "scripts/audit_retained_faint_detail.py"),
        "PYTHONPATH": f"{work / 'src'}:{work / 'scripts'}",
        "inputs": [ref(train / "plan.json"), ref(work / "configs/gfx-green-mesh-20231231.json")],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Same16 saved faint ADC observations, four contexts/fourCFAs and seven methods. "
        "Original-source DCT masks and camera/sRGB DC-spatial errors, shared40x native160 display. "
        "420strata/224decompositions/four9-cell boards/2764800RGBchannels. No new neural/noise/RAW/"
        "optimizer calls, output-based selection or resizing; references remain approximate.",
    }
    template = root / "faint-analysis-template-v1.json"
    save(template, faint)
    queue = {
        **old,
        "root": str(root),
        "work": str(work),
        "training_plan": ref(train / "plan.json"),
        "training_owner": training_owner,
        "controller": ref(controller),
        "endpoint_binder": ref(binder),
        "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
        "reporter": ref(work / "scripts/report_checkpoint_pilot.py"),
        "auditor": ref(work / "scripts/audit_checkpoint_pilot.py"),
        "baseline_quality": ref(previous / "queue-plan-v1.json"),
        "baseline_quality_owner": previous_owner,
        "faint_template": ref(template),
        "faint_operator": faint["operator"],
        "faint_auditor": faint["auditor"],
        "camera_operator": ref(camera),
        "absolute_deadline_unix": old["absolute_deadline_unix"] + 86400,
        "launch_RAM_GiB": 50,
        "expected_metrics": 672,
        "expected_summaries": 168,
        "expected_primary_PNGs": 64,
        "expected_primary_RGB_channels": 29491200,
        "reused_control_predictions": 612,
        "inputs": [
            *old["inputs"],
            ref(train / "plan.json"),
            ref(train / "launch-v1.json"),
            ref(support_path),
            ref(previous / "queue-plan-v1.json"),
            ref(work / "configs/gfx-green-mesh-20231231.json"),
            ref(template),
        ],
        "scope": "OriginalV1401000 endpoint only:patch-memory-v4/107EMA16Adam/91 frozen parent/69trainedmodules. "
        "102 new IEEE FP32 root/DINO calls on64shadow/16ordinary/16faintADC/4mainGFX512/2mesh768. "
        "Adopt612 saved V120/V129/V136/V137/V138/V139 predictions; exact102 fixed observations and existing "
        "four-control prefix, inheritedV138 controls plus actualV139 predictions. Require all1000 clean/noisy "
        "hashes equal actualV139 and savedV137, actualstate/source checks, originalV139 finalreview and ownerexit. "
        "No control replay, new noise/RAW/optimizer work, tuning, retries or horizon/deadline resets. "
        "672metrics/168groups/64PNGs/29491200channels, seven-method faint and four cameraJPEG boards. "
        "Same masks/ROIs/display, native exactGT triplets and both corrected protectedGFX pairs. Real references "
        "notGT. Actual viewing/publication still required. New50GiB CUDA/40GiB CPU admission,12GiB CUDAcap/"
        "32GiB runtime reserve,2h headroom waits,1h collection/30minCPUstages; new deadline originalV139quality"
        "deadline+24h. Original queues unchanged. Not full427/camera/color/fullframe/speed or broad superiority.",
    }
    queue["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
    for p in (controller, binder, camera, template):
        queue["frozen_files"][str(p)] = ref(p)["sha256"]
    assert len(queue["observations"]) == 102
    assert sum(len(o["controls"]) for o in queue["observations"]) == 408
    save(root / "queue-plan-v1.json", queue)
    guard(queue)
    assert "torch" not in sys.modules
    return root / "queue-plan-v1.json"


def controller(path):
    queue = read(path)
    guard(queue)
    assert ref(__file__) == queue["controller"] and "torch" not in sys.modules
    root = Path(queue["root"])
    (root / "controller.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    state = {"owner": owner, "plan": ref(path), "completed": {}}
    child = child_owner = None

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        save(root / "status.json", state)

    def resources(cuda):
        deadline, stable = time.time() + 7200, None
        while True:
            assert time.time() < min(deadline, queue["absolute_deadline_unix"])
            enough = (
                psutil.virtual_memory().available
                >= (queue["launch_RAM_GiB"] if cuda else 40) * 2**30
                and shutil.disk_usage(root).free >= 128 * 2**30
                and shutil.disk_usage("/mnt/external").free >= 208 * 2**30
            )
            stable = (time.monotonic() if stable is None else stable) if enough else None
            if stable is not None and time.monotonic() - stable >= 15:
                return
            time.sleep(2)

    def run(stage, script, args, cuda, timeout, keep_primary_status=False):
        nonlocal child, child_owner
        guard(queue)
        resources(cuda)
        work = Path(queue["work"])
        env = dict(
            os.environ,
            PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
            CUDA_VISIBLE_DEVICES="0" if cuda else "",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
            OPENBLAS_NUM_THREADS="1",
            OMP_NUM_THREADS="2",
            PYTHONDONTWRITEBYTECODE="1",
            CUBLAS_WORKSPACE_CONFIG=":4096:8",
        )
        intermediate = "completed-global1000-review-awaiting-actual-native-viewing"
        with (root / (stage + "-v1.log")).open("x") as log:
            child = subprocess.Popen(
                [queue["python"], "-B", "-P", str(script), *map(str, args)],
                cwd=work,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record(
                intermediate if keep_primary_status else "running-patch-memory-" + stage,
                child=child_owner,
                stage=stage,
            )
            began = time.monotonic()
            while child.poll() is None:
                assert (
                    time.monotonic() - began < timeout
                    and time.time() < queue["absolute_deadline_unix"]
                )
                time.sleep(2)
            assert child.wait() == 0, (stage, child.returncode)
        state["completed"][stage] = True
        record(
            intermediate if keep_primary_status else "completed-patch-memory-" + stage, child=None
        )

    try:
        policy = read(queue["faint_template"]["path"])
        policy["quality_owner"] = owner
        policy["inputs"].append(ref(path))
        assert not (root / "faint-analysis-plan-v1.json").exists()
        save(root / "faint-analysis-plan-v1.json", policy)
        record("waiting-for-original-V140-training", child=None)
        training = read(queue["training_plan"]["path"])
        while True:
            assert time.time() < queue["absolute_deadline_unix"]
            status = read(Path(training["root"]) / "status.json")
            assert (
                status["plan"] == queue["training_plan"]
                and status["controller"] == queue["training_owner"]
            )
            assert not status["status"].startswith("failed"), status
            if not live(queue["training_owner"]):
                assert status["status"] == "completed-training-awaiting-model-comparisons"
                assert status.get("child") is None or not live(status["child"])
                break
            time.sleep(10)
        run("bind-endpoint", queue["endpoint_binder"]["path"], [path], False, 1800)
        evaluation = root / "plan-v1.json"
        assert read(evaluation)["planned_new_root_forwards"] == 102
        run("collect", queue["collector"]["path"], [evaluation], True, 3600)
        run(
            "report",
            queue["reporter"]["path"],
            [evaluation, root / "collection-v1.json"],
            False,
            1800,
        )
        run("audit", queue["auditor"]["path"], [root], False, 1800)
        primary = read(root / "independent-audit-v1.json")
        assert primary["status"].startswith("passed")
        for key, expected in (
            ("metric_rows", 672),
            ("summary_groups", 168),
            ("PNG_images", 64),
            ("PNG_channels_exact", 29491200),
        ):
            assert primary[key] == expected
        record("completed-global1000-review-awaiting-actual-native-viewing", child=None)
        analysis = root / "faint-analysis-plan-v1.json"
        run("faint-analyze", queue["faint_operator"]["path"], [analysis], False, 1800, True)
        run("faint-audit", queue["faint_auditor"]["path"], [analysis], False, 1800, True)
        faint = read(root / "faint-detail-v1/independent-audit-v1.json")
        assert faint["status"].startswith("passed")
        assert faint["stratum_rows"] == 420 and faint["decomposition_rows"] == 224
        assert faint["PNG_images"] == 4 and faint["PNG_channels_exact"] == 2764800
        run("camera-JPEG", queue["camera_operator"]["path"], [], False, 1800, True)
        cameras = read(root / "camera-JPEG-v1/manifest-v1.json")
        assert len(cameras["images"]) == 4 and cameras["native_RGB_channels_exact"] == 2150400
        guard(queue)
        record(
            "completed-patch-memory1000-review-awaiting-actual-native-viewing",
            child=None,
            primary_report=ref(root / "report-v1/report.json"),
            primary_audit=ref(root / "independent-audit-v1.json"),
            faint_result=ref(root / "faint-detail-v1/result-v1.json"),
            faint_audit=ref(root / "faint-detail-v1/independent-audit-v1.json"),
            camera_JPEGs=ref(root / "camera-JPEG-v1/manifest-v1.json"),
        )
    except BaseException as error:
        if child is not None and child.poll() is None and live(child_owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(child_owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record(
            "failed-patch-memory-review-preserved-no-automatic-retry", child=None, error=repr(error)
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path.resolve()))
    else:
        controller(args.path.resolve())
