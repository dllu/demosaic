"""Verify actual matched exports, copied evidence, native crops and browser pixels."""

import argparse
import re
from pathlib import Path

import numpy as np
from PIL import Image
from publish_local_phase_evidence_trial import (
    ARMS,
    IMAGES,
    INDEX,
    METHODS,
    REPO,
    REPORT,
    ROOT,
    VERIFICATION,
    completed_context,
    factory,
    read,
    ref,
    save,
)


def verify(diary):
    plan, training, scores, figures, paired = completed_context(ROOT, viewed=True)
    if VERIFICATION.exists():
        raise FileExistsError(VERIFICATION)
    final = read(INDEX)
    assert final["plan"] == ref(ROOT / "plan-v1.json")
    for key in ["report", "figures", "notes", "publication_source"]:
        assert ref(final[key]["path"]) == final[key]
    for pair in final["copies"].values():
        for binding in pair.values():
            assert ref(binding["path"]) == binding
        assert (
            Path(pair["original"]["path"]).read_bytes() == Path(pair["public"]["path"]).read_bytes()
        )
    seal = read(final["publication_source"]["path"])
    assert seal["verifier"] == ref(__file__)
    for binding in seal["helpers"]:
        assert ref(binding["path"]) == {k: binding[k] for k in ["path", "sha256"]}
        if "text" in binding:
            assert Path(binding["path"]).read_text() == binding["text"]

    import torch
    from phase_evidence_training_state import load_matching_ema
    from profile_raw_kernel_inference import model_hash
    from reduce_local_phase_evidence_trial import tables
    from report_late_spectral_mixed_quiet import independent_display

    assert not torch.cuda.is_initialized()
    strict_loads = 0
    for arm in ARMS:
        source = torch.load(
            training[arm]["final_checkpoint"]["path"], map_location="cpu", weights_only=True
        )
        for endpoint in ["raw", "EMA"]:
            method = METHODS[arm][endpoint]
            entry = final["checkpoints"][method]
            assert entry["source_checkpoint"] == training[arm]["final_checkpoint"]
            assert entry["state"] == endpoint and entry["arm"] == arm
            assert ref(entry["export"]["path"]) == entry["export"]
            exported = torch.load(entry["export"]["path"], map_location="cpu", weights_only=True)
            actual = factory(arm, plan["module_config"]).eval()
            actual.load_state_dict(exported["state_dict"], strict=True)
            expected = factory(arm, plan["module_config"]).eval()
            expected.load_state_dict(source["models"], strict=True)
            if endpoint == "EMA":
                load_matching_ema(expected, source["ema"])
            assert (
                model_hash(actual)
                == model_hash(expected)
                == scores["module_hashes"][method]["before"]
                == entry["module_hash"]
            )
            assert model_hash(actual.frozen) == plan["frozen_component"]["module_hash"]
            assert exported["component"] == type(actual).__name__ == entry["component"]
            assert (
                exported["old_network_updates"] == 1800 and exported["new_optimizer_updates"] == 900
            )
            assert exported["adapter_updates"] == (900 if arm == "evidence" else 0)
            assert exported["source_checkpoint"] == entry["source_checkpoint"]
            assert ref(exported["source"]["path"]) == exported["source"] == entry["source"]
            strict_loads += 1
            del actual, expected, exported
        del source

    table_text, cells = tables(paired["summary"])
    assert len(cells) == 882 and cells == paired["table_cells"]
    assert (ROOT / "comparison-tables-v1.md").read_text() == table_text + "\n"
    assert table_text in REPORT.read_text() and final["report"] == ref(REPORT)
    manifest = read(final["figures"]["path"])
    assert (
        manifest["fixture"] is False
        and manifest["method_checkpoints"] == final["viewer_method_checkpoints"]
    )
    assert len(manifest["images"]) == 60 and sum(i["triplet"] for i in manifest["images"]) == 12
    prior = read(plan["prior_figures"]["path"])
    old_map = {item["image"]["path"]: item for item in prior["images"]}
    new_channels = copied_channels = prior_recomputed_channels = 0
    for item in manifest["images"]:
        assert ref(item["image"]["path"]) == item["image"] and item["no_resize"]
        assert Path(item["image"]["path"]).parent == IMAGES
        assert (
            Path(item["image"]["path"]).read_bytes()
            == Path(item["original_image"]["path"]).read_bytes()
        )
        old = old_map[item["source_figure"]["path"]]
        assert item["source_figure"] == old["image"] == ref(old["image"]["path"])
        assert all(item[k] == old[k] for k in ["ROI_xywh", "anchor", "contrast", "exposure"])
        image, old_image = [
            np.asarray(Image.open(v["path"]).convert("RGB")) for v in [item["image"], old["image"]]
        ]
        arrays = dict(np.load(item["case"]["arrays"]["path"], allow_pickle=False))
        anchor = np.asarray(item["anchor"]).reshape(1, 3, 1, 1)
        old_panels = {panel["label"]: panel for panel in old["panels"]}
        for panel in item["panels"]:
            label = panel["label"]
            x, y, width, height = panel["xywh"]
            assert width == height == 160
            if label.startswith("V180-local-phase-"):
                binding = item["predictions"][label]
                assert ref(binding["path"]) == binding
                value = np.load(binding["path"], allow_pickle=False)
                expected_pixels = independent_display(
                    anchor + item["contrast"] * (value.astype(np.float64) - anchor),
                    arrays,
                    item["ROI_xywh"],
                    item["exposure"],
                )
                new_channels += expected_pixels.size
            else:
                px, py, pw, ph = old_panels[label]["xywh"]
                expected_pixels = old_image[py : py + ph, px : px + pw]
                copied_channels += expected_pixels.size
                if label in item["predictions"]:
                    binding = item["predictions"][label]
                    assert ref(binding["path"]) == binding
                    value = np.load(binding["path"], allow_pickle=False)
                    regenerated = independent_display(
                        anchor + item["contrast"] * (value.astype(np.float64) - anchor),
                        arrays,
                        item["ROI_xywh"],
                        item["exposure"],
                    )
                    np.testing.assert_array_equal(expected_pixels, regenerated)
                    prior_recomputed_channels += regenerated.size
            np.testing.assert_array_equal(image[y : y + height, x : x + width], expected_pixels)
    assert new_channels == figures["new_RGB_channels_independently_checked"] == 8294400
    assert copied_channels == figures["unchanged_RGB_channels_copied"]
    browser = read(REPO / "docs/results/v180-local-native-viewer-verification-v1.json")
    assert not browser["fixture_only_no_actual_V180_quality"]
    assert browser["cases"] == 48 and browser["browser_crop_screenshots"] == 480
    assert browser["RGB_channels_exact_source_PNG"] == 36864000
    assert browser["manifest"] == ref(IMAGES / "manifest-v1.json")
    assert browser["viewer"] == ref(IMAGES / "native-viewer.html")
    assert browser["per_method_state_metadata_checked"] and browser["JS_errors"] == []

    diary = diary.resolve()
    assert diary.is_relative_to(REPO / "diary") and diary.is_file()
    documents = [
        REPO / name
        for name in [
            "README.md",
            "docs/index.md",
            "docs/current-model.md",
            "docs/research.md",
            "docs/experiments.md",
            "docs/local-phase-evidence-matching.md",
            "docs/phase-evidence-matching.md",
            "docs/local-phase-evidence-comparison.md",
        ]
    ] + [diary]
    links = 0
    for path in documents:
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            assert resolved == VERIFICATION or resolved.is_file(), (path, target)
            links += 1
    assert not torch.cuda.is_initialized()
    save(
        VERIFICATION,
        {
            "status": "pass-exact-evidence-two-local-exports-comparison-tables-native-and-browser-pixels",
            "publication": ref(INDEX),
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "exact_receipt_copies": len(final["copies"]),
            "strict_CPU_export_loads": strict_loads,
            "matched_table_cells": 882,
            "native_figures": 60,
            "native_triplets": 12,
            "new_native_RGB_channels_recomputed": new_channels,
            "unchanged_native_RGB_channels_compared": copied_channels,
            "prior_V178_RGB_channels_also_recomputed": prior_recomputed_channels,
            "browser_RGB_channels_exact": 36864000,
            "document_links": links,
            "documents": {str(p): ref(p) for p in documents},
            "new_neural_forwards": 0,
            "new_sensor_noise_draws": 0,
            "CUDA_initialized": False,
            "scope": "Checks actual completed publication, not layout fixtures. Matched trial quality conclusions remain the recorded human interpretation; no blind-generalization or calibrated-noisy-sky claim follows from source/pixel integrity.",
        },
    )
    print(
        f"PASS two strict local exports/882cells/60nativefigures/{new_channels + copied_channels}RGBchannels/{links}links"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diary", type=Path, required=True)
    verify(parser.parse_args().diary)
