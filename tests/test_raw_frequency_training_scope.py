import pytest
import torch

from demosaic.cfa import color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.train import make_optimizer, update_ema, validate_raw_frequency_only


def make_model(enabled=True):
    return JointDemosaic(
        ModelConfig(
            restoration_backbone="pretrained-rgb",
            width=64,
            camera_conditioning=True,
            variance_stabilization=True,
            physical_anchors=True,
            raw_frequency_features=enabled,
        )
    )


@pytest.mark.parametrize("amp", [False, True])
def test_frequency_only_training_preserves_common_weights_ema_and_flat_outputs(amp):
    torch.manual_seed(81)
    model = make_model()
    model.set_noise(0.001, 1e-5)
    optimizer = make_optimizer(model, {"raw_frequency_only": True, "lr": 0.001})
    branch = model.pretrained_rgb.raw_frequency
    selected = {id(p) for p in branch.parameters()}
    assert {id(p) for p in model.parameters() if p.requires_grad} == selected
    assert {id(p) for group in optimizer.param_groups for p in group["params"]} == selected
    common = {
        key: value.detach().clone()
        for key, value in model.restoration_state_dict().items()
        if not key.startswith("pretrained_rgb.raw_frequency.")
    }
    ema = {key: value.detach().clone() for key, value in model.restoration_state_dict().items()}
    colors = torch.stack([color_indices(p) for p in ("RGGB", "BGGR", "GRBG", "GBRG")])
    flat = torch.tensor([0.08, 0.18, 0.35])[colors][:, :, None, None].expand(4, 4, 10, 12)
    variance = torch.full_like(flat, 0.0003)
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        before_flat = model(flat, variance, colors, auxiliary=True)
    generator = torch.Generator().manual_seed(82)
    raw = torch.rand(1, 4, 10, 12, generator=generator) * 0.5
    target = torch.rand(1, 3, 20, 24, generator=generator)
    noise = torch.full_like(raw, 0.0003)
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
    assert len(optimizer.state) == 5
    assert all(torch.isfinite(p).all() for p in branch.parameters())
    for key, expected in common.items():
        assert torch.equal(model.restoration_state_dict()[key], expected), key
        assert torch.equal(ema[key], expected), key
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        after_flat = model(flat, variance, colors, auxiliary=True)
        after = model(raw, noise, colors[0])
    assert all(torch.equal(a, b) for a, b in zip(before_flat, after_flat, strict=True))
    assert not torch.equal(first, after)
    assert branch.project.weight.count_nonzero()
    assert not torch.equal(
        ema["pretrained_rgb.raw_frequency.project.weight"], torch.zeros_like(branch.project.weight)
    )


@pytest.mark.parametrize("value", [1, "true", None])
def test_frequency_only_requires_boolean(value):
    with pytest.raises(ValueError, match="must be a boolean"):
        validate_raw_frequency_only({"raw_frequency_only": value})


@pytest.mark.parametrize(
    "other",
    [
        "raw_kernel_only",
        "refiner_only",
        "coarse_refiner_only",
        "pyramid_refiner_only",
        "late_rgb_only",
    ],
)
def test_frequency_only_rejects_other_training_scopes(other):
    with pytest.raises(ValueError, match="cannot combine"):
        validate_raw_frequency_only({"raw_frequency_only": True, other: True})


def test_frequency_only_requires_frequency_adapter():
    with pytest.raises(ValueError, match="requires RAW frequency features"):
        make_optimizer(make_model(False), {"raw_frequency_only": True})


def test_frequency_only_defaults_to_full_existing_training_scope():
    model = make_model()
    make_optimizer(model, {})
    assert all(p.requires_grad for p in model.parameters())
    assert validate_raw_frequency_only({}) is False
