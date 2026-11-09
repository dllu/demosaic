"""Cross-scale input bindings, tamper rejection, bounds and ADC absence."""

import copy

import pytest
import torch
from cfa_wave_evidence_receipt import validate_cfa
from scale_cfa_evidence_receipt import (
    describe_legacy_cfa,
    describe_scale_support,
    validate_scale_support,
)
from test_cfa_wave_evidence_receipt import receipt

from demosaic.cfa_scale_support import cfa_cross_scale_support


def measured(pattern="RGGB"):
    aux, config, field, colors, _ = receipt(pattern)
    variance = torch.full_like(field, 1e-6)
    context, support = cfa_cross_scale_support(
        field,
        variance,
        colors,
        aux["wave_selection"]["bin_yx"],
        aux["wave_selection"]["valid"],
        windows=(9, 7, 3),
        strides=(8, 4, 4),
    )
    aux["cfa_context"] = torch.cat((aux["cfa_context"], context), 2)
    aux["scale_support"] = support
    return aux, config, field, colors


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_actual_scale_geometry_and_unchanged_legacy_binding(pattern):
    aux, config, field, colors = measured(pattern)
    legacy = describe_legacy_cfa(aux)
    validate_cfa(legacy, field.shape, colors.numpy(), config)
    record = describe_scale_support(aux)
    validate_scale_support(record, field.shape, legacy["selection"], config, legacy)


@pytest.mark.parametrize(
    "damage",
    [
        "window",
        "stride",
        "full_context",
        "legacy",
        "agreement_dtype",
        "bound_shape",
        "boxes",
        "canonical",
        "amplitude_dtype",
        "covariance_shape",
        "rank_count",
        "finite",
    ],
)
def test_changed_support_binding_rejects(damage):
    aux, config, field, _ = measured()
    legacy = describe_legacy_cfa(aux)
    record = copy.deepcopy(describe_scale_support(aux))
    if damage == "window":
        record["windows"][0] += 2
    elif damage == "stride":
        record["strides"][1] += 1
    elif damage == "full_context":
        record["context"]["shape"][2] = 24
    elif damage == "legacy":
        record["legacy_context"]["sha256"] = "0" * 64
    elif damage == "agreement_dtype":
        record["agreement"]["dtype"] = "<f8"
    elif damage == "bound_shape":
        record["nominal_interpolated_trace_bound"]["shape"][2] = 2
    elif damage == "boxes":
        record["scales"][1]["fields"]["boxes_xywh"]["sha256"] = "0" * 64
    elif damage == "canonical":
        record["scales"][2]["fields"]["canonical_phase_indices"]["sha256"] = "0" * 64
    elif damage == "amplitude_dtype":
        record["scales"][1]["fields"]["canonical_center_amplitudes"]["dtype"] = "<f8"
    elif damage == "covariance_shape":
        record["scales"][0]["fields"]["nominal_untransported_center_covariance"]["shape"][-1] = 3
    elif damage == "rank_count":
        record["scales"][2]["rank_counts"]["2"] += 1
    elif damage == "finite":
        record["finite_bounded_agreement_and_nonnegative_nominal_trace"] = False
    with pytest.raises(AssertionError):
        validate_scale_support(record, field.shape, legacy["selection"], config, legacy)


@pytest.mark.parametrize(
    "damage",
    ["nonfinite", "unbounded", "negative_trace", "asymmetric_covariance", "indefinite_covariance"],
)
def test_bad_actual_values_reject_before_fingerprinting(damage):
    aux, _, _, _ = measured()
    if damage == "nonfinite":
        aux["cfa_context"][0, 0, 24, 0, 0] = float("nan")
    elif damage == "unbounded":
        aux["cfa_context"][0, 0, 24, 0, 0] = 2
    elif damage == "negative_trace":
        aux["scale_support"]["nominal_interpolated_trace_bound"][0, 0, 0, 0, 0, 0] = -1
    else:
        cov = aux["scale_support"]["scale_geometry"][0]["nominal_untransported_center_covariance"]
        if damage == "asymmetric_covariance":
            cov[0, 0, 0, 0, 0, 1] += 1
        else:
            cov[0, 0, 0, 0, 0, 0] = -1
    with pytest.raises((AssertionError, ValueError)):
        describe_scale_support(aux)


def test_ADC_receipts_absent():
    aux = dict.fromkeys(
        [
            "wave_selection",
            "cfa_evidence",
            "cfa_context",
            "cfa_waves",
            "wave_support",
            "scale_support",
        ]
    )
    assert describe_legacy_cfa(aux) is describe_scale_support(aux) is None
