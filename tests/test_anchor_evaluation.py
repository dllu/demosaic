import copy

import numpy as np
import pytest
from torch import nn

from demosaic.experiments.artifacts import read_json, reference, write_json
from demosaic.experiments.evaluation.detail import DetailMetrics
from demosaic.experiments.evaluation.native import write_native
from demosaic.experiments.evaluation.runner import evaluate_cases
from demosaic.prediction_archive import fingerprint


class Extension(nn.Module):
    def forward(self, base, *args, return_aux=False):
        output = base + 0.0005
        aux = {
            "anchor_output": base,
            "inherited_aux": {
                "anchor_output": base * 0.95,
                "anchor_aux": {"frozen_output": base * 0.8, "inherited_output": base * 0.9},
                "wave_correction": base - base * 0.95,
                "matching_evaluated": True,
            },
        }
        return (output, aux) if return_aux else output


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
    inherited, frozen, v183 = parent * 0.95, parent * 0.8, parent * 0.9
    wave = parent - inherited
    control.update(
        method="control",
        index=0,
        values=fingerprint(parent),
        inherited_values=fingerprint(inherited),
        frozen_values=fingerprint(frozen),
        V183_values=fingerprint(v183),
        wave_correction_values=fingerprint(wave),
        wave_correction_RMS_DN16=float(np.sqrt(np.mean(wave.astype(np.float64) ** 2))) * 65535,
        ADC_exact=False,
        anchor_V195_EMA_replay_exact=True,
        V183_replay_exact=True,
        frozen_V169_replay_exact=True,
    )
    native = parent.copy()
    if mutation == "scalar":
        control["correction_RMS_DN16"] = 1.0
    if mutation == "pixels":
        native[0, 0, 0, 0] += 1e-6
    if mutation == "index":
        control["index"] = 1
    if mutation == "intermediate":
        control["inherited_values"] = fingerprint(parent)
    binding = write_native(root / "native.json", native)
    control["prediction"] = binding
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
    assert result["anchor_verification"]["exact_output_array_fingerprints"] == 1
    assert result["anchor_verification"]["new_anchor_forwards"] == 0
    assert result["rows"][0]["correction_RMS_DN16"] > 0
    assert result["rows"][0]["reference_scored"] is False


@pytest.mark.parametrize("mutation", ["scalar", "pixels", "duplicate", "index", "intermediate"])
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
