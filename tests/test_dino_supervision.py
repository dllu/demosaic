"""Feature gradients reach RGB only, and incompatible continuation is rejected."""

from types import SimpleNamespace

import pytest
import torch
from torch import nn

from demosaic.dino_supervision import (
    POLICY,
    feature_options,
    require_resume_features,
    spatial_feature_loss,
)


def config(weight=0.1):
    return {
        "dino_feature_weight": weight,
        "dino_feature_policy": POLICY if weight else None,
        "model": {"dino": True, "dino_feature_fusion": "convnext-pyramid"},
        "camera_supervision": "sensor-valid-v1",
    }


def test_frozen_shared_first_stage_only_with_detached_target():
    stage = nn.Conv2d(3, 3, 1, bias=False)
    with torch.no_grad():
        stage.weight.copy_(torch.eye(3)[..., None, None])
    stage.requires_grad_(False)
    backbone = nn.Module()
    backbone.stages = nn.ModuleList([stage])
    backbone.eval()
    context = SimpleNamespace(
        backbone=backbone, mean=torch.zeros(1, 3, 1, 1), std=torch.ones(1, 3, 1, 1)
    )
    model = SimpleNamespace(context=context)
    observed = []
    stage.register_forward_pre_hook(
        lambda module, args: observed.append((torch.is_grad_enabled(), args[0].requires_grad))
    )
    pred = torch.full((1, 3, 16, 24), 0.2, requires_grad=True)
    target = torch.full_like(pred, 0.21, requires_grad=True)
    wb = torch.ones(1, 3)
    matrix = torch.eye(3)[None]
    loss = spatial_feature_loss(model, pred, {"sensor_target": target, "wb": wb, "matrix": matrix})
    loss.backward()
    assert observed == [(False, False), (True, True)]
    assert pred.grad is not None and torch.isfinite(pred.grad).all() and (pred.grad < 0).all()
    assert target.grad is None and stage.weight.grad is None


@pytest.mark.parametrize(
    "change",
    [
        {"dino_feature_weight": 0.2},
        {"dino_feature_policy": "unknown"},
        {"noise_pair_draws": 2},
        {"forward_patch_size": 128},
        {"optimizer_forward_groups": 2},
    ],
)
def test_changed_weight_policy_or_batch_layout_is_rejected(change):
    previous = config()
    with pytest.raises(ValueError):
        require_resume_features(previous, {**previous, **change})


def test_legacy_zero_is_compatible_and_inactive_policy_is_rejected():
    require_resume_features({}, config(0))
    with pytest.raises(ValueError):
        feature_options({"dino_feature_weight": 0, "dino_feature_policy": POLICY})
    with pytest.raises(ValueError):
        feature_options(config(float("nan")))
