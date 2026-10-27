"""Queue new endpoint responses on stored noise draws, reusing old controls."""

import argparse
import ast
import gc
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import psutil
from report_conditional_noise_response import checked, validate_observations
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
QUALITY_TERMINAL = "completed-matched-endpoint-evaluation-awaiting-independent-and-native-review"
MESH_TERMINAL = "completed-new-mesh-predictions-native-viewing-pending"


class DisabledFrequencyFeature(ast.NodeTransformer):
    """Specialize only the added, disabled RAW-frequency feature to False/None."""

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load) and node.id == "raw_frequency_features":
            return ast.copy_location(ast.Constant(False), node)
        return node

    def visit_Attribute(self, node):
        if isinstance(node.ctx, ast.Load):
            if node.attr == "raw_frequency_features":
                return ast.copy_location(ast.Constant(False), node)
            if node.attr == "raw_frequency":
                return ast.copy_location(ast.Constant(None), node)
        return self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if isinstance(node.target, ast.Name) and node.target.id == "raw_frequency_features":
            if not isinstance(node.value, ast.Constant) or node.value.value is not False:
                raise ValueError("RAW-frequency default must remain disabled")
            return None
        return self.generic_visit(node)

    def visit_Assign(self, node):
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Attribute)
            and node.targets[0].attr == "raw_frequency"
        ):
            if not isinstance(node.value, ast.Constant) or node.value.value is not None:
                raise ValueError("Disabled RAW-frequency state must initialize to None")
            return None
        return self.generic_visit(node)

    def visit_arguments(self, node):
        keep, defaults = [], []
        for arg, default in zip(node.kwonlyargs, node.kw_defaults, strict=True):
            if arg.arg == "raw_frequency_features":
                if not isinstance(default, ast.Constant) or default.value is not False:
                    raise ValueError("RAW-frequency constructor default must be False")
            else:
                keep.append(arg)
                defaults.append(default)
        node.kwonlyargs, node.kw_defaults = keep, defaults
        return self.generic_visit(node)

    def visit_Call(self, node):
        node.keywords = [kw for kw in node.keywords if kw.arg != "raw_frequency_features"]
        node = self.generic_visit(node)
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "type"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and type(node.args[0].value) is bool
        ):
            return ast.copy_location(ast.Name(id="bool", ctx=ast.Load()), node)
        return node

    def visit_Compare(self, node):
        node = self.generic_visit(node)
        if len(node.ops) != 1 or not isinstance(node.ops[0], (ast.Is, ast.IsNot)):
            return node
        left, right = node.left, node.comparators[0]
        equal = None
        if isinstance(left, ast.Constant) and isinstance(right, ast.Constant):
            equal = left.value is right.value
        elif (
            isinstance(left, ast.Name)
            and isinstance(right, ast.Name)
            and left.id == right.id == "bool"
        ):
            equal = True
        if equal is None:
            return node
        return ast.copy_location(
            ast.Constant(equal if isinstance(node.ops[0], ast.Is) else not equal), node
        )

    def visit_BoolOp(self, node):
        node = self.generic_visit(node)
        neutral = isinstance(node.op, ast.And)
        values = []
        for value in node.values:
            if isinstance(value, ast.Constant) and type(value.value) is bool:
                if value.value is not neutral:
                    return value
            else:
                values.append(value)
        return (
            values[0]
            if len(values) == 1
            else ast.BoolOp(op=node.op, values=values)
            if values
            else ast.Constant(neutral)
        )

    def visit_If(self, node):
        node.test = self.visit(node.test)
        if isinstance(node.test, ast.Constant) and type(node.test.value) is bool:
            return [self.visit(n) for n in (node.body if node.test.value else node.orelse)]
        return self.generic_visit(node)


def specialized_source(source):
    tree = DisabledFrequencyFeature().visit(ast.parse(source))
    return ast.dump(tree, include_attributes=False)


