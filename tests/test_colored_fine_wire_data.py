"""Fresh coloured RGB targets, true CFA sites and independent physical noise."""

import numpy as np
import pytest
from colored_fine_wire_data import PATTERNS, PRIORS, observe, render


@pytest.mark.parametrize("source", [0, 1])
def test_exact_finite_increments_keep_declared_signed_RGB_colours(source):
    arrays, recipe = render(source, size=64, supersample=4)
    target = arrays["target"]
    assert target.dtype == np.float32
    for i in range(2):
        delta = target[i + 1].astype("f8") - target[i]
        colour = np.array(recipe["increment_colours_sensor_RGB"][i])
        unit = colour / np.linalg.norm(colour)
        projected = np.einsum("c,cyx->yx", unit, delta)[None] * unit[:, None, None]
        # Subtracting two stored FP32 targets and projecting RGB introduces
        # rounding at the bright edge; use two native FP32 ULPs, far below1DN16.
        np.testing.assert_allclose(delta, projected, atol=2 * np.spacing(target.max()))
        assert np.mean(delta[:, arrays["quiet"]] ** 2) < 1e-16
    if source == 1:
        weak = target[2] - target[1]
        assert weak[0].max() > 0 and weak[1].min() < 0 and weak[2].max() > 0
    assert arrays["quiet"].any() and arrays["edge_band"].any()
    again, _ = render(source, size=64, supersample=4)
    np.testing.assert_array_equal(target, again["target"])


@pytest.mark.parametrize("pattern", PATTERNS)
def test_every_CFA_layout_uses_its_actual_colour_and_distinct_role_noise(pattern):
    target = np.broadcast_to(
        np.array([0.01, 0.03, 0.08], np.float32)[None, :, None, None], (3, 3, 256, 256)
    ).copy()
    arrays, identities = observe(target, pattern, "iso1600", source=0)
    assert len({tuple(r["key"]) for r in identities}) == 3
    packed = arrays["packed"]
    noise = PRIORS["iso1600"]
    for phase, color in enumerate(PATTERNS[pattern]):
        expected = target[0, color, 0, 0]
        residual = packed[:, phase].astype("f8") - expected
        variance = expected * noise["shot"] + noise["read"]
        assert abs(residual.mean()) < 4 * np.sqrt(variance / residual.size)
        assert abs(residual.var() / variance - 1) < 0.05
    assert not np.array_equal(packed[0], packed[1])
    np.testing.assert_array_equal(
        observe(target, pattern, "iso1600", source=0)[0]["packed"], packed
    )


def test_zero_signal_retains_signed_read_noise():
    target = np.zeros((3, 3, 64, 64), np.float32)
    arrays, _ = observe(target, "RGGB", "iso6400", source=0)
    value = arrays["packed"]
    assert value.min() < 0 < value.max()
    assert abs(value.mean()) < 4 * np.sqrt(PRIORS["iso6400"]["read"] / value.size)
    assert abs(value.var() / PRIORS["iso6400"]["read"] - 1) < 0.05
