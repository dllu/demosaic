import json
from copy import deepcopy

import numpy as np
import pytest
import torch
import yaml
from torch import nn

from demosaic.cfa import PATTERNS, color_indices
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import PretrainedRgbDemosaic


@pytest.mark.parametrize("scale", [1, 2])
def test_parent_forward_and_trainable_tensors_are_exact(scale):
    torch.manual_seed(7)
    old = PretrainedRgbDemosaic(stabilized=True, physical_anchors=True, processing_scale=scale)
    with torch.no_grad():
        old.measurement_adapter.weight.normal_(std=0.01)
        old.measurement_adapter.bias.normal_(std=0.01)
    centered = PretrainedRgbDemosaic(
        stabilized=True, physical_anchors=True, processing_scale=scale, center_camera_matrix=True
    )
    missing, unexpected = centered.load_state_dict(old.state_dict(), strict=False)
    assert missing == ["camera_matrix_reference"] and not unexpected
    centered.initialize_camera_matrix_reference()
    assert dict(old.named_parameters()).keys() == dict(centered.named_parameters()).keys()
    for name, value in old.named_parameters():
        torch.testing.assert_close(value, dict(centered.named_parameters())[name], rtol=0, atol=0)
    assert not centered.camera_matrix_reference.requires_grad
    assert "camera_matrix_reference" not in old.state_dict()
    condition = torch.randn(2, 21, 7, 9)
    torch.testing.assert_close(
        old.project_measurements(condition),
        centered.project_measurements(condition),
        rtol=0,
        atol=0,
    )
    raw = torch.rand(4, 4, 16, 16) * 0.2
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    with torch.no_grad():
        old.set_noise(0.0, 0.0)
        centered.set_noise(0.0, 0.0)
        a = old(raw, torch.zeros_like(raw), colors)
        b = centered(raw, torch.zeros_like(raw), colors)
    torch.testing.assert_close(a, b, rtol=0, atol=0)
    with pytest.raises(ValueError, match="disabled"):
        old.initialize_camera_matrix_reference()


def test_neutral_matrix_cannot_drive_diagonal_weight_updates_but_deltas_remain():
    net = PretrainedRgbDemosaic(center_camera_matrix=True)
    with torch.no_grad():
        net.measurement_adapter.weight.normal_(std=0.02)
    net.initialize_camera_matrix_reference()
    reference = net.camera_matrix_reference.clone()
    condition = torch.randn(1, 21, 4, 4)
    condition[:, 12:] = 0
    condition[:, [12, 16, 20]] = 1
    net.project_measurements(condition).sum().backward()
    gradient = net.measurement_adapter.weight.grad
    torch.testing.assert_close(
        gradient[:, [12, 16, 20]], torch.zeros_like(gradient[:, [12, 16, 20]]), rtol=0, atol=0
    )
    assert gradient[:, :12].abs().sum() > 0
    net.zero_grad(set_to_none=True)
    changed = condition.clone()
    changed[:, 12] += 0.25
    assert not torch.equal(net.project_measurements(condition), net.project_measurements(changed))
    net.project_measurements(changed).sum().backward()
    torch.testing.assert_close(
        net.measurement_adapter.weight.grad[:, 12], torch.full((64, 1, 1), 4.0)
    )
    torch.optim.SGD(net.parameters(), lr=0.001).step()
    torch.testing.assert_close(net.camera_matrix_reference, reference, rtol=0, atol=0)


def test_reference_survives_portable_checkpoint_and_is_required(tmp_path, monkeypatch):
    config = ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        rgb_center_camera_matrix=True,
    )
    model = JointDemosaic(config)
    with torch.no_grad():
        model.pretrained_rgb.measurement_adapter.weight.normal_(std=0.01)
    model.pretrained_rgb.initialize_camera_matrix_reference()
    with torch.no_grad():
        model.pretrained_rgb.measurement_adapter.weight[:, 12] += 0.01
    state = {"model_config": config.to_dict(), "model": model.restoration_state_dict(), "step": 1}
    path = tmp_path / "model.pt"
    torch.save(state, path)
    restored, _ = load_checkpoint(path)
    condition = torch.randn(1, 21, 5, 6)
    torch.testing.assert_close(
        model.pretrained_rgb.project_measurements(condition),
        restored.pretrained_rgb.project_measurements(condition),
        rtol=0,
        atol=0,
    )
    corrupt = deepcopy(state)
    del corrupt["model"]["pretrained_rgb.camera_matrix_reference"]
    monkeypatch.setattr(torch, "load", lambda *args, **kwargs: corrupt)
    with pytest.raises(ValueError, match="Incompatible checkpoint"):
        load_checkpoint(path)


def test_old_parent_initialization_and_resume_preserve_fixed_reference(tmp_path, monkeypatch):
    import demosaic.pretrained_rgb as rgb_module
    from demosaic.train import train

    class TinyTrunk(nn.Module):
        def __init__(self, **kwargs):
            super().__init__()

        def forward(self, rgb, noise, *, head_offset=None, middle_offset=None):
            return rgb + head_offset[:, :3]

    monkeypatch.setattr(rgb_module, "RgbRestorationTrunk", TinyTrunk)
    model_config = ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        variance_stabilization=True,
        physical_anchors=True,
    )
    parent = JointDemosaic(model_config)
    with torch.no_grad():
        parent.pretrained_rgb.measurement_adapter.weight.normal_(std=0.001)
    reference = (
        parent.pretrained_rgb.measurement_adapter.weight[:, [12, 16, 20], 0, 0].detach().clone()
    )
    checkpoint = tmp_path / "parent.pt"
    torch.save(
        {
            "model_config": model_config.to_dict(),
            "model": parent.restoration_state_dict(),
            "step": 0,
        },
        checkpoint,
    )
    np.save(
        tmp_path / "clean.npy",
        np.random.default_rng(3).integers(0, 65536, (40, 40, 3), dtype=np.uint16),
    )
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps({"id": s, "cache": "clean.npy", "split": s}) for s in ["train", "val"])
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
        "model": {**model_config.to_dict(), "rgb_center_camera_matrix": True},
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    full = torch.load(train(path, initialize=checkpoint), weights_only=True)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    interrupted = train(path, initialize=checkpoint, stop_after=2)
    actual = torch.load(train(path, resume=interrupted), weights_only=True)
    for field in ["model", "ema"]:
        for name, value in full[field].items():
            torch.testing.assert_close(value, actual[field][name], rtol=0, atol=0)
    torch.testing.assert_close(
        actual["model"]["pretrained_rgb.camera_matrix_reference"], reference, rtol=0, atol=0
    )
    assert actual["config"]["initialized_from"]["camera_matrix_centering"]
    assert torch.equal(full["torch_rng"], actual["torch_rng"])
    for key, values in full["optimizer"]["state"].items():
        for field, value in values.items():
            torch.testing.assert_close(
                value, actual["optimizer"]["state"][key][field], rtol=0, atol=0
            )
    del actual["model"]["pretrained_rgb.camera_matrix_reference"]
    actual.pop("ema")
    corrupt = tmp_path / "corrupt.pt"
    torch.save(actual, corrupt)
    config["run"] = str(tmp_path / "bad")
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="Incompatible initialization"):
        train(path, initialize=corrupt, stop_after=1)


def test_centering_requires_pretrained_rgb():
    with pytest.raises(ValueError, match="pretrained RGB"):
        JointDemosaic(ModelConfig(rgb_center_camera_matrix=True))
