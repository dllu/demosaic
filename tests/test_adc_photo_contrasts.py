import copy

import pytest
from audit_adc_photo_contrasts import condition_subsets, paired_sources, summarize


def inputs():
    methods = ["reference", "parent", "control", "candidate", "classical"]
    conditions = [
        {"name": "misleading-ISO12800", "shot": 0.0, "read": 0.0},
        {"name": "misleading-ADC", "shot": 0.001, "read": 0.0},
        {"name": "read-only", "shot": 0.0, "read": 1e-6},
    ]
    sources = {"photo": ["a", "b"], "synthetic": ["s"]}
    patterns = ["RGGB", "BGGR"]
    rows = []
    for model in methods:
        for kind, identities in sources.items():
            for identity in identities:
                for condition in conditions:
                    adc = condition["shot"] == condition["read"] == 0
                    for pattern in patterns:
                        delta = 0
                        if model == "candidate":
                            delta = (
                                (8 if identity == "a" else 4)
                                if adc
                                else (-3 if identity == "a" else -1)
                            )
                        rows.append(
                            {
                                "model": model,
                                "kind": kind,
                                "id": identity,
                                "condition": condition["name"],
                                "pattern": pattern,
                                "metrics": {
                                    "srgb_psnr": 30 + delta + (0.5 if pattern == "RGGB" else -0.5),
                                    "srgb_ssim": 0.9
                                    + (0.01 if kind == "photo" else -0.01) * (model == "candidate"),
                                },
                            }
                        )
    return rows, {
        "methods": methods,
        "primary_models": methods[:4],
        "sources": sources,
        "conditions": conditions,
        "patterns": patterns,
    }


def contrast(result, subset, kind="photo", metric="srgb_psnr"):
    return next(
        row
        for row in result["paired_comparisons"]
        if row["subset"] == subset
        and row["kind"] == kind
        and row["metric"] == metric
        and row["first"] == "candidate"
        and row["second"] == "control"
    )


def test_adc_gain_cannot_hide_positive_noise_regression_or_procedural_ssim_loss():
    rows, options = inputs()
    result = summarize(rows, **options)
    assert len(result["paired_comparisons"]) == 72
    assert len(result["source_balanced_means"]) == 48
    assert result["conditions_by_subset"] == {
        "all": ["misleading-ISO12800", "misleading-ADC", "read-only"],
        "ADC": ["misleading-ISO12800"],
        "positive_noise": ["misleading-ADC", "read-only"],
    }
    assert contrast(result, "all")["mean_first_minus_second"] == pytest.approx(2 / 3)
    adc = contrast(result, "ADC")
    assert adc["mean_first_minus_second"] == 6
    assert adc["sources"] == 2  # Resample photographs, not condition/CFA tiles.
    noisy = contrast(result, "positive_noise")
    assert noisy["mean_first_minus_second"] == -2
    assert noisy["source_bootstrap_95_interval"] == [-3, -1]
    assert noisy["worst10"] == [{"id": "a", "delta": -3}, {"id": "b", "delta": -1}]
    assert contrast(result, "ADC", "photo", "srgb_ssim")["mean_first_minus_second"] > 0
    assert contrast(result, "ADC", "synthetic", "srgb_ssim")["mean_first_minus_second"] < 0
    assert summarize(list(reversed(rows)), **options) == result


@pytest.mark.parametrize(
    "damage",
    [
        "missing",
        "duplicate",
        "extra-model",
        "extra-source",
        "extra-condition",
        "extra-pattern",
        "nonfinite",
        "missing-metric",
    ],
)
def test_partial_or_corrupted_score_grids_are_rejected(damage):
    rows, options = inputs()
    if damage == "missing":
        rows.pop()
    elif damage == "duplicate":
        rows.append(copy.deepcopy(rows[0]))
    elif damage.startswith("extra-"):
        key = {
            "extra-model": "model",
            "extra-source": "id",
            "extra-condition": "condition",
            "extra-pattern": "pattern",
        }[damage]
        rows[0][key] = "unexpected"
    elif damage == "nonfinite":
        rows[0]["metrics"]["srgb_psnr"] = float("nan")
    else:
        del rows[0]["metrics"]["srgb_ssim"]
    with pytest.raises((AssertionError, KeyError)):
        summarize(rows, **options)


@pytest.mark.parametrize(
    "damage", ["negative", "nan", "boolean", "duplicate-name", "two-ADC", "no-ADC"]
)
def test_ambiguous_or_invalid_priors_cannot_select_subsets(damage):
    _, options = inputs()
    conditions = options["conditions"]
    if damage in ("negative", "nan", "boolean"):
        conditions[0]["shot"] = {"negative": -1, "nan": float("nan"), "boolean": False}[damage]
    elif damage == "duplicate-name":
        conditions[1]["name"] = conditions[0]["name"]
    elif damage == "two-ADC":
        conditions[1]["shot"] = 0
    else:
        conditions[0]["read"] = 1e-8
    with pytest.raises(AssertionError):
        condition_subsets(conditions)


def test_unmatched_source_sets_cannot_be_paired_and_constant_difference_has_exact_interval():
    with pytest.raises(AssertionError):
        paired_sources({"a": 1}, {"b": 1})
    result = paired_sources({"a": 2, "b": 5}, {"b": 4, "a": 1})
    assert result["mean_first_minus_second"] == 1
    assert result["source_bootstrap_95_interval"] == [1, 1]
