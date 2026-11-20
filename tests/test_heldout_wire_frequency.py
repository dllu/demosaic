import numpy as np
import pytest

from demosaic.heldout_wire_frequency import refine_wire_frequencies


def field():
    y, x = np.indices((128, 128))
    xx = 2 * x[..., None] + np.array([0, 1, 0, 1]) - 127.5
    yy = 2 * y[..., None] + np.array([0, 0, 1, 1]) - 127.5
    wavevectors = np.array([[0.090, 0.064], [0.114, -0.052]])
    channels = np.array([0.7, 1.0, 1.0, 0.65])
    raw = 0.25 + 0.0004 * xx + 0.0003 * yy
    for amount, (fx, fy) in zip((0.012, 0.008), wavevectors, strict=True):
        c = 2 * np.pi * (fx * xx + fy * yy) + 0.13
        raw = raw + channels * amount * (np.cos(c) + 0.3 * np.cos(2 * c))
    radius = np.hypot(xx / 31, yy / 35)
    radial = wavevectors / np.linalg.norm(wavevectors, axis=1, keepdims=True)
    displaced = wavevectors + 0.5 * radial / 256
    return raw, radius, wavevectors, displaced, channels


@pytest.mark.parametrize("innovation", [False, True])
def test_half_bin_recovery_on_a_mixed_two_direction_field(innovation):
    raw, radius, exact, displaced, channels = field()
    output = refine_wire_frequencies(
        raw,
        radius,
        displaced,
        channels,
        shot=0,
        read=1e-7,
        discovery_parity=0,
        innovation=innovation,
    )
    assert output["accepted"] and output["heldout_gain"] > 2
    np.testing.assert_allclose(output["chosen"], exact, rtol=0, atol=2e-15)


def test_nomination_excludes_validation_and_inside_aperture_samples():
    raw, radius, _, proposed, channels = field()
    args = {"shot": 0, "read": 1e-7, "discovery_parity": 0, "innovation": True}
    fit = refine_wire_frequencies(raw, radius, proposed, channels, **args)
    y, x = np.indices(raw.shape[:2])
    removed = raw.copy()
    removed[((y + x) % 2 == 1)[..., None] | (radius <= 1.4)] = 0.95
    assert refine_wire_frequencies(removed, radius, proposed, channels, **args) == fit

    removed = raw.copy()
    removed[(y // 8 + x // 8) % 2 == 1] = 0.3
    audited = refine_wire_frequencies(removed, radius, proposed, channels, **args)
    assert audited["nomination"] == fit["nomination"]
    assert audited["training_cell_gain"] == fit["training_cell_gain"]
    assert audited["heldout_gain"] < fit["heldout_gain"]
