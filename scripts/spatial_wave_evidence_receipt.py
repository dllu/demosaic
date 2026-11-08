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
