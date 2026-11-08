"""Larger129window measurements and synthesis versus independent QR/NumPy."""

import numpy as np
import pytest
import torch
from dense_spectrum_reference import measurements, native_readout
from test_late_dense_local_spectrum import nonzero_head, numpy_state

from demosaic.cfa import color_indices
from demosaic.late_dense_local_spectrum import LateDenseLocalSpectrumDetail, dense_local_spectrum


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_larger_clipped_window_all_fields_and_native_pixels(pattern, dtype):
    rng = np.random.default_rng(19301)
    raw = torch.tensor(rng.uniform(0.001, 0.04, (1, 4, 48, 56)), dtype=dtype)
    variance = torch.tensor(rng.uniform(1e-7, 4e-6, raw.shape), dtype=dtype)
    colors = color_indices(pattern)
    x, c, g = dense_local_spectrum(
        raw, variance, colors, window=129, stride=64, support_windows=(33, 17)
    )
    ex, ec, eg = measurements(
        raw.numpy(),
        variance.numpy(),
        colors.numpy(),
        window=129,
        stride=64,
        support_windows=(33, 17),
    )
    tolerance = 4e-6 if dtype == torch.float32 else 4e-9
    np.testing.assert_allclose(x.numpy(), ex, rtol=tolerance, atol=tolerance)
    np.testing.assert_allclose(c.numpy(), ec, rtol=tolerance, atol=3e-10)
    np.testing.assert_allclose(
        g["aligned_spectra"].numpy(), eg["aligned_spectra"], rtol=2e-8, atol=3e-12
    )
    np.testing.assert_allclose(
        g["propagated_variance"].numpy(), eg["propagated_variance"], rtol=2e-8, atol=3e-16
    )
    head = nonzero_head(dtype)
    actual = head(x, c, g).detach().numpy()
    expected = native_readout(numpy_state(head), ex, ec, eg)
    np.testing.assert_allclose(
        actual, expected, rtol=tolerance, atol=3e-8 if dtype == torch.float32 else 3e-11
    )
    assert g["normalization"].min() > 0 and x.shape[1:] == (18, 129, 129)


def test_larger_configuration_has_identical_initial_state_and_no_new_parameters_or_RNG():
    before = torch.get_rng_state().clone()
    old = LateDenseLocalSpectrumDetail()
    new = LateDenseLocalSpectrumDetail(dense_window=129, dense_stride=64)
    assert torch.equal(before, torch.get_rng_state()) and len(new.state_dict()) == 193
    assert all(
        torch.equal(value, old.state_dict()[name]) for name, value in new.state_dict().items()
    )
    assert sum(p.numel() for p in new.parameters() if p.requires_grad) == 508
    assert (
        not new.frozen.training and not new.network.training and not new.phase_evidence_in.training
    )
