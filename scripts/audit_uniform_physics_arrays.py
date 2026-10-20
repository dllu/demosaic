"""Independently reduce saved uniform-profile CUDA arrays without Torch/inference."""

import argparse
import math
import statistics
from pathlib import Path

import numpy as np
from queue_tf32x3_cuda import alive
from queue_uniform_physics_cuda import COMPLETE, REJECTED, guard
from train_directional_bank_trial import read, ref, save

from demosaic.safety import writable_path


def expected_shape(label):
    if label in ("photo0-native256", "photo1-native256"):
        return (1, 3, 256, 256)
    if label in ("GFX-four-native512", "analytic-four-CFA-native512"):
        return (4, 3, 512, 512)
    raise ValueError("Unknown frozen input label")


def check_pairs(cases, *, original_key="original"):
    """Independent FP64 subtraction and scalar fsum; never clip or quantize."""
    audited, seen = [], set()
    for case in cases:
        key = case["model"], case["fixture"]["label"]
        if key in seen:
            raise ValueError("Duplicate model/input array pair")
        seen.add(key)
        for item in [case["arrays"], case["checkpoint"], case["fixture"]["observation"]]:
            assert ref(item["path"]) == item
        with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
            assert set(arrays.files) == {original_key, "candidate"}
            original, candidate = arrays[original_key], arrays["candidate"]
            assert original.shape == candidate.shape == expected_shape(key[1])
            assert original.dtype == candidate.dtype == np.float32
            assert np.isfinite(original).all() and np.isfinite(candidate).all()
            delta = (candidate.astype(np.float64) - original.astype(np.float64)) * 65535
            maximum = float(np.abs(delta).max())
            rms = math.sqrt(math.fsum(float(v) ** 2 for v in delta.flat) / delta.size)
            exact = original.tobytes() == candidate.tobytes()
        measured = case["difference"]
        assert maximum == measured["maximum_DN16"]
        assert abs(rms - measured["RMS_DN16"]) < 1e-12
        if "bytes_exact" in measured:
            assert exact == measured["bytes_exact"]
        if "values" in measured:
            assert delta.size == measured["values"]
        audited.append(
            {
                "model": key[0],
                "fixture": key[1],
                "arrays": case["arrays"],
                "values": delta.size,
                "bytes_exact": exact,
                "maximum_DN16": maximum,
                "RMS_DN16": rms,
                "RMS_replay_difference": abs(rms - measured["RMS_DN16"]),
                "passes_original_limits": maximum <= 1 and rms <= 0.25,
            }
        )
    return audited


def check_timings(timings, models):
    assert len(timings) == len(models)
    result = []
    for model in models:
        items = [t for t in timings if t["model"] == model]
        assert len(items) == 1
        item = items[0]
        assert [s["candidate"] for s in item["samples"]] == [
            False,
            True,
            True,
            False,
            True,
            False,
            False,
            True,
        ]
        samples = {
            name: [s["seconds"] for s in item["samples"] if s["candidate"] is flag]
            for name, flag in [("original", False), ("candidate", True)]
        }
        assert all(
            len(v) == 4 and all(math.isfinite(x) and x > 0 for x in v) for v in samples.values()
        )
        medians = {name: statistics.median(v) for name, v in samples.items()}
        assert medians == item["median_seconds"]
        result.append(
            {
                "model": model,
                "samples_seconds": samples,
                "median_seconds": medians,
                "candidate_over_original_median": medians["candidate"] / medians["original"],
            }
        )
    return result


def completed(controller_plan_path):
    """No output directory is created until exact successful/rejected owners exit."""
    controller_plan = read(controller_plan_path)
    gpu = guard(controller_plan)
    root = Path(controller_plan["root"])
    state = read(root / "status.json")
    launch = read(root / "queue-launch.json")
    verified = read(root / "verified-queue.json")
    if (
        state["plan"] != ref(controller_plan_path)
        or state["plan"] != launch["plan"]
        or state["controller"] != launch["owner"]
        or state["controller"] != verified["controller_owner"]
        or state["plan"] != verified["controller_plan"]
    ):
        raise ValueError("Controller plan changed")
    if alive(state["controller"]) or any(alive(o) for o in gpu["blocking_owners"]):
        raise RuntimeError("Exact CUDA/training/quality owners remain live; no completed review")
    if state.get("child") and alive(state["child"]):
        raise RuntimeError("CUDA worker is still live")
    if state["status"] not in (COMPLETE, REJECTED):
        raise RuntimeError("Probe has no completed/rejected CUDA terminal; no retry")
    worker_status_path = Path(gpu["output"]) / "status.json"
    worker = read(worker_status_path)
    assert worker["owner"] == state["child"] and worker["plan"] == controller_plan["GPU_plan"]
    assert worker["status"] == state["status"]
    if state["status"] == COMPLETE:
        assert state["receipt"] == worker["receipt"] == ref(worker["receipt"]["path"])
        source = worker["receipt"]
        result = read(source["path"])
        assert result["owner"] == worker["owner"] and result["plan"] == worker["plan"]
        assert result["CUDA_initialized"] is True and result["status"] == COMPLETE
    else:
        source = ref(worker_status_path)
        result = dict(worker, resident_timings=[])
    return gpu, result, source


def main(controller_plan_path, output):
    gpu, result, source = completed(controller_plan_path)
    fixtures = {f["label"]: f for f in gpu["fixtures"]}
    expected = [(m, f["label"]) for m in gpu["checkpoints"] for f in gpu["fixtures"]]
    cases = result["cases"]
    assert [(c["model"], c["fixture"]["label"]) for c in cases] == expected[: len(cases)]
    for case in cases:
        assert case["checkpoint"] == gpu["checkpoints"][case["model"]]
        assert case["fixture"] == fixtures[case["fixture"]["label"]]
        assert case["CPU_relative_native_xywh"] is None
        assert case["candidate_repeat_bytes_exact"] and case["restored_original_bytes_exact"]
        assert case["model_DINO_state_parameter_identities_and_RNG_unchanged"]
    audited = check_pairs(cases)
    if result["status"] == COMPLETE:
        assert len(cases) == len(expected) == 8
        assert all(c["passes_original_limits"] for c in audited)
        timings = check_timings(result["resident_timings"], gpu["checkpoints"])
    else:
        assert 1 <= len(cases) <= 8 and not audited[-1]["passes_original_limits"]
        assert all(c["passes_original_limits"] for c in audited[:-1])
        assert not result["resident_timings"]
        timings = []
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    save(
        output / "array-audit.json",
        {
            "status": "audited-complete-uniform-physics-CUDA-arrays-awaiting-native-review"
            if result["status"] == COMPLETE
            else "audited-rejected-uniform-physics-CUDA-arrays-no-timing",
            "driver": ref(__file__),
            "controller_plan": ref(controller_plan_path),
            "worker_result": source,
            "GPU_plan": read(controller_plan_path)["GPU_plan"],
            "input_bindings_verified": len(gpu["inputs"]),
            "cases": audited,
            "total_RGB_values": sum(c["values"] for c in audited),
            "resident_timings": timings,
            "manual_review_completed": False,
            "Torch_imported": False,
            "scope": "Independent NumPy FP64/fsum arithmetic on complete saved arrays, without clipping, quantization, inference, fresh timing, promotion or full-frame extrapolation. Partial numerical rejection is retained accurately; native inspection remains required.",
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("controller_plan", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    main(a.controller_plan.resolve(), a.output.resolve())
