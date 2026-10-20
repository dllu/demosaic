"""Independently replay a completed saved precision screen with CPU Torch math."""

import argparse
import json
import math
import os
from pathlib import Path

from render_mature_precision import arrays, checked, prediction, save_new
from train_directional_bank_trial import guard, read, ref


def main(protocol_path, result_path, output):
    import torch
    from diagnose_texture_response import linear_srgb, response_metrics
    from evaluate_texture_candidates import flat_metrics

    from demosaic.metrics import quality_metrics

    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or torch.cuda.is_initialized():
        raise ValueError("Independent replay must remain CPU-only")
    torch.set_num_threads(2)
    protocol, result = read(protocol_path), read(result_path)
    guard(protocol)
    if result["protocol"] != ref(protocol_path) or result["new_network_forwards"] != 0:
        raise ValueError("Wrong completed saved-output review")
    gpu = read(checked(result["GPU_receipt"]))
    plan = read(checked(protocol["GPU_plan"]))
    guard(plan)
    rows = result["per_observation"]
    key = lambda r: (
        r["model"],
        r["policy"],
        r["fixture"],
        json.dumps(r.get("case"), sort_keys=True),
    )
    saved = {key(r): r for r in rows}
    if len(saved) != len(rows) or len(rows) != 588:
        raise ValueError("Duplicate/missing saved scalar observations")
    errors, analytic_fields, photo_fields, physical_values, repeats, ramp_fields = {}, 0, 0, 0, 0, 0
    physical = {
        (r["model"], r["policy"], r["fixture"]): r
        for r in result["physical_differences_unclipped_DN16"]
    }
    ramp_rows = {(r["model"], r["policy"], r["pattern"]): r for r in result["native_ramps"]}
    methods = {}

    def close(name, current, expected):
        error = abs(float(current) - float(expected))
        if not math.isfinite(error) or error > 1e-10:
            raise ValueError(f"Independent scalar mismatch: {name}, error={error}")
        errors[name] = max(errors.get(name, 0), error)

    for model in gpu["models"]:
        captures = {(r["policy"], r["fixture"]): r for r in model["captures"]}
        methods[model["model"]] = captures
        for fixture in plan["fixtures"]:
            host = arrays(fixture["arrays"])
            shape = (
                len(host["packed"]),
                3,
                host["packed"].shape[-2] * 2,
                host["packed"].shape[-1] * 2,
            )
            predictions = {}
            for policy in ("fp32", "fp16", "fp16-hidden"):
                capture = captures[policy, fixture["id"]]
                values = prediction(capture["RGB"], shape)
                predictions[policy] = values
                if fixture["kind"] == "photo":
                    metrics = quality_metrics(
                        *(
                            torch.from_numpy(v)
                            for v in (values, host["target"], host["wb"], host["matrix"])
                        )
                    )
                    previous = saved[model["model"], policy, fixture["id"], "null"]
                    for name in ("srgb_psnr", "srgb_ssim"):
                        close(
                            "canonical_" + name, metrics[name][0], previous["canonical_FP32"][name]
                        )
                        photo_fields += 1
                elif fixture["kind"] == "analytic":
                    wb, matrix = (torch.from_numpy(host[k]) for k in ("wb", "matrix"))
                    pred, target = (
                        linear_srgb(torch.from_numpy(v), wb, matrix)
                        for v in (values, host["target"])
                    )
                    metrics = (
                        response_metrics(pred, target, fixture["cases"][0]["period"])
                        if fixture["signal_kind"] == "carrier"
                        else flat_metrics(pred, target)
                    )
                    for j, case in enumerate(fixture["cases"]):
                        previous = saved[
                            model["model"], policy, fixture["id"], json.dumps(case, sort_keys=True)
                        ]
                        for name, metric in metrics.items():
                            close("analytic_" + name, metric[j], previous["metrics"][name])
                            analytic_fields += 1
            for policy in ("fp16", "fp16-hidden"):
                delta = (
                    torch.from_numpy(predictions[policy]).double()
                    - torch.from_numpy(predictions["fp32"]).double()
                )
                previous = physical[model["model"], policy, fixture["id"]]
                if delta.numel() != previous["RGB_values"]:
                    raise ValueError("Physical difference coverage changed")
                close(
                    "physical_max_DN16", delta.abs().max().item() * 65535, previous["max_abs_DN16"]
                )
                close(
                    "physical_RMS_DN16",
                    delta.square().mean().sqrt().item() * 65535,
                    previous["RMS_DN16"],
                )
                physical_values += delta.numel()
        first_id = plan["fixtures"][0]["id"]
        for sample in model["timings"]:
            if sample["kind"] != "synchronized-resident-unhooked-sample":
                continue
            checked(sample["RGB"])
            original = captures[sample["policy"], first_id]["RGB"]
            # File hashes establish byte identity, including signed-zero encodings.
            same = sample["RGB"]["sha256"] == original["sha256"]
            if same != sample["byte_equal_first_capture"] or not same:
                raise ValueError("Timed repeat is not independently byte-identical")
            repeats += 1
        base, plus = plan["fixtures"][-2:]
        for policy in ("fp32", "fp16", "fp16-hidden"):
            a = torch.from_numpy(
                prediction(captures[policy, base["id"]]["RGB"], (4, 3, 256, 256))
            ).double()
            b = torch.from_numpy(
                prediction(captures[policy, plus["id"]]["RGB"], (4, 3, 256, 256))
            ).double()
            codes = (a.clamp(0, 1) * 65535).round().long()
            for j, pattern in enumerate(base["patterns"]):
                previous = ramp_rows[model["model"], policy, pattern]
                if torch.unique(codes[j]).numel() != previous["codes"]:
                    raise ValueError("Independent native code count differs")
                close(
                    "native_one_DN_RMS",
                    (b[j] - a[j]).square().mean().sqrt(),
                    previous["one_DN_response_RMS"],
                )
                ramp_fields += 2
    if (analytic_fields, photo_fields, physical_values, repeats, ramp_fields) != (
        3840,
        24,
        95944704,
        24,
        48,
    ):
        raise ValueError("Incomplete independent review coverage")
    guard(protocol)
    guard(plan)
    if torch.cuda.is_initialized():
        raise ValueError("Independent replay initialized CUDA")
    save_new(
        output,
        {
            "status": "completed-independent-Torch-replay-of-mature-precision-screen",
            "driver": ref(__file__),
            "protocol": ref(protocol_path),
            "result": ref(result_path),
            "analytic_fields": analytic_fields,
            "canonical_photo_fields": photo_fields,
            "physical_RGB_difference_values": physical_values,
            "repeat_files_SHA256_exact": repeats,
            "native_ramp_fields": ramp_fields,
            "maximum_scalar_replay_errors": errors,
            "CUDA_initialized": False,
            "new_network_forwards": 0,
            "scope": "Independent CPU Torch analytic/difference/ramp arithmetic over genuine completed outputs; photo canonical metrics repeat exactly and all24 timed output files are SHA256-identical to their first capture. Scalar parity bound1e-10 is separate from unchanged policy noninferiority limits. No new inference, population quality, full-frame timing, default change or promotion.",
        },
    )
    print(
        {
            "status": "completed-independent-Torch-replay",
            "analytic_fields": analytic_fields,
            "physical_values": physical_values,
            "exact_repeat_files": repeats,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("protocol", "result", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    main(args.protocol, args.result, args.output)
