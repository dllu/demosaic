"""Verify ranking and held-out semantics for a larger donor catalog."""

import numpy as np
import torch

import demosaic.scene_window_donors as windows
from demosaic.scene_context import SceneGrid
from demosaic.screened_scene_donors import donor_affinities
from demosaic.search_donor_geometry import screening_mask


def test_rejected_affinity_winner_is_fixed_before_reserved_samples(monkeypatch):
    query = (128, 128, 128, 128)
    boxes = [(0, 128, 128, 128), (256, 128, 128, 128), (128, 0, 128, 128), (128, 256, 128, 128)]
    yy, xx = np.indices((128, 128))
    layout = np.array([0, 1, 1, 2])
    raw = 0.13 + 0.025 * np.cos(2 * np.pi * (0.106 * xx + 0.044 * yy))
    donors = []
    for i, box in enumerate(boxes):
        samples = raw if i > 1 else np.where(screening_mask(box), raw, 0.13)
        packed = samples.reshape(64, 2, 64, 2).transpose(1, 3, 0, 2).reshape(4, 64, 64)
        donors.append((packed, layout, box))

    validate = windows._confirm_pair
    checks = []

    def observed(left, right, *args, **kwargs):
        checks.append((left[0], right[0]))
        return validate(left, right, *args, **kwargs)

    monkeypatch.setattr(windows, "_confirm_pair", observed)
    scores = {"top": [1, 1, 0.4, 0.4], "duplicate": [1, 1, 0.3, 0.3], "other": [0, 0, 1, 1]}
    results = windows.rank_scene_windows(donors, query, shot=8e-5, read=2.56e-8, affinities=scores)
    assert checks == [(boxes[0], boxes[1]), (boxes[2], boxes[3])]
    assert (
        results["top"]["candidate_indices"] == results["duplicate"]["candidate_indices"] == [0, 1]
    )
    assert results["top"]["active"] == [False, False]
    assert results["other"]["active"] == [True, False]


def test_route_lowers_affinity_for_a_similar_endpoint_across_another_surface():
    # Both endpoints and the query match. Only the left path crosses the stripe.
    grid = SceneGrid((128, 128), (128, 128), (128, 128))
    feature = torch.zeros((1, 2, 128, 128))
    feature[:, 0] = 1
    feature[:, 0, :, 24:44] = 0
    feature[:, 1, :, 24:44] = 1
    maps = tuple(feature[:, :, ::s, ::s] for s in (4, 8, 16))
    query = (48, 48, 32, 32)
    boxes = [(0, 48, 22, 32), (106, 48, 22, 32)]
    end = donor_affinities(maps, grid, boxes, query)
    linked = windows.corridor_affinities(maps, grid, boxes, query, end)
    np.testing.assert_allclose(end, 1, atol=1e-6)
    assert linked[0] < 0.8 and linked[1] > 0.99
