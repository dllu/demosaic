import numpy as np
import pytest
from dense_measurement_support import METHODS, cases, measure, target_frequencies, ratios
from dense_support_reference import reference


@pytest.mark.parametrize("method", list(METHODS))
@pytest.mark.parametrize("position", ["interior", "corner"])
@pytest.mark.parametrize("noise", ["uniform", "graded"])
def test_weighted_plane_operator_and_SNR_match_independent_QR(method, position, noise):
    for case in cases():
        if (
            case["method"] == method
            and case["position"] == position
            and case["noise"] == noise
            and case["target"] in [0, 13, 47]
        ):
            a, b = measure(case), reference(case)
            for key, value in b.items():
                np.testing.assert_allclose(a[key], value, rtol=2e-11, atol=2e-11)
            assert a["maximum_affine_annihilation_error"] < 1e-12


def test_fixed_target_grid_and_closed_case_cross():
    targets = target_frequencies()
    spec = cases()
    assert len(targets) == 48 and len(spec) == 1152 and len(set(c["id"] for c in spec)) == 1152
    for target in targets:
        fy, fx = target["native_fyx"]
        assert 1 / 16 < np.hypot(fy, fx) < 1 / 3 and abs(fy) < 0.25 and abs(fx) < 0.25
    assert len(set(tuple(t["native_fyx"]) for t in targets)) == 48


def test_unfitted_effective_support_exact_counts():
    for method, expected in [
        ("rect65_grid256", 4225),
        ("hann65_grid65", 16384 / 9),
        ("hann129_grid129", 65536 / 9),
    ]:
        case = next(c for c in cases() if c["method"] == method and c["position"] == "interior")
        assert measure(case)["raw_taper_effective_sample_count_without_affine"] == pytest.approx(
            expected
        )


def test_exact_frequency_quantization_changes_only_carrier_not_target():
    specs = [
        c
        for c in cases()
        if c["target"] == 1 and c["position"] == "interior" and c["noise"] == "uniform"
    ]
    result = ratios([measure(c) for c in specs], specs)
    assert len(result) == 4
    nearest = next(
        c
        for c in specs
        if c["method"] == "hann65_grid65" and c["mode"] == "nearest_available_carrier"
    )
    exact = dict(nearest, mode="exact_frequency")
    assert (
        measure(nearest)["phase_averaged_signal_to_noise_power"]
        < measure(exact)["phase_averaged_signal_to_noise_power"]
    )
