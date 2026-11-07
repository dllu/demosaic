"""Independent complex adjoints and semantics of the new phase-bearing input."""

import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.late_harmonic_context import LateHarmonicContextDetail, dyadic_frequency_context
from demosaic.late_harmonic_phase import LateHarmonicPhaseDetail, harmonic_phase_features
from demosaic.late_spectral_relative import relative_spectrum_features
from demosaic.raw_frequency_features import frequency_descriptor


@pytest.mark.parametrize("size", [4, 8, 16])
def test_numpy_values_and_full_complex_input_noise_adjoints(size):
    rng = np.random.default_rng(16301 + size)
    data = [
        rng.normal(size=(2, 4, size, size)) + 1j * rng.normal(size=(2, 4, size, size))
        for _ in range(2)
    ]
    noise = rng.uniform(0.1, 1, (2, 4))
    upstream = rng.normal(size=(2, 16, size, size))
    expected, adjoints = [], []
    noise_adjoint = np.zeros_like(noise)
    for index, spectrum in enumerate(data):
        denominator = (
            np.sum(spectrum.real**2 + spectrum.imag**2, axis=1, keepdims=True)
            + noise.sum(1)[:, None, None, None]
        )
        unit = spectrum / np.sqrt(denominator)
        product = np.empty_like(unit)
        for y in range(size):
            for x in range(size):
                product[:, :, y, x] = unit[:, :, y, x] ** 2 * np.conj(
                    unit[:, :, 2 * y % size, 2 * x % size]
                )
        expected.extend([product.real, product.imag])
        q = upstream[:, index * 8 : index * 8 + 4] + 1j * upstream[:, index * 8 + 4 : index * 8 + 8]
        unit_adjoint = np.zeros_like(unit)
        for y in range(size):
            for x in range(size):
                dy, dx = 2 * y % size, 2 * x % size
                a, b = unit[:, :, y, x], unit[:, :, dy, dx]
                unit_adjoint[:, :, y, x] += 2 * np.conj(a) * b * q[:, :, y, x]
                unit_adjoint[:, :, dy, dx] += a**2 * np.conj(q[:, :, y, x])
        radial = np.real(np.sum(np.conj(unit_adjoint) * spectrum, axis=1, keepdims=True))
        adjoints.append(unit_adjoint / np.sqrt(denominator) - spectrum * radial / denominator**1.5)
        shared_noise = -0.5 * np.sum(radial / denominator**1.5, axis=(1, 2, 3))
        noise_adjoint += shared_noise[:, None]
    values = [torch.tensor(a, requires_grad=True) for a in data]
    proxy = torch.tensor(noise, requires_grad=True)
    result = harmonic_phase_features(*values, proxy)
    (result * torch.tensor(upstream)).sum().backward()
    np.testing.assert_allclose(
        result.detach().numpy(), np.concatenate(expected, 1), rtol=2e-14, atol=2e-14
    )
    for value, gradient in zip(values, adjoints, strict=True):
        np.testing.assert_allclose(value.grad.numpy(), gradient, rtol=3e-13, atol=3e-13)
    np.testing.assert_allclose(proxy.grad.numpy(), noise_adjoint, rtol=3e-13, atol=3e-13)


@pytest.mark.parametrize("dtype", [torch.complex64, torch.complex128])
def test_bounded_features_and_zero_noise_floor_are_finite(dtype):
    generator = torch.Generator().manual_seed(16302)
    observed = torch.complex(
        torch.randn(2, 4, 8, 8, generator=generator), torch.randn(2, 4, 8, 8, generator=generator)
    ).to(dtype)
    noise = torch.ones(2, 4, dtype=observed.real.dtype) * 0.1
    result = harmonic_phase_features(observed, observed * 0.7j, noise)
    assert result.shape == (2, 16, 8, 8) and torch.isfinite(result).all()
    for start in (0, 8):
        magnitude = torch.complex(
            result[:, start : start + 4], result[:, start + 4 : start + 8]
        ).abs()
        assert magnitude.max() <= 1 + 2e-6
    zero = torch.zeros_like(observed, requires_grad=True)
    result = harmonic_phase_features(zero, zero, torch.zeros_like(noise))
    result.sum().backward()
    assert result.count_nonzero() == zero.grad.count_nonzero() == 0
    assert torch.isfinite(zero.grad).all()


