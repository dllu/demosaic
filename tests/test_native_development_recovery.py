import builtins
import json
from pathlib import Path

import numpy as np
import pytest
from evaluate_native_camera_development import binding, reuse_completed_joint_predictions

from demosaic.prediction_archive import PredictionArchive, fingerprint, iter_predictions


@pytest.fixture
def partial(tmp_path):
    dataset = {"rows": [], "observations": []}
    values = []
    for index in range(2):
        target = np.full((1, 3, 16, 16), 0.1 + index * 0.01, np.float32)
        path = tmp_path / f"target{index}.npy"
        np.save(path, target)
        data = {
            "target": target,
            "wb": np.ones((1, 3), np.float32),
            "matrix": np.eye(3, dtype=np.float32)[None],
        }
        identity = f"case{index}"
        dataset["rows"].append({"case_id": identity, "reference_camera_FP32": binding(path)})
        observation = {
            "id": identity,
            "case_id": identity,
            "arrays": binding(path),
            "input_fingerprints": {key: fingerprint(data[key]) for key in ("wb", "matrix")},
        }
        dataset["observations"].append(observation)
        values.append(data)
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset))
    methods = [
        {"label": label, "kind": "joint", "checkpoint": {"sha256": str(i + 1) * 64}}
        for i, label in enumerate(("V114", "V115", "V117", "V119"))
    ]
    archive = PredictionArchive(tmp_path / "original")
    for method in methods:
        model = {
            "label": method["label"],
            "kind": "joint",
            "step": 20000,
            "self_ensemble": "none",
            "sha256": method["checkpoint"]["sha256"],
        }
        for observation, data in zip(dataset["observations"], values, strict=True):
            context = {
                **observation,
                "ids": [observation["id"]],
                "input_arrays": observation["arrays"],
            }
            archive.append(model, context, data["target"] + np.float32(0.001), data)
    previous = tmp_path / "execution.json"
    previous.write_text(json.dumps({"dataset_manifest": binding(path), "methods": methods}))
    failure = tmp_path / "failure.json"
    failure.write_text(
        json.dumps(
            {
                "execution_plan": binding(previous),
                "actual_tracking": {
                    "method": "RawNIND-preup",
                    "started_root_calls": 8,
                    "completed_valid_root_calls": 8,
                    "encoder_calls": 8,
                    "reference_network_calls": 0,
                },
            }
        )
    )
    plan = {
        "methods": methods,
        "dataset_manifest": binding(path),
        "retained_collection": {
            "execution_plan": binding(previous),
            "failure": binding(failure),
            "archive": binding(archive.manifest),
        },
    }
    return plan, dataset, archive


def test_partial_archive_reuse_preserves_bytes_and_never_imports_model_code(
    partial, tmp_path, monkeypatch
):
    plan, dataset, original = partial
    before = original.manifest.read_bytes()
    recovered = PredictionArchive(tmp_path / "recovered")
    original_import = builtins.__import__

    def forbid(name, *args, **kwargs):
        if name == "torch" or name.startswith(("demosaic.inference", "demosaic.model")):
            raise AssertionError("Prediction reuse must not load a model")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", forbid)
    result = reuse_completed_joint_predictions(plan, dataset, recovered)
    assert sum(r["new_root_calls"] for r in result) == 0
    assert sum(r["reused_prediction_count"] for r in result) == 8
    assert original.manifest.read_bytes() == before
    for (old, old_pixels, _), (new, new_pixels, _) in zip(
        iter_predictions(original.manifest), iter_predictions(recovered.manifest), strict=True
    ):
        assert old["prediction"]["sha256"] == new["prediction"]["sha256"]
        assert old["context"] == new["context"] and np.array_equal(old_pixels, new_pixels)


@pytest.mark.parametrize("damage", ["completed_reference", "changed_input"])
def test_recovery_refuses_unsupported_failure_or_observation(partial, tmp_path, damage):
    plan, dataset, _ = partial
    if damage == "completed_reference":
        path = plan["retained_collection"]["failure"]["path"]
        data = json.loads(Path(path).read_text())
        data["actual_tracking"]["reference_network_calls"] = 1
        with open(path, "w") as stream:
            json.dump(data, stream)
        plan["retained_collection"]["failure"] = binding(path)
    else:
        dataset["observations"][0]["input_fingerprints"] = {}
    with pytest.raises(AssertionError):
        reuse_completed_joint_predictions(plan, dataset, PredictionArchive(tmp_path / "rejected"))
