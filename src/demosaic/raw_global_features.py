"""Content-dependent global RAW summaries with linear spatial attention cost."""

import torch
from torch import nn
from torch.nn import functional as F

from .precision import ieee_fp32


def cross_attention(query, key, value, heads=4):
    """Independent per-image attention; query and memory lengths may differ."""
    if query.ndim != 3 or key.ndim != 3 or type(heads) is not int or heads < 1:
        raise ValueError("Global attention requires three-dimensional features and positive heads")
    batch, queries, width = query.shape
    tokens = key.shape[1]
    if width % heads or key.shape != value.shape or key.shape[::2] != (batch, width):
        raise ValueError("Global attention requires matching per-image key/value channels")
    q = query.reshape(batch, queries, heads, width // heads).transpose(1, 2)
    k = key.reshape(batch, tokens, heads, width // heads).transpose(1, 2)
    v = value.reshape(batch, tokens, heads, width // heads).transpose(1, 2)
    weights = (q @ k.transpose(-2, -1) / (width // heads) ** 0.5).softmax(-1)
    return (weights @ v).transpose(1, 2).reshape(batch, queries, width)


def require_resume_global_features(previous, current):
    """Reject a changed global branch before constructing a resumed model."""
    old = previous.get("model", {}).get("raw_global_features", False)
    new = current.get("model", {}).get("raw_global_features", False)
    if type(old) is not bool or type(new) is not bool or old != new:
        raise ValueError("Resume RAW global features differ; initialize a new run")
    modes = [
        config.get("model", {}).get("raw_global_conditioning", "legacy-v1")
        for config in (previous, current)
    ]
    if any(
        type(mode) is not str
        or mode not in ("legacy-v1", "cosine-rms-v2", "memory-only-v3", "patch-memory-v4")
        for mode in modes
    ):
        raise ValueError("Resume RAW global conditioning is invalid")
    if modes[0] != modes[1] or not new and modes[1] != "legacy-v1":
        raise ValueError("Resume RAW global conditioning differs; initialize a new run")


class RawGlobalFeatures(nn.Module):
    """64 learned queries summarize signed detail, then return context to pixels.

    Values retain their amplitude rather than receiving RMS normalization.
    Bias-free content paths make all per-phase spatial constants exactly zero,
    even after learning. This does not protect a separately trained RGB trunk.
    """

    def __init__(self):
        super().__init__()
        with torch.random.fork_rng(devices=[]):
            torch.set_rng_state(torch.Generator(device="cpu").manual_seed(13601).get_state())
            self.latents = nn.Parameter(torch.empty(1, 64, 32, device="cpu"))
            nn.init.normal_(self.latents, std=0.02)
            self.embed = nn.Linear(8, 32, bias=False, device="cpu")
            self.to_keys = nn.Linear(32, 32, bias=False, device="cpu")
            self.to_values = nn.Linear(32, 32, bias=False, device="cpu")
            self.condition = nn.Linear(16, 32, bias=False, device="cpu")
            self.read_query = nn.Linear(32, 32, bias=False, device="cpu")
            self.read_out = nn.Linear(32, 32, bias=False, device="cpu")
            self.write_query = nn.Linear(32, 32, bias=False, device="cpu")
            self.write_key = nn.Linear(32, 32, bias=False, device="cpu")
            self.write_value = nn.Linear(32, 32, bias=False, device="cpu")
            self.write_out = nn.Linear(32, 32, bias=False, device="cpu")
            self.up = nn.Linear(32, 64, bias=False, device="cpu")
            self.down = nn.Linear(64, 32, bias=False, device="cpu")
            self.expand = nn.Linear(32, 64, bias=False, device="cpu")
            self.project = nn.Conv2d(16, 64, 1, bias=False, device="cpu")
            self.content_gain = nn.Parameter(torch.ones(32, device="cpu"))
            self.memory_gain = nn.Parameter(torch.ones(32, device="cpu"))
            self.ff_gain = nn.Parameter(torch.ones(32, device="cpu"))
        nn.init.zeros_(self.project.weight)

    @staticmethod
    def normalize(value, gain):
        scale = (value.square().mean(-1, keepdim=True) + 1e-4).sqrt()
        return value / scale * gain, scale

    def mix(self, content, condition):
        """Expose the global mixer for independent attention and batching checks."""
        normalized, _ = self.normalize(content, self.content_gain)
        keys = self.to_keys(normalized) + self.condition(condition)
        queries = self.read_query(self.latents).expand(content.shape[0], -1, -1)
        memory = self.read_out(cross_attention(queries, keys, self.to_values(content)))
        normalized_memory, _ = self.normalize(memory, self.memory_gain)
        query = self.write_query(normalized) + self.condition(condition)
        content = content + self.write_out(
            cross_attention(query, self.write_key(normalized_memory), self.write_value(memory))
        )
        normalized, scale = self.normalize(content, self.ff_gain)
        return content + self.down(F.gelu(self.up(normalized))) * scale

    def embed_content(self, content):
        """Point embedding; optional variants can add spatial descriptors here."""
        return self.embed(content.flatten(2).transpose(1, 2))

    def forward(self, packed, variance, colors, span=None):
        if packed.ndim != 4 or packed.shape[1] != 4 or variance.shape != packed.shape:
            raise ValueError("Global features require matching four-phase RAW and variance")
        batch, _, height, width = packed.shape
        if min(batch, height, width) < 1:
            raise ValueError("Global features require nonempty image dimensions")
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        if colors.shape != (batch, 4):
            raise ValueError("Global features require one CFA layout per image")
        if span is not None and span.shape != (batch, 1, 1, 1):
            raise ValueError("Global features require one restoration scale per image")
        with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
            packed, variance = packed.float(), variance.float()
            scale = packed.new_ones(batch, 1, 1, 1) if span is None else span.float()
            scale = scale.clamp_min(1e-6)
            dx = F.pad(packed[..., 1:] - packed[..., :-1], (0, 1))
            dy = F.pad(packed[..., 1:, :] - packed[..., :-1, :], (0, 0, 0, 1))
            content = torch.cat((dx, dy), 1) / scale
            noise = torch.log1p(variance.clamp_min(0) / scale.square())
            placement = F.one_hot(colors, 3).flatten(1).to(packed.dtype)
            placement = placement[:, :, None, None].expand(-1, -1, height, width)
            condition = torch.cat((noise, placement), 1).flatten(2).transpose(1, 2)
            features = self.embed_content(content)
            features = self.mix(features, condition)
            latent = self.expand(features).transpose(1, 2).reshape(batch, 64, height, width)
            return self.project(F.pixel_shuffle(latent, 2))
