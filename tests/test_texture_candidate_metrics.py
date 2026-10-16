import math
from pathlib import Path

import pytest
import torch


@pytest.fixture
def metrics(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from evaluate_texture_candidates import flat_metrics

    return flat_metrics


def test_constant_color_bias_is_separate_from_false_texture(metrics):
    target = torch.full((1, 3, 256, 256), 0.2, dtype=torch.float64)
    prediction = target + torch.tensor([0.001, -0.001, 0], dtype=torch.float64)[None, :, None, None]
    result = metrics(prediction, target)
    assert math.isclose(result["dc_bias_abs_rgb"][0], 2 / 3 * 0.001, rel_tol=1e-10)
    assert result["spatial_luma_rms"][0] < 1e-14
    assert result["relative_band_rms"][0] < 1e-14
    assert result["relative_peak_band_contrast"][0] < 1e-14


def test_false_periodic_structure_at_an_oblique_angle_is_measured(metrics):
    y, x = torch.meshgrid(
        torch.arange(256, dtype=torch.float64),
        torch.arange(256, dtype=torch.float64),
        indexing="ij",
    )
    wave = 0.005 * torch.cos(2 * math.pi * (12 * x + 16 * y) / 160)
    target = torch.full((1, 3, 256, 256), 0.2, dtype=torch.float64)
    result = metrics(target + wave[None, None], target)
    assert math.isclose(result["spatial_luma_rms"][0], 0.005 / math.sqrt(2), rel_tol=1e-10)
    assert math.isclose(result["relative_band_rms"][0], 0.005 / 0.2 / math.sqrt(2), rel_tol=1e-10)
    assert math.isclose(result["relative_peak_band_contrast"][0], 0.005 / 0.2, rel_tol=1e-10)
