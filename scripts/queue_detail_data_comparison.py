"""Join retained V114/V116 endpoints after both exact independent audits finish."""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np
import psutil
import yaml
from audit_quality_archive import binding, write
from compare_quality_archives import STAGES, compare, read_bound
from compare_quality_crops import gfx_comparison, photo_comparison
from queue_quality_archive_audit import guard, live, read

REPO = Path(__file__).resolve().parents[1]
AUDIT_TERMINAL = "completed-independent-primary-and-analytic-audit-native-viewing-pending"


def recipe_contrast(control, candidate, reviewed_manifest):
    recipes = [yaml.safe_load(Path(item["path"]).read_text()) for item in (control, candidate)]
    for item, recipe in zip((control, candidate), recipes, strict=True):
        if binding(item["path"]) != item:
            raise ValueError("Changed frozen training recipe")
        recipe.setdefault("normalized_band_weight", 0.0)
        recipe.setdefault("fine_weak_texture_fraction", 0.0)
    a, b = recipes
    allowed = {"run", "experiment_notes", "validation_protocol", "paired_manifest", "fine_weak_texture_fraction"}
    differences = {key: {"control": a.get(key), "candidate": b.get(key)} for key in a.keys() | b.keys()
                   if a.get(key) != b.get(key)}
    if set(differences) - allowed:
        raise ValueError(f"Unplanned training changes: {sorted(set(differences)-allowed)}")
    if (a["fine_weak_texture_fraction"] != 0 or b["fine_weak_texture_fraction"] != .075
            or a["paired_manifest"] == b["paired_manifest"] or b["paired_manifest"] != reviewed_manifest["path"]
            or binding(b["paired_manifest"]) != reviewed_manifest
            or binding(a["validation_protocol"])["sha256"] != binding(b["validation_protocol"])["sha256"]
            or a["steps"] != 20000 or a["normalized_band_weight"] != 0):
        raise ValueError("Recipes do not describe the declared matched data trial")
    return {"recipes": {"control": control, "candidate": candidate}, "differences": differences,
            "matched_parent": a["initialize_parent"], "matched_model": a["model"], "updates_per_arm": a["steps"],
            "scope": "Combined fine-source and four reviewed-mask changes; not separate causal effects. Missing optional loss/fine fields use their verified default-off values. Paths/notes differ, validation protocol bytes agree; all other explicit settings match."}


