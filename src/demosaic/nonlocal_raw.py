"""Noise-conditioned RAW denoising and a measured-CFA update of a DINO parent.

The externally trained NLFeMF checkpoint is a comparison model. Its training
data differ from this project's free-image pipeline. Neither this adapter nor
the released weights establish superiority on our fine-wire/flat-field goal.
"""

from pathlib import Path

import torch
from torch import nn

from .cfa import malvar, mosaic
from .precision import ieee_fp32

# Flipping an even native image flips its packed grid and its phase-slot bits.
# The resulting CFA is RGGB. RGBG then swaps its last two packed channels.
_TRANSFORMS = {
    (0, 1, 1, 2): (False, False),
    (2, 1, 1, 0): (True, True),
    (1, 0, 2, 1): (False, True),
    (1, 2, 0, 1): (True, False),
}


def canonical_raw(packed, colors):
    """Map physical Bayer slots to RGGB-oriented RGBG, including spatial flips."""
    if packed.ndim != 4 or packed.shape[1] != 4 or min(packed.shape) < 1:
        raise ValueError("Expected nonempty N x 4 x H x W packed RAW")
    if colors.ndim == 1:
        colors = colors[None].expand(len(packed), -1)
    if colors.shape != (len(packed), 4):
        raise ValueError("Expected one four-slot CFA per image")
    result, transforms = [], []
    for value, layout in zip(packed, colors, strict=True):
        pattern = tuple(layout.tolist())
        if pattern not in _TRANSFORMS:
            raise ValueError("Expected a standard Bayer CFA")
        vertical, horizontal = _TRANSFORMS[pattern]
        mask = 2 * vertical + horizontal
        order = [phase ^ mask for phase in range(4)]
        value = value[order]
        if vertical:
            value = value.flip(-2)
        if horizontal:
            value = value.flip(-1)
        result.append(value[[0, 1, 3, 2]])
        transforms.append((vertical, horizontal))
    return torch.stack(result), transforms


def physical_raw(canonical, transforms):
    """Invert canonical_raw exactly, without interpolation or value changes."""
    if canonical.ndim != 4 or canonical.shape[1] != 4 or len(canonical) != len(transforms):
        raise ValueError("Expected RGBG values and matching spatial transforms")
    result = []
    for value, (vertical, horizontal) in zip(canonical, transforms, strict=True):
        value = value[[0, 1, 3, 2]]
        if horizontal:
            value = value.flip(-1)
        if vertical:
            value = value.flip(-2)
        mask = 2 * vertical + horizontal
        result.append(value[[phase ^ mask for phase in range(4)]])
    return torch.stack(result)


class NonlocalRawDemosaic(nn.Module):
    """One released RAW-network call, followed by two fixed RGB reconstructions.

    The returned hybrid is parent + Malvar(denoised_RAW - CFA(parent)). This
    keeps the parent's RGB interpolation residual while changing measured CFA
    samples to the RAW estimate, up to FP32 rounding. The direct Malvar result
    is returned separately for comparison. Both can retain or add false detail.

    This frontend uses the pinned compiled sampling operator for inference.
    Training is not exposed here. The released model clips its output to[0,1];
    the signed RGB residual and final camera RGB are not clipped.
    """

    def __init__(self):
        super().__init__()
        from .nonlocal_matchfilter import SimpleBlockMatchingUNet

        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(17001).get_state())
            self.network = SimpleBlockMatchingUNet(
                input_channels=8,
                output_channels=4,
                n_features=32,
                neighbours={"scale1": [5, 5], "scale2": [3, 5], "scale3": [3, 3]},
                max_search_dist=9.0,
            )

    def load_released_state(self, path):
        payload = torch.load(Path(path), map_location="cpu", weights_only=True)
        self.network.load_state_dict(payload["state_dict"], strict=True)
        return self

    def forward(self, base, packed, variance, colors, wb=None, *, return_aux=False):
        if packed.shape != variance.shape or packed.dtype != torch.float32:
            raise ValueError("Expected matching FP32 RAW and variance")
        if base.shape != (len(packed), 3, 2 * packed.shape[-2], 2 * packed.shape[-1]):
            raise ValueError("Expected matching native camera RGB parent")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            values, transforms = canonical_raw(packed.clamp(0, 1), colors)
            conditioned, same = canonical_raw(variance.clamp_min(0).sqrt(), colors)
            assert transforms == same
            clean = self.network(torch.cat((values, conditioned), 1)).clamp(0, 1)
            denoised = physical_raw(clean, transforms)
            direct = malvar(denoised, colors, wb)
            change = malvar(denoised - mosaic(base, colors), colors, wb)
            result = base + change
            if return_aux:
                return result, {
                    "denoised_packed": denoised,
                    "direct_rgb": direct,
                    "correction": change,
                }
            return result
