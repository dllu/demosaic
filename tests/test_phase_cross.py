"""Independent mask operators, convex optima and physical phase isolation."""

import numpy as np
import pytest
import torch

from demosaic.phase_cross import (
    _solver,
    cross_phase_masks,
    fit_masks,
    interpolation_weights,
    reciprocal_templates,
)


@pytest.fixture(autouse=True)
def single_thread():
    previous = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(previous)


def test_interpolation_uses_centered_clamped_knots_without_repeated_measurements():
    expected = np.array(
        [
            [1, 0],
            [1, 0],
            [0.875, 0.125],
            [0.625, 0.375],
            [0.375, 0.625],
            [0.125, 0.875],
            [0, 1],
            [0, 1],
        ]
    )
    np.testing.assert_array_equal(interpolation_weights(8, 2), expected)
    np.testing.assert_allclose(interpolation_weights(16, 3).sum(1), 1, atol=1e-16)


def dense_problem(waves):
    rng = np.random.default_rng(734 + waves)
    fine, coarse = 16, 3
    weight, area = 0.13, 0.001
    w = interpolation_weights(fine, coarse)
    interpolation = np.kron(w, w)
    y, x = np.mgrid[:fine, :fine]
    templates = rng.normal(size=(waves, fine, fine)) * ((y + x) % 2 == 1)
    data = np.concatenate([t.ravel()[:, None] * interpolation for t in templates], axis=1)
    size = waves * coarse * coarse
    gradient = np.zeros((2 * size, size))
    for k in range(waves):
        for y in range(coarse):
            for x in range(coarse):
                i = k * coarse * coarse + y * coarse + x
                if y + 1 < coarse:
                    gradient[i, i], gradient[i, i + coarse] = -1, 1
                if x + 1 < coarse:
                    gradient[size + i, i], gradient[size + i, i + 1] = -1, 1
    known = rng.uniform(0.3, 0.7, size=(waves, coarse, coarse))
    g = (gradient @ known.ravel()).reshape(2, waves, coarse, coarse)
    dual = g / np.maximum(np.sqrt(np.sum(g * g, 0)), 1e-30)[None]
    areas = np.broadcast_to(
        area * (interpolation.T @ np.ones(fine * fine)).reshape(coarse, coarse), known.shape
    )
    wanted = -weight * (gradient.T @ dual.ravel()) - areas.ravel()
    q = np.linalg.lstsq(data.T, wanted, rcond=None)[0]
    np.testing.assert_allclose(data.T @ q, wanted, rtol=0, atol=2e-14)
    target = (data @ known.ravel() - q).reshape(fine, fine)
    return templates, target, known, data, gradient, interpolation, areas, weight, area


@pytest.mark.parametrize("waves", [1, 2])
def test_dense_forward_adjoint_and_diagonal_steps_have_correct_norm(waves):
    t, _, known, a, d, p, _, weight, _ = dense_problem(waves)
    solver = _solver(t.shape, 3, "cpu")
    solver.t.copy_(torch.from_numpy(t))
    q = np.random.default_rng(80).normal(size=(16, 16))
    np.testing.assert_allclose(
        solver.transpose(torch.from_numpy(q)).numpy().ravel(), a.T @ q.ravel(), rtol=0, atol=4e-15
    )
    np.testing.assert_allclose(
        solver.expand(torch.from_numpy(known)).numpy().reshape(waves, -1),
        known.reshape(waves, -1) @ p.T,
        rtol=0,
        atol=4e-16,
    )
    np.testing.assert_array_equal(
        solver.gradient(torch.from_numpy(known)).numpy().ravel(), d @ known.ravel()
    )
    operator = np.concatenate([a, weight * d])
    tau = 0.99 / np.maximum(np.abs(operator).sum(0), 1e-12)
    sigma = np.concatenate(
        [0.99 / np.maximum(np.abs(a).sum(1), 1e-12), np.full(len(d), 0.99 / (2 * weight))]
    )
    norm = np.linalg.norm(np.sqrt(sigma)[:, None] * operator * np.sqrt(tau)[None], ord=2)
    assert norm <= 0.99 + 1e-14


@pytest.mark.parametrize("waves", [1, 2])
def test_positive_TV_and_area_match_constructed_interior_KKT_optimum(waves):
    t, target, known, a, d, _, areas, weight, area = dense_problem(waves)

    def objective(u):
        g = (d @ u.ravel()).reshape(2, waves, 3, 3)
        return (
            0.5 * np.sum((a @ u.ravel() - target.ravel()) ** 2)
            + weight * np.sqrt(np.sum(g * g, 0)).sum()
            + np.sum(areas * u)
        )

    _, info = fit_masks(t, target, weight=weight, area=area, coarse=3)
    actual = _solver(t.shape, 3, "cpu").u.numpy()
    optimum = objective(known)
    assert info["converged"]
    assert info["lower"] - 1e-10 <= optimum <= info["primal"] + 1e-10
    np.testing.assert_allclose(objective(actual), info["primal"], rtol=0, atol=1e-11)
    np.testing.assert_allclose(actual, known, rtol=0, atol=1e-4)


