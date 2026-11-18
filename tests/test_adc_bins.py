"""Independent exhaustive code-boundary and measured-error checks."""

import numpy as np
import pytest
import torch

from demosaic.adc_bins import adc_bin_bounds, adc_bin_projection, near_adc_residual_projection
from demosaic.cfa import color_indices, mosaic


def encode_numpy(value, bits, black, precision):
    dtype = np.dtype(precision).type
    value, offset = np.asarray(value, dtype=dtype), dtype(black)
    return np.rint(np.clip(value * (dtype(1) - offset) + offset, 0, 1) * dtype(2**bits - 1)).astype(
        np.int64
    )


def decode_numpy(codes, bits, black, precision):
    dtype = np.dtype(precision).type
    offset = dtype(black)
    return ((codes.astype(dtype) / dtype(2**bits - 1) - offset) / (dtype(1) - offset)).astype(
        np.float32
    )


@pytest.mark.parametrize("bits", [8, 16])
@pytest.mark.parametrize("black", [0.0, 0.03])
@pytest.mark.parametrize("precision", ["float32", "float64"])
def test_every_code_and_its_adjacent_float32_boundaries(bits, black, precision):
    codes = np.arange(2**bits)
    observed = torch.from_numpy(decode_numpy(codes, bits, black, precision))
    low, high = adc_bin_bounds(
        observed, bit_depth=bits, black_level=black, quantizer_precision=precision
    )
    lo, hi = low.numpy(), high.numpy()
    np.testing.assert_array_equal(encode_numpy(lo, bits, black, precision), codes)
    np.testing.assert_array_equal(encode_numpy(hi, bits, black, precision), codes)
    before = np.nextafter(lo[1:], np.float32(-np.inf))
    after = np.nextafter(hi[:-1], np.float32(np.inf))
    assert np.all(encode_numpy(before, bits, black, precision) < codes[1:])
    assert np.all(encode_numpy(after, bits, black, precision) > codes[:-1])
    assert np.isneginf(lo[0]) and np.isposinf(hi[-1])


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("precision", ["float32", "float64"])
@pytest.mark.parametrize("mode", ["malvar", "bilinear", "sites", "flat-aware"])
def test_realizable_target_codes_measured_error_and_idempotence(pattern, precision, mode):
    generator = torch.Generator().manual_seed(91)
    truth = torch.rand(2, 3, 16, 16, generator=generator) * 1.3 - 0.1
    colors = color_indices(pattern)[None].expand(2, -1)
    sampled = mosaic(truth, colors).numpy()
    codes = encode_numpy(sampled, 16, 0.03, precision)
    observed = torch.from_numpy(decode_numpy(codes, 16, 0.03, precision))
    prediction = truth + 0.05 * torch.randn(truth.shape, generator=generator)
    options = {
        "bit_depth": 16,
        "black_level": 0.03,
        "quantizer_precision": precision,
        "shot": 0.0,
        "read": 0.0,
        "mode": mode,
    }
    result = adc_bin_projection(prediction, observed, colors, **options)
    actual = mosaic(result, colors)
    np.testing.assert_array_equal(encode_numpy(actual.numpy(), 16, 0.03, precision), codes)
    reference = mosaic(truth, colors).double()
    assert torch.all(
        (actual.double() - reference).square()
        <= (mosaic(prediction, colors).double() - reference).square()
    )
    assert torch.equal(adc_bin_projection(result, observed, colors, **options), result)
    assert adc_bin_projection(truth, observed, colors, **options) is truth
    assert (
        adc_bin_projection(prediction, observed, colors, **dict(options, shot=0.00128))
        is prediction
    )


