"""The wider-band receipt admits real low bins and rejects altered bindings."""

import copy

import pytest
import torch
from innovation_wave_evidence_receipt import validate_innovation_pooled
from pooled_wave_evidence_receipt import (
    describe_pooled,
    describe_support,
    validate_pooled,
    validate_support,
)

from demosaic.cfa import color_indices
from demosaic.late_innovation_wave import innovation_phase_bins
from demosaic.late_pooled_phase_wave import fixed_bin_wave_maps
from demosaic.late_spatial_context_wave import fixed_bin_support_context


@pytest.fixture(scope="module")
def record():
    y, x = torch.meshgrid(torch.arange(32), torch.arange(48), indexing="ij")
    value = 0.02 + 0.001 * torch.cos(2 * torch.pi * (y / 32 + x / 48))
    raw = value[None, None].expand(1, 4, -1, -1).contiguous()
    variance = torch.full_like(raw, 1e-6)
    colors = color_indices("RGGB")
    bins, valid, selection = innovation_phase_bins(raw, variance, colors, peaks=2)
    maps, evidence = fixed_bin_wave_maps(raw, variance, colors, bins, valid, window=9, stride=8)
    context, support = fixed_bin_support_context(
        raw, variance, colors, bins, valid, windows=(7, 3), stride=4
    )
    aux = {
        "wave_selection": selection,
        "wave_evidence": evidence,
        "wave_evidence_features": maps,
        "wave_support": support,
        "wave_support_context": context,
    }
    config = {
        "evidence_peaks": 2,
        "evidence_window": 9,
        "evidence_stride": 8,
        "support_windows": [7, 3],
        "support_stride": 4,
    }
    return describe_pooled(aux), describe_support(aux), raw.shape, colors.numpy(), config


def test_wide_receipt_and_fixed_support_accept_actual_low_measurement(record):
    pooled, support, shape, colors, config = record
    validate_innovation_pooled(pooled, shape, colors, config)
    validate_support(support, shape, pooled["selection"], config)
    with pytest.raises(AssertionError):
        validate_pooled(pooled, shape, colors, config)


@pytest.mark.parametrize("change", ["bin", "rank", "feature_hash", "geometry_hash"])
def test_altered_receipt_rejected(record, change):
    pooled, _, shape, colors, config = record
    bad = copy.deepcopy(pooled)
    if change == "bin":
        bad["selection"]["bin_yx"][0][0][0] = [0, 0]
    elif change == "rank":
        bad["selection"]["rank"][0][0][0] = 9
    elif change == "feature_hash":
        bad["features"]["sha256"] = "invalid"
    else:
        bad["fields"]["boxes_xywh"]["sha256"] = "0" * 64
    with pytest.raises(AssertionError):
        validate_innovation_pooled(bad, shape, colors, config)
