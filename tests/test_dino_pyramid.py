from copy import deepcopy

import pytest
import torch
from torch.nn import functional as F

from demosaic.cfa import color_indices
from demosaic.dino_pyramid import DinoPyramidContext
from demosaic.inference import load_checkpoint
from demosaic.model import DinoContext, JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import RgbRestorationTrunk


@pytest.fixture
def tiny_convnext(monkeypatch):
    from transformers import AutoModel, DINOv3ConvNextConfig, DINOv3ConvNextModel

    torch.manual_seed(21)
    backbone = DINOv3ConvNextModel(
        DINOv3ConvNextConfig(hidden_sizes=[8, 16, 24, 32], depths=[1, 1, 1, 1])
    ).eval()
    monkeypatch.setattr(AutoModel, "from_pretrained", lambda *args, **kwargs: deepcopy(backbone))
    return backbone


def config(**kwargs):
    values = {
        "restoration_backbone": "pretrained-rgb",
        "width": 64,
        "camera_conditioning": True,
        "rgb_middle_skip_fp32": True,
        "dino": True,
        "dino_feature_fusion": "convnext-pyramid",
    }
    return ModelConfig(**(values | kwargs))


def test_zero_branch_preserves_common_weights_rng_and_amp_values_gradients(tiny_convnext):
    models, rng = [], []
    for enabled in [False, True]:
        torch.manual_seed(9)
        models.append(
            JointDemosaic(
                config(
                    dino=enabled,
                    dino_feature_fusion="convnext-pyramid" if enabled else "bottleneck",
                )
            )
        )
        rng.append(torch.get_rng_state())
    torch.testing.assert_close(*rng, rtol=0, atol=0)
    for name, value in models[0].restoration_state_dict().items():
        torch.testing.assert_close(value, models[1].state_dict()[name], rtol=0, atol=0)
    raw = torch.rand(1, 4, 17, 25) * 0.3
    variance = torch.full_like(raw, 1e-4)
    predictions = []
    for model in models:
        with torch.autocast("cpu", dtype=torch.bfloat16):
            predictions.append(model(raw, variance, color_indices("GBRG")))
        predictions[-1].square().mean().backward()
    torch.testing.assert_close(*predictions, rtol=0, atol=0)
    for (_, a), (_, b) in zip(
        models[0].pretrained_rgb.named_parameters(), models[1].pretrained_rgb.named_parameters()
    ):
        torch.testing.assert_close(a.grad, b.grad, rtol=0, atol=0)
    assert sum(g.grad.abs().sum() for g in models[1].context.gates) > 0


def test_all_levels_learn_while_encoder_stays_fixed_and_eval(tiny_convnext):
    net = DinoPyramidContext(config()).train()
    assert not net.backbone.training and net.laterals.training
    originals = {k: p.detach().clone() for k, p in net.backbone.named_parameters()}
    optimizer = torch.optim.AdamW([p for p in net.parameters() if p.requires_grad], lr=0.01)
    preview = torch.rand(1, 3, 33, 49)
    for step in range(2):
        optimizer.zero_grad(set_to_none=True)
        offsets = net(preview, (5, 7))
        assert [list(x.shape) for x in offsets] == [
            [1, 128, 20, 28],
            [1, 256, 10, 14],
            [1, 512, 5, 7],
        ]
        sum((x - 1).square().mean() for x in offsets).backward()
        assert all(g.grad.abs().sum() > 0 for g in net.gates)
        if step:
            assert all(m.weight.grad.abs().sum() > 0 for m in net.laterals)
            assert all(m.weight.grad.abs().sum() > 0 for m in net.projections)
        assert all(p.grad is None for p in net.backbone.parameters())
        assert all(
            p.grad is not None and torch.isfinite(p.grad).all()
            for p in net.parameters()
            if p.requires_grad
        )
        optimizer.step()
    for name, param in net.backbone.named_parameters():
        torch.testing.assert_close(param, originals[name], rtol=0, atol=0)


