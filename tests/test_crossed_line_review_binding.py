"""A data-only review must preserve every input outside the changed source domain."""

from copy import deepcopy

import pytest
from review_crossed_line_pilot import check_training_batches


def rows():
    return {
        "observed_inputs": [
            {"step": i, "domain": domain, "clean_sha256": f"clean{i}", "batch_sha256": f"noisy{i}"}
            for i, domain in enumerate(("commons", "native", "paired"), 1)
        ],
        "domain_counts": {"commons": 1, "native": 1, "paired": 1},
    }


def changed():
    control = rows()
    actual = deepcopy(control)
    actual["observed_inputs"][0]["clean_sha256"] = "new-source-target"
    actual["observed_inputs"][0]["batch_sha256"] = "new-source-observation"
    return actual, control


def test_actual_data_intervention_only_changes_commons():
    actual, control = changed()
    result = check_training_batches(actual, control, 3)
    assert result["changed_input_batches"] == {"commons": 1}
    assert result["all_native_paired_clean_and_noisy_match"]


@pytest.mark.parametrize("domain_index", [1, 2])
@pytest.mark.parametrize("field", ["clean_sha256", "batch_sha256"])
def test_reject_any_changed_native_or_paired_target_or_observation(domain_index, field):
    actual, control = changed()
    actual["observed_inputs"][domain_index][field] = "unexpected-change"
    with pytest.raises(AssertionError):
        check_training_batches(actual, control, 3)


def test_reject_no_actual_intervention():
    with pytest.raises(AssertionError):
        check_training_batches(rows(), rows(), 3)


@pytest.mark.parametrize("change", ["domain", "count", "step", "domain_counts"])
def test_reject_unmatched_schedule(change):
    actual, control = changed()
    if change == "domain":
        actual["observed_inputs"][0]["domain"] = "native"
    elif change == "count":
        actual["observed_inputs"].pop()
    elif change == "step":
        actual["observed_inputs"][1]["step"] = 3
    else:
        actual["domain_counts"]["commons"] = 2
    with pytest.raises(AssertionError):
        check_training_batches(actual, control, 3)
