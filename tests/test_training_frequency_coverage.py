import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_training_frequency_coverage import spectrum


def test_native_four_pixel_carrier_has_expected_relative_power():
    mean, amplitude = .2, .01
    signal = mean+amplitude*np.cos(2*np.pi*np.arange(256)/4)
    rgb = np.broadcast_to(signal[None, None], (3, 256, 256))
    result = spectrum(rgb)
    assert result["mean_linear_luminance"] == pytest.approx(mean)
    for band in result["bands"].values():
        assert band["relative_RMS"] == pytest.approx(amplitude/np.sqrt(2)/mean, rel=1e-5)
        assert band["fraction_of_1over64_to_045_power"] > .999999


def test_coarser_carrier_is_not_counted_as_four_pixel_structure():
    signal = .2+.01*np.cos(2*np.pi*np.arange(256)/16)
    result = spectrum(np.broadcast_to(signal[None, None], (3, 256, 256)))
    assert all(m["fraction_of_1over64_to_045_power"] < 1e-8 for m in result["bands"].values())


def test_exact_flat_has_no_fine_energy_and_invalid_contexts_fail():
    result = spectrum(np.ones((3, 256, 256)))
    assert all(m["relative_RMS"] == 0 for m in result["bands"].values())
    for value in (np.zeros((3, 128, 128)), np.full((3, 256, 256), np.nan)):
        with pytest.raises(ValueError, match="native256"):
            spectrum(value)
