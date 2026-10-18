import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image


@pytest.fixture(scope="module")
def worker():
    path = Path("scripts/build_native_crop_board.py")
    spec = importlib.util.spec_from_file_location("native_board", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def report(tmp_path):
    crops = []
    for model in ("A-step10000", "B-step40000"):
        for case in ("photo-0", "photo-1"):
            pixels = np.zeros((192, 512, 3), dtype=np.uint8)
            # Nonuniform pixels expose any interpolation, shift or resize.
            grid = np.arange(160 * 160 * 3, dtype=np.uint32).reshape(160, 160, 3)
            for part, x in enumerate([8, 176, 344]):
                delta = 9 * part + (case == "photo-1") + 17 * (part == 1 and model.startswith("B"))
                pixels[24:184, x : x + 160] = (grid + delta) % 256
            path = tmp_path / f"{model}-{case}.png"
            Image.fromarray(pixels).save(path)
            crops.append(
                {
                    "image": path.name,
                    "png_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "model_label": model,
                    "checkpoint_sha256": ("a" if model.startswith("A") else "b") * 64,
                    "source_id": case,
                    "source": {"id": case},
                    "condition": {"shot": 0.00256, "read": 0.0000262144},
                    "evaluation_tile_xywh": [48, 48, 160, 160],
                    "display_exposure": 1,
                    "reference": "Exact synthetic GT",
                    "pixel_scale": "1 PNG pixel = 1 image pixel",
                    "display_encoding": "8-bit sRGB",
                    "panels": [
                        {"label": label, "png_xywh": [x, 24, 160, 160]}
                        for label, x in zip(
                            ["Noisy (Malvar)", "Denoised", "GT (synthetic)"],
                            [8, 176, 344],
                            strict=True,
                        )
                    ],
                }
            )
    path = tmp_path / "summary.json"
    path.write_text(json.dumps({"native_crops": crops}))
    return path, crops


def test_complete_board_preserves_every_native_pixel_and_actual_model_labels(worker, report):
    path, crops = report
    output = path.parent / "board.png"
    result = worker.build([path], output, "synthetic")
    assert result["native_cells_exact"] == 8
    assert [m["label"] for m in result["models"]] == ["A-step10000", "B-step40000"]
    assert all(c["row_label"] == "GT (synthetic)" for c in result["cells"] if c["part"] == 2)
    actual = np.asarray(Image.open(output))
    for cell in result["cells"]:
        x, y, w, h = cell["board_xywh"]
        a, b, c, d = cell["source_xywh"]
        source = np.asarray(Image.open(cell["image"]["path"]))
        np.testing.assert_array_equal(actual[y : y + h, x : x + w], source[b : b + d, a : a + c])
    assert (
        json.loads(output.with_suffix(".json").read_text())["source_triplets"][0]["crop"]
        == crops[0]
    )


@pytest.mark.parametrize(
    "problem",
    [
        "hash",
        "resize",
        "bounds",
        "overlap",
        "reference-label",
        "noisy-label",
        "noise",
        "ROI",
        "exposure",
        "missing-metadata",
        "checkpoint",
        "duplicate",
        "missing",
        "outer-pixels",
    ],
)
def test_mismatched_evidence_rejected_before_output(worker, report, problem):
    path, crops = report
    changed = copy.deepcopy(crops)
    crop = changed[2]  # Second model, same first photo.
    if problem == "hash":
        crop["png_sha256"] = "0" * 64
    elif problem == "resize":
        crop["panels"][1]["png_xywh"][2] = 159
    elif problem == "bounds":
        crop["panels"][1]["png_xywh"][0] = -1
    elif problem == "overlap":
        crop["panels"][1]["png_xywh"] = [8, 24, 160, 160]
    elif problem == "reference-label":
        crop["panels"][2]["label"] = "ISO100 ref (not GT)"
    elif problem == "noisy-label":
        crop["panels"][0]["label"] = "Denoised"
    elif problem == "noise":
        crop["condition"]["shot"] *= 2
    elif problem == "ROI":
        crop["evaluation_tile_xywh"][0] += 1
    elif problem == "exposure":
        crop["display_exposure"] = 4
    elif problem == "missing-metadata":
        del crop["condition"]
    elif problem == "checkpoint":
        crop["checkpoint_sha256"] = "c" * 64
    elif problem == "duplicate":
        changed.append(copy.deepcopy(crop))
    elif problem == "missing":
        changed.pop()
    else:
        image = path.parent / crop["image"]
        pixels = np.asarray(Image.open(image)).copy()
        pixels[24, 8] ^= 1
        Image.fromarray(pixels).save(image)
        crop["png_sha256"] = hashlib.sha256(image.read_bytes()).hexdigest()
    path.write_text(json.dumps({"native_crops": changed}))
    output = path.parent / "rejected.png"
    with pytest.raises(ValueError):
        worker.build([path], output, "synthetic")
    assert not output.exists() and not output.with_suffix(".json").exists()


def test_labels_must_be_complete_unique_and_are_preserved(worker, report):
    path, _ = report
    for labels in [{"A-step10000": "A"}, {"A-step10000": "same", "B-step40000": "same"}]:
        with pytest.raises(ValueError, match="Display labels"):
            worker.build([path], path.parent / "rejected.png", "synthetic", labels)
    result = worker.build(
        [path],
        path.parent / "aliases.png",
        "synthetic",
        {"A-step10000": "new 10k", "B-step40000": "old 40k"},
    )
    assert [m["display_label"] for m in result["models"]] == ["new 10k", "old 40k"]


def test_existing_output_is_not_overwritten(worker, report):
    path, _ = report
    output = path.parent / "exists.png"
    output.write_bytes(b"preserve")
    with pytest.raises(ValueError, match="new PNG"):
        worker.build([path], output, "synthetic")
    assert output.read_bytes() == b"preserve"


def test_published_reference_weight_hash_schema_is_retained_without_guessing(worker, report):
    path, crops = report
    for crop in crops:
        crop["model"] = {
            "label": crop.pop("model_label"),
            "weight_sha256": crop.pop("checkpoint_sha256"),
        }
    path.write_text(json.dumps({"native_crops": crops}))
    result = worker.build([path], path.parent / "reference-schema.png", "synthetic")
    assert [m["sha256"] for m in result["models"]] == ["a" * 64, "b" * 64]
    crops[0]["checkpoint_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="Conflicting"):
        worker.identity(crops[0])
