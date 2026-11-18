"""Keep selection samples separate and require a repeatable donor signal."""

import numpy as np

from demosaic.search_donor_geometry import (
    _native,
    _screen_peaks,
    _verify_planes,
    candidate_boxes,
    recover_curved_direction,
    screening_mask,
    search_donor_geometry,
)

_COLORS = np.array([0, 1, 1, 2])
_NOISE = {"shot": 8e-5, "read": 2.56e-8}
_FREQUENCY = np.array([7.3, 2.1]) / 64


def _donor(box, phase, wave, *, amplitude=0.014):
    x, y, w, h = box
    yy, xx = np.mgrid[y : y + h, x : x + w]
    angle = 2 * np.pi * (xx * _FREQUENCY[0] + yy * _FREQUENCY[1] + phase)
    raw = 0.12 + (amplitude * np.cos(angle) if wave else 0 * xx)
    packed = raw.reshape(h // 2, 2, w // 2, 2).transpose(1, 3, 0, 2).reshape(4, h // 2, w // 2)
    return packed, _COLORS, box


def test_screening_uses_the_same_sites_across_overlapping_candidates():
    full = screening_mask((-16, -16, 128, 128))
    shifted = screening_mask((-14, -10, 64, 64))
    np.testing.assert_array_equal(full[6:70, 2:66], shifted)
    for a in (0, 1):
        for b in (0, 1):
            parity = full[a::2, b::2].reshape(32, 2, 32, 2)
            np.testing.assert_array_equal(parity.sum((1, 3)), np.ones((32, 32)))


def test_screening_ignores_validation_samples_and_validation_ignores_screening():
    packed, colors, box = _donor((-64, 0, 64, 64), 0.2, True)
    raw, layout = _native(packed, colors, box)
    mask = screening_mask(box)
    peaks = _screen_peaks(raw, layout, mask, **_NOISE)
    withheld = _screen_peaks(np.where(mask, raw, np.nan), layout, mask, **_NOISE)
    assert peaks and len(peaks) == len(withheld)
    for (f, a), (g, b) in zip(peaks, withheld, strict=True):
        np.testing.assert_array_equal(f, g)
        assert a == b
    seeds = np.stack([peaks[0][0]])
    eligible = ~mask
    original = _verify_planes(raw, layout, eligible, seeds, 72, **_NOISE)
    unseen = _verify_planes(np.where(eligible, raw, np.nan), layout, eligible, seeds, 72, **_NOISE)
    np.testing.assert_array_equal(original, unseen)


def test_donor_search_transfers_a_single_direction_and_rejects_a_flat_bracket():
    query = (0, 0, 64, 64)
    left = _donor((-64, 0, 64, 64), 0.17, True)
    right = _donor((64, 0, 64, 64), 0.81, True)
    above = _donor((0, -64, 64, 64), 0, False)
    below = _donor((0, 64, 64, 64), 0, False)
    fit = search_donor_geometry([above, right, below, left], query, **_NOISE)
    assert fit["donor_boxes"] == [list(right[2]), list(left[2])]
    assert fit["active"] == [True, False]
    np.testing.assert_allclose(fit["frequencies_xy"][0], _FREQUENCY, atol=0.0005, rtol=0)
    assert search_donor_geometry([above, below, left], query, **_NOISE)["active"] == [False, False]


def test_camera_candidates_include_bayer_aligned_abutting_boxes():
    frame, query = (2, 0, 512, 512), (136, 148, 256, 256)
    boxes = candidate_boxes(frame, query)
    assert (8, 128, 128, 128) in boxes
    assert (130, 20, 128, 128) in boxes
    for x, y, w, h in boxes:
        assert x % 2 == y % 2 == 0
        assert x + w <= 136 or x >= 392 or y + h <= 148 or y >= 404


def test_context_changes_the_selection_before_reserved_donor_scoring():
    query = (0, 0, 64, 64)
    left = _donor((-64, 0, 64, 64), 0.17, True)
    right = _donor((64, 0, 64, 64), 0.81, True)
    top = _donor((0, -64, 64, 64), 0.23, True, amplitude=0.022)
    bottom = _donor((0, 64, 64, 64), 0.46, True, amplitude=0.022)
    views = [left, right, top, bottom]
    spectral = search_donor_geometry(views, query, **_NOISE)
    affinity = [1, 1, 0.8, 0.8]
    weighted = search_donor_geometry(views, query, donor_affinity=affinity, **_NOISE)
    contextual = search_donor_geometry(
        views, query, donor_affinity=affinity, affinity_first=True, **_NOISE
    )
    assert spectral["donor_boxes"] == [list(top[2]), list(bottom[2])]
    assert weighted["donor_boxes"] == spectral["donor_boxes"]
    assert contextual["donor_boxes"] == [list(left[2]), list(right[2])]
    assert contextual["active"] == spectral["active"] == [True, False]
    np.testing.assert_allclose(contextual["frequencies_xy"][0], _FREQUENCY, atol=0.0005, rtol=0)
    views[0] = _donor(left[2], 0, False)
    held = search_donor_geometry(
        views, query, donor_affinity=affinity, affinity_first=True, **_NOISE
    )
    assert held["donor_boxes"] == spectral["donor_boxes"]


def test_reserved_donor_folds_verify_an_extra_swept_direction():
    width = 128
    query = (0, 0, width, width)
    weak = np.array([-0.019, 0.072])
    views = []
    for origin in (-width, width):
        y, x = np.mgrid[:width, origin : origin + width] - (width - 1) / 2
        first = 0.116 * x + 0.025 * y
        second = weak[0] * x + weak[1] * y + 0.00008 * x**2
        raw = 0.12 + 0.020 * np.cos(2 * np.pi * first) + 0.017 * np.cos(2 * np.pi * second)
        packed = raw.reshape(64, 2, 64, 2).transpose(1, 3, 0, 2).reshape(4, 64, 64)
        views.append((packed, _COLORS, (origin, 0, width, width)))
    first = search_donor_geometry(views, query, **_NOISE)
    assert first["active"] == [True, False]
    expanded = recover_curved_direction(views, query, first, **_NOISE)
    assert expanded["curved_direction_added"]
    assert expanded["active"] == [True, True]
    np.testing.assert_array_equal(expanded["frequencies_xy"][0], first["frequencies_xy"][0])
    np.testing.assert_allclose(expanded["frequencies_xy"][1], weak, atol=0.001, rtol=0)
