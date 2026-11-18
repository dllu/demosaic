"""Screening previews and native scoring use disjoint RAW sites."""

import numpy as np
import torch

from demosaic.screened_scene_donors import donor_affinities, retain_near_preview, screening_preview
from demosaic.search_donor_geometry import screening_mask


def test_scene_preview_contains_only_the_common_absolute_screening_sites():
    raw = np.random.default_rng(113).uniform(0.02, 0.2, (140, 88)).astype(np.float32)
    scope = screening_mask((0, 0, 88, 140))
    masked = np.where(scope, raw, np.nan)
    options = {"long_side": 30, "exposure": 1.2}
    a, grid = screening_preview(raw, "GRBG", [1, 1, 1], np.eye(3), **options)
    b, other = screening_preview(masked, "GRBG", [1, 1, 1], np.eye(3), **options)
    torch.testing.assert_close(a, b, rtol=0, atol=0)
    assert grid == other
    assert grid.preview_hw == (30, 19)


def test_near_intervention_preserves_the_original_coordinates():
    preview, grid = screening_preview(
        np.random.default_rng(9).uniform(0.02, 0.12, (128, 128)).astype(np.float32),
        "RGGB",
        [1, 1, 1],
        np.eye(3),
        long_side=32,
    )
    retained = retain_near_preview(preview, grid, (16, 32, 64, 48))
    torch.testing.assert_close(retained[..., 8:20, 4:20], preview[..., 8:20, 4:20], rtol=0, atol=0)
    torch.testing.assert_close(
        retained[..., 0, 0], preview[..., 8:20, 4:20].mean((-2, -1)), rtol=0, atol=0
    )
    assert not torch.equal(preview[..., 0, 0], retained[..., 0, 0])


def test_scene_affinity_uses_aligned_donor_positions():
    _, grid = screening_preview(np.full((256, 256), 0.08), "RGGB", [1, 1, 1], np.eye(3))
    fields = []
    for stride in (4, 8, 16):
        canvas = torch.zeros((1, 2, 64 // stride, 64 // stride))
        canvas[:, 0, : canvas.shape[-2] // 2, :] = 1
        canvas[:, 1, canvas.shape[-2] // 2 :, :] = 1
        fields.append(canvas)
    anchor = (96, 8, 64, 64)
    same = (8, 8, 64, 64)
    different = (8, 184, 64, 64)
    first, second = donor_affinities(fields, grid, [same, different], anchor)
    assert first > 0.99 and second < 0.01
