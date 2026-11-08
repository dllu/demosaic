"""Independent public V195 table/export/native/browser verification and final index."""

import argparse
import csv
import gzip
import hashlib
import re
import shutil
import time
from pathlib import Path
from urllib.parse import unquote

import numpy as np
from directional_trial_protocol import MODES, REPO, factory, freeze, read, ref, save
from directional_trial_protocol import TRIAL as ROOT
from lossless_native import load_native
from phase_admission_protocol import owner_live
from publish_directional_response import EVIDENCE, IMAGES, INDEX, PROOF, REPORT, STAGE
from review_directional_response import source_guard
from spatial_trial_protocol import read as read_any


def prepare():
    plan = read(ROOT / "plan-v1.json")
    source_guard(plan)
    assert not (ROOT / "verification-source-v1.json").exists()
    work, sources = freeze(ROOT / "verification-frozen-v1", ["verify_directional_publication.py"])
    save(
        ROOT / "verification-source-v1.json",
        {
            "runner": ref(work / "scripts/verify_directional_publication.py"),
            "work": str(work),
            "plan": ref(ROOT / "plan-v1.json"),
            "frozen_files": sources,
        },
    )
    print("Prepared independent public artifact verifier; no result declared")


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify(diary):
    plan = read(ROOT / "plan-v1.json")
    source_guard(plan)
    seal = read(ROOT / "verification-source-v1.json")
    assert ref(__file__) == seal["runner"] and seal["plan"] == ref(ROOT / "plan-v1.json")
    for name, digest in seal["frozen_files"].items():
        assert sha(name) == digest
    assert not INDEX.exists() and not PROOF.exists()
    stage = read(STAGE)
    scores = read(ROOT / "scores-v1.json")
    assert not owner_live(scores["owner"]) and len(scores["rows"]) == 3288
    for name in ["training-audit-v1.json", "quality-audit-v1.json"]:
        assert read(ROOT / name)["status"].startswith("pass-")
    for pair in stage["copies"].values():
        assert ref(pair["original"]["path"]) == pair["original"]
        if "public_gzip" in pair:
            assert ref(pair["public_gzip"]["path"]) == pair["public_gzip"]
            with gzip.open(pair["public_gzip"]["path"], "rb") as f:
                assert hashlib.file_digest(f, "sha256").hexdigest() == pair["original"]["sha256"]
        else:
            assert ref(pair["public"]["path"])["sha256"] == pair["original"]["sha256"]
    paired = read_any(ROOT / "paired-comparisons-v1.json.gz")
    with (EVIDENCE / "metrics-table-v1.csv").open(newline="") as f:
        table = list(csv.DictReader(f))
    assert len(table) == len(paired["table_rows"]) == 122
    cells = 0
    for actual, expected in zip(table, paired["table_rows"], strict=True):
        for key in ["kind", "condition", "cohort", "field", "cases"]:
            value = "" if expected[key] is None else str(expected[key])
            assert actual[key] == value
        for method in paired["methods"]:
            assert float(actual[method]) == expected["values"][method]
            cells += 1
    assert cells == 732
    bindings = read(ROOT / "report-bindings-v1.json")
    assert ref(REPORT) == bindings["report"]
    assert (ROOT / "report-core-table-v1.md").read_text().strip() in REPORT.read_text()
    assert (ROOT / "report-direction-table-v1.md").read_text().strip() in REPORT.read_text()
    manifest = read(IMAGES / "manifest-v1.json")
    viewing = read(ROOT / "native-viewing-completion-v1.json")
    assert viewing["indices"] == list(range(72)) and viewing["sheets"] == list(range(18))
    assert viewing["figures"] == ref(ROOT / "figures-v1.json")
    assert ref(viewing["journal"]["path"]) == viewing["journal"]
    browser = read(ROOT / "browser-source-pixels-v1.json")
    assert browser["RGB_channels_exact_source_PNG"] == 36864000
    assert browser["browser_crop_screenshots"] == 480 and browser["JS_errors"] == []
    assert browser["viewer"] == ref(IMAGES / "native-viewer.html")
    assert browser["manifest"] == ref(IMAGES / "manifest-v1.json")
    for binding in browser["screenshot_bindings"]:
        assert ref(binding["path"]) == binding
    import torch
    from phase_wave_training_state import inherited_hash
    from profile_raw_kernel_inference import model_hash
    from report_late_spectral_mixed_quiet import independent_display

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    original = torch.nn.Module._call_impl

    def forbidden(*args, **kwargs):
        raise RuntimeError("No module forward during publication verification")

    torch.nn.Module._call_impl = forbidden
    exports = read(ROOT / "exports-v1.json")["exports"]
    strict = prediction_channels = source_channels = triplets = 0
    cache = {}
    try:
        for mode in MODES:
            for endpoint, method in plan["methods"][mode].items():
                entry = exports[method]
                assert stage["checkpoints"][method] == entry
                assert ref(entry["export"]["path"]) == entry["export"]
                payload = torch.load(entry["export"]["path"], map_location="cpu", weights_only=True)
                module = factory(plan["module_config"])
                module.load_state_dict(payload["state_dict"], strict=True)
                assert (
                    model_hash(module)
                    == entry["module_hash"]
                    == scores["module_hashes"][method]["before"]
                )
                assert inherited_hash(module) == plan["initializer"]["module_hash"]
                assert (
                    len(module.state_dict()) == 193
                    and sum(p.numel() for p in module.parameters() if p.requires_grad) == 508
                )
                assert (
                    payload["prior_donor_readout_updates"]
                    == payload["new_readout_updates"]
                    == payload["head_Adam_updates"]
                    == 900
                )
                assert payload["fresh_head_Adam_initial_updates"] == 0
                assert payload["endpoint"] == entry["state"] == endpoint
                assert payload["trained_head_donor"] == plan["donor"]
                strict += 1
        assert len(manifest["images"]) == 72 and manifest["fixture"] is False
        from PIL import Image

        for item in manifest["images"]:
            assert ref(item["image"]["path"]) == item["image"]
            assert sha(item["image"]["path"]) == sha(item["original_image"]["path"])
            case = item["case"]
            with np.load(case["arrays"]["path"], allow_pickle=False) as a:
                arrays = {k: a[k] for k in ["wb", "matrix"]}
            image = np.asarray(Image.open(item["image"]["path"]).convert("RGB"))
            anchor = np.asarray(item["anchor"], dtype=np.float64).reshape(1, 3, 1, 1)
            sx, sy, sw, sh = item["ROI_xywh"]
            assert sw == sh == 160 and item["no_resize"] is True
            for panel in item["panels"]:
                x, y, w, h = panel["xywh"]
                assert w == h == 160
                if "prediction" in panel:
                    binding = panel["prediction"]
                    key = binding["path"]
                    if key not in cache:
                        cache[key] = load_native(binding)
                    value = cache[key][..., sy : sy + sh, sx : sx + sw]
                    displayed = anchor + item["contrast"] * (value.astype(np.float64) - anchor)
                    expected = independent_display(
                        displayed, arrays, [0, 0, 160, 160], item["exposure"]
                    )
                    prediction_channels += expected.size
                else:
                    binding = panel["source_figure"]
                    assert ref(binding["path"]) == binding
                    px, py, pw, ph = panel["source_xywh"]
                    expected = np.asarray(Image.open(binding["path"]).convert("RGB"))[
                        py : py + ph, px : px + pw
                    ]
                    source_channels += expected.size
                np.testing.assert_array_equal(image[y : y + h, x : x + w], expected)
            triplets += int(item["triplet"])
            if len(cache) > 20:
                cache.clear()
        assert strict == 4 and triplets == 24 and prediction_channels == 20275200
        assert source_channels == 11673600
    finally:
        torch.nn.Module._call_impl = original
    assert not torch.cuda.is_initialized()
    # Preserve supplementary evidence as exact copies; avoid recopied datasets/arrays.
    extras = {}
    for name in [
        "native-viewing-v1.jsonl",
        "native-viewing-completion-v1.json",
        "browser-source-pixels-v1.json",
        "render-source-v2.json",
        "publication-canonical-lint-v1.json",
        "report-bindings-v1.json",
    ]:
        source = ROOT / name
        target = EVIDENCE / name
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
        extras[name] = {"original": ref(source), "public": ref(target)}
    documents = [
        REPO / name
        for name in [
            "README.md",
            "docs/index.md",
            "docs/current-model.md",
            "docs/research.md",
            "docs/experiments.md",
            "docs/directional-pair-response.md",
        ]
    ] + [REPORT, diary]
    checked_links = 0
    from diary import resolve

    for document in documents:
        for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", document.read_text()):
            target = match.group(1).strip().strip("<>")
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            target = unquote(target.split("#", 1)[0])
            destination = (document.parent / target).resolve()
            if destination in [INDEX, PROOF]:
                continue
            if not destination.exists() and destination.is_relative_to(REPO):
                destination = resolve(REPO, destination)
            assert destination.exists(), (document, target)
            checked_links += 1
    final = dict(stage)
    final.update(
        status="completed-V195-matched-response-quality-audited-native-viewed-and-four-exports",
        report=ref(REPORT),
        diary=ref(diary),
        native_viewing=ref(ROOT / "native-viewing-completion-v1.json"),
        browser_verification=ref(ROOT / "browser-source-pixels-v1.json"),
        verification_source=ref(ROOT / "verification-source-v1.json"),
        supplementary_copies=extras,
        metric_CSV=ref(EVIDENCE / "metrics-table-v1.csv"),
        evidence_source=ref(ROOT / "quality-audit-v1.json"),
        scope="Completed four-endpoint matched response-pressure comparison. Whole EMA is a stronger-response option with quiet/flat costs; angular balancing gives slightly lower quiet RMS than whole control but weaker mesh response. No convincing new real fine cab crossings or elimination of flat mottle. V187 remains a quieter alternative and V120 general. Full goal remains unresolved.",
    )
    save(INDEX, final)
    save(
        PROOF,
        {
            "status": "pass-V195-public-exports-tables-native-browser-pixels-and-documents",
            "created_unix_UTC": time.time(),
            "publication": ref(INDEX),
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "strict_CPU_export_loads": strict,
            "inherited_tensor_comparisons": 756,
            "table_rows": 122,
            "numeric_table_cells": cells,
            "main_report_cells": 84,
            "native_figures": 72,
            "native_triplets": triplets,
            "prediction_RGB_channels_independently_displayed": prediction_channels,
            "unchanged_noisy_reference_RGB_channels_compared": source_channels,
            "browser_RGB_channels_exact": 36864000,
            "browser_native_captures": 480,
            "document_links_checked": checked_links,
            "documents": [ref(p) for p in documents],
            "new_module_forwards": 0,
            "CUDA_initialized": False,
            "scope": "Every public panel checked at native160px; 732 CSV values matched to complete source means. Four exports strictly loaded and matched to evaluated states and explicit fresh-stage history. Actual native viewing and separate browser screenshot proof inspected. Source/reference caveats preserved.",
        },
    )
    print("PASS: final V195 publication /732 table cells /72 native figures /480 browser captures")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "verify"])
    parser.add_argument("--diary", type=Path)
    args = parser.parse_args()
    prepare() if args.phase == "prepare" else verify(args.diary.resolve())