@pytest.mark.parametrize("area,expected", [(0, 1), (0.001, 0)])
def test_zero_templates_choose_constant_mask_without_inventing_a_wave(area, expected):
    masks, info = fit_masks(np.zeros((2, 8, 8)), np.ones((8, 8)), area=area, coarse=2)
    np.testing.assert_array_equal(masks, np.full((2, 8, 8), expected))
    assert info["converged"] and info["absolute_gap"] == 0


PATTERNS = [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)]


@pytest.mark.parametrize("colors", PATTERNS)
@pytest.mark.parametrize("frequency", [(-0.0713, 0.0532), (0.2343, 0.1482)])
def test_reciprocal_templates_keep_physical_phase_and_ignore_parent(colors, frequency):
    colors = np.array(colors)
    y, x = np.mgrid[:128, :128]
    plane = np.stack([np.ones_like(x), x / 127, y / 127], -1).reshape(-1, 3)
    packed = np.stack(
        [
            0.02
            + 0.002
            * np.cos(
                2 * np.pi * (frequency[0] * (2 * x + p % 2) + frequency[1] * (2 * y + p // 2)) + 0.7
            )
            for p in range(4)
        ]
    )
    fitted = {
        "packed": packed,
        "variance": np.full_like(packed, 1e-7),
        "colors": colors,
        "plane": plane,
        "base": np.zeros((3, 256, 256)),
    }
    templates, target = reciprocal_templates(fitted, [frequency])
    yy, xx = np.mgrid[:256, :256]
    true = 0.002 * np.cos(2 * np.pi * (frequency[0] * xx + frequency[1] * yy) + 0.7) / np.sqrt(1e-7)
    for p in np.flatnonzero(colors == 1):
        a = templates[0, p // 2 :: 2, p % 2 :: 2][32:96, 32:96]
        b = true[p // 2 :: 2, p % 2 :: 2][32:96, 32:96]
        np.testing.assert_allclose(a, b, rtol=0, atol=1e-3)
    fitted["base"].fill(100)
    other = reciprocal_templates(fitted, [frequency])
    np.testing.assert_array_equal(other[0], templates)
    np.testing.assert_array_equal(other[1], target)
    # Alter one phase only: its prediction from the other green and the other
    # phase's target retain their values when the supplied variances are fixed.
    phase, other_phase = np.flatnonzero(colors == 1)
    fitted["packed"][phase] += np.random.default_rng(84).normal(0, 0.001, (128, 128))
    changed, changed_target = reciprocal_templates(fitted, [frequency])
    np.testing.assert_array_equal(
        changed[0, phase // 2 :: 2, phase % 2 :: 2], templates[0, phase // 2 :: 2, phase % 2 :: 2]
    )
    np.testing.assert_array_equal(
        changed_target[other_phase // 2 :: 2, other_phase % 2 :: 2],
        target[other_phase // 2 :: 2, other_phase % 2 :: 2],
    )


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
def test_CPU_CUDA_match_and_preserve_RNG_on_dense_positive_TV_problem():
    t, target, _, _, _, _, _, weight, area = dense_problem(2)
    before = torch.get_rng_state().clone()
    gpu_before = torch.cuda.get_rng_state().clone()
    cpu, ci = fit_masks(t, target, weight=weight, area=area, coarse=3)
    gpu, gi = fit_masks(t, target, weight=weight, area=area, coarse=3, device="cuda")
    np.testing.assert_allclose(cpu, gpu, rtol=0, atol=2e-13)
    assert ci["converged"] and gi["converged"]
    assert torch.equal(before, torch.get_rng_state()) and torch.equal(
        gpu_before, torch.cuda.get_rng_state()
    )


@pytest.mark.parametrize(
    "kwargs", [{"coarse": 0}, {"coarse": 9}, {"area": -0.1}, {"weight": 0}, {"iterations": 33}]
)
def test_invalid_mask_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        fit_masks(np.zeros((1, 8, 8)), np.zeros((8, 8)), **kwargs)


def test_partial_wave_keeps_interior_support_and_rejects_distant_blank_pixels():
    y, x = np.mgrid[:256, :256]
    frequency = (-0.0713, 0.0532)
    signal = 0.002 * np.cos(2 * np.pi * (frequency[0] * x + frequency[1] * y) + 0.7)
    signal *= (x >= 16) & (x < 128) & (y >= 16) & (y < 128)
    raw = 0.02 + signal
    py, px = np.mgrid[:128, :128]
    packed = np.stack([raw[p // 2 :: 2, p % 2 :: 2] for p in range(4)])
    fitted = {
        "packed": packed,
        "variance": np.full_like(packed, 1e-7),
        "colors": np.array(PATTERNS[0]),
        "plane": np.stack([np.ones_like(px), px / 127, py / 127], -1).reshape(-1, 3),
    }
    support, info = cross_phase_masks(fitted, [frequency])
    assert support[0, 48:96, 48:96].all()
    assert not support[0, 200:240, 200:240].any()
    assert not info["confidence_calibrated"]
