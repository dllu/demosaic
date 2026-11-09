"""Direct QR noise operators, physical CFA transport and overlapping-window bounds."""

import numpy as np
import pytest
import torch

from demosaic.cfa import color_indices, mosaic
from demosaic.cfa_scale_support import (
    AMPLITUDE_FLOOR_SQUARED,
    cfa_cross_scale_support,
    cfa_scale_amplitudes,
    local_amplitude_grid,
    scale_agreement,
)
from demosaic.late_cfa_innovation_wave import cfa_innovation_wave_maps


def direct_operator(height, width, chosen, box):
    """Explicit affine QR and real wave Gram, unrelated to integral moments."""
    x0, y0, nx, ny = box
    y, x = np.mgrid[y0 : y0 + ny, x0 : x0 + nx]
    ky, kx = [
        b if b <= (n - 1) // 2 else b - n for b, n in zip(chosen, [height, width], strict=True)
    ]
    theta = 2 * np.pi * (ky * y / height + kx * x / width)
    nuisance = np.stack((np.ones_like(x), x - x.mean(), y - y.mean()), -1).reshape(-1, 3)
    q, _ = np.linalg.qr(nuisance, mode="reduced")
    wave = np.stack((np.cos(theta), -np.sin(theta)), -1).reshape(-1, 2)
    residual = wave - q @ (q.T @ wave)
    eig, vectors = np.linalg.eigh(residual.T @ residual)
    keep = eig > nx * ny * 1e-10
    inverse = (vectors * np.where(keep, 1 / np.maximum(eig, 1e-300), 0)) @ vectors.T
    kernel = inverse @ residual.T
    return kernel, int(keep.sum())


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_every_amplitude_and_covariance_entry_matches_direct_heteroscedastic_QR(dtype):
    rng = np.random.default_rng(20001)
    raw = torch.tensor(rng.normal(scale=0.003, size=(2, 3, 24, 31)), dtype=dtype)
    variance = torch.tensor(rng.uniform(1e-7, 8e-6, raw.shape), dtype=dtype)
    bins = torch.tensor([[3, 4], [22, 29]])
    boxes = torch.tensor([[0, 0, 5, 5], [10, 9, 11, 9], [21, 17, 10, 7]])
    amplitude, covariance, rank = local_amplitude_grid(raw, variance, bins, boxes)
    for n in range(2):
        for l, box in enumerate(boxes.numpy()):
            kernel, expected_rank = direct_operator(24, 31, bins[n].numpy(), box)
            assert rank[n, l] == expected_rank == 2
            x, y, w, h = box
            for p in range(3):
                values = raw[n, p, y : y + h, x : x + w].double().numpy().ravel()
                noise = variance[n, p, y : y + h, x : x + w].double().numpy().ravel()
                solution = kernel @ values
                expected_cov = (kernel * noise) @ kernel.T
                np.testing.assert_allclose(
                    amplitude[n, p, l], solution[0] + 1j * solution[1], rtol=2e-9, atol=2e-12
                )
                np.testing.assert_allclose(covariance[n, p, l], expected_cov, rtol=3e-9, atol=2e-16)
    assert amplitude.dtype == torch.complex128 and covariance.dtype == torch.float64
    assert (torch.linalg.eigvalsh(covariance) >= -1e-16).all()


@pytest.mark.parametrize(
    "bin_yx,expected_rank", [([0, 0], 0), ([0, 16], 1), ([12, 0], 1), ([12, 16], 1)]
)
def test_zero_and_singular_nyquist_covariance_have_the_actual_numerical_rank(bin_yx, expected_rank):
    rng = np.random.default_rng(20002)
    raw = torch.tensor(rng.normal(size=(1, 2, 24, 32)), dtype=torch.float64)
    variance = torch.tensor(rng.uniform(0.1, 0.8, raw.shape))
    boxes = torch.tensor([[0, 0, 7, 6], [10, 9, 11, 9], [27, 19, 5, 5]])
    amplitude, covariance, ranks = local_amplitude_grid(
        raw, variance, torch.tensor([bin_yx]), boxes
    )
    assert (ranks == expected_rank).all()
    for l, box in enumerate(boxes.numpy()):
        kernel, _ = direct_operator(24, 32, bin_yx, box)
        x, y, w, h = box
        for p in range(2):
            expected = (kernel * variance[0, p, y : y + h, x : x + w].numpy().ravel()) @ kernel.T
            np.testing.assert_allclose(covariance[0, p, l], expected, rtol=1e-10, atol=1e-12)
    if expected_rank == 0:
        assert amplitude.count_nonzero() == covariance.count_nonzero() == 0


