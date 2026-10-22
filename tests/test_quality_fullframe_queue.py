import copy
import json

import numpy as np
import pytest
import tifffile
from queue_quality_fullframe import COMPLETE, evaluation_ready, inspect_export

from demosaic.io import write_rgb16


@pytest.mark.parametrize("flip", [0, 3, 5, 6])
@pytest.mark.parametrize("color_space", ["linear-camera-RGB", "sRGB"])
def test_decoded_rgb16_samples_cover_orientation_and_color_tags(tmp_path, flip, color_space):
    rgb = np.linspace(-0.1, 1.1, 67 * 71 * 3, dtype=np.float32).reshape(67, 71, 3)
    path = tmp_path / "export.tiff"
    write_rgb16(path, rgb, flip=flip, color_space=color_space)
    result = inspect_export(path, rgb, flip=flip, color_space=color_space)
    expected_shape = [71, 67, 3] if flip in (5, 6) else [67, 71, 3]
    assert result["shape"] == expected_shape and result["dtype"] == "uint16"
    assert result["sampled_maximum_quantization_error_DN16"] <= 0.504


@pytest.mark.parametrize("damage", ["RGB8", "missing-ICC", "changed-pixels"])
def test_bad_encoded_exports_are_rejected(tmp_path, damage):
    rgb = np.full((8, 12, 3), 0.25, dtype=np.float32)
    path = tmp_path / "bad.tiff"
    if damage in ("RGB8", "missing-ICC"):
        tifffile.imwrite(
            path,
            np.zeros(rgb.shape, dtype=np.uint8 if damage == "RGB8" else np.uint16),
            photometric="rgb",
            metadata=None,
            description=json.dumps({"color_space": "sRGB", "bits_per_sample": 16}),
        )
    else:
        write_rgb16(path, rgb, color_space="sRGB")
        pixels = tifffile.memmap(path, mode="r+")
        pixels[0, 0, 0] += 8
        pixels.flush()
    with pytest.raises(AssertionError):
        inspect_export(path, rgb, flip=0, color_space="sRGB")


PLAN = {"path": "/evaluation/plan.json", "sha256": "a" * 64}
OWNER = {"pid": 111, "created": 1.0}


def completed():
    return {"plan": copy.deepcopy(PLAN), "controller": copy.deepcopy(OWNER), "status": COMPLETE}


def test_fullframe_waits_for_original_evaluation_controller_to_exit():
    assert not evaluation_ready(completed(), PLAN, OWNER, is_live=lambda _: True)
    assert evaluation_ready(completed(), PLAN, OWNER, is_live=lambda _: False)


@pytest.mark.parametrize("damage", ["owner", "plan", "failure", "premature-exit"])
def test_failed_or_wrong_evaluation_boundary_cannot_start_fullframe(damage):
    state = completed()
    if damage == "owner":
        state["controller"]["created"] += 1
    elif damage == "plan":
        state["plan"]["sha256"] = "b" * 64
    elif damage == "failure":
        state["status"] = "failed-quality-recipe-evaluation-preserved"
    else:
        state["status"] = "running-quality-recipe-evaluation"
    with pytest.raises(AssertionError):
        evaluation_ready(state, PLAN, OWNER, is_live=lambda _: False)
