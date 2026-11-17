"""A grey or absent increment must not masquerade as signed-colour recovery."""

import numpy as np
from score_colored_fine_wires import colour_increments


def fixture():
    yy, xx = np.indices((32, 32))
    strong = np.exp(-(((xx - 16) / 3) ** 2))[None] * np.array([0.3, 1.0, 0.4])[:, None, None]
    weak = np.exp(-(((yy - 16) / 3) ** 2))[None] * np.array([1.0, -0.3, 0.7])[:, None, None]
    background = np.full_like(strong, 2.0)
    return np.stack([background, background + strong, background + strong + weak])


def test_perfect_signed_colour_has_unit_channel_response_and_no_colour_orthogonal_error():
    target = fixture()
    values = colour_increments(target, target)
    for name, value in values.items():
        np.testing.assert_allclose(value, 1 if name.endswith("gain") else 0, atol=1e-10)


def test_neutralizing_or_erasing_weak_colour_is_not_true_recovery():
    target = fixture()
    neutral = target.copy()
    neutral[2] = target[1] + (target[2] - target[1]).mean(axis=0, keepdims=True)
    measured = colour_increments(target, neutral)
    assert measured["weak_G_gain"] < 0
    assert measured["weak_colour_orthogonal_RMS_DN16"] > 1000
    absent = target.copy()
    absent[2] = target[1]
    measured = colour_increments(target, absent)
    for color in "RGB":
        assert measured["weak_" + color + "_gain"] == 0
