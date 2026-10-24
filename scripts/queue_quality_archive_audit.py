"""Queue an independent CPU archive audit after the exact endpoint evaluator."""

import argparse
import json
import os
import shutil
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
from audit_quality_archive import audit, binding, paired_changes, read_rows, write

REPO = Path(__file__).resolve().parents[1]
NUMERICAL = ("photo", "known", "unseen", "texture", "color")
V112 = "21c3cca8370df21e3412f9ccbf441c35afcfad8fd03174c7727f4f88874783b1"


def read(path):
    return json.loads(Path(path).read_text())


def live(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def guard(plan):
    for item in plan["inputs"]:
        if binding(item["path"]) != item:
            raise ValueError(f"Changed input: {item['path']}")
    for path, digest in plan["frozen_files"].items():
        if binding(path)["sha256"] != digest:
            raise ValueError(f"Changed frozen source: {path}")


def prepare(root, quality_plan, proof):
    root, quality_plan = root.absolute(), quality_plan.absolute()
    if not root.resolve().is_relative_to(REPO/".cache"):
        raise ValueError("Audit queue roots belong in the repository cache")
    quality = read(quality_plan)
    guard(quality)
    status_path = Path(quality["root"])/"status.json"
    state = read(status_path)
    if state["queue_plan"] != binding(quality_plan) or not live(state["owner"]) or state["status"].startswith("failed"):
        raise ValueError("Expected live original endpoint evaluator")
    if read(proof)["new_neural_forwards"] != 0:
        raise ValueError("Proof must use retained arrays only")
    root.mkdir(parents=True, exist_ok=False)
    work = root/"work"
    sources = ["scripts/queue_quality_archive_audit.py", "scripts/audit_quality_archive.py",
               "src/demosaic/archive_metrics.py", "src/demosaic/prediction_archive.py", "src/demosaic/safety.py",
               "src/demosaic/__init__.py", "pyproject.toml", "uv.lock"]
    for source in sources:
        destination = work/source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO/source, destination)
    inputs = [binding(quality_plan), binding(proof), *quality["existing_control_files"]]
    controls = {}
    for stage in NUMERICAL:
        path = Path(quality["existing_control_files"][NUMERICAL.index(stage)]["path"])
        report = path if stage == "color" else path.parent/"summary.json"
        controls[stage] = {"rows": binding(path), "report": binding(report)}
        inputs.append(binding(report))
    plan = {"root": str(root), "work": str(work), "output": str(work/"audit-output"), "python": sys.executable,
            "quality_plan": binding(quality_plan), "quality_status": str(status_path), "quality_owner": state["owner"],
            "expected_terminal": "completed-matched-endpoint-evaluation-awaiting-independent-and-native-review",
            "proof": binding(proof), "controls": controls, "baseline_sha256": V112,
            "strong_reference": quality["existing_control_files"][-1],
            "material_ids": ["0ae232278265dabbdd54f52c34045a3d03323aa7", "212ae12913effa23268af953b4c8f8e8b7ab4ef5"],
            "maximum_wait_seconds": 345600, "minimum_available_RAM_GiB": 8, "minimum_free_output_GiB": 2,
            "expected_observations_per_model": {s: quality["stages"][s]["observations_per_model"] for s in NUMERICAL},
            "controller_source": binding(work/"scripts/queue_quality_archive_audit.py"),
            "inputs": inputs, "frozen_files": {str(p): binding(p)["sha256"] for p in work.rglob("*") if p.is_file()},
            "scope": "NumPy64 independent primary/analytic metrics from exact retained targets; 28380 observations, zero neural/encoder calls, noise regeneration, RAW decoding or CUDA. Two native bark/canopy triplets per model. Existing V112/stronger RawNIND controls reused. Human photo/GFX viewing and model recommendation remain separate; no automatic retry or promotion."}
    write(root/"queue-plan-v1.json", plan)
    guard(plan)
    return root/"queue-plan-v1.json"


