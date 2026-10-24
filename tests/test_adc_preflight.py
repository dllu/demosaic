import importlib.util
import json
from pathlib import Path

import pytest
import torch

from demosaic.model import JointDemosaic, ModelConfig


def script(name):
    path = Path(__file__).resolve().parents[1] / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("mode", ["sites", "malvar"])
def test_real_export_preflight_checks_selected_policy_and_actual_cpu_precision(tmp_path, mode):
    exporter = script("export_adc_cfa_projection")
    preflight = script("preflight_adc_cfa_projection")
    config = ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        variance_stabilization=True,
        physical_anchors=True,
    )
    model = JointDemosaic(config).eval()
    parent = tmp_path / "parent.pt"
    torch.save(
        {"model_config": config.to_dict(), "model": model.restoration_state_dict(), "step": 7},
        parent,
    )
    digest = exporter.sha(parent)
    exported = exporter.export(parent, tmp_path / "export", digest, mode=mode)
    preflight.main(Path(exported["export"]), tmp_path / "preflight", "cpu")
    result = json.loads((tmp_path / "preflight" / "receipt.json").read_text())
    assert result["projection_mode"] == mode
    assert len(result["records"]) == 8
    assert {r["precision"] for r in result["records"]} == {"float32"}
    assert all(r["positive_prior_images_exact"] for r in result["records"])
    assert result["max_valid_cfa_error"] < 2e-7
    assert result["tiled_max_cfa_error"] < 2e-7
    assert result["identical_restoration_tensors"]
    assert exporter.sha(parent) == digest
