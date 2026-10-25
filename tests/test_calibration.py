import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from demosaic.calibration import estimate_noise
from demosaic.noise import add_noise


def test_noise_estimate_recovers_known_poisson_gaussian_and_rejects_texture():
    torch.set_num_threads(2)
    # Flat fields span intensity; some fields deliberately contain structured detail.
    rng = np.random.default_rng(8)
    clean = np.repeat(np.repeat(rng.uniform(0.01, 0.8, (8, 8)), 128, 0), 128, 1)
    yy, xx = np.mgrid[:1024, :1024]
    clean[:256] += 0.08 * np.sin(xx[:256] * 0.3 + yy[:256] * 0.7)
    clean = torch.from_numpy(clean.astype(np.float32)).clamp_min(0)
    shot, read = 0.0008, 1e-5
    noisy = add_noise(
        clean, shot, read, black_level=0.04, generator=torch.Generator().manual_seed(9)
    )
    estimate = estimate_noise(noisy.numpy())
    assert estimate.reliable, estimate
    assert abs(estimate.shot / shot - 1) < 0.12
    assert abs(estimate.read / read - 1) < 0.25
    assert estimate.accepted_patches < estimate.candidate_patches


def test_noise_estimate_refuses_shot_read_separation_on_constant_signal():
    noisy = add_noise(
        torch.full((1024, 1024), 0.2),
        0.001,
        1e-6,
        black_level=0.03,
        generator=torch.Generator().manual_seed(4),
    )
    estimate = estimate_noise(noisy.numpy())
    assert not estimate.reliable
    assert estimate.reason == "insufficient_intensity_span"
    assert estimate.shot is None and estimate.read is None
    assert abs(estimate.reference_variance / 0.000201 - 1) < 0.1


def test_negative_read_noise_is_not_adc_censoring_after_black_subtraction():
    rng = np.random.default_rng(20261025)
    raw = rng.normal(0.002, 0.003, (512, 512)).astype(np.float32)
    original = raw.copy()
    metadata = SimpleNamespace(black_levels=[4096] * 4, white_levels=[65535] * 4)
    legacy = estimate_noise(raw)
    actual = estimate_noise(raw, metadata=metadata)
    assert legacy.accepted_patches == 0
    assert actual.accepted_patches > 3000
    assert not actual.reliable and actual.reason == "insufficient_intensity_span"
    assert actual.shot is None and actual.read is None
    assert abs(actual.reference_variance / 0.003**2 - 1) < 0.12
    assert actual.lower_clip_levels == [-4096 / np.float32(65535 - 4096)] * 4
    np.testing.assert_array_equal(raw, original)


def test_true_adc_floor_is_still_rejected_in_the_correct_cfa_phase():
    rng = np.random.default_rng(20261026)
    raw = rng.normal(0.006, 0.001, (256, 256)).astype(np.float32)
    black = np.array([1, 2, 3, 4], dtype=np.float32)
    white = np.full(4, 65535, dtype=np.float32)
    metadata = SimpleNamespace(black_levels=black.tolist(), white_levels=white.tolist())
    clean = estimate_noise(raw, max_patches=64, metadata=metadata)
    for phase in range(4):
        damaged = raw.copy()
        phase_patch = damaged[phase // 2 : 64 : 2, phase % 2 : 64 : 2]
        # Just over1% floor samples, while mean and texture remain usable.
        phase_patch.flat[:12] = -black[phase] / (white[phase] - black[phase])
        estimate = estimate_noise(damaged, max_patches=64, metadata=metadata)
        assert estimate.accepted_patches == clean.accepted_patches - 1


def test_noise_profile_cli_preserves_signed_raw_metadata(monkeypatch, tmp_path):
    from demosaic import io
    from demosaic.cli import main

    raw = np.random.default_rng(20261027).normal(0.002, 0.003, (128, 128)).astype(np.float32)
    metadata = io.RawMetadata(
        source="signed.raf",
        camera="Test camera",
        pattern="RGGB",
        black_levels=[4096] * 4,
        white_levels=[65535] * 4,
        white_balance=[1, 1, 1],
        camera_to_srgb=np.eye(3).tolist(),
        flip=0,
        iso=6400,
    )
    monkeypatch.setattr(io, "read_raw", lambda path: (raw, metadata))
    output = tmp_path / "profile.json"
    main(["noise-profile", "signed.raf", str(output), "--max-patches", "64"])
    profile = json.loads(output.read_text())
    assert profile["method"] == "flat-patch-Haar-NNLS-ADC-floor-v2"
    assert profile["raw_metadata"]["black_levels"] == [4096] * 4
    assert profile["estimate"]["accepted_patches"] > 50
    assert profile["estimate"]["reason"] == "insufficient_intensity_span"
    assert max(profile["estimate"]["lower_clip_levels"]) < -0.06


@pytest.mark.parametrize(
    "black,white",
    [
        ([0] * 3, [1] * 4),
        ([0] * 4, [1] * 3),
        ([0, 0, 0, float("nan")], [1] * 4),
        ([0] * 4, [1, 1, 1, 0]),
    ],
)
def test_bad_phase_metadata_cannot_silently_change_clip_units(black, white):
    with pytest.raises(ValueError, match="four finite phase"):
        estimate_noise(
            np.ones((64, 64), np.float32) * 0.1,
            max_patches=64,
            metadata=SimpleNamespace(black_levels=black, white_levels=white),
        )
