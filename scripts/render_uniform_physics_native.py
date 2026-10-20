"""Native crop package from audited saved arrays; no model forward or resized pixels."""

import argparse
import hashlib
import os
import random
from pathlib import Path

import numpy as np
import torch
from audit_uniform_physics_arrays import completed
from build_native_crop_board import build
from PIL import Image
from train_directional_bank_trial import read, ref, save

from demosaic.cfa import PATTERNS, malvar
from demosaic.data import camera_pair
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path

FIXTURE = Path(
    "/mnt/external/demosaic/benchmarks/packed-isotropic-compilation-inputs-v1/inputs.json"
)
FIXTURE_SHA = "11655660520041c0b9255f197758c6c313ef50834605dc78350c1e5c6f3d8784"


def png_parts(output, crop):
    path = Path(output) / crop["image"]
    assert ref(path)["sha256"] == crop["png_sha256"]
    with Image.open(path) as image:
        assert image.mode == "RGB" and image.size == (512, 192)
        pixels = np.asarray(image).copy()
    parts = []
    for p in crop["panels"]:
        x, y, w, h = p["png_xywh"]
        assert (w, h) == (160, 160)
        parts.append(pixels[y : y + h, x : x + w])
    return parts


def photo_target(metadata, batch):
    source = metadata["source"]
    assert ref(source["cache"])["sha256"] == source["cache_sha256"]
    values = np.load(source["cache"], mmap_mode="r", allow_pickle=False)
    rng = random.Random(metadata["validation_seed"] + metadata["validation_index"])
    rng.random()
    y, x = rng.randrange(values.shape[0] - 256 + 1), rng.randrange(values.shape[1] - 256 + 1)
    rgb = torch.from_numpy(values[y : y + 256, x : x + 256].copy().astype(np.float32))
    rgb = rgb.permute(2, 0, 1)[None] / 65535
    _, replay = camera_pair(
        rgb, torch.linalg.inv(batch["matrix"]), batch["wb"], reconstruct_highlights=True
    )
    torch.testing.assert_close(batch["target"], replay, atol=1e-7, rtol=0)
    return batch["target"], {
        "source_id": metadata["source_id"],
        "source": source,
        "condition": metadata["condition"],
        "evaluation_tile_xywh": [48, 48, 160, 160],
        "source_cache_context_xywh": [x, y, 256, 256],
        "source_cache_ROI_xywh": [x + 48, y + 48, 160, 160],
        "reference": "Exact saved synthetic GT; replayed from its original 8x-binned source cache",
    }


