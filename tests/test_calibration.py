import numpy as np
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
