"""Queue two fixed-profile native fence comparisons for completed new endpoints."""

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
from audit_quality_archive import binding, write
from queue_quality_archive_audit import guard, live, read

REPO = Path(__file__).resolve().parents[1]
REPORT_TERMINAL = "completed-saved-quality-comparisons-native-viewing-pending"


def report_ready(state, dependency, *, is_live=live, terminal=REPORT_TERMINAL):
    if state["owner"] != dependency["owner"] or state["plan"] != dependency["plan"]:
        raise ValueError("Comparison queue identity differs")
    if state["status"].startswith("failed"):
        raise RuntimeError("Comparison failed; preserve its existing work")
    if is_live(dependency["owner"]):
        return False
    if state["status"] != terminal:
        raise RuntimeError("Comparison owner exited before completion")
    return True


def endpoint_methods(checkpoints, arms, suffix, *, adopted=()):
    if not arms or len(set(arms)) != len(arms):
        raise ValueError("Declare new mesh endpoints")
    if set(checkpoints) != set(arms) or len({v["sha256"] for v in checkpoints.values()}) != len(
        arms
    ):
        raise ValueError("Completed mesh endpoint coverage differs")
    labels = {arm + suffix: arm for arm in arms}
    adopted_labels = set()
    for method in adopted:
        label = method["label"]
        if (
            label not in labels
            or label in adopted_labels
            or method["kind"] != "checkpoint"
            or "prediction" not in method
            or method["checkpoint"]["sha256"] != checkpoints[labels[label]]["sha256"]
        ):
            raise ValueError("Adopted mesh endpoint differs from the completed checkpoint")
        adopted_labels.add(label)
    return [
        {
            "label": arm + suffix,
            "kind": "checkpoint",
            "checkpoint": checkpoints[arm],
            "expected_step": 20000,
        }
        for arm in arms
        if arm + suffix not in adopted_labels
    ]


def completed_endpoint_methods(result, expected_inputs, input_arrays, arms, suffix):
    """Adopt only a genuine completed endpoint forward on this exact observation."""
    if (
        result["inputs"] != expected_inputs
        or result["input_arrays"] != input_arrays
        or result["new_RAW_decodes"]
        or result["new_noise_observations"]
        or result["optimizer_updates"]
        or result["CUDA_initialized"]
        or not result["status"].startswith("completed-new-green-mesh-CPU-context-inference")
    ):
        raise ValueError("Completed endpoint mesh inputs or execution scope differ")
    allowed = {arm + suffix for arm in arms}
    selected = []
    seen = set()
    for method in result["methods"]:
        label = method["label"]
        if label in seen:
            raise ValueError("Duplicate completed mesh method")
        seen.add(label)
        if method["new_inference"] and label not in allowed:
            raise ValueError("Unexpected newly evaluated mesh endpoint")
        if label not in allowed:
            if method["actual_root_forwards"] or method["actual_encoder_forwards"]:
                raise ValueError("Retained controls must not have been rerun")
            continue
        if (
            method["kind"] != "checkpoint"
            or not method["new_inference"]
            or method["actual_root_forwards"] != 1
            or method["actual_encoder_forwards"] != 1
            or method["step"] != 20000
            or method["source_inputs_sha256"] != input_arrays["sha256"]
        ):
            raise ValueError("Adoption requires the original completed endpoint execution")
        selected.append(
            {
                key: method[key]
                for key in (
                    "label",
                    "kind",
                    "checkpoint",
                    "prediction",
                    "source_inputs_sha256",
                    "step",
                )
            }
        )
    if (
        not selected
        or result["new_root_forwards"] != len(selected)
        or result["new_encoder_forwards"] != len(selected)
    ):
        raise ValueError("Completed endpoint mesh accounting differs")
    return selected


def retained_profile_controls(result, inputs, arrays, source_arms, wanted_arms, suffix, references):
    """Select saved profile predictions only for the audited control weights."""
    selected = completed_endpoint_methods(result, inputs, arrays, source_arms, suffix)
    retained = []
    for arm in wanted_arms:
        matches = [method for method in selected if method["label"] == arm + suffix]
        if (
            len(matches) != 1
            or matches[0]["checkpoint"]["sha256"] != references[arm]["checkpoint"]["sha256"]
        ):
            raise ValueError("Retained mesh checkpoint differs from the audited control")
        retained.extend(matches)
    return retained


