"""Inspect an exited mixed16 arm on fixed CPU photos/contexts while its peer trains.

This selected native-pixel review does not release the matched GPU review, alter
training, replace full-frame exports, or support population quality/speed claims.
"""

import argparse
import gc
import json
import os
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml
from PIL import Image, ImageDraw
from review_mixed_packed_trial import (
    check_observations,
    check_worker,
    original_data_matches,
    read,
    ref,
    rows,
    sha,
    source_bundle,
)

from demosaic.cfa import malvar, pack, unpack
from demosaic.inference import load_checkpoint
from demosaic.noise import variance_map
from demosaic.precision import amp_context
from demosaic.reference import load_rawnind, publisher_input_scale
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path


def batch(path):
    with np.load(path, allow_pickle=False) as arrays:
        return {key: torch.from_numpy(value.copy()) for key, value in arrays.items()}


def verify_png(output, crop, panels):
    path = output / crop["image"]
    assert sha(path) == crop["png_sha256"]
    with Image.open(path) as image:
        assert image.size == (512, 192) and image.mode == "RGB"
        for panel, values in zip(crop["panels"], panels, strict=True):
            x, y, w, h = panel["png_xywh"]
            assert (w, h) == (160, 160)
            expected = np.rint(np.clip(values, 0, 1) * 255).astype(np.uint8)
            np.testing.assert_array_equal(np.array(image.crop((x, y, x + w, y + h))), expected)


def board(output, crops, labels, cases, filename):
    # All tiles are copied at native scale; only labels/margins are added.
    left, cell, top, row = 140, 168, 32, 184
    image = Image.new("RGB", (left + cell * len(cases), top + row * (len(labels) + 2)), "white")
    draw = ImageDraw.Draw(image)
    for column, case in enumerate(cases):
        draw.text((left + column * cell, 8), case, fill="black")
        selected = [c for c in crops if c["case"] == case]
        assert len(selected) == len(labels)
        reference_label = "GT (synthetic)" if case.startswith("photo-") else "ISO100 ref, not GT"
        for index, label in enumerate(["Noisy Malvar", *labels, reference_label]):
            draw.text((4, top + index * row + 8), label, fill="black")
            crop = (
                selected[0]
                if index in [0, len(labels) + 1]
                else next(c for c in selected if c["method"] == label)
            )
            panel = crop["panels"][0 if index == 0 else 2 if index == len(labels) + 1 else 1]
            x, y, w, h = panel["png_xywh"]
            with Image.open(output / crop["image"]) as source:
                image.paste(
                    source.crop((x, y, x + w, y + h)),
                    (left + column * cell, top + index * row + 24),
                )
    path = output / filename
    image.save(path)
    return ref(path)


