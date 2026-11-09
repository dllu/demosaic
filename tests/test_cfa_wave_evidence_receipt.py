"""Reject altered phase, geometry, physical-wave and rank bindings."""

import copy

import pytest
import torch
from cfa_wave_evidence_receipt import describe_cfa, describe_cfa_support, validate_cfa
from pooled_wave_evidence_receipt import validate_support

from demosaic.cfa import color_indices
from demosaic.late_cfa_innovation_wave import cfa_innovation_wave_maps
from demosaic.late_innovation_wave import innovation_phase_bins
from demosaic.late_pooled_phase_wave import fixed_bin_wave_maps
from demosaic.late_spatial_context_wave import fixed_bin_support_context


def receipt(pattern):
    torch.manual_seed(19802)
    field = torch.randn(1, 4, 32, 48) * 0.003
    noise = torch.full_like(field, 1e-6)
    colors = color_indices(pattern)
    bins, valid, selection = innovation_phase_bins(field, noise, colors, peaks=2)
    large, waves, evidence = cfa_innovation_wave_maps(
        field, noise, colors, bins, valid, window=9, stride=8
    )
    small, support = fixed_bin_support_context(
        field, noise, colors, bins, valid, windows=(7, 3), stride=4
    )
    aux = {
        "wave_selection": selection,
        "cfa_context": torch.cat((large[:, :, :6], small, large[:, :, 6:]), 2),
        "cfa_waves": waves,
        "cfa_evidence": evidence,
        "wave_support": support,
    }
    config = {
        "evidence_peaks": 2,
        "evidence_window": 9,
        "evidence_stride": 8,
        "support_windows": [7, 3],
        "support_stride": 4,
    }
    _, old = fixed_bin_wave_maps(field, noise, colors, bins, valid, window=9, stride=8)
    return aux, config, field, colors, old


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_actual_geometry_and_historical_green_bridge(pattern):
    from lossless_native import fingerprint

    aux, config, field, colors, old = receipt(pattern)
    record = describe_cfa(aux)
    validate_cfa(record, field.shape, colors.numpy(), config)
    support = describe_cfa_support(aux)
    validate_support(support, field.shape, record["selection"], config)
    assert record["legacy_green_center_power"] == fingerprint(old["local_center_power"].numpy())


@pytest.mark.parametrize(
    "change",
    [
        "canonical",
        "bin",
        "rank",
        "geometry",
        "wave_shape",
        "wave_hash",
        "rank_count",
        "power_shape",
    ],
)
def test_modified_measurement_receipt_is_rejected(change):
    aux, config, field, colors, _ = receipt("RGGB")
    record = copy.deepcopy(describe_cfa(aux))
    if change == "canonical":
        record["fields"]["canonical_phase_indices"]["sha256"] = "0" * 64
    elif change == "bin":
        record["selection"]["bin_yx"][0][0][0] = [0, 0]
    elif change == "rank":
        record["selection"]["rank"][0][0][0] = 9
    elif change == "geometry":
        record["fields"]["boxes_xywh"]["sha256"] = "0" * 64
    elif change == "wave_shape":
        record["physical_waves"]["shape"][2] = 2
    elif change == "wave_hash":
        record["physical_waves"]["sha256"] = "invalid"
    elif change == "rank_count":
        record["wave_gram_rank_counts"]["2"] += 1
    elif change == "power_shape":
        record["fields"]["nominal_center_power"]["shape"][2] = 2
    with pytest.raises(AssertionError):
        validate_cfa(record, field.shape, colors.numpy(), config)


def test_ADC_only_measurements_absent():
    aux = {
        key: None
        for key in ["wave_selection", "cfa_evidence", "cfa_context", "cfa_waves", "wave_support"]
    }
    assert describe_cfa(aux) is describe_cfa_support(aux) is None
