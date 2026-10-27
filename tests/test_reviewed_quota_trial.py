"""Quota-only recipe and saved-input contracts; no neural execution."""

import copy
from pathlib import Path

import numpy as np
import pytest
import yaml
from train_directional_bank_trial import ref
from train_reviewed_quota_trial import compare_inputs, unchanged_slots, validate_recipes


def test_actual_recipe_changes_only_the_photographic_quota():
    repo = Path(__file__).resolve().parents[1]
    candidate = yaml.safe_load((repo / "configs/quality-v120-reviewed-quota-v133.yaml").read_text())
    control = yaml.safe_load((repo / "configs/quality-v120-raw-spatial-v131.yaml").read_text())
    validate_recipes(candidate, control)
    for key in ("manifest", "reviewed_roi_catalogue", "seed", "steps", "model", "noise_pair_draws"):
        wrong = copy.deepcopy(candidate)
        wrong[key] = "different"
        with pytest.raises(AssertionError, match="differs beyond"):
            validate_recipes(wrong, control)


def fixture(tmp_path, domain="commons"):
    config = {"seed": 70, "batch_size": 16, "flat_fraction": 0.1, "synthetic_fraction": 0.2}
    step = next(
        s
        for s in range(1, 19)
        if any(unchanged_slots(config, s)) and not all(unchanged_slots(config, s))
    )
    mask = (
        np.array(unchanged_slots(config, step)) if domain == "commons" else np.ones(16, dtype=bool)
    )
    previous = np.zeros((16, 1, 2, 2), dtype=np.float32)
    actual = previous.copy()
    actual[~mask] = 1
    old_path, new_path = tmp_path / "old.npz", tmp_path / "new.npz"
    np.savez(old_path, packed=previous, global_condition=np.array(16))
    np.savez(new_path, packed=actual, global_condition=np.array(16))
    row = {"step": step, "domain": domain, "clean_sha256": "same", "batch_sha256": "same"}
    old = {"observed_inputs": [{**row, "prepared_tensors": ref(old_path)}]}
    new = {"observed_inputs": [{**row, "prepared_tensors": ref(new_path)}]}
    if not all(mask):
        new["observed_inputs"][0].update(clean_sha256="changed", batch_sha256="changed")
    return config, mask, old, new, new_path


def test_real_saved_arrays_allow_only_the_intended_changed_examples(tmp_path):
    config, mask, old, new, _ = fixture(tmp_path)
    result = compare_inputs(new, old, config)
    assert result["unaffected_first18_examples"] == mask.sum()
    assert result["exact_unaffected_prepared_values"] == mask.sum() * 4 + 1
    assert result["Commons_batches_with_expected_selection_changes"] == 1


@pytest.mark.parametrize("domain", ["native", "paired"])
def test_other_domains_must_match_entire_batches(tmp_path, domain):
    config, _mask, old, new, _ = fixture(tmp_path, domain)
    result = compare_inputs(new, old, config)
    assert result[f"{domain}_whole_batches_exact"] == 1
    new["observed_inputs"][0]["batch_sha256"] = "unexpected drift"
    with pytest.raises(AssertionError):
        compare_inputs(new, old, config)


@pytest.mark.parametrize(
    "corruption", ["unaffected", "global", "dtype", "keys", "hash", "domain", "partial"]
)
def test_saved_input_corruption_is_rejected(tmp_path, corruption):
    config, mask, old, new, path = fixture(tmp_path)
    with np.load(path, allow_pickle=False) as values:
        arrays = {key: values[key].copy() for key in values.files}
    if corruption == "unaffected":
        arrays["packed"][np.flatnonzero(mask)[0]] += 1
    elif corruption == "global":
        arrays["global_condition"] += 1
    elif corruption == "dtype":
        arrays["packed"] = arrays["packed"].astype(np.float64)
    elif corruption == "keys":
        arrays.pop("global_condition")
    elif corruption == "domain":
        new["observed_inputs"][0]["domain"] = "paired"
    elif corruption == "partial":
        new["observed_inputs"] = []
    else:
        path.write_bytes(b"Not the recorded archive")
    if corruption not in ("hash", "partial"):
        np.savez(path, **arrays)
        new["observed_inputs"][0]["prepared_tensors"] = ref(path)
    with pytest.raises(AssertionError):
        compare_inputs(new, old, config)
