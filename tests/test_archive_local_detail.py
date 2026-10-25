"""Closed-form and identity checks for the saved-output local-detail audit."""

import copy
import json

import numpy as np
import pytest
from diagnose_archive_local_detail import (
    CONDITIONS,
    PATTERNS,
    analyze,
    fingerprint,
    matched,
    read_records,
)
from diagnose_local_material_detail import binding


def metadata(sha="a" * 64):
    return {
        "index": 0,
        "schema": "demosaic-predictions-v1",
        "model": {"sha256": sha, "self_ensemble": "none", "step": 20000},
        "context": {
            "ids": ["c" * 40],
            "condition": {"name": "adc-only", "exposure": 1, "shot": 0, "read": 0},
            "pattern": "RGGB",
            "stage": "photo",
            "seed": 1,
            "input_fingerprints": {
                key: {"sha256": "d" * 64}
                for key in ("packed", "variance", "colors", "wb", "matrix")
            },
        },
        "supervision_values": {"target": {"sha256": "e" * 64}},
    }


@pytest.mark.parametrize("field", ["packed", "variance", "colors", "wb", "matrix"])
def test_changed_physical_input_rejected(field):
    a = metadata()
    b = copy.deepcopy(a)
    b["context"]["input_fingerprints"][field]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="Noisy input"):
        matched(a, b)


def test_changed_target_rejected():
    a = metadata()
    b = copy.deepcopy(a)
    b["supervision_values"]["target"]["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="Target"):
        matched(a, b)


def test_missing_input_rejected():
    a = metadata()
    del a["context"]["input_fingerprints"]["packed"]
    with pytest.raises(ValueError, match="Missing"):
        matched(a, copy.deepcopy(a))


def test_duplicate_and_policy_rejected(tmp_path):
    a, b = metadata(), metadata()
    b["index"] = 1
    path = tmp_path / "records.jsonl"
    path.write_text(json.dumps(a) + "\n" + json.dumps(b) + "\n")
    with pytest.raises(ValueError, match="Duplicate"):
        read_records(path, "a" * 64)
    a["model"]["self_ensemble"] = "dihedral8"
    path.write_text(json.dumps(a) + "\n")
    with pytest.raises(ValueError, match="single-view"):
        read_records(path, "a" * 64)


def test_full_closed_form_source_and_CFA_reduction(tmp_path, monkeypatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    x = np.arange(256)
    target = (
        np.broadcast_to(0.18 + 0.0032 * np.sin(2 * np.pi * x / 4), (1, 3, 256, 256))
        .astype(np.float32)
        .copy()
    )
    wb, matrix = np.ones((1, 3), np.float32), np.eye(3, dtype=np.float32)[None]
    supervision = tmp_path / "supervision.npz"
    np.savez(supervision, target=target, wb=wb, matrix=matrix)
    values = {k: fingerprint(v) for k, v in {"target": target, "wb": wb, "matrix": matrix}.items()}
    manifests = []
    for method, gain in (("a", 0.5), ("b", 0.75)):
        prediction = (0.18 + gain * (target - 0.18)).astype(np.float32)
        path = tmp_path / (method + ".npy")
        np.save(path, prediction)
        records = []
        for condition in sorted(CONDITIONS):
            for pattern in sorted(PATTERNS):
                row = metadata(method * 64)
                row["index"] = len(records)
                row["context"]["condition"]["name"] = condition
                row["context"]["pattern"] = pattern
                row.update(
                    prediction=binding(path),
                    prediction_values=fingerprint(prediction),
                    supervision=binding(supervision),
                    supervision_values=values,
                )
                records.append(row)
        manifest = tmp_path / (method + ".jsonl")
        manifest.write_text("".join(json.dumps(r) + "\n" for r in records))
        manifests.append(manifest)
    result = analyze(
        manifests[0], "a" * 64, manifests[1], "b" * 64, tmp_path / "output", expected_images=1
    )
    assert result["unique_source_blocks"] == 225
    assert result["paired_source_noise_CFA_observations"] == 12
    assert len(result["summaries"]) == 3
    for row in result["summaries"]:
        assert row["first"]["contributing_sources"] == row["second"]["contributing_sources"] == 1
        assert row["first"]["pooled"]["blocks"] == 900
        assert row["first"]["source_balanced"]["GT_projected_gain"] == pytest.approx(0.5, abs=1e-5)
        assert row["second"]["source_balanced"]["GT_projected_gain"] == pytest.approx(
            0.75, abs=1e-5
        )
        assert row["second_minus_first"]["GT_projected_gain"] == pytest.approx(0.25, abs=1e-5)
    assert result["new_neural_forwards"] == result["new_noise_observations"] == 0
