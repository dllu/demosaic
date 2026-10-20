"""Review saved mature precision scalars only after actual native-cell viewing."""

import argparse
import os
from pathlib import Path

import numpy as np
from mature_precision_review_tools import (
    carrier_metrics,
    comparison_gates,
    display_metrics,
    flat_metrics,
    input_fingerprint,
    linear_rgb,
    physical_difference,
)
from queue_tf32x3_cuda import alive
from render_mature_precision import (
    POLICIES,
    arrays,
    checked,
    gpu_methods,
    prediction,
    save_new,
)
from train_directional_bank_trial import guard, read, ref


def manual_review(index_path, manual_path, methods):
    index, manual = read(index_path), read(manual_path)
    if manual.get("status") != "actually-viewed-all-native-mature-precision-cells-before-scalars":
        raise ValueError("Actual native viewing receipt is required before scalar review")
    if (
        manual.get("render_index") != ref(index_path)
        or manual.get("new_scalars_interpreted") is not False
    ):
        raise ValueError("Manual viewing must precede scalar interpretation for these exact boards")
    if index["methods"] != methods or index["triplets"] != 36 or index["native_cells_exact"] != 48:
        raise ValueError("Native render does not cover all actual pilot policies and fixed cases")
    if len(manual.get("boards", [])) != 2 or not manual.get("observed_UTC"):
        raise ValueError("Both actual native boards and viewing time are required")
    for item, viewed in zip(index["boards"], manual["boards"], strict=True):
        board = read(checked(item))
        checked(board["board"])
        if (
            viewed["receipt"] != item
            or viewed["image"] != board["board"]
            or viewed["native_cells_viewed"] != board["native_cells_exact"]
            or not viewed.get("observations")
        ):
            raise ValueError("Manual receipt must describe every cell in each exact native board")
    findings = manual.get("per_policy_findings", [])
    expected = {(m["model"], m["policy"]) for m in methods if m["policy"] != "fp32"}
    keys = [(r["model"], r["policy"]) for r in findings]
    if (
        len(set(keys)) != len(keys)
        or set(keys) != expected
        or any(
            type(r.get("no_visible_new_artifact")) is not bool or not r.get("notes")
            for r in findings
        )
    ):
        raise ValueError("Record an actual visible-artifact finding for each half policy/model")
    return {(r["model"], r["policy"]): r for r in findings}


