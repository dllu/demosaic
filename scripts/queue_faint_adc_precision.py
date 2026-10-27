"""Declare and collect a new heldout faint-photographic ADC precision panel."""

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import numpy as np
import psutil
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / ".cache/current-quality-20261023-v1"
PATTERNS = {"RGGB": (0, 1, 1, 2), "BGGR": (2, 1, 1, 0), "GRBG": (1, 0, 2, 1), "GBRG": (1, 2, 0, 1)}
NAMES = ("packed", "variance", "colors", "wb", "matrix")


def faint_target(original):
    """Preserve each camera channel's spatial DC; reduce deviations to2.5%."""
    value = np.asarray(original, np.float64)
    if value.shape != (1, 3, 256, 256) or not np.isfinite(value).all():
        raise ValueError("Use one finite native256 camera-RGB target")
    mean = value.mean((-1, -2), keepdims=True)
    return (mean + 0.025 * (value - mean)).astype(np.float32)


def adc_observation(target, pattern):
    """Fixed16-bit ADC/black.03, FP64 code selection then FP32 dequantization."""
    colors = PATTERNS[pattern]
    value = np.asarray(target, np.float64)
    phases = np.stack(
        [
            value[:, c, y::2, x::2]
            for c, (y, x) in zip(colors, ((0, 0), (0, 1), (1, 0), (1, 1)), strict=True)
        ],
        axis=1,
    )
    codes = np.rint((phases * 0.97 + 0.03).clip(0, 1) * 65535)
    packed = ((codes / 65535 - 0.03) / 0.97).astype(np.float32)
    return packed, np.zeros_like(packed), np.asarray([colors], dtype=np.int64)


def fingerprint(value):
    import hashlib

    return {
        "shape": list(value.shape),
        "dtype": value.dtype.str,
        "sha256": hashlib.sha256(value.tobytes()).hexdigest(),
    }