def inference_compatibility(original_work, quality_work):
    training_only = {"train.py", "source_loss.py", "data.py", "raw_clean.py", "conditional_bias.py"}
    result = []
    for original in (original_work / "src/demosaic").glob("*.py"):
        if original.name in training_only:
            continue
        current = quality_work / "src/demosaic" / original.name
        if not current.exists():
            raise ValueError("An original inference source is missing")
        if original.read_bytes() == current.read_bytes():
            continue
        if original.name not in {"model.py", "pretrained_rgb.py"}:
            raise ValueError(f"Conditional inference source changed: {original.name}")
        before, after = (
            specialized_source(original.read_text()),
            specialized_source(current.read_text()),
        )
        if before != after:
            raise ValueError(f"Active inference mathematics changed: {original.name}")
        result.append(
            {
                "original": ref(original),
                "current": ref(current),
                "disabled_frequency_specialized_AST_sha256": hashlib.sha256(
                    before.encode()
                ).hexdigest(),
            }
        )
    return result


def dependency_ready(state, dependency, *, is_live=live):
    if (
        state["owner"] != dependency["owner"]
        or state[dependency["plan_field"]] != dependency["plan"]
    ):
        raise ValueError("Conditional-response dependency identity changed")
    if state["status"].startswith("failed"):
        raise RuntimeError("Dependency failed; preserve its existing work")
    if is_live(dependency["owner"]):
        return False
    if state["status"] != dependency["terminal"]:
        raise RuntimeError("Dependency owner exited before successful completion")
    if state.get("child") and is_live(state["child"]):
        raise RuntimeError("Dependency still has a live child")
    return True


def dependency(path, plan_field, terminal):
    plan = read(path)
    status_path = Path(plan["root"]) / "status.json"
    state = read(status_path)
    result = {
        "status": str(status_path),
        "plan": ref(path),
        "plan_field": plan_field,
        "owner": state["owner"],
        "terminal": terminal,
    }
    dependency_ready(state, result)
    return result


def completed_methods(evaluation, photo, arms):
    if not arms or len(arms) != len(set(arms)):
        raise ValueError("Declare distinct new endpoint labels")
    checkpoints = {row["arm"]: row for row in evaluation["checkpoints"]}
    invariants = {row["checkpoint"]["arm"]: row for row in photo["invariants"]}
    if len(checkpoints) != len(evaluation["checkpoints"]) or len(invariants) != len(
        photo["invariants"]
    ):
        raise ValueError("Duplicate full-quality checkpoint or execution records")
    if not set(arms) <= checkpoints.keys() or set(invariants) != checkpoints.keys():
        raise ValueError("Completed quality endpoints do not cover the requested models")
    result = []
    for arm in arms:
        checkpoint, invariant = checkpoints[arm], invariants[arm]
        if (
            invariant["checkpoint"] != checkpoint
            or checkpoint["expected_lineage"]["step"] != 20000
            or invariant["calls"] != 3108
            or invariant["encoder_calls"] != 3108
            or invariant["observations"] != 12404
        ):
            raise ValueError("Require the completed full endpoint and original photo execution")
        result.append(
            {
                "label": arm,
                "checkpoint": {k: checkpoint[k] for k in ("path", "sha256")},
                "expected_lineage": checkpoint["expected_lineage"],
                "expected_backbone": checkpoint["expected_backbone"],
                "expected_full_model_sha256": invariant["before"],
            }
        )
    if len({m["checkpoint"]["sha256"] for m in result}) != len(result):
        raise ValueError("New endpoint checkpoint identities must be distinct")
    return result


