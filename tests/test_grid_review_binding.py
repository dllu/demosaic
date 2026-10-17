import importlib.util
import sys
from copy import deepcopy
from pathlib import Path

import pytest


def bind():
    directory = Path("scripts").resolve()
    sys.path.insert(0, str(directory))
    try:
        spec = importlib.util.spec_from_file_location(
            "grid_review", directory / "review_packed_grid.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module.legacy_frame


def fixture():
    return {
        "models": [
            {
                "label": "own-model",
                "sha256": "actual-weight-hash",
                "precision": "float16",
                "device": "cuda",
                "model_config": {"restoration_backbone": "packed-isotropic"},
            }
        ],
        "full_frames": [
            {
                "model_label": "own-model",
                "display_exposure": 4,
                "timing": {
                    "tile": 512,
                    "overlap": 64,
                    "batch_size": 4,
                    "compute_precision": "float16",
                },
                "files": [{"path": "restored-0-linear16.tiff"}, {"path": "restored-0-srgb16.tiff"}],
            }
        ],
    }


def test_legacy_export_binding_uses_weight_and_method_and_linear_encoding():
    model, frame, image = bind()(fixture(), {"sha256": "actual-weight-hash"})
    assert model["label"] == frame["model_label"] == "own-model"
    assert image["path"] == "restored-0-linear16.tiff"


@pytest.mark.parametrize(
    "case",
    [
        "weight",
        "ambiguous-weight",
        "method",
        "ambiguous-method",
        "precision",
        "grid",
        "tile",
        "encoding",
    ],
)
def test_legacy_binding_rejects_wrong_or_ambiguous_controls(case):
    report = deepcopy(fixture())
    if case == "weight":
        report["models"][0]["sha256"] = "another-checkpoint"
    elif case == "ambiguous-weight":
        report["models"].append(deepcopy(report["models"][0]))
    elif case == "method":
        report["full_frames"][0]["model_label"] = "another-method"
    elif case == "ambiguous-method":
        report["full_frames"].append(deepcopy(report["full_frames"][0]))
    elif case == "precision":
        report["models"][0]["precision"] = "bfloat16"
    elif case == "grid":
        report["full_frames"][0]["timing"]["tile_grid_alignment"] = 32
    elif case == "tile":
        report["full_frames"][0]["timing"]["tile"] = 256
    else:
        report["full_frames"][0]["files"] = [{"path": "restored-0-srgb16.tiff"}]
    with pytest.raises(AssertionError):
        bind()(report, {"sha256": "actual-weight-hash"})
