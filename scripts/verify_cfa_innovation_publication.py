"""Independent public V198 table/export/native/browser verification and final index."""

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
from admit_cfa_innovation_wave import MODES, factory
from directional_trial_protocol import REPO, freeze, read, ref, save
from lossless_native import load_native
from phase_admission_protocol import owner_live
from publish_cfa_innovation_wave import EVIDENCE, IMAGES, INDEX, PROOF, REPORT, STAGE
from review_cfa_innovation_wave import review_plan, source_guard
from spatial_trial_protocol import read as read_any
from train_cfa_innovation_wave import ROOT


def prepare():
    plan = review_plan()
    source_guard(plan)
    assert not (ROOT / "verification-source-v1.json").exists()
    work, sources = freeze(
        ROOT / "verification-frozen-v1",
        ["verify_cfa_innovation_publication.py", "represent_cfa_innovation_real_crops.py"],
    )
    save(
        ROOT / "verification-source-v1.json",
        {
            "runner": ref(work / "scripts/verify_cfa_innovation_publication.py"),
            "representer": ref(work / "scripts/represent_cfa_innovation_real_crops.py"),
            "work": str(work),
            "plan": ref(ROOT / "plan-v1.json"),
            "frozen_files": sources,
        },
    )
    print("Prepared independent public artifact verifier; no result declared")


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def verify_report_values(bindings, paired):
    core = (ROOT / "report-core-table-v1.md").read_text().strip().splitlines()
    records = bindings["core_numeric_bindings"]
    assert len(records) == 126 and len(core) == 16
    methods = paired["methods"]
    assert len(methods) == 9 and len({(r["row"], r["method"]) for r in records}) == 126
    for record in records:
        source = [
            r
            for r in paired["table_rows"]
            if all(r[k] == record[k] for k in ["kind", "condition", "cohort", "field"])
        ]
        assert len(source) == 1
        source = source[0]
        cells = [v.strip() for v in core[record["row"] + 2].strip("|").split("|")]
        assert len(cells) == 11 and cells[1] == str(source["cases"])
        expected = format(source["values"][record["method"]] * record["scale"], record["format"])
        assert cells[2 + methods.index(record["method"])] == record["display"] == expected
    direction = read(ROOT / "directional-breakdown-v1.json")
    rows = direction["rows"] + direction["previous_context_rows"]
    indexed = {(r["id"], r["method"]): r for r in rows}
    assert len(indexed) == 16
    table = (ROOT / "report-direction-table-v1.md").read_text().strip().splitlines()
    records = bindings["direction_numeric_bindings"]
    assert len(table) == 18 and len(records) == 48
    assert len({(r["id"], r["method"], r["metric"]) for r in records}) == 48
    for record in records:
        source = indexed[record["id"], record["method"]]
        if record["metric"] == "whole":
            value, column = source["whole_template_gain"], 2
        else:
            index = {"regionA": 0, "regionB": 1}[record["metric"]]
            value, column = source["sectors"][index]["gain"], 3 + index
        cells = [v.strip() for v in table[record["row"] + 2].strip("|").split("|")]
        assert cells[0] == record["id"].split("seed")[1][:10]
        assert cells[1] == bindings["direction_method_labels"][record["method"]]
        assert cells[column] == record["display"] == format(value * 100, record["format"])
    return 126, 48