def spectra():
    generator = torch.Generator().manual_seed(16303)
    return [
        torch.fft.fft2(
            torch.randn(2, 4, 16, 16, generator=generator, dtype=torch.float64), norm="ortho"
        )
        for _ in range(2)
    ]


def test_exact_old_descriptor_collision_exposes_new_phase_information():
    observed, innovation = spectra()
    sign = torch.ones(16, 16, dtype=torch.float64)
    sign[2, 6] = sign[-2, -6] = -1
    changed = [v * sign for v in (observed, innovation)]
    noise = torch.ones(2, 4, dtype=torch.float64)
    colors = color_indices("RGGB")[None].expand(2, -1)

    def conditioning(a, b):
        first, second = (
            frequency_descriptor(a, noise, colors),
            frequency_descriptor(b, noise, colors),
        )
        relative = relative_spectrum_features(a, b, noise)
        return [
            torch.cat((first, second[:, :17]), 1),
            relative,
            dyadic_frequency_context(torch.cat((first[:, :17], second[:, :17], relative), 1)),
        ]

    assert all(
        torch.equal(a, b)
        for a, b in zip(conditioning(observed, innovation), conditioning(*changed), strict=True)
    )
    before = harmonic_phase_features(observed, innovation, noise)
    after = harmonic_phase_features(*changed, noise)
    assert not torch.equal(before, after)
    assert (before - after).abs().max() > 0.01
    assert all(torch.fft.ifft2(v, norm="ortho").imag.abs().max() < 1e-14 for v in changed)


@pytest.mark.parametrize("shift", [(1, 0), (0, 3), (5, -2)])
def test_integer_circular_shift_phase_ramps_cancel(shift):
    observed, innovation = spectra()
    shifted = [
        torch.fft.fft2(
            torch.roll(torch.fft.ifft2(v, norm="ortho").real, shift, (-2, -1)), norm="ortho"
        )
        for v in (observed, innovation)
    ]
    noise = torch.ones(2, 4, dtype=torch.float64)
    torch.testing.assert_close(
        harmonic_phase_features(observed, innovation, noise),
        harmonic_phase_features(*shifted, noise),
        rtol=2e-13,
        atol=2e-13,
    )


def test_products_have_real_image_conjugate_symmetry():
    values = harmonic_phase_features(*spectra(), torch.ones(2, 4, dtype=torch.float64))
    reverse = (-torch.arange(16)) % 16
    for start in (0, 8):
        product = torch.complex(values[:, start : start + 4], values[:, start + 4 : start + 8])
        torch.testing.assert_close(
            product,
            product.index_select(-2, reverse).index_select(-1, reverse).conj(),
            rtol=2e-14,
            atol=3e-16,
        )


def inputs():
    generator = torch.Generator().manual_seed(16304)
    base = torch.rand(4, 3, 22, 26, generator=generator) * 0.01
    packed = torch.rand(4, 4, 11, 13, generator=generator) * 0.01
    variance = torch.rand(packed.shape, generator=generator) * 1e-5 + 1e-7
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    wb = torch.rand(4, 3, generator=generator) + 0.7
    return base, packed, variance, colors, wb