def prepare(root, provenance, proof):
    root = root.absolute()
    if not root.resolve().is_relative_to(REPO/".cache"):
        raise ValueError("Comparison roots belong in the repository cache")
    original = read_bound(binding(provenance))
    checked = read_bound(binding(proof))
    if checked["new_neural_forwards"] != 0 or checked["Torch_imported"]:
        raise ValueError("Readiness proof must use retained outputs without Torch")
    roles, inputs = {}, [binding(provenance), binding(proof), original["source_compatibility"]]
    for role, arm in (("control", "V114"), ("candidate", "V116")):
        audit_binding = original[f"{role}_independent_audit_plan"]
        audit = read_bound(audit_binding)
        guard(audit)
        status = Path(audit["root"])/"status.json"
        state = read(status)
        if not live(state["owner"]) or state["plan"] != audit_binding or state["status"].startswith("failed"):
            raise ValueError("Expected the exact live original independent audit")
        quality_binding = original[f"{role}_quality_plan"]
        if audit["quality_plan"] != quality_binding:
            raise ValueError("Independent audit is attached to another quality run")
        quality = read_bound(quality_binding)
        guard(quality)
        execution = read_bound(quality["training_execution"])
        guard(execution)
        arm_plan = next(a["training_plan"] for a in execution["arms"] if a["arm"] == arm)
        training = read_bound(arm_plan)
        guard(training)
        recipe = binding(training["arms"][arm]["train"])
        if training["frozen_files"].get(recipe["path"]) != recipe["sha256"]:
            raise ValueError("Training recipe is outside its frozen source")
        roles[role] = {"arm": arm, "audit_plan": audit_binding, "audit_owner": state["owner"],
                       "audit_status": str(status), "quality_plan": quality_binding,
                       "training_execution": quality["training_execution"], "training_plan": arm_plan,
                       "training_owner": quality["training_owner"], "training_status": quality["training_status"],
                       "training_terminal": quality["expected_training_terminal"], "recipe": recipe,
                       "expected_source_archive_sha256": (read_bound(original["completed_control_training"])["source_sha256"]
                                                          if role == "control" else execution["expected_source_archive_sha256"])}
        inputs.extend([audit_binding, quality_binding, quality["training_execution"], arm_plan, recipe])
    execution = read_bound(roles["candidate"]["training_execution"])
    reviewed = execution["reviewed_paired_manifest"]
    recipes = recipe_contrast(roles["control"]["recipe"], roles["candidate"]["recipe"], reviewed)
    root.mkdir(parents=True, exist_ok=False)
    work = root/"work"
    sources = ["scripts/queue_detail_data_comparison.py", "scripts/compare_quality_archives.py",
               "scripts/compare_quality_crops.py", "scripts/queue_quality_archive_audit.py",
               "scripts/audit_quality_archive.py", "src/demosaic/archive_metrics.py",
               "src/demosaic/prediction_archive.py", "src/demosaic/safety.py", "src/demosaic/__init__.py",
               "pyproject.toml", "uv.lock"]
    for source in sources:
        destination = work/source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO/source, destination)
    plan = {"root": str(root), "work": str(work), "output": str(work/"comparison-output"), "roles": roles,
            "provenance": binding(provenance), "proof": binding(proof), "recipe_comparison": recipes,
            "reviewed_manifest": reviewed, "expected_control_checkpoint": original["control_checkpoint"],
            "expected_observations": {s: read_bound(roles["candidate"]["audit_plan"])["expected_observations_per_model"][s] for s in STAGES},
            "minimum_available_RAM_GiB": 8, "minimum_free_output_GiB": 2, "maximum_wait_seconds": 172800,
            "controller_source": binding(work/"scripts/queue_detail_data_comparison.py"),
            "inputs": [*inputs, reviewed], "frozen_files": {str(p): binding(p)["sha256"] for p in work.rglob("*") if p.is_file()},
            "scope": "CPU/NumPy-only join of complete independent V114/V116 archives and native crop preparation. Zero inference/noise/RAW work. Original jobs remain untouched. Wait exact audit identities and successful exit; stop/preserve failures without retries. No automatic recommendation or documentation publication; actual material/GFX viewing follows."}
    write(root/"queue-plan-v1.json", plan)
    guard(plan)
    return root/"queue-plan-v1.json"


def completed_role(role):
    state = read(role["audit_status"])
    if (state["owner"] != role["audit_owner"] or state["plan"] != role["audit_plan"]
            or state["status"] != AUDIT_TERMINAL or live(state["owner"])):
        raise ValueError("Independent audit has not successfully finished with its exact identity")
    result = read_bound(state["result"])
    if (result["owner"] != state["owner"] or result["queue_plan"] != role["audit_plan"]
            or set(result["stages"]) != set(STAGES) or result["Torch_imported"]
            or any(result[k] != 0 for k in ("new_neural_forwards", "new_encoder_forwards", "RAW_decodes", "new_noise_observations"))):
        raise ValueError("Incomplete or inconsistent independent audit")
    training = read(role["training_status"])
    if (training["owner"] != role["training_owner"] or training["execution_plan"] != role["training_execution"]
            or training["status"] != role["training_terminal"] or live(training["owner"])):
        raise ValueError("Training did not finish with its original identity")
    read_bound(training["result"])
    accounting = training["completed"][f"train-{role['arm']}"]
    receipt = read_bound(accounting)
    worker = read_bound(receipt["worker_result"])
    counts = {"training_forwards": 20000, "encoder_training_forwards": 20000, "optimizer_steps": 20000,
              "prepared_training_batches": 20000, "validation_forwards": 640, "encoder_validation_forwards": 640}
    if (receipt["counts"] != counts or worker["arm"] != role["arm"] or worker["updates"] != 20000
            or receipt["execution_plan"] != role["training_execution"] or worker["owner"] != receipt["owner"]
            or worker["source_sha256"] != receipt["source_sha256"] or receipt["phase"] != "train"
            or receipt["checkpoint"] != worker["checkpoint"] or live(receipt["owner"])
            or receipt["source_sha256"] != role["expected_source_archive_sha256"]
            or not all(receipt[k] for k in ("initial_all91_EMA_exact_to_explicit_parent", "frozen_encoder_no_gradients", "model_EMA_Adam_finite"))
            or receipt["fresh_AdamW_states"] != 89 or receipt["all_AdamW_steps"] != 20000):
        raise ValueError("Completed training does not match declared common-parent budget/source")
    if binding(receipt["checkpoint"]["path"]) != receipt["checkpoint"]:
        raise ValueError("Trained endpoint bytes changed")
    boundary = read_bound(result["completed_evaluation"])
    full_gfx = boundary["stage_results"]["full-gfx"]
    read_bound(full_gfx)
    return {"terminal_status": binding(role["audit_status"]), "audit": state["result"],
            "training": accounting, "checkpoint": receipt["checkpoint"], "full_gfx": full_gfx,
            "official_frozen_encoder_hash": receipt["official_frozen_encoder_hash"]}


