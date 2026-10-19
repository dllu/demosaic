import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/train_native_data_trial.py"
spec = importlib.util.spec_from_file_location("native_data_trial", SCRIPT)
trial = importlib.util.module_from_spec(spec)
original_path = list(sys.path)
try:
    sys.path.insert(0, str(SCRIPT.parent))
    spec.loader.exec_module(trial)
finally:
    sys.path[:] = original_path


def observation(step, domain, fingerprint):
    return {
        "step": step,
        "domain": domain,
        "full_batch_sha256": fingerprint,
        "input_sha256": fingerprint,
    }


def test_data_treatment_allows_native_changes_and_preserves_other_domains():
    a = [
        observation(1, "commons", "a"),
        observation(2, "native", "b"),
        observation(3, "paired", "c"),
    ]
    b = [
        observation(1, "commons", "a"),
        observation(2, "native", "changed"),
        observation(3, "paired", "c"),
    ]
    assert trial.compare_observations(a, b, require_native_change=True) == {
        "shared_pairs_exact": 2,
        "native_pairs": 1,
        "native_pairs_changed": 1,
    }


@pytest.mark.parametrize("domain", ["commons", "paired"])
def test_data_treatment_cannot_hide_shared_domain_drift(domain):
    with pytest.raises(ValueError, match="Shared Commons/paired"):
        trial.compare_observations(
            [observation(1, domain, "a")],
            [observation(1, domain, "different")],
            require_native_change=False,
        )


def test_domain_and_step_must_match_even_when_native_pixels_may_change():
    with pytest.raises(ValueError, match="domain/step"):
        trial.compare_observations(
            [observation(1, "native", "a")],
            [observation(2, "native", "b")],
            require_native_change=False,
        )


@pytest.mark.parametrize(
    "rows", [[observation(1, "commons", "a")], [observation(1, "native", "a")]]
)
def test_production_requires_actual_treatment_and_shared_input_coverage(rows):
    with pytest.raises(ValueError, match="coverage"):
        trial.compare_observations(rows, rows, require_native_change=True)