@pytest.mark.parametrize("pattern", PATTERNS)
def test_zero_adapter_embeds_nonzero_head_and_common_parameter_gradients(pattern):
    rng = torch.get_rng_state().clone()
    baseline, candidate = LateHarmonicContextDetail(8), LateHarmonicPhaseDetail(8)
    assert torch.equal(rng, torch.get_rng_state())
    assert (
        sum(p.numel() for p in candidate.parameters()) == 124909
        and len(candidate.state_dict()) == 47
    )
    generator = torch.Generator().manual_seed(16305)
    with torch.no_grad():
        for name, p in baseline.named_parameters():
            p.copy_(torch.randn(p.shape, generator=generator) * 0.02)
            candidate.state_dict()[name].copy_(p)
    data = inputs()
    data = (*data[:3], color_indices(pattern), data[4])
    expected, actual = baseline(*data), candidate(*data)
    assert not torch.equal(expected, data[0])
    assert expected.detach().numpy().tobytes() == actual.detach().numpy().tobytes()
    target = data[0] * 0.97
    (((expected - target) / 0.002) ** 2).mean().backward()
    (((actual - target) / 0.002) ** 2).mean().backward()
    for name, p in baseline.named_parameters():
        assert torch.equal(p.grad, dict(candidate.named_parameters())[name].grad), name


@pytest.mark.parametrize("training", [False, True])
def test_active_phase_path_has_no_cross_batch_output_or_input_adjoint(training):
    module = LateHarmonicPhaseDetail(8).train(training)
    generator = torch.Generator().manual_seed(16306)
    with torch.no_grad():
        for p in module.parameters():
            p.copy_(torch.randn(p.shape, generator=generator) * 0.02)
    base, packed, variance, colors, wb = inputs()
    fields = [v.requires_grad_() for v in (base, packed, variance, wb)]
    result = module(base, packed, variance, colors, wb)
    grads = torch.autograd.grad(result[0].square().sum(), fields)
    assert all(torch.isfinite(g).all() and g[1:].count_nonzero() == 0 for g in grads)
    changed = [v.detach().clone() for v in fields]
    for value in changed:
        value[1:] = value[1:].flip(0) * 4.2 + 0.003
    with torch.no_grad():
        other = module(changed[0], changed[1], changed[2], colors, changed[3])
    assert result[0].detach().numpy().tobytes() == other[0].numpy().tobytes()


def test_all47_parameter_tensors_receive_finite_nonzero_prefix_gradients():
    module = LateHarmonicPhaseDetail(8)
    data = inputs()
    target = (
        data[0]
        + (torch.rand(data[0].shape, generator=torch.Generator().manual_seed(16307)) - 0.5) * 0.002
    )
    optimizer = torch.optim.AdamW(module.parameters(), lr=1e-3)
    maximum = {n: 0.0 for n, _ in module.named_parameters()}
    for _ in range(4):
        optimizer.zero_grad(set_to_none=True)
        ((module(*data) - target) / 0.002).square().mean().backward()
        for n, p in module.named_parameters():
            assert p.grad is not None and torch.isfinite(p.grad).all()
            maximum[n] = max(maximum[n], float(p.grad.abs().max()))
        optimizer.step()
    assert len(maximum) == 47 and min(maximum.values()) > 0


def test_active_phase_model_preserves_noiseless_constants_for_all_CFAs():
    module = LateHarmonicPhaseDetail(8)
    with torch.no_grad():
        for p in module.parameters():
            p.fill_(0.02)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    base = torch.tensor([0.01, 0.02, 0.013333])[None, :, None, None].expand(4, -1, 22, 26)
    packed = mosaic(base, colors)
    with torch.no_grad():
        actual = module(base, packed, torch.zeros_like(packed), colors)
    assert torch.equal(actual, base)


@pytest.mark.parametrize(
    "shape", [(1, 4, 3, 3), (1, 4, 6, 6), (1, 4, 4, 8), (0, 4, 8, 8), (1, 3, 8, 8)]
)
def test_invalid_frequency_geometry(shape):
    with pytest.raises(ValueError):
        harmonic_phase_features(
            torch.zeros(shape, dtype=torch.complex64),
            torch.zeros(shape, dtype=torch.complex64),
            torch.ones(shape[0], 4),
        )


def test_real_inputs_are_rejected():
    with pytest.raises(ValueError):
        harmonic_phase_features(torch.zeros(1, 4, 8, 8), torch.zeros(1, 4, 8, 8), torch.ones(1, 4))
