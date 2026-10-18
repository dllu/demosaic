"""Measured-CFA supervision from a separate, verified real RAW training split."""

import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import Dataset

from .cfa import color_indices, mosaic, pack
from .color import render
from .losses import image_log_mse, multiscale_sensor_loss, validate_reconstruction_objective
from .noise import variance_map
from .paired import TRAINING_SCENES
from .paired_admission import approved_extension_cases, case_key


def paired_step(step, seed, fraction):
    # Independent of worker scheduling, global RNG and the number of prior draws.
    return random.Random(f"paired:{seed}:{step}").random() < fraction


def transform(value, turns, flip):
    value = torch.rot90(value, turns, (-2, -1))
    return value.flip(-1) if flip else value


class PairedDataset(Dataset):
    def __init__(self, manifest, *, patch_size=256, seed=42):
        self.path = Path(manifest)
        self.payload = self.path.read_bytes()
        self.sha256 = hashlib.sha256(self.payload).hexdigest()
        data = json.loads(self.payload)
        if data["split"] != "train":
            raise ValueError("Paired training requires an explicitly separate train manifest")
        if patch_size < 32 or patch_size % 16:
            raise ValueError("Paired patch size must be >=32 and divisible by 16")
        approved = approved_extension_cases(data)
        seen_extensions = set()
        self.size, self.seed, self.scenes = patch_size, seed, {}
        for case in data["cases"]:
            key = case_key(case)
            reviewed = approved.get(key)
            valid_source = (
                case["scene"] in TRAINING_SCENES and case.get("paired_source_family") is None
            ) or case == reviewed
            if not valid_source or case.get("unknown_sensor"):
                raise ValueError("Paired training manifest contains a protected/unknown scene")
            if reviewed is not None:
                if key in seen_extensions:
                    raise ValueError("Repeated reviewed paired case")
                seen_extensions.add(key)
            if not case["crops"]:
                continue
            for crop in case["crops"]:
                path = self.path.parent / crop["path"]
                with path.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                if digest != crop["sha256"]:
                    raise ValueError(f"Paired training crop checksum mismatch: {path}")
            group = (
                reviewed.get("scene_group", case["scene"])
                if reviewed is not None
                else case["scene"]
            )
            self.scenes.setdefault(group, []).append(case)
        if seen_extensions != set(approved):
            raise ValueError("Paired training manifest omits reviewed extension cases")
        self.names = sorted(self.scenes)
        if not self.names:
            raise ValueError("Paired training has no usable scenes")

    def __len__(self):
        return len(self.names)

    def __getitem__(self, index):
        rng = random.Random(self.seed + index)
        scene = self.names[rng.randrange(len(self.names))]
        case = rng.choice(self.scenes[scene])
        crop = rng.choice(case["crops"])
        with np.load(self.path.parent / crop["path"], allow_pickle=False) as arrays:
            raw = arrays["raw"]
            h, w = raw.shape
            if min(h, w) < self.size:
                raise ValueError("Prepared paired crop is smaller than the training patch")
            mask = arrays["sensor_mask"].astype(bool)
            # Reference-defined invalid regions may be skipped during training.
            positions = [
                (
                    rng.randrange((h - self.size) // 2 + 1) * 2,
                    rng.randrange((w - self.size) // 2 + 1) * 2,
                )
                for _ in range(8)
            ] + [(y, x) for y in (0, h - self.size) for x in (0, w - self.size)]
            usable = [
                (y, x)
                for y, x in positions
                if mask[:, y : y + self.size, x : x + self.size].sum() >= self.size**2 / 4
            ]
            if not usable:
                raise ValueError("Prepared crop has insufficient valid paired training samples")
            y, x = usable[0]
            region = (..., slice(y, y + self.size), slice(x, x + self.size))
            values = {
                "raw": torch.from_numpy(raw[region].copy()),
                "target": torch.from_numpy(arrays["reference_rgb"][region].copy()),
                "sensor_reference": torch.from_numpy(arrays["sensor_reference"][region].copy()),
                "sensor_mask": torch.from_numpy(mask[region].copy()),
            }
        turns, flip = rng.randrange(4), rng.random() < 0.5
        values = {k: transform(v, turns, flip).contiguous() for k, v in values.items()}
        meta = case["metadata"]
        colors = transform(color_indices(meta["pattern"]).reshape(2, 2), turns, flip).flatten()
        packed = pack(values.pop("raw")[None, None])[0]
        shot = torch.tensor(case["conditioning"]["shot"]).reshape(1, 1, 1)
        read = torch.tensor(case["conditioning"]["read"]).reshape(1, 1, 1)
        return {
            **values,
            "packed": packed,
            "variance": variance_map(packed, shot, read),
            "colors": colors,
            "wb": torch.tensor(meta["white_balance"], dtype=torch.float32),
            "matrix": torch.tensor(meta["camera_to_srgb"], dtype=torch.float32),
            "shot": shot,
            "read": read,
        }


def masked_charbonnier(error, mask):
    return (error.float().square() + 1e-8).sqrt().masked_fill(
        ~mask, 0
    ).sum() / mask.sum().clamp_min(1)


def paired_reconstruction_loss(
    prediction, batch, auxiliary=None, *, multiscale_sensor_weight=0.0,
    objective="charbonnier-v1",
):
    """Measured samples determine detail; AHD supplies only coarse RGB color.

    The 4x4 spatial means avoid supervising the network with AHD's fine-scale
    interpolation artifacts. Reference saturation masks apply to both losses.
    Independent low-ISO reference noise remains a limitation of real pairs.
    """
    validate_reconstruction_objective(objective)
    if not math.isfinite(multiscale_sensor_weight) or multiscale_sensor_weight < 0:
        raise ValueError("Multiscale sensor loss weight must be finite and nonnegative")
    reference, valid = batch["sensor_reference"], batch["sensor_mask"].bool()
    penalty = image_log_mse if objective == "image-log-mse-v1" else masked_charbonnier
    sensor = penalty(prediction - reference, valid)
    coarse_valid = F.avg_pool2d(valid.any(1, keepdim=True).float(), 4, 4) >= 0.999
    coarse_prediction = F.avg_pool2d(prediction.float(), 4, 4)
    coarse_reference = F.avg_pool2d(batch["target"].float(), 4, 4)
    display = render(coarse_prediction, batch["wb"], batch["matrix"])
    truth = render(coarse_reference, batch["wb"], batch["matrix"])
    coarse = penalty(display - truth, coarse_valid.expand_as(display))
    auxiliary_loss = prediction.new_zeros(())
    if auxiliary is not None:
        auxiliary_loss = masked_charbonnier(
            auxiliary - mosaic(reference, batch["colors"]), mosaic(valid, batch["colors"])
        )
    loss = sensor + 0.5 * coarse + 0.1 * auxiliary_loss
    terms = {
        "paired_sensor": sensor,
        "paired_coarse_rendered": coarse,
        "paired_auxiliary": auxiliary_loss,
    }
    if multiscale_sensor_weight:
        multiscale = multiscale_sensor_loss(prediction, batch)
        loss = loss + multiscale_sensor_weight * multiscale
        terms["multiscale_sensor"] = multiscale
    return loss, terms
