"""Physical moments,Poisson marginals,ADC and RNG for counterfactual pairs."""

import math

import numpy as np
import pytest
import torch
from coupled_sensor_noise import coupled_sensor_noise


@pytest.mark.parametrize("shot,read", [(0.00128, 6.5536e-6), (0.00256, 2.62144e-5), (0, 6.5536e-6)])
def test_physical_pre_ADC_means_variances_covariance_and_difference(shot, read):
    n = 262144
    a, b = 0.02, 0.024
    _, (x, y) = coupled_sensor_noise(
        torch.full((n,), a),
        torch.full((n,), b),
        shot,
        read,
        generator=torch.Generator().manual_seed(16001),
        return_pre_ADC=True,
    )
    x, y = x.double().numpy(), y.double().numpy()
    expected_variance = [shot * a + read, shot * b + read]
    for z, mean, variance in zip([x, y], [a, b], expected_variance, strict=True):
        assert abs(z.mean() - mean) < 8 * math.sqrt(variance / n) + 1e-8
        assert abs(z.var() / variance - 1) < 0.025
    covariance = np.mean((x - x.mean()) * (y - y.mean()))
    assert abs(covariance / (shot * min(a, b) + read) - 1) < 0.025
    if shot:
        assert abs((y - x).var() / (shot * abs(b - a)) - 1) < 0.025
    else:
        np.testing.assert_allclose(y - x, b - a, rtol=0, atol=4e-9)


def test_entire_low_count_Poisson_marginals_against_analytic_PMF():
    n = 262144
    shot = 0.01
    _, pre = coupled_sensor_noise(
        torch.full((n,), shot),
        torch.full((n,), 4 * shot),
        shot,
        0,
        generator=torch.Generator().manual_seed(16002),
        return_pre_ADC=True,
    )
    for z, rate in zip(pre, [1, 4], strict=True):
        counts = np.rint(z.numpy() / shot).astype(np.int64)
        histogram = np.bincount(counts, minlength=20) / n
        for k in range(12):
            probability = math.exp(-rate) * rate**k / math.factorial(k)
            assert (
                abs(histogram[k] - probability)
                < 8 * math.sqrt(probability * (1 - probability) / n) + 8 / n
            )


@pytest.mark.parametrize("shot,read", [(0.00128, 6.5536e-6), (0, 0), (0, 6.5536e-6)])
def test_identical_clean_pixels_share_exact_noisy_values_in_mask(shot, read):
    a = torch.full((2, 1, 32, 40), 0.02)
    b = a.clone()
    b[..., 8:24, 10:30] += 0.001
    x, y = coupled_sensor_noise(a, b, shot, read, generator=torch.Generator().manual_seed(16003))
    mask = a == b
    assert torch.equal(x[mask], y[mask])
    assert not torch.equal(x[~mask], y[~mask])


def test_ADC_and_overexposure_count_before_clip_match_explicit_calibration():
    a = torch.tensor([[-0.02, 0, 0.123, 0.9, 1.2]], dtype=torch.float32)
    b = a + 0.01
    pair, pre = coupled_sensor_noise(
        a,
        b,
        0.2,
        0.001,
        bit_depth=12,
        black_level=0.1,
        generator=torch.Generator().manual_seed(16004),
        return_pre_ADC=True,
    )
    for actual, raw in zip(pair, pre, strict=True):
        expected = (
            ((raw.double().numpy() * 0.9 + 0.1).clip(0, 1) * 4095).round() / 4095 - 0.1
        ) / 0.9
        np.testing.assert_allclose(actual, expected, rtol=1e-6, atol=1e-7)
    # Deterministic ADC-only overexposure exercises the same physical clipping order.
    x, y = coupled_sensor_noise(a, b, 0, 0, bit_depth=12, black_level=0.1)
    assert x[0, -1] == y[0, -1] == 1


def test_broadcast_coefficients_and_local_generator_reproducibility():
    a = torch.full((2, 1, 4, 5), 0.01)
    shot = torch.tensor([0, 0.00128]).reshape(2, 1, 1, 1)
    global_before = torch.get_rng_state().clone()
    first = coupled_sensor_noise(
        a, a * 1.1, shot, 6.5536e-6, generator=torch.Generator().manual_seed(16005)
    )
    second = coupled_sensor_noise(
        a, a * 1.1, shot, 6.5536e-6, generator=torch.Generator().manual_seed(16005)
    )
    assert all(torch.equal(x, y) for x, y in zip(first, second, strict=True))
    assert torch.equal(global_before, torch.get_rng_state())


@pytest.mark.parametrize("bad", ["shape", "dtype", "nan", "shot", "read", "black", "bits"])
def test_invalid_inputs_reject_before_any_random_draw(bad):
    a = torch.full((1, 1, 4, 5), 0.01)
    b = a.clone()
    args = {"shot": 0.00128, "read": 6.5536e-6}
    if bad == "shape":
        b = b[..., :3]
    if bad == "dtype":
        b = b.double()
    if bad == "nan":
        b[..., 0, 0] = float("nan")
    if bad == "shot":
        args["shot"] = -0.1
    if bad == "read":
        args["read"] = float("inf")
    if bad == "black":
        args["black_level"] = 1
    if bad == "bits":
        args["bit_depth"] = 17
    generator = torch.Generator().manual_seed(16006)
    before = generator.get_state().clone()
    with pytest.raises(ValueError):
        coupled_sensor_noise(a, b, generator=generator, **args)
    assert torch.equal(before, generator.get_state())
