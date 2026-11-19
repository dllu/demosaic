"""Guard signed real FFT indexing and the phase search's donor order."""

import numpy as np
from scipy.fft import fft2

from demosaic.phase_witness import (
    PAD,
    SIDE,
    UNIQUE,
    WEIGHT,
    _gather,
    _neighborhood,
    _transform,
    measure_witnesses,
)


def test_indexed_real_fft_recovers_signed_coordinates():
    rng = np.random.default_rng(741)
    raw = rng.uniform(0.2, 0.3, (4, 128, 128)).astype(np.float32)
    transforms, _ = _transform(raw, 0.00128, 6.5536e-6)
    crop = raw[3, 56:72, 56:72]
    mean = (crop * WEIGHT).sum() / WEIGHT.sum()
    full = fft2((crop - mean) * WEIGHT, s=(PAD, PAD)) / 16
    signed = full[UNIQUE[:, 0] % PAD, UNIQUE[:, 1] % PAD]
    coords = (UNIQUE[:, 0] + UNIQUE[:, 1]) / (2 * PAD)
    phase = np.exp(-2j * np.pi * coords).astype(np.complex64)
    np.testing.assert_array_equal(_gather(transforms, 3)[7 * SIDE + 7], signed * phase)


def test_donor_accumulation_preserves_rounding_order():
    center = 7 * SIDE + 7
    green = np.zeros((SIDE**2, 1), dtype=np.complex64)
    green[[center - 2 * SIDE, center - 2, center + 2], 0] = [1e8, -1e8, 1]
    donor, variance = _neighborhood(
        green, np.ones(SIDE**2, dtype=np.float32), np.ones((1, 2), dtype=np.complex64)
    )
    np.testing.assert_array_equal(donor[center], [1.0])
    assert variance[center] == 4


def test_center_samples_do_not_nominate_phase():
    y, x = np.indices((256, 256))
    wave = 0.22 + 0.05 * np.cos(2 * np.pi * (0.121 * x - 0.074 * y))
    raw = np.stack([wave[p // 2 :: 2, p % 2 :: 2] for p in range(4)]).astype(np.float32)
    layout = [0, 1, 1, 2]
    noise = {"shot": 0.00128, "read": 6.5536e-6}
    reference = measure_witnesses(raw, layout, noise, pair_features=True)
    raw[:, 56:72, 56:72] = 0.22
    held = measure_witnesses(raw, layout, noise, pair_features=True)
    center = 7 * SIDE + 7
    np.testing.assert_array_equal(reference.frequency[center], held.frequency[center])
    np.testing.assert_array_equal(reference.phase[center], held.phase[center])
    np.testing.assert_array_equal(reference.pair_features[center], held.pair_features[center])
    assert np.max(abs(held.features[center, :, 2:6])) < 1e-5
