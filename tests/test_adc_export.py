import hashlib
import importlib.util
from pathlib import Path

import pytest
import torch

from demosaic.model import ModelConfig

spec = importlib.util.spec_from_file_location(
    "export_adc_cfa_projection",
    Path(__file__).resolve().parents[1] / "scripts/export_adc_cfa_projection.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def checkpoint(tmp_path, **overrides):
    config = ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        variance_stabilization=True,
    ).to_dict()
    config.update(overrides)
    path = tmp_path / "parent.pt"
    torch.save(
        {
            "model_config": config,
            "model": {"weight": torch.zeros(512)},
            "ema": {"weight": torch.arange(512) / 65535},
            "step": 7,
            "optimizer": {"ignored": True},
        },
        path,
    )
    return path, module.sha(path)


def test_export_changes_only_the_policy_and_preserves_ema_and_parent(tmp_path):
    path, digest = checkpoint(tmp_path)
    result = module.export(path, tmp_path / "export", digest)
    state = torch.load(result["export"], weights_only=True)
    assert state["step"] == 7 and "optimizer" not in state
    assert result["weight_selection"] == "ema" and state["config"]["inference_only"]
    torch.testing.assert_close(state["model"]["weight"], torch.arange(512) / 65535, rtol=0, atol=0)
    assert [
        k for k, v in result["model_config"].items() if v != result["parent_model_config"][k]
    ] == ["adc_cfa_projection"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    with pytest.raises(FileExistsError):
        module.export(path, tmp_path / "export", digest)


def test_export_refuses_changed_parent_before_creating_output(tmp_path):
    path, _ = checkpoint(tmp_path)
    with pytest.raises(ValueError, match="SHA256"):
        module.export(path, tmp_path / "export", "0" * 64)
    assert not (tmp_path / "export").exists()


def test_training_export_retains_lineage_without_claiming_projected_training(tmp_path):
    path, _ = checkpoint(tmp_path)
    state = torch.load(path, weights_only=True)
    lineage = {"path": "V95.pt", "sha256": "a" * 64, "step": 20000}
    state["config"] = {
        "run": "V98",
        "initialized_from": lineage,
        "model": state["model_config"],
        "source_sha256": "b" * 64,
    }
    torch.save(state, path)
    digest = module.sha(path)
    result = module.export(path, tmp_path / "export", digest, preserve_training_lineage=True)
    exported = torch.load(result["export"], weights_only=True)
    assert exported["config"]["initialized_from"] == lineage
    assert exported["config"]["source_sha256"] == "b" * 64
    assert exported["config"]["model"]["adc_cfa_projection"] is True
    assert result["training_model_config"]["adc_cfa_projection"] is False
    assert result["retained_training_lineage"] == lineage
    assert exported["model"].keys() == state["ema"].keys()
    assert module.tensor_digest(exported["model"]) == module.tensor_digest(state["ema"])
    assert module.sha(path) == digest


def test_training_export_rejects_missing_lineage_before_writing(tmp_path):
    path, digest = checkpoint(tmp_path)
    with pytest.raises(ValueError, match="initializer"):
        module.export(path, tmp_path / "export", digest, preserve_training_lineage=True)
    assert not (tmp_path / "export").exists()


def test_sites_export_preserves_weights_and_records_only_policy_changes(tmp_path):
    path, digest = checkpoint(tmp_path)
    result = module.export(path, tmp_path / "export", digest, mode="sites")
    state = torch.load(result["export"], weights_only=True)
    assert state["model_config"]["adc_cfa_projection"] is True
    assert state["model_config"]["adc_cfa_projection_mode"] == "sites"
    assert {
        key for key, value in result["model_config"].items()
        if value != result["parent_model_config"][key]
    } == {"adc_cfa_projection", "adc_cfa_projection_mode"}
    torch.testing.assert_close(state["model"]["weight"], torch.arange(512) / 65535, rtol=0, atol=0)
    assert module.sha(path) == digest


def test_invalid_mode_is_rejected_before_writing(tmp_path):
    path, digest = checkpoint(tmp_path)
    with pytest.raises(ValueError, match="mode"):
        module.export(path, tmp_path / "export", digest, mode="unknown")
    assert not (tmp_path / "export").exists()


@pytest.mark.parametrize(
    "overrides",
    [
        {"variance_stabilization": False},
        {"adc_cfa_projection": True},
        {"physical_fp32": False},
    ],
)
def test_export_rejects_unsupported_parent(tmp_path, overrides):
    path, digest = checkpoint(tmp_path, **overrides)
    with pytest.raises(ValueError, match="stabilized"):
        module.export(path, tmp_path / "export", digest)
    assert not (tmp_path / "export").exists()
