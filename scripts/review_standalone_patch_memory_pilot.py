"""Bind and review standalone V140 on the 102 previously retained inputs."""

import argparse
import os
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

from bind_patch_memory_review import matching_batches, require_training_result
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / ".cache/current-quality-20261023-v1"
METHODS = ["V120", "V129 1k EMA", "V136 1k EMA", "V137 1k EMA", "V140 1k EMA"]


def prepare(root, training_path):
    training = read(training_path)
    guard(training)
    previous = BASE / "raw-global-conditioned-quality-v1"
    old = read(previous / "plan-v1.json")
    guard(old)
    collection = read(previous / "collection-v1.json")
    assert collection["plan"] == ref(previous / "plan-v1.json")
    assert collection["counts"] == {"root": 102, "encoder": 102}
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for directory in ("src", "scripts"):
        shutil.copytree(
            Path(training["work"]) / directory,
            work / directory,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    shutil.copytree(
        BASE / "raw-patch-memory-quality-v1/work/scripts",
        work / "scripts",
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (work / "configs").mkdir()
    shutil.copyfile(
        REPO / "configs/gfx-green-mesh-20231231.json", work / "configs/gfx-green-mesh-20231231.json"
    )
    observations = deepcopy(old["observations"])
    assert [o["id"] for o in observations] == [r["id"] for r in collection["observations"]]
    for observation, row in zip(observations, collection["observations"], strict=True):
        assert ref(row["prediction"]["path"]) == row["prediction"]
        observation["controls"].append(
            {
                "model": {
                    "label": "V137 1k EMA",
                    "step": 1000,
                    "sha256": old["checkpoint"]["sha256"],
                },
                "prediction": row["prediction"],
            }
        )
    camera_source = (BASE / "raw-patch-memory-quality-v1/render-mesh-JPEG-v1.py").read_text()
    camera = root / "render-mesh-JPEG-v1.py"
    camera.write_text(camera_source.replace("V139", "V137"))
    scope = (
        "Standalone V140 complete1k pilot, four saved controls and102 fixed inputs: "
        "64 shadow/16 ordinary/16 faintADC/four mainGFX512/two mesh768 profiles. "
        "All ROIs/noise/display/source masks fixed;408 control predictions reused. "
        "Matched actualV137 training batches, but scope/LR/operator differ, so this "
        "is not an isolated descriptor ablation. Exact syntheticGT and approximate "
        "binned/separateISO100 references retain accurate roles. Native160 no-resize "
        "triplets, faint40x displays, both corrected GFX pairs and both cameraJPEGs. "
        "No new noise/RAW/reference-model calls. Not full427/camera/color/fullframe quality."
    )
    queue = {
        **old,
        "root": str(root),
        "work": str(work),
        "training_plan": ref(training_path),
        "observations": observations,
        "model_label": METHODS[-1],
        "EMA_tensors": 107,
        "raw_global_conditioning": "patch-memory-v4",
        "scope": scope,
        "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
        "reporter": ref(work / "scripts/report_checkpoint_pilot.py"),
        "auditor": ref(work / "scripts/audit_checkpoint_pilot.py"),
        "inputs": [
            ref(training_path),
            ref(previous / "plan-v1.json"),
            ref(previous / "collection-v1.json"),
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
    }
    del queue["checkpoint"]
    queue["frozen_files"][str(camera)] = ref(camera)["sha256"]
    save(root / "queue-plan-v1.json", queue)
    faint = read(BASE / "raw-global-conditioned-faint-detail-v1/analysis-plan-v1.json")
    faint.update(
        root=str(root),
        quality_root=str(root),
        quality_owner=None,
        output=str(root / "faint-detail-v1"),
        methods=METHODS,
        operator=ref(work / "scripts/analyze_retained_faint_detail.py"),
        auditor=ref(work / "scripts/audit_retained_faint_detail.py"),
        PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
        inputs=[ref(root / "queue-plan-v1.json")],
        frozen_files=queue["frozen_files"],
        scope=scope
        + " Same original-source faint strata and DC/spatial decomposition;40x is display only.",
    )
    save(root / "faint-analysis-plan-v1.json", faint)
    guard(queue)
    guard(faint)
    return root / "queue-plan-v1.json"


def bind(root):
    queue = read(root / "queue-plan-v1.json")
    guard(queue)
    training = read(queue["training_plan"]["path"])
    status = read(Path(training["root"]) / "standalone-status.json")
    assert status["status"] == "completed-standalone-V140-awaiting-quality-review"
    assert status["plan"] == queue["training_plan"] and not live(status["owner"])
    assert ref(status["result"]["path"]) == status["result"]
    actual = read(status["result"]["path"])
    require_training_result(actual)
    assert not live(actual["owner"])
    assert ref(actual["matched_control_result"]["path"]) == actual["matched_control_result"]
    matching_batches(actual, read(actual["matched_control_result"]["path"]))
    import torch

    torch.set_num_threads(2)
    checkpoint = actual["checkpoint"]
    assert ref(checkpoint["path"]) == checkpoint
    state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
    parent = torch.load(
        training["parent"]["path"], weights_only=True, map_location="cpu", mmap=True
    )
    assert state["step"] == state["config"]["steps"] == 1000
    assert state["model_config"]["raw_global_conditioning"] == "patch-memory-v4"
    assert state["config"]["raw_global_only"] and state["config"]["lr"] == 0.001
    assert state["config"]["initialized_from"] == queue["expected_lineage"]
    assert len(state["model"]) == len(state["ema"]) == 107
    for field in ("model", "ema"):
        assert all(torch.equal(state[field][k], v) for k, v in parent["ema"].items())
    optimizer = state["optimizer"]["state"]
    assert len(optimizer) == 16 and all(float(s["step"]) == 1000 for s in optimizer.values())
    values = [*state["model"].values(), *state["ema"].values()]
    values += [v for s in optimizer.values() for v in s.values() if isinstance(v, torch.Tensor)]
    assert all(torch.isfinite(v).all() for v in values)
    trained_source = Path(state["config"]["source_snapshot"])
    sources = list((Path(queue["work"]) / "src/demosaic").glob("*.py"))
    assert len(sources) == 69
    assert all(p.read_bytes() == (trained_source / p.name).read_bytes() for p in sources)
    assert not torch.cuda.is_initialized()
    destination = root / "V140-step1000-inference.pt"
    os.link(checkpoint["path"], destination)
    destination.chmod(0o444)
    endpoint = {
        "training_result": status["result"],
        "checkpoint": ref(destination),
        "all1000_clean_and_noisy_batches_match_saved_V137": True,
        "frozen_parent91_model_and_EMA_exact": True,
        "finite_state_values": sum(v.numel() for v in values),
        "EMA_tensors": 107,
        "Adam_states": 16,
        "Adam_steps": 1000,
        "trained_source_modules_exact": 69,
        "new_neural_forwards": 0,
    }
    save(root / "endpoint-verification-v1.json", endpoint)
    plan = {
        **queue,
        "checkpoint": ref(destination),
        "inputs": [
            *queue["inputs"],
            status["result"],
            ref(destination),
            ref(root / "endpoint-verification-v1.json"),
        ],
    }
    save(root / "plan-v1.json", plan)
    guard(plan)


def run(root):
    plan = read(root / "plan-v1.json")
    work = Path(plan["work"])
    env = dict(
        os.environ,
        PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
        HF_HUB_OFFLINE="1",
        TRANSFORMERS_OFFLINE="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        PYTHONDONTWRITEBYTECODE="1",
    )
    scripts = work / "scripts"
    stages = [
        (
            "collect",
            scripts / "collect_retained_checkpoint_pilot.py",
            [root / "plan-v1.json"],
            True,
        ),
        (
            "report",
            scripts / "report_checkpoint_pilot.py",
            [root / "plan-v1.json", root / "collection-v1.json"],
            False,
        ),
        ("audit", scripts / "audit_checkpoint_pilot.py", [root], False),
        (
            "faint-analyze",
            scripts / "analyze_retained_faint_detail.py",
            [root / "faint-analysis-plan-v1.json"],
            False,
        ),
        (
            "faint-audit",
            scripts / "audit_retained_faint_detail.py",
            [root / "faint-analysis-plan-v1.json"],
            False,
        ),
        ("camera-JPEG", root / "render-mesh-JPEG-v1.py", [], False),
    ]
    for label, script, args, cuda in stages:
        guard(plan)
        with (root / f"{label}.log").open("x") as log:
            subprocess.run(
                [plan["python"], "-P", str(script), *map(str, args)],
                cwd=work,
                env={**env, "CUDA_VISIBLE_DEVICES": "0" if cuda else ""},
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=3600 if cuda else 1800,
                check=True,
            )
        print(label, "completed", flush=True)
        if label == "audit":
            # Compatibility with the existing faint-analysis stage contract:
            # all primary numeric/pixel checks are complete; viewing is pending.
            save(
                root / "status.json",
                {
                    "owner": None,
                    "status": "completed-global1000-review-awaiting-actual-native-viewing",
                    "plan": ref(root / "plan-v1.json"),
                    "primary_audit": ref(root / "independent-audit-v1.json"),
                    "scope": "Standalone V140 primary stages completed by this runner; no dependency owner.",
                },
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "bind", "run"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--training-plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.root.resolve(), args.training_plan.resolve()))
    elif args.mode == "bind":
        bind(args.root.resolve())
    else:
        run(args.root.resolve())