def prepare(
    root,
    comparison_plan,
    quality_plan,
    nominal,
    nearby,
    *,
    adopted=None,
    retained_endpoint_results=None,
    deferred_endpoint_plan=None,
    render_models=None,
    maximum_wait_seconds=432000,
):
    root = root.resolve()
    if not root.is_relative_to(REPO / ".cache"):
        raise ValueError("Mesh queues belong in the repository cache")
    comparison, quality = read(comparison_plan), read(quality_plan)
    guard(comparison)
    guard(quality)
    audit = read(comparison["dependency"]["plan"]["path"])
    if audit["quality_plan"] != binding(quality_plan):
        raise ValueError("Mesh models and comparison refer to different quality runs")
    state_path = Path(comparison["root"]) / "status.json"
    state = read(state_path)
    if state["plan"] != binding(comparison_plan) or state["status"].startswith("failed"):
        raise ValueError("Expected the original successful comparison queue")
    if not live(state["owner"]):
        report_ready(state, {"owner": state["owner"], "plan": binding(comparison_plan)})
    adopted = adopted or {}
    if set(adopted) - {"nominal", "profile3879"}:
        raise ValueError("Unknown adopted mesh profile")
    inputs = [binding(comparison_plan), binding(quality_plan)]
    retained_endpoint_results = retained_endpoint_results or {}
    if set(retained_endpoint_results) - {"nominal", "profile3879"}:
        raise ValueError("Unknown retained mesh profile")
    variants, records = [], []
    for name, path, labels, suffix in (
        ("nominal", nominal, {"V115", "V119", "RawNIND-preup"}, ""),
        ("profile3879", nearby, {"V115-profile3879", "V119-profile3879"}, "-profile3879"),
    ):
        result = read(path)
        inputs += [binding(path), result["inputs"]]
        metadata = read(result["inputs"]["path"])
        records.append(metadata)
        retained = [
            {
                key: method[key]
                for key in ("label", "kind", "checkpoint", "prediction", "source_inputs_sha256")
            }
            for method in result["methods"]
            if method["label"] in labels
        ]
        if {m["label"] for m in retained} != labels or len(retained) != len(labels):
            raise ValueError("Missing retained mesh controls")
        if any(m["source_inputs_sha256"] != metadata["input_arrays"]["sha256"] for m in retained):
            raise ValueError("Retained control conditioning differs")
        inputs += [metadata["input_arrays"], metadata["derived_selection"]]
        inputs += [m["prediction"] for m in retained]
        for entry in retained_endpoint_results.get(name, []):
            source = entry["result"]
            if binding(source["path"]) != source:
                raise ValueError("Retained endpoint mesh receipt changed")
            selected = retained_profile_controls(
                read(source["path"]),
                result["inputs"],
                metadata["input_arrays"],
                entry["arms"],
                entry["arms"],
                suffix,
                comparison["references"],
            )
            retained.extend(selected)
            inputs.extend(
                [source, *[m[key] for m in selected for key in ("prediction", "checkpoint")]]
            )
        if len({m["label"] for m in retained}) != len(retained):
            raise ValueError("Retained mesh labels must be distinct")
        for case in metadata["cases"]:
            if case["ROI_xywh"][2:] != [160, 160]:
                raise ValueError("Mesh crops must retain native160 pixels")
            inputs.extend(item["pixels"] for item in case["camera_JPEGs"].values())
        endpoints = []
        adopted_result = None
        if name in adopted:
            adopted_result = binding(adopted[name])
            endpoints = completed_endpoint_methods(
                read(adopted[name]),
                result["inputs"],
                metadata["input_arrays"],
                comparison["new_arms"],
                suffix,
            )
            for method in endpoints:
                checkpoint = Path(method["checkpoint"]["path"])
                if checkpoint.is_symlink() or checkpoint.stat().st_mode & 0o222:
                    raise ValueError("Adopted mesh checkpoint must be an immutable copy")
            inputs.append(adopted_result)
            inputs.extend(m[key] for m in endpoints for key in ("prediction", "checkpoint"))
        variants.append(
            {
                "name": name,
                "inputs": result["inputs"],
                "retained_methods": retained,
                "adopted_methods": endpoints,
                "adopted_result": adopted_result,
                "new_label_suffix": suffix,
                "conditioning": metadata["conditioning"],
            }
        )
    if any(
        records[0][key] != records[1][key] for key in ("cases", "source_bindings", "registrations")
    ):
        raise ValueError("Mesh profile geometry or reference differs")
    deferred = None
    if deferred_endpoint_plan is not None:
        previous = read(deferred_endpoint_plan)
        guard(previous)
        previous_state_path = Path(previous["root"]) / "status.json"
        previous_state = read(previous_state_path)
        if (
            previous_state["plan"] != binding(deferred_endpoint_plan)
            or previous_state["status"].startswith("failed")
            or "V131" not in previous["new_arms"]
        ):
            raise ValueError("Expected original V131 mesh-control queue")
        if (
            not live(previous_state["owner"])
            and previous_state["status"] != "completed-new-mesh-predictions-native-viewing-pending"
        ):
            raise ValueError("Mesh-control queue exited before successful completion")
        if {v["name"]: v["inputs"] for v in previous["variants"]} != {
            v["name"]: v["inputs"] for v in variants
        }:
            raise ValueError("Deferred mesh-control observations differ")
        deferred = {
            "plan": binding(deferred_endpoint_plan),
            "status": str(previous_state_path),
            "owner": previous_state["owner"],
            "arms": ["V131"],
        }
        inputs.append(binding(deferred_endpoint_plan))
    rendered_models = list(render_models or comparison["new_arms"])
    if not rendered_models or len(set(rendered_models)) != len(rendered_models):
        raise ValueError("Require distinct mesh render models")
    for variant in variants:
        available = {m["label"] for m in variant["retained_methods"]}
        available |= {arm + variant["new_label_suffix"] for arm in comparison["new_arms"]}
        if deferred:
            available |= {arm + variant["new_label_suffix"] for arm in deferred["arms"]}
        if any(arm + variant["new_label_suffix"] not in available for arm in rendered_models):
            raise ValueError("Mesh render model has no declared prediction")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for source in (Path(quality["work"]) / "src/demosaic").glob("*.py"):
        target = work / "src/demosaic" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    helpers = (
        "queue_green_mesh_review.py",
        "queue_quality_archive_audit.py",
        "audit_quality_archive.py",
        "evaluate_gfx_green_mesh.py",
        "report_gfx_green_mesh_profiles.py",
        "prepare_gfx_green_mesh_inputs.py",
        "prepare_gfx_highlight_inputs.py",
    )
    for name in helpers:
        target = work / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "scripts" / name, target)
    for relative in (
        "third_party/dinov3/LICENSE.md",
        "third_party/gaussian/Noise2VST-LICENSE",
        "third_party/gaussian/KAIR-LICENSE",
    ):
        target = work / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / relative, target)
    inputs = list({(r["path"], r["sha256"]): r for r in inputs}.values())
    plan = {
        "root": str(root),
        "work": str(work),
        "python": sys.executable,
        "controller_source": binding(work / "scripts/queue_green_mesh_review.py"),
        "dependency": {
            "owner": state["owner"],
            "plan": binding(comparison_plan),
            "status": str(state_path),
        },
        "new_arms": comparison["new_arms"],
        "deferred_endpoint_controls": deferred,
        "render_models": rendered_models,
        "variants": variants,
        "model_source_quality_plan": binding(quality_plan),
        "planned_new_root_forwards": sum(
            len(comparison["new_arms"]) - len(v["adopted_methods"]) for v in variants
        ),
        "planned_new_encoder_forwards": sum(
            len(comparison["new_arms"]) - len(v["adopted_methods"]) for v in variants
        ),
        "planned_completed_endpoint_predictions_adopted": sum(
            len(v["adopted_methods"]) for v in variants
        ),
        "planned_retained_control_predictions_reused": (
            2 * len(deferred["arms"]) if deferred else 0
        )
        + sum(len(v["retained_methods"]) for v in variants),
        "maximum_wait_seconds": maximum_wait_seconds,
        "start_RAM_GiB": 48,
        "runtime_RAM_GiB": 32,
        "minimum_free_output_GiB": 4,
        "inputs": inputs,
        "frozen_files": {str(p): binding(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Completed declared endpoints only, CPU IEEE FP32/B1/native768, same saved DSCF3842 observation and independent DSCF3835 reference, two fixed existing noise profiles and two160px ROIs. Reuse selected controls and explicitly adopted completed endpoint predictions with zero NN, checking adopted checkpoint SHA against the final comparison. Native4EV boards/triplets; no RAW/noise regeneration, profile search, full-frame/speed/PSNR or automatic retry/promotion. Actual viewing remains pending.",
    }
    write(root / "queue-plan-v1.json", plan)
    guard(plan)
    return root / "queue-plan-v1.json"


def controller(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Mesh controller requires CPU; neural work belongs to explicit children")
    plan = read(path)
    guard(plan)
    if binding(__file__) != plan["controller_source"]:
        raise ValueError("Mesh controller source differs")
    os.nice(10)
    process = psutil.Process()
    process.cpu_affinity(process.cpu_affinity()[:2])
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "owner": {"pid": os.getpid(), "created": process.create_time()},
        "plan": binding(path),
        "completed": {},
    }
    child = child_owner = None

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        temporary = root / "status.tmp"
        temporary.write_text(json.dumps(state, indent=2, allow_nan=False) + "\n")
        temporary.replace(root / "status.json")

    def run(command, label):
        nonlocal child, child_owner
        began = time.monotonic()
        record("waiting-for-mesh-CPU-headroom", stage=label, child=None)
        while psutil.virtual_memory().available < plan["start_RAM_GiB"] * 2**30:
            if time.monotonic() - began > 7200:
                raise TimeoutError("Mesh resource observation window expired")
            time.sleep(5)
        guard(plan)
        env = dict(
            os.environ,
            PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
            CUDA_VISIBLE_DEVICES="",
            OPENBLAS_NUM_THREADS="1",
            OMP_NUM_THREADS="2",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
        )
        with (root / (label + ".log")).open("x") as log:
            child = subprocess.Popen(
                command,
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-explicit-mesh-child", stage=label, child=child_owner)
            began = time.monotonic()
            while child.poll() is None:
                if (
                    time.monotonic() - began > 1800
                    or psutil.virtual_memory().available < plan["runtime_RAM_GiB"] * 2**30
                    or shutil.disk_usage(root).free < plan["minimum_free_output_GiB"] * 2**30
                ):
                    raise RuntimeError("Mesh runtime bound reached; partial outputs preserved")
                time.sleep(2)
            if child.wait() != 0:
                raise RuntimeError(f"Mesh child failed: {label}; retained outputs are preserved")

    try:
        dependency = plan["dependency"]
        record(
            "waiting-for-completed-endpoint-comparisons", dependency=dependency["owner"], child=None
        )
        began = time.monotonic()
        while not report_ready(read(dependency["status"]), dependency):
            if time.monotonic() - began > plan["maximum_wait_seconds"]:
                raise TimeoutError("Comparison observation window expired")
            time.sleep(10)
        completed = read(dependency["status"])
        result = read(completed["result"]["path"])
        if (
            binding(completed["result"]["path"]) != completed["result"]
            or result["owner"] != dependency["owner"]
        ):
            raise ValueError("Completed comparison evidence differs")
        checkpoints = result["checkpoints"]
        saved_result = saved_plan = saved_binding = None
        if saved := plan.get("deferred_endpoint_controls"):
            record("waiting-for-original-retained-mesh-controls", child=None)
            while not report_ready(
                read(saved["status"]),
                saved,
                terminal="completed-new-mesh-predictions-native-viewing-pending",
            ):
                if time.monotonic() - began > plan["maximum_wait_seconds"]:
                    raise TimeoutError("Retained mesh-control observation window expired")
                time.sleep(10)
            saved_state = read(saved["status"])
            saved_binding = saved_state["result"]
            if binding(saved_binding["path"]) != saved_binding:
                raise ValueError("Retained mesh-control result changed")
            saved_result = read(saved_binding["path"])
            if saved_result["owner"] != saved["owner"]:
                raise ValueError("Retained mesh-control producer differs")
            saved_plan = read(saved["plan"]["path"])
            guard(saved_plan)
        reports = {}
        for variant in plan["variants"]:
            adopted = variant.get("adopted_methods", [])
            retained = list(variant["retained_methods"])
            if saved_result is not None:
                saved_stage = saved_result["reports"][variant["name"]]
                if binding(saved_stage["path"]) != saved_stage:
                    raise ValueError("Retained mesh profile result changed")
                metadata = read(variant["inputs"]["path"])
                selected = retained_profile_controls(
                    read(saved_stage["path"]),
                    variant["inputs"],
                    metadata["input_arrays"],
                    saved_plan["new_arms"],
                    saved["arms"],
                    variant["new_label_suffix"],
                    result["references"],
                )
                retained.extend(selected)
            if len({m["label"] for m in retained}) != len(retained):
                raise ValueError("Resolved retained mesh controls duplicate labels")
            methods = endpoint_methods(
                checkpoints, plan["new_arms"], variant["new_label_suffix"], adopted=adopted
            )
            for method in methods:
                checkpoint = method["checkpoint"]
                p = Path(checkpoint["path"])
                if binding(p) != checkpoint or p.is_symlink() or p.stat().st_mode & 0o222:
                    raise ValueError("Mesh requires the original immutable endpoint copy")
            stage_plan = root / (variant["name"] + "-evaluation-plan-v1.json")
            write(
                stage_plan,
                {
                    "inputs": variant["inputs"],
                    "methods": [*retained, *adopted, *methods],
                },
            )
            output = work / "artifacts" / variant["name"]
            run(
                [
                    plan["python"],
                    "-P",
                    str(work / "scripts/evaluate_gfx_green_mesh.py"),
                    str(stage_plan),
                    str(output),
                ],
                variant["name"],
            )
            report = read(output / "result-v1.json")
            if report["new_root_forwards"] != len(methods) or report["new_encoder_forwards"] != len(
                methods
            ):
                raise ValueError("Mesh neural-call count differs")
            if (
                report["new_RAW_decodes"]
                or report["new_noise_observations"]
                or report["CUDA_initialized"]
            ):
                raise ValueError("Mesh exceeded its declared input/runtime scope")
            for method in report["methods"]:
                if method["label"] in {m["label"] for m in [*retained, *adopted]} and (
                    method["new_inference"]
                    or method["actual_root_forwards"]
                    or method["actual_encoder_forwards"]
                ):
                    raise ValueError("Retained mesh prediction was rerun")
            reports[variant["name"]] = binding(output / "result-v1.json")
            state["completed"][variant["name"]] = reports[variant["name"]]
            record("completed-new-endpoint-mesh-profile", child=None)
        rendering = work / "artifacts/native4EV"
        run(
            [
                plan["python"],
                "-P",
                str(work / "scripts/report_gfx_green_mesh_profiles.py"),
                reports["nominal"]["path"],
                reports["profile3879"]["path"],
                str(rendering),
                "--models",
                *plan.get("render_models", plan["new_arms"]),
            ],
            "native4EV",
        )
        guard(plan)
        write(
            root / "result-v1.json",
            {
                "owner": state["owner"],
                "queue_plan": binding(path),
                "completed_comparisons": completed["result"],
                "checkpoints": checkpoints,
                "reports": reports,
                "retained_endpoint_control_result": saved_binding,
                "native_manifest": binding(rendering / "manifest.json"),
                "new_root_forwards": plan["planned_new_root_forwards"],
                "new_encoder_forwards": plan["planned_new_encoder_forwards"],
                "retained_control_predictions_reused": plan[
                    "planned_retained_control_predictions_reused"
                ],
                "completed_endpoint_predictions_adopted": plan.get(
                    "planned_completed_endpoint_predictions_adopted", 0
                ),
                "new_RAW_decodes": 0,
                "new_noise_observations": 0,
                "optimizer_updates": 0,
                "controller_Torch_imported": "torch" in sys.modules,
                "native_review": "Native160 boards/triplets prepared; actual viewing and pixel audit remain pending",
                "scope": plan["scope"],
            },
        )
        record(
            "completed-new-mesh-predictions-native-viewing-pending",
            result=binding(root / "result-v1.json"),
            child=None,
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
        record("failed-mesh-review-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--comparisons", type=Path)
    parser.add_argument("--quality", type=Path)
    parser.add_argument("--nominal", type=Path)
    parser.add_argument("--nearby", type=Path)
    parser.add_argument("--adopted-nominal", type=Path)
    parser.add_argument("--adopted-nearby", type=Path)
    args = parser.parse_args()
    if args.mode == "controller":
        controller(args.path.resolve())
    else:
        adopted = {
            name: path
            for name, path in (
                ("nominal", args.adopted_nominal),
                ("profile3879", args.adopted_nearby),
            )
            if path is not None
        }
        print(
            prepare(
                args.path,
                args.comparisons,
                args.quality,
                args.nominal,
                args.nearby,
                adopted=adopted,
            )
        )
