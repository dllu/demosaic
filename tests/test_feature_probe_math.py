"""Independent physical-control identities, without a pretrained encoder."""

import random
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from feature_probe_math import (
    blocks,
    coefficients,
    controlled_bands,
    gradient_projection,
    reference_mask,
)
from probe_dino_feature_loss import check_supervision_arrays
from train_directional_bank_trial import ref


def fixture():
    x = np.arange(256) + 0.5
    target = (
        np.broadcast_to(
            0.2 + 0.01 * np.cos(np.pi * x * 4 / 16)[None, None, None, :], (1, 3, 256, 256)
        )
        .copy()
        .astype(np.float32)
    )
    mask = reference_mask(target, np.ones((1, 3)), np.eye(3)[None], 1)
    return target, mask


def test_controls_preserve_mean_unselected_bands_and_wrong_detail_energy():
    target, mask = fixture()
    assert mask.sum() == 100
    before = target.copy()
    values, true, wrong = controlled_bands(target, mask)
    np.testing.assert_array_equal(target, before)
    t, q = coefficients(true), coefficients(wrong)
    np.testing.assert_allclose(np.sum(t * q, axis=-1), 0, atol=1e-16)
    np.testing.assert_allclose(np.sum(t * t, axis=-1), np.sum(q * q, axis=-1), atol=1e-16)
    outside = np.ones(target.shape, bool)
    outside[..., 48:208, 48:208] = False
    for v in values.values():
        np.testing.assert_array_equal(v[outside], target[outside])
        np.testing.assert_allclose(
            blocks(v).mean((-1, -2)), blocks(target).mean((-1, -2)), atol=2e-8
        )
    np.testing.assert_allclose(
        coefficients(values["half-band"]), 0.5 * coefficients(target), atol=5e-8
    )
    np.testing.assert_allclose(coefficients(values["phase-flip"]), -coefficients(target), atol=5e-8)


def test_true_quadratic_gradient_has_unit_corrective_alignment():
    target, mask = fixture()
    values, _, _ = controlled_bands(target, mask)
    prediction = values["half-band"]
    gradient = (prediction - target).astype(np.float64)
    result = gradient_projection(gradient, prediction, target, mask)
    assert result["descent_cosine_to_true_band_correction"] == pytest.approx(1)
    assert result["directional_derivative_toward_true_band"] < 0
    assert result["negative_gradient_target_gain_slope"] == pytest.approx(0.5, abs=1e-6)


def test_geometry_validation_and_global_random_state():
    py_state = random.getstate()
    np_state = np.random.get_state()
    target, mask = fixture()
    controlled_bands(target, mask)
    assert random.getstate() == py_state
    for a, b in zip(np.random.get_state(), np_state, strict=True):
        np.testing.assert_array_equal(a, b)
    with pytest.raises(ValueError):
        reference_mask(np.full_like(target, 0.2), np.ones((1, 3)), np.eye(3)[None], 0)
    with pytest.raises(ValueError):
        blocks(np.zeros((3, 160, 160)))


def test_target_identity_checks_arrays_instead_of_npz_order_or_path(tmp_path):
    data = {
        "target": np.arange(12, dtype=np.float32).reshape(1, 3, 2, 2),
        "wb": np.ones((1, 3), np.float32),
    }
    first, second = tmp_path / "first.npz", tmp_path / "second.npz"
    np.savez(first, **data)
    np.savez(second, wb=data["wb"], target=data["target"])
    assert ref(first)["sha256"] != ref(second)["sha256"]
    check_supervision_arrays(ref(first), data)
    check_supervision_arrays(ref(second), data)
    changed = {**data, "target": data["target"] + np.float32(1 / 65535)}
    with pytest.raises(AssertionError):
        check_supervision_arrays(ref(second), changed)
