import copy

import pytest
import torch
from train_v43_quality_trial import expected_training_model_config

from demosaic.cfa import adc_cfa_projection, color_indices, mosaic


def test_only_the_declared_constraint_changes_the_candidate_config():
    original = {"width": 64, "adc_cfa_projection": False, "encoder_blocks": (2, 2, 4)}
    before = copy.deepcopy(original)
    plan = {"arms": ["V98", "V99"], "model_overrides": {"V99": {"adc_cfa_projection": True}}}
    assert expected_training_model_config(original, plan, "V98") == original
    candidate = expected_training_model_config(original, plan, "V99")
    assert candidate == {**original, "adc_cfa_projection": True}
    assert original == before
    assert expected_training_model_config(original, {}, "V95") == original


@pytest.mark.parametrize("case", ["width", "wrong-arm", "wrong-study", "already-on", "integer"])
def test_unplanned_model_changes_are_rejected(case):
    parent = {"width": 64, "adc_cfa_projection": False}
    plan = {"arms": ["V98", "V99"], "model_overrides": {"V99": {"adc_cfa_projection": True}}}
    arm = "V99"
    if case == "width":
        plan["model_overrides"]["V99"]["width"] = 128
    elif case == "wrong-arm":
        arm = "V95"
    elif case == "wrong-study":
        plan["arms"] = ["V96", "V97"]
    elif case == "already-on":
        parent["adc_cfa_projection"] = True
    else:
        plan["model_overrides"]["V99"]["adc_cfa_projection"] = 1
    with pytest.raises(ValueError, match="override"):
        expected_training_model_config(parent, plan, arm)


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_projected_training_retains_nonzero_nullspace_directions(pattern):
    generator = torch.Generator().manual_seed(58)
    prediction = torch.rand(1, 3, 16, 20, generator=generator)
    packed = torch.rand(1, 4, 8, 10, generator=generator) * 0.8 + 0.1
    direction = torch.randn(prediction.shape, generator=generator)
    colors = color_indices(pattern)
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    _, tangent = torch.autograd.functional.jvp(
        lambda value: adc_cfa_projection(value, packed, colors, wb), prediction, direction
    )
    # Learned demosaicing can change unmeasured colors, while the measured
    # output samples remain fixed under a prediction perturbation.
    assert torch.isfinite(tangent).all() and tangent.norm() > 1
    # WB rescaling and cancellation round in FP32. Bound the derivative
    # residual relative to the supplied direction, not sensor-code units.
    rounding = torch.finfo(direction.dtype).eps * float(direction.abs().max())
    torch.testing.assert_close(
        mosaic(tangent, colors), torch.zeros_like(packed), rtol=0, atol=rounding
    )
