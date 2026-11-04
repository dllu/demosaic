"""Independent cross-spectrum arithmetic, descriptor ambiguity and native embedding."""

import numpy as np
import pytest
import torch
from test_late_spectral_matrix import descriptor_numpy, measurements

from demosaic.late_spectral_matrix import LateSpectralMatrixDetail
from demosaic.late_spectral_relative import LateSpectralRelativeDetail, relative_spectrum_features
from demosaic.raw_frequency_features import frequency_descriptor


def numpy_relative(first, second, noise):
    a, b = first.astype(np.complex128), second.astype(np.complex128)
    n = np.maximum(noise, 0).sum(1)[:, None, None, None]
    energy_a = np.maximum(np.sum(a.real**2 + a.imag**2, axis=1, keepdims=True) + n, 1e-12)
    energy_b = np.maximum(np.sum(b.real**2 + b.imag**2, axis=1, keepdims=True) + n, 1e-12)
    cross = np.einsum("nchw,nchw->nchw", a, b.conj())
    return np.concatenate((cross.real, cross.imag), 1) / np.sqrt(energy_a * energy_b)


@pytest.mark.parametrize("noise_level", [0, 1e-6])
def test_relative_values_and_complex_gradients_match_numpy_finite_differences(noise_level):
    rng = np.random.default_rng(15201)
    first = (rng.normal(size=(1, 4, 3, 3)) + 1j * rng.normal(size=(1, 4, 3, 3))) * 0.002
    second = (rng.normal(size=first.shape) + 1j * rng.normal(size=first.shape)) * 0.001
    noise = np.full((1, 4), noise_level)
    weights = rng.normal(size=(1, 8, 3, 3))
    a, b = torch.tensor(first, requires_grad=True), torch.tensor(second, requires_grad=True)
    actual = relative_spectrum_features(a, b, torch.tensor(noise))
    np.testing.assert_allclose(
        actual.detach().numpy(), numpy_relative(first, second, noise), atol=2e-16
    )
    assert actual.abs().max() <= 1
    (actual * torch.tensor(weights)).sum().backward()
    epsilon = 1e-8
    for which, values, grad in [(0, first, a.grad.numpy()), (1, second, b.grad.numpy())]:
        for index in [(0, 0, 0, 1), (0, 2, 1, 2), (0, 3, 2, 0)]:
            expected = []
            for direction in [1, 1j]:
                plus, minus = values.copy(), values.copy()
                plus[index] += epsilon * direction
                minus[index] -= epsilon * direction
                pair_plus = (plus, second) if which == 0 else (first, plus)
                pair_minus = (minus, second) if which == 0 else (first, minus)
                derivative = (
                    (numpy_relative(*pair_plus, noise) - numpy_relative(*pair_minus, noise))
                    * weights
                ).sum() / (2 * epsilon)
                expected.append(derivative)
            np.testing.assert_allclose(
                [grad[index].real, grad[index].imag], expected, rtol=2e-7, atol=2e-6
            )


def test_marginal_descriptors_alias_opposite_innovation_but_relative_features_distinguish_it():
    generator = torch.Generator().manual_seed(15202)
    observed = torch.fft.fft2(torch.randn(1, 4, 8, 8, generator=generator), norm="ortho")
    innovation = torch.fft.fft2(torch.randn(1, 4, 8, 8, generator=generator), norm="ortho")
    noise = torch.full((1, 4), 0.2)
    colors = torch.tensor([[0, 1, 1, 2]])
    assert torch.equal(
        frequency_descriptor(innovation, noise, colors),
        frequency_descriptor(-innovation, noise, colors),
    )
    original = relative_spectrum_features(observed, innovation, noise)
    opposite = relative_spectrum_features(observed, -innovation, noise)
    assert torch.equal(original, -opposite) and original.abs().max() > 0.1
    assert torch.equal(original, relative_spectrum_features(-observed, -innovation, noise))
    phase = torch.polar(
        torch.ones_like(observed.real), torch.rand(observed.shape, generator=generator)
    )
    torch.testing.assert_close(
        relative_spectrum_features(observed * phase, innovation * phase, noise),
        original,
        atol=2e-7,
        rtol=2e-6,
    )


