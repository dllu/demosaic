from copy import deepcopy

import pytest
import torch

from demosaic.inference import load_checkpoint
from demosaic.model import DinoContext, JointDemosaic, ModelConfig


@pytest.fixture
def tiny_input_backbone(monkeypatch):
    from transformers import AutoModel, DINOv3ViTConfig, DINOv3ViTModel

    torch.manual_seed(21)
    backbone = DINOv3ViTModel(
        DINOv3ViTConfig(
            hidden_size=32,
            num_hidden_layers=3,
            num_attention_heads=2,
            intermediate_size=64,
            layerscale_value=1.0,
        )
    ).eval()
    monkeypatch.setattr(AutoModel, "from_pretrained", lambda *args, **kwargs: deepcopy(backbone))


def test_identity_preserves_common_weights_rng_and_rectangular_features(tiny_input_backbone):
    models, states = [], []
    for enabled in [False, True]:
        torch.manual_seed(9)
        model = JointDemosaic(
            ModelConfig(
                dino=True,
                dino_input_adapter=enabled,
                width=4,
                encoder_blocks=(1,),
                decoder_blocks=(1,),
                middle_blocks=1,
            )
        ).eval()
        states.append(torch.get_rng_state())
        models.append(model)
    torch.testing.assert_close(*states, rtol=0, atol=0)
    control, adapted = (m.restoration_state_dict() for m in models)
    assert set(control) == {k for k in adapted if not k.startswith("context.input_adapter.")}
    for name, value in control.items():
        torch.testing.assert_close(value, adapted[name], rtol=0, atol=0)
    with torch.no_grad():
        for model in models:
            model.context.gate.fill_(0.2)
        preview = torch.rand(2, 3, 33, 49)
        outputs = [m.context(preview, (5, 7)) for m in models]
    torch.testing.assert_close(*outputs, rtol=0, atol=0)


@pytest.mark.parametrize("rank", [0, 2])
def test_gradient_crosses_frozen_encoder_to_input_adapter(tiny_input_backbone, rank):
    net = DinoContext(ModelConfig(dino=True, dino_input_adapter=True, dino_lora_rank=rank), 8)
    with torch.no_grad():
        net.gate.fill_(0.2)
    original = {
        k: p.detach().clone() for k, p in net.backbone.named_parameters() if not p.requires_grad
    }
    optimizer = torch.optim.AdamW([p for p in net.parameters() if p.requires_grad], lr=0.01)
    net.train()
    assert not net.backbone.training and net.input_adapter.training
    preview = torch.rand(2, 3, 32, 48)
    for step in range(2):
        optimizer.zero_grad(set_to_none=True)
        net(preview, (4, 6)).square().mean().backward()
        assert net.input_adapter.layers[-1].weight.grad.abs().sum() > 0
        if step:
            assert net.input_adapter.layers[0].weight.grad.abs().sum() > 0
        assert all(
            p.grad is not None and torch.isfinite(p.grad).all()
            for p in net.input_adapter.parameters()
        )
        assert all(p.grad is None for p in net.backbone.parameters() if not p.requires_grad)
        optimizer.step()
    for name, param in net.backbone.named_parameters():
        if name in original:
            torch.testing.assert_close(param, original[name], rtol=0, atol=0)


def test_learned_input_survives_portable_load_and_missing_weights_fail(
    tiny_input_backbone, tmp_path
):
    model = JointDemosaic(
        ModelConfig(
            dino=True,
            dino_input_adapter=True,
            width=4,
            encoder_blocks=(1,),
            decoder_blocks=(1,),
            middle_blocks=1,
        )
    ).eval()
    with torch.no_grad():
        model.context.gate.fill_(0.2)
        model.context.input_adapter.layers[-1].weight.normal_(std=0.01)
    state = model.restoration_state_dict()
    assert not any(k.startswith("context.backbone.") for k in state)
    path = tmp_path / "adapted.pt"
    torch.save({"model_config": model.config.to_dict(), "model": state, "step": 2}, path)
    restored, _ = load_checkpoint(path)
    with torch.no_grad():
        preview = torch.rand(1, 3, 32, 48)
        expected = model.context(preview, (4, 6))
        actual = restored.context(preview, (4, 6))
    torch.testing.assert_close(expected, actual, rtol=0, atol=0)
    del state["context.input_adapter.layers.4.weight"]
    torch.save({"model_config": model.config.to_dict(), "model": state, "step": 2}, path)
    with pytest.raises(ValueError, match="Incompatible checkpoint"):
        load_checkpoint(path)


@pytest.mark.parametrize("value", [1, "true", None])
def test_input_adapter_requires_boolean(value):
    with pytest.raises(ValueError, match="boolean"):
        JointDemosaic(ModelConfig(dino_input_adapter=value))


def test_input_adapter_requires_dino():
    with pytest.raises(ValueError, match="requires DINO"):
        JointDemosaic(ModelConfig(dino_input_adapter=True))
