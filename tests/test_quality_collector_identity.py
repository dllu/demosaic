import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from collect_quality_predictions import verify_forward_witness, verify_recorded_backbone
from profile_raw_kernel_inference import model_hash


def test_collector_uses_the_real_required_backbone_identity_interface():
    backbone = torch.nn.Linear(1, 1, bias=False)
    config = {"dino_model": "unit-official-backbone", "dino_revision": "a" * 40}
    model = SimpleNamespace(
        config=SimpleNamespace(to_dict=lambda: config), context=SimpleNamespace(backbone=backbone)
    )
    identity = {
        "model": config["dino_model"],
        "revision": config["dino_revision"],
        "sha256": model_hash(backbone),
    }
    record = {"expected_backbone": identity}
    assert verify_recorded_backbone(model, record) == identity["sha256"]
    for changed in (
        {**identity, "model": "wrong"},
        {**identity, "revision": "b" * 40},
        {**identity, "sha256": "0" * 64},
    ):
        with pytest.raises(ValueError, match="backbone"):
            verify_recorded_backbone(model, {"expected_backbone": changed})
    with pytest.raises(KeyError):
        verify_recorded_backbone(model, {})


def test_forward_witness_requires_all_arguments_before_neural_work():
    from demosaic.prediction_archive import fingerprint

    actual = {
        name: fingerprint(torch.ones(1, index + 1))
        for index, name in enumerate(("packed", "variance", "colors", "wb", "matrix"))
    }
    old = {
        "argument_fingerprints": {name: value["sha256"] for name, value in actual.items()},
        "argument_metadata": {
            name: {key: value[key] for key in ("shape", "dtype")} for name, value in actual.items()
        },
    }
    verify_forward_witness(None, 0, actual)
    verify_forward_witness([old], 0, actual)
    verify_forward_witness(
        [{key: value for key, value in old.items() if key != "argument_metadata"}], 0, actual
    )
    for name, value in actual.items():
        changed = {**actual, name: {**value, "sha256": "0" * 64}}
        with pytest.raises(ValueError, match="before forward"):
            verify_forward_witness([old], 0, changed)
    changed = {**actual, "packed": {**actual["packed"], "shape": [999]}}
    with pytest.raises(ValueError, match="shape/dtype"):
        verify_forward_witness([old], 0, changed)
    for index in (-1, 1):
        with pytest.raises(ValueError, match="does not cover"):
            verify_forward_witness([old], index, actual)
