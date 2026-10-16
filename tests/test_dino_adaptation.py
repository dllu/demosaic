from copy import deepcopy

import pytest
import torch
from torch import nn

from demosaic.dino_adaptation import install_qv_adapters
from demosaic.inference import load_checkpoint
from demosaic.model import DinoContext, JointDemosaic, ModelConfig


@pytest.fixture
def tiny_backbone(monkeypatch):
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
    return backbone


def context(rank):
    return DinoContext(ModelConfig(dino=True, dino_lora_rank=rank), 8)


def test_zero_updates_preserve_features_and_default_portable_keys(tiny_backbone):
    original, adapted = context(0), context(2)
    adapted.adapter.load_state_dict(original.adapter.state_dict())
    with torch.no_grad():
        original.gate.fill_(0.2)
        adapted.gate.copy_(original.gate)
        preview = torch.rand(2, 3, 32, 48)
        a, b = (net(preview, (4, 6)) for net in [original, adapted])
    torch.testing.assert_close(a, b, rtol=0, atol=0)
    assert not any(k.startswith("lora.") for k in original.state_dict())
    assert len(adapted.lora) == 6
    assert sum(p.numel() for p in adapted.lora.parameters()) == 768


def test_gradients_reach_adapters_and_base_weights_stay_fixed(tiny_backbone):
    net = context(2).train()
    assert not net.backbone.training
    with torch.no_grad():
        net.gate.fill_(0.2)
    originals = {
        n: p.detach().clone() for n, p in net.backbone.named_parameters() if not p.requires_grad
    }
    optimizer = torch.optim.AdamW([p for p in net.parameters() if p.requires_grad], lr=0.01)
    preview = torch.rand(2, 3, 32, 32)
    net(preview, (4, 4)).square().mean().backward()
    assert all(p.grad is None for p in net.backbone.parameters() if not p.requires_grad)
    assert all(torch.isfinite(p.grad).all() for p in net.lora.parameters())
    assert sum(m.up.grad.abs().sum() for m in net.lora.values()) > 0
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    net(preview, (4, 4)).square().mean().backward()
    assert sum(m.down.grad.abs().sum() for m in net.lora.values()) > 0
    for n, p in net.backbone.named_parameters():
        if n in originals:
            torch.testing.assert_close(p, originals[n], rtol=0, atol=0)
    assert len({id(p) for group in optimizer.param_groups for p in group["params"]}) == sum(
        len(g["params"]) for g in optimizer.param_groups
    )


def test_nonzero_updates_survive_portable_checkpoint(tiny_backbone, tmp_path):
    model = JointDemosaic(
        ModelConfig(
            dino=True,
            dino_lora_rank=2,
            width=4,
            encoder_blocks=(1,),
            decoder_blocks=(1,),
            middle_blocks=1,
        )
    )
    with torch.no_grad():
        model.context.gate.fill_(0.2)
        for update in model.context.lora.values():
            update.up.normal_(std=0.01)
    state = model.restoration_state_dict()
    assert any(k.startswith("context.lora.") for k in state)
    assert not any(k.startswith("context.backbone.") for k in state)
    path = tmp_path / "model.pt"
    torch.save({"model_config": model.config.to_dict(), "model": state, "step": 1}, path)
    restored, _ = load_checkpoint(path)
    assert state.keys() == restored.restoration_state_dict().keys()
    for name, value in state.items():
        torch.testing.assert_close(value, restored.restoration_state_dict()[name], rtol=0, atol=0)
    with torch.no_grad():
        preview = torch.rand(1, 3, 32, 32)
        a = model.context(preview, (4, 4))
        b = restored.context(preview, (4, 4))
    torch.testing.assert_close(a, b, rtol=0, atol=0)
    del state["context.lora.layer000_q_proj.up"]
    torch.save({"model_config": model.config.to_dict(), "model": state, "step": 1}, path)
    with pytest.raises(ValueError, match="Incompatible checkpoint"):
        load_checkpoint(path)


@pytest.mark.parametrize("rank", [-1, 1.5, True])
def test_invalid_model_rank_is_rejected(rank):
    with pytest.raises(ValueError, match="rank"):
        JointDemosaic(ModelConfig(dino_lora_rank=rank))


def test_positive_rank_requires_context():
    with pytest.raises(ValueError, match="require DINO"):
        JointDemosaic(ModelConfig(dino_lora_rank=2))


def test_target_validation_precedes_mutation(tiny_backbone):
    tiny_backbone.layer[-1].attention.v_proj = nn.Identity()
    with pytest.raises(ValueError, match="Unsupported"):
        install_qv_adapters(tiny_backbone, 2)
    assert all(p.requires_grad for p in tiny_backbone.parameters())
    with pytest.raises(ValueError, match="rank"):
        install_qv_adapters(tiny_backbone, 1000)


@pytest.mark.parametrize("adaptation", ["lora", "input"])
def test_training_resume_preserves_adaptation_optimizer_ema_and_rng(
    tiny_backbone, tmp_path, adaptation
):
    import json

    import numpy as np
    import yaml

    from demosaic.train import train

    source = tmp_path / "clean.npy"
    np.save(source, np.random.default_rng(5).integers(0, 65536, (40, 40, 3), dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": split, "cache": source.name, "split": split})
            for split in ["train", "val"]
        )
    )
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "steps": 4,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 1,
        "min_available_gb": 0,
        "data_seed_per_step": True,
        "trace_observations": True,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "middle_blocks": 0,
            "decoder_blocks": [1],
            "attention": False,
            "dino": True,
            "dino_revision": "test-fixture",
            "dino_lora_rank": 2 if adaptation == "lora" else 0,
            "dino_input_adapter": adaptation == "input",
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    full = torch.load(train(path), weights_only=True)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    interrupted = train(path, stop_after=2)
    actual = torch.load(train(path, resume=interrupted), weights_only=True)
    assert full["step"] == actual["step"] == 4
    for field in ["model", "ema"]:
        assert full[field].keys() == actual[field].keys()
        for name, value in full[field].items():
            torch.testing.assert_close(value, actual[field][name], rtol=0, atol=0)
    learned_keys = (
        [k for k in actual["model"] if k.startswith("context.lora.") and k.endswith(".up")]
        if adaptation == "lora"
        else ["context.input_adapter.layers.4.weight"]
    )
    assert any(actual["model"][k].abs().sum() > 0 for k in learned_keys)
    assert full["optimizer"]["param_groups"] == actual["optimizer"]["param_groups"]
    for key, state in full["optimizer"]["state"].items():
        for field, value in state.items():
            torch.testing.assert_close(
                value, actual["optimizer"]["state"][key][field], rtol=0, atol=0
            )
    assert torch.equal(full["torch_rng"], actual["torch_rng"])
