"""Physical CFA positions, tile seams and boundary extension in optional inference."""

import numpy as np
import pytest

from demosaic.cli import parser
from demosaic.phase_harmonic import refine_phase_harmonics


def mosaic(image, colors):
    raw = np.empty(image.shape[-2:], dtype=np.float32)
    for p, c in enumerate(colors):
        raw[p // 2 :: 2, p % 2 :: 2] = image[c, p // 2 :: 2, p % 2 :: 2]
    return raw


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_wave_crosses_internal_seams_and_odd_complete_image(colors):
    y, x = np.mgrid[:401, :531]
    base = np.full((3, 401, 531), 0.02, dtype=np.float32)
    wave = np.cos(2 * np.pi * (0.0625 * x + 0.09375 * y))
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * wave
    raw = mosaic(target, colors)
    before = raw.copy()
    actual, stats = refine_phase_harmonics(raw, colors, base, shot=0, read=1e-7)
    region = (..., slice(48, -48), slice(48, -48))
    assert actual.shape == base.shape and actual.dtype == np.float32
    assert np.mean((actual[region] - target[region]) ** 2) < 0.015 * np.mean(
        (base[region] - target[region]) ** 2
    )
    # Check narrow bands around regular seams and the final nonregular origin.
    for seam in [128, 146, 256, 276]:
        error = actual[:, 48:-48, seam - 2 : seam + 2] - target[:, 48:-48, seam - 2 : seam + 2]
        assert np.sqrt(np.mean(error**2)) < 0.0002
    np.testing.assert_array_equal(raw, before)
    np.testing.assert_array_equal(base, np.full_like(base, 0.02))
    assert stats["patches"] == stats["active_patches"] == 12


def test_small_image_extension_preserves_phases_and_ADC_bypass():
    colors = [1, 2, 0, 1]
    base = np.full((3, 7, 9), 0.02, dtype=np.float32)
    raw = mosaic(base, colors)
    actual, stats = refine_phase_harmonics(raw, colors, base, shot=0, read=1e-7)
    np.testing.assert_array_equal(actual, base)
    assert stats["patches"] == 1 and stats["active_patches"] == 0
    actual, stats = refine_phase_harmonics(raw, colors, base, shot=0, read=0)
    np.testing.assert_array_equal(actual, base)
    assert stats["ADC_only_bypass"] and stats["patches"] == 0


@pytest.mark.parametrize("stride", [0, 3, 194, 128.0])
def test_invalid_stride_rejected(stride):
    with pytest.raises(ValueError, match="Stride"):
        refine_phase_harmonics(
            np.zeros((7, 9)), [0, 1, 1, 2], np.zeros((3, 7, 9)), shot=0, read=1e-7, stride=stride
        )


def test_cli_refinement_is_explicit():
    args = parser().parse_args(["infer", "model.pt", "input.npy", "output.tiff"])
    assert not args.phase_harmonic and args.phase_harmonic_stride == 128
    assert args.phase_harmonic_envelope == "complex"
    args = parser().parse_args(
        [
            "infer",
            "model.pt",
            "input.npy",
            "output.tiff",
            "--phase-harmonic",
            "--phase-harmonic-stride",
            "192",
        ]
    )
    assert args.phase_harmonic and args.phase_harmonic_stride == 192
