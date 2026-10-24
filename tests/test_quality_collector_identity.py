import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from collect_quality_predictions import verify_recorded_backbone
from profile_raw_kernel_inference import model_hash


def test_collector_uses_the_real_required_backbone_identity_interface():
    backbone = torch.nn.Linear(1, 1, bias=False)
    config = {"dino_model": "unit-official-backbone", "dino_revision": "a"*40}
    model = SimpleNamespace(config=SimpleNamespace(to_dict=lambda: config), context=SimpleNamespace(backbone=backbone))
    identity = {"model": config["dino_model"], "revision": config["dino_revision"], "sha256": model_hash(backbone)}
    record = {"expected_backbone": identity}
    assert verify_recorded_backbone(model, record) == identity["sha256"]
    for changed in ({**identity, "model": "wrong"}, {**identity, "revision": "b"*40}, {**identity, "sha256": "0"*64}):
        with pytest.raises(ValueError, match="backbone"):
            verify_recorded_backbone(model, {"expected_backbone": changed})
    with pytest.raises(KeyError):
        verify_recorded_backbone(model, {})
