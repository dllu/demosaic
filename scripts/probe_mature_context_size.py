"""Compare the same standing sensor ROIs under256/512 and full-frame windows."""

import argparse
import copy
import json
import os
from pathlib import Path

import numpy as np
import psutil
import torch
from PIL import Image
from probe_saved_cfa_gain_grid import read, ref
from profile_raw_kernel_inference import model_hash

from demosaic.cfa import pack
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.reporting import display_crop, save_triplet


@torch.inference_mode()
def main(plan_path):
    os.nice(5)
    torch.set_num_threads(4)
    plan = read(plan_path)
    output = Path(plan["output"])
    assert ref(__file__) == plan["worker"]
    for item in [
        *plan["source_files"],
        plan["checkpoint"],
        plan["fixture"],
        plan["contexts"],
        plan["prediction512"],
        plan["prediction_full"],
        plan["raw"],
        plan["native_report"],
    ]:
        assert ref(item["path"]) == item
    old = read(plan["photo_terminal"]["path"])
    assert ref(plan["photo_terminal"]["path"]) == plan["photo_terminal"]
    assert (
        old["status"]
        == "completed-shared-forward-photo-test-awaiting-native-camera-and-decision-review"
    )
    try:
        p = psutil.Process(old["controller"]["pid"])
        assert p.create_time() != old["controller"]["created"] or p.status() == psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        pass
    assert psutil.virtual_memory().available > 32 * 2**30
    assert psutil.disk_usage(output.parent).free > 128 * 2**30
    assert not torch.cuda.is_initialized()
    torch.cuda.set_per_process_memory_fraction(
        16 * 2**30 / torch.cuda.get_device_properties(0).total_memory, 0
    )
    torch.backends.cudnn.benchmark = False
    output.mkdir(parents=True, exist_ok=False)
    fixture = read(plan["fixture"]["path"])
    with np.load(plan["contexts"]["path"], allow_pickle=False) as values:
        arrays = {k: values[k].copy() for k in values.files}
    cpu = {k: torch.from_numpy(v) for k, v in arrays.items()}
    assert cpu["packed"].shape == (4, 4, 256, 256)
    raw = np.load(plan["raw"]["path"], mmap_mode="r", allow_pickle=False)
    for i, region in enumerate(fixture["gfx_regions"]):
        x, y, w, h = region["context_xywh"]
        assert (w, h) == (512, 512)
        patch = torch.from_numpy(np.array(raw[y : y + h, x : x + w], copy=True))[None, None]
        assert torch.equal(pack(patch), cpu["packed"][i : i + 1])
    args = [cpu[k].cuda() for k in ["packed", "variance", "colors", "wb", "matrix"]]
    args[0] = args[0][..., 64:192, 64:192].contiguous(memory_format=torch.channels_last)
    args[1] = args[1][..., 64:192, 64:192].contiguous(memory_format=torch.channels_last)
    model, state = load_checkpoint(plan["checkpoint"]["path"], "cuda")
    assert state["step"] == 20000
    del state
    model.eval().to(memory_format=torch.channels_last)
    before = model_hash(model)
    model.set_noise(fixture["conditioning"]["shot"], fixture["conditioning"]["read"])
    with amp_context("cuda", dtype="float32"):
        prediction = model(*args).cpu()
    assert prediction.shape == (4, 3, 256, 256) and prediction.dtype == torch.float32
    assert torch.isfinite(prediction).all() and model_hash(model) == before
    target = output / "GFX-context256-RGB-f32.npy"
    np.save(target, prediction.numpy(), allow_pickle=False)
    prediction512 = np.load(plan["prediction512"]["path"], mmap_mode="r", allow_pickle=False)
    full = np.load(plan["prediction_full"]["path"], mmap_mode="r", allow_pickle=False)
    assert prediction512.shape == (4, 3, 512, 512) and full.shape == (3, *raw.shape)
    original_report = Path(plan["native_report"]["path"])
    templates = [
        c
        for c in read(original_report)["native_crops"]
        if c["model_label"] == "V63-step20000:original-FP32"
    ]
    assert len(templates) == 4
    crops, comparisons = [], []
    for i, template in enumerate(templates):
        assert template["region"] == fixture["gfx_regions"][i]["region"]
        source = original_report.parent / template["image"]
        assert ref(source)["sha256"] == template["png_sha256"]
        pixels = np.asarray(Image.open(source))
        x, y = template["region"]["noisy_xy"]
        cx, cy, _, _ = fixture["gfx_regions"][i]["context_xywh"]
        variants = [
            (
                "V63-context256",
                prediction.numpy()[i, :, 48:208, 48:208],
                ref(target),
                [cx + 128, cy + 128, 256, 256],
                False,
            ),
            (
                "V63-context512",
                np.array(prediction512[i, :, 176:336, 176:336], copy=True),
                plan["prediction512"],
                [cx, cy, 512, 512],
                False,
            ),
            (
                "V63-full512-overlap64",
                np.array(full[:, y : y + 160, x : x + 160], copy=True),
                plan["prediction_full"],
                [0, 0, raw.shape[1], raw.shape[0]],
                True,
            ),
        ]
        for label, values, array, extent, full_frame in variants:
            rgb = torch.from_numpy(values.copy())[None]
            model_record = {
                "label": label,
                "sha256": plan["checkpoint"]["sha256"],
                "prediction": array,
                "input_sensor_xywh": extent,
                "full_frame": full_frame,
                "ROI_xywh": [x, y, 160, 160],
                "compute_precision": "IEEE FP32",
                "memory_format": "channels_last",
                "scope": "256 newly inferred;512/full reuse verified saved unchanged-model predictions",
            }

            def panel(index, template=template, pixels=pixels):
                a, b, w, h = template["panels"][index]["png_xywh"]
                return pixels[b : b + h, a : a + w].astype(np.float64) / 255

            metadata = {
                k: copy.deepcopy(template[k])
                for k in [
                    "region",
                    "conditioning",
                    "display_exposure",
                    "shared_wb",
                    "shared_matrix",
                    "reference",
                    "source",
                    "checkpoint_sha256",
                ]
            }
            metadata["model"] = model_record
            crops.append(
                save_triplet(
                    output,
                    label + ":" + template["region"]["name"],
                    [
                        ("Noisy (Malvar)", panel(0)),
                        (
                            "Denoised",
                            display_crop(
                                rgb,
                                cpu["wb"][i : i + 1],
                                cpu["matrix"][i : i + 1],
                                [0, 0, 160, 160],
                                exposure=template["display_exposure"],
                            ),
                        ),
                        ("ISO100 ref (not GT)", panel(2)),
                    ],
                    caption=template["region"]["name"] + " / " + label,
                    metadata=metadata,
                )
            )
        for first, second in [(0, 1), (0, 2), (1, 2)]:
            delta = variants[first][1].astype(np.float64) - variants[second][1].astype(np.float64)
            comparisons.append(
                {
                    "region": template["region"]["name"],
                    "first": variants[first][0],
                    "second": variants[second][0],
                    "max_camera_RGB_difference": float(np.abs(delta).max()),
                    "RMS_camera_RGB_difference": float(np.square(delta).mean() ** 0.5),
                    "mean_camera_RGB_difference": delta.mean((1, 2)).tolist(),
                }
            )
    assert len(crops) == 12 and len(comparisons) == 12
    report = {
        "status": "completed-same-sensor-ROI-context-size-probe-awaiting-native-review",
        "plan": ref(plan_path),
        "native_crops": crops,
        "comparisons": comparisons,
        "new_model_forwards": 1,
        "model_state_unchanged": True,
        "source_observation_pixels_exact": True,
        "scope": plan["scope"],
    }
    (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps({"status": report["status"], "triplets": len(crops), "new_network_forwards": 1}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
