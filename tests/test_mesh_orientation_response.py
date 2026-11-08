import math

import numpy as np
import pytest
from mesh_orientation_response import detrend, project, sectors


def example():
    y, x = np.mgrid[:64, :64]
    a = np.cos(2 * np.pi * (5 * x + 3 * y) / 64)
    b = 0.25 * np.cos(2 * np.pi * (-4 * x + 7 * y) / 64)
    c = 0.1 * (-1.0) ** (x + y)
    return (
        np.stack([a + 0.5 * b + 0.2 * c] * 3),
        np.stack([0.2 * a + 0.5 * 1.8 * b + 0.2 * -0.3 * c] * 3),
        [math.atan2(3, 5), math.atan2(7, -4)],
    )


def test_known_independent_native_carrier_amplitudes_and_recomposition():
    target, value, angles = example()
    r = project(value, target, np.zeros_like(target), angles)
    for actual, want in zip([s["gain"] for s in r["sectors"]], [0.2, 1.8, -0.3], strict=True):
        assert actual == pytest.approx(want, abs=1e-11)
    assert r["whole_template_gain"] == pytest.approx(
        sum(s["gain"] * s["template_energy_fraction"] for s in r["sectors"]), abs=1e-13
    )
    assert r["whole_template_gain"] != pytest.approx(1.0)


def test_exact_GT_and_empty_response_and_affine_invariance():
    t, v, a = example()
    y, x = np.mgrid[:64, :64]
    background = np.stack([5 + 2 * x + 0.3 * y] * 3)
    for value, want in [(t, 1.0), (np.zeros_like(t), 0.0)]:
        r = project(value + background, t + background, background, a)
        assert r["whole_template_gain"] == pytest.approx(want, abs=1e-11)
        for s in r["sectors"]:
            assert s["gain"] == pytest.approx(want, abs=1e-11)
    np.testing.assert_allclose(detrend(v + background), detrend(v), atol=2e-13)


def test_conjugate_closed_partition_and_recipe_order_symmetry():
    t, v, a = example()
    m = sectors((64, 64), a)
    assert np.all(m.sum(0) == 1)
    p = project(v, t, np.zeros_like(t), a)
    q = project(v, t, np.zeros_like(t), a[::-1])
    assert p["whole_template_gain"] == q["whole_template_gain"]
    assert [s["gain"] for s in p["sectors"][:2]] == pytest.approx(
        [s["gain"] for s in q["sectors"][:2]][::-1]
    )


@pytest.mark.parametrize("angles", [[0, 0], [0, math.pi], [0, float("nan")], [0]])
def test_invalid_normals(angles):
    with pytest.raises(ValueError):
        sectors((64, 64), angles)


def test_no_template_and_mismatched_native_shapes():
    t, v, a = example()
    with pytest.raises(ValueError):
        project(v, np.zeros_like(t), np.zeros_like(t), a)
    with pytest.raises(ValueError):
        project(v, t[:, :, :32], np.zeros_like(t), a)


@pytest.mark.parametrize("rotation", range(4))
@pytest.mark.parametrize("flip", [False, True])
def test_native_angle_transport_matches_exact_pixel_transforms(rotation, flip):
    from mesh_orientation_response import native_angles

    target, value, angles = example()
    target, value = [np.rot90(v, rotation, axes=(-2, -1)) for v in [target, value]]
    if flip:
        target, value = [v[..., ::-1] for v in [target, value]]
    carried = native_angles(angles, rotation, flip)
    measured = project(value, target, np.zeros_like(target), carried)
    assert [s["gain"] for s in measured["sectors"]] == pytest.approx([0.2, 1.8, -0.3], abs=1e-11)
    # Independent coordinate-grid transport, including translations.
    y, x = np.mgrid[:64, :64]
    xy = np.rot90(np.stack([x, y]), rotation, axes=(-2, -1))
    if flip:
        xy = xy[..., ::-1]
    jacobian = np.stack([xy[:, 0, 1] - xy[:, 0, 0], xy[:, 1, 0] - xy[:, 0, 0]], axis=1)
    for original, actual in zip(angles, carried, strict=True):
        expected = jacobian.T @ np.array([math.cos(original), math.sin(original)])
        assert abs(np.dot(expected, [math.cos(actual), math.sin(actual)])) == pytest.approx(
            1.0, abs=1e-14
        )
