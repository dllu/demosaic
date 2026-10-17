"""Evaluate the frozen color grid after the owned palette workflow exits.

Reuses the same observations for parent/control/wide; optional authors' RAW
reference stays FP32. This grid is diagnostic, not photographic/SOTA evidence.
"""

import argparse
import gc
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
import torch
from audit_colored_flats import metrics
from prepare_color_grid import sha, validate

from demosaic.cfa import malvar
from demosaic.inference import load_checkpoint
from demosaic.nonlocal_reference import CHECKPOINT_SHA256, load_nonlocal_reference
from demosaic.precision import amp_context
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def read(path):
    return json.loads(Path(path).read_text())


def completed(workflow):
    status = read(workflow)
    if status["status"] != "completed-first1000-and-evaluation-awaiting-manual-review":
        raise RuntimeError("Preceding palette evaluation incomplete; do not overlap or restart it")
    owner = status["controller"]
    try:
        p = psutil.Process(owner["pid"])
        if abs(p.create_time() - owner["created"]) < 0.01 and p.status() != psutil.STATUS_ZOMBIE:
            raise RuntimeError(f"Preceding palette owner remains live: PID{p.pid}")
    except psutil.NoSuchProcess:
        pass
    return status


def summarize(rows):
    grouped = defaultdict(list)
    for r in rows:
        grouped[
            r["model_index"], r["condition"], r["source"]["saturation"], r["source"]["peak"]
        ].append(r["metrics"])
    result = []
    for key, values in sorted(grouped.items()):
        measures = {
            "max_abs_channel_mean_error": [
                max(abs(x) for x in v["camera_RGB_mean_error"]) for v in values
            ],
            "camera_RGB_RMSE": [np.sqrt(v["camera_RGB_MSE"]) for v in values],
            "centered_camera_RGB_RMS": [v["spatially_centered_camera_RGB_RMS"] for v in values],
        }
        result.append(
            {
                "model_index": key[0],
                "condition": key[1],
                "saturation": key[2],
                "peak": key[3],
                "cases": len(values),
                "descriptive_metrics": {
                    name: {
                        "mean": float(np.mean(x)),
                        "median": float(np.median(x)),
                        "p95": float(np.quantile(x, 0.95)),
                        "maximum": float(np.max(x)),
                    }
                    for name, x in measures.items()
                },
            }
        )
    return result


