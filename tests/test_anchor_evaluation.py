import copy

import numpy as np
import pytest
from torch import nn

from demosaic.experiments.artifacts import read_json, reference, write_json
from demosaic.experiments.evaluation.detail import DetailMetrics
from demosaic.experiments.evaluation.native import write_native
from demosaic.experiments.evaluation.runner import evaluate_cases


class Extension(nn.Module):
    def forward(self, base, *args, return_aux=False):
        output = base + 0.0005
        return (output, {"anchor_output": base}) if return_aux else output


def fixture(root, mutation=None):
    root.mkdir()
    parent = np.full((1, 3, 32, 32), 0.02, np.float32)
    np.save(root / "parent.npy", parent)
    arrays = {
        "packed": np.full((1, 4, 16, 16), 0.02, np.float32),
        "variance": np.full((1, 4, 16, 16), 1e-6, np.float32),
        "colors": np.array([[0, 1, 1, 2]]),
        "wb": np.ones((1, 3), np.float32),
    }
    np.savez(root / "arrays.npz", **arrays)
    case = {
        "id": "real",
        "kind": "real",
        "arrays": reference(root / "arrays.npz"),
        "parent": reference(root / "parent.npy"),
    }
    write_json(root / "cases.json", {"observations": [case]})
    control = DetailMetrics().measure(case, arrays, parent, parent)
    control["method"] = "control"
    native = parent.copy()
    if mutation == "scalar":
        control["correction_RMS_DN16"] = 1.0
    if mutation == "pixels":
        native[0, 0, 0, 0] += 1e-6
    binding = write_native(root / "native.json", native)
    rows = [control]
    if mutation == "duplicate":
        rows.append(copy.copy(control))
    write_json(
        root / "control.json", {"rows": rows, "native_predictions": {"real": {"control": binding}}}
    )
    return root / "cases.json", {"scores": reference(root / "control.json"), "method": "control"}


def test_anchor_is_checked_inside_the_actual_delivered_forward(tmp_path):
    cases, control = fixture(tmp_path / "input")
    binding = evaluate_cases(
        Extension(), cases, tmp_path / "out", checkpoint={}, method="new", anchor_reference=control
    )
    result = read_json(binding["path"])
    assert result["anchor_verification"]["cases"] == 1
    assert result["anchor_verification"]["exact_retained_native_RGB_channels"] == 3072
    assert result["anchor_verification"]["new_anchor_forwards"] == 0
    assert result["rows"][0]["correction_RMS_DN16"] > 0
    assert result["rows"][0]["reference_scored"] is False


@pytest.mark.parametrize("mutation", ["scalar", "pixels", "duplicate"])
def test_changed_anchor_cannot_publish_completed_evaluation(tmp_path, mutation):
    cases, control = fixture(tmp_path / "input", mutation)
    with pytest.raises((ValueError, AssertionError)):
        evaluate_cases(
            Extension(),
            cases,
            tmp_path / "out",
            checkpoint={},
            method="new",
            anchor_reference=control,
        )
    assert not (tmp_path / "out/scores.json").exists()