def report(output, statistics, materials, gfx):
    lines = ["# V116 data recipe versus matched V114 Tiny", "",
             "Complete saved-output comparison. **Native material/GFX viewing is pending.** These measurements do not automatically change the recommended model.", "",
             f"V114 SHA256 `{statistics['control_sha256']}`. V116 SHA256 `{statistics['candidate_sha256']}`.", "",
             "Same V112 parent, Tiny architecture, seed and 20,000-update budget. The combined intervention replaces half the weak-source quota with fine sources and revises four reviewed paired-reference masks.", "",
             "| Panel / metric | V114 | V116 | V116 − V114 | Source/scene 95% interval |", "| --- | ---: | ---: | ---: | --- |"]
    stages = {s: read_bound(item) for s, item in statistics["stages"].items()}
    for name in ("photo", "known", "unseen"):
        for value in stages[name]["summaries"]["all"]:
            if value["available"]:
                low, high = value["bootstrap_95_interval"]
                lines.append(f"| {name} / {value['metric']} | {value['control_mean']:.6f} | {value['current_mean']:.6f} | {value['change']:+.6f} | [{low:+.6f}, {high:+.6f}] |")
    lines.extend(["", "PSNR increases are improvements; chroma/gradient error decreases are improvements. Photos are source-weighted; camera crops are averaged within capture, captures within scene, and scenes equally. Bootstrap intervals describe these fixed sources/scenes, not training-seed uncertainty or all cameras. AHD reference metrics are auxiliary, not exact-RGB GT. Full per-observation changes, condition summaries and largest changes remain in the JSON files.", "",
                  "| Weak carrier (level .18, contrast .02, ISO12800) | V114 in-phase gain | V116 in-phase gain | V114 / V116 noncarrier RMS |", "| --- | ---: | ---: | --- |"])
    for group in stages["texture"]["summaries"]["analytic_groups"]:
        meta = group["group"]
        if meta["kind"] == "carrier" and meta["level"] == .18 and meta["contrast"] == .02 and meta["condition"] == "iso12800-prior":
            a, b = group["control"], group["candidate"]
            lines.append(f"| Period {meta['period']} | {a['in_phase_gain']['mean']:.5f} | {b['in_phase_gain']['mean']:.5f} | {a['noncarrier_rms']['mean']:.7f} / {b['noncarrier_rms']['mean']:.7f} |")
    lines.extend(["", "Carrier gain is interpreted relative to one, together with phase, residual and flat-field false texture in the JSON; increasing gain alone is not a quality verdict. Analytic patterns are descriptive.", "",
                  "| Color condition | V114 / V116 mean max-channel bias (DN16) | V114 / V116 worst bias (DN16) |", "| --- | --- | --- |"])
    for condition in sorted({r["condition"] for r in stages["color"]["rows"]}):
        selected = [r for r in stages["color"]["rows"] if r["condition"] == condition]
        values = [[max(map(abs, r[role]["camera_RGB_mean_error"]))*65535 for r in selected] for role in ("control", "candidate")]
        lines.append(f"| {condition} | {np.mean(values[0]):.3f} / {np.mean(values[1]):.3f} | {max(values[0]):.3f} / {max(values[1]):.3f} |")
    lines.extend(["", "## Native material crops", "", "Rows: noisy, V114, V116, exact synthetic GT. Each crop is 160×160 native pixels. Source IDs, attribution, coordinates, checkpoint/observation hashes, conditioning and common display transforms are in the adjacent receipts.", "", "![Matched materials](matched-materials.png)", ""])
    for copied in materials["candidate_triplets"]:
        lines.extend([f"![Noisy / V116 / exact GT]({Path(copied['image']['path']).name})", ""])
    lines.extend(["## Standing GFX DSCF3879 / DSCF3880", "", "Rows: noisy, V114, V116, independently demosaiced ISO100 reference. The reference differs in aperture and moving subjects; it is not pixelwise GT and has no numerical quality score. All four rows share the same exposure, WB and matrix. Predictions are native crops of each complete blended 102MP frame, retained before RGB16 quantization.", ""])
    for item in gfx["boards"]:
        lines.extend([f"![GFX native comparisons]({Path(item['image']['path']).name})", ""])
    lines.extend(["Columns across the two boards: "+", ".join(gfx["regions_in_column_order"])+".", "", "This report performs no model inference, observation generation or RAW decoding. Actual material/GFX review and an explicit account of gains and weaknesses are required before publishing a recommendation.", ""])
    with (Path(output)/"report.md").open("x") as stream:
        stream.write("\n".join(lines))


