"""Stage compact V200 native comparisons; record actual viewing separately."""

import argparse
import gzip
import hashlib
import json
import shutil
import time
from pathlib import Path

from directional_trial_protocol import REPO, freeze, read, ref, save
from phase_admission_protocol import owner_live
from review_scale_supported_cfa_wave import review_plan, source_guard
from spatial_trial_protocol import read as read_any
from train_scale_supported_cfa_wave import ROOT

STEM = "v200-scale-supported-cfa-wave-v1"
IMAGES = REPO / "docs/images" / STEM
EVIDENCE = REPO / "docs/results" / STEM
REPORT = REPO / "docs/scale-supported-cfa-wave-comparison.md"
INDEX = REPO / "docs/results/v200-scale-supported-cfa-wave-final-v1.json"
PROOF = REPO / "docs/results/v200-scale-supported-cfa-wave-publication-verification-v1.json"
STAGE = REPO / "docs/results/v200-scale-supported-cfa-wave-native-stage-v1.json"


def prepare():
    plan = review_plan()
    source_guard(plan)
    assert not (ROOT / "publication-source-v1.json").exists()
    work, sources = freeze(
        ROOT / "publication-frozen-v1",
        [
            "publish_scale_supported_cfa_wave.py",
            "check_scale_supported_cfa_viewer_pixels.py",
            "build_scale_supported_cfa_viewer.py",
        ],
    )
    checker = work / "scripts/verify-scale-supported-cfa-viewer-actual-v1.cjs"
    shutil.copyfile(REPO / "scripts" / checker.name, checker)
    save(
        ROOT / "publication-source-v1.json",
        {
            "plan": ref(ROOT / "plan-v1.json"),
            "work": str(work),
            "publisher": ref(work / "scripts/publish_scale_supported_cfa_wave.py"),
            "browser_checker": ref(checker),
            "pixel_checker": ref(work / "scripts/check_scale_supported_cfa_viewer_pixels.py"),
            "frozen_files": sources,
            "scope": "Stage only after actual two-endpoint review and CPU audits/exports. Compact60figures/12triplets and seven-state viewer. Actual native viewing and browser source-pixel checks precede a final quality report/publication.",
        },
    )
    print("Prepared compact native publication sources; no outputs copied")


def publication_guard():
    plan = review_plan()
    source_guard(plan)
    seal = read(ROOT / "publication-source-v1.json")
    assert ref(__file__) == seal["publisher"]
    for path, digest in seal["frozen_files"].items():
        assert ref(path)["sha256"] == digest
    assert ref(seal["browser_checker"]["path"]) == seal["browser_checker"]
    return plan, seal


def completed():
    plan, seal = publication_guard()
    controller = read(ROOT / "quality-controller-v1/watch-result-v1.json")
    assert not owner_live(controller["owner"])
    assert controller["figures"] == ref(ROOT / "figures-v1.json")
    scores = read(ROOT / "scores-v1.json")
    assert not owner_live(scores["owner"])
    assert scores["status"] == "completed-V200-two-endpoint-quality-awaiting-native-viewing"
    assert len(scores["rows"]) == 1644 and scores["counts"] == plan["expected_quality_counts"]
    for name in ["training-audit-v1.json", "quality-audit-v1.json", "exports-v1.json"]:
        assert read(ROOT / name)["status"].startswith("pass-")
    figures = read(ROOT / "figures-v1.json")
    assert figures["native_figures"] == 60 and figures["native_triplets"] == 12
    assert len(figures["images"]) == 60 and len(figures["sheets"]) == 15
    assert all(f["no_resize"] for f in figures["images"])
    exports = read(ROOT / "exports-v1.json")["exports"]
    assert len(exports) == 2
    assert read(ROOT / "directional-breakdown-v1.json")["status"].startswith("pass-four-V200")
    return plan, seal, scores, figures, exports


