"""Lifecycle fixtures cannot stand in for actual native viewing or exports."""

import json

import audit_coherent_pair_evidence_trial as lifecycle
import publish_phase_wave_trial as publication
import pytest


def write(path, value):
    path.write_text(json.dumps(value) + "\n")


@pytest.fixture
def boundary(tmp_path, monkeypatch):
    # Metadata-only unit fixture: no array, model, pixel or quality observation.
    monkeypatch.setattr(publication, "guard", lambda plan: None)
    monkeypatch.setattr(lifecycle, "owner_live", lambda owner: False)
    write(tmp_path / "plan-v1.json", {"unit_fixture": True})
    plan = publication.ref(tmp_path / "plan-v1.json")
    write(
        tmp_path / "publication-source-v1.json",
        {"publisher": publication.ref(publication.__file__), "helpers": []},
    )
    for phase, name, status in [
        (
            "wave-train",
            "wave-train-result-v1.json",
            "completed-isolated-readout-one-pass-frozen-V183-EMA",
        ),
        (
            "review",
            "scores-v1.json",
            "completed-two-endpoint-wave-readout-fixed-quality-awaiting-native-viewing",
        ),
    ]:
        owner = {"pid": 999999999, "created": 1.0}
        write(tmp_path / f"{phase}-launch-v1.json", {"owner": owner})
        write(tmp_path / name, {"owner": owner, "status": status, "plan": plan})
    scores = publication.ref(tmp_path / "scores-v1.json")
    for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
        write(
            tmp_path / name, {"status": "pass-unit-boundary-only", "plan": plan, "scores": scores}
        )
    write(
        tmp_path / "figures-v1.json",
        {
            "plan": plan,
            "scores": scores,
            "fixture_only_no_actual_V184_quality": False,
            "native_figures": 60,
            "native_triplets": 12,
            "images": [{"no_resize": True, "triplet": i < 12} for i in range(60)],
            "sheets": [{"indices": list(range(i, i + 4))} for i in range(0, 60, 4)],
        },
    )
    write(
        tmp_path / "paired-comparisons-v1.json",
        {
            "plan": plan,
            "scores": scores,
            "methods": 21,
            "metric_rows": 17262,
            "contrasts": 38,
            "primary_endpoint_contrasts": 2,
            "table_cells": [{}] * 1386,
            "real_references_scored": False,
        },
    )
    return tmp_path


def test_terminal_metadata_acceptance_still_requires_actual_viewing(boundary):
    publication.completed_context(boundary)
    with pytest.raises(FileNotFoundError):
        publication.completed_context(boundary, viewed=True)


def test_live_owner_cannot_be_overridden_by_completed_metadata(boundary, monkeypatch):
    monkeypatch.setattr(lifecycle, "owner_live", lambda owner: True)
    with pytest.raises(AssertionError):
        publication.completed_context(boundary)


def test_owner_observation_error_propagates(boundary, monkeypatch):
    def denied(owner):
        raise PermissionError("unit observation failure")

    monkeypatch.setattr(lifecycle, "owner_live", denied)
    with pytest.raises(PermissionError):
        publication.completed_context(boundary)


@pytest.mark.parametrize("change", ["owner", "status", "failure"])
def test_wrong_or_failed_training_cannot_publish(boundary, change):
    path = boundary / "wave-train-result-v1.json"
    value = publication.read(path)
    if change == "owner":
        value["owner"]["created"] = 2.0
    if change == "status":
        value["status"] = "completed-layout-only"
    if change == "failure":
        write(boundary / "wave-train-failure-v1.json", {"failed": True})
    write(path, value)
    with pytest.raises(AssertionError):
        publication.completed_context(boundary)


@pytest.mark.parametrize("damage", ["fixture", "triplet", "scores", "resized"])
def test_incomplete_or_fixture_render_cannot_publish(boundary, damage):
    path = boundary / "figures-v1.json"
    value = publication.read(path)
    if damage == "fixture":
        value["fixture_only_no_actual_V184_quality"] = True
    if damage == "triplet":
        value["images"][0]["triplet"] = False
    if damage == "scores":
        value["scores"]["sha256"] = "0" * 64
    if damage == "resized":
        value["images"][0]["no_resize"] = False
    write(path, value)
    with pytest.raises(AssertionError):
        publication.completed_context(boundary)


@pytest.mark.parametrize(
    "field,value",
    [("primary_endpoint_contrasts", 1), ("real_references_scored", True), ("contrasts", 37)],
)
def test_both_frozen_baseline_contrasts_and_unscored_real_refs_required(boundary, field, value):
    path = boundary / "paired-comparisons-v1.json"
    record = publication.read(path)
    record[field] = value
    write(path, record)
    with pytest.raises(AssertionError):
        publication.completed_context(boundary)


def test_wrong_quality_audit_binding_rejects(boundary):
    path = boundary / "quality-audit-v1.json"
    value = publication.read(path)
    value["scores"]["sha256"] = "0" * 64
    write(path, value)
    with pytest.raises(AssertionError):
        publication.completed_context(boundary)


def test_missing_human_notes_rejects_before_export_or_output(tmp_path, monkeypatch):
    monkeypatch.setattr(publication, "completed_context", lambda *a, **k: ({}, {}, {}, {}, {}))

    def forbidden(*args):
        raise AssertionError("No export before actual notes")

    monkeypatch.setattr(publication, "export_checkpoints", forbidden)
    with pytest.raises(ValueError, match="quality notes"):
        publication.publish(tmp_path, tmp_path / "missing.md")


def test_linked_publication_preserves_both_paths_and_bytes(tmp_path):
    source = tmp_path / "closed.json"
    destination = tmp_path / "public.json"
    source.write_bytes(b'{"closed":true}\n')
    publication.linked_copy(source, destination)
    assert source.read_bytes() == destination.read_bytes() == b'{"closed":true}\n'
    assert source.stat().st_ino == destination.stat().st_ino
    with pytest.raises(AssertionError):
        publication.linked_copy(source, destination)
