from copy import deepcopy

import pytest
import torch
from torch.nn import functional as F

from demosaic.cfa import PATTERNS, bilinear, color_indices, mosaic
from demosaic.dino_pyramid import DinoPackedContext
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.train import expand_stem


def config(**options):
    return ModelConfig(
        **(
            {
                "restoration_backbone": "packed-isotropic",
                "camera_conditioning": True,
                "width": 8,
                "isotropic_groups": 2,
                "isotropic_blocks": 1,
                "isotropic_local_width": 8,
            }
            | options
        )
    )


@pytest.fixture
def tiny_convnext(monkeypatch):
    from transformers import AutoModel, DINOv3ConvNextConfig, DINOv3ConvNextModel

    torch.manual_seed(21)
    backbone = DINOv3ConvNextModel(
        DINOv3ConvNextConfig(hidden_sizes=[8, 16, 24, 32], depths=[1, 1, 1, 1])
    ).eval()
    monkeypatch.setattr(AutoModel, "from_pretrained", lambda *a, **k: deepcopy(backbone))
    return backbone


def observation():
    torch.manual_seed(11)
    raw = torch.rand(4, 4, 17, 25) * 0.6 - 0.02
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    return raw, raw.clamp_min(0) * 0.002 + 1e-5, colors


def test_initialization_preserves_fp32_signal_all_phases_and_odd_rectangles():
    net = JointDemosaic(config())
    raw, variance, colors = observation()
    captured = []
    handle = net.packed_isotropic.stem.register_forward_pre_hook(
        lambda _module, args: captured.append(args[0].detach().clone())
    )
    with torch.autocast("cpu", dtype=torch.bfloat16):
        predicted, auxiliary = net(raw, variance, colors, auxiliary=True)
    handle.remove()
    assert predicted.dtype == torch.float32 and predicted.shape == (4, 3, 34, 50)
    torch.testing.assert_close(predicted, bilinear(raw, colors), rtol=0, atol=0)
    torch.testing.assert_close(auxiliary, raw, rtol=0, atol=0)
    # Recover the entry samples from the quarter-resolution tensor. Distinct
    # phases/subpixels must survive, including at the padded odd borders.
    recovered = F.pixel_shuffle(captured[0][:, :16], 2)[..., :17, :25]
    torch.testing.assert_close(recovered, raw, rtol=0, atol=0)
    changed = raw.clone()
    changed[0, 3, 7, 12] += 1 / 65535
    with torch.autocast("cpu", dtype=torch.bfloat16):
        updated = net(changed, variance, colors)
    assert not torch.equal(predicted, updated)


def test_trainable_path_and_portable_reload(tmp_path):
    torch.manual_seed(9)
    net = JointDemosaic(config())
    raw, variance, colors = observation()
    target = torch.rand(4, 3, 34, 50)
    optimizer = torch.optim.AdamW(net.parameters(), lr=1e-3)
    initial = {name: value.detach().clone() for name, value in net.named_parameters()}
    for _ in range(3):
        optimizer.zero_grad(set_to_none=True)
        prediction, auxiliary = net(raw, variance, colors, auxiliary=True)
        torch.testing.assert_close(auxiliary, mosaic(prediction, colors), rtol=0, atol=0)
        (prediction - target).square().mean().backward()
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in net.parameters())
        optimizer.step()
    assert all(not torch.equal(value, initial[name]) for name, value in net.named_parameters())
    expected = net(raw, variance, colors).detach()
    path = tmp_path / "model.pt"
    state = net.restoration_state_dict()
    torch.save({"model_config": net.config.to_dict(), "model": state}, path)
    restored, _ = load_checkpoint(path)
    torch.testing.assert_close(restored(raw, variance, colors), expected, rtol=0, atol=0)
    del state["packed_isotropic.stem.weight"]
    torch.save({"model_config": net.config.to_dict(), "model": state}, path)
    with pytest.raises(ValueError, match="Incompatible checkpoint"):
        load_checkpoint(path)


