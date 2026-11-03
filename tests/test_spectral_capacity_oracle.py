"""Independent coefficient fixtures; GT oracle rows are never inference."""

import numpy as np
import pytest
import torch
from diagnose_late_spectral_capacity import coefficient_witnesses, image_alpha


def fixture(dtype=torch.float64):
    rng = np.random.default_rng(14901)
    x = np.fft.fft2(rng.normal(size=(2, 4, 8, 8)), norm="ortho")
    y = np.fft.fft2(rng.normal(size=(2, 4, 8, 8)), norm="ortho") * 0.3
    cap = np.full((2, 1, 8, 8), 0.4)
    cdtype = torch.complex128 if dtype == torch.float64 else torch.complex64
    return (
        torch.tensor(x, dtype=cdtype),
        torch.tensor(y, dtype=cdtype),
        torch.tensor(cap, dtype=dtype),
    )


def test_numpy_scalar_optimum_and_relaxed_ball_projection():
    x, y, cap = fixture()
    scalar, _, relaxed, _ = coefficient_witnesses(x, y, cap)
    a, b, c = x.numpy(), y.numpy(), cap.numpy()
    energy = np.sum(abs(a) ** 2, axis=1, keepdims=True)
    gain = np.clip(np.real(np.sum(np.conj(a) * b, axis=1, keepdims=True)) / energy, -c, c)
    np.testing.assert_allclose(scalar.numpy(), gain * a, rtol=1e-12, atol=1e-12)
    radius = c * np.sqrt(energy)
    expected = b * np.minimum(1, radius / np.linalg.norm(b, axis=1, keepdims=True))
    np.testing.assert_allclose(relaxed.numpy(), expected, rtol=1e-12, atol=1e-12)
    assert (relaxed - y).abs().square().sum() <= (scalar - y).abs().square().sum()
    for perturb in [-0.1, 0.1]:
        shifted = np.clip(gain + perturb, -c, c) * a
        assert np.sum(abs(gain * a - b) ** 2) <= np.sum(abs(shifted - b) ** 2)


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_feasible_rank_one_matrix_matches_independent_numpy(dtype):
    x, y, cap = fixture(dtype)
    _, delta, _, matrix = coefficient_witnesses(x, y, cap)
    a, b, c = x.numpy().astype(np.complex128), y.numpy().astype(np.complex128), cap.numpy()
    raw = (
        b[:, :, None] * np.conj(a[:, None]) / np.sum(abs(a) ** 2, axis=1, keepdims=True)[:, :, None]
    )
    gauge = np.sqrt(
        np.max(np.sum(abs(raw), axis=1), axis=1) * np.max(np.sum(abs(raw), axis=2), axis=1)
    )[:, None]
    H = raw / np.maximum(c, gauge)[:, :, None]
    H = np.clip(H.real, -1 + 1e-6, 1 - 1e-6) + 1j * np.clip(H.imag, -1 + 1e-6, 1 - 1e-6)
    reverse = (-np.arange(8)) % 8
    H = (H + np.conj(H[..., reverse, :][..., :, reverse])) * 0.5
    bound = np.sqrt(np.max(np.sum(abs(H), axis=1), axis=1) * np.max(np.sum(abs(H), axis=2), axis=1))
    H /= np.maximum(1, bound)[:, None, None]
    expected = c * np.einsum("noihw,nihw->nohw", H, a)
    tol = 2e-6 if dtype == torch.float32 else 1e-12
    np.testing.assert_allclose(matrix.numpy(), H, rtol=tol, atol=tol)
    np.testing.assert_allclose(delta.numpy(), expected, rtol=tol, atol=tol)
    sv = np.linalg.svd(np.moveaxis(matrix.numpy(), (1, 2), (-2, -1)), compute_uv=False)
    assert sv.max() <= 1 + 2e-6
    assert matrix.real.abs().max() < 1 and matrix.imag.abs().max() < 1
    imag = torch.fft.ifft2(delta).imag.abs().max()
    assert imag < tol


def test_zero_innovation_zero_cap_and_exact_easy_target():
    x, y, cap = fixture()
    for a, c in [(x, torch.zeros_like(cap)), (torch.zeros_like(x), cap)]:
        values = coefficient_witnesses(a, y, c)
        assert all(torch.isfinite(v).all() for v in values)
        assert all(v.count_nonzero() == 0 for v in values[:3])
    desired = x * 0.05
    scalar, matrix, relaxed, _ = coefficient_witnesses(x, desired, cap)
    torch.testing.assert_close(scalar, desired, rtol=1e-12, atol=1e-12)
    torch.testing.assert_close(matrix, desired, rtol=1e-12, atol=1e-12)
    torch.testing.assert_close(relaxed, desired, rtol=1e-12, atol=1e-12)


def test_global_image_alpha_uses_full_context_and_stays_feasible():
    base = torch.zeros(1, 3, 8, 8)
    correction = torch.arange(192, dtype=torch.float32).reshape_as(base) / 100
    assert image_alpha(base, base + correction * 0.3, correction) == pytest.approx(0.3, abs=1e-7)
    assert image_alpha(base, base - correction, correction) == 0
    assert image_alpha(base, base + 2 * correction, correction) == 1
    assert image_alpha(base, base, torch.zeros_like(base)) == 0


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_cuda_coefficient_witnesses_match_cpu():
    x, y, cap = fixture(torch.float32)
    expected = coefficient_witnesses(x, y, cap)
    actual = coefficient_witnesses(x.cuda(), y.cuda(), cap.cuda())
    for a, b in zip(actual, expected, strict=True):
        torch.testing.assert_close(a.cpu(), b, rtol=5e-6, atol=2e-6)
