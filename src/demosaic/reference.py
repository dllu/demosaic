"""Optional evaluation adapter for separately acquired RawNIND reference code."""

import importlib.util
import sys
import types
from pathlib import Path

import torch
from torch import nn
from torch.nn import functional as F

from .cfa import PATTERNS, mosaic, pack, unpack


def publisher_input_scale(white_levels, black_levels, adc_white_level):
    """Convert our per-phase camera-white units to upstream global-ADC units."""
    if adc_white_level is None or len(white_levels) != 4 or len(black_levels) != 4:
        raise ValueError("Four phase levels and the global ADC white level are required")
    if any(adc_white_level <= b or w <= b for w, b in zip(white_levels, black_levels)):
        raise ValueError("Invalid RAW normalization levels")
    return [(w - b) / (adc_white_level - b) for w, b in zip(white_levels, black_levels)]


class RawNind(nn.Module):
    def __init__(self, network, gain_mode="input-mean", *, input_scale=None, clip_input=False):
        super().__init__()
        if gain_mode not in ("input-mean", "cfa-ls", "cfa-channel"):
            raise ValueError("Unknown gain matching method")
        self.network = network.eval()
        self.gain_mode = gain_mode
        self.clip_input = clip_input
        self.register_buffer(
            "input_scale",
            None
            if input_scale is None
            else torch.as_tensor(input_scale, dtype=torch.float32).reshape(4),
            persistent=False,
        )

    def forward(self, packed, variance, colors, wb=None, matrix=None):
        if colors.ndim == 1:
            colors = colors[None].expand(packed.shape[0], -1)
        outputs = []
        flips = {"RGGB": (), "BGGR": (-2, -1), "GRBG": (-1,), "GBRG": (-2,)}
        patterns = {tuple(value): name for name, value in PATTERNS.items()}
        # Normalize the actual mosaic geometry, not just channel names: RGB
        # PixelShuffle's spatial phase is part of the pretrained model contract.
        for sample, labels in zip(packed, colors):
            pattern = patterns[tuple(labels.tolist())]
            prepared = sample.float()
            if self.input_scale is not None:
                prepared = prepared * self.input_scale.to(prepared)[:, None, None]
            if self.clip_input:
                prepared = prepared.clamp(0, 1)
            raw = unpack(prepared[None])
            if flips[pattern]:
                raw = raw.flip(flips[pattern])
            canonical = pack(raw)
            h, w = canonical.shape[-2:]
            canonical = F.pad(canonical, (0, -w % 16, 0, -h % 16), mode="replicate")
            with torch.autocast(device_type=packed.device.type, enabled=False):
                output = self.network(canonical.float())[..., : 2 * h, : 2 * w]
            if flips[pattern]:
                output = output.flip(flips[pattern])
            if self.gain_mode == "input-mean":
                denominator = output.mean()
                measured = sample.clamp(0, 1) if self.clip_input else sample
                gain = measured.mean() / torch.where(
                    denominator.abs() > 1e-12, denominator, denominator.new_ones(())
                )
            else:
                observed = mosaic(output, labels[None])
                if self.gain_mode == "cfa-ls":
                    gain = (observed * sample[None]).sum() / observed.square().sum().clamp_min(
                        1e-12
                    )
                else:
                    gains = []
                    for channel in range(3):
                        mask = (labels == channel)[None, :, None, None]
                        gains.append(
                            (observed * sample[None] * mask).sum()
                            / (observed.square() * mask).sum().clamp_min(1e-12)
                        )
                    gain = torch.stack(gains)[None, :, None, None]
            outputs.append(output * gain)
        return torch.cat(outputs)


def load_rawnind(
    directory, *, gain_mode="input-mean", device="cpu", input_scale=None, clip_input=False
):
    directory = Path(directory)
    # The imported upstream module only uses rawproc in a separate Passthrough
    # class. Avoid importing its entire research training dependency stack.
    names = ("rawnind", "rawnind.libs", "rawnind.libs.rawproc")
    previous = {name: sys.modules.get(name) for name in names}
    try:
        for name in names:
            sys.modules[name] = types.ModuleType(name)
        spec = importlib.util.spec_from_file_location(
            "demosaic_rawnind_reference", directory / "raw_denoiser.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, value in previous.items():
            if value is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = value
    network = module.UtNet2(in_channels=4, funit=32, activation="LeakyReLU")
    state = torch.load(directory / "utnet2-bayer.pt", map_location="cpu", weights_only=True)
    network.load_state_dict(state, strict=True)
    return (
        RawNind(network, gain_mode, input_scale=input_scale, clip_input=clip_input)
        .to(device)
        .eval()
    )