def prepare(root, quality_path, mesh_path, source, arms=None):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Queue preparation is CPU-only and cannot import Torch")
    root, source = root.resolve(), source.resolve()
    if not root.is_relative_to(REPO / ".cache"):
        raise ValueError("Conditional-response outputs belong in the repository cache")
    quality, mesh = read(quality_path), read(mesh_path)
    guard(quality)
    guard(mesh)
    if mesh["model_source_quality_plan"] != ref(quality_path):
        raise ValueError("Mesh and quality sources refer to different endpoints")
    arms = list(arms if arms is not None else mesh["new_arms"])
    if not arms or len(set(arms)) != len(arms) or not set(arms) <= set(mesh["new_arms"]):
        raise ValueError("New endpoint labels must come from the matched review")
    dependencies = [
        dependency(mesh_path, "plan", MESH_TERMINAL),
        dependency(quality_path, "queue_plan", QUALITY_TERMINAL),
    ]
    original = read(source / "plan-v1.json")
    guard(original)
    preparation = read(source / "input-preparation-v1.json")
    collection = read(source / "collection-v1.json")
    original_binding = ref(source / "plan-v1.json")
    if preparation["plan"] != original_binding or collection["plan"] != original_binding:
        raise ValueError("Retained observations and controls have different provenance")
    count = validate_observations(original["cases"], original["observations"])
    if count != 128 or collection["alignment"]["records"] != 256:
        raise ValueError("Expected the established four-target conditional-noise panel")
    compatibility = inference_compatibility(Path(original["work"]), Path(quality["work"]))
    if preparation["variance_values_independently_checked"] != 8388608:
        raise ValueError("Original independent input-variance proof is missing")
    exact_cases = [
        c["id"]
        for c in original["cases"]
        if c["reference_role"].startswith("Exact synthetic target")
    ]
    if len(exact_cases) != 2:
        raise ValueError("The conditional panel must retain its two exact synthetic targets")
    controls = original["methods"]
    if (
        collection["new_root_forwards"] != 256
        or [r["method"] for r in collection["methods"]] != controls
    ):
        raise ValueError("Retained controls do not match their original completed execution")
    if set(arms) & {m["label"] for m in controls}:
        raise ValueError("Already evaluated controls cannot be scheduled as new endpoints")
    inputs = [
        ref(quality_path),
        ref(mesh_path),
        original_binding,
        ref(source / "input-preparation-v1.json"),
        ref(source / "collection-v1.json"),
        ref(source / "analysis-v1.json"),
        collection["archive"],
    ]
    inputs += [o["arrays"] for o in original["observations"]]
    inputs += [c["target"] for c in original["cases"]]
    inputs += [binding for pair in compatibility for binding in (pair["original"], pair["current"])]
    for line in checked(collection["archive"]).read_text().splitlines():
        record = json.loads(line)
        inputs.extend((record["prediction"], record["supervision"]))
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for path in (Path(quality["work"]) / "src/demosaic").glob("*.py"):
        target = work / "src/demosaic" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        inputs.append(ref(path))
    helper = work / "src/demosaic/conditional_bias.py"
    if not helper.exists():
        shutil.copyfile(REPO / "src/demosaic/conditional_bias.py", helper)
    for name in (
        "queue_conditional_noise_response.py",
        "report_conditional_noise_response.py",
        "train_directional_bank_trial.py",
        "train_v43_quality_trial.py",
        "profile_raw_kernel_inference.py",
        "frozen_backbone_identity.py",
    ):
        target = work / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "scripts" / name, target)
    for name in (
        "third_party/dinov3/LICENSE.md",
        "third_party/gaussian/Noise2VST-LICENSE",
        "third_party/gaussian/KAIR-LICENSE",
    ):
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    plan = {
        "root": str(root),
        "work": str(work),
        "python": sys.executable,
        "controller_source": ref(work / "scripts/queue_conditional_noise_response.py"),
        "report_source": ref(work / "scripts/report_conditional_noise_response.py"),
        "quality_plan": ref(quality_path),
        "dependencies": dependencies,
        "source_plan": original_binding,
        "retained_archive": collection["archive"],
        "retained_methods": controls,
        "retained_control_inference_compatibility": compatibility,
        "new_arms": arms,
        "triplet_arms": arms,
        "cases": original["cases"],
        "observations": original["observations"],
        "noise": original["noise"],
        "exact_synthetic_cases": exact_cases,
        "observations_per_model": count,
        "planned_new_root_forwards": count * len(arms),
        "planned_new_encoder_forwards": count * len(arms),
        "retained_control_predictions": count * len(controls),
        "planned_native_exact_GT_triplets": 2 * len(arms),
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "reference_neural_forwards": 0,
        "optimizer_updates": 0,
        "automatic_retries": 0,
        "maximum_dependency_wait_seconds": 1209600,
        "maximum_headroom_wait_seconds": 7200,
        "maximum_collection_seconds": 7200,
        "maximum_analysis_seconds": 3600,
        "phase_start_RAM_GiB": 48,
        "runtime_RAM_GiB": 32,
        "CUDA_quota_GiB": 12,
        "phase_start_internal_free_GiB": 128,
        "runtime_internal_reserve_GiB": 96,
        "runtime_external_reserve_GiB": 208,
        "inputs": list({v["path"]: v for v in inputs}.values()),
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": (
            "Supplemental completed-endpoint bias/variance comparison after exact full quality/"
            "mesh owners exit successfully. Only new models run on128 already stored observations "
            "each;256 V120/V117 controls are reused without neural reruns. Four targets, four CFAs, "
            "eight draws; original noise/input/display/target protocol. Two native exact-synthetic-"
            "GT triplets per new endpoint and single/mean8 diagnostic boards. No reference NN, "
            "new noise, RAW, optimizer, automatic retry or promotion. Primary gains can be "
            "documented independently; this supplement is not a promotion gate."
        ),
    }
    path = root / "queue-plan-v1.json"
    save(path, plan)
    guard(plan)
    return path


