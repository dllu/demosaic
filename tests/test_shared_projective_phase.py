"""Check perspective transport and its separation from delivery RAW."""

import numpy as np

from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.search_donor_geometry import screening_mask
from demosaic.shared_projective_phase import projective_hessians, reserve_projective_phase


def test_shared_hessian_matches_second_order_perspective_phase():
    f = np.array([[0.08, 0.023], [-0.03, 0.07]])
    g = np.array([0.0012, -0.0004])
    h = projective_hessians(f, g)
    points = np.array([[12, 33], [-17, 5], [31, -20], [0, 0]])
    expected = -(f @ points.T) * (points @ g)
    np.testing.assert_allclose(0.5 * np.einsum("pi,kij,pj->kp", points, h, points), expected)
    np.testing.assert_array_equal(h, h.swapaxes(-1, -2))
    np.testing.assert_array_equal(projective_hessians(-f, g), -h)


def test_anchor_perspective_estimate_excludes_the_delivery_samples():
    n = 128
    box = (48, 80, n, n)
    angles = np.array([[0.079, 0.029], [-0.036, 0.069]])
    gradient = np.array([0.18, -0.09])
    yy, xx = np.indices((n, n)) - (n - 1) / 2
    grid = np.stack((xx, yy), axis=-1)
    phase = (grid @ angles.T) * (1 - (grid @ (gradient / n))[..., None])
    rng = np.random.default_rng(309)
    raw = 0.12 + 0.014 * np.cos(2 * np.pi * phase[..., 0] + 0.4)
    raw += 0.001 * np.cos(2 * np.pi * phase[..., 1] - 0.2)
    raw += rng.normal(0, 0.0008, (n, n))
    reserved = screening_mask(box)
    colors = np.array([0, 1, 1, 2])
    guide = {"frequencies_xy": angles.tolist(), "active": [True, True]}
    config = LocalWaveConfig(window=n, stride=n)
    checked = []
    for values in (raw, np.where(reserved, raw, np.nan)):
        packed = (
            values.reshape(n // 2, 2, n // 2, 2).transpose(1, 3, 0, 2).reshape(4, n // 2, n // 2)
        )
        checked.append(
            reserve_projective_phase(
                packed, colors, box, guide, shot=0, read=0.0008**2, config=config
            )
        )
    (h0, record0), (h1, record1) = checked
    assert record0 == record1
    np.testing.assert_array_equal(h0, h1)
    assert record0["directions"][0]["accepted"]
    assert record0["directions"][0]["proposed"] == tuple(gradient)
    np.testing.assert_allclose(h0[0], projective_hessians(angles, gradient / n))
