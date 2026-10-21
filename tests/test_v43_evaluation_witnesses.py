"""Catch a changed reference model, coverage or physical-input sample across studies."""

import copy

import pytest
from evaluate_v43_quality_trial import check_reference_witnesses


def observations():
    return [
        {
            "model_SHA256": name,
            "forwards": 3108,
            "DINO_calls": 3108,
            "observations": 12404,
            "sampled_input_hashes_before_after_exact": [
                {"forward": 1, "sha256": "observation-one"},
                {"forward": 256, "sha256": "observation-two"},
            ],
        }
        for name in ("V43", "V93", "V94", "V95")
    ]


def test_reference_identity_follows_the_new_order_without_reusing_predictions():
    old = observations()
    fresh = copy.deepcopy([old[0], old[3], old[1], old[2]])
    result = check_reference_witnesses(fresh, old)
    assert set(result) == {"V43", "V95"}
    assert all(r["sampled_input_hashes_exact_previous"] == 2 for r in result.values())


@pytest.mark.parametrize("index", [0, 1])
@pytest.mark.parametrize("changed", ["weight", "forwards", "DINO", "coverage", "input", "missing"])
def test_reference_gate_rejects_changed_identity_counts_or_physical_samples(index, changed):
    old = observations()
    fresh = copy.deepcopy([old[0], old[3], old[1], old[2]])
    value = fresh[index]
    if changed == "weight":
        value["model_SHA256"] = "different-weights"
    elif changed == "forwards":
        value["forwards"] -= 1
    elif changed == "DINO":
        value["DINO_calls"] -= 1
    elif changed == "coverage":
        value["observations"] -= 1
    elif changed == "input":
        value["sampled_input_hashes_before_after_exact"][0]["sha256"] = "different-noise"
    else:
        value["sampled_input_hashes_before_after_exact"].pop()
    with pytest.raises(AssertionError):
        check_reference_witnesses(fresh, old)
