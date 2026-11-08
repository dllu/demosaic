"""Verify completed readout exports, evidence, native/browser pixels and guides."""

import argparse
import re
from pathlib import Path

import numpy as np
from lossless_native import load_native
from PIL import Image
from publish_dense_spectrum_trial import (
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
    plan, training, scores, _figures, paired = completed_context(ROOT, viewed=True)
    if VERIFICATION.exists():
        raise FileExistsError(VERIFICATION)
    final = read(INDEX)
    assert final["plan"] == ref(ROOT / "plan-v1.json")
    for key in ["report", "figures", "notes", "publication_source"]:
        assert ref(final[key]["path"]) == final[key]
    for pair in final["copies"].values():
        for binding in pair.values():
            assert ref(binding["path"]) == binding
        a, b = [Path(pair[k]["path"]) for k in ["original", "public"]]
        assert a.read_bytes() == b.read_bytes() and (a.stat().st_dev, a.stat().st_ino) == (
            b.stat().st_dev,
            b.stat().st_ino,
        )
    seal = read(final["publication_source"]["path"])
    assert seal["verifier"] == ref(__file__)
    for binding in seal["helpers"]:
        assert ref(binding["path"]) == {k: binding[k] for k in ["path", "sha256"]}
        if "text" in binding:
            assert Path(binding["path"]).read_text() == binding["text"]
    import torch
    from phase_wave_training_state import inherited_hash, load_ema
    from profile_raw_kernel_inference import model_hash
    from reduce_dense_spectrum_trial import tables
    from report_late_spectral_mixed_quiet import independent_display
    from spatial_wave_training_state import expand_checkpoint

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    original_call = torch.nn.Module._call_impl

    def forbidden(*args, **kwargs):
        raise RuntimeError("No Module forward in final publication verification")

    torch.nn.Module._call_impl = forbidden
    try:
        state = expand_checkpoint(
            torch.load(training["final_checkpoint"]["path"], map_location="cpu", weights_only=True)
        )
        initializer = torch.load(
            plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
        )
        strict = 0
        for endpoint, method in METHODS.items():
            entry = final["checkpoints"][method]
            assert (
                entry["source_checkpoint"] == training["final_checkpoint"]
                and entry["state"] == endpoint
            )
            assert ref(entry["export"]["path"]) == entry["export"]
            exported = torch.load(entry["export"]["path"], map_location="cpu", weights_only=True)
            actual = factory(plan["module_config"]).eval()
            actual.load_state_dict(exported["state_dict"], strict=True)
            expected = factory(plan["module_config"]).eval()
            expected.load_state_dict(state["models"], strict=True)
            if endpoint == "EMA":
                load_ema(expected, state["ema"])
            assert (
                model_hash(actual)
                == model_hash(expected)
                == entry["module_hash"]
                == scores["module_hashes"][method]["before"]
            )
            assert inherited_hash(actual) == plan["initializer"]["module_hash"]
            assert all(
                torch.equal(actual.state_dict()[n], v) for n, v in initializer["state_dict"].items()
            )
            assert (
                len(actual.state_dict()) == 193
                and sum(p.numel() for p in actual.parameters() if p.requires_grad) == 508
            )
            assert exported["component"] == type(actual).__name__ == entry["component"]
            assert exported["module_config"] == entry["module_config"] == plan["module_config"]
            assert (
                exported["new_readout_updates"] == 900
                and exported["inherited_network_updates"] == 1800
                and exported["inherited_adapter_updates"] == 900
            )
            assert (
                exported["frozen_V183_initializer"]
                == entry["frozen_V183_initializer"]
                == plan["initializer"]
            )
            assert ref(exported["source"]["path"]) == exported["source"] == entry["source"]
            strict += 1
        text, cells = tables(paired["summary"])
        assert len(cells) == 2058 and cells == paired["table_cells"]
        assert (
            ROOT / "comparison-tables-v1.md"
        ).read_text() == text + "\n" and text in REPORT.read_text()
        manifest = read(final["figures"]["path"])
        assert (
            manifest["fixture"] is False
            and manifest["method_checkpoints"] == final["viewer_method_checkpoints"]
        )
        old_index = read(final["baseline_publication"]["path"])
        assert all(
            manifest["method_checkpoints"][m] == v
            for m, v in old_index["viewer_method_checkpoints"].items()
        )
        assert len(manifest["method_checkpoints"]) == 20
        prior = read(ROOT.parent / "V189-spaced-pooled-trial-v1/figures-v1.json")
        old_map = {i["image"]["path"]: i for i in prior["images"]}
        new_channels = copied_channels = old_prediction_channels = 0
        assert len(manifest["images"]) == 60 and sum(i["triplet"] for i in manifest["images"]) == 12
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
            assert item["case"] == old["case"]
            image = np.asarray(Image.open(item["image"]["path"]).convert("RGB"))
            old_image = np.asarray(Image.open(old["image"]["path"]).convert("RGB"))
            arrays = dict(np.load(item["case"]["arrays"]["path"], allow_pickle=False))
            anchor = np.asarray(item["anchor"]).reshape(1, 3, 1, 1)
            old_panels = {p["label"]: p for p in old["panels"]}
            for panel in item["panels"]:
                label = panel["label"]
                x, y, w, h = panel["xywh"]
                assert w == h == 160
                actual = image[y : y + h, x : x + w]
                if label in METHODS.values():
                    binding = item["predictions"][label]
                    assert (
                        binding == scores["native_predictions"][item["case"]["id"]][label]
                        and ref(binding["path"]) == binding
                    )
                    rgb = load_native(binding)
                    displayed = anchor + item["contrast"] * (rgb.astype(np.float64) - anchor)
                    np.testing.assert_array_equal(
                        actual,
                        independent_display(displayed, arrays, item["ROI_xywh"], item["exposure"]),
                    )
                    new_channels += actual.size
                else:
                    old_panel = old_panels[label]
                    ox, oy, ow, oh = old_panel["xywh"]
                    assert ow == oh == 160
                    np.testing.assert_array_equal(actual, old_image[oy : oy + oh, ox : ox + ow])
                    copied_channels += actual.size
                    if label in item.get("predictions", {}):
                        binding = item["predictions"][label]
                        assert ref(binding["path"]) == binding
                        rgb = load_native(binding)
                        displayed = anchor + item["contrast"] * (rgb.astype(np.float64) - anchor)
                        np.testing.assert_array_equal(
                            actual,
                            independent_display(
                                displayed, arrays, item["ROI_xywh"], item["exposure"]
                            ),
                        )
                        old_prediction_channels += actual.size
        assert (
            new_channels == 8294400
            and copied_channels == 95001600
            and old_prediction_channels == 66355200
        )
        browser_path = REPO / "docs/results/v191-dense-spectrum-native-viewer-verification-v1.json"
        browser = read(browser_path)
        assert (
            browser["RGB_channels_exact_source_PNG"] == 36864000
            and browser["browser_crop_screenshots"] == 480
        )
        assert (
            browser["JS_errors"] == [] and browser["fixture_only_no_actual_V191_quality"] is False
        )
        assert (
            browser["viewer"] == ref(IMAGES / "native-viewer.html")
            and browser["manifest"] == final["figures"]
        )
        diary = diary.resolve()
        assert diary.is_relative_to(REPO / "diary") and diary.is_file()
        documents = [
            REPO / p
            for p in [
                "README.md",
                "docs/index.md",
                "docs/current-model.md",
                "docs/research.md",
                "docs/experiments.md",
                "docs/dense-local-spectrum-readout.md",
                "docs/phase-evidence-matching.md",
                "docs/dense-local-spectrum-comparison.md",
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
                "status": "pass-readout-exports-frozen-inheritance-tables-native-browser-pixels-and-documents",
                "publication": ref(INDEX),
                "source": dict(ref(__file__), text=Path(__file__).read_text()),
                "exact_linked_receipt_copies": len(final["copies"]),
                "strict_CPU_export_loads": strict,
                "inherited_tensor_comparisons": 378,
                "table_cells": 2058,
                "native_figures": 60,
                "native_triplets": 12,
                "new_native_RGB_channels_recomputed": new_channels,
                "unchanged_native_RGB_channels_compared": copied_channels,
                "old_eighteen_prediction_channels_also_recomputed": old_prediction_channels,
                "browser_RGB_channels_exact": 36864000,
                "document_links": links,
                "documents": {str(p): ref(p) for p in documents},
                "new_module_forwards": 0,
                "new_sensor_noise_draws": 0,
                "CUDA_initialized": False,
                "scope": "Actual completed publication integrity. Dense local spectra,raw-coefficient units andHannOLA synthesis change together at matched508parameter/900update budget;human quality interpretation remains separate. No blind-generalization or calibrated noisy-sky safety claim.",
            },
        )
        print(
            f"PASS2strictExports/2058cells/60native/{new_channels + copied_channels}RGBchannels/480browser/{links}links"
        )
    finally:
        torch.nn.Module._call_impl = original_call


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--diary", type=Path, required=True)
    verify(parser.parse_args().diary)
