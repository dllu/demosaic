"""Input-only V200 support bindings; retain the exact 24-channel V198 receipt.

Covariance and interpolation summaries concern a nominal fixed linear RAW-noise
model. They do not establish calibrated innovation confidence or flat safety.
"""

import numpy as np
from cfa_wave_evidence_receipt import checked_fingerprint, describe_cfa
from lossless_native import fingerprint


def describe_legacy_cfa(aux):
    context = aux["cfa_context"]
    return describe_cfa(dict(aux, cfa_context=None if context is None else context[:, :, :24]))


def describe_scale_support(aux):
    if aux["scale_support"] is None:
        assert aux["cfa_context"] is None
        return None
    context = aux["cfa_context"].detach().cpu().numpy()
    support = aux["scale_support"]
    assert context.shape[2] == 36 and np.isfinite(context).all()
    new = context[:, :, 24:]
    for offset in (0, 6):
        assert (
            np.hypot(new[:, :, offset : offset + 3], new[:, :, offset + 3 : offset + 6]) <= 1 + 2e-6
        ).all()
    bound = support["nominal_interpolated_trace_bound"].detach().cpu().numpy()
    assert bound.dtype == np.float64 and np.isfinite(bound).all() and (bound >= 0).all()
    geometry = []
    for scale in support["scale_geometry"]:
        arrays = {k: v.detach().cpu().numpy() for k, v in scale.items()}
        assert all(np.isfinite(v).all() for v in arrays.values())
        cov = arrays["nominal_untransported_center_covariance"]
        np.testing.assert_array_equal(cov, cov.swapaxes(-1, -2))
        a, b, d = cov[..., 0, 0], cov[..., 0, 1], cov[..., 1, 1]
        trace = a + d
        minimum_eigenvalue = (trace - np.hypot(a - d, 2 * b)) / 2
        assert (minimum_eigenvalue >= -2e-8 * np.maximum(abs(trace), 1e-30)).all()
        ranks = arrays["wave_gram_rank"]
        geometry.append(
            {
                "fields": {k: fingerprint(v) for k, v in arrays.items()},
                "rank_counts": {str(k): int((ranks == k).sum()) for k in (0, 1, 2)},
                "finite_amplitudes_covariance_geometry": True,
                "symmetric_nominal_covariance_PSD_within_roundoff": True,
            }
        )
    return {
        "windows": list(support["windows"]),
        "strides": list(support["strides"]),
        "legacy_context": fingerprint(context[:, :, :24]),
        "context": fingerprint(context),
        "agreement": fingerprint(new),
        "nominal_interpolated_trace_bound": fingerprint(bound),
        "scales": geometry,
        "finite_bounded_agreement_and_nonnegative_nominal_trace": True,
    }


def validate_scale_support(record, shape, selection, config, legacy):
    n, phases, h, w = shape
    k = 2 * config["evidence_peaks"]
    assert phases == 4
    windows = [config["evidence_window"], *config["support_windows"]]
    strides = [config["evidence_stride"], config["support_stride"], config["support_stride"]]
    assert record["windows"] == windows and record["strides"] == strides
    assert record["finite_bounded_agreement_and_nonnegative_nominal_trace"] is True
    assert record["legacy_context"] == legacy["context"]
    checked_fingerprint(record["context"], (n, k, 36, h, w), "<f4")
    checked_fingerprint(record["agreement"], (n, k, 12, h, w), "<f4")
    checked_fingerprint(record["nominal_interpolated_trace_bound"], (n, k, 3, 3, h, w), "<f8")
    assert len(record["scales"]) == 3
    for item, window, stride in zip(record["scales"], windows, strides, strict=True):
        assert item["finite_amplitudes_covariance_geometry"] is True
        assert item["symmetric_nominal_covariance_PSD_within_roundoff"] is True
        ay, ax = [
            np.unique([*range(0, length, stride), length - 1]).astype("<i8") for length in (h, w)
        ]
        cy, cx = np.meshgrid(ay, ax, indexing="ij")
        centers = np.stack((cy.ravel(), cx.ravel()), 1)
        start = np.maximum(centers - window // 2, 0)
        end = np.minimum(centers + window // 2 + 1, [h, w])
        boxes = np.stack(
            (start[:, 1], start[:, 0], end[:, 1] - start[:, 1], end[:, 0] - start[:, 0]), 1
        )
        fields = item["fields"]
        expected = {
            "canonical_phase_indices": legacy["fields"]["canonical_phase_indices"],
            "centers_y": fingerprint(ay),
            "centers_x": fingerprint(ax),
            "boxes_xywh": fingerprint(boxes),
            "bin_yx": fingerprint(np.asarray(selection["bin_yx"], dtype="<i8")),
            "valid": fingerprint(np.asarray(selection["valid"], dtype=np.bool_)),
        }
        assert set(fields) == set(expected) | {
            "canonical_center_amplitudes",
            "nominal_untransported_center_covariance",
            "wave_gram_rank",
        }
        for key, value in expected.items():
            assert fields[key] == value, key
        length = len(ay) * len(ax)
        checked_fingerprint(fields["canonical_center_amplitudes"], (n, k, 4, length), "<c16")
        checked_fingerprint(
            fields["nominal_untransported_center_covariance"], (n, k, 4, length, 2, 2), "<f8"
        )
        checked_fingerprint(fields["wave_gram_rank"], (n, k, length), "<i8")
        counts = item["rank_counts"]
        assert set(counts) == {"0", "1", "2"}
        assert all(type(v) is int and v >= 0 for v in counts.values())
        assert sum(counts.values()) == n * k * length
