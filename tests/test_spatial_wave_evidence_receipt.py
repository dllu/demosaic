import copy

import pytest
from spatial_wave_evidence_receipt import describe_support, validate_support
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
