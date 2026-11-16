"""Evaluate V131 with the byte-preserved V120 primary numerical pipeline."""

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as f:
        return {"path": str(path), "sha256": hashlib.file_digest(f, "sha256").hexdigest()}


def checked(binding):
    if ref(binding["path"])["sha256"] != binding["sha256"]:
        raise ValueError("Bound broad-evaluation artifact changed")
    return Path(binding["path"])


def write(path, data, *, replace=False):
    path = Path(path)
    temp = path.with_name("." + path.name + ".tmp")
    with temp.open("x") as f:
        json.dump(data, f, indent=2, allow_nan=False)
        f.write("\n")
    try:
        if replace:
            temp.replace(path)
        else:
            os.link(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def prepare(root):
    import torch

    repo = Path.cwd()
    old = repo / ".cache/current-quality-20261023-v1/V120-V121-paired32-weak-detail-quality-v1"
    original = read(old / "evaluation-plan-v1.json")
    checkpoint = (
        repo / ".cache/experiments/raw-spatial-continuation-v2/work/artifacts/train/V131/last.pt"
    )
    binding = ref(checkpoint)
    if binding["sha256"] != "4d78e6302f6e72d68acb03fe58eb7106763b8129ccb059747ef5d2cfbd3ec1e1":
        raise ValueError("Require the completed V131 endpoint")
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if state["step"] != 20000 or len(state["ema"]) != 91:
        raise ValueError("V131 step/EMA coverage differs")
    disabled = {"raw_frequency_features": False, "raw_spatial_features": False}
    if any(state["model_config"].get(k) is not False for k in disabled):
        raise ValueError("Historical runtime only supports these branches disabled")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    files = {}
    for source, digest in original["frozen_files"].items():
        p = checked({"path": source, "sha256": digest})
        target = work / p.relative_to(Path(original["work"]))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        files[str(target)] = digest
    wrapper = work / "scripts" / Path(__file__).name
    shutil.copyfile(__file__, wrapper)
    files[str(wrapper)] = ref(wrapper)["sha256"]
    stages = {}
    for name in ["photo", "known", "unseen", "texture", "color"]:
        item = {**original["stages"][name], "output": str(work / "artifacts" / name)}
        if "protocol" in item:
            item["protocol"] = ref(
                work / Path(item["protocol"]["path"]).relative_to(Path(original["work"]))
            )
        stages[name] = item
    (work / "artifacts").mkdir()
    endpoint = repo / ".cache/experiments/raw-spatial-endpoint-review-v3"
    queue = read(endpoint / "queue-plan.json")
    collection = read(endpoint / "V131/collection-v1.json")
    observations = {r["id"]: r for r in collection["observations"]}
    probes = []
    for name in ["bark-RGGB-draw0", "raccoon-fur-GRBG-draw0"]:
        row = next(r for r in queue["observations"] if r["id"] == name)
        probes.append(
            {
                "id": name,
                "arrays": row["arrays"],
                "input_fingerprints": row["input_fingerprints"],
                "saved_V131": observations[name]["prediction"],
                "noise": row["noise"],
            }
        )
    inputs = [
        ref(old / "evaluation-plan-v1.json"),
        binding,
        ref(endpoint / "queue-plan.json"),
        ref(endpoint / "V131/collection-v1.json"),
    ]
    for stage in stages.values():
        inputs.extend(stage[k] for k in ["manifest", "protocol", "input_witness"] if k in stage)
    inputs.append(original["color_inputs"])
    inputs.extend(r[k] for r in probes for k in ["arrays", "saved_V131"])
    controls = {}
    for name in stages:
        result = old / "work/artifacts" / name / "result.json"
        value = read(result)
        controls[name] = {
            "result": ref(result),
            "report": value["report"],
            "archive": value["archive"],
        }
        inputs.extend(controls[name].values())
    plan = {
        "root": str(root),
        "work": str(work),
        "python": sys.executable,
        "wrapper": ref(wrapper),
        "collector_source": ref(work / "scripts/collect_quality_predictions.py"),
        "stages": stages,
        "checkpoints": [
            {
                **binding,
                "arm": "V131",
                "expected_lineage": {
                    "step": 20000,
                    "initialized_from": state["config"]["initialized_from"],
                },
                "expected_backbone": original["checkpoints"][0]["expected_backbone"],
            }
        ],
        "disabled_model_config_fields": disabled,
        "probes": probes,
        "compatibility_tolerance_camera_DN16": 0.25,
        "compatibility_RMS_tolerance_camera_DN16": 0.025,
        "compatibility_rule_reason": "The initial arbitrary0.01DN16 maximum rejected cross-session FP32/layout/kernel rounding (0.03906DN16 max after matching channels_last). Two implementations are byte-identical within one process under both convolution policies, with exact91 EMA/backbone tensors. Use explicit quarter-output-DN maximum and one-fortieth-DN RMS precision bounds; record actual differences. These are numerical compatibility bounds, not image-quality gates. All failed attempts remain preserved; no checkpoint or neural operation changes.",
        "shared_checkpoint_cache": str(work / "artifacts/checkpoint-cache"),
        "material_photo_ids": original["material_photo_ids"],
        "color_inputs": original["color_inputs"],
        "runtime_external_reserve_GiB": 96,
        "runtime_internal_reserve_GiB": 128,
        "existing_controls": controls,
        "planned_panel_forwards": sum(s["calls_per_model"] for s in stages.values()),
        "planned_panel_observations": sum(s["observations_per_model"] for s in stages.values()),
        "inputs": list({(b["path"], b["sha256"]): b for b in inputs}.values()),
        "frozen_files": files,
        "scope": "One completed V13120k EMA; same byte-preserved historical V120 primary model/observation/metric pipeline. Adapter removes only two explicitly disabled, unsupported model-config flags; checkpoint bytes and91 EMA tensors unchanged. Two saved-V131 compatibility probes precede all4450 panel forwards/14190 observations. All original argument/target witnesses enforced, including443 photo+procedural inputs and427-photo source-balanced reporting. Existing V120/V121 controls reused without forwards. No GFX/RAW work or training signals. All new writes/checkpoint cache internal, with128GiB internal/96GiB external/32GiB runtimeRAM reserves,48GiB at stage entry. Concurrent V132 training may affect timing, not the declared20k horizon.",
    }
    plan["previous_failed_attempts"] = []
    for version in [1, 2, 3, 4]:
        previous = repo / f".cache/experiments/v131-broad-primary-v{version}"
        if previous != root and (previous / "status.json").exists():
            failure = read(previous / "status.json")
            if not failure["status"].startswith("failed-owned-"):
                raise ValueError("The previous declared broad attempt is not terminal")
            bindings = {
                name: ref(previous / name)
                for name in ["plan.json", "status.json", "compatibility.log"]
            }
            bindings.update(
                {
                    name: ref(previous / name)
                    for name in ["compatibility.json", "photo.log"]
                    if (previous / name).exists()
                }
            )
            plan["previous_failed_attempts"].append(bindings)
            plan["inputs"].extend(bindings.values())
    diagnostic = repo / ".cache/experiments/v131-primary-runtime-diagnostic-v1/result.json"
    d = read(diagnostic)
    if not d["all_EMA_backbone_tensors_exact"] or not all(
        r["old_new_bit_exact"] and all(r["repeat_bit_exact"]) for r in d["rows"]
    ):
        raise ValueError("Historical/native same-process implementation diagnostic failed")
    plan["runtime_diagnostic"] = ref(diagnostic)
    plan["inputs"].append(plan["runtime_diagnostic"])
    plan["compatibility_model_memory_format"] = (
        "channels_last, as in saved targeted review and primary evaluator"
    )
    if not Path(plan["shared_checkpoint_cache"]).is_relative_to(work) or any(
        not Path(s["output"]).is_relative_to(work) for s in stages.values()
    ):
        raise ValueError("Historical evaluator writes must remain inside its frozen work root")
    write(root / "plan.json", plan)
    return root / "plan.json"


def install_metadata_adapter(plan):
    from demosaic.model import ModelConfig

    original = ModelConfig.from_checkpoint
    fields = set(ModelConfig.__dataclass_fields__) | {"baseline_fp32"}

    def parse(cls, values):
        extras = {k: v for k, v in values.items() if k not in fields}
        if extras != plan["disabled_model_config_fields"] or any(
            v is not False for v in extras.values()
        ):
            raise ValueError("Unsupported or enabled feature in historical-runtime checkpoint")
        return original({k: v for k, v in values.items() if k in fields})

    ModelConfig.from_checkpoint = classmethod(parse)


def worker(root, phase):
    import numpy as np
    import psutil
    import torch
    from collect_quality_predictions import (
        collect,
        model_hash,
        strict_float32,
        verify_recorded_backbone,
    )
    from train_directional_bank_trial import guard

    from demosaic.inference import load_checkpoint
    from demosaic.prediction_archive import fingerprint

    plan = read(root / "plan.json")
    guard(plan)
    if ref(__file__) != plan["wrapper"] or psutil.virtual_memory().available < 48 * 2**30:
        raise RuntimeError("Require frozen source and stage-entry reserve")
    os.nice(10)
    install_metadata_adapter(plan)
    if phase != "compatibility":
        collect(root / "plan.json", phase)
        return
    (root / "compatibility.claim").open("x").close()
    torch.set_num_threads(4)
    strict_float32()
    torch.backends.cudnn.benchmark = True
    with torch.inference_mode():
        model, state = load_checkpoint(checked(plan["checkpoints"][0]), device="cuda")
        model.eval().requires_grad_(False).to(memory_format=torch.channels_last)
        if (
            state["loaded_sha256"] != plan["checkpoints"][0]["sha256"]
            or len(model.restoration_state_dict()) != 91
        ):
            raise ValueError("Unexpected compatibility model")
        for key, value in model.restoration_state_dict().items():
            if not torch.equal(value.cpu(), state["ema"][key]):
                raise ValueError("Historical model did not load the exact EMA")
        verify_recorded_backbone(model, plan["checkpoints"][0])
        before, records = model_hash(model), []
        for row in plan["probes"]:
            with np.load(checked(row["arrays"]), allow_pickle=False) as z:
                arrays = {k: z[k] for k in ["packed", "variance", "colors", "wb", "matrix"]}
            if {k: fingerprint(v) for k, v in arrays.items()} != row["input_fingerprints"]:
                raise ValueError("Compatibility inputs differ")
            model.set_noise(row["noise"]["shot"], row["noise"]["read"])
            prediction = (
                model(*[torch.from_numpy(v.copy()).cuda() for v in arrays.values()]).cpu().numpy()
            )
            saved = np.load(checked(row["saved_V131"]), allow_pickle=False)
            if (
                prediction.shape != saved.shape
                or prediction.dtype != np.float32
                or saved.dtype != np.float32
            ):
                raise ValueError("Compatibility native shape/dtype differs")
            delta = prediction.astype(np.float64) - saved.astype(np.float64)
            maximum = float(np.max(np.abs(delta)) * 65535)
            rms = float(np.sqrt(np.mean(delta**2)) * 65535)
            path = root / (row["id"] + "-compatibility.npy")
            with path.open("xb") as f:
                np.save(f, prediction, allow_pickle=False)
            if (
                not np.isfinite(prediction).all()
                or maximum > plan["compatibility_tolerance_camera_DN16"]
                or rms > plan["compatibility_RMS_tolerance_camera_DN16"]
            ):
                raise ValueError(
                    "Historical/current V131 outputs exceed the compatibility tolerance"
                )
            records.append(
                {
                    "case": row,
                    "prediction": ref(path),
                    "maximum_camera_DN16": maximum,
                    "RMS_camera_DN16": rms,
                    "bit_exact": prediction.tobytes() == saved.tobytes(),
                }
            )
        if model_hash(model) != before:
            raise ValueError("Compatibility probe mutated the model")
    write(
        root / "compatibility.json",
        {
            "plan": ref(root / "plan.json"),
            "records": records,
            "EMA_tensors_exact": 91,
            "new_V131_forwards": 2,
            "new_reference_forwards": 0,
            "scope": "Historical primary runtime with disabled-metadata adapter, compared to saved V131 targeted-review FP32 outputs. Any small numeric runtime difference is retained; no source/noise/RAW/optimizer work.",
        },
    )


def run(root):
    import psutil

    plan = read(root / "plan.json")
    (root / "run.claim").open("x").close()
    state = {
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(root / "plan.json"),
    }
    child, identity = None, None
    try:
        for phase in ["compatibility", *plan["stages"]]:
            if (
                psutil.virtual_memory().available < 48 * 2**30
                or shutil.disk_usage(root).free < 128 * 2**30
            ):
                raise RuntimeError("Broad-evaluation reserves unavailable")
            env = {
                **os.environ,
                "PYTHONPATH": plan["work"] + "/src:" + plan["work"] + "/scripts",
                "CUDA_VISIBLE_DEVICES": "0",
                "OPENBLAS_NUM_THREADS": "1",
                "OMP_NUM_THREADS": "4",
            }
            limit = 7200 if phase == "photo" else 1800
            with (root / (phase + ".log")).open("x") as log:
                child = subprocess.Popen(
                    [
                        plan["python"],
                        "-P",
                        plan["wrapper"]["path"],
                        "worker",
                        str(root),
                        "--phase",
                        phase,
                    ],
                    cwd=plan["work"],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
                identity = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
                state.update(
                    status="running-" + phase, child=identity, deadline_UTC_unix=time.time() + limit
                )
                write(root / "status.json", state, replace=True)
                if child.wait(timeout=limit):
                    raise RuntimeError(f"Owned broad {phase} exited {child.returncode}")
        state.update(
            status="completed-five-numerical-panels-awaiting-independent-audit", child=None
        )
        write(root / "status.json", state, replace=True)
    except BaseException as error:
        if child is not None and child.poll() is None:
            try:
                if psutil.Process(identity["pid"]).create_time() == identity["created"]:
                    os.killpg(child.pid, signal.SIGINT)
                    child.wait(timeout=30)
            except psutil.Error:
                pass
        state.update(
            status="failed-owned-broad-evaluation-preserved-no-automatic-retry",
            child=None,
            error=repr(error),
        )
        write(root / "status.json", state, replace=True)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run", "worker"])
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--phase", choices=["compatibility", "photo", "known", "unseen", "texture", "color"]
    )
    args = parser.parse_args()
    {"prepare": prepare, "run": run, "worker": lambda r: worker(r, args.phase)}[args.mode](
        args.root.resolve()
    )
