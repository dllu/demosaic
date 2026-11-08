import copy

import numpy as np
import pytest
import torch
from dense_spectrum_reference import measurements, native_readout

from demosaic.cfa import color_indices
from demosaic.late_dense_local_spectrum import (
    DenseLocalSpectrumReadout,
    LateDenseLocalSpectrumDetail,
    dense_local_spectrum,
)
from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail


def fixture(pattern="RGGB", dtype=torch.float64, batch=1):
    rng = np.random.default_rng(19101)
    raw = torch.tensor(rng.uniform(0.001, 0.04, (batch, 4, 8, 11)), dtype=dtype)
    var = torch.tensor(rng.uniform(1e-7, 4e-6, raw.shape), dtype=dtype)
    return raw, var, color_indices(pattern)


def nonzero_head(dtype=torch.float64):
    head = DenseLocalSpectrumReadout().to(dtype=dtype)
    with torch.no_grad():
        head.context.weight.copy_(
            torch.linspace(-0.09, 0.07, head.context.weight.numel(), dtype=dtype).reshape_as(
                head.context.weight
            )
        )
        head.mixing.weight.copy_(
            torch.linspace(-0.05, 0.07, head.mixing.weight.numel(), dtype=dtype).reshape_as(
                head.mixing.weight
            )
        )
        head.mixing.bias.copy_(torch.linspace(-0.02, 0.03, 12, dtype=dtype))
    return head


def numpy_state(head):
    return {n: v.detach().cpu().numpy() for n, v in head.state_dict().items()}


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_all_clipped_patch_measurements_and_native_outputs_match_QR_numpy(pattern, dtype):
    raw, var, colors = fixture(pattern, dtype, batch=2)
    context, coef, aux = dense_local_spectrum(
        raw, var, colors, window=9, stride=4, support_windows=(7, 5)
    )
    expected, ec, ea = measurements(
        raw.numpy(), var.numpy(), colors.numpy(), window=9, stride=4, support_windows=(7, 5)
    )
    tolerance = 4e-6 if dtype == torch.float32 else 3e-10
    np.testing.assert_allclose(context.numpy(), expected, rtol=tolerance, atol=tolerance)
    np.testing.assert_allclose(coef.numpy(), ec, rtol=tolerance, atol=tolerance * 0.01)
    np.testing.assert_allclose(
        aux["aligned_spectra"].numpy(), ea["aligned_spectra"], rtol=3e-9, atol=3e-13
    )
    np.testing.assert_allclose(
        aux["propagated_variance"].numpy(), ea["propagated_variance"], rtol=4e-10, atol=3e-18
    )
    np.testing.assert_array_equal(aux["centers_yx"].numpy(), ea["centers_yx"])
    head = nonzero_head(dtype)
    expected_output = native_readout(numpy_state(head), expected, ec, ea)
    actual = head(context, coef, aux)
    np.testing.assert_allclose(
        actual.detach().numpy(), expected_output, rtol=tolerance, atol=tolerance * 0.01
    )
    assert not context.requires_grad and not coef.requires_grad


def test_initial_state_parameter_budget_and_RNG_are_identical_to_V187():
    rng = torch.get_rng_state().clone()
    module, old = LateDenseLocalSpectrumDetail(), LatePooledPhaseWaveDetail()
    assert torch.equal(rng, torch.get_rng_state())
    assert len(module.state_dict()) == 193
    assert sum(p.numel() for p in module.parameters() if p.requires_grad) == 508
    assert all(torch.equal(v, old.state_dict()[n]) for n, v in module.state_dict().items())
    module.train()
    assert (
        not module.frozen.training
        and not module.network.training
        and not module.phase_evidence_in.training
        and module.wave_readout.training
    )
    assert all(
        n.startswith("wave_readout.") for n, p in module.named_parameters() if p.requires_grad
    )
    with pytest.raises(ValueError):
        module.initialize_from_evidence({})


def test_zero_initial_output_has_mixing_gradient_and_zero_spectra_cannot_add_bias():
    raw, var, colors = fixture()
    x, c, g = dense_local_spectrum(raw, var, colors, window=9, stride=4, support_windows=(7, 5))
    head = DenseLocalSpectrumReadout().double()
    value = head(x, c, g)
    assert value.count_nonzero() == 0
    (value * torch.linspace(-1, 1, value.numel()).reshape_as(value)).sum().backward()
    for name, p in head.named_parameters():
        assert p.grad is not None and torch.isfinite(p.grad).all()
        assert bool(p.grad.count_nonzero()) == name.startswith("mixing.")
    assert nonzero_head()(x, c * 0, g).count_nonzero() == 0


