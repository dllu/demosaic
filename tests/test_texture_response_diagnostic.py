import importlib.util
import math
from pathlib import Path

import numpy as np
import torch

spec = importlib.util.spec_from_file_location(
    "diagnose_texture_response",
    Path(__file__).resolve().parents[1] / "scripts/diagnose_texture_response.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_known_contrast_phase_and_bias_are_measured_independently():
    x = torch.arange(256, dtype=torch.float64)
    target = (0.18 + 0.02 * torch.cos(2 * math.pi * x / 8))[None, None, None].expand(1, 3, 256, 256)
    prediction = (
        0.19 + 0.01 * torch.cos(2 * math.pi * x / 8) + 0.005 * torch.sin(2 * math.pi * x / 8)
    )[None, None, None].expand_as(target)
    result = module.response_metrics(prediction, target, 8)
    np.testing.assert_allclose(result["in_phase_gain"], [0.5], atol=1e-12)
    np.testing.assert_allclose(result["quadrature_gain"], [0.25], atol=1e-12)
    np.testing.assert_allclose(result["amplitude_ratio"], [math.sqrt(0.5**2 + 0.25**2)], atol=1e-12)
    np.testing.assert_allclose(result["dc_bias_abs"], [0.01], atol=1e-12)
    assert result["noncarrier_rms"][0] < 1e-14


def test_unrelated_frequency_is_not_counted_as_recovered_detail():
    x = torch.arange(256, dtype=torch.float64)
    target = (0.18 + 0.02 * torch.cos(2 * math.pi * x / 16))[None, None, None].expand(
        1, 3, 256, 256
    )
    prediction = (0.18 + 0.03 * torch.cos(2 * math.pi * x / 4))[None, None, None].expand_as(target)
    result = module.response_metrics(prediction, target, 16)
    np.testing.assert_allclose(result["in_phase_gain"], [0], atol=1e-12)
    np.testing.assert_allclose(result["amplitude_ratio"], [0], atol=1e-12)
    np.testing.assert_allclose(result["noncarrier_rms"], [0.03 / math.sqrt(2)], atol=1e-12)
