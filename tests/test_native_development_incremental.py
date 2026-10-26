"""New endpoints must reuse completed controls without another model forward."""

import builtins
import copy
import json

import numpy as np
import pytest
from evaluate_native_camera_development import (
    binding,
    comparison_pairs,
    expected_counts,
    reuse_verified_predictions,
    validate_methods,
)

from demosaic.prediction_archive import PredictionArchive, fingerprint, iter_predictions


@pytest.fixture
def completed(tmp_path):
    data = {"rows": [], "observations": [], "target_role": "fixture low-noise estimate, not GT"}
    samples = []
    for i in range(2):
        identity = f"source-{i}"
        target = np.full((1, 3, 16, 16), 0.1 + i * 0.01, np.float32)
        target_path = tmp_path / f"target-{i}.npy"
        np.save(target_path, target)
        batch = {
            "packed": np.full((1, 4, 8, 8), 0.1, np.float32),
            "variance": np.full((1, 4, 8, 8), 0.001, np.float32),
            "colors": np.array([[0, 1, 1, 2]], np.int64),
            "wb": np.ones((1, 3), np.float32),
            "matrix": np.eye(3, dtype=np.float32)[None],
        }
        path = tmp_path / f"input-{i}.npz"
        np.savez(path, **batch)
        data["rows"].append(
            {
                "case_id": identity,
                "reference_camera_FP32": binding(target_path),
                "display_exposure": 1,
            }
        )
        observation = {
            "id": identity,
            "case_id": identity,
            "source_id": identity,
            "scene_group": "fixture",
            "source_file_id": str(i),
            "condition": {"name": "adc-only", "shot": 0, "read": 0},
            "pattern": "RGGB",
            "arrays": binding(path),
            "input_fingerprints": {k: fingerprint(v) for k, v in batch.items()},
        }
        data["observations"].append(observation)
        samples.append({"target": target, "wb": batch["wb"], "matrix": batch["matrix"]})
    dataset_path = tmp_path / "dataset.json"
    dataset_path.write_text(json.dumps(data))
    methods = [
        {"label": label, "kind": kind, "checkpoint": {"sha256": digest * 64}}
        for label, kind, digest in [
            ("old-A", "joint", "a"),
            ("old-B", "joint", "b"),
            ("reference", "rawnind-preup", "c"),
        ]
    ]
    archive = PredictionArchive(tmp_path / "original")
    for method in methods:
        for observation, supervision in zip(data["observations"], samples, strict=True):
            context = {
                **{k: v for k, v in observation.items() if k not in {"id", "arrays"}},
                "ids": [observation["id"]],
                "input_arrays": observation["arrays"],
                "target_role": data["target_role"],
                "score_ROI_xywh": [48, 48, 160, 160],
                "display_exposure": 1,
            }
            descriptor = {
                "label": method["label"],
                "sha256": method["checkpoint"]["sha256"],
                "kind": method["kind"],
                "self_ensemble": "none",
                "step": 20000 if method["kind"] == "joint" else None,
            }
            archive.append(descriptor, context, supervision["target"] + 0.001, supervision)
    previous_path = tmp_path / "execution.json"
    previous_path.write_text(
        json.dumps({"dataset_manifest": binding(dataset_path), "methods": methods})
    )
    collection = {
        "status": "completed-new-native-input-predictions-awaiting-CPU-review",
        "execution_plan": binding(previous_path),
        "archive": binding(archive.manifest),
        "methods": [
            {
                "method": m,
                "root_calls": 2,
                "encoder_calls": 2 if m["kind"] == "joint" else 0,
                "reference_network_calls": 2 if m["kind"] == "rawnind-preup" else 0,
            }
            for m in methods
        ],
    }
    path = tmp_path / "collection.json"
    path.write_text(json.dumps(collection))
    new = {"label": "new", "kind": "joint", "checkpoint": {"sha256": "d" * 64}}
    plan = {
        "methods": [*methods, new],
        "dataset_manifest": binding(dataset_path),
        "comparison_pairs": [["old-A", "new"], ["reference", "new"]],
        "retained_predictions": {
            m["label"]: {"collection": binding(path), "archive": binding(archive.manifest)}
            for m in methods
        },
    }
    return plan, data, archive, path


