"""Optional local attention over signed, phase-preserving RAW differences.

This independently implemented feature branch supplies native RGB-stem offsets;
it is not an RGB prediction, a fixed detail-strength control or a paper reproduction.
"""

import torch
from torch import nn
from torch.nn import functional as F

from .precision import ieee_fp32


def partition_windows(values, size):
    """BHWC -> independent square windows, without periodic wraparound."""
    batch, height, width, channels = values.shape
    return (
        values.reshape(batch, height // size, size, width // size, size, channels)
        .permute(0, 1, 3, 2, 4, 5)
        .reshape(-1, size * size, channels)
    )


def restore_windows(values, size, batch, height, width):
    return (
        values.reshape(batch, height // size, width // size, size, size, -1)
        .permute(0, 1, 3, 2, 4, 5)
        .reshape(batch, height, width, -1)
    )


class SpatialWindowBlock(nn.Module):
    """Bias-free value/MLP paths preserve zero content after learning.

    Padding changes the partition origin instead of rolling image borders into
    one another. Invalid padded keys cannot receive attention probability.
    """

    def __init__(self, width=32, heads=4, window=8, shift=0):
        super().__init__()
        if width % heads or not 0 <= shift < window:
            raise ValueError("Invalid window attention dimensions")
        self.width, self.heads, self.window, self.shift = width, heads, window, shift
        self.q = nn.Linear(width, width, bias=False, device="cpu")
        self.k = nn.Linear(width, width, bias=False, device="cpu")
        self.v = nn.Linear(width, width, bias=False, device="cpu")
        self.condition_q = nn.Linear(16, width, bias=False, device="cpu")
        self.out = nn.Linear(width, width, bias=False, device="cpu")
        self.up = nn.Linear(width, 2 * width, bias=False, device="cpu")
        self.down = nn.Linear(2 * width, width, bias=False, device="cpu")
        self.norm1 = nn.Parameter(torch.ones(width, device="cpu"))
        self.norm2 = nn.Parameter(torch.ones(width, device="cpu"))
        self.relative_bias = nn.Parameter(torch.zeros(heads, (2 * window - 1) ** 2, device="cpu"))
        y, x = torch.meshgrid(
            torch.arange(window, device="cpu"), torch.arange(window, device="cpu"), indexing="ij"
        )
        dy = y.flatten()[:, None] - y.flatten()[None, :]
        dx = x.flatten()[:, None] - x.flatten()[None, :]
        index = (dy + window - 1) * (2 * window - 1) + dx + window - 1
        self.register_buffer("relative_index", index, persistent=False)

    @staticmethod
    def normalize(values, gain):
        scale = (values.square().mean(-1, keepdim=True) + 1e-4).sqrt()
        return values / scale * gain, scale

    def attention(self, query, key, value, valid):
        """Window-token attention, exposed for independent dense-matrix checks."""
        count, tokens, _ = query.shape

        def split(values):
            return values.reshape(count, tokens, self.heads, -1).transpose(1, 2)

        q, k, v = (split(x) for x in (query, key, value))
        scores = q @ k.transpose(-2, -1) / ((self.width // self.heads) ** 0.5)
        scores = scores + self.relative_bias[:, self.relative_index][None]
        scores = scores.masked_fill(~valid[:, None, None, :], -torch.inf)
        return (scores.softmax(-1) @ v).transpose(1, 2).reshape(count, tokens, self.width)

    def forward(self, values, condition):
        batch, height, width, _ = values.shape
        size, shift = self.window, self.shift
        padding = (0, 0, shift, -(width + shift) % size, shift, -(height + shift) % size)
        normalized, _ = self.normalize(values, self.norm1)
        query = F.pad(self.q(normalized) + self.condition_q(condition), padding)
        key = F.pad(self.k(normalized), padding)
        # Unnormalized values keep the observed detail amplitude in this path.
        value = F.pad(self.v(values), padding)
        valid = F.pad(torch.ones_like(values[..., :1], dtype=torch.bool), padding)
        hp, wp = query.shape[1:3]
        windows = [partition_windows(x, size) for x in (query, key, value)]
        mask = partition_windows(valid, size)[..., 0]
        attended = self.attention(*windows, mask)
        attended = restore_windows(attended, size, batch, hp, wp)
        values = values + self.out(attended[:, shift : shift + height, shift : shift + width])
        normalized, scale = self.normalize(values, self.norm2)
        return values + self.down(F.gelu(self.up(normalized))) * scale


class RawSpatialFeatures(nn.Module):
    """Two packed-grid attention blocks -> phase-aligned native64 stem offsets.

    Signed horizontal/vertical differences retain all four CFA phases. Every
    per-phase spatial constant gives exactly zero content, even after learning.
    This does not protect a separately trained common restoration trunk.
    """

    def __init__(self):
        super().__init__()
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(13101).get_state())
            self.embed = nn.Linear(8, 32, bias=False, device="cpu")
            self.blocks = nn.ModuleList([SpatialWindowBlock(shift=0), SpatialWindowBlock(shift=4)])
            self.expand = nn.Linear(32, 64, bias=False, device="cpu")
            self.project = nn.Conv2d(16, 64, 1, bias=False, device="cpu")
        nn.init.zeros_(self.project.weight)

    def forward(self, packed, variance, colors, span=None):
        if packed.ndim != 4 or packed.shape[1] != 4 or variance.shape != packed.shape:
            raise ValueError("Spatial features require matching four-phase RAW and variance")
        batch, _, height, width = packed.shape
        if min(height, width) < 1:
            raise ValueError("Spatial features require nonempty packed dimensions")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if colors.shape != (batch, 4):
            raise ValueError("Spatial features require one CFA layout per image")
        if span is not None and span.shape != (batch, 1, 1, 1):
            raise ValueError("Spatial features require one restoration scale per image")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            packed, variance = packed.float(), variance.float()
            scale = packed.new_ones(batch, 1, 1, 1) if span is None else span.float()
            scale = scale.clamp_min(1e-6)
            # Subtract before scaling to keep spatial constants exactly zero.
            dx = F.pad(packed[..., 1:] - packed[..., :-1], (0, 1))
            dy = F.pad(packed[..., 1:, :] - packed[..., :-1, :], (0, 0, 0, 1))
            content = torch.cat((dx, dy), 1) / scale
            noise = torch.log1p(variance.clamp_min(0) / scale.square())
            placement = F.one_hot(colors, 3).flatten(1).to(packed.dtype)
            placement = placement[:, :, None, None].expand(-1, -1, height, width)
            condition = torch.cat((noise, placement), 1).permute(0, 2, 3, 1)
            features = self.embed(content.permute(0, 2, 3, 1))
            for block in self.blocks:
                features = block(features, condition)
            latent = self.expand(features).permute(0, 3, 1, 2)
            return self.project(F.pixel_shuffle(latent, 2))
