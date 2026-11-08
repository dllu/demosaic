"""Compact exact input-only support bindings; no confidence interpretation."""

import re

import numpy as np
from lossless_native import fingerprint


def describe_support(aux):
    if aux["wave_support"] is None:
        assert aux["wave_support_context"] is None
        return None
    fields = {k: v.detach().cpu().numpy() for k, v in aux["wave_support"].items()}
    context = aux["wave_support_context"].detach().cpu().numpy()
    if not np.isfinite(context).all() or not np.isfinite(fields["center_power"]).all():
        raise ValueError("Nonfinite support receipt")
    return {
        "windows": fields.pop("windows").tolist(),
        "stride": int(fields.pop("stride")),
        "context": fingerprint(context),
        "fields": {k: fingerprint(v) for k, v in fields.items()},
        "finite_context_and_center_power": True,
    }


def validate_support(record, shape, evidence, config):
    batch, channels, height, width = shape
    assert channels == 4
    windows, stride, peaks = (
        config["support_windows"],
        config["support_stride"],
        config["evidence_peaks"],
    )
    assert record["windows"] == list(windows) and record["stride"] == stride
    assert record["finite_context_and_center_power"] is True
    expected_context = {"shape": [batch, 2 * peaks, 12, height, width], "dtype": "<f4"}
    assert {k: record["context"][k] for k in expected_context} == expected_context
    assert re.fullmatch("[0-9a-f]{64}", record["context"]["sha256"])
    ay, ax = [np.unique([*range(0, n, stride), n - 1]).astype("<i8") for n in [height, width]]
    cy, cx = np.meshgrid(ay, ax, indexing="ij")
    centers = np.stack((cy.ravel(), cx.ravel()), 1)
    boxes = []
    for window in windows:
        start = np.maximum(centers - window // 2, 0)
        end = np.minimum(centers + window // 2 + 1, [height, width])
        boxes.append(
            np.stack(
                (start[:, 1], start[:, 0], end[:, 1] - start[:, 1], end[:, 0] - start[:, 0]), 1
            )
        )
    expected = {
        "centers_y": ay,
        "centers_x": ax,
        "boxes_xywh": np.stack(boxes),
        "bin_yx": np.asarray(evidence["bin_yx"], dtype="<i8"),
        "valid": np.asarray(evidence["valid"], dtype=np.bool_),
        "green_phase_indices": np.asarray(evidence["green_phase_indices"], dtype="<i8"),
    }
    assert set(record["fields"]) == set(expected) | {"center_power"}
    for key, value in expected.items():
        assert record["fields"][key] == fingerprint(value)
    power = record["fields"]["center_power"]
    assert power["shape"] == [batch, 2, 2, peaks, 2, len(ay), len(ax)] and power["dtype"] == "<f8"
    assert re.fullmatch("[0-9a-f]{64}", power["sha256"])


def describe_pooled(aux):
    if aux["wave_selection"] is None:
        assert aux["wave_evidence"] is aux["wave_evidence_features"] is None
        return None
    selection = {k: v.detach().cpu().tolist() for k, v in aux["wave_selection"].items()}
    fields = {k: v.detach().cpu().numpy() for k, v in aux["wave_evidence"].items()}
    features = aux["wave_evidence_features"].detach().cpu().numpy()
    assert np.isfinite(features).all() and np.isfinite(fields["local_center_power"]).all()
    return {
        "selection": selection,
        "fields": {k: fingerprint(v) for k, v in fields.items()},
        "features": fingerprint(features),
        "finite_features_and_powers": True,
    }


def validate_pooled(record, shape, colors, config):
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
            assert ((radius >= 1 / 16) & (radius <= 1 / 3)).all()
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
