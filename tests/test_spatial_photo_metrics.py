import numpy as np
import pytest
from review_spatial_photo_supplement import photo_metrics


@pytest.mark.parametrize("side", [384, 512])
def test_photo_gain_tracks_detail_independently_of_dc_and_preserves_error_decomposition(side):
    y, x = np.mgrid[:side, :side]
    texture = 0.001 * np.cos(2 * np.pi * x / 7) + 0.0007 * np.sin(2 * np.pi * y / 5)
    target = np.broadcast_to(0.02 + texture, (1, 3, side, side)).copy()
    arrays = {"wb": np.ones((1, 3)), "matrix": np.eye(3)[None]}
    origin = (side - 160) // 2
    roi = [origin, origin, 160, 160]
    a = photo_metrics(target, target, arrays, roi)
    assert a["crop_linear_sRGB_luma_band_gain"] == pytest.approx(1)
    assert a["crop_relative_band_error"] == pytest.approx(0, abs=1e-15)
    prediction = 0.4 * target + 0.003
    b = photo_metrics(prediction, target, arrays, roi)
    assert b["crop_linear_sRGB_luma_band_gain"] == pytest.approx(0.4)
    assert b["crop_orthogonal_band_RMS_DN16"] < 1e-10
    assert b["crop_error_RMS_DN16"] ** 2 == pytest.approx(
        b["crop_DC_RMS_DN16"] ** 2 + b["crop_spatial_RMS_DN16"] ** 2, rel=1e-12
    )


def test_photo_band_metric_rejects_a_flat_target():
    values = np.zeros((1, 3, 384, 384))
    with pytest.raises(ValueError, match="nonzero target detail"):
        photo_metrics(
            values, values, {"wb": np.ones((1, 3)), "matrix": np.eye(3)[None]}, [112, 112, 160, 160]
        )
