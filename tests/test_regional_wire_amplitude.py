import numpy as np

from demosaic.regional_wire_amplitude import (
    matched_supported_amplitude,
    regional_deficit,
    tangent_neighbor_weights,
)


def test_tangent_pooling_never_crosses_the_other_wire_rows():
    w = np.eye(15)
    borrowed = tangent_neighbor_weights(w)
    np.testing.assert_array_equal(borrowed.sum(0), np.ones(15))
    np.testing.assert_array_equal(borrowed.sum(1), np.ones(15))
    np.testing.assert_array_equal(borrowed[4, 3:6], [0.25, 0.75, 0])
    np.testing.assert_array_equal(borrowed[7, 6:9], [0.25, 0.5, 0.25])


def test_reciprocal_deficit_limits_amplitude_and_uses_signed_agreement():
    a = np.array([[3.0, 1.5, 3.0, np.nan, 2.0], [-1.0, 1.5, 2.0, 4.0, 0.5]])
    expected = [0, 1.5, 2, 0, 1]
    np.testing.assert_allclose(regional_deficit(a, 2, reciprocal=True), expected)
    np.testing.assert_allclose(regional_deficit(a[::-1], 2, reciprocal=True), expected)
    np.testing.assert_allclose(regional_deficit(a, 2, reciprocal=False), [1, 1.5, 2, 0, 1.25])


def test_uniform_amplitude_matches_energy_on_the_same_envelope():
    carrier = np.array([-1, 2, -3, 2], dtype=float)
    support = np.array([0, 0.1, 0.8, 0.2])
    amplitude = support * [0, 3, 1, 2]
    k = matched_supported_amplitude(carrier, support, amplitude)
    assert 1.0 <= k <= 3.0
    np.testing.assert_allclose(
        np.sum((k * support * carrier) ** 2), np.sum((amplitude * carrier) ** 2)
    )
    assert matched_supported_amplitude(carrier, np.zeros(4), np.zeros(4)) == 0
