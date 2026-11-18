"""Opt-in RAW-supported correction for a crop of a fine, two-direction mesh."""

import numpy as np

from ._mesh_frequency import ADJACENT_SEARCH, adjacent_prior, infer_prior, query_phases
from ._mesh_profiles import extra_query_check, ribbon, supported_patch
from .cfa import PATTERNS
from .isolated_line import native_sites

TRANSLATIONS = ((0, 0),) + tuple(
    shift
    for distance in (2, 8, 16)
    for shift in ((distance, 0), (-distance, 0), (0, distance), (0, -distance))
)


def _crop(array, box, scale=1):
    x, y, width, height = (v // scale for v in box)
    return array[..., y : y + height, x : x + width]


def _contains(outer, inner):
    x, y, width, height = outer
    u, v, w, h = inner
    return x <= u and y <= v and u + w <= x + width and v + h <= y + height


def refine_local_raw_mesh(
    parent, scene, variance, colors, box, roi, *,
    shot, read, donor_span=80, suppress_gaps=False, adjacent_donors=False,
):
    """Return camera-linear RGB for ``roi`` using Bayer evidence in ``box``.

    ``parent`` is one float RGB prediction shaped [3, 2H, 2W]. ``scene`` and
    ``variance`` are co-registered packed Bayer arrays shaped [4, H, W].
    ``colors`` gives their CFA plane colors. ``box`` is an even-aligned 256×256
    fitting window. Both rectangles use native (x, y, width, height) pixels.
    ``shot`` and ``read`` are the RAW variance coefficients. The surrounding
    region should contain several nearby ``donor_span``-pixel windows.

    Donors propose frequencies. The query establishes phase, verifies both
    directions on disjoint sensor samples, and limits the eligible footprint.
    Unsupported crops return the parent pixels. Requires the ``eval`` extra.
    ``suppress_gaps`` further attenuates the correction where the central
    RAW query supports a break in the rear wire in three separate checks.
    ``adjacent_donors`` also tries a pair of frequencies from a nearby
    disjoint RAW tile when the usual donor fit yields no correction.
    """
    if scene.ndim != 3 or scene.shape[0] != 4 or variance.shape != scene.shape:
        raise ValueError("scene and variance must be packed Bayer arrays with matching shapes")
    width, height = 2 * scene.shape[2], 2 * scene.shape[1]
    if parent.shape != (3, height, width) or not np.issubdtype(parent.dtype, np.floating):
        raise ValueError("parent must be a floating-point camera RGB prediction matching the RAW")
    if tuple(colors) not in PATTERNS.values():
        raise ValueError("colors must describe a Bayer CFA pattern")
    if not np.isfinite((shot, read)).all() or shot < 0 or read < 0 or shot + read == 0:
        raise ValueError("shot and read must describe positive RAW noise variance")
    if donor_span < 64 or donor_span % 2:
        raise ValueError("donor_span must be even and at least 64 native pixels")
    left, top, w, h = box
    field = (0, 0, width, height)
    if (w, h) != (256, 256) or left % 2 or top % 2 or not _contains(field, box):
        raise ValueError("box must be an even-aligned 256×256 native window inside the input")
    if min(roi[2:]) <= 0 or not _contains(box, roi):
        raise ValueError("roi must have positive area and be contained in box")
    source = _crop(parent, roi)
    noise = {"shot": shot, "read": read}
    prior = infer_prior(scene, colors, box, noise, span=donor_span)
    correction, central_carriers = _overlap_correction(
        parent, scene, variance, colors, box, roi, noise, prior,
    )
    if adjacent_donors and (correction is None or not np.any(correction)):
        nearby = adjacent_prior(scene, colors, box, noise)
        correction, central_carriers = _overlap_correction(
            parent, scene, variance, colors, box, roi, noise, nearby, search=ADJACENT_SEARCH,
        )
    if correction is None:
        return source
    if suppress_gaps and central_carriers is not None and np.any(correction):
        from ._mesh_gap import confirmed_gap

        raw = _crop(scene, box, 2)
        x, y = native_sites(raw.shape[-2:], (-(w - 1) / 2, -(h - 1) / 2))
        front, rear = (ribbon(x, y, guide) for guide in central_carriers)
        mask = confirmed_gap(raw, colors, front, rear, shot, read)
        if mask is not None:
            inside = (roi[0] - left, roi[1] - top, roi[2], roi[3])
            correction = (correction * (1 - _crop(mask, inside))).astype(parent.dtype)
    return source + correction


def _overlap_correction(parent, scene, variance, colors, box, roi, noise, prior, **phase_options):
    if prior is None:
        return None, None
    left, top, width, height = box
    field = (0, 0, parent.shape[2], parent.shape[1])
    shot, read = noise["shot"], noise["read"]
    corrections = []
    central_carriers = None
    for dx, dy in TRANSLATIONS:
        query = (left + dx, top + dy, width, height)
        if not _contains(field, query) or not _contains(query, roi):
            continue
        raw = _crop(scene, query, 2)
        offset = dx // 2
        carriers, reserve, scores = query_phases(
            raw, colors, prior, noise, packed_offset=offset, **phase_options,
        )
        if dx == dy == 0:
            central_carriers = carriers
        current = _crop(parent, query)
        restored = current
        if max(scores) >= 3:
            try:
                if extra_query_check(raw, colors, carriers, shot, read, offset):
                    restored = supported_patch(
                        current,
                        raw,
                        _crop(variance, query, 2),
                        colors,
                        carriers,
                        reserve,
                        shot,
                        read,
                    )
            except np.linalg.LinAlgError:
                # A degenerate candidate has no reproducible amplitude estimate.
                pass
        inside = (roi[0] - query[0], roi[1] - query[1], roi[2], roi[3])
        corrections.append(_crop(restored - current, inside))
    active = sum(bool(np.any(delta)) for delta in corrections)
    if len(corrections) < 3 or 2 * active <= len(corrections):
        return None, None
    correction = np.median(np.stack(corrections), axis=0)
    return correction, central_carriers