def execution_plan(path):
    plan = read(path)
    guard(plan)
    for dep in plan["dependencies"]:
        if not dependency_ready(read(dep["status"]), dep):
            raise RuntimeError("Original dependency is still live")
    quality = read(plan["quality_plan"]["path"])
    state = read(Path(quality["root"]) / "status.json")
    if set(state["completed"]) != set(quality["stages"]):
        raise ValueError("Full endpoint quality stages are incomplete")
    evaluation_path = Path(quality["root"]) / "evaluation-plan-v1.json"
    evaluation = read(evaluation_path)
    guard(evaluation)
    photo_binding = state["completed"]["photo"]
    photo = read(checked(photo_binding))
    if live(photo["owner"]) or photo["plan"] != ref(evaluation_path):
        raise ValueError("Original photo result owner or plan differs")
    methods = completed_methods(evaluation, photo, plan["new_arms"])
    hashes = [m["expected_full_model_sha256"] for m in plan["retained_methods"] + methods]
    if len(set(hashes)) != len(hashes):
        raise ValueError(
            "A model state was already evaluated; review and adopt equivalent stored responses before scheduling neural work"
        )
    for method in methods:
        checkpoint = checked(method["checkpoint"])
        if checkpoint.is_symlink() or checkpoint.stat().st_mode & 0o222:
            raise ValueError("Conditional response requires immutable completed checkpoint copies")
    result = {
        **plan,
        "queue_plan": ref(path),
        "methods": methods,
        "inputs": [
            *plan["inputs"],
            ref(evaluation_path),
            photo_binding,
            *[m["checkpoint"] for m in methods],
            *[ref(d["status"]) for d in plan["dependencies"]],
        ],
    }
    target = Path(plan["root"]) / "execution-plan-v1.json"
    save(target, result)
    guard(result)
    return target