def main(protocol_path, receipt_path, index_path, manual_path, output):
    import torch

    import demosaic.metrics as canonical

    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or torch.cuda.is_initialized():
        raise ValueError("Scalar review must remain CPU-only")
    torch.set_num_threads(2)
    protocol = read(protocol_path)
    guard(protocol)
    if (
        ref(__file__) != protocol["reviewer"]
        or ref(canonical.__file__) != protocol["canonical_metrics"]
    ):
        raise ValueError("Run the source-frozen scalar reviewer and canonical metrics")
    plan_path = checked(protocol["GPU_plan"])
    plan = read(plan_path)
    guard(plan)
    status = read(Path(plan["root"]) / "controller-status.json")
    gpu = read(receipt_path)
    if (
        status["status"]
        != "completed-mature-precision-pilot-arrays-awaiting-native-and-independent-scalar-review"
        or status["plan"] != ref(plan_path)
        or status["receipt"] != ref(receipt_path)
        or status["child"] != gpu["owner"]
        or alive(status["controller"])
        or alive(status["child"])
    ):
        raise ValueError("GPU worker/controller must complete successfully and actually exit")
    methods = gpu_methods(plan_path, receipt_path)
    index = read(index_path)
    if index["driver"] != protocol["renderer"] or ref(receipt_path) not in index["evidence"]:
        raise ValueError("Native renderer/input receipt differs from the frozen postprocessing")
    findings = manual_review(index_path, manual_path, methods)
    # No quality/timing reduction occurs above the actual-viewing requirement.
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    cpu = read(checked(plan["CPU_preflight"]))
    inputs = {f["id"]: arrays(f["arrays"]) for f in plan["fixtures"]}
    fingerprints = {k: input_fingerprint(v) for k, v in inputs.items()}
    base_fixture, plus_fixture = plan["fixtures"][-2:]
    if (
        base_fixture["kind"] != "ramp"
        or plus_fixture["kind"] != "ramp"
        or base_fixture["patterns"] != ["RGGB", "BGGR", "GRBG", "GBRG"]
    ):
        raise ValueError("Expected the frozen all-CFA ramp pair")
    for name in inputs[base_fixture["id"]]:
        expected = inputs[base_fixture["id"]][name]
        if name == "packed":
            expected = expected + np.float32(1 / 65535)
        np.testing.assert_array_equal(inputs[plus_fixture["id"]][name], expected)
    rows, differences, ramps, timing_rows, policy_results = [], [], [], [], []
    for model in gpu["models"]:
        label = model["model"]
        proof = next(r for r in cpu["models"] if r["label"] == label)
        if (
            model["model_sha256"] != proof["model_sha256"]
            or model["DINO_sha256"] != proof["DINO_sha256"]
            or not model["FP32_hidden_identity_exact"]
            or not model["model_config_parameter_RNG_exact"]
            or model["instrumented_encoder_calls"] != 94
            or model["unhooked_timing_forwards"] != 12
        ):
            raise ValueError("GPU state/dtype/forward evidence differs from fixed pilot")
        captures = {(c["policy"], c["fixture"]): c for c in model["captures"]}
        scored = {}
        for fixture in plan["fixtures"]:
            host = inputs[fixture["id"]]
            shape = (
                len(host["packed"]),
                3,
                host["packed"].shape[-2] * 2,
                host["packed"].shape[-1] * 2,
            )
            predictions = {}
            for policy in POLICIES:
                capture = captures[policy, fixture["id"]]
                expected_dtypes = {
                    "physical_head": "torch.float32",
                    "middle": "torch.float32",
                    "physical_tail": "torch.float32",
                    "first_encoder": "torch.float16"
                    if policy == "fp16-hidden"
                    else "torch.float32",
                }
                if (
                    capture["input_sha256"] != fingerprints[fixture["id"]]
                    or capture["dtypes"] != expected_dtypes
                ):
                    raise ValueError("GPU physical input fingerprint or observed dtype differs")
                pred = prediction(capture["RGB"], shape)
                predictions[policy] = pred
                if fixture["kind"] == "photo":
                    tensors = [
                        torch.from_numpy(v)
                        for v in (pred, host["target"], host["wb"], host["matrix"])
                    ]
                    values = canonical.quality_metrics(*tensors)
                    fp32 = {k: float(values[k][0]) for k in ("srgb_psnr", "srgb_ssim")}
                    f64 = {
                        k: float(v[0])
                        for k, v in display_metrics(
                            pred, host["target"], host["wb"], host["matrix"]
                        ).items()
                    }
                    row = {
                        "model": label,
                        "policy": policy,
                        "fixture": fixture["id"],
                        "kind": "photo",
                        "RGB": capture["RGB"],
                        "canonical_FP32": fp32,
                        "independent_float64": f64,
                    }
                    scored[policy, fixture["id"], 0] = row
                    rows.append(row)
                elif fixture["kind"] == "analytic":
                    p, t = [
                        linear_rgb(v, host["wb"], host["matrix"]) for v in (pred, host["target"])
                    ]
                    if fixture["signal_kind"] == "carrier":
                        values = carrier_metrics(p, t, fixture["cases"][0]["period"])
                        kind = (
                            "adc-carrier"
                            if fixture["condition"]["name"] == "adc-only"
                            else "weak-noisy-carrier"
                        )
                    else:
                        values, kind = flat_metrics(p, t), "flat"
                    for j, case in enumerate(fixture["cases"]):
                        row = {
                            "model": label,
                            "policy": policy,
                            "fixture": fixture["id"],
                            "case": case,
                            "condition": fixture["condition"],
                            "kind": kind,
                            "RGB": capture["RGB"],
                            "metrics": {k: float(v[j]) for k, v in values.items()},
                        }
                        if kind == "adc-carrier":
                            row["duplicate_original_draw_labels"] = [0, 1, 2, 3]
                        scored[policy, fixture["id"], j] = row
                        rows.append(row)
            for policy in POLICIES[1:]:
                differences.append(
                    {
                        "model": label,
                        "policy": policy,
                        "fixture": fixture["id"],
                        **physical_difference(predictions[policy], predictions["fp32"]),
                    }
                )
        base, plus = plan["fixtures"][-2:]
        for policy in POLICIES:
            pred = prediction(captures[policy, base["id"]]["RGB"], (4, 3, 256, 256))
            other = prediction(captures[policy, plus["id"]]["RGB"], pred.shape)
            quantized = np.rint(np.clip(pred, 0, 1).astype(np.float64) * 65535).astype(np.uint16)
            for j, pattern in enumerate(base["patterns"]):
                codes = int(np.unique(quantized[j]).size)
                response = float(np.sqrt(np.mean((other[j].astype(np.float64) - pred[j]) ** 2)))
                ramps.append(
                    {
                        "model": label,
                        "policy": policy,
                        "pattern": pattern,
                        "codes": codes,
                        "one_DN_response_RMS": response,
                        "passed": codes > 256 and response > 0,
                    }
                )
        for policy in POLICIES[1:]:
            gates, deltas = [], []
            for (p, fixture_id, j), row in scored.items():
                if p != policy:
                    continue
                baseline = scored["fp32", fixture_id, j]
                if row["kind"] == "photo":
                    canonical_gate = comparison_gates(
                        "photo", baseline["canonical_FP32"], row["canonical_FP32"]
                    )
                    independent_gate = comparison_gates(
                        "photo", baseline["independent_float64"], row["independent_float64"]
                    )
                    result = {
                        "canonical_FP32": canonical_gate,
                        "independent_float64": independent_gate,
                        "gate_decisions_agree": canonical_gate == independent_gate,
                    }
                    passed = all(canonical_gate.values()) and all(independent_gate.values())
                else:
                    result = comparison_gates(row["kind"], baseline["metrics"], row["metrics"])
                    passed = all(result.values())
                    deltas.append(
                        {
                            "fixture": fixture_id,
                            "case": row["case"],
                            "kind": row["kind"],
                            "delta": {
                                k: row["metrics"][k] - baseline["metrics"][k]
                                for k in row["metrics"]
                            },
                        }
                    )
                gates.append(
                    {
                        "fixture": fixture_id,
                        "case_index": j,
                        "kind": row["kind"],
                        "gates": result,
                        "passed": bool(passed),
                    }
                )
            ramp_pass = all(
                r["passed"]
                for r in ramps
                if r["model"] == label and r["policy"] in ("fp32", policy)
            )
            visible_pass = findings[label, policy]["no_visible_new_artifact"]
            policy_results.append(
                {
                    "model": label,
                    "policy": policy,
                    "gates": gates,
                    "analytic_deltas": deltas,
                    "native_artifact_screen_passed": visible_pass,
                    "ramp_passed": ramp_pass,
                    "finite_screen_passed": bool(
                        visible_pass and ramp_pass and all(g["passed"] for g in gates)
                    ),
                }
            )
        timing = model["timings"]
        first_calls = [r for r in timing if r["kind"] == "first-policy-call-in-this-process"]
        if (
            len(timing) != 15
            or len(first_calls) != 3
            or {r["policy"] for r in first_calls} != set(POLICIES)
            or any(
                not r["includes_dtype_hooks_and_checks"]
                or not np.isfinite(r["seconds"])
                or r["seconds"] <= 0
                for r in first_calls
            )
        ):
            raise ValueError("Expected one finite instrumented first call per policy/model")
        samples = [r for r in timing if r["kind"] == "synchronized-resident-unhooked-sample"]
        if len(samples) != 12 or sorted(r["sample"] for r in samples) != list(range(12)):
            raise ValueError("Expected all twelve fixed resident timing samples")
        for policy in POLICIES:
            group = [r for r in samples if r["policy"] == policy]
            if len(group) != 4:
                raise ValueError("Expected exactly four samples per policy/model")
            first = prediction(captures[policy, plan["fixtures"][0]["id"]]["RGB"], (4, 3, 512, 512))
            repeats = []
            for sample in group:
                saved = prediction(sample["RGB"], first.shape)
                equal = np.array_equal(first, saved)
                if (
                    bool(equal) != sample["byte_equal_first_capture"]
                    or not np.isfinite(sample["seconds"])
                    or sample["seconds"] <= 0
                ):
                    raise ValueError("Resident timing repeat/finite-duration evidence differs")
                repeats.append(
                    {
                        "sample": sample["sample"],
                        "RGB": sample["RGB"],
                        "byte_equal_first_capture": bool(equal),
                        **physical_difference(saved, first),
                    }
                )
            seconds = [r["seconds"] for r in group]
            timing_rows.append(
                {
                    "model": label,
                    "policy": policy,
                    "seconds": seconds,
                    "median_seconds": float(np.median(seconds)),
                    "minimum_seconds": min(seconds),
                    "maximum_seconds": max(seconds),
                    "repeat_checks": repeats,
                    "first_calls": [
                        r
                        for r in timing
                        if r["kind"] == "first-policy-call-in-this-process"
                        and r["policy"] == policy
                    ],
                }
            )
    if len(rows) != 588 or len(ramps) != 24 or len(differences) != 116:
        raise ValueError("Fixed scalar observation coverage is incomplete")
    for row in timing_rows:
        baseline = next(
            r for r in timing_rows if r["model"] == row["model"] and r["policy"] == "fp32"
        )
        row["median_speedup_fraction"] = baseline["median_seconds"] / row["median_seconds"] - 1
    groups = {}
    for row in rows:
        if row["kind"] == "photo":
            continue
        case = row["case"]
        key = (
            row["model"],
            row["policy"],
            row["kind"],
            case["level"],
            case["contrast"],
            case["period"],
        )
        groups.setdefault(key, []).append(row)
    means = [
        {
            "model": k[0],
            "policy": k[1],
            "kind": k[2],
            "level": k[3],
            "contrast": k[4],
            "period": k[5],
            "unique_observations": len(v),
            "metrics": {
                name: float(np.mean([r["metrics"][name] for r in v])) for name in v[0]["metrics"]
            },
        }
        for k, v in groups.items()
    ]
    if len(means) != 90 or torch.cuda.is_initialized():
        raise ValueError("Expected all fixed analytic groups and CPU-only review")
    save_new(
        output / "result.json",
        {
            "status": "completed-fixed-mature-precision-scalar-screen",
            "protocol": ref(protocol_path),
            "GPU_receipt": ref(receipt_path),
            "native_render": ref(index_path),
            "actual_manual_viewing_before_scalars": ref(manual_path),
            "driver": ref(__file__),
            "per_observation": rows,
            "group_means": means,
            "policy_screens": policy_results,
            "physical_differences_unclipped_DN16": differences,
            "native_ramps": ramps,
            "resident_timings": timing_rows,
            "CUDA_initialized": torch.cuda.is_initialized(),
            "new_network_forwards": 0,
            "scope": "Finite existing-weight screen only. All 96 unique analytic observations retained per method; 48 ADC observations carry 192 historical duplicate labels. Photo metrics use full native256 outputs; analytic ROI is native160 at48,48. GFX ISO100 is not scored. FP32 production and independent float64 photo gate decisions must both pass. Timing is resident B4/native512 only, excludes export/full-frame inference. No model/default change, automatic continuation, quality-population, SOTA or100MP/10s claim.",
        },
    )
    guard(protocol)
    guard(plan)
    print(
        {
            "status": "completed-fixed-mature-precision-scalar-screen",
            "rows": len(rows),
            "native_ramps": len(ramps),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "GPU_receipt", "render_index", "manual_viewing", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    main(args.protocol, args.GPU_receipt, args.render_index, args.manual_viewing, args.output)
