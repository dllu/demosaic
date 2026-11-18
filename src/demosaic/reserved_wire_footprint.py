"""Locate a shared wire footprint using a fixed reserve of query RAW sites."""

from itertools import product

import numpy as np

from .experiments.evaluation.withheld import stratified_split
from .local_validated_waves import fit_local_candidate
from .search_donor_geometry import _native_view, _validate_search, screening_mask

CENTERS = tuple(np.linspace(0.25, 0.75, 9))
RADIUS_FRACTION = 0.43
MINIMUM_LOCALIZATION = 1.0


def wire_footprint(shape, center_xy):
    """Fixed broad native cosine taper, in coordinates local to the query."""
    h, w = shape
    x, y = center_xy
    yy, xx = np.ogrid[:h, :w]
    radius = np.hypot(xx - x, yy - y) / (RADIUS_FRACTION * min(h, w))
    return np.where(radius < 1, np.cos((np.pi / 2) * np.minimum(radius, 1)) ** 2, 0)


def _standardized_gain(observed, reference, prediction):
    difference = prediction - reference
    norm = np.linalg.norm(difference)
    return float((observed - reference) @ difference / norm - norm / 2) if norm else 0.0


def _reserved_scores(raw, cfa, fold, test, centers, config, guide, active, shot, read):
    fitted = fit_local_candidate(
        raw,
        cfa,
        fold,
        shot=shot,
        read=read,
        config=config,
        guide_frequencies_xy=guide,
        phase_bins=8,
        phase_harmonics=((1,), (1,)),
    )
    discover = (fold & (cfa == 1)).ravel()
    confirm = (test & (cfa == 1)).ravel()
    sigma = np.sqrt(fitted.variance_cfa.ravel())
    learn, observe = raw.ravel()[discover] / sigma[discover], raw.ravel()[confirm] / sigma[confirm]
    train_design = fitted.design[discover] / sigma[discover, None]
    test_design = fitted.design[confirm] / sigma[confirm, None]
    allowed = np.ones(train_design.shape[1], bool)
    for direction, (start, stop) in enumerate(fitted.wave_slices):
        allowed[start:stop] = active[direction]

    def predict(columns):
        coef = np.linalg.lstsq(train_design[:, columns], learn, rcond=1e-10)[0]
        return test_design[:, columns] @ coef

    uniform_prediction = predict(allowed)
    scores = np.zeros((2, len(centers), 2), np.float64)
    for direction, (start, stop) in enumerate(fitted.wave_slices):
        if not active[direction]:
            continue
        absent = allowed.copy()
        absent[start:stop] = False
        null = predict(absent)
        original_train = train_design[:, start:stop].copy()
        original_test = test_design[:, start:stop].copy()
        for index, xy in enumerate(centers):
            weight = wire_footprint(raw.shape, xy).ravel()
            train_design[:, start:stop] = original_train * weight[discover, None]
            test_design[:, start:stop] = original_test * weight[confirm, None]
            local = predict(allowed)
            scores[direction, index, 0] = _standardized_gain(observe, null, local)
            scores[direction, index, 1] = _standardized_gain(observe, uniform_prediction, local)
        train_design[:, start:stop] = original_train
        test_design[:, start:stop] = original_test
    return scores


def select_wire_footprint(
    packed,
    colors,
    query,
    guide_frequencies_xy,
    active,
    *,
    shot,
    read,
    config,
    record_partner=False,
):
    """Compare local vs uniform carriers on disjoint parts of the reserved RAW.

    A single direction may locate the footprint. The subsequent query fits and
    validation must use the complement of the screening mask. The two choices
    require positive gains over both references in both reserve folds, at
    thresholds zero and one respectively.
    The optional partner receipt records the other direction's scores at the
    selected center.
    """
    _validate_search(query, shot, read)
    raw, cfa = _native_view(packed, colors, query)
    if len(active) != 2 or any(type(a) is not bool for a in active):
        raise ValueError("Require two fixed active-direction flags")
    reserved = screening_mask(query)
    raw = np.where(reserved, raw, np.nan)
    if not np.isfinite(raw[reserved]).all():
        raise ValueError("Require finite RAW in the footprint reserve")
    if not any(active):
        return {"screened": None, "confirmed": None}, {"winner": None, "reason": "no guide"}
    h, w = raw.shape
    centers = tuple((fx * (w - 1), fy * (h - 1)) for fx, fy in product(CENTERS, repeat=2))
    halves = stratified_split(raw.shape, config.split_seed + 346284)
    folds = (reserved & halves, reserved & ~halves)
    scores = np.stack(
        [
            _reserved_scores(
                raw, cfa, fold, test, centers, config, guide_frequencies_xy, active, shot, read
            )
            for fold, test in (folds, folds[::-1])
        ]
    )
    present, locality = np.min(scores, axis=0).transpose(2, 0, 1)
    ranks = np.where(present > 0, np.minimum(present, locality), -np.inf)
    direction, index = np.unravel_index(ranks.argmax(), ranks.shape)
    if not np.isfinite(ranks[direction, index]):
        return {"screened": None, "confirmed": None}, {"winner": None, "reason": "no crossed wave"}
    gain = float(ranks[direction, index])
    center = centers[index]
    footprint = wire_footprint(raw.shape, center) if gain > 0 else None
    evidence = {}
    if record_partner and all(active):
        peer = scores[:, 1 - direction, index]
        evidence["partner"] = {
            "wave_scores": peer[:, 0].tolist(),
            "localization_scores": peer[:, 1].tolist(),
        }
    return {
        "screened": footprint,
        "confirmed": footprint if gain > MINIMUM_LOCALIZATION else None,
    }, {
        "winner": {
            "direction": int(direction),
            "center_xy": center,
            "wave_scores": scores[:, direction, index, 0].tolist(),
            "localization_scores": scores[:, direction, index, 1].tolist(),
        },
        "admitted": gain > 0,
        "confirmed": gain > MINIMUM_LOCALIZATION,
        "reason": "localized" if gain > 0 else "uniform",
        **evidence,
    }
