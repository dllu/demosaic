"""Join audited endpoints and retained controls, exports and native crops without NN."""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import psutil
from audit_quality_archive import binding, write
from compare_quality_archives import compare, read_bound
from compare_quality_crops import gfx_comparison, matched_material_stage, photo_comparison
from diagnose_archive_local_detail import analyze
from queue_quality_archive_audit import guard, live, read
from verify_rgb16_exports import verify_exports

REPO = Path(__file__).resolve().parents[1]
TERMINAL = "completed-saved-quality-comparisons-native-viewing-pending"
AUDIT_TERMINAL = "completed-independent-primary-and-analytic-audit-native-viewing-pending"
EXPECTED = {"photo": 12404, "known": 72, "unseen": 90, "texture": 448, "color": 1176}


def save_status(path, state):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def audit_ready(state, dependency, *, is_live=live):
    if state["owner"] != dependency["owner"] or state["plan"] != dependency["plan"]:
        raise ValueError("Independent audit identity differs")
    if state["status"].startswith("failed"):
        raise RuntimeError("Independent audit failed; preserve its completed work")
    if is_live(dependency["owner"]):
        return False
    if state["status"] != AUDIT_TERMINAL:
        raise RuntimeError("Independent audit owner exited before successful completion")
    return True


def endpoint_checkpoints(evaluation, arms):
    records = evaluation["checkpoints"]
    if len(records) != len(arms) or {r["arm"] for r in records} != set(arms):
        raise ValueError("Audited endpoint coverage differs")
    if len({r["sha256"] for r in records}) != len(arms):
        raise ValueError("Audited endpoints must have distinct checkpoints")
    if any(r["expected_lineage"]["step"] != 20000 for r in records):
        raise ValueError("Only complete original 20000-update endpoints enter this report")
    return {r["arm"]: {k: r[k] for k in ("path", "sha256")} for r in records}


def deferred_reference(state, dependency, label):
    """Resolve a completed audit by its original owner and declared endpoint."""
    if not audit_ready(state, dependency):
        return None
    audited = read_bound(state["result"])
    if (
        audited["owner"] != dependency["owner"]
        or audited["new_neural_forwards"]
        or audited["Torch_imported"]
    ):
        raise ValueError("Expected the original completed CPU control audit")
    quality = read_bound(dependency["quality_plan"])
    training = read_bound(quality["training_execution"])
    boundary = read_bound(audited["completed_evaluation"])
    evaluation = read_bound(boundary["evaluation_plan"])
    if evaluation["training_execution"] != quality["training_execution"]:
        raise ValueError("Deferred control training lineage differs")
    checkpoints = endpoint_checkpoints(evaluation, list(training["arms"]))
    if label not in checkpoints:
        raise ValueError("Deferred control endpoint is not declared")
    checkpoint = checkpoints[label]
    if binding(checkpoint["path"]) != checkpoint:
        raise ValueError("Deferred control checkpoint changed")
    return {"audit": state["result"], "checkpoint": checkpoint}


def matching_fullframe_inputs(control, candidate, control_sha, candidate_sha):
    """Compare every actual tile batch, rather than only a grid declaration."""
    sequences = []
    for stage, sha in ((control, control_sha), (candidate, candidate_sha)):
        rows = [row for row in stage["invariants"] if row["checkpoint"]["sha256"] == sha]
        if len(rows) != 1:
            raise ValueError("Require one declared full-frame endpoint")
        row = rows[0]
        if row["calls"] != 130 or row["encoder_calls"] != 130 or len(row["input_sequence"]) != 130:
            raise ValueError("Full-frame input coverage differs")
        sequences.append(row["input_sequence"])
    if sequences[0] != sequences[1]:
        raise ValueError("Actual full-frame tile inputs differ")
    return {"actual_tile_batches_exact": 130, "new_neural_forwards": 0}


