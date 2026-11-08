"""Publication lifecycle corruption checks; all synthetic records are unit fixtures."""

import json
import os
import subprocess
import sys
from pathlib import Path

import publish_flat_spatial_evidence_trial as publication
import pytest


def write(path, value):
    path.write_text(json.dumps(value) + "\n")


@pytest.fixture
def boundary(tmp_path, monkeypatch):
    # No model, checkpoint, image or trained-quality observation is simulated.
    # These small records isolate owner/binding/gate behavior only.
    monkeypatch.setattr(publication, "guard", lambda plan: None)
    monkeypatch.setattr(publication, "owner_live", lambda owner: False)
    write(tmp_path / "plan-v1.json", {"unit_fixture": True})
    plan = publication.ref(tmp_path / "plan-v1.json")
    write(
        tmp_path / "publication-source-v1.json",
        {
            "publisher": publication.ref(publication.__file__),
            "helpers": [],
        },
    )
    for phase, name, status in [
        ("evidence-train", "evidence-train-result-v1.json", "completed-matched-warmstart-one-pass"),
        (
            "review",
            "scores-v1.json",
            "completed-two-endpoint-flat-spatial-fixed-quality-awaiting-native-viewing",
        ),
        (
            "completion",
            "completion-result-v1.json",
            "completed-flat-spatial-training-quality-audits-tables-render-awaiting-actual-viewing",
        ),
    ]:
        owner = {"pid": 123456789, "created": 1.0}
        write(tmp_path / f"{phase}-launch-v1.json", {"owner": owner})
        write(tmp_path / name, {"owner": owner, "status": status, "plan": plan})
    scores = publication.ref(tmp_path / "scores-v1.json")
    for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
        write(tmp_path / name, {"status": "pass-unit-fixture-only", "plan": plan, "scores": scores})
    figures = {
        "plan": plan,
        "scores": scores,
        "fixture_only_no_actual_V181_quality": False,
        "native_figures": 60,
        "native_triplets": 12,
        "images": [{"no_resize": True, "triplet": i < 12} for i in range(60)],
        "sheets": [{"indices": list(range(i, i + 4))} for i in range(0, 60, 4)],
    }
    write(tmp_path / "figures-v1.json", figures)
    completion = publication.read(tmp_path / "completion-result-v1.json")
    completion["figures"] = publication.ref(tmp_path / "figures-v1.json")
    write(tmp_path / "completion-result-v1.json", completion)
    write(
        tmp_path / "paired-comparisons-v1.json",
        {
            "plan": plan,
            "scores": scores,
            "table_cells": [{}] * 1050,
            "status": "completed-unit-fixture-only",
            "methods": 17,
            "metric_rows": 13974,
            "matched_endpoint_contrasts": 2,
            "contrasts": 28,
            "real_references_scored": False,
        },
    )
    return tmp_path


def test_completed_looking_result_cannot_override_live_owner(boundary, monkeypatch):
    monkeypatch.setattr(publication, "owner_live", lambda owner: True)
    with pytest.raises(RuntimeError, match="still live"):
        publication.completed_context(boundary)


@pytest.mark.parametrize("change", ["owner", "status", "failure"])
def test_wrong_owner_status_or_preserved_failure_blocks_publication(boundary, change):
    path = boundary / "evidence-train-result-v1.json"
    value = publication.read(path)
    if change == "owner":
        value["owner"]["created"] = 2.0
    elif change == "status":
        value["status"] = "completed-simulated-layout"
    else:
        write(boundary / "evidence-train-failure-v1.json", {"failed": True})
    write(path, value)
    with pytest.raises((ValueError, RuntimeError)):
        publication.completed_context(boundary)


def test_observation_error_is_not_interpreted_as_terminal(boundary, monkeypatch):
    def denied(owner):
        raise PermissionError("unit observation failure")

    monkeypatch.setattr(publication, "owner_live", denied)
    with pytest.raises(PermissionError):
        publication.completed_context(boundary)


@pytest.mark.parametrize("damage", ["fixture", "missing_triplet", "wrong_scores", "resized"])
def test_fixture_partial_or_wrong_result_render_rejects(boundary, damage):
    path = boundary / "figures-v1.json"
    value = publication.read(path)
    if damage == "fixture":
        value["fixture_only_no_actual_V181_quality"] = True
    elif damage == "missing_triplet":
        value["images"][0]["triplet"] = False
    elif damage == "wrong_scores":
        value["scores"]["sha256"] = "0" * 64
    else:
        value["images"][0]["no_resize"] = False
    write(path, value)
    completion = publication.read(boundary / "completion-result-v1.json")
    completion["figures"] = publication.ref(path)
    write(boundary / "completion-result-v1.json", completion)
    with pytest.raises(ValueError, match="actual 60-figure"):
        publication.completed_context(boundary)


def test_quality_audit_must_bind_the_actual_scores(boundary):
    path = boundary / "quality-audit-v1.json"
    value = publication.read(path)
    value["scores"]["sha256"] = "0" * 64
    write(path, value)
    with pytest.raises(ValueError, match="different scores"):
        publication.completed_context(boundary)


@pytest.mark.parametrize(
    "field,value", [("matched_endpoint_contrasts", 1), ("real_references_scored", True)]
)
def test_comparisons_require_both_matched_contrasts_and_unscored_real_refs(boundary, field, value):
    path = boundary / "paired-comparisons-v1.json"
    record = publication.read(path)
    record[field] = value
    write(path, record)
    with pytest.raises(ValueError, match="matched/context"):
        publication.completed_context(boundary)


def test_human_viewing_cannot_be_inferred_from_completed_renderer(boundary):
    publication.completed_context(boundary)
    with pytest.raises(FileNotFoundError):
        publication.completed_context(boundary, viewed=True)


def test_changed_publisher_source_rejects_before_completed_records(boundary):
    path = boundary / "publication-source-v1.json"
    value = publication.read(path)
    value["publisher"]["sha256"] = "0" * 64
    write(path, value)
    with pytest.raises(ValueError, match="sealed publication"):
        publication.completed_context(boundary)


def test_missing_notes_stop_before_export_or_output_mutation(boundary, monkeypatch):
    monkeypatch.setattr(publication, "completed_context", lambda *a, **k: ({}, {}, {}, {}, {}))

    def forbidden(*args):
        raise AssertionError("No export should be attempted")

    monkeypatch.setattr(publication, "export_checkpoints", forbidden)
    with pytest.raises(ValueError, match="quality notes"):
        publication.publish(boundary, boundary / "missing-notes.md")


def test_missing_cli_notes_reject_before_torch_import():
    script = Path(publication.__file__).resolve()
    code = (
        "import runpy,sys;sys.argv=[sys.argv[1],'publish'];"
        "\ntry:runpy.run_path(sys.argv[0],run_name='__main__')"
        "\nexcept SystemExit as error:"
        "\n assert error.code==2 and 'torch' not in sys.modules"
        "\nelse:raise AssertionError('Missing required notes accepted')"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(script)],
        env=dict(os.environ, CUDA_VISIBLE_DEVICES=""),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
