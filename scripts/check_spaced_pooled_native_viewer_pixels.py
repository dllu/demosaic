"""Check actual raw/EMA matched browser captures against their public PNG pixels."""

import argparse
from pathlib import Path

import numpy as np
from phase_admission_protocol import read, ref
from PIL import Image
from train_spaced_pooled_trial import REPO, save

METHODS = {
    "control": {e: f"V187-pooled-wave-{e}" for e in ["raw", "EMA"]},
    "evidence": {e: f"V189-spaced-pooled-{e}" for e in ["raw", "EMA"]},
}


def verify(directory, output):
    if output.exists():
        raise FileExistsError(output)
    browser = read(directory / "browser-records-v1.json")
    assert browser["fixture_only_no_V189_quality"] is False and browser["JS_errors"] == []
    assert len(browser["records"]) == 480 and len(browser["metadata"]) == 96
    viewer = Path(browser["viewer"])
    manifest_path = viewer.with_name("manifest-v1.json")
    manifest = read(manifest_path)
    assert manifest["fixture"] is False and manifest["native_figures"] == 60
    expected_old = read(REPO / "docs/results/v187-pooled-wave-final-v1.json")[
        "viewer_method_checkpoints"
    ]
    assert set(manifest["method_checkpoints"]) == set(expected_old) | set(
        METHODS["evidence"].values()
    )
    for method, entry in expected_old.items():
        assert manifest["method_checkpoints"][method] == entry
    for entry in manifest["method_checkpoints"].values():
        assert ref(entry["source_checkpoint"]["path"]) == entry["source_checkpoint"]
    images = {item["image"]["path"]: item for item in manifest["images"] if not item["triplet"]}
    assert len(images) == 48
    for item in images.values():
        assert ref(item["image"]["path"]) == item["image"]
    assert len({(m["case"], m["endpoint"]) for m in browser["metadata"]}) == 96
    for record in browser["metadata"]:
        for arm in ["control", "evidence"]:
            method = METHODS[arm][record["endpoint"]]
            metadata = manifest["method_checkpoints"][method]
            assert metadata["state"] == record["endpoint"]
            for value in [method, metadata["source_checkpoint"]["sha256"], metadata["module_hash"]]:
                assert value in record["description"]
    channels = 0
    assert len({(r["case"], r["endpoint"], r["id"]) for r in browser["records"]}) == 480
    for record in browser["records"]:
        rect = record["rect"]
        assert rect["width"] == rect["height"] == 160
        assert rect["x"].is_integer() and rect["y"].is_integer()
        item = images[record["source"]]
        expected_panel = next(p for p in item["panels"] if p["label"] == record["label"])
        assert expected_panel["xywh"] == record["panel"]
        if record["id"] in ["a", "b"]:
            arm = "control" if record["id"] == "a" else "evidence"
            assert record["label"] == METHODS[arm][record["endpoint"]]
        x, y, width, height = record["panel"]
        assert width == height == 160
        expected = np.asarray(Image.open(record["source"]).convert("RGB"))[
            y : y + height, x : x + width
        ]
        actual = np.asarray(Image.open(record["screenshot"]).convert("RGB"))
        np.testing.assert_array_equal(actual, expected)
        channels += actual.size
    assert channels == 36864000
    save(
        output,
        {
            "status": "pass-actual-matched-browser-480-native-crops-checkpoint-state-and-source-pixels",
            "viewer": ref(viewer),
            "manifest": ref(manifest_path),
            "browser_records": ref(directory / "browser-records-v1.json"),
            "browser_version": browser["browser"],
            "cases": 48,
            "matched_raw_EMA_pairs": 96,
            "browser_crop_screenshots": 480,
            "RGB_channels_exact_source_PNG": channels,
            "rectangle_width_height": [160, 160],
            "per_method_state_metadata_checked": True,
            "default_V187_EMA_vs_V187_EMA": True,
            "click_keyboard_flip_and_navigation": True,
            "JS_errors": [],
            "screenshot_bindings": [ref(r["screenshot"]) for r in browser["records"]],
            "fixture_only_no_actual_V189_quality": False,
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": "Actual headless-browser screenshot pixels and source/checkpoint-state metadata are checked. Image-quality gains and costs require the separate matched measurements and actual human native viewing.",
        },
    )
    print("PASS480actualbrowsercrops/36864000RGBchannels/raw+EMAstate-metadata")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    verify(args.directory.resolve(), args.output.resolve())
