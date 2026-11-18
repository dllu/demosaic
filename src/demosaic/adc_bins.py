"""Experimental ADC-bin consistency for explicitly calibrated zero-noise inputs."""

import math
from functools import lru_cache

import torch
from torch.nn.functional import max_pool2d

from .cfa import bilinear, malvar, mosaic
from .precision import ieee_fp32


def _settings(bit_depth, black_level, quantizer_precision):
    if type(bit_depth) is not int or not 8 <= bit_depth <= 16:
        raise ValueError("ADC bit depth must be an integer in8..16")
    if not math.isfinite(black_level) or not 0 <= black_level < 1:
        raise ValueError("ADC black fraction must be in[0,1)")
    if quantizer_precision not in {"float32", "float64"}:
        raise ValueError("Declare float32 or float64 ADC simulator arithmetic")
    dtype = getattr(torch, quantizer_precision)
    if float(torch.tensor(black_level, dtype=dtype)) >= 1:
        raise ValueError("Black fraction rounds to one at the declared precision")
    return (1 << bit_depth) - 1, dtype


def _encode(value, levels, black_level, dtype):
    value = value.to(dtype)
    black = torch.as_tensor(black_level, dtype=dtype, device=value.device)
    return ((value * (1 - black) + black).clamp(0, 1) * levels).round().long()


def _decode(codes, levels, black_level, dtype):
    black = torch.as_tensor(black_level, dtype=dtype, device=codes.device)
    return ((codes.to(dtype) / levels - black) / (1 - black)).float()


def _ordered_float(keys):
    # Monotone unsigned ordering across finite float32 values and infinities;
    # NaNs lie outside the searched interval. Both signed zeros are retained.
    bits = torch.where(keys >= 0x80000000, keys ^ 0x80000000, ~keys) & 0xFFFFFFFF
    return bits.to(torch.int32).view(torch.float32)


@lru_cache(maxsize=4)
def _bounds_table(bit_depth, black_level, quantizer_precision):
    levels, dtype = _settings(bit_depth, black_level, quantizer_precision)
    codes = torch.arange(levels + 1, dtype=torch.int64)
    low = torch.full_like(codes, 0x007FFFFF)  # ordered -infinity
    high = torch.full_like(codes, 0xFF800000)  # ordered +infinity
    for _ in range(32):
        middle = (low + high) // 2
        above = _encode(_ordered_float(middle), levels, black_level, dtype) >= codes
        high = torch.where(above, middle, high)
        low = torch.where(above, low, middle + 1)
    if not torch.equal(low, high):
        raise RuntimeError("ADC inverse search did not converge")
    lower = _ordered_float(low)
    upper_keys = torch.cat((low[1:] - 1, low.new_tensor([0xFF800000])))
    upper = _ordered_float(upper_keys)
    if not torch.all(lower <= upper):
        raise RuntimeError("ADC code has no representable float32 preimage")
    return lower, upper, _decode(codes, levels, black_level, dtype)


@lru_cache(maxsize=4)
def _device_table(bit_depth, black_level, quantizer_precision, device):
    return tuple(
        table.to(device) for table in _bounds_table(bit_depth, black_level, quantizer_precision)
    )


def adc_bin_bounds(packed, *, bit_depth, black_level, quantizer_precision):
    """Exact float32 preimages of the declared ADC encoder, including tie rules.

    CPU simulator arithmetic is calibration metadata: the historical FP64 faint
    quantizer and FP32 color-grid quantizer have slightly different boundaries.
    Saturated endpoint codes have one-sided intervals. The packed input must
    match the declared CPU decoder exactly; arbitrary floating RAW is not
    assumed to use this calibration. Tables are constructed on CPU and copied
    to the processing device so CUDA rounding cannot redefine the source codec.
    """
    if packed.dtype != torch.float32 or not torch.isfinite(packed).all():
        raise ValueError("ADC bins require finite float32 packed observations")
    levels, dtype = _settings(bit_depth, black_level, quantizer_precision)
    black = torch.tensor(black_level, dtype=dtype)
    # Invert decoded bin centers in double precision to recover integer codes.
    # This is deliberately separate from encoding signals near bin boundaries.
    codes = ((packed.double() * float(1 - black) + float(black)) * levels).round().long()
    if not ((codes >= 0) & (codes <= levels)).all():
        raise ValueError("Packed values do not match the declared ADC decoder")
    lower, upper, decoded = _device_table(
        bit_depth, black_level, quantizer_precision, str(packed.device)
    )
    if not torch.equal(decoded[codes], packed):
        raise ValueError("Packed values do not match the declared ADC decoder")
    return lower[codes], upper[codes]