@pytest.mark.parametrize(
    "units", [{}, {"isotropic_raw_gain": 32, "isotropic_residual_scale": 1 / 32}]
)
def test_zero_context_preserves_common_weights_rng_and_output(tiny_convnext, units):
    nets, rng = [], []
    for enabled in (False, True):
        torch.manual_seed(5)
        net = JointDemosaic(
            config(
                dino=enabled,
                dino_feature_fusion="packed-convnext" if enabled else "bottleneck",
                **units,
            )
        )
        # Open the output head to test the entire context path at initialization.
        with torch.no_grad():
            net.packed_isotropic.head.weight.fill_(0.001)
        nets.append(net)
        rng.append(torch.get_rng_state())
    torch.testing.assert_close(*rng, rtol=0, atol=0)
    for key, value in nets[0].restoration_state_dict().items():
        torch.testing.assert_close(value, nets[1].state_dict()[key], rtol=0, atol=0)
    args = observation()
    predictions = [net(*args) for net in nets]
    torch.testing.assert_close(*predictions, rtol=0, atol=0)
    for prediction in predictions:
        prediction.square().mean().backward()
    for a, b in zip(nets[0].packed_isotropic.parameters(), nets[1].packed_isotropic.parameters()):
        torch.testing.assert_close(a.grad, b.grad, rtol=0, atol=0)
    assert nets[1].context.gate.grad.abs().sum() > 0


def test_dino_learns_all_scales_without_backbone_updates_and_preserves_extent(tiny_convnext):
    options = config(dino=True, dino_feature_fusion="packed-convnext")
    net = DinoPackedContext(options).train()
    assert not net.backbone.training
    original = {name: value.detach().clone() for name, value in net.backbone.named_parameters()}
    optimizer = torch.optim.AdamW([p for p in net.parameters() if p.requires_grad], lr=0.01)
    preview = torch.rand(1, 3, 34, 50)
    for step in range(2):
        optimizer.zero_grad(set_to_none=True)
        output = net(preview, (9, 13))
        assert output.shape == (1, 8, 9, 13)
        (output - 1).square().mean().backward()
        assert net.gate.grad.abs().sum() > 0
        if step:
            assert all(m.weight.grad.abs().sum() > 0 for m in net.laterals)
            assert net.projection.weight.grad.abs().sum() > 0
        optimizer.step()
    assert all(p.grad is None for p in net.backbone.parameters())
    assert all(torch.equal(p, original[name]) for name, p in net.backbone.named_parameters())
    with torch.no_grad():
        a = net(preview, (9, 13))
        b = net(F.pad(preview, (0, 14, 0, 30), mode="replicate"), (16, 16))
    torch.testing.assert_close(a, b[..., :9, :13], rtol=0, atol=0)
    with pytest.raises(ValueError, match="quarter-resolution"):
        net(preview, (8, 12))


@pytest.mark.parametrize(
    "units", [{}, {"isotropic_raw_gain": 32, "isotropic_residual_scale": 1 / 32}]
)
def test_nonzero_dino_context_survives_portable_checkpoint(tiny_convnext, tmp_path, units):
    net = JointDemosaic(config(dino=True, dino_feature_fusion="packed-convnext", **units))
    with torch.no_grad():
        net.context.gate.fill_(0.1)
        net.packed_isotropic.head.weight.fill_(0.001)
    state = net.restoration_state_dict()
    assert not any(key.startswith("context.backbone.") for key in state)
    path = tmp_path / "dino.pt"
    torch.save({"model_config": net.config.to_dict(), "model": state}, path)
    restored, _ = load_checkpoint(path)
    with torch.no_grad():
        torch.testing.assert_close(net(*observation()), restored(*observation()), rtol=0, atol=0)


@pytest.mark.parametrize(
    "values",
    [
        {"width": 0},
        {"isotropic_blocks": -1},
        {"isotropic_groups": 1.5},
        {"isotropic_local_width": True},
        {"camera_conditioning": False},
        {"physical_fp32": False},
        {"baseline": "wiener-malvar"},
        {"noise_refinement": True},
        {"variance_stabilization": True},
        {"dino": True},
        {"dino_feature_fusion": "packed-convnext"},
        {"restoration_backbone": "local", "dino": True, "dino_feature_fusion": "packed-convnext"},
    ],
)
def test_rejects_incompatible_options_before_loading(values):
    with pytest.raises(ValueError):
        JointDemosaic(config(**values))


def test_rejects_rgb_warm_start_and_training_normalization_mask():
    net = JointDemosaic(config())
    with pytest.raises(ValueError, match="same backbone"):
        expand_stem({}, ModelConfig(restoration_backbone="pretrained-rgb").to_dict(), net)
    with pytest.raises(ValueError, match="Normalization augmentation"):
        net(*observation(), normalization_mask=torch.ones(4, dtype=torch.bool))
