"""Evaluate the frozen color grid after the owned palette workflow exits.

Reuses the same observations for parent/control/wide; optional authors' RAW
reference stays FP32. This grid is diagnostic, not photographic/SOTA evidence.
"""

import argparse
import copy
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


TERMINALS = {
    1000: "completed-first1000-and-evaluation-awaiting-manual-review",
    4000: "completed-original4000-and-evaluation-awaiting-manual-review",
}


def completed(workflow, expected_step=1000):
    status = read(workflow)
    if status["status"] != TERMINALS[expected_step]:
        raise RuntimeError("Preceding palette evaluation incomplete; do not overlap or restart it")
    owner = status["controller"]
    try:
        p = psutil.Process(owner["pid"])
        if abs(p.create_time() - owner["created"]) < 0.01 and p.status() != psutil.STATUS_ZOMBIE:
            raise RuntimeError(f"Preceding palette owner remains live: PID{p.pid}")
    except psutil.NoSuchProcess:
        pass
    return status


def reuse_manifest(report_path, audit_path, inputs, source):
    """Require audited identical observations and model code before reusing arrays."""
    if report_path is None:
        if audit_path is not None:
            raise ValueError("Reuse audit requires a reuse report")
        return None
    if audit_path is None:
        raise ValueError("A completed independent case-array audit is required for reuse")
    report, audit = read(report_path), read(audit_path)
    assert audit["input_report_sha256"] == sha(report_path)
    assert audit["observations"] == 1176 and not audit["CUDA_initialized"]
    assert len(audit["native_panel_triplets"]) == len(report["native_crops"])
    old = read(report["plan"])
    assert sha(report["plan"]) == report["plan_sha256"]
    assert old["input_plan_sha256"] == sha(inputs)
    assert old["cases"] == read(inputs)["cases"]
    assert old["source_files"] == source
    count = len(report["checkpoints"])
    assert audit["float_predictions"] == len(report["float_predictions"]) == 1176 * count
    assert audit["metric_fields"] == 1176 * count * 6
    arrays = {(r["model_index"], r["case"]): r for r in report["float_predictions"]}
    assert len(arrays) == 1176 * count and arrays.keys() == {
        (m, c) for m in range(count) for c in range(1176)
    }
    return {
        "report": str(report_path),
        "report_sha256": sha(report_path),
        "case_audit": str(audit_path),
        "case_audit_sha256": sha(audit_path),
        "checkpoints": report["checkpoints"],
        "arrays": arrays,
        "native_crops": report["native_crops"],
    }


