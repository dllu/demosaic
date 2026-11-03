from copy import deepcopy
from types import SimpleNamespace

import pytest
import torch
from torch import nn

from demosaic.raw_spatial_training import require_resume_spatial_lr, spatial_lr_multiplier
from demosaic.train import make_optimizer, set_learning_rate


class SmallModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.config = SimpleNamespace(
            raw_spatial_features=True,
            late_rgb_refinement="none",
            raw_directional_residual=False,
            raw_spectral_residual=False,
            raw_frequency_features=False,
            raw_global_features=False,
        )
        self.pretrained_rgb = nn.Module()
        self.pretrained_rgb.raw_spatial = nn.Linear(2, 2, bias=False)
        self.trunk = nn.Linear(2, 2, bias=False)
        self.encoder = nn.Linear(2, 2, bias=False).requires_grad_(False)


def options(multiplier=100):
    return {
        "lr": 1e-5,
        "model": {"raw_spatial_features": True},
        "raw_spatial_lr_multiplier": multiplier,
    }


def test_scheduled_groups_and_adam_resume_preserve_continuation():
    torch.manual_seed(145)
    model = SmallModel()
    optimizer = make_optimizer(model, options())
    branch = {id(p) for p in model.pretrained_rgb.raw_spatial.parameters()}
    groups = [{id(p) for p in group["params"]} for group in optimizer.param_groups]
    assert groups[1] == branch
    assert not groups[0] & groups[1]
    assert set.union(*groups) == {id(p) for p in model.parameters() if p.requires_grad}

    def update(m, opt, lr):
        set_learning_rate(opt, lr)
        opt.zero_grad()
        x = torch.tensor([[0.2, -0.3]])
        (m.trunk(x) + m.pretrained_rgb.raw_spatial(x)).square().sum().backward()
        opt.step()

    encoder = model.encoder.weight.detach().clone()
    update(model, optimizer, 2e-6)
    assert [g["lr"] for g in optimizer.param_groups] == pytest.approx([2e-6, 2e-4])
    restored = deepcopy(model)
    resumed = make_optimizer(restored, options())
    resumed.load_state_dict(deepcopy(optimizer.state_dict()))
    update(model, optimizer, 1e-6)
    update(restored, resumed, 1e-6)
    assert all(torch.equal(a, b) for a, b in zip(model.parameters(), restored.parameters()))
    assert torch.equal(model.encoder.weight, encoder)
    assert len(resumed.state) == 2


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "100", None])
def test_invalid_multiplier_rejected(value):
    with pytest.raises(ValueError, match="Spatial"):
        spatial_lr_multiplier(options(value))


def test_missing_or_frozen_branch_rejected():
    model = SmallModel()
    with pytest.raises(ValueError, match="requires RAW spatial"):
        make_optimizer(model, {"raw_spatial_lr_multiplier": 100})
    model.config.raw_spatial_features = False
    with pytest.raises(ValueError, match="requires RAW spatial"):
        make_optimizer(model, options())
    model.config.raw_spatial_features = True
    model.pretrained_rgb.raw_spatial.requires_grad_(False)
    with pytest.raises(ValueError, match="trainable branch"):
        make_optimizer(model, options())


@pytest.mark.parametrize(
    "key",
    [
        "phase_lr_multiplier",
        "raw_directional_lr_multiplier",
        "raw_spectral_lr_multiplier",
        "raw_frequency_lr_multiplier",
        "late_rgb_lr_multiplier",
    ],
)
def test_conflicting_groups_rejected(key):
    with pytest.raises(ValueError, match="cannot combine"):
        spatial_lr_multiplier({**options(), key: 2})


def test_resume_rate_change_rejected_and_legacy_defaults_unchanged():
    require_resume_spatial_lr({}, {"raw_spatial_lr_multiplier": 1})
    with pytest.raises(ValueError, match="Resume spatial"):
        require_resume_spatial_lr(options(), options(1))
    model = SmallModel()
    default = make_optimizer(model, {})
    explicit = make_optimizer(model, options(1))
    assert len(default.param_groups) == len(explicit.param_groups) == 1
    assert [id(p) for p in default.param_groups[0]["params"]] == [
        id(p) for p in explicit.param_groups[0]["params"]
    ]