def verify(diary):
    plan = review_plan()
    source_guard(plan)
    seal = read(ROOT / "verification-source-v1.json")
    assert ref(__file__) == seal["runner"] and seal["plan"] == ref(ROOT / "plan-v1.json")
    for name, digest in seal["frozen_files"].items():
        assert sha(name) == digest
    assert not INDEX.exists() and not PROOF.exists()
    stage = read(STAGE)
    scores = read(ROOT / "scores-v1.json")
    assert not owner_live(scores["owner"]) and len(scores["rows"]) == 1644
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
    assert cells == 1098
    bindings = read(ROOT / "report-bindings-v1.json")
    main_cells, direction_cells = verify_report_values(bindings, paired)
    assert ref(REPORT) == bindings["report"]
    assert (ROOT / "report-core-table-v1.md").read_text().strip() in REPORT.read_text()
    assert (ROOT / "report-direction-table-v1.md").read_text().strip() in REPORT.read_text()
    manifest = read(IMAGES / "manifest-v1.json")
    viewing = read(ROOT / "native-viewing-completion-v1.json")
    assert viewing["indices"] == list(range(60)) and viewing["sheets"] == list(range(15))
    assert viewing["figures"] == ref(ROOT / "figures-v1.json")
    assert ref(viewing["journal"]["path"]) == viewing["journal"]
    browser = read(ROOT / "browser-source-pixels-v1.json")
    assert browser["RGB_channels_exact_source_PNG"] == 110592000
    assert browser["browser_crop_screenshots"] == 1440 and browser["JS_errors"] == []
    assert browser["viewer"] == ref(IMAGES / "native-viewer.html")
    assert browser["manifest"] == ref(IMAGES / "manifest-v1.json")
    for binding in browser["screenshot_bindings"]:
        assert ref(binding["path"]) == binding
    import torch
    from cfa_innovation_state import anchor_hash
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
                module = factory(plan, mode)
                module.load_state_dict(payload["state_dict"], strict=True)
                assert (
                    model_hash(module)
                    == entry["module_hash"]
                    == scores["module_hashes"][method]["before"]
                )
                assert anchor_hash(module) == plan["initializer"]["module_hash"]
                assert (
                    len(module.state_dict()) == 197
                    and sum(p.numel() for p in module.parameters() if p.requires_grad) == 451
                )
                assert payload["new_readout_updates"] == payload["head_Adam_updates"] == 900
                assert payload["prior_anchor_readout_updates"] == 1800
                assert payload["module_config"] == dict(
                    plan["module_config"], lower=plan["lower_native_frequency"]
                )
                assert payload["fresh_head_Adam_initial_updates"] == 0
                assert payload["endpoint"] == entry["state"] == endpoint
                assert payload["frozen_V195_anchor"] == plan["anchor"]
                strict += 1
        assert len(manifest["images"]) == 60 and manifest["fixture"] is False
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
        assert strict == 2 and triplets == 12 and prediction_channels == 23040000
        assert source_channels == 9830400
    finally:
        torch.nn.Module._call_impl = original
    assert not torch.cuda.is_initialized()
    representatives = read(EVIDENCE / "representative-figures-v1.json")
    assert representatives["core_manifest"] == ref(IMAGES / "manifest-v1.json")
    assert len(representatives["images"]) == 2
    representative_channels = 0
    by_source = {item["image"]["path"]: item for item in manifest["images"]}
    for item in representatives["images"]:
        assert item["no_resize"] and ref(item["image"]["path"]) == item["image"]
        assert ref(item["source_figure"]["path"]) == item["source_figure"]
        assert item["checkpoint"] == manifest["method_checkpoints"]["V198-CFA-wave-EMA"]
        core = by_source[item["source_figure"]["path"]]
        for key in ["case", "ROI_xywh", "exposure", "contrast", "anchor"]:
            assert item[key] == core[key]
        labels = [p["label"] for p in item["panels"]]
        assert labels == [core["panels"][0]["label"], "V198-CFA-wave-EMA", "ISO100 AHD, not GT"]
        assert "not exactGT" in item["reference_role"]
        actual = np.asarray(Image.open(item["image"]["path"]).convert("RGB"))
        source = np.asarray(Image.open(item["source_figure"]["path"]).convert("RGB"))
        for panel in item["panels"]:
            source_panel = next(p for p in core["panels"] if p["label"] == panel["label"])
            assert panel["source_xywh"] == source_panel["xywh"]
            sx, sy, w, h = panel["source_xywh"]
            x, y, dw, dh = panel["xywh"]
            assert w == h == dw == dh == 160
            np.testing.assert_array_equal(
                actual[y : y + h, x : x + w], source[sy : sy + h, sx : sx + w]
            )
            representative_channels += w * h * 3
    assert representative_channels == representatives["RGB_channels_exact_source_copy"] == 460800
    # Preserve supplementary evidence as exact copies; avoid recopied datasets/arrays.
    extras = {}
    for name in [
        "native-viewing-v1.jsonl",
        "native-viewing-completion-v1.json",
        "browser-source-pixels-v1.json",
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
            "docs/cfa-innovation-wave.md",
            "docs/cfa-innovation-evaluation.md",
            "docs/innovation-frequency-selection.md",
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
        status="completed-V198-CFA-architecture-quality-audited-native-viewed-and-two-exports",
        report=ref(REPORT),
        diary=ref(diary),
        native_viewing=ref(ROOT / "native-viewing-completion-v1.json"),
        browser_verification=ref(ROOT / "browser-source-pixels-v1.json"),
        verification_source=ref(ROOT / "verification-source-v1.json"),
        supplementary_copies=extras,
        metric_CSV=ref(EVIDENCE / "metrics-table-v1.csv"),
        representative_real_panels=ref(EVIDENCE / "representative-figures-v1.json"),
        evidence_source=ref(ROOT / "quality-audit-v1.json"),
        scope=bindings["interpretation"],
    )
    save(INDEX, final)
    save(
        PROOF,
        {
            "status": "pass-V198-public-exports-tables-native-browser-pixels-and-documents",
            "created_unix_UTC": time.time(),
            "publication": ref(INDEX),
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "strict_CPU_export_loads": strict,
            "frozen_anchor_tensor_comparisons": 386,
            "table_rows": 122,
            "numeric_table_cells": cells,
            "main_report_cells": main_cells,
            "direction_report_cells": direction_cells,
            "native_figures": 60,
            "native_triplets": triplets,
            "prediction_RGB_channels_independently_displayed": prediction_channels,
            "unchanged_noisy_reference_RGB_channels_compared": source_channels,
            "browser_RGB_channels_exact": 110592000,
            "browser_native_captures": 1440,
            "representative_real_RGB_channels_exact": representative_channels,
            "document_links_checked": checked_links,
            "documents": [ref(p) for p in documents],
            "new_module_forwards": 0,
            "CUDA_initialized": False,
            "scope": "Every public panel checked at native160px; 1098 CSV values matched to complete source means. Two exports strictly loaded and matched to evaluated states and explicit fresh-stage history. Actual native viewing and separate browser screenshot proof inspected. Source/reference caveats preserved.",
        },
    )
    print(
        "PASS: final V198 publication /1098 table cells /60 native figures /1440 browser captures"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "verify"])
    parser.add_argument("--diary", type=Path)
    args = parser.parse_args()
    prepare() if args.phase == "prepare" else verify(args.diary.resolve())
