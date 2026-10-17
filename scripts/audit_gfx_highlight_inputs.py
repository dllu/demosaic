"""Check supplementary native GFX inputs against the cached RAW pair and PNGs."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from prepare_gfx_highlight_inputs import read, sha

from demosaic.io import read_raw
from demosaic.realdata import read_reference
from demosaic.safety import writable_path


def display64(rgb, wb, matrix, exposure):
    """Independent float64 NumPy camera transform and sRGB transfer."""
    linear = np.einsum(
        "bij,bjhw->bihw",
        matrix.astype(np.float64),
        rgb.astype(np.float64) * exposure * wb.astype(np.float64)[..., None, None],
    )
    bounded = np.clip(linear, 0, 1)
    encoded = np.where(
        bounded <= 0.0031308,
        12.92 * bounded,
        1.055 * np.maximum(bounded, 0) ** (1 / 2.4) - 0.055,
    )
    return np.rint(np.clip(encoded[0].transpose(1, 2, 0), 0, 1) * 255).astype(np.uint8)


def main(inputs, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan = read(inputs)
    assert (
        plan["status"]
        == "prepared-input-only-GFX-highlight-regions-awaiting-independent-and-native-review"
    )
    assert len(plan["cases"]) == 2 and plan["display_exposure"] == 4
    assert sha(plan["selection"]) == plan["selection_sha256"]
    assert sha(plan["parent_selection"]) == plan["parent_selection_sha256"]
    assert sha(plan["conditioning_report"]) == plan["conditioning_report_sha256"]
    old = read(plan["conditioning_report"])
    assert plan["conditioning"] == old["conditioning"]
    assert plan["reference_calibration"] == old["reference_calibration"]
    for path, digest in plan["source_files"].items():
        assert sha(path) == digest
    sources = {record["role"]: record for record in plan["sources"]}
    cache = Path.cwd() / ".cache/gfx-qualitative-20231231"
    for record in sources.values():
        assert Path(record["path"]).parent == cache
        assert sha(record["path"]) == record["sha256"]
    raw, _ = read_raw(sources["noisy"]["path"])
    _, reference, _, _ = read_reference(sources["reference"]["path"])
    checks = []
    for case in plan["cases"]:
        assert sha(case["arrays"]) == case["sha256"]
        with np.load(case["arrays"], allow_pickle=False) as loaded:
            arrays = {key: loaded[key].copy() for key in loaded.files}
        shapes = {
            "packed": [1, 4, 256, 256],
            "variance": [1, 4, 256, 256],
            "colors": [1, 4],
            "wb": [1, 3],
            "matrix": [1, 3, 3],
            "noisy_rgb": [1, 3, 512, 512],
            "reference_rgb": [1, 3, 160, 160],
        }
        assert arrays.keys() == shapes.keys()
        for key, shape in shapes.items():
            assert list(arrays[key].shape) == shape and np.isfinite(arrays[key]).all()
            assert arrays[key].dtype == (np.int64 if key == "colors" else np.float32)
        assert arrays["colors"].tolist() == [[0, 1, 1, 2]]
        x, y, w, h = case["context_xywh"]
        assert w == h == 512 and x % 2 == y % 2 == 0
        patch = raw[y : y + h, x : x + w]
        expected = np.stack(
            [patch[0::2, 0::2], patch[0::2, 1::2], patch[1::2, 0::2], patch[1::2, 1::2]]
        )[None]
        assert np.array_equal(expected, arrays["packed"])
        condition = plan["conditioning"]
        assert np.array_equal(
            np.maximum(expected, 0) * condition["shot"] + condition["read"], arrays["variance"]
        )
        region = case["region"]
        rx, ry = region["reference_xy"]
        ref = reference[ry : ry + 160, rx : rx + 160].transpose(2, 0, 1)[None]
        assert np.array_equal(ref, arrays["reference_rgb"])
        nx, ny = region["noisy_xy"]
        roi = case["ROI_xywh"]
        assert roi == [nx - x, ny - y, 160, 160]
        assert abs(rx - nx) < 8 and abs(ry - ny) < 8
        assert len(case["previews"]) == 2
        pixel_checks = []
        for record in case["previews"]:
            assert sha(record["path"]) == record["sha256"]
            observed = np.array(Image.open(record["path"]).convert("RGB"))
            if record["role"] == "noisy-Malvar":
                px, py, pw, ph = roi
                rgb = arrays["noisy_rgb"][..., py : py + ph, px : px + pw]
            else:
                assert record["role"] == "independent-ISO100-AHD-reference-not-GT"
                rgb = arrays["reference_rgb"]
            rendered = display64(rgb, arrays["wb"], arrays["matrix"], plan["display_exposure"])
            assert observed.shape == rendered.shape == (160, 160, 3)
            difference = np.abs(observed.astype(np.int16) - rendered.astype(np.int16))
            # Predeclared preview bound for independent64 vs producer32 rounding.
            # Float arrays/source samples remain exact, with no metric tolerance.
            assert difference.max() <= 1
            pixel_checks.append(
                {
                    "role": record["role"],
                    "channel_values": int(difference.size),
                    "changed_values": int(np.count_nonzero(difference)),
                    "maximum8bit_difference": int(difference.max()),
                }
            )
        px, py, pw, ph = roi
        values = arrays["packed"][..., py // 2 : (py + ph) // 2, px // 2 : (px + pw) // 2]
        checks.append(
            {
                "region": region,
                "raw_packing_bitwise_source": True,
                "variance_exact": True,
                "reference_crop_bitwise_fresh_AHD_decode": True,
                "RAW_samples": int(values.size),
                "RAW_samples_at_or_above_0_999": int(np.count_nonzero(values >= 0.999)),
                "RAW_minimum": float(values.min()),
                "RAW_maximum": float(values.max()),
                "preview_checks": pixel_checks,
            }
        )
    result = {
        "status": "completed-independent-GFX-highlight-input-and-native-preview-audit",
        "inputs": str(inputs),
        "inputs_sha256": sha(inputs),
        "cases": checks,
        "CUDA_initialized": False,
        "driver_sha256": sha(__file__),
        "scope": "Input/reference source and native display integrity only. Two extra evaluation-only GFX regions; independent AHD ISO100 reference is not GT. No learned model, reference score, training or performance claim. Actual native selection review is separate.",
    }
    output = writable_path(output)
    assert not output.exists()
    output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output.parent / "source" / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({"audit": str(output), "regions": len(checks)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