def prepare(root):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("Preparation is CPU-only, without neural/noise work")
    source_path = BASE / "conditional-noise-response-v1/plan-v1.json"
    source = read(source_path)
    guard(source)
    training_path = BASE / "fp32-training-pilot-v1/run/plan.json"
    training = read(training_path)
    guard(training)
    status = read(Path(training["root"]) / "status.json")
    assert status["plan"] == ref(training_path) and live(status["controller"])
    assert status["phase"] == "train" and live(status["child"])
    control_path = BASE / "reviewed-detail-training-pilot-v1/run/train-V129-result.json"
    control = read(control_path)
    assert (
        control["updates"] == 1000
        and control["model_EMA_Adam_finite"]
        and not live(control["owner"])
    )
    assert ref(control["checkpoint"]["path"]) == control["checkpoint"]
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    controller_path = root / "controller.py"
    shutil.copyfile(__file__, controller_path)
    for helper in ("train_directional_bank_trial.py", "train_v43_quality_trial.py"):
        shutil.copyfile(REPO / "scripts" / helper, root / helper)
    work = root / "inputs"
    work.mkdir()
    cases, observations, inputs = [], [], [ref(source_path), ref(training_path), ref(control_path)]
    for original in source["cases"]:
        assert ref(original["target"]["path"]) == original["target"]
        with np.load(original["target"]["path"], allow_pickle=False) as archive:
            values = {k: archive[k].copy() for k in ("target", "wb", "matrix")}
        values["target"] = faint_target(values["target"])
        identity = original["id"] + "-contrast0p025-adc"
        target_path = work / (identity + "-target.npz")
        np.savez(target_path, **values)
        case = {
            **original,
            "id": identity,
            "original_case_id": original["id"],
            "original_target": original["target"],
            "target": ref(target_path),
            "additional_contrast_factor": 0.025,
            "contrast_operator": "Per-camera-channel whole256x256 spatial DC plus.025 times deviations, FP64 then FP32; no spatial interpolation.",
        }
        cases.append(case)
        inputs += [original["target"], ref(target_path)]
        for pattern in PATTERNS:
            packed, variance, colors = adc_observation(values["target"], pattern)
            arrays = {
                "packed": packed,
                "variance": variance,
                "colors": colors,
                "wb": values["wb"],
                "matrix": values["matrix"],
            }
            path = work / f"{identity}-{pattern}.npz"
            np.savez(path, **arrays)
            observations.append(
                {
                    "id": f"{identity}-{pattern}",
                    "kind": "material",
                    "case_id": identity,
                    "original_case_id": original["id"],
                    "case": case,
                    "source_id": original["source_id"],
                    "pattern": pattern,
                    "arrays": ref(path),
                    "target": ref(target_path),
                    "noise": {
                        "name": "adc-only",
                        "shot": 0.0,
                        "read": 0.0,
                        "ADC_bits": 16,
                        "black_level": 0.03,
                        "draws": 1,
                    },
                    "input_fingerprints": {k: fingerprint(v) for k, v in arrays.items()},
                    "output_shape": [1, 3, 256, 256],
                    "ROI_xywh": [48, 48, 160, 160],
                    "display_exposure": 1.0,
                    "reference_role": case["reference_role"],
                    "controls": [],
                }
            )
            inputs.append(ref(path))
    assert len(cases) == 4 and len(observations) == 16
    baseline = next(m for m in source["methods"] if m["label"] == "V120")
    methods = {
        "V120": {
            "checkpoint": baseline["checkpoint"],
            "step": 20000,
            "expected_lineage": baseline["expected_lineage"]["initialized_from"],
            "expected_full_model_sha256": baseline["expected_full_model_sha256"],
        },
        "V129": {
            "checkpoint": control["checkpoint"],
            "step": 1000,
            "expected_lineage": {**training["parent"], "step": 20000},
        },
        "V130": {"step": 1000, "expected_lineage": {**training["parent"], "step": 20000}},
    }
    script_names = (
        "collect_retained_checkpoint_pilot.py",
        "report_checkpoint_pilot.py",
        "audit_checkpoint_pilot.py",
        "train_directional_bank_trial.py",
        "train_v43_quality_trial.py",
        "frozen_backbone_identity.py",
        "profile_raw_kernel_inference.py",
    )
    for label in methods:
        destination = root / label / "work"
        (destination / "scripts").mkdir(parents=True)
        shutil.copytree(
            REPO / "src", destination / "src", ignore=shutil.ignore_patterns("__pycache__")
        )
        for name in script_names:
            shutil.copyfile(REPO / "scripts" / name, destination / "scripts" / name)
    inputs += [baseline["checkpoint"], control["checkpoint"]]
    plan = {
        "root": str(root),
        "controller": ref(controller_path),
        "python": training["python"],
        "source_plan": ref(source_path),
        "training_plan": ref(training_path),
        "training_owner": status["controller"],
        "training_worker": status["child"],
        "absolute_training_deadline_unix": status["child"]["created"]
        + training["maximum_train_worker_seconds"],
        "cases": cases,
        "observations": observations,
        "methods": methods,
        "expected_backbone": baseline["expected_backbone"],
        "model_label": "V130 1k EMA",
        "planned_new_root_forwards_per_model": 16,
        "planned_new_root_forwards_total": 48,
        "planned_new_encoder_forwards_total": 48,
        "maximum_collector_seconds": 1200,
        "launch_RAM_GiB": 48,
        "runtime_RAM_GiB": 32,
        "CUDA_quota_GiB": 8,
        "launch_internal_reserve_GiB": 128,
        "runtime_internal_reserve_GiB": 96,
        "launch_external_reserve_GiB": 208,
        "runtime_external_reserve_GiB": 208,
        "inputs": inputs,
        "frozen_files": {str(p): ref(p)["sha256"] for p in root.rglob("*") if p.is_file()},
        "new_deterministic_ADC_observations": 16,
        "new_stochastic_noise_draws": 0,
        "RAW_decodes": 0,
        "automatic_retries": 0,
        "scope": "New heldout photographic faint-ADC panel:4 established material sources x4CFAs, each with a new DC-preserving.025 contrast operator and fixed FP64-code16bit ADC/black.03, no spatial interpolation.16 new IEEE FP32 calls each for V120/V129/V130,48 total. New inputs make V120 baseline calls necessary; no old inference repeated. V129/V130 use exact1000-update endpoints. No noise RNG/RAW/reference/optimizer work or inference fitting. Exact processed synthetic Commons targets distinguished from approximate binned native estimates. Four sources are not16 independent photos. Original training/86-call quality budgets unchanged; no automatic retry/reset. Independent preparation/metric/pixel and actual native review required.",
    }
    save(root / "plan-v1.json", plan)
    guard(plan)
    return root / "plan-v1.json"


