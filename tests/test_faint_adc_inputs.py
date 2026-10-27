"""Verify the declared contrast/ADC operator without neural or noise sampling."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from queue_faint_adc_precision import PATTERNS, adc_observation, faint_target


def test_faint_contrast_preserves_DC_and_scales_spatial_detail():
    x = np.linspace(-1, 1, 256, dtype=np.float32)
    source = np.broadcast_to((0.3 + 0.2 * x)[None, None, None], (1, 3, 256, 256)).copy()
    value = faint_target(source)
    np.testing.assert_allclose(
        value.mean((-1, -2), dtype=np.float64),
        source.mean((-1, -2), dtype=np.float64),
        atol=2e-8,
        rtol=0,
    )
    np.testing.assert_allclose(np.ptp(value, axis=-1), 0.01, atol=2e-8, rtol=0)
    assert value.shape == source.shape and value.dtype == np.float32
    with pytest.raises(ValueError):
        faint_target(source[..., :-1])


@pytest.mark.parametrize("pattern", PATTERNS)
def test_all_CFA_phases_and_fixed_ADC_known_codes(pattern):
    # Invert exact ADC codes so distinct values identify channel AND phase.
    codes = np.array(
        [[15000, 20000, 25000, 30000], [35000, 40000, 45000, 50000], [51000, 52000, 53000, 54000]]
    )
    target = np.empty((1, 3, 256, 256), np.float32)
    for c in range(3):
        for phase, (y, x) in enumerate(((0, 0), (0, 1), (1, 0), (1, 1))):
            target[0, c, y::2, x::2] = (codes[c, phase] / 65535 - 0.03) / 0.97
    packed, variance, colors = adc_observation(target, pattern)
    for phase, c in enumerate(PATTERNS[pattern]):
        recovered = np.rint((packed[0, phase].astype(np.float64) * 0.97 + 0.03) * 65535)
        np.testing.assert_array_equal(recovered, np.full((128, 128), codes[c, phase]))
    assert not variance.any() and colors.tolist() == [list(PATTERNS[pattern])]
