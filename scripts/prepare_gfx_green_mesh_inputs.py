"""Freeze the held-out DSCF3842/3835 mesh case from cached RAWs and camera JPEGs."""

import argparse
import hashlib
import io
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import psutil
import torch
from PIL import Image, ImageCms, ImageOps
from prepare_gfx_highlight_inputs import integer_offset

from demosaic.cfa import color_indices, malvar, pack
from demosaic.color import render
from demosaic.io import read_raw
from demosaic.realdata import read_reference
from demosaic.safety import writable_path


def binding(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def camera_jpeg(path):
    Image.MAX_IMAGE_PIXELS = 120_000_000
    with Image.open(path) as image:
        image = ImageOps.exif_transpose(image)
        profile = image.info.get("icc_profile")
        image = image.convert("RGB")
        if profile:
            image = ImageCms.profileToProfile(
                image,
                ImageCms.ImageCmsProfile(io.BytesIO(profile)),
                ImageCms.createProfile("sRGB"),
                outputMode="RGB",
            )
        return image.copy()


def green(values, wb, matrix):
    return render(values, wb, matrix)[0, 1].numpy()


def jpeg_offset(anchor, image, x, y):
    """Coarse area8 NCC only selects coordinates; native pixels are never warped."""
    size, radius, factor = anchor.shape[0], 128, 8
    window = np.asarray(image.crop((x - radius, y - radius, x + size + radius, y + size + radius)))
    full = window[:, :, 1].astype(np.float32) / 255
    coarse_a = anchor.reshape(size // factor, factor, size // factor, factor).mean((1, 3))
    side = (size + 2 * radius) // factor
    coarse_b = full.reshape(side, factor, side, factor).mean((1, 3))
    cx, cy, coarse_score = integer_offset(
        coarse_a, coarse_b, radius // factor, radius // factor, radius=radius // factor
    )
    fx, fy, score = integer_offset(
        anchor, full, radius + cx * factor, radius + cy * factor, radius=16
    )
    return cx * factor + fx, cy * factor + fy, score, coarse_score


@torch.inference_mode()
def main(selection, output, decoded=None):
    assert not torch.cuda.is_initialized()
    assert psutil.virtual_memory().available > 40 * 2**30
    torch.set_num_threads(2)
    selection = Path(selection).resolve()
    plan = json.loads(selection.read_text())
    paths = {}
    for role, item in plan["sources"].items():
        path = Path(item["path"]).resolve()
        assert path.is_relative_to(Path.cwd() / ".cache")
        assert binding(path)["sha256"] == item["sha256"]
        paths[role] = path
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    save(
        output / "execution-plan-v1.json",
        {
            "selection": binding(selection),
            "driver": binding(__file__),
            "registration_helper": binding(
                Path(__file__).with_name("prepare_gfx_highlight_inputs.py")
            ),
            "sources": {k: binding(v) for k, v in paths.items()},
            "new_neural_forwards": 0,
            "scope": "New held-out green-mesh inputs only; no training/model/noise generation or full-frame model restoration.",
        },
    )
    x, y, size, height = plan["raw_context_xywh"]
    assert x % 2 == y % 2 == 0 and size == height == 768
    if decoded:
        from demosaic.io import RawMetadata

        previous = json.loads(Path(decoded).read_text())
        assert previous["source_bindings"] == {k: binding(v) for k, v in paths.items()}
        assert previous["context_xywh"] == plan["raw_context_xywh"]
        assert binding(previous["arrays"]["path"]) == previous["arrays"]
        with np.load(previous["arrays"]["path"], allow_pickle=False) as stored:
            raw_context = stored["raw_context"].copy()
            reference = stored["reference_window"].copy()
        metadata = RawMetadata(**previous["metadata"])
        ref_metadata = RawMetadata(**previous["reference_metadata"])
        calibration = previous["reference_calibration"]
        decoder_opens = 0
    else:
        raw, metadata = read_raw(paths["noisy"])
        ref_raw, reference, ref_metadata, calibration = read_reference(paths["reference"])
        assert raw.shape == ref_raw.shape == (8746, 11662)
        raw_context = raw[y : y + size, x : x + size].copy()
        reference = reference[y - 128 : y + size + 128, x - 128 : x + size + 128].copy()
        del raw, ref_raw
        decoder_opens = 3
    assert metadata.iso == 6400 and ref_metadata.iso == 100
    assert metadata.pattern == ref_metadata.pattern == "RGGB"
    decoded_path = output / "decoded-contexts-v1.npz"
    np.savez(decoded_path, raw_context=raw_context, reference_window=reference)
    save(
        output / "decoded-contexts-v1.json",
        {
            "arrays": binding(decoded_path),
            "metadata": asdict(metadata),
            "reference_metadata": asdict(ref_metadata),
            "reference_calibration": calibration,
            "source_bindings": {k: binding(v) for k, v in paths.items()},
            "context_xywh": plan["raw_context_xywh"],
            "RAW_decoder_opens": decoder_opens,
        },
    )
    packed = pack(torch.from_numpy(raw_context)[None, None])
    wb = torch.tensor(metadata.white_balance)[None]
    matrix = torch.tensor(metadata.camera_to_srgb)[None]
    colors = color_indices(metadata.pattern)[None]
    noisy = malvar(packed, colors, wb)
    # Match the two independent captures using input/reference only.
    dx, dy, score = integer_offset(noisy[0, 1].numpy(), reference[:, :, 1], 128, 128, radius=16)
    reference_context = reference[128 + dy : 128 + dy + size, 128 + dx : 128 + dx + size].copy()
    del reference
    reference_tensor = torch.from_numpy(reference_context).permute(2, 0, 1)[None]
    registrations = {"reference_RAW_minus_noisy_RAW_xy": [dx, dy], "reference_RAW_green_NCC": score}
    images = {}
    offsets = {}
    for role, rgb in [("noisy_camera_jpeg", noisy), ("reference_camera_jpeg", reference_tensor)]:
        im = camera_jpeg(paths[role])
        # The expected central crop is14x10 pixels smaller than visible RAW.
        bx, by = x - (11662 - im.width) // 2, y - (8746 - im.height) // 2
        anchor = green(rgb, wb, matrix)
        ox, oy, corr, coarse_corr = jpeg_offset(anchor, im, bx, by)
        offsets[role] = [bx + ox - x, by + oy - y]
        images[role] = im
        registrations[role] = {
            "JPEG_context_minus_noisy_context_xy": offsets[role],
            "JPEG_context_origin_xy": [bx + ox, by + oy],
            "green_NCC": corr,
            "coarse_area8_green_NCC": coarse_corr,
            "raw_anchor_xy": [
                x + (dx if role.startswith("reference") else 0),
                y + (dy if role.startswith("reference") else 0),
            ],
            "note": "Integer coordinates only. Residual lens/camera-pipeline geometry and radiometry differences remain.",
        }
    # reference_tensor is at [x+dx,y+dy], but its JPEG search above starts at x,y;
    # its returned offset already maps that specific reference context to JPEG.
    arrays = output / "inputs-v1.npz"
    condition = plan["conditioning"]
    variance = packed.clamp_min(0) * condition["shot"] + condition["read"]
    np.savez(
        arrays,
        packed=packed.numpy(),
        variance=variance.numpy(),
        colors=colors.numpy(),
        wb=wb.numpy(),
        matrix=matrix.numpy(),
        noisy_rgb=noisy.numpy(),
        reference_rgb=reference_tensor.numpy(),
        raw_context=raw_context,
    )
    records = []
    for region in plan["regions"]:
        jx, jy = region["noisy_camera_jpeg_xy"]
        edge = region["size"]
        nx, ny = jx - offsets["noisy_camera_jpeg"][0], jy - offsets["noisy_camera_jpeg"][1]
        roi = [nx - x, ny - y, edge, edge]
        assert min(roi[:2]) >= 64 and roi[0] + edge <= size - 64 and roi[1] + edge <= size - 64
        rx, ry = nx + dx, ny + dy
        # reference JPEG offset above is relative to context origin x,y,
        # so apply it to the within-context region, without adding dx/dy twice.
        rjx, rjy = (
            nx + offsets["reference_camera_jpeg"][0],
            ny + offsets["reference_camera_jpeg"][1],
        )
        previews = {}
        for role, cx, cy in [("noisy_camera_jpeg", jx, jy), ("reference_camera_jpeg", rjx, rjy)]:
            pixels = np.asarray(images[role].crop((cx, cy, cx + edge, cy + edge))).copy()
            file = output / (region["name"] + "-" + role + "-native.npy")
            np.save(file, pixels, allow_pickle=False)
            previews[role] = {
                "pixels": binding(file),
                "xywh": [cx, cy, edge, edge],
                "scope": "Native camera-rendered sRGB8 pixels; no resizing/warping.",
            }
        records.append(
            {
                "name": region["name"],
                "ROI_xywh": roi,
                "noisy_raw_xywh": [nx, ny, edge, edge],
                "reference_raw_xywh": [rx, ry, edge, edge],
                "camera_JPEGs": previews,
            }
        )
    derived = {
        **plan,
        "regions": records,
        "registrations": registrations,
        "raw_metadata": asdict(metadata),
        "reference_metadata": asdict(ref_metadata),
        "reference_AHD_calibration": calibration,
    }
    save(output / "selection-derived-v1.json", derived)
    result = {
        "status": "prepared-new-DSCF3842-3835-green-mesh-inputs-no-model-work",
        "selection": binding(selection),
        "derived_selection": binding(output / "selection-derived-v1.json"),
        "input_arrays": binding(arrays),
        "context_shape": [1, 3, size, size],
        "conditioning": condition,
        "display_exposure": plan["display_exposure"],
        "cases": records,
        "registrations": registrations,
        "source_bindings": {k: binding(v) for k, v in paths.items()},
        "new_neural_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decoder_opens": decoder_opens,
        "optimizer_updates": 0,
        "CUDA_initialized": False,
        "scope": "New768 context and two native160 ROIs fixed from source/camera JPEGs only. ISO100 AHD and cameraJPEGs are qualitative comparators, not GT. Same noisy WB/matrix used for raw-method displays. Standing3879/3880 and all training unchanged.",
    }
    save(output / "result-v1.json", result)
    print(json.dumps({"status": result["status"], "registrations": registrations}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--decoded",
        type=Path,
        help="Reuse a preserved decoded-contexts JSON after an alignment-only failure",
    )
    args = parser.parse_args()
    main(args.selection, args.output, args.decoded)
