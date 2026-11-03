import math

import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, malvar
from demosaic.collaborative_detail import collaborative_detail, dct8, patch_spectra


def observation(pattern="RGGB", size=64):
    colors = torch.tensor([PATTERNS[pattern]])
    _yy, xx = torch.meshgrid(torch.arange(size), torch.arange(size), indexing="ij")
    packed = torch.stack(
        [0.1 + 0.02 * torch.cos(2 * math.pi * (2 * xx + p % 2) / 16) for p in range(4)]
    )[None]
    return packed, torch.full_like(packed, 1e-8), colors


@pytest.mark.parametrize("pattern", PATTERNS)
def test_constant_color_and_adc_preserve_parent_exactly(pattern):
    colors = torch.tensor([PATTERNS[pattern]])
    base = torch.tensor([0.003, 0.03, 0.6])[None, :, None, None].expand(1, 3, 64, 80)
    packed = base[:, colors[0], ::2, ::2].clone()
    variance = torch.linspace(1e-8, 1e-4, packed.numel()).reshape_as(packed)
    correction, info = collaborative_detail(base, packed, variance, colors, neighbors=8)
    assert torch.count_nonzero(correction) == 0 and info["active_coefficients"] == 0
    changed = packed + torch.arange(packed.numel()).reshape_as(packed) * 1e-6
    correction, info = collaborative_detail(base, changed, variance * 0, colors)
    assert torch.count_nonzero(correction) == 0 and info["ADC_only_bypass"]


@pytest.mark.parametrize("pattern", PATTERNS)
def test_recovers_unrepresented_carrier_without_doubling_existing_detail(pattern):
    packed, variance, colors = observation(pattern)
    target = malvar(packed, colors)
    base = torch.full_like(target, 0.1)
    correction, info = collaborative_detail(base, packed, variance, colors)
    assert info["active_coefficients"] > 0
    assert len(info["candidate_grids"]) == 4
    # Four nonoverlapping origins keep the query's waveform phase, including
    # half-patch offsets. A single candidate grid incorrectly cancels it.
    torch.testing.assert_close(
        (base + correction)[..., 16:-16, 16:-16],
        target[..., 16:-16, 16:-16],
        rtol=0,
        atol=4e-5,
    )
    correction, info = collaborative_detail(target, packed, variance, colors)
    assert info["active_coefficients"] > 0
    assert torch.count_nonzero(correction) == 0


def test_heteroscedastic_dct_variance_matches_independent_linear_operator():
    basis = dct8("cpu", torch.float64)
    np.testing.assert_allclose(basis.numpy() @ basis.numpy().T, np.eye(8), atol=1e-14)
    rng = np.random.default_rng(19)
    variance = rng.uniform(0.1, 3, (8, 8))
    # Kronecker rows are the explicit independent-pixel operator, including DC.
    operator = np.kron(basis.numpy(), basis.numpy())
    expected = (operator**2 @ variance.ravel()).reshape(8, 8)
    actual = patch_spectra(torch.tensor(variance), basis.square()).numpy()
    np.testing.assert_allclose(actual, expected, atol=1e-14)
    draws = rng.normal(size=(8192, 64)) * np.sqrt(variance.ravel())
    np.testing.assert_allclose((draws @ operator.T).var(0).reshape(8, 8), expected, rtol=0.06)


def test_adaptive_grouping_rejects_fixed_gaussian_flat_draws():
    generator = torch.Generator().manual_seed(2026110302)
    active = 0
    for draw in range(32):
        pattern = list(PATTERNS)[draw % 4]
        colors = torch.tensor([PATTERNS[pattern]])
        packed = 0.02 + torch.randn(1, 4, 64, 64, generator=generator) * 0.004
        base = torch.full((1, 3, 128, 128), 0.02)
        correction, info = collaborative_detail(
            base, packed, torch.full_like(packed, 0.004**2), colors, neighbors=16
        )
        active += info["active_coefficients"]
        assert torch.isfinite(correction).all()
    assert active == 0


@pytest.mark.parametrize(
    "change", ["colors", "negative", "nonfinite", "neighbors", "alpha", "shape"]
)
def test_invalid_physical_inputs_refuse(change):
    packed, variance, colors = observation()
    base = malvar(packed, colors)
    options = {}
    if change == "colors":
        colors = torch.zeros_like(colors)
    elif change == "negative":
        variance[0, 0, 0, 0] = -1
    elif change == "nonfinite":
        packed[0, 0, 0, 0] = float("nan")
    elif change == "neighbors":
        options["neighbors"] = True
    elif change == "alpha":
        options["alpha"] = float("nan")
    else:
        base = base[..., :-1]
    with pytest.raises(ValueError):
        collaborative_detail(base, packed, variance, colors, **options)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_cuda_matches_cpu_carrier_and_restores_rng():
    values = observation()
    base = torch.full((1, 3, 128, 128), 0.1)
    expected, metadata = collaborative_detail(base, *values)
    torch.cuda.init()
    before = torch.cuda.get_rng_state().clone()
    actual, info = collaborative_detail(base.cuda(), *(v.cuda() for v in values))
    torch.testing.assert_close(actual.cpu(), expected, rtol=0, atol=2e-7)
    assert info["active_coefficients"] == metadata["active_coefficients"]
    assert torch.equal(torch.cuda.get_rng_state(), before)
