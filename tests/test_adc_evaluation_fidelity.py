import pytest
import torch
from evaluate_v43_quality_trial import (
    adc_profile_indices,
    adc_sample_fidelity,
    expected_adc_coverage,
)

from demosaic.cfa import PATTERNS, adc_cfa_projection, color_indices, mosaic


def coverage_inputs():
    zero = {"shot": 0.0, "read": 0.0, "name": "misleading-high-ISO-name"}
    positive = {"shot": 0.001, "read": 0.0, "name": "not-ADC"}
    protocol = {"patterns": list(PATTERNS), "conditions": [zero, positive]}
    colors = [{"condition": c} for c in [zero, positive, zero]]
    cameras = {
        "known": [{"conditioning": zero, "crops": [0, 1, 2]}],
        "unseen": [{"conditioning": positive, "crops": [0, 1, 2, 3]}],
    }
    gfx = {"gfx": positive, "gfx-highlights": zero}
    return protocol, 443, colors, cameras, gfx


def test_expected_coverage_uses_priors_and_actual_crop_counts():
    assert expected_adc_coverage(*coverage_inputs()) == {
        "photo": 1772,
        "texture": 224,
        "color": 2,
        "known": 3,
        "unseen": 0,
        "gfx": 0,
        "gfx-highlights": 2,
    }


@pytest.mark.parametrize("bad", ["duplicate-pattern", "extra-ADC", "nonfinite-prior"])
def test_ambiguous_coverage_fails_before_evaluation(bad):
    args = coverage_inputs()
    if bad == "duplicate-pattern":
        args[0]["patterns"][0] = args[0]["patterns"][1]
    elif bad == "extra-ADC":
        args[0]["conditions"].append({"shot": 0.0, "read": 0.0})
    else:
        args[4]["gfx"]["read"] = float("nan")
    with pytest.raises(AssertionError):
        expected_adc_coverage(*args)


def test_profile_selection_distinguishes_adc_from_gaussian_and_poisson_noise():
    assert adc_profile_indices([(None, 1, False)], 4) == [0, 1, 2, 3]
    assert adc_profile_indices([(object(), 1, True)], 4) == []
    assert adc_profile_indices([(None, 0.001, True)], 4) == []
    assert adc_profile_indices(
        [(None, 1, False), (object(), 1, True), (None, 0.001, True), (None, 1, False)], 4
    ) == [0, 3]


@pytest.mark.parametrize(
    "profiles,batch",
    [(None, 1), ([], 4), ([(None, 1, False)] * 2, 4), ([(None, 1, 0)], 1), ([(None, 1, False)], 0)],
)
def test_invalid_profile_coverage_fails(profiles, batch):
    with pytest.raises(AssertionError):
        adc_profile_indices(profiles, batch)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_saved_sample_measurement_detects_an_error_and_preserves_inputs(pattern):
    generator = torch.Generator().manual_seed(20261021)
    colors = color_indices(pattern)
    target = torch.rand(2, 3, 16, 20, generator=generator) * 0.6 + 0.2
    packed = mosaic(target, colors)
    wrong = target + torch.tensor([0.01, -0.02, 0.03])[None, :, None, None]
    before = wrong.clone(), packed.clone()
    rng = torch.get_rng_state()
    result = adc_sample_fidelity(wrong, packed, colors)
    assert result["observations"] == 2 and result["valid_CFA_values"] == packed.numel()
    assert result["maximum_absolute_error_sensor_units"] > 0.029
    projected = adc_cfa_projection(wrong, packed, colors, torch.tensor([[2.0, 1.0, 1.5]]))
    corrected = adc_sample_fidelity(projected, packed, colors)
    assert corrected["maximum_absolute_error_sensor_units"] <= 1e-6
    assert torch.equal(wrong, before[0]) and torch.equal(packed, before[1])
    assert torch.equal(rng, torch.get_rng_state())


def test_clipped_boundaries_and_empty_valid_support_are_reported_without_false_accuracy():
    colors = color_indices("RGGB")
    prediction = torch.ones(1, 3, 4, 8) * 100
    packed = (
        torch.tensor([0.0, 1.0, 1 / 65535, 1 - 1 / 65535]).reshape(1, 1, 1, 4).expand(1, 4, 2, 4)
    )
    result = adc_sample_fidelity(prediction, packed, colors)
    assert result["observations"] == 1 and result["valid_CFA_values"] == 0
    assert result["maximum_absolute_error_sensor_units"] is None


def test_nonfinite_observations_cannot_be_silently_masked_out():
    colors = color_indices("RGGB")
    packed = torch.ones(1, 4, 2, 2) * 0.5
    packed[..., 0, 0] = float("nan")
    with pytest.raises(AssertionError):
        adc_sample_fidelity(torch.ones(1, 3, 4, 4), packed, colors)