def reuse_match(record, reuse):
    if reuse is None:
        return None
    matches = [
        i
        for i, c in enumerate(reuse["checkpoints"])
        if (c["kind"], c["sha256"], c["path"]) == (record["kind"], record["sha256"], record["path"])
    ]
    assert len(matches) <= 1
    if not matches:
        return None
    old = reuse["checkpoints"][matches[0]]
    if record["kind"] == "joint-checkpoint":
        assert old["compute_precision"] == "float16, physicalFP32"
        assert old["memory_format"] == "channels_last"
    else:
        assert old["compute_precision"] == "IEEE float32"
        assert old["memory_format"] == "contiguous, as loaded by the verified reference wrapper"
    return matches[0]


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
def main(
    inputs,
    workflow,
    output,
    nonlocal_reference,
    expected_step=1000,
    reuse_report=None,
    reuse_audit=None,
    reuse_only=False,
):
    status = completed(workflow, expected_step)
    plan = read(inputs)
    validate(plan)
    output = writable_path(output)
    if output.exists():
        raise ValueError("Grid output exists; inspect it or choose a new directory")
    parent = read(status["plan"])["parent"]
    assert sha(parent["path"]) == parent["sha256"]
    records = [{**parent, "kind": "joint-checkpoint", "arm": "parent10k"}]
    for c in status["checkpoints"]:
        assert c["step"] == expected_step and sha(c["path"]) == c["sha256"]
        records.append(
            {
                "path": c["path"],
                "sha256": c["sha256"],
                "kind": "joint-checkpoint",
                "arm": c["arm"] + f"-additional{expected_step // 1000}k",
            }
        )
    assert len(records) == 3 and {r["arm"] for r in records} == {
        "parent10k",
        f"control-additional{expected_step // 1000}k",
        f"wide-additional{expected_step // 1000}k",
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
    evaluate_records(
        inputs,
        workflow,
        output,
        records,
        parent["sha256"],
        expected_step,
        reuse_report,
        reuse_audit,
        reuse_only,
    )


def check_joint_lineage(state, checkpoint_sha256, parent_sha256, expected_step):
    """Recognize the verified parent by content, independently of display labels."""
    if checkpoint_sha256 != parent_sha256:
        assert state["config"]["initialized_from"]["sha256"] == parent_sha256
        assert state["step"] == expected_step


@torch.inference_mode()
def evaluate_records(
    inputs,
    workflow,
    output,
    records,
    parent_sha256,
    expected_step=1000,
    reuse_report=None,
    reuse_audit=None,
    reuse_only=False,
):
    """Evaluate explicitly validated records; callers validate their actual owner."""
    plan = read(inputs)
    validate(plan)
    output = writable_path(output)
    if output.exists():
        raise ValueError("Grid output exists; inspect it or choose a new directory")
    assert records and len({r["sha256"] for r in records}) == len(records)
    source = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    reuse = reuse_manifest(reuse_report, reuse_audit, inputs, source)
    matches = [reuse_match(r, reuse) for r in records]
    if reuse_only and any(m is None for m in matches):
        raise RuntimeError("Reuse-only execution requires every exact model in the audited report")
    needs_cuda = any(m is None for m in matches)
    if needs_cuda:
        assert torch.cuda.is_available() and psutil.virtual_memory().available / 1e9 > 24
    torch.set_num_threads(2 if reuse_only else 4)
    cached = []
    for c in plan["cases"]:
        assert sha(c["arrays"]) == c["sha256"]
        with np.load(c["arrays"], allow_pickle=False) as values:
            arrays = {k: v.copy() for k, v in values.items()}
        cpu = {k: torch.from_numpy(v) for k, v in arrays.items()}
        assert all(torch.isfinite(v).all() for v in cpu.values())
        cached.append((arrays, cpu))
    output.mkdir(parents=True, exist_ok=False)
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
        "expected_checkpoint_step": expected_step,
        "reuse": None
        if reuse is None
        else {k: reuse[k] for k in ["report", "report_sha256", "case_audit", "case_audit_sha256"]},
        "reused_model_index_in_previous_report": matches,
        "scope": plan["scope"],
        "runtime": "New inference: CUDA native256/B1, jointFP16/physicalFP32, authorsRAW IEEEFP32. Reused exact-weight/source/observation F32 arrays keep their previous precision. Reuse-only uses CPU and no inference. No new observations, output correction or training.",
        "input_loading": "Verify/read each observation once into CPU memory; reuse it across methods and leave clean targets on CPU.",
    }
    (output / "plan.json").write_text(json.dumps(execution, indent=2) + "\n")
    results = []
    predictions = []
    crops = []
    new_count, reused_count = 0, 0
    for model_index, record in enumerate(records):
        previous_index = matches[model_index]
        model = None
        if previous_index is not None:
            record.update(copy.deepcopy(reuse["checkpoints"][previous_index]))
        elif record["kind"] == "joint-checkpoint":
            assert sha(record["path"]) == record["sha256"]
            model, state = load_checkpoint(record["path"], "cuda")
            record.update(
                step=state["step"],
                label=record["arm"],
                model_config=model.config.to_dict(),
                compute_precision="float16, physicalFP32",
                memory_format="channels_last",
            )
            check_joint_lineage(state, record["sha256"], parent_sha256, expected_step)
            del state
        else:
            model = load_nonlocal_reference(record["path"], device="cuda", archive=output)
            record.update(
                label=model.receipt["label"],
                reference_receipt=model.receipt,
                compute_precision="IEEE float32",
                memory_format="contiguous, as loaded by the verified reference wrapper",
            )
        if model is not None:
            model.eval()
            if record["kind"] == "joint-checkpoint":
                model.to(memory_format=torch.channels_last)
        for case_index, c in enumerate(plan["cases"]):
            arrays, cpu = cached[case_index]
            condition = c["condition"]
            if previous_index is not None:
                saved = reuse["arrays"][previous_index, case_index]
                path = Path(saved["path"])
                assert sha(path) == saved["sha256"]
                v = np.load(path, allow_pickle=False)
                reused_count += 1
            else:
                batch = {
                    k: cpu[k].to("cuda") for k in ["packed", "variance", "colors", "wb", "matrix"]
                }
                model.set_noise(condition["shot"], condition["read"])
                with amp_context("cuda", dtype="float16"):
                    p = model(
                        batch["packed"],
                        batch["variance"],
                        batch["colors"],
                        batch["wb"],
                        batch["matrix"],
                    )
                v = p.cpu().numpy()
                path = output / f"model{model_index}-case{case_index}-RGB-f32.npy"
                np.save(path, v, allow_pickle=False)
                new_count += 1
            assert v.shape == (1, 3, 256, 256) and v.dtype == np.float32 and np.isfinite(v).all()
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
        if needs_cuda:
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
        "CUDA_initialized": torch.cuda.is_initialized(),
        "prediction_work": {"new_inference": new_count, "reused_verified_arrays": reused_count},
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
    p.add_argument("--expected-step", type=int, choices=[1000, 4000], default=1000)
    p.add_argument("--reuse-report", type=Path)
    p.add_argument("--reuse-audit", type=Path)
    p.add_argument("--reuse-only", action="store_true")
    a = p.parse_args()
    main(
        a.inputs,
        a.workflow,
        a.output,
        a.nonlocal_reference,
        a.expected_step,
        a.reuse_report,
        a.reuse_audit,
        a.reuse_only,
    )