def test_completed_joint_and_reference_reuse_never_loads_models(completed, tmp_path, monkeypatch):
    plan, data, archive, _ = completed
    original_bytes = archive.manifest.read_bytes()
    original_import = builtins.__import__

    def forbid(name, *args, **kwargs):
        if name == "torch" or name.startswith(("demosaic.inference", "demosaic.model")):
            raise AssertionError("Completed controls must not load models")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", forbid)
    output = PredictionArchive(tmp_path / "extended")
    results = reuse_verified_predictions(plan, data, output)
    assert sum(r["new_root_calls"] for r in results) == 0
    assert sum(r["reused_prediction_count"] for r in results) == 6
    assert archive.manifest.read_bytes() == original_bytes
    assert output.verify_alignment()["models"] == 3
    for old, new in zip(
        iter_predictions(archive.manifest), iter_predictions(output.manifest), strict=True
    ):
        assert old[0]["prediction"]["sha256"] == new[0]["prediction"]["sha256"]
        np.testing.assert_array_equal(old[1], new[1])
        assert old[0]["context"] == new[0]["context"]


@pytest.mark.parametrize(
    "damage", ["partial", "dataset", "method", "archive", "input", "target", "condition", "display"]
)
def test_completed_reuse_rejects_changed_evidence(completed, tmp_path, damage):
    plan, data, _, path = completed
    if damage in {"partial", "dataset", "method", "archive"}:
        collection = json.loads(path.read_text())
        if damage == "partial":
            collection["methods"][0]["root_calls"] = 1
        elif damage == "dataset":
            plan["dataset_manifest"] = {"path": "different", "sha256": "0" * 64}
        elif damage == "method":
            plan["methods"][0]["checkpoint"]["sha256"] = "e" * 64
        else:
            collection["archive"] = {"path": "different", "sha256": "0" * 64}
        path.write_text(json.dumps(collection))
        for item in plan["retained_predictions"].values():
            item["collection"] = binding(path)
    elif damage == "input":
        data["observations"][0]["input_fingerprints"]["variance"]["sha256"] = "0" * 64
    elif damage == "target":
        data["rows"][0]["reference_camera_FP32"] = data["rows"][1]["reference_camera_FP32"]
    elif damage == "condition":
        data["observations"][0]["condition"]["shot"] = 0.2
    else:
        data["rows"][0]["display_exposure"] = 2
    with pytest.raises((AssertionError, ValueError)):
        reuse_verified_predictions(plan, data, PredictionArchive(tmp_path / "rejected"))


def test_incremental_and_legacy_budgets_and_comparisons(completed):
    plan, _, _, _ = completed
    assert expected_counts(plan, 240) == {"root": 960, "encoder": 720, "reference": 240}
    assert comparison_pairs(plan) == [["old-A", "new"], ["reference", "new"]]
    old = copy.deepcopy(plan)
    old.pop("comparison_pairs")
    old["methods"] = [
        {
            "label": label,
            "kind": "joint" if label != "RawNIND-preup" else "rawnind-preup",
            "checkpoint": {"sha256": digest * 64},
        }
        for label, digest in zip(
            ["V114", "V115", "V117", "V119", "RawNIND-preup"], "abcde", strict=True
        )
    ]
    assert expected_counts(old, 240) == {"root": 1200, "encoder": 960, "reference": 240}
    assert len(comparison_pairs(old)) == 4
    for invalid in [[], [["new", "new"]], [["missing", "new"]], [["old-A", "new"]] * 2]:
        with pytest.raises(ValueError, match="comparison pairs"):
            comparison_pairs({**plan, "comparison_pairs": invalid})
    for methods in [
        [],
        plan["methods"] + [plan["methods"][0]],
        [{**plan["methods"][0], "kind": "unknown"}],
    ]:
        with pytest.raises(ValueError, match="distinct native operators"):
            validate_methods({"methods": methods})
