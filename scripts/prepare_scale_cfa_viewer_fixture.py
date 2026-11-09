"""Exercise seven viewer states using explicitly marked reused V198 pixels.

Fixture aliases and checkpoint metadata are not evaluated V200 predictions.
The actual-quality browser verifier must reject fixture records.
"""

import argparse
import shutil
from pathlib import Path

import numpy as np
from build_scale_supported_cfa_viewer import build
from check_scale_supported_cfa_viewer_pixels import DEFAULTS, METHODS
from directional_trial_protocol import REPO, freeze, guard, read, ref, save
from PIL import Image
from train_scale_supported_cfa_wave import ROOT as TRIAL

ROOT = TRIAL / "viewer-fixture-v1"
ALIASES = {f"V200-scale-wave-{e}": f"V198-CFA-wave-{e}" for e in ("raw", "EMA")}


def prepare():
    assert not ROOT.exists()
    ROOT.mkdir()
    work, sources = freeze(ROOT, ["prepare_scale_cfa_viewer_fixture.py"])
    browser = work / "scripts/verify-scale-cfa-viewer-fixture-v1.cjs"
    shutil.copyfile(REPO / "scripts" / browser.name, browser)
    source = REPO / "docs/images/v198-cfa-innovation-wave-v1/manifest-v1.json"
    save(
        ROOT / "plan-v1.json",
        {
            "runner": ref(work / "scripts/prepare_scale_cfa_viewer_fixture.py"),
            "work": str(work),
            "browser_checker": ref(browser),
            "source_manifest": ref(source),
            "inputs": [ref(source), ref(browser)],
            "frozen_files": sources,
            "fixture_only_no_V200_quality": True,
            "methods": METHODS,
            "aliases": ALIASES,
            "scope": "Six preselected V198 boards reused exactly for seven-state UI checking. "
            "V200 fixture aliases reuse V198 raw/EMA pixels and checkpoint metadata,not candidate outputs. "
            "No neural forward,new data/noise,RAW decode,original/dataz access,quality or promotion claim.",
        },
    )
    print("Prepared six-case reused-pixel fixture; no V200 quality")


def fixture():
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    source = read(plan["source_manifest"]["path"])
    assert source["fixture"] is False
    cases = [
        ("mesh-seed2026112302-present-iso6400-prior-RGGB", [176, 176, 160, 160]),
        ("mesh-seed2026112309-present-iso6400-prior-RGGB", [176, 176, 160, 160]),
        ("main-building-detail", [176, 176, 160, 160]),
        ("mesh-nominal", [426, 189, 160, 160]),
        ("flat512-gray-l0.02-iso12800-prior-RGGB", [176, 176, 160, 160]),
        ("photo-3e638bbb56ed80abc88939468783e3bf9b92ee77-photo-faint-RGGB", [176, 176, 160, 160]),
    ]
    out = ROOT / "images"
    out.mkdir()
    images = []
    for case_id, roi in cases:
        item = next(
            i
            for i in source["images"]
            if i["case"]["id"] == case_id and i["ROI_xywh"] == roi and not i["triplet"]
        )
        assert ref(item["image"]["path"]) == item["image"]
        path = out / Path(item["image"]["path"]).name
        shutil.copyfile(item["image"]["path"], path)
        assert ref(path)["sha256"] == item["image"]["sha256"]
        panels = [p for p in item["panels"] if p["label"] != "V197-RAW-wave-EMA"]
        for alias, original in ALIASES.items():
            panel = next(p for p in panels if p["label"] == original)
            panels.append(dict(panel, label=alias))
        images.append(
            dict(
                item,
                image=ref(path),
                original_image=item["image"],
                panels=panels,
                predictions={m: item["predictions"][ALIASES.get(m, m)] for m in METHODS},
            )
        )
    manifest = {
        "fixture": True,
        "fixture_only_no_V200_quality": True,
        "aliases": ALIASES,
        "images": images,
        "method_checkpoints": {m: source["method_checkpoints"][ALIASES.get(m, m)] for m in METHODS},
        "source_manifest": plan["source_manifest"],
    }
    save(out / "manifest-v1.json", manifest)
    build(
        out / "manifest-v1.json",
        out / "native-viewer.html",
        "fixture-only-no-V200-quality.md",
        method_a=DEFAULTS["a"],
        method_b=DEFAULTS["b"],
    )
    print("Built fixture: six cases,seven states; reused pixels only")


def verify():
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    folder = ROOT / "browser-v1"
    browser = read(folder / "browser-records-v1.json")
    manifest = read(ROOT / "images/manifest-v1.json")
    assert manifest["fixture"] and browser["fixture_only_no_V200_quality"] is True
    assert browser["methods"] == METHODS and browser["default_pair"] == DEFAULTS
    assert (
        browser["JS_errors"] == []
        and len(browser["records"]) == 210
        and len(browser["metadata"]) == 42
    )
    assert len({(r["case"], r["pair"], r["id"]) for r in browser["records"]}) == 210
    by_path = {i["image"]["path"]: i for i in manifest["images"]}
    for metadata in browser["metadata"]:
        a, b = METHODS[metadata["pair"]], METHODS[(metadata["pair"] + 1) % 7]
        assert metadata["a"] == a and metadata["b"] == b
        for method in (a, b):
            entry = manifest["method_checkpoints"][method]
            for value in [
                method,
                entry["state"] + " state",
                entry["module_hash"],
                entry["source_checkpoint"]["sha256"],
            ]:
                assert value in metadata["description"]
    channels = 0
    for r in browser["records"]:
        item = by_path[r["source"]]
        assert ref(item["image"]["path"]) == item["image"]
        panel = next(p for p in item["panels"] if p["label"] == r["label"])
        assert panel["xywh"] == r["panel"]
        rect = r["rect"]
        assert rect["width"] == rect["height"] == 160 and rect["x"] % 1 == rect["y"] % 1 == 0
        x, y, w, h = r["panel"]
        assert w == h == 160
        expected = np.array(Image.open(r["source"]).convert("RGB"))[y : y + h, x : x + w]
        actual = np.array(Image.open(r["screenshot"]).convert("RGB"))
        np.testing.assert_array_equal(actual, expected)
        channels += actual.size
    assert channels == 16128000
    save(
        ROOT / "browser-fixture-verification-v1.json",
        {
            "status": "pass-seven-state-six-case-browser-fixture-no-V200-quality",
            "plan": ref(ROOT / "plan-v1.json"),
            "source": ref(__file__),
            "viewer": ref(ROOT / "images/native-viewer.html"),
            "browser_records": ref(folder / "browser-records-v1.json"),
            "native_captures": 210,
            "exact_RGB_channels": channels,
            "all_methods_in_both_selectors": METHODS,
            "fixture_only_no_V200_quality": True,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "scope": plan["scope"],
        },
    )
    print("PASS210fixturecaptures/16128000RGBchannels/seven states;not V200 quality")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["prepare", "fixture", "verify"])
    a = p.parse_args()
    {"prepare": prepare, "fixture": fixture, "verify": verify}[a.phase]()
