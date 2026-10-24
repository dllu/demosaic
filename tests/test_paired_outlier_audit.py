"""Reference-phase, support and mask checks for the offline training audit."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "audit_paired_outliers", Path(__file__).parents[1] / "scripts/audit_paired_outliers.py"
)
audit_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit_module)
candidates = audit_module.isolated_reference_candidates


def shifted_reference(size=16):
    reference = np.zeros((3, size, size), np.float32)
    count = np.zeros_like(reference, np.uint8)
    # GBRG: a red reference sample is on the noisy RGGB green phase.
    for phase, color in enumerate((1, 2, 0, 1)):
        y, x = divmod(phase, 2)
        reference[color, y::2, x::2] = 0.02
        count[color, y::2, x::2] = 2
    reference[0, 7, 8] = 0.5
    return reference, count


def test_shifted_reference_phase_and_missing_neighbor():
    reference, count = shifted_reference()
    sites, _ = candidates(reference, count, shot=1e-4, read=1e-7)
    assert np.argwhere(sites).tolist() == [[0, 7, 8]]
    count[0, 5, 6] = 0
    assert not candidates(reference, count, shot=1e-4, read=1e-7)[0].any()


def test_same_color_line_and_borders_are_not_isolated():
    reference, count = shifted_reference()
    reference[0, 7, 10] = 0.49
    reference[0, 1, 2] = 0.8
    assert not candidates(reference, count, shot=1e-4, read=1e-7)[0].any()


def test_matches_scalar_oracle_with_multiple_reference_phases():
    rng = np.random.default_rng(384)
    reference = rng.uniform(0.01, 0.03, (3, 11, 12)).astype(np.float32)
    reference[:, 3, 4] = 0.4
    reference[2, 7, 8] = 0.8
    count = rng.integers(0, 3, reference.shape, dtype=np.uint8)
    count[:, 1::2, 2::2] = 1
    actual, _ = candidates(reference, count, shot=0.0002, read=1e-6)
    expected = np.zeros_like(actual)
    for color in range(3):
        for y in range(2, 9):
            for x in range(2, 10):
                neighbors = [(y + dy, x + dx) for dy in (-2, 0, 2) for dx in (-2, 0, 2) if dy or dx]
                if not count[color, y, x] or any(not count[color, yy, xx] for yy, xx in neighbors):
                    continue
                high = max(float(reference[color, yy, xx]) for yy, xx in neighbors)
                value = float(reference[color, y, x])
                expected[color, y, x] = value > 2 * max(0, high) and value - high > max(
                    0.005, 6 * np.sqrt(0.0002 * max(0, high) + 1e-6)
                )
    assert expected.any()
    assert np.array_equal(actual, expected)


@pytest.mark.parametrize(
    "options", [{"shot": -1}, {"read": float("nan")}, {"sigma": 0}, {"ratio": 1}, {"min_delta": -1}]
)
def test_bad_thresholds_fail(options):
    reference, count = shifted_reference()
    arguments = {"shot": 0.0001, "read": 1e-7, **options}
    with pytest.raises(ValueError):
        candidates(reference, count, **arguments)


def test_audit_counts_existing_mask_without_changing_source(tmp_path):
    reference, count = shifted_reference()
    valid = count > 0
    valid[0, 7, 8] = False
    crop = tmp_path / "crop.npz"
    np.savez(
        crop,
        raw=np.full((16, 16), 0.02, np.float32),
        reference_rgb=reference,
        sensor_reference=reference,
        sensor_count=count,
        sensor_mask=valid,
    )
    digest = audit_module.sha(crop)
    case = {
        "scene": "synthetic-fixture",
        "metadata": {"camera": "fixture", "iso": 100, "pattern": "RGGB"},
        "conditioning": {"shot": 0.0001, "read": 1e-7},
        "references": [],
        "crops": [{"id": "fixture", "path": crop.name, "sha256": digest, "xywh": [0, 0, 16, 16]}],
    }
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"split": "train", "cases": [case]}))
    result = audit_module.audit(manifest, tmp_path / "out")
    assert result["totals"]["reference_candidates"] == 1
    assert result["totals"]["reference_candidates_sensor_loss_masked"] == 1
    assert result["totals"]["reference_candidates_sensor_loss_valid"] == 0
    row = json.loads((tmp_path / "out/per-crop.jsonl").read_text())
    assert row["examples"][0]["coarse_RGB_loss_block_valid"] is False
    assert audit_module.sha(crop) == digest
    assert result["new_model_or_encoder_calls"] == 0


def test_heldout_split_is_rejected_before_output_creation(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"split": "development", "cases": []}))
    output = tmp_path / "out"
    with pytest.raises(ValueError, match="training/quarantine"):
        audit_module.audit(manifest, output)
    assert not output.exists()