def adc_bin_projection(
    prediction,
    packed,
    colors,
    wb=None,
    *,
    bit_depth,
    black_level,
    quantizer_precision,
    shot,
    read,
    mode="malvar",
):
    """Clamp measured ADC sites and optionally lift their residual into missing colors.

    Positive photon/read noise returns the original prediction object. At zero
    noise, only incompatible measured predictions are clamped to their nearest
    feasible float32 value. Malvar lifts the residual with cross-color terms,
    bilinear interpolation uses only same-color residuals, and sites leaves
    missing channels unchanged. Flat-aware delivery uses bilinear where each
    phase's measured codes are constant across its packed 3x3 neighborhood.
    Measured channels are restored exactly after FP32 interpolation. Their
    camera-space squared error cannot increase when truth is in the declared
    bins. Missing-color, rendered-color and spatial errors have no such bound.
    This helper is opt-in; no model config or default inference path calls it.
    """
    if mode not in ("malvar", "bilinear", "sites", "flat-aware"):
        raise ValueError("ADC bin projection mode must be malvar, bilinear, sites or flat-aware")
    if any(not math.isfinite(v) or v < 0 for v in (shot, read)):
        raise ValueError("Noise coefficients must be finite and nonnegative")
    if shot > 0 or read > 0:
        return prediction
    if packed.ndim != 4 or packed.shape[1] != 4:
        raise ValueError("Expected four packed CFA phases")
    if prediction.shape != (len(packed), 3, packed.shape[2] * 2, packed.shape[3] * 2):
        raise ValueError("Prediction and packed dimensions differ")
    if not torch.isfinite(prediction).all():
        raise ValueError("Prediction must be finite")
    if colors.ndim == 1:
        colors = colors[None].expand(len(packed), -1)
    if colors.shape != (len(packed), 4):
        raise ValueError("One four-phase CFA description is required per image")
    patterns = colors.new_tensor([[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
    if not ((colors[:, None] == patterns[None]).all(-1).any(-1)).all():
        raise ValueError("Expected a Bayer color pattern")
    with torch.autocast(prediction.device.type, enabled=False), ieee_fp32():
        p = prediction.float()
        lower, upper = adc_bin_bounds(
            packed,
            bit_depth=bit_depth,
            black_level=black_level,
            quantizer_precision=quantizer_precision,
        )
        observed = mosaic(p, colors)
        compatible = (observed >= lower) & (observed <= upper)
        nearest = torch.where(compatible, observed, observed.clamp(min=lower, max=upper))
        residual = nearest - observed
        if not residual.count_nonzero():
            return prediction
        if mode == "sites":
            output = p.clone()
        else:
            correction = (
                bilinear(residual, colors) if mode == "bilinear" else malvar(residual, colors, wb)
            )
            if mode == "flat-aware":
                high = max_pool2d(packed, 3, stride=1, padding=1)
                low = -max_pool2d(-packed, 3, stride=1, padding=1)
                flat = (low == high).all(dim=1, keepdim=True)
                flat_pixels = flat.repeat_interleave(2, dim=-2).repeat_interleave(2, dim=-1)
                correction = torch.where(flat_pixels, bilinear(residual, colors), correction)
            output = torch.where(correction != 0, p + correction, p)
        for b in range(len(p)):
            for phase, channel in enumerate(colors[b]):
                y, x = divmod(phase, 2)
                output[b, int(channel), y::2, x::2] = nearest[b, phase]
        return output
