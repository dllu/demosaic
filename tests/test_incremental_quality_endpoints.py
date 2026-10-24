"""Incremental archives must cover their declared models without rerunning controls."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import queue_matched_quality_predictions as queue
from collect_quality_predictions import validate_checkpoint_declarations, verify_model_coverage
from queue_quality_archive_audit import verify_audit_counts

from demosaic.prediction_archive import PredictionArchive, fingerprint, iter_predictions


@pytest.mark.parametrize("count", [1, 2])
def test_real_archive_covers_one_candidate_or_two_endpoints(tmp_path, count):
    archive = PredictionArchive(tmp_path / "archive")
    target = np.full((1, 3, 8, 8), .2, np.float32)
    context = {"ids": ["training-independent-fixture"],
               "input_fingerprints": {"packed": fingerprint(target)}}
    supervision = {"target": target, "wb": np.ones((1, 3), np.float32),
                   "matrix": np.eye(3, dtype=np.float32)[None]}
    checkpoints = [{"sha256": c * 64} for c in "ab"[:count]]
    records = []
    for index, checkpoint in enumerate(checkpoints):
        archive.append({**checkpoint, "label": f"model{index}", "self_ensemble": "none"},
                       context, target, supervision)
        records.append({"checkpoint": checkpoint})
    alignment = archive.verify_alignment()
    assert verify_model_coverage(checkpoints, records, alignment) == count
    assert len(list(iter_predictions(archive.manifest))) == count
    verify_audit_counts({"models": count, "observations": {str(i): 1 for i in range(count)}},
                        count, 1)
    if count == 2:
        with pytest.raises(ValueError, match="coverage"):
            verify_model_coverage(checkpoints, records[:1])
        with pytest.raises(ValueError, match="Archive model count"):
            verify_model_coverage(checkpoints, records, {"models": 1})


@pytest.mark.parametrize("checkpoints", [[], [{"sha256": "a" * 64}] * 2,
                                         [{"sha256": "bad"}], [{"sha256": "A" * 64}]])
def test_invalid_declarations_rejected_before_neural_work(checkpoints):
    with pytest.raises(ValueError, match="distinct nonempty"):
        validate_checkpoint_declarations(checkpoints)


@pytest.mark.parametrize("result", [
    {"models": 1, "observations": {}},
    {"models": 2, "observations": {"candidate": 72}},
    {"models": 1, "observations": {"candidate": 71}},
])
def test_independent_audit_requires_all_declared_observations(result):
    with pytest.raises(ValueError, match="observation counts"):
        verify_audit_counts(result, 1, 72)


@pytest.mark.parametrize("internal,count", [(True, 1), (False, 2)])
def test_queue_prepares_incremental_internal_and_legacy_external_plans(tmp_path, monkeypatch,
                                                                     internal, count):
    repo = tmp_path / "repo"
    (repo / "src/demosaic").mkdir(parents=True)
    (repo / "src/demosaic/suite.py").write_text("def observation():\n    return None\n")
    files = [*("scripts/" + name for name in queue.HELPERS), "pyproject.toml", "uv.lock",
             "third_party/dinov3/LICENSE.md", "configs/evaluation.yaml"]
    for name in files:
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# fixture\n")
    monkeypatch.setattr(queue, "REPO", repo)
    monkeypatch.setattr(queue, "live", lambda owner: True)
    train_root = repo / ".cache/training"
    train_root.mkdir(parents=True)
    arm_names = ["V116"] if count == 1 else ["V114", "V115"]
    training_plan = train_root / "plan.json"
    training_plan.write_text(json.dumps({"work": str(repo), "inputs": [], "frozen_files": {}}))
    execution = {"arms": [{"arm": name, "training_plan": queue.ref(training_plan)}
                           for name in arm_names], "inputs": [], "frozen_files": {}}
    if internal:
        execution["terminal_status"] = "completed-V116-training"
    path = train_root / "execution-plan-v1.json"
    path.write_text(json.dumps(execution))
    (train_root / "status.json").write_text(json.dumps({"execution_plan": queue.ref(path),
        "owner": {"pid": 123, "created": 1}, "status": "waiting"}))
    witness = {"historical_suite": queue.ref(repo / "src/demosaic/suite.py"),
               "inputs": [], "frozen_files": {}, "stages": {}}
    for stage in queue.STAGES:
        witness["stages"][stage] = {"output": str(tmp_path / "unused" / stage)}
        if stage in {"photo", "known", "unseen"}:
            manifest = tmp_path / (stage + ".json")
            manifest.write_text("{}")
            witness["stages"][stage]["manifest"] = queue.ref(manifest)
        if stage == "photo":
            witness["stages"][stage]["protocol"] = queue.ref(repo / "configs/evaluation.yaml")
    colors = tmp_path / "colors.json"
    colors.write_text("{}")
    witness["color_inputs"] = queue.ref(colors)
    witness_path = tmp_path / "witness.json"
    witness_path.write_text(json.dumps(witness))
    root = repo / ".cache/evaluation"
    artifacts = root / "work/artifacts" if internal else Path("/mnt/external/demosaic/unit-unused")
    result = json.loads(queue.prepare(root, artifacts, train_root, witness_path, {}).read_text())
    assert result["expected_model_count"] == count
    assert result["expected_training_phases"] == [f"{phase}-{name}" for phase in ("CUDA", "train")
                                                  for name in arm_names]
    assert result["estimated_retained_and_export_budget_GiB"] == 15 * count
    assert result["first_stage_external_free_GiB"] == (208 if internal else 248)
    assert result["phase_start_internal_free_GiB"] == (128 if internal else 32)
    assert result["expected_training_terminal"] == ("completed-V116-training" if internal else
        "completed-matched-V114-V115-training-awaiting-quality-comparisons")
