"""A noiseless compatibility oracle isolates representation from optimization."""

import importlib.util
from pathlib import Path


def test_sensor_unclipped_reference_white_conflict_has_zero_head_gradient(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").absolute()))
    spec = importlib.util.spec_from_file_location(
        "target_audit", Path("scripts/audit_camera_target_conventions.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    rows = module.cases()
    assert len(rows) == 12
    for row in rows:
        assert row["maximum_trainable_head_gradient"] == row["maximum_feature_gradient"] == 0
        if row["case"] == "reference-white-only-clipped":
            assert row["sensor_samples_are_unclipped"]
            assert row["raw_head_reference_white_MSE"] > 0.001
            assert row["raw_head_valid_sensor_MSE"] < 2e-14
            assert row["projected_head_reference_white_MSE"] < 2e-14
            assert row["projected_head_valid_sensor_MSE"] > 0.001
