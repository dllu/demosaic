"""Whole-frame input-only gain from saved linear arrays, without new inference."""

import argparse
import copy
import json
import math
import os
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from probe_saved_cfa_gain_grid import read, ref

from demosaic.cfa import PATTERNS, mosaic
from demosaic.reporting import display_crop, save_triplet


def global_gain(rgb, raw, colors, *, rows=256):
    """Sum all measured samples before dividing; never average tile gains.

    Read-only CHW/HW arrays are traversed with even row chunks to retain CFA
    phase. Independent NumPy phase slices/dot products audit Torch64 sums.
    Targets, display transforms and low-noise references are unavailable here.
    """
    if rgb.ndim != 3 or rgb.shape[0] != 3 or raw.ndim != 2 or rgb.shape[1:] != raw.shape:
        raise ValueError("Expected matching CHW RGB and HW CFA")
    if rgb.dtype != np.float32 or raw.dtype != np.float32:
        raise ValueError("Saved arrays must be float32")
    if min(raw.shape) < 2 or any(size % 2 for size in raw.shape):
        raise ValueError("Whole-frame sensor dimensions must be even")
    if type(rows) is not int or rows < 2 or rows % 2:
        raise ValueError("Chunk height must be positive and even")
    if list(colors) not in [list(value) for value in PATTERNS.values()]:
        raise ValueError("Expected a declared Bayer layout")
    terms = {
        name: [[] for _ in range(3)]
        for name in ["numerator", "denominator", "numpy_numerator", "numpy_denominator"]
    }
    counts = [0, 0, 0]
    labels = torch.tensor(colors, dtype=torch.int64)[None]
    for y in range(0, raw.shape[0], rows):
        source = np.array(rgb[:, y : y + rows], copy=True)
        measured = np.stack(
            [
                np.asarray(raw[y + dy : min(y + rows, raw.shape[0]) : 2, dx::2])
                for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1)]
            ]
        )
        if not np.isfinite(source).all() or not np.isfinite(measured).all():
            raise ValueError("Nonfinite saved prediction/observation")
        predicted = mosaic(torch.from_numpy(source)[None].double(), labels)[0]
        observed = torch.from_numpy(measured).double()
        for channel in range(3):
            mask = labels[0] == channel
            p, z = predicted[mask], observed[mask]
            terms["numerator"][channel].append(float((p * z).sum()))
            terms["denominator"][channel].append(float(p.square().sum()))
            np_terms, np_squared = [], []
            for phase, color in enumerate(colors):
                if color != channel:
                    continue
                # No Torch mosaic/gain routine in this independent oracle.
                values = source[channel, phase // 2 :: 2, phase % 2 :: 2].astype(np.float64).ravel()
                noisy = measured[phase].astype(np.float64).ravel()
                np_terms.append(float(np.dot(values, noisy)))
                np_squared.append(float(np.dot(values, values)))
                counts[channel] += values.size
            terms["numpy_numerator"][channel].append(math.fsum(np_terms))
            terms["numpy_denominator"][channel].append(math.fsum(np_squared))
    sums = {name: [math.fsum(values) for values in channels] for name, channels in terms.items()}
    gains = np.asarray(sums["numerator"]) / np.maximum(sums["denominator"], 1e-12)
    oracle = np.asarray(sums["numpy_numerator"]) / np.maximum(sums["numpy_denominator"], 1e-12)
    np.testing.assert_allclose(gains, oracle, rtol=2e-12, atol=2e-12)
    assert sum(counts) == raw.size
    return {
        "gains": gains.tolist(),
        "independent_numpy_gains": oracle.tolist(),
        "max_absolute_gain_difference": float(np.max(np.abs(gains - oracle))),
        "sample_counts_per_RGB": counts,
        "sums": sums,
        "chunks": len(terms["numerator"][0]),
    }


@torch.inference_mode()
def main(plan_path):
    os.nice(10)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan = read(plan_path)
    root, output = Path(plan["root"]), Path(plan["output"])
    assert ref(__file__) == plan["worker"]
    for item in [
        *plan["source_files"],
        plan["RGB"],
        plan["raw"],
        plan["fixture"],
        plan["native_report"],
    ]:
        assert ref(item["path"]) == item
    assert psutil.virtual_memory().available > 24 * 2**30
    assert psutil.disk_usage(root).free > 128 * 2**30
    with (root / "claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "plan": ref(plan_path),
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
    }

    def record(state, **values):
        status.update(status=state, updated_unix=time.time(), **values)
        temporary = root / "status.tmp"
        temporary.write_text(json.dumps(status, indent=2) + "\n")
        temporary.replace(root / "status.json")
        print(json.dumps({"status": state}), flush=True)

    try:
        record("fitting-one-global-input-only-CFA-gain-from-saved-full-frame")
        output.mkdir(parents=True, exist_ok=False)
        fixture = read(plan["fixture"]["path"])
        rgb = np.load(plan["RGB"]["path"], mmap_mode="r", allow_pickle=False)
        raw = np.load(plan["raw"]["path"], mmap_mode="r", allow_pickle=False)
        assert rgb.shape == (3, 8746, 11662) and raw.shape == (8746, 11662)
        started = time.monotonic()
        result = global_gain(rgb, raw, PATTERNS[fixture["gfx_metadata"]["pattern"]])
        seconds = time.monotonic() - started
        gain = np.asarray(result["gains"], dtype=np.float64)
        # Check virtual corrected values across the entire frame, without saving
        # another1.2GB array or presenting a new RGB16 export/timing result.
        maximum = 0.0
        minimum = float("inf")
        upper = -float("inf")
        squared = []
        samples = 0
        for y in range(0, raw.shape[0], 256):
            before = np.array(rgb[:, y : y + 256], copy=True)
            corrected = (before.astype(np.float64) * gain[:, None, None]).astype(np.float32)
            assert np.isfinite(corrected).all()
            difference = corrected.astype(np.float64) - before.astype(np.float64)
            maximum = max(maximum, float(np.abs(difference).max()))
            squared.append(float(np.square(difference).sum()))
            samples += difference.size
            minimum = min(minimum, float(corrected.min()))
            upper = max(upper, float(corrected.max()))
        assert samples == 3 * raw.size
        source_report = Path(plan["native_report"]["path"])
        templates = [
            c
            for c in read(source_report)["native_crops"]
            if c["model_label"] == plan["original_model_label"]
        ]
        assert len(templates) == 4 and all(c["model"]["full_F32"] == plan["RGB"] for c in templates)
        from PIL import Image

        crops = []
        for template in templates:
            source = source_report.parent / template["image"]
            assert ref(source)["sha256"] == template["png_sha256"]
            shutil.copyfile(source, output / source.name)
            crops.append(copy.deepcopy(template))
            pixels = np.array(Image.open(source))

            def panel(index, template=template, pixels=pixels):
                x, y, w, h = template["panels"][index]["png_xywh"]
                return pixels[y : y + h, x : x + w].astype(np.float64) / 255

            x, y = template["region"]["noisy_xy"]
            before = np.array(rgb[:, y : y + 160, x : x + 160], copy=True)
            corrected = torch.from_numpy(
                (before.astype(np.float64) * gain[:, None, None]).astype(np.float32)
            )[None]
            wb = torch.tensor(template["shared_wb"])[None]
            matrix = torch.tensor(template["shared_matrix"])[None]
            metadata = {
                k: copy.deepcopy(v)
                for k, v in template.items()
                if k
                not in [
                    "image",
                    "caption",
                    "panels",
                    "png_sha256",
                    "pixel_scale",
                    "display_encoding",
                    "model_label",
                    "model",
                    "runtime",
                ]
            }
            label = "V63-saved-FP32-global-input-CFA-gain"
            metadata.update(
                model_label=label,
                device="CPU correction of saved CUDA prediction",
                compute_precision="Saved IEEE FP32, correction FP64 then FP32",
                model={
                    "label": label,
                    "sha256": plan["checkpoint_sha256"],
                    "base_prediction": plan["RGB"],
                    "input_only_global_gains": result["gains"],
                    "fit_samples": raw.size,
                    "correction": "FP64 multiply, cast toFP32; no target or per-tile fit",
                    "full_corrected_array_saved": False,
                },
                runtime={
                    "scope": "Reused earlier full-frame restore; no new neural inference or end-to-end timing",
                    "CPU_global_fit_seconds": seconds,
                },
            )
            crops.append(
                save_triplet(
                    output,
                    f"{label}:{template['region']['name']}",
                    [
                        ("Noisy (Malvar)", panel(0)),
                        (
                            "Denoised",
                            display_crop(
                                corrected,
                                wb,
                                matrix,
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
        report = {
            "status": "completed-saved-full-frame-global-gain-probe-awaiting-native-review",
            "plan": ref(plan_path),
            "fit": result,
            "CPU_global_fit_seconds": seconds,
            "all_corrected_values_finite": samples,
            "corrected_camera_RGB_range": [minimum, upper],
            "maximum_camera_RGB_change": maximum,
            "RMS_camera_RGB_change": math.sqrt(math.fsum(squared) / samples),
            "native_crops": crops,
            "CUDA_initialized": False,
            "new_model_forwards": 0,
            "new_corrected_full_frame_or_RGB16_export": False,
            "scope": plan["scope"],
        }
        (output / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        assert not torch.cuda.is_initialized()
        record(report["status"], result=ref(output / "report.json"))
    except BaseException as error:
        record("failed-global-input-gain-probe-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
