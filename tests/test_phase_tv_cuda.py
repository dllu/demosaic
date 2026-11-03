"""Actual float64 CUDA graph parity and RNG preservation, without neural calls."""

import numpy as np
import pytest
import torch

from demosaic.phase_tv import denoise_complex_tv


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
def test_CUDA_graph_matches_CPU_with_reused_buffers_and_keeps_RNG():
    torch.cuda.init()
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state().clone()
    rng = np.random.default_rng(2026110302)
    values = rng.normal(size=(2, 9, 11)) * 0.001
    weights = rng.uniform(0.0001, 0.001, size=(9, 11))
    for value, weight, cap in [
        (values, weights, 16),
        (values * 0.37, weights * 0.5, 24),
        (values, weights, 1),
    ]:
        expected, reference = denoise_complex_tv(value, weight, cap)
        actual, info = denoise_complex_tv(value, weight, cap, device="cuda")
        np.testing.assert_allclose(actual, expected, rtol=1e-10, atol=1e-13)
        assert info["iterations"] == reference["iterations"]
        assert info["relative_primal_dual_gap"] == pytest.approx(
            reference["relative_primal_dual_gap"], abs=1e-10
        )
    assert torch.equal(cpu_rng, torch.get_rng_state())
    assert torch.equal(cuda_rng, torch.cuda.get_rng_state())