@torch.inference_mode()
def render_cases(
    cases,
    output,
    *,
    original_key="original",
    candidate_label="Batched FP32",
    evidence="actual-uniform-physics-CUDA",
):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    assert ref(FIXTURE)["sha256"] == FIXTURE_SHA
    fixture = read(FIXTURE)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    rng = torch.get_rng_state().clone()
    crops, common, reports, boards = [], {}, [], []
    for case in cases:
        label = case["fixture"]["label"]
        if label == "analytic-four-CFA-native512":
            continue  # All values are audited; the fixed photographic/GFX views are unchanged.
        observation = case["fixture"]["observation"]
        assert (
            ref(observation["path"]) == observation
            and ref(case["arrays"]["path"]) == case["arrays"]
        )
        with np.load(observation["path"], allow_pickle=False) as data:
            batch = {k: torch.from_numpy(data[k].copy()) for k in data.files}
        photo = label.startswith("photo")
        if photo:
            index = int(label[5])
            item = fixture["photos"][index]
            assert item["observation"] == observation
            target, metadata = photo_target(item["metadata"], batch)
            items = [(0, f"photo{index}", [48, 48, 160, 160], 1.0, target, metadata)]
        else:
            assert (
                label == "GFX-four-native512"
                and observation == fixture["serving_probes"][0]["observation"]
            )
            items = []
            for index, region in enumerate(fixture["gfx_regions"]):
                assert ref(region["noisy_packed"]["path"]) == region["noisy_packed"]
                packed = np.load(region["noisy_packed"]["path"], allow_pickle=False)
                assert np.array_equal(packed, batch["packed"][index : index + 1].numpy())
                assert ref(region["reference_RGB"]["path"]) == region["reference_RGB"]
                target = torch.from_numpy(
                    np.load(region["reference_RGB"]["path"], allow_pickle=False).copy()
                )
                assert tuple(target.shape) == (1, 3, 160, 160)
                px, py = region["region"]["noisy_xy"]
                cx, cy, _, _ = region["context_xywh"]
                items.append(
                    (
                        index,
                        region["region"]["name"],
                        [px - cx, py - cy, 160, 160],
                        4.0,
                        target,
                        {
                            "region": region["region"],
                            "context_xywh": region["context_xywh"],
                            "reference_RGB": region["reference_RGB"],
                            "source": fixture["gfx_sources"],
                            "reference": region["reference"],
                            "full_frame": False,
                        },
                    )
                )
        for key in ("shot", "read"):
            expected = (
                fixture["photos"][index]["metadata"]["condition"][key]
                if photo
                else fixture["conditioning"][key]
            )
            assert case["fixture"]["conditioning"][key] == expected
        with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
            for index, name, roi, exposure, target, metadata in items:
                wb, matrix = batch["wb"][index : index + 1], batch["matrix"][index : index + 1]
                colors = batch["colors"][index : index + 1]
                pattern = next(
                    k for k, v in PATTERNS.items() if colors.flatten().tolist() == list(v)
                )
                noisy = display_crop(
                    malvar(batch["packed"][index : index + 1], colors),
                    wb,
                    matrix,
                    roi,
                    exposure=exposure,
                )
                reference = display_crop(
                    target, wb, matrix, roi if photo else [0, 0, 160, 160], exposure=exposure
                )
                for policy, array_key, caption in [
                    ("original", original_key, "Original FP32"),
                    ("candidate", "candidate", candidate_label),
                ]:
                    predicted = torch.from_numpy(arrays[array_key][index : index + 1].copy())
                    restored = display_crop(predicted, wb, matrix, roi, exposure=exposure)
                    key = f"{case['model']}:{name}:{policy}:{evidence}"
                    crop = save_triplet(
                        output,
                        key,
                        [
                            ("Noisy (Malvar)", noisy),
                            (caption, restored),
                            ("GT (synthetic)" if photo else "ISO100 ref (not GT)", reference),
                        ],
                        caption=key,
                        metadata={
                            **metadata,
                            "model": {
                                "label": f"{case['model']} / {caption}",
                                "sha256": case["checkpoint"]["sha256"],
                                "base_label": case["model"],
                                "policy": policy,
                            },
                            "checkpoint": case["checkpoint"],
                            "fixture_label": name,
                            "observation": observation,
                            "predictions": case["arrays"],
                            "conditioning": case["fixture"]["conditioning"],
                            "ROI_xywh": roi,
                            "pattern": pattern,
                            "white_balance": wb.tolist(),
                            "camera_to_srgb": matrix.tolist(),
                            "display_exposure": exposure,
                            "compute_precision": "float32",
                            "prediction_evidence": evidence,
                            "render_device": "CPU",
                        },
                    )
                    parts = png_parts(output, crop)
                    pair = parts[0], parts[2]
                    if name in common:
                        assert all(
                            np.array_equal(a, b) for a, b in zip(pair, common[name], strict=True)
                        )
                    else:
                        common[name] = tuple(p.copy() for p in pair)
                    crop["panel_pixel_sha256"] = [
                        hashlib.sha256(p.tobytes()).hexdigest() for p in parts
                    ]
                    # Keep panel hashes inside method metadata for shared-metadata board checks.
                    crop["model"]["panel_pixel_sha256"] = crop.pop("panel_pixel_sha256")
                    crops.append(crop)
    assert len(crops) == 24
    for model in ["V43", "V63"]:
        for photo, kind in [(True, "synthetic"), (False, "gfx")]:
            selected = [
                c
                for c in crops
                if c["model"]["base_label"] == model
                and c["fixture_label"].startswith("photo") is photo
            ]
            assert len(selected) == (4 if photo else 8)
            path = output / f"{model}-{kind}-sources.json"
            save(path, {"native_crops": selected, "evidence": evidence})
            board = build([path], output / f"{model}-{kind}-native.png", kind)
            reports.append(ref(path))
            boards.append(board)
    assert torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    save(
        output / "report.json",
        {
            "status": "prepared-native-views-awaiting-actual-inspection",
            "driver": ref(__file__),
            "fixture": ref(FIXTURE),
            "evidence": evidence,
            "native_crops": crops,
            "reports": reports,
            "boards": boards,
            "native_source_triplets": len(crops),
            "displayed_board_cells": sum(b["native_cells_exact"] for b in boards),
            "photo_targets_replayed_from_source_caches": True,
            "shared_noisy_reference_panels_exact": True,
            "resized_pixels": False,
            "manual_review_completed": False,
            "CUDA_initialized": False,
        },
    )
    return output / "report.json"


def main(audit_path, output):
    audit = read(audit_path)
    assert audit["status"] == "audited-complete-uniform-physics-CUDA-arrays-awaiting-native-review"
    gpu, result, source = completed(Path(audit["controller_plan"]["path"]))
    assert ref(audit["controller_plan"]["path"]) == audit["controller_plan"]
    assert source == audit["worker_result"] and len(result["cases"]) == len(audit["cases"]) == 8
    assert all(c["passes_original_limits"] for c in audit["cases"])
    assert audit["GPU_plan"] == read(audit["controller_plan"]["path"])["GPU_plan"]
    assert ref(FIXTURE) in gpu["inputs"]
    report = render_cases(result["cases"], output)
    save(
        output / "audit-binding.json",
        {"array_audit": ref(audit_path), "native_report": ref(report)},
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("array_audit", type=Path)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    main(a.array_audit.resolve(), a.output.resolve())
