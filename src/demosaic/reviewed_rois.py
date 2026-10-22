"""Bind reviewed training-only photograph regions to their exact source data."""

import hashlib
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def validate_roi_fraction(value):
    if isinstance(value, bool):
        raise TypeError("Reviewed photographic ROI fraction must be a probability")
    value = float(value)
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Reviewed photographic ROI fraction must be finite and within [0,1]")
    return value


def require_resume_rois(previous, current):
    if previous.get("reviewed_roi_fraction", 0.0) != current.get("reviewed_roi_fraction", 0.0):
        raise ValueError("Resume reviewed photographic ROI fraction differs; initialize a new run")
    if previous.get("reviewed_roi_catalogue_sha256") != current.get(
        "reviewed_roi_catalogue_sha256"
    ):
        raise ValueError("Resume reviewed photographic ROI catalogue differs; initialize a new run")


@dataclass(frozen=True)
class ReviewedPhotoROI:
    record: dict
    xywh: tuple[int, int, int, int]


class ReviewedPhotoROIs:
    def __init__(self, catalogue, manifest, rows, *, required_size, expected_sha256=None):
        self.path = Path(catalogue)
        self.payload = self.path.read_bytes()
        self.sha256 = hashlib.sha256(self.payload).hexdigest()
        if expected_sha256 is not None and self.sha256 != expected_sha256:
            raise ValueError("Reviewed ROI catalogue changed after its training snapshot")
        data = json.loads(self.payload)
        manifest = Path(manifest)
        reference = data["source_manifest"]
        if (
            Path(reference["path"]).resolve() != manifest.resolve()
            or reference["sha256"] != hashlib.sha256(manifest.read_bytes()).hexdigest()
        ):
            raise ValueError("Reviewed ROI source manifest differs")
        if (
            data["source_split"] != "train"
            or data["source_bin_factor"] != 4
            or data["final_area_reduction"] != 2
            or data["effective_bin_factor"] != 8
            or data["target_native_shape"] != [256, 256, 3]
        ):
            raise ValueError("Reviewed ROI catalogue must describe native8 training targets")
        by_id = {row["id"]: row for row in rows}
        if len(by_id) != len(rows):
            raise ValueError("Reviewed ROI training source identities are ambiguous")
        self.regions, seen = [], set()
        for example in data["examples"]:
            identity, source = example["id"], example["source"]
            if (
                identity in seen
                or identity not in by_id
                or source != by_id[identity]
                or source["split"] != "train"
                or source.get("bin_factor") != 4
                or source.get("dtype") != "uint16"
                or source.get("color_space") != "linear-sRGB"
            ):
                raise ValueError("Reviewed ROI must identify one exact active training source")
            seen.add(identity)
            box = example["ROI_in_bin4_xywh"]
            if len(box) != 4 or any(type(v) is not int for v in box):
                raise ValueError("Reviewed ROI coordinates must be integers")
            x, y, width, height = box
            if x < 0 or y < 0 or x % 2 or y % 2 or width != 512 or height != 512:
                raise ValueError("Reviewed ROI requires an aligned512x512 bin4 context")
            if required_size > min(width, height):
                raise ValueError(
                    "Reviewed ROI is smaller than the required native training context"
                )
            cache = manifest.parent / source["cache"]
            with cache.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != source["cache_sha256"]:
                raise ValueError("Reviewed ROI source cache hash changed")
            array = np.load(cache, mmap_mode="r", allow_pickle=False)
            if (
                array.dtype != np.uint16
                or array.ndim != 3
                or array.shape[-1] != 3
                or list(array.shape) != source["shape"]
                or x + width > array.shape[1]
                or y + height > array.shape[0]
            ):
                raise ValueError("Reviewed ROI cache shape/dtype or bounds differ")
            crop = array[y : y + height, x : x + width].copy()
            if hashlib.sha256(crop.tobytes()).hexdigest() != example["actual_bin4_crop_sha256"]:
                raise ValueError("Reviewed ROI pixel hash changed")
            target = crop.astype(np.float32).reshape(256, 2, 256, 2, 3).mean((1, 3)) / 65535
            if (
                hashlib.sha256(target.tobytes()).hexdigest()
                != example["native8_target_float32_sha256"]
            ):
                raise ValueError("Reviewed ROI native8 target hash changed")
            self.regions.append(ReviewedPhotoROI(by_id[identity], tuple(box)))
        if not self.regions:
            raise ValueError("Reviewed ROI catalogue has no training regions")

    def choose(self, seed, index, fraction):
        """Use an independent stream so untouched samples keep every legacy draw."""
        value = hashlib.sha256(f"reviewed-photo-roi-v1:{seed}:{index}".encode()).digest()
        rng = random.Random(int.from_bytes(value[:8], "little"))
        if rng.random() >= fraction:
            return None
        return self.regions[rng.randrange(len(self.regions))]