@torch.inference_mode()
def main(review_plan, inputs, arm_name, output):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), (
        "Hide CUDA for this CPU-only preview"
    )
    torch.set_num_threads(2)
    os.nice(10)
    plan, fixture = read(review_plan), read(inputs)
    training = read(plan["training_workflow"])
    assert training["plan"] == plan["training_plan"] == ref(training["plan"]["path"])
    train_plan = read(training["plan"]["path"])
    for collection in [plan, train_plan]:
        for path, digest in {**collection["inputs"], **collection["guards"]}.items():
            assert sha(path) == digest, path
    for path, digest in fixture["files"].items():
        assert sha(path) == digest, path
    arm = next(a for a in train_plan["arms"] if a["arm"] == arm_name)
    if "finish-" + arm_name not in training["completed"]:
        raise RuntimeError("Selected arm has not archived its completed first gate")
    recipe = yaml.safe_load(Path(arm["config"]).read_text())
    bundle = source_bundle(train_plan, recipe)
    for phase in ["prefix", "finish"]:
        check_worker(training, train_plan, arm, phase, bundle)
    records = [r for r in rows(Path(recipe["run"]) / "metrics.jsonl") if r.get("event") == "train"]
    check_observations(records)
    assert original_data_matches(records, rows(plan["original_RAW_metrics"]["path"])) == 82
    # Use exactly the trained package, rather than whatever happens to be installed.
    source_files = {}
    import demosaic

    for source in Path(demosaic.__file__).parent.glob("*.py"):
        expected = Path(train_plan["work"]) / "src/demosaic" / source.name
        assert sha(source) == sha(expected), source
        source_files[str(source)] = sha(source)
    checkpoints = [
        {**ref(arm["target"]), "label": f"V{arm['version']} {arm_name} new2k/32kex"},
        {
            **next(
                c
                for c in plan["matched_budget_references"]
                if ("V71" if arm_name == "no-dino" else "V70") in c["label"]
            ),
            "label": "Original RAW8k/32kex",
        },
        {
            **ref(
                Path(arm["target"]).parent
                / (
                    "no-dino-packed-isotropic-b4-v71-step40000.pt"
                    if arm_name == "no-dino"
                    else "dino-packed-isotropic-b4-v70-step40000.pt"
                )
            ),
            "label": "Original RAW40k/160kex",
        },
        *[
            {**c, "label": label}
            for c, label in zip(plan["references"], ["V43 working", "V63 mature"], strict=True)
        ],
    ]
    assert checkpoints[2]["sha256"] == (
        "5708fdc19542ca1ef1aaafec25038dc049e4f5027782809846cf6d888ebed2cc"
        if arm_name == "no-dino"
        else "4c2926e77dc5dea8580879eff9ebb69550fa891a295fa329a5800189c7fa8337"
    )
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    source_dir = output / "source"
    source_dir.mkdir()
    for path in [Path(__file__), *map(Path, source_files)]:
        (source_dir / path.name).write_bytes(path.read_bytes())
    cases = []
    for index, entry in enumerate(fixture["photos"]):
        values = batch(entry["observation"]["path"])
        metadata = entry["metadata"]
        cases.append(
            {
                "name": f"photo-{index}",
                "values": values,
                "roi": metadata["evaluation_tile_xywh"],
                "reference": values["target"],
                "reference_roi": metadata["evaluation_tile_xywh"],
                "condition": metadata["condition"],
                "exposure": metadata["display_exposure"],
                "metadata": metadata,
                "observation": entry["observation"],
            }
        )
    values = batch(fixture["serving_probes"][0]["observation"]["path"])
    raw = np.load(fixture["full_raw"]["path"], allow_pickle=False, mmap_mode="r")
    aligned, aligned_contexts = [], []
    for index, entry in enumerate(fixture["gfx_regions"]):
        context = entry["context_xywh"]
        x, y = context[0] // 32 * 32, context[1] // 32 * 32
        region = entry["region"]
        old_x, old_y = region["noisy_xy"][0] - context[0], region["noisy_xy"][1] - context[1]
        new_x, new_y = region["noisy_xy"][0] - x, region["noisy_xy"][1] - y
        tile = torch.from_numpy(raw[y : y + 512, x : x + 512].copy())[None, None]
        assert tile.shape == (1, 1, 512, 512)
        # The native standing ROI is unchanged. Only the surrounding input
        # window moves to a common32-pixel grid for all trunks/reference models.
        torch.testing.assert_close(
            tile[..., new_y : new_y + 160, new_x : new_x + 160],
            unpack(values["packed"][index : index + 1])[
                ..., old_y : old_y + 160, old_x : old_x + 160
            ],
            rtol=0,
            atol=0,
        )
        aligned.append(pack(tile))
        aligned_contexts.append([x, y, 512, 512])
    values["packed"] = torch.cat(aligned)
    values["variance"] = variance_map(
        values["packed"], fixture["conditioning"]["shot"], fixture["conditioning"]["read"]
    )
    aligned_path = output / "GFX-common32-grid-native512.npz"
    np.savez(aligned_path, **{key: value.numpy() for key, value in values.items()})
    aligned_ref = ref(aligned_path)
    for index, entry in enumerate(fixture["gfx_regions"]):
        region, context = entry["region"], aligned_contexts[index]
        cases.append(
            {
                "name": region["name"],
                "values": {k: v[index : index + 1] for k, v in values.items()},
                "roi": [
                    region["noisy_xy"][0] - context[0],
                    region["noisy_xy"][1] - context[1],
                    160,
                    160,
                ],
                "reference": torch.from_numpy(
                    np.load(entry["reference_RGB"]["path"], allow_pickle=False).copy()
                ),
                "reference_roi": [0, 0, 160, 160],
                "condition": fixture["conditioning"],
                "exposure": fixture["display_exposure"],
                "metadata": {
                    **entry,
                    "fixture_context_xywh": entry["context_xywh"],
                    "context_xywh": context,
                    "context_alignment_sensor_pixels": 32,
                    "raw_selection": fixture["full_raw"],
                    "source": fixture["gfx_sources"],
                    "full_frame": False,
                    "reference": entry["reference"],
                },
                "observation": {**aligned_ref, "sample_index": index},
            }
        )
    rawnind_weight = plan["rawnind_weights"]
    assert ref(rawnind_weight["path"]) == rawnind_weight
    methods = [
        *checkpoints,
        *[
            {**rawnind_weight, "label": "RawNIND " + mode, "gain_mode": mode}
            for mode in ["cfa-ls", "cfa-channel"]
        ],
    ]
    crops, predictions, receipts = [], [], []
    for method_index, method in enumerate(methods):
        assert ref(method["path"])["sha256"] == method["sha256"]
        if "gain_mode" in method:
            model = load_rawnind(plan["rawnind"], gain_mode=method["gain_mode"], device="cpu")
            receipt = {
                **method,
                "gain": "Observed input CFA only; no target fit",
                "compute_precision": "IEEE float32",
            }
        else:
            model, state = load_checkpoint(method["path"], "cpu")
            receipt = {
                **method,
                "step": state["step"],
                "model_config": model.config.to_dict(),
                "training_config": state["config"],
                "compute_precision": "IEEE float32",
            }
            del state
        model.eval()
        receipts.append(receipt)
        for case in cases:
            data = case["values"]
            if hasattr(model, "set_noise"):
                model.set_noise(case["condition"]["shot"], case["condition"]["read"])
            if "gain_mode" in method:
                meta = fixture["gfx_metadata"]
                model.input_scale = (
                    None
                    if case["name"].startswith("photo-")
                    else torch.tensor(
                        publisher_input_scale(
                            meta["white_levels"], meta["black_levels"], meta["adc_white_level"]
                        )
                    ).reshape(4)
                )
            with amp_context("cpu", dtype="float32"):
                prediction = model(
                    *(data[key] for key in ["packed", "variance", "colors", "wb", "matrix"])
                )
            assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
            path = output / f"method{method_index}-{case['name']}-RGB-f32.npy"
            np.save(path, prediction.numpy(), allow_pickle=False)
            assert np.array_equal(np.load(path, allow_pickle=False), prediction.numpy())
            saved = {
                **ref(path),
                "method": method["label"],
                "case": case["name"],
                "shape": list(prediction.shape),
                "dtype": "float32",
            }
            predictions.append(saved)
            wb, matrix = data["wb"], data["matrix"]
            values = [
                display_crop(value, wb, matrix, roi, exposure=case["exposure"])
                for value, roi in [
                    (malvar(data["packed"], data["colors"], wb), case["roi"]),
                    (prediction, case["roi"]),
                    (case["reference"], case["reference_roi"]),
                ]
            ]
            synthetic = case["name"].startswith("photo-")
            crop = save_triplet(
                output,
                method["label"] + case["name"],
                list(
                    zip(
                        [
                            "Noisy Malvar",
                            method["label"],
                            "GT (synthetic)" if synthetic else "ISO100 ref, not GT",
                        ],
                        values,
                        strict=True,
                    )
                ),
                caption=method["label"] + " / " + case["name"],
                metadata={
                    **case["metadata"],
                    "method": method["label"],
                    "case": case["name"],
                    "checkpoint_sha256": method["sha256"],
                    "model": receipt,
                    "observation": case["observation"],
                    "prediction": saved,
                    "conditioning": case["condition"],
                    "display_exposure": case["exposure"],
                    "context_roi_xywh": case["roi"],
                    "reference_roi_xywh": case["reference_roi"],
                    "white_balance": wb[0].tolist(),
                    "camera_to_srgb": matrix[0].tolist(),
                    "compute_precision": "IEEE float32, CPU",
                },
            )
            verify_png(output, crop, values)
            crops.append(crop)
            print(
                json.dumps(
                    {
                        "method": method["label"],
                        "case": case["name"],
                        "native_triplet": crop["image"],
                    }
                ),
                flush=True,
            )
        del model
        gc.collect()
    boards = [
        board(output, crops, [m["label"] for m in methods], names, filename)
        for names, filename in [
            (["photo-0", "photo-1"], "photos-native-board.png"),
            (
                ["overcast-sky", "building-detail", "foliage", "chain-link-fence"],
                "GFX-contexts-native-board.png",
            ),
        ]
    ]
    assert len(crops) == len(predictions) == 42
    assert all(sha(path) == digest for path, digest in source_files.items())
    assert not torch.cuda.is_initialized()
    result = {
        "status": "completed-selected-trained-arm-CPU-native-preview-awaiting-manual-view-and-full-matched-review",
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "training": ref(plan["training_workflow"]),
        "training_plan": plan["training_plan"],
        "selected_arm": arm_name,
        "selected_boundary": training["completed"]["finish-" + arm_name],
        "selected_arm_all82_logs_and_original_source_noise_match": True,
        "inputs": ref(inputs),
        "GFX_aligned_contexts": aligned_ref,
        "standing_ROI_sensor_samples_bitwise_equal_to_frozen_contexts": True,
        "driver": ref(__file__),
        "source_files": source_files,
        "methods": receipts,
        "native_crops": crops,
        "float_predictions": predictions,
        "native_boards": boards,
        "CUDA_initialized": False,
        "scope": "Selected fixed CPU observations/IEEEFP32 only: two exact-synthetic-GT photos and four native512 GFX contexts; not full-frame CUDA predictions or population statistics. New arm has2000 effective16 updates/32000 examples; original8kB4 has same examples,40kB4 has160000. Mature V43/V63 have other histories. RawNIND adapters share weights with observed-CFA gain fits. GFX independent ISO100 f/5.6 capture differs in optics/time/moving subjects; not GT. No training or recipe/queue change, final-panel reuse, automatic promotion or speed claim. Manual inspection remains.",
    }
    (output / "report.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--arm", choices=["no-dino", "dino"], required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.review_plan, args.inputs, args.arm, args.output)
