"""Check signed RAW profile selection and its independent reserve."""

import numpy as np

from demosaic.finite_wire_profiles import _sample_profiles, reserve_wire_profiles
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.search_donor_geometry import screening_mask


def test_profile_phase_and_width_are_selected_from_reserved_raw_only():
    n = 128
    query = (48, 80, n, n)
    colors = np.array([0, 1, 1, 2])
    layout = np.tile(colors.reshape(2, 2), (n // 2, n // 2))
    frequencies = np.array([[0.081, 0.035], [-0.039, 0.071]])
    hessian = np.zeros((2, 2))
    yy, xx = np.indices((n, n)) - (n - 1) / 2
    profile = _sample_profiles(
        xx.ravel(), yy.ravel(), frequencies[0], hessian, np.array([0.3125]), np.array([0.07])
    ).reshape(n, n)
    rng = np.random.default_rng(7219)
    raw = 0.13 + np.array([-0.012, 0.025, 0.014])[layout] * profile
    raw += rng.normal(0, 0.0009, raw.shape)
    guide = {"active": [True, False], "frequencies_xy": frequencies}
    reserve = screening_mask(query)
    controls = []
    for values in (raw, np.where(reserve, raw, np.nan)):
        packed = np.stack([values[i::2, j::2] for i in range(2) for j in range(2)])
        controls.append(
            reserve_wire_profiles(
                packed,
                colors,
                query,
                guide,
                shot=0,
                read=0.0009**2,
                config=LocalWaveConfig(window=n, stride=n),
            )
        )
    (left, a), (right, b) = controls
    assert a == b
    assert a["trials"] == 48
    direction = a["directions"][0]
    assert direction["accepted"]
    assert (direction["phase_cycles"], direction["width_cycles"]) == (0.3125, 0.07)
    assert left[1] is right[1] is None
    np.testing.assert_array_equal(left[0], right[0])
    np.testing.assert_array_equal(left[0], profile)
