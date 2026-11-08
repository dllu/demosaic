"""Stage compact V195 native comparisons; record actual viewing separately."""

import argparse
import gzip
import hashlib
import json
import shutil
import time
from pathlib import Path

from directional_trial_protocol import REPO, freeze, read, ref, save
from directional_trial_protocol import TRIAL as ROOT
from phase_admission_protocol import owner_live
from review_directional_response import source_guard
from spatial_trial_protocol import read as read_any

STEM = "v195-directional-response-v1"
IMAGES = REPO / "docs/images" / STEM
EVIDENCE = REPO / "docs/results" / STEM
REPORT = REPO / "docs/directional-response-comparison.md"
INDEX = REPO / "docs/results/v195-response-final-v1.json"
PROOF = REPO / "docs/results/v195-response-publication-verification-v1.json"
STAGE = REPO / "docs/results/v195-response-native-stage-v1.json"


def prepare():
    plan = read(ROOT / "plan-v1.json")
    source_guard(plan)
    assert not (ROOT / "publication-source-v1.json").exists()
    work, sources = freeze(
        ROOT / "publication-frozen-v1",
        [
            "publish_directional_response.py",
            "check_directional_viewer_pixels.py",
            "build_large_dense_native_viewer.py",
        ],
    )
    checker = work / "scripts/verify-directional-viewer-actual-v1.cjs"
    shutil.copyfile(REPO / "scripts" / checker.name, checker)
    save(
        ROOT / "publication-source-v1.json",
        {
            "plan": ref(ROOT / "plan-v1.json"),
            "work": str(work),
            "publisher": ref(work / "scripts/publish_directional_response.py"),
            "browser_checker": ref(checker),
            "pixel_checker": ref(work / "scripts/check_directional_viewer_pixels.py"),
            "frozen_files": sources,
            "scope": "Stage only after actual four-endpoint review and CPU audits/exports. Compact72figures/24triplets and five-state viewer. Actual native viewing and browser source-pixel checks precede a final quality report/publication.",
        },
    )
    print("Prepared compact native publication sources; no outputs copied")


def publication_guard():
    plan = read(ROOT / "plan-v1.json")
    source_guard(plan)
    seal = read(ROOT / "publication-source-v1.json")
    assert ref(__file__) == seal["publisher"]
    for path, digest in seal["frozen_files"].items():
        assert ref(path)["sha256"] == digest
    assert ref(seal["browser_checker"]["path"]) == seal["browser_checker"]
    return plan, seal


def completed():
    plan, seal = publication_guard()
    scores = read(ROOT / "scores-v1.json")
    assert not owner_live(scores["owner"])
    assert scores["status"] == "completed-V195-four-endpoint-quality-awaiting-native-viewing"
    assert len(scores["rows"]) == 3288 and scores["counts"] == plan["expected_quality_counts"]
    for name in ["training-audit-v1.json", "quality-audit-v1.json", "exports-v1.json"]:
        assert read(ROOT / name)["status"].startswith("pass-")
    figures = read(ROOT / "figures-v1.json")
    assert figures["native_figures"] == 72 and figures["native_triplets"] == 24
    assert len(figures["images"]) == 72 and len(figures["sheets"]) == 18
    assert all(f["no_resize"] for f in figures["images"])
    exports = read(ROOT / "exports-v1.json")["exports"]
    assert len(exports) == 4
    assert read(ROOT / "directional-breakdown-v2/result-v1.json")["status"].startswith(
        "pass-eight-new"
    )
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
    old = read(REPO / "docs/results/v187-pooled-wave-final-v1.json")
    manifest.update(
        fixture=False,
        method_checkpoints={
            "V187-pooled-wave-EMA": old["checkpoints"]["V187-pooled-wave-EMA"],
            **exports,
        },
        publication_source=ref(ROOT / "publication-source-v1.json"),
    )
    save(IMAGES / "manifest-v1.json", manifest)
    from build_large_dense_native_viewer import build

    build(
        IMAGES / "manifest-v1.json",
        IMAGES / "native-viewer.html",
        REPORT.name,
        method_a=plan["methods"]["whole"]["EMA"],
        method_b=plan["methods"]["directional"]["EMA"],
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
        ]
    ]
    paths += [ROOT / "directional-breakdown-v2/result-v1.json"]
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
            "status": "staged-actual-V195-native-comparisons-awaiting-viewing-and-final-report",
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v1.json"),
            "figures": ref(IMAGES / "manifest-v1.json"),
            "viewer": ref(IMAGES / "native-viewer.html"),
            "copies": copies,
            "checkpoints": exports,
            "viewer_method_checkpoints": manifest["method_checkpoints"],
            "native_figures": 72,
            "native_triplets": 24,
            "table_rows": len(paired["table_rows"]),
            "comparison_methods": paired["methods"],
            "publication_source": ref(ROOT / "publication-source-v1.json"),
            "scope": "Actual trained outputs/audits staged with no pixel resizing. Native viewing,actual browser pixels,interpretation and final report remain pending; this is not a promotion claim.",
        },
    )
    print("Staged72nativefigures/24triplets/five-state viewer; actual viewing remains")


def record_viewing(selected, notes):
    _, _, _, figures, _ = completed()
    assert selected and len(selected) == len(set(selected))
    assert set(selected) <= set(range(18)) and notes.strip()
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
    if seen == set(range(18)):
        save(
            ROOT / "native-viewing-completion-v1.json",
            {
                "status": "actually-viewed72-native-figures-and24triplets-in18-original-detail-sheets",
                "figures": ref(ROOT / "figures-v1.json"),
                "journal": ref(path),
                "indices": list(range(72)),
                "sheets": list(range(18)),
                "no_resize": True,
            },
        )
    print("Recorded", selected, "; viewed", len(seen), "/18 original sheets")


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
