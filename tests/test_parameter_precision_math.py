"""Quadratic native-band objective, numerical derivative and gradient geometry."""

import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from feature_probe_math import controlled_bands
from parameter_precision_math import (
    gradient_summary,
    numpy_band_error,
    relative_band_error,
    valid_reference_blocks,
)


def test_band_objective_half_amplitude_and_independent_derivative():
    x = np.arange(256) + 0.5
    target = (
        np.broadcast_to(0.2 + 0.01 * np.cos(np.pi * x * 4 / 16)[None, None, None], (1, 3, 256, 256))
        .copy()
        .astype(np.float32)
    )
    mask = valid_reference_blocks(target, np.ones((1, 3)), np.eye(3)[None])
    values, true, _ = controlled_bands(target, mask)
    pred = torch.from_numpy(values["half-band"]).requires_grad_(True)
    truth = torch.from_numpy(target).requires_grad_(True)
    q = relative_band_error(pred, truth, mask)
    grad, target_grad = torch.autograd.grad(q, (pred, truth), allow_unused=True)
    assert q.item() == pytest.approx(0.125, abs=1e-7)
    assert target_grad is None
    step = 1e-3
    fd = (
        numpy_band_error(pred.detach().numpy() + step * true, target, mask)
        - numpy_band_error(pred.detach().numpy() - step * true, target, mask)
    ) / (2 * step)
    assert np.sum(grad.numpy().astype(np.float64) * true) == pytest.approx(fd, abs=2e-7)
    assert fd == pytest.approx(-0.5, abs=2e-7)


def test_gradient_comparison_distinguishes_scale_rotation_and_harmful_descent():
    a = np.array([[1.0, 0], [0, 2.0], [-1.0, 0]])
    result = gradient_summary(a @ a.T)
    assert result["gradient_cosine_BF16_FP32"] == 0
    assert result["gradient_norm_BF16_over_FP32"] == 2
    assert result["FP32_unit_step_band_error_derivative"] == 1
    assert result["BF16_unit_step_band_error_derivative"] == 0