def test_constructor_rng_meta_and_common_parameters(monkeypatch):
    before = torch.get_rng_state().clone()

    def forbidden(*args, **kwargs):
        raise AssertionError("Constructor seeded CUDA")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    with torch.device("meta"):
        control, relative = LateSpectralMatrixDetail(8), LateSpectralRelativeDetail(8)
    assert torch.equal(before, torch.get_rng_state())
    assert (
        len(relative.state_dict()) == 13 and sum(p.numel() for p in relative.parameters()) == 33713
    )
    assert all(
        torch.equal(value, relative.state_dict()[name])
        for name, value in control.state_dict().items()
    )
    assert relative.relative_in.weight.count_nonzero() == 0
    assert all(v.device.type == "cpu" for v in [*relative.parameters(), *relative.buffers()])


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_any_trained_native_head_embeds_exactly_and_learned_constants_remain_exact(pattern):
    control, relative = LateSpectralMatrixDetail(8), LateSpectralRelativeDetail(8)
    generator = torch.Generator().manual_seed(15203)
    with torch.no_grad():
        for parameter in control.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.2)
    missing, unexpected = relative.load_state_dict(control.state_dict(), strict=False)
    assert missing == ["relative_in.weight"] and not unexpected
    base, raw, variance, colors = measurements(pattern)
    assert torch.equal(control(base, raw, variance, colors), relative(base, raw, variance, colors))
    with torch.no_grad():
        relative.relative_in.weight.copy_(
            torch.randn(relative.relative_in.weight.shape, generator=generator) * 0.2
        )
    constants = torch.tensor([0.002, 0.007, 0.03])[colors][:, :, None, None].expand_as(raw)
    for noise in [variance, torch.zeros_like(variance)]:
        assert torch.equal(relative(base, constants, noise, colors), base)


def circular_convolution(values, weights, bias=None):
    result = np.zeros((values.shape[0], weights.shape[0], *values.shape[-2:]))
    if bias is not None:
        result += bias[None, :, None, None]
    for y in range(3):
        for x in range(3):
            result += np.einsum(
                "oc,nchw->nohw", weights[:, :, y, x], np.roll(values, (1 - y, 1 - x), (-2, -1))
            )
    return result


def test_full_learned_relative_matrix_matches_independent_numpy():
    rng = np.random.default_rng(15204)
    module = LateSpectralRelativeDetail(8)
    with torch.no_grad():
        for parameter in module.parameters():
            parameter.copy_(
                torch.from_numpy(rng.normal(size=parameter.shape).astype("float32") * 0.1)
            )
    observed = np.fft.fft2(rng.normal(size=(2, 4, 8, 8)), norm="ortho")
    innovation = observed - np.fft.fft2(rng.normal(size=observed.shape) * 0.5, norm="ortho")
    noise = rng.uniform(0.1, 0.3, size=(2, 4))
    colors = np.array([[0, 1, 1, 2], [1, 2, 0, 1]])
    descriptor = descriptor_numpy(observed, noise, colors)
    marginal = np.concatenate((descriptor, descriptor_numpy(innovation, noise, colors)[:, :17]), 1)
    state = {k: v.detach().numpy().astype(np.float64) for k, v in module.state_dict().items()}
    hidden = circular_convolution(
        marginal, state["frequency_in.weight"], state["frequency_in.bias"]
    )
    hidden += circular_convolution(
        numpy_relative(observed, innovation, noise), state["relative_in.weight"]
    )
    hidden /= 1 + np.exp(-hidden)
    values = np.einsum("oc,nchw->nohw", state["frequency_out.weight"][:, :, 0, 0], hidden).reshape(
        2, 4, 4, 2, 8, 8
    )
    real = np.tanh(values[:, :, :, 0] + state["frequency_real_bias"][None, :, :, None, None])
    matrix = real + 1j * np.tanh(values[:, :, :, 1])
    reverse = (-np.arange(8)) % 8
    matrix = (matrix + matrix[..., reverse, :][..., :, reverse].conj()) / 2
    bound = np.sqrt(abs(matrix).sum(1).max(1) * abs(matrix).sum(2).max(1))
    matrix /= np.maximum(1, bound)[:, None, None]
    expected = matrix * descriptor[:, :4].sum(1)[:, None, None] * module.band_8.numpy()
    actual = module.frequency_gain(
        torch.tensor(observed, dtype=torch.complex64),
        torch.tensor(innovation, dtype=torch.complex64),
        torch.tensor(noise, dtype=torch.float32),
        torch.tensor(colors),
    )
    np.testing.assert_allclose(actual.detach().numpy(), expected, atol=4e-7, rtol=3e-5)
    actual.abs().square().sum().backward()
    assert (
        torch.isfinite(module.relative_in.weight.grad).all()
        and module.relative_in.weight.grad.abs().max() > 0
    )


def test_zero_spectra_and_noise_have_finite_values_and_gradients():
    first = torch.zeros(1, 4, 4, 4, dtype=torch.complex64, requires_grad=True)
    second = first.detach().clone().requires_grad_()
    result = relative_spectrum_features(first, second, torch.zeros(1, 4))
    assert result.count_nonzero() == 0
    result.sum().backward()
    assert torch.isfinite(first.grad).all() and torch.isfinite(second.grad).all()
