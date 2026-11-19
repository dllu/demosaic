"""Replayable full-scene photo observations for matched scene-context training."""

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from .data import validate_probability
from .experiments.artifacts import reference
from .photo_epoch_order import PhotoEpochOrder, reader_policy
from .prediction_archive import fingerprint
from .scene_data import SceneObservation, observe_scene, sample_scene_recipe, scene_crop_boxes


def scene_seed(seed, index, purpose):
    data = f"{seed}:{index}:{purpose}".encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "little") % 2**62


def _attenuate_local_contrast(rgb, box, scale, *, flat_core=False):
    """Reduce texture inside one crop with a smooth taper into the original scene."""
    x, y, width, height = box
    crop = rgb[:, y : y + height, x : x + width]
    center = crop[:, height // 2, width // 2, None, None]
    size = min(width, height)
    radius, taper = size * (72 / 256), size * (20 / 256)

    def axis(count):
        distance = (torch.arange(count, dtype=rgb.dtype, device=rgb.device) - (count - 1) / 2).abs()
        u = ((radius - distance) / taper).clamp(0, 1)
        return u.square() * (3 - 2 * u)

    support = axis(height)[:, None] * axis(width)[None, :]
    if flat_core:
        level = crop[:, height // 4 : height - height // 4, width // 4 : width - width // 4]
        level = level.mean(dim=(-2, -1), keepdim=True)
        changed = torch.where(support == 1, level, torch.lerp(crop, level, support))
    else:
        centered = crop - center
        low = F.avg_pool2d(
            centered[None], kernel_size=9, stride=1, padding=4, count_include_pad=False
        )[0]
        changed = crop + (1 - scale) * support * (low - centered)
    scene = rgb.clone()
    scene[:, y : y + height, x : x + width] = torch.where(support > 0, changed, crop)
    return scene


@dataclass(frozen=True)
class SceneTrainingSample:
    observation: SceneObservation
    crops: dict
    metadata: dict


class ScenePhotoDataset:
    """Retain a complete binned source, then camera/noise once before cropping.

    Integer area reduction and global D4 precede optional local contrast
    attenuation or flattening in one crop. Each selected cache's bytes are checked once
    per dataset instance.
    """

    def __init__(
        self,
        manifest,
        *,
        seed,
        patch_size=256,
        crops_per_scene=4,
        reduction=1,
        local_contrast_fraction=0.0,
        local_flat_core_fraction=0.0,
        photo_epoch_order=None,
        photo_epoch_order_sha256=None,
    ):
        self.manifest = Path(manifest)
        self.rows = [
            json.loads(line) for line in self.manifest.read_text().splitlines() if line.strip()
        ]
        if (
            not self.rows
            or type(reduction) is not int
            or reduction not in (1, 2)
            or type(patch_size) is not int
            or patch_size < 16
            or patch_size % 8
            or type(crops_per_scene) is not int
            or crops_per_scene < 1
            or len({r["id"] for r in self.rows}) != len(self.rows)
        ):
            raise ValueError(
                "Require unique declared scenes, integer reduction and native crop geometry"
            )
        for row in self.rows:
            if (
                row["bin_factor"] != 4
                or row["color_space"] != "linear-sRGB"
                or row["dtype"] != "uint16"
                or len(row["cache_sha256"]) != 64
                or min(row["shape"][:2]) // reduction < patch_size
            ):
                raise ValueError(
                    "Require fitting linear uint16 bin4 cache fields with declared hashes"
                )
        self.seed, self.patch_size, self.crops_per_scene = seed, patch_size, crops_per_scene
        self.reduction = reduction
        self.local_contrast_fraction = validate_probability(
            local_contrast_fraction, "Scene local contrast fraction"
        )
        self.local_flat_core_fraction = validate_probability(
            local_flat_core_fraction, "Scene flat fraction within local contrast selection"
        )
        if self.local_flat_core_fraction and not self.local_contrast_fraction:
            raise ValueError("Scene flat cores require a positive local contrast fraction")
        self.checked_files = set()
        if photo_epoch_order is None and photo_epoch_order_sha256 is not None:
            raise ValueError("Photographic epoch order hash requires its header")
        self.photo_epoch_order = (
            None
            if photo_epoch_order is None
            else PhotoEpochOrder(
                photo_epoch_order,
                self.manifest,
                self.rows,
                reader_policy(seed, 0, 0, 0, None),
                expected_sha256=photo_epoch_order_sha256,
            )
        )

    def source_row(self, index):
        if self.photo_epoch_order is not None:
            return self.photo_epoch_order.ordinary(index)
        chooser = random.Random(scene_seed(self.seed, index, "source"))
        return self.rows[chooser.randrange(len(self.rows))]

    def __getitem__(self, index):
        row = self.source_row(index)
        path = (self.manifest.parent / row["cache"]).resolve()
        if path not in self.checked_files:
            if reference(path)["sha256"] != row["cache_sha256"]:
                raise ValueError("Complete-scene source cache hash changed")
            self.checked_files.add(path)
        array = np.load(path, mmap_mode="r", allow_pickle=False)
        if list(array.shape) != row["shape"] or array.dtype != np.uint16:
            raise ValueError("Complete-scene source header changed")
        rgb = (
            torch.from_numpy(np.array(array, dtype=np.float32, copy=True)).permute(2, 0, 1) / 65535
        )
        if self.reduction == 2:
            rgb = F.avg_pool2d(rgb, 2)
        rgb = rgb[:, : rgb.shape[1] // 2 * 2, : rgb.shape[2] // 2 * 2]
        augmentation = random.Random(scene_seed(self.seed, index, "D4"))
        rotation, mirror = augmentation.randrange(4), bool(augmentation.randrange(2))
        rgb = torch.rot90(rgb, rotation, (-2, -1))
        if mirror:
            rgb = rgb.flip(-1)
        recipe = sample_scene_recipe(scene_seed(self.seed, index, "camera-noise"))
        boxes = scene_crop_boxes(
            rgb.shape[-2:],
            patch_size=self.patch_size,
            count=self.crops_per_scene,
            seed=scene_seed(self.seed, index, "crops"),
        )
        local_contrast = None
        if self.local_contrast_fraction:
            contrast_rng = random.Random(scene_seed(self.seed, index, "local-contrast"))
            if contrast_rng.random() < self.local_contrast_fraction:
                box = contrast_rng.choice(boxes)
                scale = 2 ** contrast_rng.uniform(-3, -1)
                flat = bool(self.local_flat_core_fraction) and (
                    contrast_rng.random() < self.local_flat_core_fraction
                )
                rgb = _attenuate_local_contrast(rgb, box, scale, flat_core=flat)
                local_contrast = {"box_xywh": list(box), "scale": 0.0 if flat else scale}
                if flat:
                    local_contrast["exact_flat_core"] = True
        observation = observe_scene(rgb.contiguous(), recipe)
        crops = observation.crops(boxes)
        metadata = {
            "index": index,
            "source_id": row["id"],
            "cache": str(path),
            "cache_sha256": row["cache_sha256"],
            "cache_shape": list(array.shape),
            "reduction": self.reduction,
            "D4_quarter_turns": rotation,
            "mirror_x": mirror,
            "native_hw": list(rgb.shape[-2:]),
            "boxes_xywh": boxes,
            "recipe": recipe.__dict__,
            "scene_packed": fingerprint(observation.packed),
            "scene_variance": fingerprint(observation.variance),
            "crop_fingerprints": {k: fingerprint(v) for k, v in crops.items()},
            "scope": "One complete camera/noise observation; preview and native crops share actual RAW samples. Targets never enter scene encoding. Global D4 only; no independent crop resize/homography.",
        }
        if self.photo_epoch_order is not None:
            metadata["photo_epoch_order_sha256"] = self.photo_epoch_order.sha256
        if local_contrast is not None:
            metadata["local_contrast"] = local_contrast
            metadata["scope"] = (
                "One complete camera/noise observation with localized flat core "
                "before Bayer sampling. Preview and crops share observed RAW."
                if local_contrast.get("exact_flat_core")
                else "One complete camera/noise observation with localized contrast attenuation "
                "before Bayer sampling. Preview and crops share observed RAW."
            )
        return SceneTrainingSample(observation, crops, metadata)