def controller(path):
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    (root / "controller.claim").open("x").close()
    state = {
        "plan": ref(path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "completed": {},
    }
    child = owner = None

    def record(status, **details):
        state.update(status=status, updated_unix=time.time(), **details)
        save(root / "status.json", state)

    try:
        audit = read(root / "input-audit-v1.json")
        assert (
            audit["plan"] == ref(path)
            and audit["status"] == "passed-independent-faint-target-and-ADC-preparation-audit"
        )
        for label, specification in plan["methods"].items():
            spec = dict(specification)
            if label == "V130":
                record("waiting-for-original-V1301000-endpoint", child=None)
                while True:
                    assert time.time() < plan["absolute_training_deadline_unix"]
                    guard(plan)
                    training = read(plan["training_plan"]["path"])
                    current = read(Path(training["root"]) / "status.json")
                    assert (
                        current["plan"] == plan["training_plan"]
                        and current["controller"] == plan["training_owner"]
                    )
                    if current["status"].startswith("failed"):
                        raise RuntimeError("Original V130 training failed; preserve partial work")
                    if not live(plan["training_owner"]):
                        assert current["status"] == "completed-training-awaiting-model-comparisons"
                        assert current.get("child") is None or not live(current["child"])
                        binding = current["completed"]["train-V130"]
                        assert ref(binding["path"]) == binding
                        result = read(binding["path"])
                        assert result["updates"] == result["all_AdamW_steps"] == 1000
                        assert (
                            result["model_EMA_Adam_finite"]
                            and result["all_observed_inputs_match_saved_control"]
                        )
                        assert result["owner"] == plan["training_worker"] and not live(
                            result["owner"]
                        )
                        spec["checkpoint"] = result["checkpoint"]
                        break
                    time.sleep(15)
            assert ref(spec["checkpoint"]["path"]) == spec["checkpoint"]
            endpoint = root / label
            work = endpoint / "work"
            observations = []
            for original in plan["observations"]:
                controls = []
                for previous, binding in state["completed"].items():
                    collected = read(binding["path"])
                    row = next(r for r in collected["observations"] if r["id"] == original["id"])
                    controls.append(
                        {
                            "model": {
                                "label": previous if previous == "V120" else f"{previous} 1k EMA"
                            },
                            "prediction": row["prediction"],
                        }
                    )
                observations.append({**original, "controls": controls})
            execution = {
                **plan,
                **spec,
                "root": str(endpoint),
                "work": str(work),
                "model_label": label if label == "V120" else f"{label} 1k EMA",
                "observations": observations,
                "EMA_tensors": 91,
                "raw_frequency_features": False,
                "collector": ref(work / "scripts/collect_retained_checkpoint_pilot.py"),
                "planned_new_root_forwards": 16,
                "planned_new_encoder_forwards": 16,
                "inputs": [
                    *plan["inputs"],
                    ref(path),
                    spec["checkpoint"],
                    ref(root / "input-audit-v1.json"),
                    *state["completed"].values(),
                ],
            }
            execution_path = endpoint / "plan-v1.json"
            save(execution_path, execution)
            guard(execution)
            record("waiting-for-faint-ADC-headroom", label=label, child=None)
            began = time.monotonic()
            while psutil.virtual_memory().available < plan["launch_RAM_GiB"] * 2**30:
                assert time.monotonic() - began < 7200
                time.sleep(5)
            env = dict(
                os.environ,
                CUDA_VISIBLE_DEVICES="0",
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                OPENBLAS_NUM_THREADS="1",
                PYTHONPATH=f"{work / 'src'}:{work / 'scripts'}",
            )
            with (root / f"{label}.log").open("x") as log:
                child = subprocess.Popen(
                    [plan["python"], "-P", execution["collector"]["path"], str(execution_path)],
                    cwd=work,
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                record("collecting-new-faint-ADC-observations", label=label, child=owner)
                began = time.monotonic()
                while child.poll() is None:
                    assert time.monotonic() - began < plan["maximum_collector_seconds"]
                    time.sleep(2)
                assert child.wait() == 0, (label, child.returncode)
            binding = ref(endpoint / "collection-v1.json")
            collected = read(binding["path"])
            assert collected["plan"] == ref(execution_path) and collected["counts"] == {
                "root": 16,
                "encoder": 16,
            }
            assert collected["RNG_unchanged"] and not live(owner)
            state["completed"][label] = binding
            record("completed-new-faint-ADC-method", child=None)
        record("completed48-faint-ADC-forwards-awaiting-independent-and-native-review", child=None)
    except BaseException as error:
        if child is not None and child.poll() is None and live(owner):
            os.killpg(child.pid, signal.SIGINT)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                if live(owner):
                    os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
        record("failed-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "controller"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.path))
    else:
        controller(args.path.resolve())
