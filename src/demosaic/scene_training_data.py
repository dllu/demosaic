"""Replayable full-scene photo observations for matched scene-context training."""

import hashlib
import json
import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from .experiments.artifacts import reference
from .photo_epoch_order import PhotoEpochOrder, reader_policy
from .prediction_archive import fingerprint
from .scene_data import SceneObservation, observe_scene, sample_scene_recipe, scene_crop_boxes


def scene_seed(seed, index, purpose):
    data = f"{seed}:{index}:{purpose}".encode()
    return int.from_bytes(hashlib.sha256(data).digest()[:8], "little") % 2**62


@dataclass(frozen=True)
class SceneTrainingSample:
    observation: SceneObservation
    crops: dict
    metadata: dict


class ScenePhotoDataset:
    """Retain a complete binned source, then camera/noise once before cropping.

    Only global D4 augmentation is applied. Integer area reduction is explicit;
    there is no independent crop resize, optical PSF or projective transform.
    Each selected cache's actual bytes are checked once per dataset instance.
    """

    def __init__(
        self,
        manifest,
        *,
        seed,
        patch_size=256,
        crops_per_scene=4,
        reduction=1,
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
        observation = observe_scene(rgb.contiguous(), recipe)
        boxes = scene_crop_boxes(
            rgb.shape[-2:],
            patch_size=self.patch_size,
            count=self.crops_per_scene,
            seed=scene_seed(self.seed, index, "crops"),
        )
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
        return SceneTrainingSample(observation, crops, metadata)