@pytest.mark.parametrize("mode", ["bilinear", "sites"])
def test_same_color_modes_keep_unaffected_channels_exactly(mode):
    truth = torch.full((1, 3, 8, 8), 0.24)
    colors = color_indices("GBRG")
    measured = mosaic(truth, colors).numpy()
    observed = torch.from_numpy(
        decode_numpy(encode_numpy(measured, 16, 0.03, "float64"), 16, 0.03, "float64")
    )
    prediction = truth.clone()
    prediction[:, 0] += 0.04
    result = adc_bin_projection(
        prediction,
        observed,
        colors,
        bit_depth=16,
        black_level=0.03,
        quantizer_precision="float64",
        shot=0,
        read=0,
        mode=mode,
    )
    assert torch.equal(result[:, 1:], prediction[:, 1:])
    red = torch.zeros((8, 8), dtype=torch.bool)
    red[1::2, 0::2] = True
    if mode == "sites":
        assert torch.equal(result[0, 0, ~red], prediction[0, 0, ~red])
    else:
        torch.testing.assert_close(result[0, 0, ~red], result[0, 0, red][0].expand(48))


def test_wrong_decoder_and_negative_noise_rejected():
    packed = torch.full((1, 4, 2, 2), 0.1234567)
    with pytest.raises(ValueError, match="decoder"):
        adc_bin_bounds(packed, bit_depth=16, black_level=0.03, quantizer_precision="float64")
    with pytest.raises(ValueError, match="Noise"):
        adc_bin_projection(
            torch.zeros(1, 3, 4, 4),
            packed,
            color_indices("RGGB"),
            bit_depth=16,
            black_level=0.03,
            quantizer_precision="float64",
            shot=-1.0,
            read=0.0,
        )


def test_flat_aware_lift_uses_per_phase_constancy():
    colors = color_indices("RGGB")
    truth = torch.tensor([0.22, 0.31, 0.43]).reshape(1, 3, 1, 1).expand(2, 3, 8, 8).clone()
    truth[1] += torch.linspace(0, 0.16, 8)
    packed = mosaic(truth, colors).numpy()
    codes = encode_numpy(packed, 16, 0.03, "float64")
    observed = torch.from_numpy(decode_numpy(codes, 16, 0.03, "float64"))
    prediction = torch.full_like(truth, 0.25)
    args = {
        "bit_depth": 16,
        "black_level": 0.03,
        "quantizer_precision": "float64",
        "shot": 0,
        "read": 0,
    }
    result = adc_bin_projection(prediction, observed, colors, **args, mode="flat-aware")
    bilinear = adc_bin_projection(prediction, observed, colors, **args, mode="bilinear")
    malvar = adc_bin_projection(prediction, observed, colors, **args)
    assert not torch.equal(malvar[0], bilinear[0])
    assert torch.equal(result[0], bilinear[0])
    assert torch.equal(result[1], malvar[1])


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_near_adc_measured_update_matches_independent_formula(pattern):
    colors = color_indices(pattern)
    prediction = torch.linspace(0.12, 0.35, 3 * 8 * 8).reshape(1, 3, 8, 8)
    measured = mosaic(prediction, colors).numpy().astype(np.float64)
    packed = (measured + np.tile([0.08, -0.00002, -0.12, 0.00001], (4, 1))).astype(np.float32)
    packed[..., 0, 0] = 1
    packed[..., 0, 1] = np.float32(-0.03 / 0.97)
    shot, read = 1e-8, 1e-10
    sigma = np.sqrt(shot * measured + read + (1 / (65535 * 0.97)) ** 2 / 12)
    weight = 4 / (4 + 65535 * sigma)
    residual = packed - measured
    excess = np.sign(residual) * np.maximum(np.abs(residual) - 4 * sigma, 0)
    updated = measured + weight * residual + (1 - weight) * excess
    updated[..., 0, :2] = measured[..., 0, :2]
    projected = near_adc_residual_projection(
        prediction, torch.from_numpy(packed), colors, shot=shot, read=read, black_level=0.03
    )
    np.testing.assert_allclose(mosaic(projected, colors).numpy(), updated, rtol=0, atol=6e-8)


@pytest.mark.parametrize("shot,read", [(0.0, 0.0), (3.2e-7, 1e-10), (0.0, 1e-5)])
def test_near_adc_falls_back_to_original_object_outside_range(shot, read):
    prediction = torch.zeros(1, 3, 8, 8)
    colors = color_indices("RGGB")
    packed = torch.full((1, 4, 4, 4), 0.2)
    assert (
        near_adc_residual_projection(
            prediction, packed, colors, shot=shot, read=read, black_level=0.03
        )
        is prediction
    )
