import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.raw_global_training import (
    require_resume_raw_global_scope,
    validate_raw_global_only,
)
from demosaic.train import make_optimizer, update_ema

PREFIX = "pretrained_rgb.raw_global."


def options(enabled=True, mode="cosine-rms-v2", only=True):
    return {
        "raw_global_only": only,
        "lr": 0.001,
        "model": {
            "restoration_backbone": "pretrained-rgb",
            "width": 64,
            "camera_conditioning": True,
            "variance_stabilization": True,
            "physical_anchors": True,
            "raw_global_features": enabled,
            "raw_global_conditioning": mode if enabled else "legacy-v1",
        },
    }


@pytest.mark.parametrize("amp", [False, True])
@pytest.mark.parametrize("mode", ["legacy-v1", "cosine-rms-v2"])
def test_branch_training_changes_detail_preserves_parent_ema_and_flat_function(amp, mode):
    torch.manual_seed(138)
    cfg = options(mode=mode)
    model = JointDemosaic(ModelConfig(**cfg["model"]))
    model.set_noise(0.001, 1e-5)
    optimizer = make_optimizer(model, cfg)
    branch = model.pretrained_rgb.raw_global
    selected = {id(p) for p in branch.parameters()}
    assert len(selected) == 18
    assert {id(p) for p in model.parameters() if p.requires_grad} == selected
    assert {id(p) for g in optimizer.param_groups for p in g["params"]} == selected
    common = {
        k: v.detach().clone()
        for k, v in model.restoration_state_dict().items()
        if not k.startswith(PREFIX)
    }
    ema = {k: v.detach().clone() for k, v in model.restoration_state_dict().items()}
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    flat = torch.tensor([0.08, 0.18, 0.35])[colors][:, :, None, None].expand(4, 4, 10, 12)
    variance = torch.full_like(flat, 0.0003)
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        before_flat = model(flat, variance, colors, auxiliary=True)
    gen = torch.Generator().manual_seed(1381)
    raw = torch.rand(1, 4, 10, 12, generator=gen) * 0.5
    noise = torch.full_like(raw, 0.0003)
    target = torch.rand(1, 3, 20, 24, generator=gen)
    first = None
    for _ in range(3):
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
            output = model(raw, noise, colors[0])
        if first is None:
            first = output.detach().clone()
        (output - target).square().mean().backward()
        assert branch.project.weight.grad.count_nonzero()
        assert all(p.grad is None for p in model.parameters() if id(p) not in selected)
        optimizer.step()
        update_ema(model, ema, 0.9, trainable_only=True)
    assert len(optimizer.state) == 18
    for key, value in common.items():
        assert torch.equal(model.restoration_state_dict()[key], value), key
        assert torch.equal(ema[key], value), key
    assert all(torch.isfinite(p).all() for p in branch.parameters())
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        after_flat = model(flat, variance, colors, auxiliary=True)
        after = model(raw, noise, colors[0])
    assert all(torch.equal(a, b) for a, b in zip(before_flat, after_flat, strict=True))
    assert not torch.equal(first, after)
    assert ema[PREFIX + "project.weight"].count_nonzero()


@pytest.mark.parametrize("value", [1, "true", None])
def test_nonboolean_scope_rejected(value):
    with pytest.raises(ValueError, match="must be a boolean"):
        validate_raw_global_only({"raw_global_only": value})


@pytest.mark.parametrize(
    "other",
    [
        "raw_kernel_only",
        "refiner_only",
        "coarse_refiner_only",
        "pyramid_refiner_only",
        "late_rgb_only",
        "raw_frequency_only",
    ],
)
def test_conflicting_scope_rejected(other):
    cfg = options()
    cfg[other] = True
    with pytest.raises(ValueError, match="cannot combine"):
        validate_raw_global_only(cfg)


def test_scope_requires_enabled_branch_in_config_and_actual_model():
    with pytest.raises(ValueError, match="requires RAW global features"):
        validate_raw_global_only(options(enabled=False))
    model = JointDemosaic(ModelConfig(**options(enabled=False)["model"]))
    with pytest.raises(ValueError, match="requires RAW global features"):
        make_optimizer(model, options())


@pytest.mark.parametrize("previous,current", [(False, True), (True, False), (1, True)])
def test_resume_cannot_change_scope(previous, current):
    a, b = options(only=previous), options(only=current)
    with pytest.raises(ValueError, match="RAW global"):
        require_resume_raw_global_scope(a, b)


def test_missing_scope_keeps_existing_joint_optimizer_and_resume():
    cfg = options(only=False)
    cfg.pop("raw_global_only")
    model = JointDemosaic(ModelConfig(**cfg["model"]))
    optimizer = make_optimizer(model, cfg)
    assert all(p.requires_grad for p in model.parameters())
    assert {id(p) for g in optimizer.param_groups for p in g["params"]} == {
        id(p) for p in model.parameters()
    }
    assert validate_raw_global_only({}) is False
    require_resume_raw_global_scope({}, {"raw_global_only": False})
