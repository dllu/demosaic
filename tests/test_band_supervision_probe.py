import sys
from pathlib import Path

import numpy as np
import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from probe_band_supervision import band_penalty, numpy_penalty


@pytest.mark.parametrize("normalized", [False, True])
def test_new_term_matches_independent_values_and_directional_derivatives(normalized):
    rng = np.random.default_rng(42)
    target = .3+rng.normal(0, .04, (1, 3, 40, 44))
    prediction = target+rng.normal(0, .002, target.shape)
    direction = rng.normal(0, .001, target.shape)
    p = torch.tensor(prediction, requires_grad=True)
    value = band_penalty(p, torch.tensor(target), normalized=normalized)
    assert float(value.detach()) == pytest.approx(numpy_penalty(prediction, target, normalized=normalized), rel=1e-10, abs=1e-14)
    gradient = torch.autograd.grad(value, p)[0].numpy()
    h = 1e-4
    finite = (numpy_penalty(prediction+h*direction, target, normalized=normalized)-numpy_penalty(prediction-h*direction, target, normalized=normalized))/(2*h)
    assert float(np.sum(gradient*direction)) == pytest.approx(finite, rel=2e-6, abs=1e-12)


@pytest.mark.parametrize("normalized", [False, True])
def test_correct_flat_has_zero_pressure_and_clipped_targets_are_excluded(normalized):
    target = torch.full((2, 3, 32, 32), .2, dtype=torch.float64)
    p = target.clone().requires_grad_(True)
    value = band_penalty(p, target, normalized=normalized)
    assert value == 0
    assert torch.count_nonzero(torch.autograd.grad(value, p)[0]) == 0
    clipped = torch.ones_like(target)
    wrong = torch.zeros_like(target).requires_grad_(True)
    value = band_penalty(wrong, clipped, normalized=normalized)
    assert value == 0 and torch.count_nonzero(torch.autograd.grad(value, wrong)[0]) == 0


@pytest.mark.parametrize("normalized", [False, True])
def test_constant_camera_offsets_leave_term_and_mean_gradient_unchanged(normalized):
    rng = np.random.default_rng(3)
    target = torch.tensor(.3+rng.normal(0, .02, (1, 3, 40, 40)))
    prediction = (target+torch.tensor(rng.normal(0, .003, target.shape))).requires_grad_(True)
    value = band_penalty(prediction, target, normalized=normalized)
    offset = torch.tensor([.01, -.02, .03])[None, :, None, None]
    shifted = band_penalty(prediction+offset, target, normalized=normalized)
    assert float(value.detach()) == pytest.approx(float(shifted.detach()), rel=1e-10, abs=1e-14)
    gradient = torch.autograd.grad(value, prediction)[0]
    assert float(gradient.sum((-2, -1)).abs().max()) < 1e-12


def test_per_image_normalization_and_empty_image_do_not_change_valid_gradient():
    rng = np.random.default_rng(17)
    target = torch.tensor(.3+rng.normal(0, .02, (1, 3, 36, 40)))
    p = (target+torch.tensor(rng.normal(0, .003, target.shape))).requires_grad_(True)
    one = band_penalty(p, target, normalized=True)
    joined = torch.cat([p, torch.zeros_like(p)])
    two = band_penalty(joined, torch.cat([target, torch.ones_like(target)]), normalized=True)
    assert torch.equal(one, two)
    assert torch.equal(torch.autograd.grad(one, p)[0], torch.autograd.grad(two, p)[0])


def test_normalized_term_is_contrast_invariant_above_its_explicit_floor():
    rng = np.random.default_rng(52)
    target = torch.tensor(.4+rng.normal(0, .12, (1, 3, 40, 40)))
    target.clamp_(.05, .8)
    p = target+torch.tensor(rng.normal(0, .005, target.shape))
    a = band_penalty(p, target, normalized=True)
    b = band_penalty(.4+(p-.4)*.5, .4+(target-.4)*.5, normalized=True)
    assert float(a) == pytest.approx(float(b), rel=1e-12)
