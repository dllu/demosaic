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


def review_step_spec(horizon, step):
    """Require explicit selection for longer runs; preserve the original1k default."""
    if type(horizon) is not int or horizon < 8:
        raise ValueError("Need an integer training horizon >=8")
    if step is None:
        if horizon != 1000:
            raise ValueError("Select the review step explicitly for a longer training run")
        step = horizon
    if type(step) is not int or not 0 < step <= horizon:
        raise ValueError("Review step must lie inside the declared training horizon")
    return step, step < horizon


def append_retained_control(observations, previous, collection, *, checked=ref):
    """Adopt a saved method only on exactly the same declared observations."""
    result = deepcopy(observations)
    assert len(result) == len(previous["observations"]) == len(collection["observations"])
    ids = [o["id"] for o in result]
    assert len(set(ids)) == len(ids)
    assert ids == [o["id"] for o in previous["observations"]]
    assert ids == [o["id"] for o in collection["observations"]]
    label = previous["model_label"]
    for current, old, prediction in zip(
        result, previous["observations"], collection["observations"], strict=True
    ):
        assert {k: v for k, v in current.items() if k != "controls"} == {
            k: v for k, v in old.items() if k != "controls"
        }
        assert label not in {
            c.get("model", {}).get("label", c.get("label")) for c in current["controls"]
        }
        binding = prediction["prediction"]
        assert checked(binding["path"]) == binding
        current["controls"].append(
            {
                "model": {
                    "label": label,
                    "step": previous["step"],
                    "sha256": previous["checkpoint"]["sha256"],
                },
                "prediction": deepcopy(binding),
            }
        )
    return result


def select_control_methods(observations, labels):
    """Select and order explicitly named saved controls, preserving prediction bindings."""
    assert len(labels) == len(set(labels)) and labels
    result = deepcopy(observations)
    for observation in result:
        available = {}
        for control in observation["controls"]:
            label = control.get("model", {}).get("label", control.get("label"))
            if label == "V120-profile3879":
                label = "V120"
            assert label not in available
            available[label] = control
        assert all(label in available for label in labels)
        observation["controls"] = [available[label] for label in labels]
    return result


def prepare(
    root,
    training_path,
    *,
    camera_control="V137",
    comparison_scope=None,
    step=None,
    additional_control_roots=(),
    retained_control_labels=None,
    collector_cpu_threads=2,
):
    import yaml

    if type(collector_cpu_threads) is not int or collector_cpu_threads not in (1, 2):
        raise ValueError("Collector CPU threads must be1 or2")
    training = read(training_path)
    guard(training)
    assert len(training["arms"]) == 1
    arm = next(iter(training["arms"]))
    recipe = yaml.safe_load(Path(training["arms"][arm]["train"]).read_text())
    step, progress = review_step_spec(recipe["steps"], step)
    model_label = (
        arm + " 1k EMA"
        if recipe["steps"] == step == 1000
        else f"{arm} {step}of{recipe['steps']} EMA"
    )
    global_features = recipe["model"].get("raw_global_features", False)
    global_mode = recipe["model"].get("raw_global_conditioning", "legacy-v1")
    assert not global_features or global_mode == "patch-memory-v4"
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
    shutil.copyfile(
        REPO / "scripts/analyze_retained_faint_detail.py",
        work / "scripts/analyze_retained_faint_detail.py",
    )
    if collector_cpu_threads == 1:
        collector = work / "scripts/collect_retained_checkpoint_pilot.py"
        original = collector.read_text()
        assert original.count("torch.set_num_threads(2)") == 1
        collector.write_text(
            original.replace("torch.set_num_threads(2)", "torch.set_num_threads(1)")
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
    extra_labels, extra_inputs = [], []
    for control_root in additional_control_roots:
        control_root = Path(control_root)
        control_path = control_root / "plan-v1.json"
        control = read(control_path)
        guard(control)
        saved = read(control_root / "collection-v1.json")
        assert saved["plan"] == ref(control_path)
        assert saved["counts"] == {"root": 102, "encoder": 102}
        observations = append_retained_control(observations, control, saved)
        extra_labels.append(control["model_label"])
        extra_inputs += [ref(control_path), ref(control_root / "collection-v1.json")]
    control_methods = [*METHODS[:-1], *extra_labels]
    if retained_control_labels is not None:
        observations = select_control_methods(observations, retained_control_labels)
        control_methods = list(retained_control_labels)
    camera_source = (BASE / "raw-patch-memory-quality-v1/render-mesh-JPEG-v1.py").read_text()
    camera = root / "render-mesh-JPEG-v1.py"
    camera.write_text(
        camera_source.replace("V139", camera_control)
        .replace("V140 1k EMA", model_label)
        .replace("V140", arm)
    )
    scope = (
        f"Standalone {arm} complete1k pilot, four saved controls and102 fixed inputs: "
        "64 shadow/16 ordinary/16 faintADC/four mainGFX512/two mesh768 profiles. "
        "All ROIs/noise/display/source masks fixed;408 control predictions reused. "
        "Matched actualV137 training batches, but scope/LR/operator differ, so this "
        "is not an isolated descriptor ablation. Exact syntheticGT and approximate "
        "binned/separateISO100 references retain accurate roles. Native160 no-resize "
        "triplets, faint40x displays, both corrected GFX pairs and both cameraJPEGs. "
        "No new noise/RAW/reference-model calls. Not full427/camera/color/fullframe quality."
    )
    if comparison_scope is not None:
        scope = comparison_scope
    queue = {
        **old,
        "root": str(root),
        "work": str(work),
        "training_plan": ref(training_path),
        "observations": observations,
        "model_label": model_label,
        "step": step,
        "training_horizon": recipe["steps"],
        "progress_checkpoint": progress,
        "EMA_tensors": 107 if global_features else 91,
        "raw_global_features": global_features,
        "raw_global_conditioning": global_mode,
        "primary_complete_status": "completed-primary-numeric-review-awaiting-native-viewing",
        "scope": scope,
        "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
        "reporter": ref(work / "scripts/report_checkpoint_pilot.py"),
        "auditor": ref(work / "scripts/audit_checkpoint_pilot.py"),
        "inputs": [
            ref(training_path),
            ref(previous / "plan-v1.json"),
            ref(previous / "collection-v1.json"),
            *extra_inputs,
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
    }
    del queue["checkpoint"]
    for key in ("training_owner", "controller", "endpoint_binder", "maximum_training_wait_seconds"):
        queue.pop(key, None)  # Unused ownership fields from the historical V137 template.
    queue["frozen_files"][str(camera)] = ref(camera)["sha256"]
    save(root / "queue-plan-v1.json", queue)
    faint = read(BASE / "raw-global-conditioned-faint-detail-v1/analysis-plan-v1.json")
    faint.update(
        root=str(root),
        quality_root=str(root),
        quality_owner=None,
        output=str(root / "faint-detail-v1"),
        methods=[*control_methods, model_label],
        primary_complete_status=queue["primary_complete_status"],
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
                    "status": plan.get(
                        "primary_complete_status",
                        "completed-global1000-review-awaiting-actual-native-viewing",
                    ),
                    "plan": ref(root / "plan-v1.json"),
                    "primary_audit": ref(root / "independent-audit-v1.json"),
                    "scope": f"{plan['model_label']} primary stages completed by this runner; no dependency owner.",
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
