"""Structural bindings for new wide-band measurements; not calibrated confidence."""

import re

import numpy as np
from lossless_native import fingerprint


def validate_innovation_pooled(record, shape, colors, config, *, lower=1 / 64):
    b, c, h, w = shape
    k = config["evidence_peaks"]
    assert c == 4 and record["finite_features_and_powers"] is True
    s = record["selection"]
    assert set(s) == {
        "green_phase_indices",
        "bin_yx",
        "valid",
        "rank",
        "pooled_score",
        "global_nominal_power",
    }
    greens = np.asarray(s["green_phase_indices"], dtype="<i8")
    layout = np.asarray(colors)
    if layout.ndim == 1:
        layout = np.broadcast_to(layout, (b, 4))
    expected = np.stack([np.flatnonzero(v == 1) for v in layout])
    np.testing.assert_array_equal(greens, expected)
    ranks = np.asarray(s["rank"], dtype="<i8")
    np.testing.assert_array_equal(
        ranks, np.broadcast_to(np.arange(2 * k).reshape(k, 2).T, (b, 2, k))
    )
    bins = np.asarray(s["bin_yx"], dtype="<i8")
    valid = np.asarray(s["valid"], dtype=np.bool_)
    scores = np.asarray(s["pooled_score"])
    powers = np.asarray(s["global_nominal_power"])
    assert bins.shape == (b, 2, k, 2) and valid.shape == (b, 2, k)
    assert scores.shape == (b, 2, k) and powers.shape == (b, 2, k, 2)
    assert (
        np.isfinite(scores).all()
        and np.isfinite(powers).all()
        and (scores >= 0).all()
        and (powers >= 0).all()
    )
    assert (scores[~valid] == 0).all()
    for i in range(b):
        selected = bins[i][valid[i]]
        assert len(set(map(tuple, selected))) == len(selected)
        if len(selected):
            assert (selected >= 0).all() and (selected < np.asarray([h, w])).all()
            f = np.minimum(selected, np.asarray([h, w]) - selected) / np.asarray([h, w]) * 0.5
            radius = np.sqrt((f * f).sum(1))
            assert ((radius >= lower) & (radius <= 1 / 3)).all()
    f = record["features"]
    assert f["shape"] == [b, 2 * k * 10, h, w] and f["dtype"] == "<f4"
    assert re.fullmatch("[0-9a-f]{64}", f["sha256"])
    stride = config["evidence_stride"]
    win = config["evidence_window"]
    ay, ax = [np.unique([*range(0, n, stride), n - 1]).astype("<i8") for n in [h, w]]
    cy, cx = np.meshgrid(ay, ax, indexing="ij")
    centers = np.stack((cy.ravel(), cx.ravel()), 1)
    start = np.maximum(centers - win // 2, 0)
    end = np.minimum(centers + win // 2 + 1, [h, w])
    boxes = np.stack(
        (start[:, 1], start[:, 0], end[:, 1] - start[:, 1], end[:, 0] - start[:, 0]), 1
    )
    fields = record["fields"]
    exp = {
        "green_phase_indices": greens,
        "bin_yx": bins,
        "valid": valid,
        "centers_y": ay,
        "centers_x": ax,
        "boxes_xywh": boxes,
    }
    assert set(fields) == set(exp) | {"local_center_power"}
    for name, value in exp.items():
        assert fields[name] == fingerprint(value), name
    power = fields["local_center_power"]
    assert power["shape"] == [b, 2, k, 2, len(ay), len(ax)] and power["dtype"] == "<f8"
    assert re.fullmatch("[0-9a-f]{64}", power["sha256"])