@pytest.mark.parametrize(
    "name,index",
    [("context.weight", 7), ("context.bias", 3), ("mixing.weight", 59), ("mixing.bias", 5)],
)
def test_parameter_gradients_match_independent_numpy_finite_differences(name, index):
    raw, var, colors = fixture()
    x, c, g = dense_local_spectrum(raw, var, colors, window=9, stride=4, support_windows=(7, 5))
    ex, ec, eg = measurements(
        raw.numpy(), var.numpy(), colors.numpy(), window=9, stride=4, support_windows=(7, 5)
    )
    head = nonzero_head()
    direction = torch.linspace(-0.3, 0.7, 3 * 16 * 22).reshape(1, 3, 16, 22).double()
    (head(x, c, g) * direction).sum().backward()
    p = dict(head.named_parameters())[name]
    actual = float(p.grad.flatten()[index])
    initial = float(p.detach().flatten()[index])
    values = []
    for delta in [-1e-5, 1e-5]:
        with torch.no_grad():
            p.flatten()[index] = initial + delta
        values.append(
            float((native_readout(numpy_state(head), ex, ec, eg) * direction.numpy()).sum())
        )
    assert actual == pytest.approx((values[1] - values[0]) / 2e-5, rel=4e-7, abs=2e-10)


def test_affine_fields_have_negligible_dense_residual_at_all_clipped_borders():
    y, x = torch.meshgrid(torch.arange(16).double(), torch.arange(19).double(), indexing="ij")
    raw = torch.stack([0.02 + 0.001 * x - 0.0003 * y + i * 0.003 for i in range(4)])[None]
    var = torch.full_like(raw, 2e-6)
    context, coef, aux = dense_local_spectrum(
        raw, var, [0, 1, 1, 2], window=17, stride=8, support_windows=(9, 5)
    )
    assert coef.abs().max() < 1e-14
    assert nonzero_head()(context, coef, aux).abs().max() < 1e-14
    assert torch.isfinite(context).all() and aux["normalization"].min() > 0


def test_noise_conditioning_rescaling_and_individual_supplied_variance():
    raw, var, colors = fixture()
    x, c, g = dense_local_spectrum(raw, var, colors, window=9, stride=4, support_windows=(7, 5))
    sx, sc, sg = dense_local_spectrum(
        raw * 2, var * 4, colors, window=9, stride=4, support_windows=(7, 5)
    )
    # Fixed one-DN variance floor deliberately breaks scale invariance where it
    # is active. Compare only genuinely normalized bins, including all scales.
    normalized = g["propagated_variance"].amin(3) > (1 / 65535) ** 2
    normalized = normalized[:, :, :, None].expand(-1, -1, -1, 6, -1, -1).reshape_as(x)
    assert normalized.any() and not normalized.all()
    torch.testing.assert_close(x[normalized], sx[normalized], rtol=2e-12, atol=2e-12)
    torch.testing.assert_close(c * 2, sc, rtol=2e-12, atol=2e-12)
    changed = var.clone()
    changed[0, 1, 0, 0] *= 10
    _, _, other = dense_local_spectrum(
        raw, changed, colors, window=9, stride=4, support_windows=(7, 5)
    )
    assert not torch.equal(other["propagated_variance"], g["propagated_variance"])


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_wrapper_exact_inheritance_local_ADC_routing_and_gradients(pattern):
    from test_late_phase_wave_readout import FrozenFixture, NetworkFixture
    from demosaic.late_local_phase_evidence_matching import LateLocalPhaseEvidenceMatchingDetail

    old = LateLocalPhaseEvidenceMatchingDetail(evidence_window=9, evidence_stride=8)
    new = LateDenseLocalSpectrumDetail(
        evidence_window=9,
        evidence_stride=8,
        dense_window=9,
        dense_stride=4,
        dense_support_windows=(7, 5),
    )
    new.initialize_from_evidence(old.state_dict())
    old.frozen, new.frozen = FrozenFixture(), FrozenFixture()
    old.network, new.network = NetworkFixture(), NetworkFixture()
    raw, var, colors = fixture(pattern, torch.float32)
    var[..., :4, :5] = 0
    base = torch.linspace(0.001, 0.02, 3 * 16 * 22).reshape(1, 3, 16, 22)
    with torch.no_grad():
        expected = old(base, raw, var, colors)
    initial, aux = new(base, raw, var, colors, return_aux=True)
    assert (
        torch.equal(initial.view(torch.int32), expected.view(torch.int32))
        and aux["dense_spectrum"] is not None
    )
    with torch.no_grad():
        new.wave_readout.mixing.bias.fill_(0.1)
    output, aux = new(base, raw, var, colors, return_aux=True)
    adc = (aux["sigma"] == 0).expand_as(output)
    assert torch.equal(output[adc], expected[adc]) and not torch.equal(output[~adc], expected[~adc])
    output.square().mean().backward()
    assert all(p.grad is None for p in new.phase_evidence_in.parameters())
    assert any(p.grad is not None and p.grad.count_nonzero() for p in new.wave_readout.parameters())
    result, aux = new(base, raw, var * 0, colors, return_aux=True)
    assert (
        torch.equal(result, new.frozen(base))
        and aux["dense_spectrum"] is aux["dense_context"] is aux["dense_coefficient"] is None
    )


