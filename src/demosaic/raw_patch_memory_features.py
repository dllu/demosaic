"""Neighboring RAW-gradient descriptors for the memory-only global branch."""

import torch
from torch import nn
from torch.nn import functional as F

from .raw_global_memory_features import MemoryOnlyRawGlobalFeatures


def neighboring_gradients(content):
    """Eight neighboring vectors, row-major; zero outside, no center or wrap."""
    if content.ndim != 4 or content.shape[1] != 8 or min(content.shape) < 1:
        raise ValueError("Patch descriptors require nonempty Bx8xHxW signed gradients")
    height, width = content.shape[-2:]
    padded = F.pad(content, (1, 1, 1, 1))
    return torch.cat(
        [
            padded[..., y : y + height, x : x + width]
            for y in range(3)
            for x in range(3)
            if (y, x) != (1, 1)
        ],
        dim=1,
    )


class PatchMemoryRawGlobalFeatures(MemoryOnlyRawGlobalFeatures):
    """Keep the point token and learn a zero-initialized spatial addition.

    Both point and neighboring content still pass through read/write memory;
    there is no added local path to the returned stem offset. Shared tensors
    and constructor RNG stay exact. Every per-phase spatial constant remains
    zero after learning, even with spatially varying variance conditioning.
    """

    def __init__(self):
        super().__init__()
        with torch.random.fork_rng(devices=[]):
            self.patch_embed = nn.Conv2d(64, 32, 1, bias=False, device="cpu")
            nn.init.zeros_(self.patch_embed.weight)

    def embed_content(self, content):
        point = super().embed_content(content)
        patch = self.patch_embed(neighboring_gradients(content)).flatten(2).transpose(1, 2)
        return point + patch
