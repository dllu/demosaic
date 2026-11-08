import copy

import pytest
from pooled_wave_evidence_receipt import describe_support, validate_support
from test_late_local_phase_evidence_matching import fixture

from demosaic.late_local_phase_evidence_matching import local_phase_evidence_maps
from demosaic.late_spatial_context_wave import fixed_bin_support_context


def example():
    raw, variance, colors = fixture()
    _, evidence = local_phase_evidence_maps(raw, variance, colors, peaks=2, window=9, stride=8)
    context, support = fixed_bin_support_context(
        raw.float(),
        variance.float(),
        colors,
        evidence["bin_yx"],
        evidence["valid"],
        windows=(9, 5),
        stride=4,
    )
    receipt = describe_support({"wave_support": support, "wave_support_context": context})
    return (
        receipt,
        list(raw.shape),
        {k: v.tolist() for k, v in evidence.items()},
        {"support_windows": [9, 5], "support_stride": 4, "evidence_peaks": 2},
    )


def test_actual_small_support_receipt_and_adc_absence():
    validate_support(*example())
    assert describe_support({"wave_support": None, "wave_support_context": None}) is None


@pytest.mark.parametrize(
    "change",
    [
        "window",
        "stride",
        "context_shape",
        "context_hash",
        "bin",
        "centers",
        "boxes",
        "power_shape",
        "power_hash",
        "finite",
    ],
)
def test_changed_support_contract_rejected(change):
    data = copy.deepcopy(example())
    r = data[0]
    if change == "window":
        r["windows"][0] += 2
    if change == "stride":
        r["stride"] += 1
    if change == "context_shape":
        r["context"]["shape"][2] = 6
    if change == "context_hash":
        r["context"]["sha256"] = "bad"
    if change == "bin":
        r["fields"]["bin_yx"]["sha256"] = "0" * 64
    if change == "centers":
        r["fields"]["centers_y"]["sha256"] = "0" * 64
    if change == "boxes":
        r["fields"]["boxes_xywh"]["sha256"] = "0" * 64
    if change == "power_shape":
        r["fields"]["center_power"]["shape"][-1] += 1
    if change == "power_hash":
        r["fields"]["center_power"]["sha256"] = "bad"
    if change == "finite":
        r["finite_context_and_center_power"] = False
    with pytest.raises(AssertionError):
        validate_support(*data)


def pooled_example():
    from pooled_wave_evidence_receipt import describe_pooled

    from demosaic.late_pooled_phase_wave import fixed_bin_wave_maps, pooled_phase_bins

    raw, variance, colors = fixture()
    bins, valid, selection = pooled_phase_bins(raw.float(), variance.float(), colors, peaks=2)
    features, fields = fixed_bin_wave_maps(
        raw.float(), variance.float(), colors, bins, valid, window=9, stride=8
    )
    record = describe_pooled(
        {"wave_selection": selection, "wave_evidence": fields, "wave_evidence_features": features}
    )
    return (
        record,
        list(raw.shape),
        colors.tolist(),
        {"evidence_peaks": 2, "evidence_stride": 8, "evidence_window": 9},
    )


def test_pooled_receipt_uses_actual_selected_wave_fields():
    from pooled_wave_evidence_receipt import validate_pooled

    validate_pooled(*pooled_example())


@pytest.mark.parametrize(
    "damage", ["rank", "bin", "score", "power", "feature_shape", "field_hash", "finite"]
)
def test_pooled_receipt_rejects_changed_geometry_and_invalid_contracts(damage):
    from pooled_wave_evidence_receipt import validate_pooled

    data = copy.deepcopy(pooled_example())
    r = data[0]
    if damage == "rank":
        r["selection"]["rank"][0][0][0] = 1
    if damage == "bin":
        r["selection"]["bin_yx"][0][0][0] = [0, 0]
    if damage == "score":
        r["selection"]["pooled_score"][0][0][0] = -1
    if damage == "power":
        r["selection"]["global_nominal_power"][0][0][0][0] = float("nan")
    if damage == "feature_shape":
        r["features"]["shape"][1] -= 1
    if damage == "field_hash":
        r["fields"]["bin_yx"]["sha256"] = "0" * 64
    if damage == "finite":
        r["finite_features_and_powers"] = False
    with pytest.raises(AssertionError):
        validate_pooled(*data)