def test_padding_is_cropped_without_squeezing_feature_coordinates(tiny_convnext):
    net = DinoPyramidContext(config()).eval()
    preview = torch.rand(1, 3, 33, 49)
    with torch.no_grad():
        for gate in net.gates:
            gate.fill_(0.2)
        a = net(preview, (5, 7))
        b = net(F.pad(preview, (0, 15, 0, 31), mode="replicate"), (8, 8))
    for crop, padded in zip(a, b):
        torch.testing.assert_close(
            crop, padded[..., : crop.shape[-2], : crop.shape[-1]], rtol=0, atol=0
        )
    with pytest.raises(ValueError, match="padded extent"):
        net(preview, (4, 6))


def test_each_encoder_offset_enters_its_own_resolution():
    trunk = RgbRestorationTrunk(middle_skip_fp32=True)
    rgb, noise = torch.rand(1, 3, 16, 24), torch.ones(1, 1, 16, 24) * 0.01
    offsets = (torch.randn(1, 128, 8, 12), torch.randn(1, 256, 4, 6))
    recorded = []
    handles = [
        trunk.m_down2.register_forward_pre_hook(lambda _m, args: recorded.append(args[0].clone())),
        trunk.m_down3.register_forward_pre_hook(lambda _m, args: recorded.append(args[0].clone())),
    ]
    with torch.no_grad():
        x1 = trunk.m_head(torch.cat((rgb, noise), 1))
        x2 = trunk.m_down1(x1) + offsets[0]
        x3 = trunk.m_down2(x2) + offsets[1]
        recorded.clear()
        trunk(rgb, noise, encoder_offsets=offsets)
    for handle in handles:
        handle.remove()
    torch.testing.assert_close(recorded[0], x2, rtol=0, atol=0)
    torch.testing.assert_close(recorded[1], x3, rtol=0, atol=0)


def test_nonzero_pyramid_survives_portable_reload_and_missing_weights_fail(tiny_convnext, tmp_path):
    model = JointDemosaic(config()).eval()
    with torch.no_grad():
        for gate in model.context.gates:
            gate.fill_(0.1)
    state = model.restoration_state_dict()
    assert not any(k.startswith("context.backbone.") for k in state)
    path = tmp_path / "pyramid.pt"
    torch.save({"model_config": model.config.to_dict(), "model": state}, path)
    restored, _ = load_checkpoint(path)
    preview = torch.rand(1, 3, 33, 49)
    with torch.no_grad():
        for a, b in zip(model.context(preview, (5, 7)), restored.context(preview, (5, 7))):
            torch.testing.assert_close(a, b, rtol=0, atol=0)
    del state["context.laterals.0.weight"]
    torch.save({"model_config": model.config.to_dict(), "model": state}, path)
    with pytest.raises(ValueError, match="Incompatible checkpoint"):
        load_checkpoint(path)


def test_rejects_convnext_in_legacy_token_path(tiny_convnext):
    with pytest.raises(ValueError, match="dino_feature_fusion"):
        DinoContext(ModelConfig(dino=True), 8)


def test_rejects_nonconvnext_backbone(monkeypatch):
    from transformers import AutoModel, DINOv3ViTConfig, DINOv3ViTModel

    monkeypatch.setattr(
        AutoModel,
        "from_pretrained",
        lambda *a, **k: DINOv3ViTModel(
            DINOv3ViTConfig(
                hidden_size=8, num_hidden_layers=1, num_attention_heads=1, intermediate_size=8
            )
        ),
    )
    with pytest.raises(ValueError, match="DINOv3 ConvNeXt"):
        DinoPyramidContext(config())


@pytest.mark.parametrize(
    "values",
    [
        {"dino_feature_fusion": "unknown"},
        {"dino": False},
        {"restoration_backbone": "local", "rgb_middle_skip_fp32": False},
        {"rgb_processing_scale": 2},
        {"dino_lora_rank": 2},
        {"dino_input_adapter": True},
    ],
)
def test_rejects_incompatible_fusion_before_loading(values):
    with pytest.raises(ValueError, match="fusion|ConvNeXt pyramid"):
        JointDemosaic(config(**values))