def summaries(plan, results):
    summaries, own = {}, {}
    for stage in NUMERICAL:
        own[stage] = read(results[stage]["independent_rows"]["path"])
        control = read(plan["controls"][stage]["report"]["path"])
        models = control["checkpoints" if stage == "color" else "models"]
        baseline_index = next(i for i, m in enumerate(models) if m.get("sha256") == plan["baseline_sha256"])
        baseline_label = baseline_index if stage == "color" else models[baseline_index]["label"]
        rows = control["results"] if stage == "color" else read_rows(plan["controls"][stage]["rows"]["path"])
        rows = [r for r in rows if r["model_index" if stage == "color" else "model"] == baseline_label]
        if stage in {"photo", "known", "unseen"}:
            metrics = ("srgb_psnr", "linear_psnr", "chroma_mae", "gradient_mae") if stage == "photo" else ("sensor_psnr", "ahd_srgb_psnr", "ahd_chroma_mae", "ahd_gradient_mae")
            groups = defaultdict(list)
            for row in own[stage]:
                groups[row["checkpoint_sha256"]].append(row)
            summaries[stage] = {digest: [paired_changes(values, rows, stage=stage, metric=m) for m in metrics]
                                for digest, values in groups.items()}
        elif stage == "color":
            summaries[stage] = []
            for name, selected in [("V112", rows), *[(digest, [r for r in own[stage] if r["checkpoint_sha256"] == digest])
                                                    for digest in sorted({r["checkpoint_sha256"] for r in own[stage]})]]:
                for condition in ("adc-only", "iso12800-prior"):
                    cases = [r for r in selected if r["condition"] == condition]
                    if len(cases) != 588:
                        raise ValueError("Incomplete analytic-color condition")
                    values = np.array([max(map(abs, r["metrics"]["camera_RGB_mean_error"])) for r in cases])*65535
                    summaries[stage].append({"model": name, "condition": condition, "cases": len(cases),
                                             "mean_DN16": float(values.mean()), "p95_DN16": float(np.quantile(values, .95)),
                                             "maximum_DN16": float(values.max()), "worst_case": cases[int(values.argmax())]["case"]})
        else:
            summaries[stage] = []
            for name, selected in [("V112", rows), *[(digest, [r for r in own[stage] if r["checkpoint_sha256"] == digest])
                                                    for digest in sorted({r["checkpoint_sha256"] for r in own[stage]})]]:
                for period in (4, 8, 16):
                    cases = [r for r in selected if r["kind"] == "carrier" and r["level"] == .18 and r["contrast"] == .02
                             and r["period"] == period and r["condition"] == "iso12800-prior"]
                    if len(cases) != 16:
                        raise ValueError("Incomplete weak-carrier condition")
                    summaries[stage].append({"model": name, "period": period, "cases": 16,
                                             "in_phase_gain": float(np.mean([r["metrics"]["in_phase_gain"] for r in cases])),
                                             "noncarrier_rms": float(np.mean([r["metrics"]["noncarrier_rms"] for r in cases]))})
    strong = read(plan["strong_reference"]["path"])
    comparisons = []
    for stage in ("known", "unseen"):
        controls = {r["scene"]: r["sensor_psnr"] for r in strong["camera_scene_means"] if r["panel"] == stage and r["model"] == "RawNIND-preup"}
        for digest, values in summaries[stage].items():
            # paired_changes retains the per-scene change; control scenes from
            # the verified V112 rows define the corresponding absolute values.
            measured = defaultdict(lambda: defaultdict(list))
            for row in own[stage]:
                if row["checkpoint_sha256"] == digest:
                    measured[row["scene"]][row["pair"]].append(row["metrics"]["sensor_psnr"])
            if measured.keys() != controls.keys():
                raise ValueError("Strong reference scenes differ")
            for scene, pairs in sorted(measured.items()):
                value = float(np.mean([np.mean(v) for v in pairs.values()]))
                comparisons.append({"panel": stage, "checkpoint_sha256": digest, "scene": scene,
                                    "sensor_psnr": value, "RawNIND_preup_sensor_psnr": controls[scene], "change": value-controls[scene]})
    summaries["strong_reference_scene_comparison"] = comparisons
    return summaries


