import numpy as np
from frequency_coverage_reference import dense_spectral_row, direct_local_power, qr_spectrum
from green_phase_spectrum import tapered_spectrum
from local_phase_projection import local_phase_projection


def test_qr_fft_variance_matches_explicit_linear_rows_at_every_small_bin():
    rng = np.random.default_rng(18603)
    image = rng.normal(0.02, 0.001, (8, 11))
    variance = rng.uniform(1e-6, 4e-6, image.shape)
    spectrum, noise, q, window = qr_spectrum(image, variance)
    for y in range(8):
        for x in range(11):
            row = dense_spectral_row(image.shape, [y, x], q, window)
            np.testing.assert_allclose(
                row @ (image - image[0, 0]).ravel(), spectrum[y, x], rtol=1e-11, atol=1e-16
            )
            np.testing.assert_allclose(
                (abs(row) ** 2) @ variance.ravel(), noise[y, x], rtol=1e-12, atol=1e-20
            )
    old = tapered_spectrum(image, variance)
    np.testing.assert_allclose(old["spectrum"], spectrum, rtol=1e-11, atol=1e-16)
    np.testing.assert_allclose(old["noise_variance"], noise, rtol=1e-12, atol=1e-20)


def test_direct_local_qr_matches_integral_projection_at_boundary_and_center():
    rng = np.random.default_rng(18604)
    image = rng.normal(0.02, 0.001, (24, 32))
    variance = rng.uniform(1e-6, 4e-6, image.shape)
    for center in [[0, 0], [12, 16], [23, 31]]:
        old = local_phase_projection(
            image, variance, np.array([3, 27]), window=9, centers_yx=np.array([center])
        )
        expected = float(
            abs(old["coefficient"][0]) ** 2 / max(float(old["noise_variance"][0]), (1 / 65535) ** 2)
        )
        np.testing.assert_allclose(
            direct_local_power(image, variance, [3, 27], center, 9),
            expected,
            rtol=1e-11,
            atol=1e-12,
        )
