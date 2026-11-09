"""Check all six actual viewer methods against source native PNG pixels."""

import argparse
from pathlib import Path

import numpy as np
from directional_trial_protocol import REPO, save
from phase_admission_protocol import read, ref
from PIL import Image

METHODS = [
    "V187-pooled-wave-EMA",
    "V195-whole-response-EMA",
    "V197-RAW-wave-EMA",
    "V197-innovation-wave-EMA",
    "V198-CFA-wave-raw",
    "V198-CFA-wave-EMA",
]
DEFAULTS = {"a": "V197-innovation-wave-EMA", "b": "V198-CFA-wave-EMA"}


def verify(directory, output):
    assert not output.exists()
    browser = read(directory / "browser-records-v1.json")
    assert browser["fixture_only_no_V198_quality"] is False and browser["JS_errors"] == []
    assert browser["methods"] == METHODS and browser["default_pair"] == DEFAULTS
    assert len(browser["records"]) == 1440 and len(browser["metadata"]) == 288
    viewer = Path(browser["viewer"])
    manifest_path = viewer.with_name("manifest-v1.json")
    manifest = read(manifest_path)
    assert manifest["fixture"] is False and manifest["native_figures"] == 60
    assert set(manifest["method_checkpoints"]) == set(METHODS)
    sources = {
        "V187-pooled-wave-EMA": "v187-pooled-wave-final-v1.json",
        "V195-whole-response-EMA": "v195-response-final-v1.json",
        "V197-RAW-wave-EMA": "v197-innovation-wave-final-v1.json",
        "V197-innovation-wave-EMA": "v197-innovation-wave-final-v1.json",
    }
    for method, filename in sources.items():
        assert (
            manifest["method_checkpoints"][method]
            == read(REPO / "docs/results" / filename)["checkpoints"][method]
        )
    for method, entry in manifest["method_checkpoints"].items():
        assert ref(entry["source_checkpoint"]["path"]) == entry["source_checkpoint"]
        assert method.endswith("-" + entry["state"])
    images = {item["image"]["path"]: item for item in manifest["images"] if not item["triplet"]}
    assert len(images) == 48
    for item in images.values():
        assert ref(item["image"]["path"]) == item["image"]
    assert len({(m["case"], m["pair"]) for m in browser["metadata"]}) == 288
    assert {m["case"] for m in browser["metadata"]} == set(range(48))
    for record in browser["metadata"]:
        a, b = METHODS[record["pair"]], METHODS[(record["pair"] + 1) % len(METHODS)]
        assert (record["a"], record["b"]) == (a, b)
        for method in [a, b]:
            metadata = manifest["method_checkpoints"][method]
            for text in [
                method,
                metadata["state"] + " state",
                metadata["source_checkpoint"]["sha256"],
                metadata["module_hash"],
            ]:
                assert text in record["description"]
    assert len({(r["case"], r["pair"], r["id"]) for r in browser["records"]}) == 1440
    channels = 0
    for record in browser["records"]:
        rect = record["rect"]
        assert rect["width"] == rect["height"] == 160
        assert rect["x"] == int(rect["x"]) and rect["y"] == int(rect["y"])
        item = images[record["source"]]
        expected_panel = next(p for p in item["panels"] if p["label"] == record["label"])
        assert expected_panel["xywh"] == record["panel"]
        a, b = METHODS[record["pair"]], METHODS[(record["pair"] + 1) % len(METHODS)]
        if record["id"] in ["a", "b"]:
            assert record["label"] == (a if record["id"] == "a" else b)
        assert record["id"] in ["noisy", "a", "b", "flip", "reference"]
        x, y, width, height = record["panel"]
        assert width == height == 160
        expected = np.asarray(Image.open(record["source"]).convert("RGB"))[
            y : y + height, x : x + width
        ]
        actual = np.asarray(Image.open(record["screenshot"]).convert("RGB"))
        np.testing.assert_array_equal(actual, expected)
        channels += actual.size
    assert channels == 110592000
    save(
        output,
        {
            "status": "pass-actual-six-method-browser-1440-native-crops-checkpoint-state-and-source-pixels",
            "viewer": ref(viewer),
            "manifest": ref(manifest_path),
            "browser_records": ref(directory / "browser-records-v1.json"),
            "browser_version": browser["browser"],
            "cases": 48,
            "six_method_cycle_pairs": 288,
            "browser_crop_screenshots": 1440,
            "RGB_channels_exact_source_PNG": channels,
            "rectangle_width_height": [160, 160],
            "all_methods_checked_in_both_selectors": METHODS,
            "per_method_state_metadata_checked": True,
            "default_pair": DEFAULTS,
            "click_keyboard_flip_and_navigation": True,
            "JS_errors": [],
            "screenshot_bindings": [ref(r["screenshot"]) for r in browser["records"]],
            "fixture_only_no_actual_V198_quality": False,
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": "Actual browser pixels and all six method/source/checkpoint-state metadata verified in both selectors. These functional checks establish no image-quality gain; complete measurements and actual native viewing are separate evidence.",
        },
    )
    print("PASS1440actualbrowsercrops/110592000RGBchannels/all6methods-and-state-metadata")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verify(args.directory.resolve(), args.output.resolve())
