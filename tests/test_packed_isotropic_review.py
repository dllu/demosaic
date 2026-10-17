import importlib.util
import json
import sys
from pathlib import Path

import psutil
import pytest
import torch


def script():
    path = Path("scripts/review_packed_isotropic_trial.py")
    spec = importlib.util.spec_from_file_location("packed_trial_review", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


@pytest.mark.parametrize("panel", ["photo", "real"])
def test_rawnind_shared_weights_keep_gain_adapters_distinct(panel):
    module = script()
    names = (
        ["RawNIND:CFA-LS", "RawNIND:CFA-channel"]
        if panel == "photo"
        else ["RawNIND:cfa-ls:publisher", "RawNIND:cfa-channel:publisher"]
    )
    summary = (
        {"models": [{"label": name, "weight_sha256": "weights"} for name in names]}
        if panel == "photo"
        else {"models": [{"label": "RawNIND", "weight_sha256": "weights"}]}
    )
    records = [{"model": name} for name in names]
    descriptors = [
        module.reference_descriptor(
            f"gain-{index}", "weights", name, "report.json", "cases.jsonl", summary, records
        )
        for index, name in enumerate(names)
    ]
    assert descriptors[0]["checkpoint_sha256"] == descriptors[1]["checkpoint_sha256"]
    assert descriptors[0]["model_label"] != descriptors[1]["model_label"]
    for digest, name in [("wrong-weights", names[0]), ("weights", "unknown-gain")]:
        with pytest.raises(AssertionError):
            module.reference_descriptor("gain", digest, name, "report", "cases", summary, records)


def test_reference_binding_rejects_duplicate_publisher_receipt():
    module = script()
    entry = {"label": "RawNIND", "weight_sha256": "weights"}
    with pytest.raises(AssertionError):
        module.reference_descriptor(
            "gain",
            "weights",
            "RawNIND:cfa-channel:publisher",
            "report",
            "cases",
            {"models": [entry, entry]},
            [{"model": "RawNIND:cfa-channel:publisher"}],
        )


def test_pending_or_live_training_cannot_release_a_quality_review(tmp_path):
    module = script()
    path = tmp_path / "training.json"
    path.write_text(json.dumps({"status": "training-to-first-example-budget-review"}))
    with pytest.raises(RuntimeError, match="incomplete"):
        module.completed(path)
    owner = psutil.Process()
    path.write_text(
        json.dumps(
            {
                "status": module.TERMINAL,
                "controller": {"pid": owner.pid, "created": owner.create_time()},
            }
        )
    )
    with pytest.raises(AssertionError):
        module.completed(path)
    assert not torch.cuda.is_initialized()