@torch.inference_mode()
def main(inputs, workflow, output, nonlocal_reference):
    status = completed(workflow)
    plan = read(inputs)
    validate(plan)
    output = writable_path(output)
    if output.exists():
        raise ValueError("Grid output exists; inspect it or choose a new directory")
    assert torch.cuda.is_available() and psutil.virtual_memory().available / 1e9 > 24
    torch.set_num_threads(4)
    cached = []
    for c in plan["cases"]:
        assert sha(c["arrays"]) == c["sha256"]
        with np.load(c["arrays"], allow_pickle=False) as values:
            arrays = {k: v.copy() for k, v in values.items()}
        cpu = {k: torch.from_numpy(v) for k, v in arrays.items()}
        assert all(torch.isfinite(v).all() for v in cpu.values())
        cached.append((arrays, cpu))
    output.mkdir(parents=True, exist_ok=False)
    parent = read(status["plan"])["parent"]
    assert sha(parent["path"]) == parent["sha256"]
    records = [{**parent, "kind": "joint-checkpoint", "arm": "parent10k"}]
    for c in status["checkpoints"]:
        assert c["step"] == 1000 and sha(c["path"]) == c["sha256"]
        records.append(
            {
                "path": c["path"],
                "sha256": c["sha256"],
                "kind": "joint-checkpoint",
                "arm": c["arm"] + "-additional1k",
            }
        )
    assert len(records) == 3 and {r["arm"] for r in records} == {
        "parent10k",
        "control-additional1k",
        "wide-additional1k",
    }
    if nonlocal_reference is not None:
        records.append(
            {
                "path": str(nonlocal_reference),
                "sha256": CHECKPOINT_SHA256,
                "kind": "authors-RAW-reference-plus-Malvar",
                "arm": "released-RAW-reference",
            }
        )
    source = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    archive = output / "source"
    archive.mkdir()
    helper_files = [
        Path(__file__).with_name("prepare_color_grid.py"),
        Path(__file__).with_name("audit_colored_flats.py"),
    ]
    for p in [Path(__file__), *helper_files, *Path("src/demosaic").glob("*.py")]:
        (archive / p.name).write_bytes(p.read_bytes())
    execution = {
        "inputs": str(inputs),
        "input_plan_sha256": sha(inputs),
        "suite": plan["suite"],
        "cases": plan["cases"],
        "ROI_xywh": plan["roi_xywh"],
        "checkpoints": records,
        "source_files": source,
        "helper_source_files": {str(p): sha(p) for p in helper_files},
        "driver_sha256": sha(__file__),
        "workflow": str(workflow),
        "workflow_sha256": sha(workflow),
        "scope": plan["scope"],
        "runtime": "CUDA native256/B1, joint-network FP16/physicalFP32; optional authors RAW IEEEFP32. Saved nativeF32 predictions; no new observations, output correction or training.",
        "input_loading": "Verify/read each observation once into CPU memory; reuse it across methods and leave clean targets on CPU.",
    }
    (output / "plan.json").write_text(json.dumps(execution, indent=2) + "\n")
    results = []
    predictions = []
    crops = []
    for model_index, record in enumerate(records):
        if record["kind"] == "joint-checkpoint":
            assert sha(record["path"]) == record["sha256"]
            model, state = load_checkpoint(record["path"], "cuda")
            record.update(
                step=state["step"],
                label=record["arm"],
                model_config=model.config.to_dict(),
                compute_precision="float16, physicalFP32",
                memory_format="channels_last",
            )
            if record["arm"] != "parent10k":
                assert state["config"]["initialized_from"]["sha256"] == parent["sha256"]
            del state
        else:
            model = load_nonlocal_reference(record["path"], device="cuda", archive=output)
            record.update(
                label=model.receipt["label"],
                reference_receipt=model.receipt,
                compute_precision="IEEE float32",
                memory_format="contiguous, as loaded by the verified reference wrapper",
            )
        model.eval()
        if record["kind"] == "joint-checkpoint":
            model.to(memory_format=torch.channels_last)
        for case_index, c in enumerate(plan["cases"]):
            arrays, cpu = cached[case_index]
            batch = {k: cpu[k].to("cuda") for k in ["packed", "variance", "colors", "wb", "matrix"]}
            condition = c["condition"]
            model.set_noise(condition["shot"], condition["read"])
            with amp_context("cuda", dtype="float16"):
                p = model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                )
            assert (
                p.shape == (1, 3, 256, 256) and p.dtype == torch.float32 and torch.isfinite(p).all()
            )
            v = p.cpu().numpy()
            path = output / f"model{model_index}-case{case_index}-RGB-f32.npy"
            np.save(path, v, allow_pickle=False)
            predictions.append(
                {
                    "path": str(path),
                    "sha256": sha(path),
                    "shape": [1, 3, 256, 256],
                    "dtype": "float32",
                    "model_index": model_index,
                    "case": case_index,
                }
            )
            results.append(
                {
                    "model_index": model_index,
                    "case": case_index,
                    "palette": c["palette"],
                    "source": c["source"],
                    "condition": condition["name"],
                    "pattern": c["pattern"],
                    "metrics": metrics(v, arrays),
                }
            )
            if case_index in plan["native_preview_cases"]:
                noisy = malvar(cpu["packed"], cpu["colors"], cpu["wb"])
                crops.append(
                    save_triplet(
                        output,
                        f"grid:{record['arm']}:{c['id']}",
                        [
                            (name, display_crop(rgb, cpu["wb"], cpu["matrix"], plan["roi_xywh"]))
                            for name, rgb in [
                                ("Noisy (Malvar)", noisy),
                                ("Restored", torch.from_numpy(v)),
                                ("GT (analytic)", cpu["target"]),
                            ]
                        ],
                        caption=record["label"] + " / " + c["id"],
                        metadata={
                            "case": c,
                            "model": record,
                            "ROI_xywh": plan["roi_xywh"],
                            "white_balance": plan["white_balance"],
                            "camera_to_srgb": plan["camera_to_srgb"],
                            "conditioning": condition,
                            "display_exposure": 1.0,
                            "reference": "Exact uniform analytic target, not a real photo.",
                        },
                    )
                )
            if (case_index + 1) % 96 == 0:
                print(
                    json.dumps(
                        {
                            "model_index": model_index,
                            "completed": case_index + 1,
                            "total": len(plan["cases"]),
                        }
                    ),
                    flush=True,
                )
        if record["kind"] == "joint-checkpoint":
            assert sha(record["path"]) == record["sha256"]
        del model
        gc.collect()
        torch.cuda.empty_cache()
    assert len(results) == len(predictions) == 1176 * len(records) and len(crops) == 3 * len(
        records
    )
    assert source == {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    assert execution["driver_sha256"] == sha(__file__) and all(
        sha(p) == digest for p, digest in execution["helper_source_files"].items()
    )
    report = {
        "status": "completed-frozen-color-grid-inference-awaiting-independent-and-native-review",
        "plan": str(output / "plan.json"),
        "plan_sha256": sha(output / "plan.json"),
        "suite": plan["suite"],
        "checkpoints": records,
        "results": results,
        "float_predictions": predictions,
        "native_crops": crops,
        "group_summary": summarize(results),
        "scope": plan["scope"],
        "CUDA_initialized": True,
        "limitations": "One observation per grid cell, one WB/camera, three brightnesses/two saturations; scene-linear HSV, not perceptually uniform. Clean targets stay below white; noisy ADC can clip. Descriptive quantiles are not confidence intervals. Not training-repeat uncertainty, real-photo quality, convergence, cause or SOTA evidence.",
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "report": str(output / "report.json"),
                "cases": len(results),
                "native_PNGs": len(crops),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", required=True, type=Path)
    p.add_argument("--workflow", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--nonlocal-reference", type=Path)
    a = p.parse_args()
    main(a.inputs, a.workflow, a.output, a.nonlocal_reference)