def controller(path):
    plan = read(path)
    guard(plan)
    if binding(__file__) != plan["controller_source"] or os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise ValueError("Frozen CPU-only controller required")
    root = Path(plan["root"])
    (root/"controller.claim").open("x").close()
    state = {"owner": {"pid": os.getpid(), "created": psutil.Process().create_time()}, "plan": binding(path), "completed": {}}
    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        temp = root/"status.tmp"
        temp.write_text(json.dumps(state, indent=2)+"\n")
        temp.replace(root/"status.json")
    try:
        record("waiting-for-exact-endpoint-evaluation-owner", dependency=plan["quality_owner"])
        began = time.monotonic()
        while live(plan["quality_owner"]):
            observed = read(plan["quality_status"])
            if observed["owner"] != plan["quality_owner"] or observed["queue_plan"] != plan["quality_plan"] or observed["status"].startswith("failed"):
                raise ValueError("Endpoint evaluator failed or identity changed")
            if time.monotonic()-began > plan["maximum_wait_seconds"]:
                raise TimeoutError("Declared evaluation wait deadline")
            time.sleep(10)
        observed = read(plan["quality_status"])
        quality = read(plan["quality_plan"]["path"])
        if observed["owner"] != plan["quality_owner"] or observed["queue_plan"] != plan["quality_plan"] or observed["status"] != plan["expected_terminal"]:
            raise ValueError("Endpoint evaluator did not finish successfully")
        if set(observed["completed"]) != set(quality["stages"]) or (observed.get("child") and live(observed["child"])):
            raise ValueError("Incomplete endpoint stages or child still live")
        guard(plan)
        guard(quality)
        evaluation_path = Path(quality["root"])/"evaluation-plan-v1.json"
        evaluation = read(evaluation_path)
        guard(evaluation)
        if "torch" in sys.modules:
            raise RuntimeError("Audit must not import Torch")
        boundary = {"terminal_status": binding(plan["quality_status"]), "evaluation_plan": binding(evaluation_path), "stage_results": observed["completed"]}
        for item in observed["completed"].values():
            if binding(item["path"]) != item or live(read(item["path"])["owner"]):
                raise ValueError("Changed stage evidence or live stage owner")
        write(root/"completed-evaluation-boundary-v1.json", boundary)
        results = {}
        output = Path(plan["output"])
        for stage in NUMERICAL:
            if psutil.virtual_memory().available < plan["minimum_available_RAM_GiB"]*2**30 or shutil.disk_usage(root).free < plan["minimum_free_output_GiB"]*2**30:
                raise RuntimeError("Insufficient CPU audit headroom")
            record("running-independent-CPU-archive-audit", stage=stage)
            original = read(observed["completed"][stage]["path"])
            for item in (original["archive"], original["report"]):
                if binding(item["path"]) != item:
                    raise ValueError("Changed archive/report")
            results[stage] = audit(original["archive"]["path"], original["report"]["path"], output/stage, stage=stage,
                                   material_ids=plan["material_ids"] if stage == "photo" else (),
                                   source_manifest=evaluation["stages"][stage]["manifest"]["path"] if stage == "photo" else None)
            counts = results[stage]["observations"]
            if results[stage]["models"] != 2 or len(counts) != 2 or any(v != plan["expected_observations_per_model"][stage] for v in counts.values()):
                raise ValueError("Independent observation counts differ")
            state["completed"][stage] = binding(output/stage/"result.json")
            record("completed-independent-CPU-stage")
        guard(plan)
        guard(evaluation)
        result = {"queue_plan": binding(path), "completed_evaluation": binding(root/"completed-evaluation-boundary-v1.json"),
                  "stages": state["completed"], "comparisons": summaries(plan, results),
                  "owner": state["owner"], "Torch_imported": "torch" in sys.modules, "new_neural_forwards": 0,
                  "new_encoder_forwards": 0, "RAW_decodes": 0, "new_noise_observations": 0,
                  "native_review": "Two bark/canopy triplets per model prepared at native160. Actual viewing of these and standing GFX/full-frame crops remains pending. No automatic recommendation change."}
        if result["Torch_imported"]:
            raise RuntimeError("Torch was imported during CPU audit")
        write(root/"result-v1.json", result)
        record("completed-independent-primary-and-analytic-audit-native-viewing-pending", result=binding(root/"result-v1.json"))
    except BaseException as error:
        record("failed-independent-audit-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "controller"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--quality-plan", type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.quality_plan, args.proof))
    else:
        controller(args.path)