def test_affine_invariance_variance_scaling_and_zero_variance():
    rng = np.random.default_rng(20003)
    raw = torch.tensor(rng.normal(size=(1, 4, 24, 31)), dtype=torch.float64)
    variance = torch.tensor(rng.uniform(1e-6, 3e-6, raw.shape))
    bins, boxes = torch.tensor([[2, 3]]), torch.tensor([[0, 0, 6, 6], [8, 7, 13, 13]])
    yy, xx = torch.meshgrid(torch.arange(24), torch.arange(31), indexing="ij")
    plane = (0.1 + 0.0002 * xx.double() - 0.0003 * yy.double())[None, None]
    a, cov, _ = local_amplitude_grid(raw, variance, bins, boxes)
    moved, same, _ = local_amplitude_grid(raw + plane, variance, bins, boxes)
    torch.testing.assert_close(a, moved, rtol=1e-10, atol=1e-11)
    torch.testing.assert_close(cov, same, rtol=0, atol=0)
    unchanged, scaled, _ = local_amplitude_grid(raw, variance * 7, bins, boxes)
    torch.testing.assert_close(a, unchanged, rtol=0, atol=0)
    torch.testing.assert_close(cov * 7, scaled, rtol=1e-9, atol=1e-16)
    _, zero, _ = local_amplitude_grid(raw, variance * 0, bins, boxes)
    assert zero.count_nonzero() == 0


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_physical_tone_all_layouts_scales_and_old_synthesis_basis(pattern, dtype):
    h, w = 24, 31
    yy, xx = torch.meshgrid(torch.arange(2 * h), torch.arange(2 * w), indexing="ij")
    theta = 2 * np.pi * (3 * yy.double() / (2 * h) + 4 * xx.double() / (2 * w))
    a = torch.tensor([0.01 + 0.003j, 0.03 - 0.006j, 0.004 + 0.009j])
    truth = (a[:, None, None] * torch.exp(1j * theta)).real[None].to(dtype)
    colors = color_indices(pattern)
    field = mosaic(truth, colors)
    variance = torch.full_like(field, 1e-12)
    bins = torch.tensor([[[[3, 4]], [[3, 4]]]])
    valid = torch.tensor([[[True], [False]]])
    agreement, aux = cfa_cross_scale_support(
        field, variance, colors, bins, valid, windows=(17, 11, 7), strides=(8, 4, 3)
    )
    assert agreement.shape == (1, 2, 12, h, w) and agreement.dtype == dtype
    assert agreement[:, 1].count_nonzero() == 0
    assert (agreement[:, 0, [0, 1, 2, 6, 7, 8]] > 0.99995).all()
    assert agreement[:, 0, [3, 4, 5, 9, 10, 11]].abs().max() < 2e-6
    amplitude, bound, _ = cfa_scale_amplitudes(
        field, variance, colors, bins, valid, window=17, stride=8
    )
    _, wave, _ = cfa_innovation_wave_maps(field, variance, colors, bins, valid, window=17, stride=8)
    theta_packed = theta[::2, ::2]
    expected_wave = amplitude * torch.exp(1j * theta_packed)[None, None, None]
    torch.testing.assert_close(
        torch.complex(wave[:, :, :, 0].double(), wave[:, :, :, 1].double()),
        expected_wave,
        rtol=2e-6,
        atol=1e-9,
    )
    assert torch.isfinite(bound).all() and (bound >= 0).all()
    assert len(aux["scale_geometry"]) == 3


def interpolation_weights(axis, position):
    lower = np.searchsorted(axis, position, side="right") - 1
    lower = min(max(0, lower), len(axis) - 2)
    t = (position - axis[lower]) / (axis[lower + 1] - axis[lower])
    return [(lower, 1 - t), (lower + 1, t)]


