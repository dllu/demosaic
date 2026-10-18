import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
import yaml

from demosaic.cfa import PATTERNS, bilinear, color_indices
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.packed_isotropic import PackedIsotropic
from demosaic.train import train


def config(**options):
    return ModelConfig(
        **(
            {
                "restoration_backbone": "packed-isotropic",
                "camera_conditioning": True,
                "width": 8,
                "isotropic_groups": 1,
                "isotropic_blocks": 1,
                "isotropic_local_width": 8,
            }
            | options
        )
    )


def observation():
    torch.manual_seed(11)
    raw = torch.rand(4, 4, 17, 25) * 0.6 - 0.02
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    return raw, raw.clamp_min(0) * 0.002 + 1e-6, colors


def diagnostic():
    directory = str(Path("scripts").absolute())
    sys.path.insert(0, directory)
    try:
        spec = importlib.util.spec_from_file_location(
            "isotropic_units_reference", Path("scripts/probe_raw_residual_units.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(directory)


def test_units_preserve_common_initial_state_rng_and_native16bit_signal():
    nets, rng = [], []
    for options in [{}, {"isotropic_raw_gain": 32, "isotropic_residual_scale": 1 / 32}]:
        torch.manual_seed(51)
        nets.append(JointDemosaic(config(**options)))
        rng.append(torch.get_rng_state())
    assert torch.equal(*rng)
    assert nets[0].state_dict().keys() == nets[1].state_dict().keys()
    assert all(
        torch.equal(value, nets[1].state_dict()[name])
        for name, value in nets[0].state_dict().items()
    )
    raw, variance, colors = observation()
    with torch.inference_mode(), torch.autocast("cpu", dtype=torch.bfloat16):
        expected = bilinear(raw, colors)
        for net in nets:
            output = net(raw, variance, colors)
            assert output.dtype == torch.float32 and torch.equal(output, expected)
        changed = raw.clone()
        changed[:, 3, 7, 12] += 1 / 65535
        updated = nets[1](changed, variance, colors)
        assert torch.equal(updated, bilinear(changed, colors))
        assert not torch.equal(updated, expected)


def test_configured_units_match_discarded_hook_predictions_gradients_and_adam_updates():
    reference = diagnostic()
    nets = []
    for options in [{}, {"isotropic_raw_gain": 32, "isotropic_residual_scale": 1 / 32}]:
        torch.manual_seed(51)
        net = JointDemosaic(config(**options))
        torch.nn.init.normal_(net.packed_isotropic.head.weight, std=0.002)
        nets.append(net)
    args = observation()
    optimizers = [torch.optim.AdamW(net.parameters(), lr=2e-4) for net in nets]
    target = torch.rand(4, 3, 34, 50)
    for _ in range(3):
        for optimizer in optimizers:
            optimizer.zero_grad(set_to_none=True)
        with reference.coordinates(nets[0], "gain32-residual32", {"shot": 0.002, "read": 1e-6}):
            expected = nets[0](*args)
        actual = nets[1](*args)
        assert torch.equal(expected, actual)
        for output in [expected, actual]:
            (output - target).square().mean().backward()
        for a, b in zip(nets[0].parameters(), nets[1].parameters(), strict=True):
            torch.testing.assert_close(a.grad, b.grad, rtol=0, atol=0)
        for optimizer in optimizers:
            torch.nn.utils.clip_grad_norm_(optimizer.param_groups[0]["params"], 1)
            optimizer.step()
        for name, value in nets[0].state_dict().items():
            assert torch.equal(value, nets[1].state_dict()[name])


def test_units_survive_portable_checkpoint_and_missing_fields_keep_legacy_defaults(tmp_path):
    cfg = config(isotropic_raw_gain=32, isotropic_residual_scale=1 / 32)
    net = JointDemosaic(cfg).eval()
    torch.nn.init.normal_(net.packed_isotropic.head.weight, std=0.002)
    path = tmp_path / "units.pt"
    torch.save({"model_config": cfg.to_dict(), "model": net.restoration_state_dict()}, path)
    restored, _ = load_checkpoint(path)
    assert restored.config.isotropic_raw_gain == 32
    assert restored.config.isotropic_residual_scale == 1 / 32
    with torch.inference_mode():
        assert torch.equal(net(*observation()), restored(*observation()))
    legacy = config().to_dict()
    del legacy["isotropic_raw_gain"], legacy["isotropic_residual_scale"]
    torch.save({"model_config": legacy, "model": net.restoration_state_dict()}, path)
    default, _ = load_checkpoint(path)
    assert default.config.isotropic_raw_gain == default.config.isotropic_residual_scale == 1
    control = JointDemosaic(config()).eval()
    control.load_state_dict(net.restoration_state_dict())
    with torch.inference_mode():
        assert torch.equal(default(*observation()), control(*observation()))


@pytest.mark.parametrize("field", ["isotropic_raw_gain", "isotropic_residual_scale"])
@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, "32"])
def test_invalid_units_rejected_before_model_construction(field, value):
    with pytest.raises(ValueError, match="finite and positive"):
        JointDemosaic(config(**{field: value}))


@pytest.mark.parametrize("field", ["isotropic_raw_gain", "isotropic_residual_scale"])
def test_nondefault_units_require_packed_backbone(field):
    with pytest.raises(ValueError, match="require the packed-isotropic"):
        JointDemosaic(ModelConfig(**{field: 32}))


def test_direct_backbone_rejects_nonphysical_units():
    with pytest.raises(ValueError, match="finite and positive"):
        PackedIsotropic(raw_gain=float("nan"))
    with pytest.raises(ValueError, match="finite and positive"):
        PackedIsotropic(residual_scale=0)


def test_actual_training_resume_preserves_units_weights_moments_and_rng(tmp_path):
    source = tmp_path / "clean.npy"
    np.save(source, np.random.default_rng(7).integers(0, 65536, (40, 40, 3), dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": split, "cache": source.name, "split": split})
            for split in ["train", "val"]
        )
    )
    recipe = {
        "manifest": str(manifest),
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "steps": 3,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "precision": "float32",
        "warmup_steps": 1,
        "checkpoint_every": 3,
        "log_every": 3,
        "min_available_gb": 0,
        "val_batches": 1,
        "model": config(isotropic_raw_gain=32, isotropic_residual_scale=1 / 32).to_dict(),
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(recipe))
    full = train(path)
    recipe["run"] = str(tmp_path / "interrupted")
    path.write_text(yaml.safe_dump(recipe))
    partial = train(path, stop_after=2)
    resumed = train(path, resume=partial)
    expected, actual = [torch.load(p, weights_only=True) for p in [full, resumed]]
    assert actual["model_config"]["isotropic_raw_gain"] == 32
    assert actual["model_config"]["isotropic_residual_scale"] == 1 / 32
    for kind in ["model", "ema"]:
        for name, value in expected[kind].items():
            assert torch.equal(value, actual[kind][name])
    for index, state in expected["optimizer"]["state"].items():
        for name, value in state.items():
            assert torch.equal(value, actual["optimizer"]["state"][index][name])
    assert torch.equal(expected["torch_rng"], actual["torch_rng"])
    assert expected["python_rng"] == actual["python_rng"]
    recipe["model"]["isotropic_raw_gain"] = 16
    path.write_text(yaml.safe_dump(recipe))
    with pytest.raises(ValueError, match="Resume model configuration differs"):
        train(path, resume=resumed)
