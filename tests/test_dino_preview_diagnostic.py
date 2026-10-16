import importlib.util
from pathlib import Path

import numpy as np
import torch

spec = importlib.util.spec_from_file_location(
    "diagnose_dino_preview",
    Path(__file__).resolve().parents[1] / "scripts/diagnose_dino_preview.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_feature_error_separates_amplitude_from_spatial_structure():
    reference = torch.tensor([[[[1.0, 2.0], [3.0, 4.0]], [[4.0, 3.0], [2.0, 1.0]]]])
    doubled = module.feature_metrics(reference * 2, reference)
    np.testing.assert_allclose(doubled["cosine"], [1])
    np.testing.assert_allclose(doubled["relative_l2"], [1])
    shifted = module.feature_metrics(reference + 10, reference)
    assert shifted["relative_l2"][0] > 1
    np.testing.assert_allclose(shifted["spatial_centered_cosine"], [1])
    np.testing.assert_array_equal(shifted["spatial_centered_relative_l2"], [0])


def test_uncertainty_groups_all_cfa_cases_by_source():
    rows = []
    for identity, difference in [("source-a", -1), ("source-b", 3)]:
        for pattern in ["RGGB", "BGGR", "GRBG", "GBRG"]:
            for method, value in [
                ("noisy-malvar", 0),
                ("wiener7-malvar", difference),
                ("clean-malvar", 0),
            ]:
                rows.append(
                    {
                        "id": identity,
                        "condition": "test",
                        "layer": 4,
                        "reference": "clean-rgb",
                        "pattern": pattern,
                        "method": method,
                        "metrics": {"example": value},
                    }
                )
    result = module.summarize(rows)[0]
    assert result["sources"] == 2
    assert result["wiener_minus_noisy"]["example"] == {
        "mean": 1,
        "source_bootstrap_95": [-1, 3],
        "sources_positive": 1,
    }
