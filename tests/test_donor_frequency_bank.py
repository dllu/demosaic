"""Independent donor confirmation and query reserve selection of a companion."""

import numpy as np

from demosaic.donor_frequency_bank import (
    donor_frequency_bank,
    screened_donor_tiles,
    select_bank_companion,
)
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.search_donor_geometry import screening_mask

LAYOUT = np.array([2, 1, 1, 0])
ANCHOR = (10 / 128, 3 / 128)
COMPANION = (-4 / 128, 11 / 128)
NOISE = {"shot": 0, "read": 1e-6}


def observation(box, *, include_companion):
    x, y, w, h = box
    yy, xx = np.indices((h, w))
    cfa = LAYOUT[(yy % 2) * 2 + xx % 2]
    rng = np.random.default_rng(x * 127 + y)
    anchor = 2 * np.pi * (ANCHOR[0] * (xx + x) + ANCHOR[1] * (yy + y))
    weak = 2 * np.pi * (COMPANION[0] * (xx + x) + COMPANION[1] * (yy + y))
    signal = 0.08 + 0.015 * np.cos(anchor + 0.43) + rng.normal(0, 0.001, cfa.shape)
    if include_companion:
        signal += np.array([-0.75, 1.0, 0.8])[cfa] * 0.003 * np.cos(weak + 0.14)
    return signal


def pack(raw):
    return raw.reshape(64, 2, 64, 2).transpose(1, 3, 0, 2).reshape(4, 64, 64)


def test_companion_survives_donor_and_reserved_query_checks():
    query = (128, 128, 128, 128)
    boxes = ((0, 128, 128, 128), (256, 128, 128, 128))
    views = [(pack(observation(b, include_companion=True)), LAYOUT, b) for b in boxes]
    tiles = screened_donor_tiles(views, query, **NOISE, localized=True)
    bank = donor_frequency_bank(
        tiles, query, [0.9, 0.8], np.array(ANCHOR), **NOISE, localized=True, family_degrees=20
    )
    assert any(
        r["donor_valid"] and np.linalg.norm(np.asarray(r["frequency_xy"]) - COMPANION) < 0.007
        for r in bank["shortlist"]
    )
    guide = {"frequencies_xy": [list(ANCHOR), [0.0, 0.08]], "active": [True, False]}
    config = LocalWaveConfig(window=128, stride=128, background="screened_curved4_step")
    raw = observation(query, include_companion=True)
    checkout = []
    for samples in (raw, np.where(screening_mask(query), raw, np.nan)):
        result = select_bank_companion(
            pack(samples), LAYOUT, query, guide, bank, **NOISE, config=config
        )
        checkout.append(result)
    (output, trace), withheld = checkout
    assert (output, trace) == withheld and trace["status"] == "selected"
    assert output["frequencies_xy"][0] == list(ANCHOR)
    assert output["active"] == [True, True]
    assert np.linalg.norm(np.asarray(output["frequencies_xy"][1]) - COMPANION) < 0.007

    null = pack(observation(query, include_companion=False))
    same, trace = select_bank_companion(null, LAYOUT, query, guide, bank, **NOISE, config=config)
    assert same == guide and trace["status"] == "uniform fallback"
