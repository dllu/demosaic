"""Verify every declared endpoint's complete GFX RGB16 exports and native samples."""

from pathlib import Path

import numpy as np
import tifffile
from audit_quality_archive import binding, write
from compare_quality_archives import read_bound


def verify_exports(stage_binding, checkpoints, destination):
    stage = read_bound(stage_binding)
    summary = read_bound(stage["report"])
    count = len(checkpoints)
    expected_sha = {item["sha256"] for item in checkpoints.values()}
    if not count or len(expected_sha) != count:
        raise ValueError("Declare distinct nonempty endpoint checkpoints")
    if len(summary["models"]) != count or len(summary["full_frames"]) != count:
        raise ValueError("Full-frame model coverage differs from declared checkpoints")
    if {item["sha256"] for item in summary["models"]} != expected_sha:
        raise ValueError("Full-frame checkpoint identities differ")
    checked, outputs = 0, []
    for model, frame in zip(summary["models"], summary["full_frames"], strict=True):
        if model["label"] != frame["model_label"]:
            raise ValueError("Full-frame labels differ")
        files, linear = [], None
        if len(frame["files"]) != 2:
            raise ValueError("Require both linear and sRGB exports per endpoint")
        roles = []
        for item in frame["files"]:
            path = Path(stage["report"]["path"]).parent / item["path"]
            bound = binding(path)
            if bound["sha256"] != item["sha256"] or path.stat().st_size != item["bytes"]:
                raise ValueError("Changed RGB16 export")
            pixels = tifffile.memmap(path, mode="r")
            if pixels.shape != (8746, 11662, 3) or pixels.dtype != np.uint16:
                raise ValueError("Require complete GFX RGB16 pixels")
            if pixels.shape[0] * pixels.shape[1] / 1e6 != frame["timing"]["megapixels"]:
                raise ValueError("Export dimensions differ from the recorded frame")
            files.append({"file": bound, "shape": list(pixels.shape), "dtype": str(pixels.dtype)})
            if item["path"].endswith("-linear16.tiff"):
                roles.append("linear")
                linear = pixels
            elif item["path"].endswith("-srgb16.tiff"):
                roles.append("srgb")
            else:
                raise ValueError("Unrecognized RGB16 export role")
        if sorted(roles) != ["linear", "srgb"]:
            raise ValueError("Require one linear and one sRGB export")
        regions = [
            row
            for row in stage["full_native_floats"]
            if row["checkpoint"]["sha256"] == model["sha256"]
        ]
        if len(regions) != 6 or len({row["region"]["name"] for row in regions}) != 6:
            raise ValueError("Require six distinct native regions per endpoint")
        for row in regions:
            if binding(row["array"]["path"]) != row["array"]:
                raise ValueError("Changed native float array")
            native = np.load(row["array"]["path"], allow_pickle=False)
            if (
                native.shape != (1, 3, 160, 160)
                or native.dtype != np.float32
                or not np.isfinite(native).all()
            ):
                raise ValueError("Require finite native160 FP32 camera RGB")
            expected = np.rint(np.clip(native[0].transpose(1, 2, 0), 0, 1) * 65535).astype(
                np.uint16
            )
            x, y = row["region"]["noisy_xy"]
            actual = linear[y : y + 160, x : x + 160]
            if not np.array_equal(actual, expected):
                raise ValueError(
                    f"Linear RGB16 quantization differs: {model['label']} / {row['region']['name']}"
                )
            checked += actual.size
        outputs.append(
            {
                "checkpoint_sha256": model["sha256"],
                "files": files,
                "native_regions": [row["region"] for row in regions],
                "timing": frame["timing"],
            }
        )
    if checked != 460800 * count:
        raise ValueError("Native export verification coverage differs")
    write(
        destination,
        {
            "stage": stage_binding,
            "models": outputs,
            "RGB16_values_checked_against_retained_FP32": checked,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "scope": "Both full-frame TIFF hashes/types/shapes and exact linear-camera FP32 clip/round quantization at six native ROIs per declared endpoint. sRGB native quantization is not independently recomputed. Timings are observations, not a controlled speed comparison.",
        },
    )
    return binding(destination)
