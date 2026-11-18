"""Test frequency selection with a fixed footprint and independent delivery sites."""

import numpy as np

from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.localized_guide_frequency import frequency_neighborhood, reserve_companion_frequencies
from demosaic.search_donor_geometry import screening_mask


def test_limited_companion_search_uses_only_reserved_raw():
    n = 128
    query = (48, 80, n, n)
    colors = np.array([0, 1, 1, 2])
    yy, xx = np.indices((n, n))
    anchor, companion = np.array([0.077, 0.022]), np.array([-0.037, 0.081])
    guide_frequency = companion * (1 + 1 / (n * np.linalg.norm(companion)))
    options = frequency_neighborhood(guide_frequency, n)
    assert len(options) == 12
    envelope = np.maximum(0, 1 - ((xx - 61) ** 2 + (yy - 47) ** 2) / 42**2)
    layout = np.tile(colors.reshape(2, 2), (n // 2, n // 2))
    raw = 0.13 + 0.019 * np.cos(2 * np.pi * (anchor[0] * xx + anchor[1] * yy))
    raw += (
        np.array([-0.007, 0.017, 0.010])[layout]
        * envelope
        * np.sin(2 * np.pi * (companion[0] * xx + companion[1] * yy) + 0.7)
    )
    raw += np.random.default_rng(19).normal(0, 0.001, (n, n))
    guide = {"active": [True, True], "frequencies_xy": [anchor.tolist(), guide_frequency.tolist()]}
    reserve = screening_mask(query)
    results = []
    for data in (raw, np.where(reserve, raw, np.nan)):
        packed = np.stack([data[i::2, j::2] for i in range(2) for j in range(2)])
        results.append(
            reserve_companion_frequencies(
                packed,
                colors,
                query,
                guide,
                options,
                shot=0,
                read=1e-6,
                config=LocalWaveConfig(window=n, stride=n),
                envelope=envelope,
            )
        )
    assert results[0] == results[1]
    chosen, witness = results[0]
    assert witness["screening"]["localized"]["accepted"]
    np.testing.assert_array_equal(chosen["localized"]["frequencies_xy"][0], anchor)
    np.testing.assert_allclose(chosen["localized"]["frequencies_xy"][1], companion)
