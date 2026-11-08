"""Independent real least-squares, Bayer transport and structural color checks."""

import math

import numpy as np
import pytest
import torch

from demosaic.cfa import color_indices, mosaic
from demosaic.late_cfa_innovation_wave import (
    CFAInnovationWaveReadout,
    LateCFAInnovationWaveDetail,
    cfa_innovation_wave_maps,
)
from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail, fixed_bin_wave_maps


def inputs(pattern="RGGB", dtype=torch.float64):
    rng = np.random.default_rng(19801)
    field = torch.tensor(rng.normal(0, 0.003, (1, 4, 12, 17)), dtype=dtype)
    variance = torch.tensor(rng.uniform(1e-7, 1e-5, field.shape), dtype=dtype)
    bins = torch.tensor([[[[2, 3]], [[3, 15]]]])
    return field, variance, color_indices(pattern), bins, torch.ones((1, 2, 1), dtype=torch.bool)


def numpy_waves(field, colors, bins, window, stride):
    """Direct per-box 5-column NumPy least squares and separate interpolation."""
    _, _, height, width = field.shape
    axes = [np.unique(np.r_[np.arange(0, n, stride), n - 1]) for n in (height, width)]
    yy, xx = np.mgrid[:height, :width]
    order = [int(np.where(colors == c)[0][j]) for c, j in [(0, 0), (1, 0), (1, 1), (2, 0)]]
    all_waves = []
    for by, bx in bins.reshape(-1, 2):
        ky, kx = (
            by if by < (height + 1) // 2 else by - height,
            bx if bx < (width + 1) // 2 else bx - width,
        )
        angle = 2 * np.pi * (ky * yy / height + kx * xx / width)
        phase_amplitudes = []
        for phase in order:
            samples = []
            for cy in axes[0]:
                row = []
                for cx in axes[1]:
                    ys = slice(max(0, cy - window // 2), min(height, cy + window // 2 + 1))
                    xs = slice(max(0, cx - window // 2), min(width, cx + window // 2 + 1))
                    x, y, t = xx[ys, xs], yy[ys, xs], angle[ys, xs]
                    design = np.stack(
                        (np.ones_like(x), x - x.mean(), y - y.mean(), np.cos(t), np.sin(t)), -1
                    ).reshape(-1, 5)
                    solution = np.linalg.lstsq(
                        design, field[0, phase, ys, xs].ravel(), rcond=1e-12
                    )[0]
                    row.append(solution[3] - 1j * solution[4])
                samples.append(row)
            grid = np.asarray(samples)
            horizontal = np.stack([np.interp(np.arange(width), axes[1], row) for row in grid])
            amplitude = np.stack(
                [np.interp(np.arange(height), axes[0], col) for col in horizontal.T], -1
            )
            offset = np.pi * (ky * (phase // 2) / height + kx * (phase % 2) / width)
            phase_amplitudes.append(amplitude * np.exp(-1j * offset))
        r, ga, gb, b = phase_amplitudes
        all_waves.append(np.stack((r, (ga + gb) / 2, b)) * np.exp(1j * angle))
    return np.stack(all_waves)[None]


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_all_pixels_against_independent_real_LS_and_green_context(pattern, dtype):
    field, variance, colors, bins, valid = inputs(pattern, dtype)
    context, wave, aux = cfa_innovation_wave_maps(
        field, variance, colors, bins, valid, window=9, stride=5
    )
    expected = numpy_waves(field.numpy(), colors.numpy(), bins.numpy(), 9, 5)
    tolerance = 2e-6 if dtype == torch.float32 else 5e-9
    np.testing.assert_allclose(wave[:, :, :, 0].numpy(), expected.real, rtol=tolerance, atol=2e-10)
    np.testing.assert_allclose(wave[:, :, :, 1].numpy(), expected.imag, rtol=tolerance, atol=2e-10)
    old, _ = fixed_bin_wave_maps(field, variance, colors, bins, valid, window=9, stride=5)
    old = old.reshape(1, 2, 10, 12, 17)
    torch.testing.assert_close(context[:, :, :6], old[:, :, 4:], rtol=2e-6, atol=2e-8)
    assert (aux["wave_gram_rank"] == 2).all()


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_physical_wave_amplitude_and_native_subpixel_phase(pattern, dtype):
    field, variance, colors, bins, valid = inputs(pattern, dtype)
    height, width = field.shape[-2:]
    yy, xx = np.mgrid[: height * 2, : width * 2]
    angle = 2 * np.pi * (2 * yy / (height * 2) + 3 * xx / (width * 2))
    cosine, sine = np.array([0.002, -0.001, 0.0007]), np.array([0.0003, 0.002, -0.001])
    truth = torch.tensor(
        cosine[:, None, None] * np.cos(angle) + sine[:, None, None] * np.sin(angle), dtype=dtype
    )[None]
    yy, xx = torch.meshgrid(torch.arange(height), torch.arange(width), indexing="ij")
    field = mosaic(truth, colors) + (0.02 + 0.0001 * yy - 0.0002 * xx)[None, None].to(dtype)
    bins[:, 1] = bins[:, 0]
    valid[:, 1] = False
    _, waves, _ = cfa_innovation_wave_maps(field, variance, colors, bins, valid, window=9, stride=5)
    readout = CFAInnovationWaveReadout().to(dtype)
    with torch.no_grad():
        readout.gates.bias.fill_(math.atanh(0.5))
    actual = readout(torch.zeros(1, 2, 24, height, width, dtype=dtype), waves, bins)
    torch.testing.assert_close(actual, truth * 0.5, rtol=2e-5, atol=2e-9)
    assert waves[:, 1].count_nonzero() == 0


def test_zero_red_blue_cannot_be_created_from_green_and_gates_are_bounded():
    field, variance, colors, bins, valid = inputs()
    field[:, [0, 3]] = 0
    _, waves, _ = cfa_innovation_wave_maps(field, variance, colors, bins, valid, window=9, stride=5)
    readout = CFAInnovationWaveReadout().double()
    with torch.no_grad():
        readout.gates.weight.fill_(10)
        readout.gates.bias.fill_(20)
    output = readout(torch.randn(1, 2, 24, 12, 17, dtype=field.dtype), waves, bins)
    assert output[:, [0, 2]].count_nonzero() == 0 and output[:, 1].count_nonzero() > 0
    bound = waves.square().sum(3).sqrt().sum(1).repeat_interleave(2, -2).repeat_interleave(2, -1)
    assert bool((abs(output) <= bound + 1e-14).all())


def test_mixed_layout_batch_affine_annihilation_and_singular_nyquist():
    field, variance, colors, bins, valid = inputs()
    layouts = torch.stack([color_indices(p) for p in ["RGGB", "BGGR", "GRBG", "GBRG"]])
    yy, xx = torch.meshgrid(torch.arange(12), torch.arange(17), indexing="ij")
    field = (0.02 + 0.0001 * yy.double() - 0.0002 * xx.double())[None, None].expand(4, 4, -1, -1)
    mixed, waves, _ = cfa_innovation_wave_maps(
        field,
        variance.expand_as(field),
        layouts,
        bins.expand(4, -1, -1, -1),
        valid.expand(4, -1, -1),
        window=9,
        stride=5,
    )
    assert abs(waves).max() < 1e-12
    assert abs(mixed).max() < 1e-10
    # An explicit Nyquist bin has only one measurable real quadrature.
    field, variance = (
        torch.randn(1, 4, 12, 16, dtype=torch.float64),
        torch.ones(1, 4, 12, 16, dtype=torch.float64),
    )
    bins = torch.tensor([[[[0, 8]], [[0, 8]]]])
    _, waves, aux = cfa_innovation_wave_maps(
        field, variance, colors, bins, valid, window=9, stride=5
    )
    assert torch.isfinite(waves).all() and (aux["wave_gram_rank"] == 1).all()


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_anchor_embedding_isolated_learning_and_ADC(pattern):
    from test_late_phase_wave_readout import FrozenFixture, NetworkFixture

    config = {
        "evidence_window": 9,
        "evidence_stride": 8,
        "support_windows": (7, 3),
        "support_stride": 4,
    }
    old = LatePooledPhaseWaveDetail(**config)
    with torch.no_grad():
        old.wave_readout.mixing.bias.fill_(0.13)
    new = LateCFAInnovationWaveDetail(**config).initialize_anchor(old.state_dict())
    assert len(new.state_dict()) == 197
    assert sum(p.numel() for p in new.parameters() if p.requires_grad) == 451
    old.frozen, new.frozen = FrozenFixture(), FrozenFixture()
    old.network, new.network = NetworkFixture(), NetworkFixture()
    field, variance, colors, _, _ = inputs(pattern, torch.float32)
    variance[..., :4, :5] = 0
    base = torch.randn(1, 3, 24, 34) * 0.003
    expected = old.eval()(base, field, variance, colors)
    actual, aux = new.train()(base, field, variance, colors, return_aux=True)
    assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))
    assert torch.equal(aux["measurement_field"], field - mosaic(expected, colors))
    assert not new.wave_readout.training and new.cfa_readout.training and not new.frozen.training
    optimizer = torch.optim.AdamW(new.cfa_readout.parameters(), lr=0.01)
    for _ in range(2):
        optimizer.zero_grad(set_to_none=True)
        actual = new(base, field, variance, colors)
        (actual - base - 0.001).square().mean().backward()
        assert all(
            p.grad is None for n, p in new.named_parameters() if not n.startswith("cfa_readout.")
        )
        optimizer.step()
    assert all(p.grad is not None and p.grad.count_nonzero() for p in new.cfa_readout.parameters())
    trained = new(base, field, variance, colors)
    mask = (aux["sigma"] == 0).expand_as(trained)
    assert torch.equal(trained[mask], expected[mask]) and not torch.equal(
        trained[~mask], expected[~mask]
    )
    adc, aux = new(base, field, variance * 0, colors, return_aux=True)
    assert torch.equal(adc, old(base, field, variance * 0, colors))
    assert aux["cfa_waves"] is aux["cfa_context"] is aux["wave_selection"] is None


def test_RNG_strict_state_and_rejections():
    before = torch.get_rng_state().clone()
    module = LateCFAInnovationWaveDetail()
    assert torch.equal(before, torch.get_rng_state())
    clone = LateCFAInnovationWaveDetail()
    clone.load_state_dict(module.state_dict(), strict=True)
    with pytest.raises(ValueError):
        module.initialize_anchor({})
    for lower in [0, 0.5, float("nan")]:
        with pytest.raises(ValueError):
            LateCFAInnovationWaveDetail(lower=lower)
    context, waves, bins = (
        torch.zeros(1, 2, 24, 12, 17),
        torch.zeros(1, 2, 3, 2, 12, 17),
        inputs()[3],
    )
    with pytest.raises(ValueError):
        module.cfa_readout(context[:, :, :23], waves, bins)
    with pytest.raises(ValueError):
        module.cfa_readout(context, waves[..., :16], bins)
    with pytest.raises(ValueError):
        module.cfa_readout(context, waves, bins.float())
    context[0, 0, 0, 0, 0] = float("nan")
    with pytest.raises(ValueError):
        module.cfa_readout(context, waves, bins)