def controller(path):
    plan = read(path)
    guard(plan)
    if binding(__file__) != plan["controller_source"] or os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise ValueError("Frozen CPU-only comparison required")
    root = Path(plan["root"])
    (root/"controller.claim").open("x").close()
    state = {"owner": {"pid": os.getpid(), "created": psutil.Process().create_time()}, "plan": binding(path), "completed": {}}
    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        temporary = root/"status.tmp"
        temporary.write_text(json.dumps(state, indent=2)+"\n")
        temporary.replace(root/"status.json")
    try:
        for role, dependency in plan["roles"].items():
            record("waiting-for-exact-independent-audits", role=role, dependency=dependency["audit_owner"])
            began = time.monotonic()
            while live(dependency["audit_owner"]):
                observed = read(dependency["audit_status"])
                if (binding(dependency["audit_plan"]["path"]) != dependency["audit_plan"]
                        or observed["owner"] != dependency["audit_owner"] or observed["plan"] != dependency["audit_plan"]
                        or observed["status"].startswith("failed")):
                    raise ValueError("Independent audit failed or identity changed")
                if time.monotonic()-began > plan["maximum_wait_seconds"]:
                    raise TimeoutError("Declared matched-comparison deadline")
                time.sleep(10)
            state["completed"][role] = completed_role(dependency)
        guard(plan)
        if (psutil.virtual_memory().available < plan["minimum_available_RAM_GiB"]*2**30
                or shutil.disk_usage(root).free < plan["minimum_free_output_GiB"]*2**30):
            raise RuntimeError("Insufficient CPU comparison headroom")
        old, new = (state["completed"][role] for role in ("control", "candidate"))
        if old["checkpoint"] != plan["expected_control_checkpoint"] or old["checkpoint"]["sha256"] == new["checkpoint"]["sha256"] or old["official_frozen_encoder_hash"] != new["official_frozen_encoder_hash"]:
            raise ValueError("Endpoint/control identity differs")
        recipes = recipe_contrast(plan["roles"]["control"]["recipe"], plan["roles"]["candidate"]["recipe"], plan["reviewed_manifest"])
        if recipes != plan["recipe_comparison"]:
            raise ValueError("Matched recipes changed")
        write(root/"completed-dependencies-v1.json", state["completed"])
        output = Path(plan["output"])
        record("joining-independent-metrics-and-native-crops")
        statistics = compare(old["audit"]["path"], new["audit"]["path"], old["checkpoint"]["sha256"], new["checkpoint"]["sha256"], output,
                             expected_observations=plan["expected_observations"])
        materials = photo_comparison(read_bound(statistics["stages"]["photo"]), output)
        gfx = gfx_comparison(old["full_gfx"]["path"], new["full_gfx"]["path"], old["checkpoint"]["sha256"], new["checkpoint"]["sha256"], output)
        report(output, statistics, materials, gfx)
        if "torch" in sys.modules:
            raise RuntimeError("CPU comparison imported Torch")
        guard(plan)
        write(root/"result-v1.json", {"queue_plan": binding(path), "owner": state["owner"],
              "dependencies": binding(root/"completed-dependencies-v1.json"), "statistics": binding(output/"result.json"),
              "recipes": recipes, "materials": materials, "gfx": gfx, "report": binding(output/"report.md"),
              "Torch_imported": False, "new_neural_forwards": 0, "new_encoder_forwards": 0,
              "new_noise_observations": 0, "RAW_decodes": 0, "native_review": "Prepared; actual human viewing pending"})
        record("completed-matched-V114-V116-comparison-native-viewing-pending", result=binding(root/"result-v1.json"))
    except BaseException as error:
        record("failed-matched-comparison-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "controller"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--provenance", type=Path)
    parser.add_argument("--proof", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.provenance, args.proof))
    else:
        controller(args.path)
