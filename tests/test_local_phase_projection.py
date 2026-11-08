"""Independent direct QR rows for local coefficients and heteroscedastic noise."""

import numpy as np
import pytest
from local_phase_projection import local_phase_projection


def direct(image, variance, frequency, box):
    x0, y0, width, height = box
    y, x = np.mgrid[y0 : y0 + height, x0 : x0 + width]
    basis = np.stack((np.ones_like(x), x - x.mean(), y - y.mean()), -1).reshape(-1, 3)
    q, _ = np.linalg.qr(basis, mode="reduced")
    carrier = np.exp(
        -2j * np.pi * (frequency[0] * y / image.shape[0] + frequency[1] * x / image.shape[1])
    ).ravel()
    row = carrier - q @ (q.T @ carrier)
    values = image[y0 : y0 + height, x0 : x0 + width].ravel()
    noise = variance[y0 : y0 + height, x0 : x0 + width].ravel()
    return row @ values, np.sum(noise * abs(row) ** 2)


@pytest.mark.parametrize("frequency", [[3, 5], [12, 17], [0, 0], [8, 0]])
@pytest.mark.parametrize("window", [3, 9, 25])
def test_integral_moments_match_direct_qr_coefficients_and_full_noise_rows(frequency, window):
    rng = np.random.default_rng(17901)
    image = rng.normal(size=(17, 23))
    variance = rng.uniform(0.001, 0.3, image.shape)
    centers = np.array([[0, 0], [8, 11], [16, 22], [1, 19], [10, 2]])
    actual = local_phase_projection(image, variance, frequency, window=window, centers_yx=centers)
    for coefficient, noise, box in zip(
        actual["coefficient"], actual["noise_variance"], actual["boxes_xywh"], strict=True
    ):
        reference, expected_noise = direct(image, variance, frequency, box)
        np.testing.assert_allclose(coefficient, reference, rtol=1e-10, atol=2e-10)
        np.testing.assert_allclose(noise, expected_noise, rtol=1e-10, atol=2e-10)


def test_affine_background_and_variance_are_handled_independently():
    rng = np.random.default_rng(17902)
    image = rng.normal(size=(32, 40))
    y, x = np.mgrid[:32, :40]
    plane = 10 + 0.3 * x - 0.7 * y
    variance = np.full_like(image, 0.1)
    options = {"bin_yx": [7, 11], "window": 17, "centers_yx": np.array([[0, 0], [16, 20], [31, 39]])}
    first = local_phase_projection(image, variance, **options)
    second = local_phase_projection(image + plane, variance, **options)
    np.testing.assert_allclose(first["coefficient"], second["coefficient"], rtol=1e-10, atol=2e-10)
    np.testing.assert_array_equal(first["noise_variance"], second["noise_variance"])
    third = local_phase_projection(image, variance * 3, **options)
    np.testing.assert_array_equal(first["coefficient"], third["coefficient"])
    np.testing.assert_allclose(first["noise_variance"] * 3, third["noise_variance"], rtol=1e-12)


def test_constant_inputs_are_exactly_zero_and_edge_boxes_are_truncated():
    image = np.full((16, 20), 0.125)
    result = local_phase_projection(
        image,
        np.zeros_like(image),
        [3, 4],
        window=9,
        centers_yx=np.array([[0, 0], [15, 19], [8, 10]]),
    )
    np.testing.assert_array_equal(result["coefficient"], 0)
    np.testing.assert_array_equal(result["noise_variance"], 0)
    np.testing.assert_array_equal(
        result["boxes_xywh"], [[0, 0, 5, 5], [15, 11, 5, 5], [6, 4, 9, 9]]
    )


@pytest.mark.parametrize("damage", ["variance", "NaN", "window", "bin", "center", "center_float"])
def test_invalid_inputs_reject(damage):
    image = np.ones((16, 20))
    variance = np.ones_like(image)
    frequency, window, centers = [3, 4], 9, np.array([[0, 0]])
    if damage == "variance":
        variance[0, 0] = -1
    elif damage == "NaN":
        image[0, 0] = np.nan
    elif damage == "window":
        window = 8
    elif damage == "bin":
        frequency = [16, 1]
    elif damage == "center":
        centers[0, 0] = -1
    else:
        centers = centers.astype(float)
    with pytest.raises(ValueError):
        local_phase_projection(image, variance, frequency, window=window, centers_yx=centers)
