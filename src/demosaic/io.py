"""Read RAWs without modifying originals; write explicitly tagged 16-bit TIFFs."""

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import tifffile

from .safety import writable_path


@dataclass
class RawMetadata:
    source: str
    camera: str
    pattern: str
    black_levels: list[float]
    white_levels: list[float]
    white_balance: list[float]
    camera_to_srgb: list[list[float]]
    flip: int
    iso: float | None = None


def camera_matrix(cam_xyz):
    """Match LibRaw cam_xyz_coeff: normalized sRGB->camera, then inverse.

    Despite rawpy's ambiguous property name, LibRaw's cam_xyz is not a
    camera->XYZ matrix to transpose directly. See src/utils/utils_dcraw.cpp.
    """
    srgb_to_xyz = np.array(
        [
            [0.412453, 0.357580, 0.180423],
            [0.212671, 0.715160, 0.072169],
            [0.019334, 0.119193, 0.950227],
        ]
    )
    srgb_to_camera = np.asarray(cam_xyz, dtype=np.float64)[:3] @ srgb_to_xyz
    white = srgb_to_camera.sum(axis=1)
    if np.any(white <= 1e-8) or not np.isfinite(srgb_to_camera).all():
        raise ValueError("RAW has no usable XYZ-to-camera color matrix")
    return np.linalg.inv(srgb_to_camera / white[:, None])


def exif_identity(path):
    """Optional read-only identity extraction; no EXIF writes or sidecars."""
    if not shutil.which("exiftool"):
        return {}
    result = subprocess.run(
        ["exiftool", "-j", "-Model", "-ISO", str(path)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    return json.loads(result.stdout)[0]


def read_raw(path):
    import rawpy

    path = Path(path).resolve()
    with rawpy.imread(str(path)) as raw:
        if raw.raw_pattern is None or raw.raw_pattern.shape != (2, 2):
            raise ValueError("Only ordinary 2×2 Bayer RAWs are currently supported")
        ids = np.array(
            [
                raw.raw_color(raw.sizes.top_margin + y, raw.sizes.left_margin + x)
                for y in range(2)
                for x in range(2)
            ]
        )
        description = raw.color_desc.decode("ascii")
        pattern = "".join(description[int(i)] for i in ids)
        from .cfa import color_indices

        color_indices(pattern)  # Reject RGBE, monochrome or other non-Bayer data.
        black = np.asarray(raw.black_level_per_channel, dtype=np.float32)[ids]
        channel_white = raw.camera_white_level_per_channel
        whites = np.asarray(channel_white or [raw.white_level] * 4, dtype=np.float32)[ids]
        whites = np.where(whites > black, whites, raw.white_level)
        if np.any(whites <= black):
            raise ValueError("Invalid RAW black/white levels")
        image = raw.raw_image_visible.astype(np.float32)
        for i in range(4):
            image[i // 2 :: 2, i % 2 :: 2] -= black[i]
            image[i // 2 :: 2, i % 2 :: 2] /= whites[i] - black[i]
        # Retain black-subtracted negative read noise until the model sees it.
        gains = np.asarray(raw.camera_whitebalance[:3], dtype=np.float64)
        if not np.all(np.isfinite(gains)) or np.any(gains <= 0):
            gains = np.asarray(raw.daylight_whitebalance[:3], dtype=np.float64)
        gains /= gains[1]
        matrix = camera_matrix(raw.rgb_xyz_matrix)
        identity = exif_identity(path)
        meta = RawMetadata(
            str(path),
            identity.get("Model", "Unknown"),
            pattern,
            black.tolist(),
            whites.tolist(),
            gains.tolist(),
            matrix.tolist(),
            int(raw.sizes.flip),
            identity.get("ISO"),
        )
    return image, meta


def orient(array, flip):
    if flip == 3:
        return np.rot90(array, 2)
    if flip == 5:
        return np.rot90(array, 1)
    if flip == 6:
        return np.rot90(array, 3)
    return array


def write_rgb16(path, rgb, *, metadata=None, color_space="linear-camera-RGB", flip=0):
    """Round once to unsigned 16-bit, tag transfer/color space, no 8-bit stage."""
    path = writable_path(path)
    if not np.isfinite(rgb).all() or rgb.ndim != 3 or rgb.shape[-1] != 3:
        raise ValueError("Expected finite H×W×3 RGB")
    path.parent.mkdir(parents=True, exist_ok=True)
    array = orient(np.rint(np.clip(rgb, 0, 1) * 65535).astype(np.uint16), flip)
    description = {
        "color_space": color_space,
        "bits_per_sample": 16,
        "metadata": asdict(metadata) if isinstance(metadata, RawMetadata) else metadata,
    }
    tags = []
    if color_space == "sRGB":
        from PIL import ImageCms

        profile = ImageCms.ImageCmsProfile(ImageCms.createProfile("sRGB")).tobytes()
        tags.append((34675, "B", len(profile), profile, False))
    temporary = path.with_suffix(path.suffix + ".tmp")
    tifffile.imwrite(
        temporary,
        array,
        photometric="rgb",
        metadata=None,
        description=json.dumps(description),
        extratags=tags,
    )
    temporary.replace(path)
