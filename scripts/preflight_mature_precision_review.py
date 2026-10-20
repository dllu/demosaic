"""Audit review math and rendering using genuine historical saved outputs only."""

import argparse
import json
import os
from pathlib import Path

import numpy as np
from build_native_crop_board import digest
from mature_precision_review_tools import (
    carrier_metrics,
    display_metrics,
    flat_metrics,
    input_fingerprint,
    linear_rgb,
)
from PIL import Image
from render_mature_precision import arrays, checked, historical_methods, prediction, save_new
from train_directional_bank_trial import read, ref


def main(plan_path, render_index, component_plan_path, output):
    import torch
    from diagnose_texture_response import response_metrics
    from evaluate_texture_candidates import flat_metrics as torch_flat

    from demosaic.metrics import quality_metrics
    from demosaic.train import batch_fingerprint

    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or torch.cuda.is_initialized():
        raise ValueError("Review preflight must remain CPU-only")
    torch.set_num_threads(2)
    plan, index = read(plan_path), read(render_index)
    if index["triplets"] != 24 or index["native_cells_exact"] != 36:
        raise ValueError("Expected all historical FP32 methods and fixed photo/GFX crops")
    methods, evidence = historical_methods(plan, index["gfx_registry"])
    if index["methods"] != methods or index["evidence"] != [*evidence, ref(plan_path)]:
        raise ValueError("Preflight must retain genuine historical FP32 policy identities")
    gfx_path = checked(index["gfx_registry"])
    gfx = read(gfx_path)
    exact_triplets, exact_cells = 0, 0
    for item in index["boards"]:
        board = read(checked(item))
        pixels = np.asarray(Image.open(checked(board["board"])))
        for cell in board["cells"]:
            x, y, w, h = cell["board_xywh"]
            if (w, h) != (160, 160) or digest(pixels[y : y + h, x : x + w].tobytes()) != cell[
                "pixel_sha256"
            ]:
                raise ValueError("Native board changed a source crop pixel")
            exact_cells += 1
        for entry in board["source_triplets"]:
            crop = entry["crop"]
            checked(entry["image"])
            model, policy = crop["model_label"].split(":")
            policy = policy.removesuffix("-FP32")
            if board["kind"] == "synthetic":
                source = (
                    checked(plan["photo_registry"]).parent.parent
                    / f"{model}-{policy}"
                    / "result.json"
                )
                original = next(
                    c for c in read(source)["native_crops"] if c["source_id"] == crop["source_id"]
                )
            else:
                original = next(
                    c
                    for c in gfx["native_crops"]
                    if c["model_label"] == crop["model_label"]
                    and c["region"]["name"] == crop["region"]["name"]
                )
            if crop["png_sha256"] != original["png_sha256"]:
                raise ValueError(
                    "Historical replay must reproduce the complete original PNG byte for byte"
                )
            exact_triplets += 1
    fingerprint_count = 0
    for fixture in plan["fixtures"]:
        host = arrays(fixture["arrays"])
        tensors = {
            k: torch.from_numpy(host[k]) for k in ("packed", "variance", "colors", "wb", "matrix")
        }
        if input_fingerprint(host) != batch_fingerprint(tensors):
            raise ValueError("Independent NumPy physical input fingerprint differs")
        fingerprint_count += 1
    photo_difference = {"srgb_psnr": 0.0, "srgb_ssim": 0.0}
    for method in methods:
        for fixture in plan["fixtures"][1:3]:
            host = arrays(fixture["arrays"])
            pred = prediction(method["RGB"][fixture["id"]], (1, 3, 256, 256))
            fp32 = quality_metrics(
                *(torch.from_numpy(v) for v in (pred, host["target"], host["wb"], host["matrix"]))
            )
            f64 = display_metrics(pred, host["target"], host["wb"], host["matrix"])
            for key, previous_difference in photo_difference.items():
                error = abs(float(fp32[key][0]) - float(f64[key][0]))
                if not np.isfinite(error):
                    raise ValueError("Historical metric comparison must be finite")
                photo_difference[key] = max(previous_difference, error)
    component = read(component_plan_path)
    component_root = Path(component["root"])
    gpu_path = component_root / "GPU-output/receipt.json"
    gpu = read(gpu_path)
    if gpu["plan"] != ref(component_plan_path):
        raise ValueError("Historical analytic outputs name a different plan")
    original_metrics_path = component_root / "scalar-review/per-case.jsonl"
    original_rows = [json.loads(line) for line in original_metrics_path.read_text().splitlines()]
    old = {
        (r["method"], r["fixture_id"], r["case"]["pattern"], r["case"]["draw"]): r["metrics"]
        for r in original_rows
    }
    methods = [
        ("parent", "full", "V63 parent"),
        ("global", "full", "V90 full"),
        ("global", "bypass", "V90 pre-head / diagnostic"),
        ("spatial", "full", "V91 full"),
        ("spatial", "bypass", "V91 pre-head / diagnostic"),
        ("spatial", "pooled", "V91 pooled / diagnostic"),
    ]
    records = {(r["model"], r["fixture_id"]): r for r in gpu["records"]}
    replay_error, torch_error, rows, torch_fields = {}, {}, 0, 0
    for fixture in component["fixtures"]:
        host = arrays(fixture["arrays"])
        target = linear_rgb(host["target"], host["wb"], host["matrix"])
        saved = {
            role: arrays(records[role, fixture["id"]]["arrays"])
            for role in ("parent", "global", "spatial")
        }
        for role, policy, label in methods:
            pred = linear_rgb(saved[role][policy], host["wb"], host["matrix"])
            values = (
                carrier_metrics(pred, target, fixture["cases"][0]["period"])
                if fixture["kind"] == "carrier"
                else flat_metrics(pred, target)
            )
            for j, case in enumerate(fixture["cases"]):
                previous = old[label, fixture["id"], case["pattern"], case["draw"]]
                for key, current in values.items():
                    error = abs(float(current[j]) - previous[key])
                    if error > 1e-10:
                        raise ValueError("NumPy review math fails historical saved scalar replay")
                    replay_error[key] = max(replay_error.get(key, 0), error)
                rows += 1
            if role == "parent":
                args = [torch.from_numpy(v) for v in (pred, target)]
                independent = (
                    response_metrics(*args, fixture["cases"][0]["period"])
                    if fixture["kind"] == "carrier"
                    else torch_flat(*args)
                )
                for key, current in values.items():
                    error = float(np.max(np.abs(np.asarray(independent[key]) - current)))
                    if error > 1e-10:
                        raise ValueError(
                            "NumPy/Torch independent analytic implementations disagree"
                        )
                    torch_error[key] = max(torch_error.get(key, 0), error)
                    torch_fields += len(current)
    if (exact_triplets, exact_cells, fingerprint_count, rows, torch_fields) != (
        24,
        36,
        29,
        576,
        640,
    ):
        raise ValueError("Historical engineering audit coverage differs")
    if torch.cuda.is_initialized():
        raise ValueError("Historical preflight initialized CUDA")
    result = {
        "status": "completed-historical-CPU-only-mature-review-tool-preflight",
        "driver": ref(__file__),
        "GPU_plan": ref(plan_path),
        "render_index": ref(render_index),
        "component_plan": ref(component_plan_path),
        "component_GPU_receipt": ref(gpu_path),
        "historical_scalar_rows": ref(original_metrics_path),
        "exact_original_PNGs": exact_triplets,
        "exact_native_board_cells": exact_cells,
        "independent_input_fingerprints": fingerprint_count,
        "historical_analytic_rows_replayed": rows,
        "independent_Torch_analytic_fields": torch_fields,
        "maximum_saved_scalar_replay_errors": replay_error,
        "maximum_NumPy_Torch_analytic_errors": torch_error,
        "maximum_historical_photo_FP32_vs_independent_float64_differences": photo_difference,
        "CUDA_initialized": False,
        "new_network_forwards": 0,
        "scope": "Genuine historical FP32 saved-output engineering preflight only. No FP16 predictions or completed CUDA pilot, fake manual-viewing record, new photographic performance result, timing conclusion, training, promotion or default change. Production FP32 and independent float64 photo metrics retain different arithmetic and must both pass prospective gates.",
    }
    save_new(output, result)
    print(
        {
            "status": result["status"],
            "exact_PNGs": exact_triplets,
            "analytic_rows": rows,
            "Torch_fields": torch_fields,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("GPU_plan", "render_index", "component_plan", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    main(args.GPU_plan, args.render_index, args.component_plan, args.output)