def collect(path):
    import torch
    from frozen_backbone_identity import verify_backbone_identity
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.prediction_archive import PredictionArchive, fingerprint

    plan = read(path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    if Path(load_checkpoint.__code__.co_filename).resolve().is_relative_to(work / "src") is False:
        raise RuntimeError("Model execution must use the actual frozen quality source")
    if ref(__file__) != plan["controller_source"] or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise RuntimeError("Unexpected conditional collector source or device")
    (root / "collect.claim").open("x").close()
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = True
    torch.cuda.set_per_process_memory_fraction(
        plan["CUDA_quota_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    cases = {case["id"]: case for case in plan["cases"]}
    archive = PredictionArchive(work / "artifacts/predictions")
    reports = []
    for method in plan["methods"]:
        model, state = load_checkpoint(checked(method["checkpoint"]), "cuda")
        if (
            state["step"] != 20000
            or state["config"]["initialized_from"] != method["expected_lineage"]["initialized_from"]
        ):
            raise ValueError("Loaded endpoint lineage differs")
        actual = model.restoration_state_dict()
        if (
            getattr(model.config, "raw_frequency_features", False)
            or getattr(model.pretrained_rgb, "raw_frequency", None) is not None
        ):
            raise ValueError("This comparison requires the unchanged V120-family operator")
        if len(actual) != 91 or any(
            not torch.equal(v.cpu(), state["ema"][k]) for k, v in actual.items()
        ):
            raise ValueError("Conditional collector did not load the exact completed EMA")
        verify_backbone_identity(
            model.config.to_dict(),
            model_hash(model.context.backbone),
            {"expected_backbone": method["expected_backbone"]},
            legacy_sha256=method["expected_backbone"]["sha256"],
        )
        del state, actual
        model.eval().to(memory_format=torch.channels_last)
        before = model_hash(model)
        if before != method["expected_full_model_sha256"]:
            raise ValueError(
                "Conditional endpoint differs from its original full quality evaluation"
            )
        counts = {"root": 0, "encoder": 0}
        witness = {}

        def pre_hook(module, args, _counts=counts, _witness=witness):
            if (
                module.training
                or torch.backends.cuda.matmul.allow_tf32
                or torch.backends.cudnn.allow_tf32
            ):
                raise RuntimeError("Conditional inference must remain single-view IEEE FP32")
            values = {
                k: fingerprint(v)
                for k, v in zip(("packed", "variance", "colors", "wb", "matrix"), args, strict=True)
            }
            if values != _witness["inputs"] or _counts["root"] >= plan["observations_per_model"]:
                raise ValueError("Actual conditional forward arguments/count differ")
            if psutil.virtual_memory().available < plan["runtime_RAM_GiB"] * 2**30:
                raise RuntimeError("Conditional collector memory reserve reached")

        def post_hook(module, args, value, _counts=counts):
            if (
                value.dtype != torch.float32
                or value.shape != (1, 3, 256, 256)
                or not torch.isfinite(value).all()
            ):
                raise ValueError("Invalid native conditional output")
            _counts["root"] += 1

        def encoder_hook(*args, _counts=counts):
            _counts["encoder"] += 1

        handles = [
            model.register_forward_pre_hook(pre_hook),
            model.register_forward_hook(post_hook),
            model.context.backbone.register_forward_hook(encoder_hook),
        ]
        model.set_noise(plan["noise"]["shot"], plan["noise"]["read"])
        with torch.inference_mode():
            for observed in plan["observations"]:
                with np.load(checked(observed["arrays"]), allow_pickle=False) as arrays:
                    cpu = {k: arrays[k] for k in arrays.files}
                expected = observed["input_fingerprints"]
                witness["inputs"] = expected
                if {k: fingerprint(v) for k, v in cpu.items()} != expected:
                    raise ValueError("Stored conditional input bytes differ")
                batch = {k: torch.from_numpy(v).to("cuda") for k, v in cpu.items()}
                prediction = model(
                    *(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix"))
                )
                with np.load(
                    checked(cases[observed["case_id"]]["target"]), allow_pickle=False
                ) as arrays:
                    target = arrays["target"]
                archive.append(
                    {
                        "label": method["label"],
                        "sha256": method["checkpoint"]["sha256"],
                        "step": 20000,
                        "self_ensemble": "none",
                    },
                    {
                        **observed,
                        "stage": "conditional-noise-response",
                        "ids": [observed["id"]],
                        "noise": plan["noise"],
                    },
                    prediction,
                    {"target": target, "wb": cpu["wb"], "matrix": cpu["matrix"]},
                )
        if (
            counts
            != {"root": plan["observations_per_model"], "encoder": plan["observations_per_model"]}
            or model_hash(model) != before
        ):
            raise ValueError("Conditional model state or actual counts changed")
        for handle in handles:
            handle.remove()
        reports.append({"method": method, **counts, "model_unchanged": True})
        del model
        gc.collect()
        torch.cuda.empty_cache()
    alignment = archive.verify_alignment()
    if alignment["records"] != plan["planned_new_root_forwards"] or alignment["models"] != len(
        plan["methods"]
    ):
        raise ValueError("Conditional prediction archive coverage differs")
    save(
        root / "collection-v1.json",
        {
            "plan": ref(path),
            "archive": ref(archive.manifest),
            "methods": reports,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "new_root_forwards": sum(r["root"] for r in reports),
            "new_encoder_forwards": sum(r["encoder"] for r in reports),
            "new_reference_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "optimizer_updates": 0,
            "alignment": alignment,
        },
    )
    guard(plan)


def controller(path):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Conditional queue controller is CPU-only")
    plan = read(path)
    guard(plan)
    if ref(__file__) != plan["controller_source"]:
        raise ValueError("Conditional controller source differs")
    root, work = Path(plan["root"]), Path(plan["work"])
    (root / "controller.claim").open("x").close()
    state = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(path),
        "completed": {},
    }
    child = child_owner = None

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    def run(command, phase, timeout):
        nonlocal child, child_owner
        record("waiting-for-conditional-response-headroom", phase=phase, child=None)
        began = time.monotonic()
        while (
            psutil.virtual_memory().available < plan["phase_start_RAM_GiB"] * 2**30
            or shutil.disk_usage(root).free < plan["phase_start_internal_free_GiB"] * 2**30
            or shutil.disk_usage("/mnt/external").free
            < plan["runtime_external_reserve_GiB"] * 2**30
        ):
            if time.monotonic() - began > plan["maximum_headroom_wait_seconds"]:
                raise TimeoutError("Conditional resource observation window expired")
            time.sleep(5)
        guard(plan)
        env = dict(
            os.environ,
            PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
            CUDA_VISIBLE_DEVICES="0" if phase == "collect" else "",
            OPENBLAS_NUM_THREADS="1",
            OMP_NUM_THREADS="2",
            HF_HUB_OFFLINE="1",
            TRANSFORMERS_OFFLINE="1",
        )
        with (root / f"{phase}-v1.log").open("x") as log:
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
            record("running-explicit-conditional-response-child", phase=phase, child=child_owner)
            began = time.monotonic()
            while child.poll() is None:
                if (
                    time.monotonic() - began > timeout
                    or psutil.virtual_memory().available < plan["runtime_RAM_GiB"] * 2**30
                    or shutil.disk_usage(root).free < plan["runtime_internal_reserve_GiB"] * 2**30
                    or shutil.disk_usage("/mnt/external").free
                    < plan["runtime_external_reserve_GiB"] * 2**30
                ):
                    raise RuntimeError("Conditional runtime reserve/window reached")
                time.sleep(2)
            if child.wait() != 0:
                raise RuntimeError(f"Conditional {phase} child failed; existing work preserved")

    try:
        began = time.monotonic()
        for dep in plan["dependencies"]:
            record("waiting-for-exact-endpoint-review-owner", dependency=dep["owner"], child=None)
            while True:
                try:
                    ready = dependency_ready(read(dep["status"]), dep)
                except (OSError, json.JSONDecodeError):
                    ready = False
                if ready:
                    break
                if time.monotonic() - began > plan["maximum_dependency_wait_seconds"]:
                    raise TimeoutError("Conditional dependency observation window expired")
                time.sleep(10)
        execution = execution_plan(path)
        run(
            [plan["python"], "-P", plan["controller_source"]["path"], "collect", str(execution)],
            "collect",
            plan["maximum_collection_seconds"],
        )
        actual = read(root / "collection-v1.json")
        if (
            actual["owner"] != child_owner
            or actual["new_root_forwards"] != plan["planned_new_root_forwards"]
        ):
            raise ValueError("Completed conditional collector owner/count differs")
        state["completed"]["collect"] = ref(root / "collection-v1.json")
        run(
            [
                plan["python"],
                "-P",
                plan["report_source"]["path"],
                str(execution),
                str(root / "collection-v1.json"),
            ],
            "analyze",
            plan["maximum_analysis_seconds"],
        )
        analysis = read(root / "analysis-v1.json")
        triplets = [i for i in analysis["images"] if i["kind"] == "single-triplet"]
        if len(triplets) != plan["planned_native_exact_GT_triplets"]:
            raise ValueError("Conditional report is missing its declared native GT triplets")
        state["completed"]["analyze"] = ref(root / "analysis-v1.json")
        record("completed-conditional-response-native-viewing-pending", child=None)
    except BaseException as error:
        if child is not None and child.poll() is None and child_owner and live(child_owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(child_owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-conditional-response-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execution", "controller", "collect"))
    parser.add_argument("path", type=Path)
    parser.add_argument("--quality", type=Path)
    parser.add_argument("--mesh", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--arms", nargs="+")
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path, args.quality, args.mesh, args.source, args.arms))
    elif args.mode == "execution":
        print(execution_plan(args.path))
    elif args.mode == "controller":
        controller(args.path)
    else:
        collect(args.path)
