"""Describe measured CFA waves and validate their input-only geometry bindings."""

import re

import numpy as np
from lossless_native import fingerprint
from pooled_wave_evidence_receipt import describe_support


def describe_cfa_support(aux):
    return describe_support(
        {
            "wave_support": aux["wave_support"],
            "wave_support_context": None
            if aux["cfa_context"] is None
            else aux["cfa_context"][:, :, 6:18],
        }
    )


def describe_cfa(aux):
    if aux["wave_selection"] is None:
        assert aux["cfa_evidence"] is aux["cfa_context"] is aux["cfa_waves"] is None
        return None
    selection = {k: v.detach().cpu().tolist() for k, v in aux["wave_selection"].items()}
    fields = {k: v.detach().cpu().numpy() for k, v in aux["cfa_evidence"].items()}
    context, waves = [aux[k].detach().cpu().numpy() for k in ["cfa_context", "cfa_waves"]]
    assert all(np.isfinite(v).all() for v in [context, waves, fields["nominal_center_power"]])
    power = fields["nominal_center_power"]
    peaks = power.shape[1] // 2
    # Bridge the exact two-green nominal powers to the completed V197 journal.
    # Canonical CFA order is R,green0,green1,B; alternate rank groups reverse G.
    green = np.stack((power[:, :peaks, [1, 2]], power[:, peaks:, [2, 1]]), 1)
    return {
        "selection": selection,
        "fields": {k: fingerprint(v) for k, v in fields.items()},
        "context": fingerprint(context),
        "physical_waves": fingerprint(waves),
        "legacy_green_center_power": fingerprint(green),
        "wave_gram_rank_counts": {
            str(k): int((fields["wave_gram_rank"] == k).sum()) for k in [0, 1, 2]
        },
        "finite_context_waves_and_powers": True,
    }


def checked_fingerprint(record, shape, dtype):
    assert set(record) == {"shape", "dtype", "sha256"}
    assert record["shape"] == list(shape) and record["dtype"] == dtype
    assert re.fullmatch("[0-9a-f]{64}", record["sha256"])


def validate_cfa(record, shape, colors, config, *, lower=1 / 64):
    batch, channels, height, width = shape
    peaks = config["evidence_peaks"]
    count = 2 * peaks
    assert channels == 4 and record["finite_context_waves_and_powers"] is True
    layout = np.asarray(colors)
    if layout.ndim == 1:
        layout = np.broadcast_to(layout, (batch, 4))
    assert layout.shape == (batch, 4)
    allowed = np.array([[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
    assert (layout[:, None] == allowed).all(-1).any(-1).all()
    greens = np.stack([np.flatnonzero(v == 1) for v in layout]).astype("<i8")
    canonical = np.stack(
        [
            np.r_[np.flatnonzero(v == 0), np.flatnonzero(v == 1), np.flatnonzero(v == 2)]
            for v in layout
        ]
    ).astype("<i8")
    selection = record["selection"]
    assert set(selection) == {
        "green_phase_indices",
        "bin_yx",
        "valid",
        "rank",
        "pooled_score",
        "global_nominal_power",
    }
    np.testing.assert_array_equal(selection["green_phase_indices"], greens)
    np.testing.assert_array_equal(
        selection["rank"], np.broadcast_to(np.arange(count).reshape(peaks, 2).T, (batch, 2, peaks))
    )
    bins = np.asarray(selection["bin_yx"], dtype="<i8")
    valid = np.asarray(selection["valid"], dtype=np.bool_)
    scores, powers = [np.asarray(selection[k]) for k in ["pooled_score", "global_nominal_power"]]
    assert bins.shape == (batch, 2, peaks, 2) and valid.shape == (batch, 2, peaks)
    assert scores.shape == (batch, 2, peaks) and powers.shape == (batch, 2, peaks, 2)
    assert (
        np.isfinite(scores).all()
        and np.isfinite(powers).all()
        and (scores >= 0).all()
        and (powers >= 0).all()
    )
    assert (scores[~valid] == 0).all()
    for item in range(batch):
        chosen = bins[item][valid[item]]
        assert len(set(map(tuple, chosen))) == len(chosen)
        assert (chosen >= 0).all() and (chosen < [height, width]).all()
        f = np.minimum(chosen, np.asarray([height, width]) - chosen) / [height, width] / 2
        radius = np.sqrt((f * f).sum(-1))
        assert ((radius >= lower) & (radius <= 1 / 3)).all()
    stride, window = config["evidence_stride"], config["evidence_window"]
    ay, ax = [np.unique([*range(0, n, stride), n - 1]).astype("<i8") for n in [height, width]]
    cy, cx = np.meshgrid(ay, ax, indexing="ij")
    centers = np.stack((cy.ravel(), cx.ravel()), 1)
    start = np.maximum(centers - window // 2, 0)
    end = np.minimum(centers + window // 2 + 1, [height, width])
    boxes = np.stack(
        (start[:, 1], start[:, 0], end[:, 1] - start[:, 1], end[:, 0] - start[:, 0]), 1
    )
    expected = {
        "canonical_phase_indices": canonical,
        "bin_yx": bins,
        "valid": valid,
        "centers_y": ay,
        "centers_x": ax,
        "boxes_xywh": boxes,
    }
    fields = record["fields"]
    assert set(fields) == set(expected) | {"nominal_center_power", "wave_gram_rank"}
    for key, value in expected.items():
        assert fields[key] == fingerprint(value), key
    checked_fingerprint(fields["nominal_center_power"], (batch, count, 4, len(ay), len(ax)), "<f8")
    checked_fingerprint(fields["wave_gram_rank"], (batch, count, len(ay) * len(ax)), "<i8")
    checked_fingerprint(record["context"], (batch, count, 24, height, width), "<f4")
    checked_fingerprint(record["physical_waves"], (batch, count, 3, 2, height, width), "<f4")
    checked_fingerprint(
        record["legacy_green_center_power"], (batch, 2, peaks, 2, len(ay), len(ax)), "<f8"
    )
    ranks = record["wave_gram_rank_counts"]
    assert set(ranks) == {"0", "1", "2"}
    assert all(type(v) is int and v >= 0 for v in ranks.values())
    assert sum(ranks.values()) == batch * count * len(ay) * len(ax)
