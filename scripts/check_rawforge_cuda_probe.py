"""Run signed original RawForge exports only after the owned review workflow exits."""

import argparse
import json
from pathlib import Path

import numpy as np
import psutil
import torch
from audit_colored_flats import sha

from demosaic.safety import writable_path


def read(path):
    return json.loads(Path(path).read_text())


def preceding_completed(path):
    s = read(path)
    if s["status"] != "completed-final4k-review-artifacts-awaiting-native-review":
        raise RuntimeError("Preceding review incomplete; do not overlap its GPU work")
    try:
        p = psutil.Process(s["controller"]["pid"])
        if (
            abs(p.create_time() - s["controller"]["created"]) < 0.01
            and p.status() != psutil.STATUS_ZOMBIE
        ):
            raise RuntimeError("Preceding review owner remains live")
    except psutil.NoSuchProcess:
        pass
    return s


@torch.inference_mode()
def main(report_path, audit_path, previous_workflow, output):
    previous = preceding_completed(previous_workflow)
    assert not torch.cuda.is_initialized()
    report, audit = read(report_path), read(audit_path)
    assert audit["report_sha256"] == sha(report_path) and audit["predictions"] == 12
    assert audit["all12_inputs_bit_exact_to_publisher_sparse_mask_F16_contract"]
    plan = read(report["plan"])
    assert sha(report["plan"]) == report["plan_sha256"]
    inspection = read(plan["inspection"])
    assert sha(plan["inspection"]) == plan["inspection_sha256"]
    output = writable_path(output)
    if output.exists():
        raise ValueError("Original-export GPU probe exists; inspect it rather than restarting")
    assert torch.cuda.is_available() and psutil.virtual_memory().available / 1e9 > 24
    torch.set_num_threads(4)
    output.mkdir(parents=True, exist_ok=False)
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    protocol = {
        "CPU_report": str(report_path),
        "CPU_report_sha256": sha(report_path),
        "CPU_audit": str(audit_path),
        "CPU_audit_sha256": sha(audit_path),
        "preceding_workflow": str(previous_workflow),
        "preceding_workflow_sha256": sha(previous_workflow),
        "preceding_controller": previous["controller"],
        "models": inspection["models"],
        "inputs": report["arrays"],
        "driver_sha256": sha(__file__),
        "comparison_policy": "Original signed TorchScript, no graph edits. Two modes: F32 input/weights without surrounding autocast, and publisher CUDA FP16 autocast. Preserve captured convolution TF32 flags; no IEEE-FP32 claim. Compare unclipped outputs against the exact CPU-port arrays, then retain every original output.",
        "predeclared_no_autocast_CPU_parity_tolerance": {
            "absolute": 0.002,
            "relative_to_CPU": 0.002,
        },
        "FP16_policy": "Report all drift without an equality/pass assumption; genuine original FP16 outputs need their own quality/native review.",
        "scope": "Six fixed observations/two models, nativeB1, no training or new noise, no protected-final/raw-source reads, no full102MP speed or benchmark claim.",
    }
    (output / "plan.json").write_text(json.dumps(protocol, indent=2) + "\n")
    rows, all_pass = [], True
    for m in inspection["models"]:
        assert sha(m["original"]) == m["original_sha256"]
        model = torch.jit.load(m["original"], map_location="cuda:0").eval()
        assert sum(v.numel() for v in model.parameters()) == 11319924
        assert all(
            v.dtype == torch.float32 and torch.isfinite(v).all()
            for v in model.state_dict().values()
        )
        for item in report["arrays"]:
            if item["model"] != m["name"]:
                continue
            loaded = {}
            for key in ["input-six-f32", "raw-network-f32"]:
                f = item["files"][key]
                assert sha(f["path"]) == f["sha256"]
                v = np.load(f["path"], allow_pickle=False)
                assert (
                    v.dtype == np.float32 and list(v.shape) == f["shape"] and np.isfinite(v).all()
                )
                loaded[key] = v
            x = torch.from_numpy(loaded["input-six-f32"]).to("cuda:0")
            baseline = loaded["raw-network-f32"].astype(np.float64)
            for mode in ["no-enclosing-autocast", "publisher-FP16-autocast"]:
                with torch.autocast(
                    "cuda", dtype=torch.float16, enabled=mode == "publisher-FP16-autocast"
                ):
                    p = model(x)
                assert p.shape == loaded["raw-network-f32"].shape and torch.isfinite(p).all()
                native_dtype = str(p.dtype)
                v = p.float().cpu().numpy()
                error = np.abs(v.astype(np.float64) - baseline)
                tolerance = 0.002 + 0.002 * np.abs(baseline)
                outside = int((error > tolerance).sum())
                passed = outside == 0
                if mode == "no-enclosing-autocast":
                    all_pass &= passed
                path = output / (m["name"] + "-" + item["case"] + "-" + mode + "-raw-f32.npy")
                np.save(path, v, allow_pickle=False)
                rows.append(
                    {
                        "model": m["name"],
                        "case": item["case"],
                        "mode": mode,
                        "original_checkpoint_sha256": m["original_sha256"],
                        "native_output_dtype": native_dtype,
                        "raw_output": str(path),
                        "raw_output_sha256": sha(path),
                        "shape": list(v.shape),
                        "CPU_max_abs_difference": float(error.max()),
                        "CPU_mean_abs_difference": float(error.mean()),
                        "CPU_RMS_difference": float(np.sqrt(np.square(error).mean())),
                        "elements": int(v.size),
                        "outside_predeclared_no_autocast_tolerance": outside,
                        "no_autocast_parity_pass": passed
                        if mode == "no-enclosing-autocast"
                        else None,
                    }
                )
                print(
                    json.dumps(
                        {
                            "model": m["name"],
                            "case": item["case"],
                            "mode": mode,
                            "maximum_difference": float(error.max()),
                            "outside": outside,
                        }
                    ),
                    flush=True,
                )
            del x, p
        del model
        torch.cuda.empty_cache()
    assert len(rows) == 24 and sha(__file__) == protocol["driver_sha256"]
    result = {
        "status": "completed-original-RawForge-GPU-probe-awaiting-numerical-and-native-review",
        "plan": str(output / "plan.json"),
        "plan_sha256": sha(output / "plan.json"),
        "results": rows,
        "all_original_no_autocast_outputs_within_predeclared_CPU_parity_tolerance": all_pass,
        "device": torch.cuda.get_device_name(0),
        "torch": torch.__version__,
        "CUDA_initialized": torch.cuda.is_initialized(),
        "limits": "Actual original exports, not the device-ported files. No-autocast can retain TF32 allowed by captured convolution flags; publisherFP16 is a separate mode. Every mismatch retained with fixed predeclared tolerance; no automatic widening or promotion. Selected six observations only; no broad/SOTA/speed claim.",
    }
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", required=True, type=Path)
    p.add_argument("--audit", required=True, type=Path)
    p.add_argument("--previous-workflow", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    a = p.parse_args()
    main(a.report, a.audit, a.previous_workflow, a.output)
