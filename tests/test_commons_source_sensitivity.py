import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest


def script():
    path = Path("scripts/report_commons_source_sensitivity.py")
    spec = importlib.util.spec_from_file_location("source_sensitivity", path)
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(path.parent.resolve()))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


def observations():
    rows = []
    for identity, offset in [("a", 1.0), ("b", 10.0)]:
        for condition, noise in [("low", 0.0), ("high", 2.0)]:
            for pattern, phase in [("RGGB", 0.0), ("BGGR", 0.5)]:
                rows.append(
                    {
                        "model": "m",
                        "kind": "photo",
                        "id": identity,
                        "condition": condition,
                        "pattern": pattern,
                        "metrics": {
                            "linear_psnr": offset + noise + phase,
                            "srgb_psnr": offset * 2 + noise + phase,
                            "srgb_ssim": offset / 100 + noise / 100 + phase / 100,
                        },
                    }
                )
    return rows


def test_actual_source_cell_coverage_is_complete_and_balanced():
    module = script()
    values = module.photo_scores(observations(), "m", ["a", "b"], ["low", "high"], ["RGGB", "BGGR"])
    assert values["a"]["linear_psnr"] == 2.25
    assert values["b"]["srgb_psnr"] == 21.25
    assert values["a"]["srgb_ssim"] == pytest.approx(0.0225)


@pytest.mark.parametrize("problem", ["duplicate", "missing", "wrong_source", "null"])
def test_invalid_observation_cannot_hide_behind_a_set_or_average(problem):
    module = script()
    rows = observations()
    if problem == "duplicate":
        rows.append(rows[0])
    elif problem == "missing":
        rows.pop()
    elif problem == "wrong_source":
        rows[-1] = {**rows[-1], "id": "other"}
    else:
        rows[-1] = {**rows[-1], "metrics": {**rows[-1]["metrics"], "srgb_psnr": None}}
    with pytest.raises(ValueError):
        module.photo_scores(rows, "m", ["a", "b"], ["low", "high"], ["RGGB", "BGGR"])


def test_exhaustive_two_source_bootstrap_has_known_interval_and_direction():
    module = script()
    # All four ordered size-two resamples of source deltas[0,2].
    indices = np.array([[0, 0], [0, 1], [1, 0], [1, 1]])
    result = module.compare_values([1.0, 4.0], [1.0, 2.0], indices)
    assert result["first_source_balanced_mean"] == 2.5
    assert result["second_source_balanced_mean"] == 1.5
    assert result["mean_first_minus_second"] == 1.0
    np.testing.assert_allclose(
        result["source_bootstrap_95_interval"], [0.075, 1.925], atol=1e-12, rtol=0
    )
    same = module.compare_values([1.0, 4.0], [1.0, 4.0], indices)
    assert same["source_bootstrap_95_interval"] == [0.0, 0.0]


def test_completed_historical_and_flat_payloads_preserve_all_nine_pairs():
    module = script()
    payload = {"sources": list(range(9)), "comparisons": list(range(27))}
    historical = {
        "review_complete": True,
        "status": "completed-controlled-first4000-long-data-review-no-promotion",
        "primary_statistics": payload,
    }
    flat = {"status": "completed-original20k-long-data-statistics-and-4k-progress", **payload}
    assert module.statistics_payload(historical) is payload
    assert module.statistics_payload(flat) is flat


def test_completed_normalization_payload_preserves_three_declared_pairs():
    payload = {
        "status": "completed-normalization-trial-statistics-and-parent-comparisons",
        "sources": list(range(3)),
        "comparisons": list(range(9)),
    }
    assert script().statistics_payload(payload) is payload


@pytest.mark.parametrize(
    "container", [{}, {"status": "waiting"}, {"review_complete": True, "status": "waiting"}]
)
def test_unfinished_statistics_cannot_be_treated_as_complete(container):
    with pytest.raises(ValueError):
        script().statistics_payload(container)


def auditor():
    path = Path("scripts/audit_commons_source_sensitivity.py")
    spec = importlib.util.spec_from_file_location("source_sensitivity_auditor", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def alias_sources():
    source = {
        "label": "first4k",
        "model_label": "native-step4000",
        "checkpoint_sha256": "abc",
        "cases": "cases.jsonl",
        "cases_sha256": "def",
        "report": "summary.json",
        "report_sha256": "ghi",
    }
    return [source, {**source, "label": "self-replay"}]


def test_report_aliases_keep_the_same_native_identity_and_both_display_labels():
    sources = alias_sources()
    assert auditor().native_aliases(sources) == {"native-step4000": sources}


@pytest.mark.parametrize("field", ["checkpoint_sha256", "cases_sha256", "report_sha256"])
def test_aliases_cannot_hide_changed_native_model_or_artifacts(field):
    sources = alias_sources()
    sources[1][field] = "changed"
    with pytest.raises(ValueError, match="Conflicting native model"):
        auditor().native_aliases(sources)


def test_duplicate_source_descriptor_is_rejected():
    sources = alias_sources()
    with pytest.raises(ValueError, match="Duplicate source"):
        auditor().native_aliases([sources[0], sources[0]])
