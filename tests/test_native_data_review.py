import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
original = list(sys.path)
try:
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location(
        "native_data_score", SCRIPTS / "score_native_data_eligibility.py"
    )
    score = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(score)
finally:
    sys.path[:] = original


def adc_rows():
    return [
        {
            "model": model,
            "kind": "carrier",
            "condition": "adc-only",
            "level": level,
            "contrast": contrast,
            "period": period,
            "pattern": pattern,
            "draw": draw,
            "metrics": {"in_phase_gain": 0.5},
        }
        for model in ["base", "extra"]
        for level in [0.01, 0.18]
        for contrast in [0.02, 0.1]
        for period in [4, 8, 16]
        for pattern in ["RGGB", "BGGR", "GRBG", "GBRG"]
        for draw in range(4)
    ]


def test_adc_gate_keeps_individual_loss_even_when_group_mean_is_small():
    rows = adc_rows()
    rows[-1]["metrics"]["in_phase_gain"] = 0.44
    result = score.adc_detail(rows, {"control": "base", "expanded": "extra"})
    assert len(result["cases"]) == 192 and len(result["group_means"]) == 12
    assert not result["no_ADC_case_loses_more_than_.05"]
    assert all(r["expanded_minus_control_gain"] > -0.05 for r in result["group_means"])


@pytest.mark.parametrize("damage", ["missing", "duplicate", "nonfinite", "different_draw"])
def test_adc_gate_rejects_incomplete_or_invalid_cases(damage):
    rows = adc_rows()
    if damage == "missing":
        rows.pop()
    elif damage == "duplicate":
        rows[-1] = rows[-2]
    elif damage == "nonfinite":
        rows[-1]["metrics"]["in_phase_gain"] = float("nan")
    else:
        rows[-1]["draw"] = 99
    with pytest.raises(ValueError):
        score.adc_detail(rows, {"control": "base", "expanded": "extra"})