def stage():
    plan, _seal, _scores, figures, exports = completed()
    assert not STAGE.exists() and not IMAGES.exists() and not EVIDENCE.exists()
    IMAGES.mkdir()
    EVIDENCE.mkdir()
    manifest = dict(figures)
    manifest["images"] = []
    for item in figures["images"]:
        assert ref(item["image"]["path"]) == item["image"]
        target = IMAGES / Path(item["image"]["path"]).name
        shutil.copyfile(item["image"]["path"], target)
        assert ref(target)["sha256"] == item["image"]["sha256"]
        manifest["images"].append(dict(item, image=ref(target), original_image=item["image"]))
    old = read(REPO / "docs/results/v195-response-final-v1.json")
    quieter = read(REPO / "docs/results/v187-pooled-wave-final-v1.json")
    innovation = read(REPO / "docs/results/v197-innovation-wave-final-v1.json")
    cfa = read(REPO / "docs/results/v198-cfa-innovation-wave-final-v1.json")
    manifest.update(
        fixture=False,
        method_checkpoints={
            "V187-pooled-wave-EMA": quieter["checkpoints"]["V187-pooled-wave-EMA"],
            "V195-whole-response-EMA": old["checkpoints"]["V195-whole-response-EMA"],
            "V197-innovation-wave-EMA": innovation["checkpoints"]["V197-innovation-wave-EMA"],
            **{m: cfa["checkpoints"][m] for m in ["V198-CFA-wave-raw", "V198-CFA-wave-EMA"]},
            **exports,
        },
        publication_source=ref(ROOT / "publication-source-v1.json"),
    )
    save(IMAGES / "manifest-v1.json", manifest)
    from build_scale_supported_cfa_viewer import build

    build(
        IMAGES / "manifest-v1.json",
        IMAGES / "native-viewer.html",
        REPORT.name,
        method_a="V198-CFA-wave-EMA",
        method_b=plan["methods"]["scale"]["EMA"],
    )
    copies = {}
    paths = [
        ROOT / name
        for name in [
            "plan-v1.json",
            "quality-audit-v1.json",
            "exports-v1.json",
            "scores-v1.json",
            "quality-events-v1.jsonl",
            "quality-observations-v1.jsonl.gz",
            "paired-comparisons-v1.json.gz",
            "reference-display-preflight-v1.json",
            "review-source-v1.json",
            "metric-preflight-v1.json",
            "input-layout-preflight-v1.json",
            "training-audit-v1.json",
            "feature-bridge-v1.json",
        ]
    ]
    paths += [ROOT / "directional-breakdown-v1.json"]
    for source in paths:
        name = (
            "directional-breakdown-result-v1.json"
            if source.parent.name == "directional-breakdown-v2"
            else source.name
        )
        original = ref(source)
        if source.stat().st_size > 200000 and source.suffix != ".gz":
            target = EVIDENCE / (name + ".gz")
            with source.open("rb") as src, gzip.open(target, "xb") as dst:
                shutil.copyfileobj(src, dst)
            with gzip.open(target, "rb") as f:
                assert hashlib.file_digest(f, "sha256").hexdigest() == original["sha256"]
            copies[name] = {
                "original": original,
                "public_gzip": ref(target),
                "decompressed_SHA256": original["sha256"],
            }
        else:
            target = EVIDENCE / name
            shutil.copyfile(source, target)
            assert ref(target)["sha256"] == original["sha256"]
            copies[name] = {"original": original, "public": ref(target)}
    paired = read_any(ROOT / "paired-comparisons-v1.json.gz")
    save(
        STAGE,
        {
            "status": "staged-actual-V200-native-comparisons-awaiting-viewing-and-final-report",
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v1.json"),
            "figures": ref(IMAGES / "manifest-v1.json"),
            "viewer": ref(IMAGES / "native-viewer.html"),
            "copies": copies,
            "checkpoints": exports,
            "viewer_method_checkpoints": manifest["method_checkpoints"],
            "native_figures": 60,
            "native_triplets": 12,
            "table_rows": len(paired["table_rows"]),
            "comparison_methods": paired["methods"],
            "publication_source": ref(ROOT / "publication-source-v1.json"),
            "scope": "Actual trained outputs/audits staged with no pixel resizing. Native viewing,actual browser pixels,interpretation and final report remain pending; this is not a promotion claim.",
        },
    )
    print("Staged60nativefigures/12triplets/seven-state viewer; actual viewing remains")


def record_viewing(selected, notes):
    _, _, _, figures, _ = completed()
    assert selected and len(selected) == len(set(selected))
    assert set(selected) <= set(range(15)) and notes.strip()
    path = ROOT / "native-viewing-v1.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
    seen = {n for event in events for n in event["sheets"]}
    assert not seen.intersection(selected)
    for n in selected:
        binding = figures["sheets"][n]["image"]
        assert ref(binding["path"]) == binding
    event = {
        "recorded_unix_UTC": time.time(),
        "sheets": selected,
        "detail": "original",
        "notes": notes,
    }
    with path.open("a") as f:
        f.write(json.dumps(event) + "\n")
    seen.update(selected)
    if seen == set(range(15)):
        save(
            ROOT / "native-viewing-completion-v1.json",
            {
                "status": "actually-viewed60-native-figures-and12triplets-in15-original-detail-sheets",
                "figures": ref(ROOT / "figures-v1.json"),
                "journal": ref(path),
                "indices": list(range(60)),
                "sheets": list(range(15)),
                "no_resize": True,
            },
        )
    print("Recorded", selected, "; viewed", len(seen), "/15 original sheets")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "stage", "view"])
    parser.add_argument("--sheets", type=int, nargs="+")
    parser.add_argument("--notes")
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare()
    elif args.phase == "stage":
        stage()
    else:
        record_viewing(args.sheets, args.notes)