def test_interpolated_trace_is_a_bound_not_an_independence_approximation():
    rng = np.random.default_rng(20004)
    field = torch.tensor(rng.normal(size=(1, 4, 24, 31)))
    variance = torch.tensor(rng.uniform(1e-7, 1e-5, field.shape))
    bins, valid = torch.tensor([[[[2, 3]], [[3, 4]]]]), torch.ones(1, 2, 1, dtype=torch.bool)
    _, bound, aux = cfa_scale_amplitudes(
        field, variance, color_indices("RGGB"), bins, valid, window=11, stride=7
    )
    ay, ax = aux["centers_y"].numpy(), aux["centers_x"].numpy()
    boxes = aux["boxes_xywh"].numpy()
    py, px = 19, 27
    for rgb_channel, phases, factor in [(0, [0], 1), (1, [1, 2], 0.25), (2, [3], 1)]:
        true_trace = center_bound = 0
        for p in phases:
            combined = np.zeros((2, 24, 31))
            weighted_root_trace = 0
            for iy, wy in interpolation_weights(ay, py):
                for ix, wx in interpolation_weights(ax, px):
                    box = boxes[iy * len(ax) + ix]
                    kernel, _ = direct_operator(24, 31, [2, 3], box)
                    x, y, w, h = box
                    combined[:, y : y + h, x : x + w] += (wx * wy) * kernel.reshape(2, h, w)
                    v = variance[0, p, y : y + h, x : x + w].numpy().ravel()
                    weighted_root_trace += wx * wy * np.sqrt(np.trace((kernel * v) @ kernel.T))
            true_trace += factor * np.sum(combined**2 * variance[0, p].numpy())
            center_bound += factor * weighted_root_trace**2
        actual_bound = float(bound[0, 0, rgb_channel, py, px])
        assert actual_bound >= true_trace * (1 - 1e-9)
        # For green, interpolating the sqrt of the summed center variances is
        # at least as conservative as summing the phasewise Jensen bounds.
        assert actual_bound >= center_bound * (1 - 1e-9)
        assert actual_bound > true_trace * 1.01


@pytest.mark.parametrize("dtype", [torch.complex64, torch.complex128])
def test_agreement_phase_sign_bounds_noise_attenuation_and_shared_phase_invariance(dtype):
    a = torch.tensor([0, 0.001 + 0.002j, 0.1 - 0.2j], dtype=dtype)
    noise = torch.full_like(a.real, 1e-8)
    positive = scale_agreement(a, a, noise, noise)
    negative = scale_agreement(a, -a, noise, noise)
    quadrature = scale_agreement(a, a * 1j, noise, noise)
    torch.testing.assert_close(negative, -positive)
    torch.testing.assert_close(quadrature, -positive * 1j)
    assert positive[0] == 0 and (positive.abs() <= 1).all()
    assert (scale_agreement(a, a, noise * 100, noise * 100).real <= positive.real).all()
    rotation = torch.tensor(np.exp(0.73j), dtype=dtype)
    torch.testing.assert_close(scale_agreement(a * rotation, a * rotation, noise, noise), positive)
    expected = 2 * a.abs().square() / (2 * a.abs().square() + 2 * noise + AMPLITUDE_FLOOR_SQUARED)
    torch.testing.assert_close(positive.real, expected)


@pytest.mark.parametrize(
    "damage", ["variance", "nan", "bins", "boxes", "window", "strides", "layout", "valid"]
)
def test_invalid_measurements_reject(damage):
    field = torch.zeros(1, 4, 12, 17, dtype=torch.float64)
    variance = torch.ones_like(field)
    bins, valid = torch.tensor([[[[2, 3]], [[3, 15]]]]), torch.ones(1, 2, 1, dtype=torch.bool)
    colors = color_indices("RGGB")
    options = {"windows": (9, 7, 3), "strides": (5, 4, 3)}
    if damage == "variance":
        variance[0, 0, 0, 0] = -1
    elif damage == "nan":
        field[0, 0, 0, 0] = float("nan")
    elif damage == "bins":
        bins = bins.float()
    elif damage == "boxes":
        with pytest.raises(ValueError):
            local_amplitude_grid(field, variance, bins[:, 0, 0], torch.tensor([[0, 0, 50, 2]]))
        return
    elif damage == "window":
        options["windows"] = (9, 3, 7)
    elif damage == "strides":
        options["strides"] = (5, 4, 0)
    elif damage == "layout":
        colors = torch.zeros(4, dtype=torch.int64)
    elif damage == "valid":
        valid = valid.float()
    with pytest.raises(ValueError):
        cfa_cross_scale_support(field, variance, colors, bins, valid, **options)
