"""Actual float64 CUDA parity, state reset and RNG integrity for both projections."""

import numpy as np
import pytest
import torch

from demosaic.phase_sparse import coefficient_tv


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA required")
def test_sparse_and_masked_CUDA_graphs_match_CPU_without_RNG_or_state_leak():
    rng = np.random.default_rng(2026110801)
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state().clone()
    for mode in ["group", "mask"]:
        for cap in [1, 127, 1024]:
            values = rng.normal(0, 0.001, (2, 13, 17))
            extra = 0.0003 if mode == "group" else rng.uniform(size=(13, 17)) > 0.3
            expected, a = coefficient_tv(values, 0.001, extra, mode=mode, iterations=cap)
            actual, b = coefficient_tv(
                values, 0.001, extra, mode=mode, iterations=cap, device="cuda"
            )
            np.testing.assert_allclose(actual, expected, rtol=0, atol=2e-16)
            assert a["iterations"] == b["iterations"]
            if mode == "mask":
                np.testing.assert_array_equal(actual[:, ~extra], 0)
    assert torch.equal(cpu_rng, torch.get_rng_state())
    assert torch.equal(cuda_rng, torch.cuda.get_rng_state())
