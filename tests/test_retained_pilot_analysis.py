"""Exercise saved-control report wiring without models, tensor work or rendering."""

import copy
import json
import os
import shutil
import sys
from pathlib import Path

import pytest

from demosaic import archive_metrics

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_shadow_pilot_endpoints as reports
from train_directional_bank_trial import ref, save


def fixture(tmp_path, monkeypatch, *, mismatch=False):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    root = tmp_path / "new-candidate-only"
    root.mkdir()
    predictions = {}
    for label in ("V120", "V126", "V128"):
        path = tmp_path / (label + "-protocol-only.txt")
        path.write_text("Fixture marker; no neural weights or predictions")
        predictions[label] = ref(path)
    observations = [
        {
            "id": f"case-{i}",
            "kind": "shadow-material" if i < 64 else "retained-material",
            "input_fingerprints": {"packed": {"sha256": f"input-{i}"}},
            "controls": [{"model": {"label": "V120"}, "prediction": predictions["V120"]}],
        }
        for i in range(86)
    ]
    baseline_path = tmp_path / "baseline.json"
    save(
        baseline_path,
        {
            "counts": {"root": 64, "encoder": 64},
            "observations": [
                {"id": r["id"], "prediction": predictions["V120"]} for r in observations[:64]
            ],
        },
    )
    control_plan = tmp_path / "saved-V126-plan.json"
    save(control_plan, {"observations": observations, "inputs": [], "frozen_files": {}})
    control_path = tmp_path / "saved-V126-collection.json"
    save(
        control_path,
        {
            "plan": ref(control_plan),
            "counts": {"root": 86, "encoder": 86},
            "observations": [
                {"id": r["id"], "prediction": predictions["V126"]} for r in observations
            ],
        },
    )
    candidate = root / "V128"
    candidate.mkdir()
    work = candidate / "work/src/demosaic"
    work.mkdir(parents=True)
    shutil.copyfile(archive_metrics.__file__, work / "archive_metrics.py")
    current = copy.deepcopy(observations)
    if mismatch:
        current[0]["input_fingerprints"]["packed"]["sha256"] = "wrong-input"
    execution = candidate / "plan-v1.json"
    save(
        execution,
        {
            "work": str(candidate / "work"),
            "observations": current,
            "inputs": [],
            "frozen_files": {},
            "scope": "Protocol fixture, zero neural work",
        },
    )
    collection = candidate / "collection-v1.json"
    save(
        collection,
        {
            "plan": ref(execution),
            "counts": {"root": 86, "encoder": 86},
            "observations": [{"id": r["id"], "prediction": predictions["V128"]} for r in current],
        },
    )
    queue = root / "queue.json"
    save(
        queue,
        {
            "root": str(root),
            "arms": ["V128"],
            "baseline_collection": ref(baseline_path),
            "matched_control_collection": ref(control_path),
            "inputs": [],
            "frozen_files": {},
        },
    )
    save(
        root / "status.json",
        {
            "plan": ref(queue),
            "owner": {"pid": os.getpid(), "created": 0.0},
            "status": "completed-pilot-predictions-awaiting-independent-and-native-review",
            "completed": {"V128": ref(collection)},
        },
    )
    original_copy = shutil.copyfile

    def fixture_reporter(source, destination):
        if Path(destination).name != "reporter-source-v1.py":
            return original_copy(source, destination)
        Path(destination).write_text(
            "import json\nfrom pathlib import Path\n"
            "def report(plan, collection):\n"
            "    p=json.loads(Path(plan).read_text())\n"
            "    assert p['model_label']=='V128 1k EMA'\n"
            "    assert len(p['observations'])==86\n"
            "    for row in p['observations']:\n"
            "        assert [c['model']['label'] for c in row['controls']]==['V120','V126 1k EMA']\n"
            "        assert Path(row['controls'][0]['prediction']['path']).name.startswith('V120-')\n"
            "        assert Path(row['controls'][1]['prediction']['path']).name.startswith('V126-')\n"
            "    c=json.loads(Path(collection).read_text())\n"
            "    assert all(Path(row['prediction']['path']).name.startswith('V128-') for row in c['observations'])\n"
            "    out=Path(p['root'])/'report-v1'\n"
            "    out.mkdir()\n"
            "    (out/'report.json').write_text(json.dumps({'fixture_only':True,'neural_calls':0}))\n"
        )
        return destination

    monkeypatch.setattr(reports.shutil, "copyfile", fixture_reporter)
    return queue


def test_single_new_endpoint_reuses_saved_control_without_new_control_directory(
    tmp_path, monkeypatch
):
    path = fixture(tmp_path, monkeypatch)
    reports.analyze(path)
    assert not (path.parent / "V126").exists()
    output = json.loads((path.parent / "retained-analysis-v1.json").read_text())
    assert set(output["reports"]) == {"V128"} and output["new_neural_forwards"] == 0
    with pytest.raises(FileExistsError):
        reports.analyze(path)


def test_changed_candidate_input_is_rejected_before_report_creation(tmp_path, monkeypatch):
    path = fixture(tmp_path, monkeypatch, mismatch=True)
    with pytest.raises(ValueError, match="identical observations"):
        reports.analyze(path)
    assert not (path.parent / "analysis-V128-v1").exists()
