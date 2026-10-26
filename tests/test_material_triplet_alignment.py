import copy

import numpy as np
import pytest
from audit_quality_archive import _triplet, binding
from compare_quality_crops import matched_material_stage, photo_comparison

from demosaic.prediction_archive import PredictionArchive


@pytest.fixture
def stage(tmp_path):
    archives = []
    receipts = []
    for role, digest in (("control", "a"), ("candidate", "b")):
        archive = PredictionArchive(tmp_path / role)
        output = tmp_path / (role + "-triplets")
        output.mkdir()
        crops = []
        for number, source_id in enumerate(("bark", "feather", "canopy")):
            target = np.full((1, 3, 256, 256), 0.15 + 0.01 * number, np.float32)
            data = {
                "target": target,
                "packed": np.full((1, 4, 128, 128), 0.17, np.float32),
                "colors": np.array([[0, 1, 1, 2]], np.int64),
                "wb": np.ones((1, 3), np.float32),
                "matrix": np.eye(3, dtype=np.float32)[None],
            }
            model = {"sha256": digest * 64, "label": role, "self_ensemble": "none"}
            context = {
                "stage": "photo",
                "ids": [source_id],
                "pattern": "RGGB",
                "condition": {"name": "iso12800-prior", "shot": 0.00256},
                "input_fingerprints": {"packed": "shared-observation-" + source_id},
            }
            record = archive.append(model, context, target + (role == "candidate") * 0.001, data)
            if source_id in ({"bark", "feather"} if role == "control" else {"bark", "canopy"}):
                crops.append(
                    _triplet(
                        output,
                        record,
                        target + (role == "candidate") * 0.001,
                        data,
                        0,
                        {"id": source_id},
                    )
                )
        archives.append(archive)
        receipts.append(crops)
    return {
        "stage": "photo",
        "all_noisy_inputs_targets_masks_and_transforms_equal": True,
        "control": {
            "model": {"sha256": "a" * 64, "self_ensemble": "none"},
            "manifest": binding(archives[0].manifest),
        },
        "candidate": {
            "model": {"sha256": "b" * 64, "self_ensemble": "none"},
            "manifest": binding(archives[1].manifest),
        },
        "control_native_triplets": receipts[0],
        "candidate_native_triplets": receipts[1],
    }


def test_different_declared_material_pairs_align_using_only_saved_arrays(stage, tmp_path):
    original = copy.deepcopy(stage)
    aligned = matched_material_stage(stage, tmp_path / "missing")
    assert stage == original
    assert [r["source_id"] for r in aligned["control_native_triplets"]] == ["bark", "canopy"]
    assert aligned["control_native_triplets"][0] == stage["control_native_triplets"][0]
    assert aligned["candidate_native_triplets"] == stage["candidate_native_triplets"]
    receipt = photo_comparison(aligned, tmp_path, labels=("old", "new"))
    assert len(receipt["candidate_triplets"]) == 2
    assert len(receipt["comparison"]["panels"]) == 8


def test_matching_pair_reuses_original_triplets_without_touching_archives(stage, tmp_path):
    aligned = matched_material_stage(stage, tmp_path / "first")
    # Same-pair rendering uses existing bound PNGs and does not need archive access.
    aligned["control"]["manifest"]["path"] = "/not-read"
    assert matched_material_stage(aligned, tmp_path / "unused") is aligned
    assert not (tmp_path / "unused").exists()


@pytest.mark.parametrize(
    "damage", ["unmatched", "manifest", "candidate-manifest", "context", "duplicate"]
)
def test_incorrect_observation_or_manifest_cannot_create_matching_material(stage, tmp_path, damage):
    if damage == "unmatched":
        stage["all_noisy_inputs_targets_masks_and_transforms_equal"] = False
    elif damage == "manifest":
        stage["control"]["manifest"]["sha256"] = "c" * 64
    elif damage == "candidate-manifest":
        stage["candidate"]["manifest"]["sha256"] = "c" * 64
    elif damage == "context":
        stage["candidate_native_triplets"][1]["context"]["pattern"] = "BGGR"
    else:
        stage["candidate_native_triplets"][1] = copy.deepcopy(stage["candidate_native_triplets"][0])
    with pytest.raises(ValueError):
        matched_material_stage(stage, tmp_path / "forbidden")
    assert not (tmp_path / "forbidden").exists()