def prepare(
    root,
    audit_plan,
    references,
    arms,
    contrasts,
    *,
    allow_gfx_conditioning_difference=False,
    deferred_reference_plans=None,
    strict_gfx_contrasts=(),
    maximum_wait_seconds=345600,
):
    root, audit_plan = root.resolve(), audit_plan.resolve()
    if not root.is_relative_to(REPO / ".cache"):
        raise ValueError("Comparison queues belong in the repository cache")
    audit = read(audit_plan)
    guard(audit)
    state_path = Path(audit["root"]) / "status.json"
    state = read(state_path)
    if state["plan"] != binding(audit_plan):
        raise ValueError("Independent audit plan differs")
    if state["status"].startswith("failed"):
        raise ValueError("Cannot queue comparisons from a failed audit")
    if not live(state["owner"]):
        audit_ready(state, {"owner": state["owner"], "plan": binding(audit_plan)})
    arms = list(arms)
    deferred_reference_plans = deferred_reference_plans or {}
    if set(deferred_reference_plans) & (set(references) | set(arms)):
        raise ValueError("Deferred controls must have distinct labels")
    available = set(references) | set(arms) | set(deferred_reference_plans)
    if not arms or len(set(arms)) != len(arms) or not contrasts:
        raise ValueError("Require distinct declared endpoints and contrasts")
    if any(
        left not in available or right not in arms or left == right for left, right in contrasts
    ):
        raise ValueError("Contrasts must use declared controls and new candidates")
    if {right for _, right in contrasts} != set(arms):
        raise ValueError("Every endpoint needs a candidate comparison")
    if any(list(pair) not in [list(c) for c in contrasts] for pair in strict_gfx_contrasts):
        raise ValueError("Strict GFX comparisons must name declared contrasts")
    inputs = [binding(audit_plan)]
    for reference in references.values():
        old = read_bound(reference["audit"])
        if live(old["owner"]) or old["new_neural_forwards"] != 0:
            raise ValueError("Controls require completed independent retained-output audits")
        inputs.extend(reference.values())
    deferred = {}
    for label, path in deferred_reference_plans.items():
        previous = read(path)
        guard(previous)
        previous_state_path = Path(previous["root"]) / "status.json"
        previous_state = read(previous_state_path)
        dependency = {
            "owner": previous_state["owner"],
            "plan": binding(path),
            "status": str(previous_state_path),
            "quality_plan": previous["quality_plan"],
        }
        quality = read_bound(previous["quality_plan"])
        training = read_bound(quality["training_execution"])
        if label not in training["arms"]:
            raise ValueError("Deferred control is absent from its training plan")
        # Checking readiness also rejects failure, identity drift or premature exit.
        audit_ready(previous_state, dependency)
        deferred[label] = dependency
        inputs.extend((binding(path), previous["quality_plan"]))
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    helpers = (
        "queue_quality_comparisons.py",
        "audit_quality_archive.py",
        "compare_quality_archives.py",
        "compare_quality_crops.py",
        "diagnose_archive_local_detail.py",
        "diagnose_local_material_detail.py",
        "verify_rgb16_exports.py",
        "queue_quality_archive_audit.py",
    )
    sources = [REPO / "scripts" / name for name in helpers]
    sources += [
        REPO / "src/demosaic" / name
        for name in ("__init__.py", "archive_metrics.py", "prediction_archive.py", "safety.py")
    ]
    for source in sources:
        target = work / source.relative_to(REPO)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    plan = {
        "root": str(root),
        "work": str(work),
        "output": str(work / "comparison-output"),
        "python": sys.executable,
        "controller_source": binding(work / "scripts/queue_quality_comparisons.py"),
        "dependency": {
            "owner": state["owner"],
            "plan": binding(audit_plan),
            "status": str(state_path),
        },
        "new_arms": arms,
        "references": references,
        "deferred_references": deferred,
        "contrasts": contrasts,
        "strict_gfx_contrasts": [list(pair) for pair in strict_gfx_contrasts],
        "allow_gfx_conditioning_difference": allow_gfx_conditioning_difference,
        "expected_observations": EXPECTED,
        "maximum_wait_seconds": maximum_wait_seconds,
        "planned_linear_RGB16_values": 460800 * len(arms),
        "minimum_available_RAM_GiB": 8,
        "minimum_free_output_GiB": 4,
        "inputs": inputs,
        "frozen_files": {str(p): binding(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Retained arrays only: complete matched primary/analytic contrasts, 427-source local detail, two native synthetic-GT material triplets and all six standing GFX regions per contrast, all declared endpoint RGB16 exports. Any explicitly allowed GFX conditioning difference is labeled on the boards and recorded separately; it cannot establish a model-only effect and requires later matching-profile comparison. Shared RAW/reference pixels, ROI and display must still match. No Torch/model calls/noise/RAW. Actual native viewing and fine green mesh remain separate; no retry or model promotion.",
    }
    write(root / "queue-plan-v1.json", plan)
    guard(plan)
    return root / "queue-plan-v1.json"


def controller(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Saved-output comparison controller requires CPU without Torch")
    plan = read(path)
    guard(plan)
    if binding(__file__) != plan["controller_source"]:
        raise ValueError("Comparison controller source differs")
    os.nice(10)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    state = {
        "owner": {"pid": os.getpid(), "created": process.create_time()},
        "plan": binding(path),
        "completed": {},
    }

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        save_status(root / "status.json", state)

    try:
        dependency = plan["dependency"]
        record("waiting-for-original-independent-audit", dependency=dependency["owner"])
        began = time.monotonic()
        while not audit_ready(read(dependency["status"]), dependency):
            if time.monotonic() - began > plan["maximum_wait_seconds"]:
                raise TimeoutError("Independent-audit observation window expired")
            time.sleep(10)
        audited_state = read(dependency["status"])
        audited = read_bound(audited_state["result"])
        if (
            audited["owner"] != dependency["owner"]
            or audited["new_neural_forwards"] != 0
            or audited["Torch_imported"]
        ):
            raise ValueError("Expected original completed retained-output audit")
        boundary = read_bound(audited["completed_evaluation"])
        evaluation = read_bound(boundary["evaluation_plan"])
        checkpoints = endpoint_checkpoints(evaluation, plan["new_arms"])
        for checkpoint in checkpoints.values():
            if binding(checkpoint["path"]) != checkpoint:
                raise ValueError("Changed immutable endpoint checkpoint")
        guard(plan)
        if (
            psutil.virtual_memory().available < plan["minimum_available_RAM_GiB"] * 2**30
            or shutil.disk_usage(root).free < plan["minimum_free_output_GiB"] * 2**30
        ):
            raise RuntimeError("Insufficient comparison RAM or output space")
        output = Path(plan["output"])
        output.mkdir(exist_ok=False)
        record("checking-all-declared-endpoint-RGB16-exports")
        exports = verify_exports(
            boundary["stage_results"]["full-gfx"],
            checkpoints,
            output / "full-export-verification-v1.json",
        )
        reference_controls = dict(plan["references"])
        for label, dependency in plan.get("deferred_references", {}).items():
            record("waiting-for-original-control-independent-audit", control=label)
            while True:
                resolved = deferred_reference(read(dependency["status"]), dependency, label)
                if resolved is not None:
                    reference_controls[label] = resolved
                    break
                if time.monotonic() - began > plan["maximum_wait_seconds"]:
                    raise TimeoutError("Deferred control audit observation window expired")
                time.sleep(10)
        references = {
            **reference_controls,
            **{
                arm: {"checkpoint": item, "audit": audited_state["result"]}
                for arm, item in checkpoints.items()
            },
        }
        contrasts, began = {}, time.monotonic()
        for left, right in plan["contrasts"]:
            label = left + "-" + right
            record("joining-audited-primary-and-native-crops", contrast=label)
            reference = references[left]
            old_audit = read_bound(reference["audit"])
            if live(old_audit["owner"]) or old_audit["new_neural_forwards"]:
                raise ValueError("Control audit is not complete")
            old_boundary = read_bound(old_audit["completed_evaluation"])
            old_sha, new_sha = reference["checkpoint"]["sha256"], checkpoints[right]["sha256"]
            directory = output / label
            statistics = compare(
                reference["audit"]["path"],
                audited_state["result"]["path"],
                old_sha,
                new_sha,
                directory,
                expected_observations=plan["expected_observations"],
            )
            if (
                sum(
                    read_bound(item)["matched_observations"]
                    for item in statistics["stages"].values()
                )
                != 14190
            ):
                raise ValueError("Numerical contrast support differs")
            labels = (left + " retained", right)
            materials = photo_comparison(
                matched_material_stage(
                    read_bound(statistics["stages"]["photo"]), directory / "matched-material-inputs"
                ),
                directory,
                labels=labels,
            )
            strict_gfx = [left, right] in plan.get("strict_gfx_contrasts", [])
            full_input_proof = None
            if strict_gfx:
                full_input_proof = matching_fullframe_inputs(
                    read_bound(old_boundary["stage_results"]["full-gfx"]),
                    read_bound(boundary["stage_results"]["full-gfx"]),
                    old_sha,
                    new_sha,
                )
            gfx = gfx_comparison(
                old_boundary["stage_results"]["full-gfx"]["path"],
                boundary["stage_results"]["full-gfx"]["path"],
                old_sha,
                new_sha,
                directory,
                labels=labels,
                allow_conditioning_difference=(
                    plan.get("allow_gfx_conditioning_difference", False) and not strict_gfx
                ),
            )
            if strict_gfx and not (gfx["conditioning_matched"] and gfx["tile_grid_matched"]):
                raise ValueError(
                    "Quota GFX comparison requires matching conditioning and tile grid"
                )
            if full_input_proof is not None:
                gfx["actual_fullframe_input_proof"] = full_input_proof
            photo = [
                read_bound(read_bound(a)["stages"]["photo"])
                for a in (reference["audit"], audited_state["result"])
            ]
            record("analyzing-full-local-photographic-detail", contrast=label)
            local_output = directory / "local-detail"
            local = analyze(
                photo[0]["manifest"]["path"],
                old_sha,
                photo[1]["manifest"]["path"],
                new_sha,
                local_output,
                expected_images=427,
                maximum_seconds=600,
            )
            if (
                local["paired_source_noise_CFA_observations"] != 5124
                or local["unique_source_blocks"] != 96075
            ):
                raise ValueError("Local photographic support differs")
            contrasts[label] = {
                "labels": labels,
                "control_sha256": old_sha,
                "candidate_sha256": new_sha,
                "statistics": binding(directory / "result.json"),
                "materials": materials,
                "gfx": gfx,
                "local_detail": binding(local_output / "result-v1.json"),
            }
            state["completed"][label] = {
                k: contrasts[label][k] for k in ("statistics", "local_detail")
            }
            record("completed-saved-output-contrast", contrast=label)
            if (
                time.monotonic() - began > 3600
                or psutil.virtual_memory().available < 8 * 2**30
                or shutil.disk_usage(root).free < 4 * 2**30
            ):
                raise RuntimeError("Comparison resource bound reached; retained work preserved")
        if "torch" in sys.modules:
            raise RuntimeError("Comparison unexpectedly imported Torch")
        guard(plan)
        write(
            root / "result-v1.json",
            {
                "queue_plan": binding(path),
                "owner": state["owner"],
                "original_audit": audited_state["result"],
                "completed_evaluation": audited["completed_evaluation"],
                "checkpoints": checkpoints,
                "references": reference_controls,
                "contrasts": contrasts,
                "GFX_conditioning_differences": [
                    label
                    for label, values in contrasts.items()
                    if not values["gfx"]["conditioning_matched"]
                ],
                "RGB16_export_verification": exports,
                "new_neural_forwards": 0,
                "new_encoder_forwards": 0,
                "optimizer_updates": 0,
                "new_noise_observations": 0,
                "RAW_decodes": 0,
                "Torch_imported": False,
                "native_review": "Native160 images prepared; actual viewing and fine green mesh pending",
                "scope": plan["scope"],
            },
        )
        record(TERMINAL, result=binding(root / "result-v1.json"))
    except BaseException as error:
        record("failed-quality-comparison-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--audit-plan", type=Path)
    parser.add_argument("--specification", type=Path)
    args = parser.parse_args()
    if args.mode == "controller":
        controller(args.path.resolve())
    else:
        spec = json.loads(args.specification.read_text())
        print(
            prepare(
                args.path,
                args.audit_plan,
                spec["references"],
                spec["new_arms"],
                spec["contrasts"],
                allow_gfx_conditioning_difference=spec.get(
                    "allow_gfx_conditioning_difference", False
                ),
            )
        )