@pytest.mark.parametrize(
    "change", ["negative_variance", "nan", "layout", "dtype", "window", "stride", "support"]
)
def test_invalid_measurements_reject(change):
    raw, var, colors = fixture()
    kw = dict(window=9, stride=4, support_windows=(7, 5))
    if change == "negative_variance":
        var[0, 0, 0, 0] = -1
    if change == "nan":
        raw[0, 0, 0, 0] = float("nan")
    if change == "layout":
        colors = [0, 0, 0, 0]
    if change == "dtype":
        var = var.float()
    if change == "window":
        kw["window"] = 8
    if change == "stride":
        kw["stride"] = 8
    if change == "support":
        kw["support_windows"] = (7, 7)
    with pytest.raises(ValueError):
        dense_local_spectrum(raw, var, colors, **kw)


@pytest.mark.parametrize("bin_yx", [(1, 2), (-3, -4), (0, 3)])
def test_exact_native_carrier_phase_at_every_subpixel(bin_yx):
    length = 9
    raw = torch.zeros((1, 4, length, length), dtype=torch.float64)
    _, _, aux = dense_local_spectrum(
        raw, raw + 1e-6, [0, 1, 1, 2], window=9, stride=4, support_windows=(7, 5)
    )
    yy, xx = torch.meshgrid(torch.arange(length), torch.arange(length), indexing="ij")
    aux["linear_indices"] = ((yy + 4) * 17 + xx + 4)[None]
    aux["normalization"] = torch.ones((length, length), dtype=torch.float64)
    aux["synthesis_window"] = torch.ones((length, length), dtype=torch.float64)
    context = torch.zeros((1, 18, length, length), dtype=torch.float64)
    coefficient = torch.zeros((1, 1, 2, length, length), dtype=torch.complex128)
    y, x = bin_yx
    value = (length / 2) * np.exp(0.31j)
    coefficient[0, 0, 0, y % length, x % length] = complex(value)
    coefficient[0, 0, 0, (-y) % length, (-x) % length] = complex(value.conjugate())
    head = DenseLocalSpectrumReadout().double()
    with torch.no_grad():
        head.mixing.bias.reshape(3, 4)[:, 0] = 1
    actual = head(context, coefficient, aux).detach().numpy()
    ny, nx = np.indices((2 * length, 2 * length))
    expected = np.cos(2 * np.pi * (y * ny / (2 * length) + x * nx / (2 * length)) + 0.31)
    np.testing.assert_allclose(actual, np.broadcast_to(expected, actual.shape), atol=4e-15)


def test_propagated_variance_matches_explicit_noisy_sample_operator_at_clipped_corner():
    raw, var, colors = fixture()
    _, _, aux = dense_local_spectrum(raw, var, colors, window=9, stride=4, support_windows=(7, 5))
    yy, xx = np.indices((9, 9))
    valid = (yy >= 4) & (xx >= 4)
    design = np.stack([np.ones_like(xx), xx, yy], -1).reshape(-1, 3)
    fft_row = np.exp(-2j * np.pi * (2 * yy + 3 * xx) / 9).ravel() / 9
    for scale_index, scale in enumerate([9, 7, 5]):
        hann = np.pad(np.hanning(scale), (9 - scale) // 2)
        weight = (hann[:, None] * hann[None, :] * valid).ravel()
        q = np.linalg.qr(weight[:, None] * design, mode="reduced")[0]
        row = (fft_row - (fft_row @ q) @ q.T) * weight
        for phase, g in enumerate(np.flatnonzero(colors.numpy() == 1)):
            v = np.zeros((9, 9))
            v[4:, 4:] = var[0, g, :5, :5].numpy()
            expected = float((abs(row) ** 2 * v.ravel()).sum())
            assert float(
                aux["propagated_variance"][0, 0, scale_index, phase, 2, 3]
            ) == pytest.approx(expected, rel=2e-12, abs=1e-20)
