"""Publish closed diagnostic evidence and verify plotted data and current guides."""

import math
import os
import re
from pathlib import Path

import numpy as np
from phase_admission_protocol import owner_live, read, ref
from report_selection_diversity import ROOT, lines, save

REPO = Path("/home/dllu/proj/demosaic")
INDEX = REPO / "docs/results/v188-selection-diversity-v1.json"
PROOF = REPO / "docs/results/v188-selection-diversity-publication-verification-v1.json"
REPORT = REPO / "docs/spectral-selection-diversity.md"
IMAGES = REPO / "docs/images/v188-selection-diversity-v1"
EVIDENCE = REPO / "docs/results/v188-selection-diversity-v1"
METHODS = ["V185_actual8slots", "V187_actual8", "spaced8", "sector8"]


def plot_data_check(result, figures):
    data = read(figures["plot_data"]["path"])
    rows = lines(result["template_journal"]["path"])
    inputs = lines(result["input_journal"]["path"])
    controls = lines(result["control_journal"]["path"])
    assert ref(figures["plot_data"]["path"]) == figures["plot_data"]
    cdf = bars = overlap = quiet = 0
    for method in METHODS:
        group = [
            r
            for r in rows
            if r["method"] == method and r["present"] and r["neighborhood"] == "localwidth"
        ]
        order = np.argsort([r["template_fraction"] for r in group], kind="stable")
        expected = [100 * group[i]["template_fraction"] for i in order]
        a = data["present_template_CDF"][method]
        assert a["x_percent"] == expected and a["cases"] == [group[i]["id"] for i in order]
        np.testing.assert_array_equal(a["CDF"], np.arange(1, 257) / 256)
        cdf += len(expected)
        for field, a in data["minimum_sector_means"].items():
            assert a["methods"] == METHODS
            at = METHODS.index(method)
            expected = 100 * math.fsum(r[field] for r in group) / len(group)
            assert a["percent"][at] == expected
            bars += 1
        group = [r for r in inputs if r["kind"] == "mesh" and r["present"]]
        a = data["present_footprint_overlap"][method]
        assert a["cases"] == [r["id"] for r in group] and a["percent"] == [
            100 * r["stats"][method]["geometry_localwidth"]["overlap_fraction_of_unclipped_sum"]
            for r in group
        ]
        overlap += len(group)
        group = [r for r in controls if r["kind"] == "mixed-quiet" and r["method"] == method]
        a = data["quiet_global_local_power"][method]
        assert (
            a["cases"] == [r["id"] for r in group]
            and a["global"] == [r["global_max_min_phase_power"] for r in group]
            and a["local"] == [r["local_max_min_phase_power"] for r in group]
        )
        quiet += len(group)
    assert (cdf, bars, overlap, quiet) == (1024, 8, 1024, 128)
    return {
        "CDF_points": cdf,
        "sector_bars": bars,
        "overlap_samples": overlap,
        "paired_quiet_points": quiet,
    }


def main():
    seal = read(ROOT / "publication-source-v1.json")
    assert seal["publisher"] == ref(__file__)
    for b in seal["helpers"]:
        assert ref(b["path"]) == b
    p = read(ROOT / "plan-v1.json")
    r = read(ROOT / "result-v1.json")
    v = read(ROOT / "verification-v1.json")
    f = read(ROOT / "figures-v1.json")
    assert v["result"] == f["result"] == ref(ROOT / "result-v1.json") and v["status"].startswith(
        "pass-closed-inputs"
    )
    assert not owner_live(r["owner"]) and not owner_live(
        read(ROOT / "audit-launch-v1.json")["owner"]
    )
    assert (
        r["owner"] == read(ROOT / "launch-v1.json")["owner"]
        and not (ROOT / "failure-v1.json").exists()
    )
    for b in p["sources"]:
        assert ref(b["path"]) == {k: b[k] for k in ["path", "sha256"]}
    for name, digest in p["dependency"]["neural101_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    assert not r["FP64_bridge_mismatches"]
    counts = plot_data_check(r, f)
    viewing = read(ROOT / "actual-figure-viewing-v1.json")
    assert viewing["figures"] == ref(ROOT / "figures-v1.json") and len(viewing["viewed_PNGs"]) == 2
    assert {b["path"] for b in viewing["viewed_PNGs"]} == {
        b["path"] for b in f["files"] if b["path"].endswith(".png")
    }
    for b in viewing["viewed_PNGs"]:
        assert ref(b["path"]) == b
    # Preserve the never-executed prepared renderer and its original seal bytes.
    before = read(ROOT / "render-source-preexecution-v1.json")
    archive = ROOT / "render-work-v1/scripts/render_selection_diversity-preexecution-v1.py"
    assert ref(archive)["sha256"] == before["renderer"]["sha256"]
    assert read(ROOT / "render-source-v1.json")["renderer"] == {
        k: f["renderer"][k] for k in ["path", "sha256"]
    }
    assert all(not q.exists() for q in [INDEX, PROOF, IMAGES, EVIDENCE])
    IMAGES.mkdir()
    EVIDENCE.mkdir()
    images = []
    for b in f["files"]:
        assert ref(b["path"]) == b
        source = Path(b["path"])
        dest = IMAGES / source.name
        os.link(source, dest)
        assert ref(dest)["sha256"] == b["sha256"]
        images.append({"original": b, "public": ref(dest)})
    names = [
        "plan-v1.json",
        "launch-v1.json",
        "owner-v1.json",
        "run-v1.log",
        "input-completion-v1.json",
        "input-selections-v1.jsonl.gz",
        "template-proximity-v1.jsonl.gz",
        "control-ROI-v1.jsonl.gz",
        "result-v1.json",
        "audit-source-v1.json",
        "audit-launch-v1.json",
        "audit-progress-v1.jsonl",
        "audit-v1.log",
        "verification-v1.json",
        "render-source-preexecution-v1.json",
        "render-source-v1.json",
        "render-v1.log",
        "figures-v1.json",
        "plot-data-v1.json",
        "actual-figure-viewing-v1.json",
        "publication-source-v1.json",
    ]
    receipts = {}
    for name in names:
        source = ROOT / name
        dest = EVIDENCE / name
        os.link(source, dest)
        receipts[name] = {"original": ref(source), "public": ref(dest)}
    sources = {}
    for b in (
        p["sources"]
        + read(ROOT / "audit-source-v1.json")["helpers"]
        + [
            read(ROOT / "audit-source-v1.json")["auditor"],
            ref(archive),
            ref(ROOT / "render-work-v1/scripts/render_selection_diversity.py"),
            ref(__file__),
            ref(REPO / "tests/test_spectral_selection_diversity.py"),
        ]
    ):
        source = Path(b["path"])
        sources[str(source)] = dict(ref(source), text=source.read_text())
    capsule = EVIDENCE / "source-capsule-v1.json"
    save(
        capsule,
        {
            "sources": list(sources.values()),
            "preexecution_correction": {
                "original_seal": ref(ROOT / "render-source-preexecution-v1.json"),
                "original_source_archive": ref(archive),
                "executed_renderer": ref(
                    ROOT / "render-work-v1/scripts/render_selection_diversity.py"
                ),
                "scope": "Before first plot execution: fix sorted CDF case IDs and axis range; original prepared source+seal bytes archived; no scientific or plotted-result replay.",
            },
            "CPU_tests": [
                dict(ref(REPO / ".cache" / n), text=(REPO / ".cache" / n).read_text())
                for n in [
                    "v188-diversity-CPU-tests-v1.log",
                    "v188-independent-reference-CPU-tests-v1.log",
                ]
            ],
        },
    )
    report = ref(REPORT)
    save(
        INDEX,
        {
            "status": "completed-input-only-selection-diversity-audited-and-actually-viewed-not-new-model-quality",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "audit": ref(ROOT / "verification-v1.json"),
            "report": report,
            "figures": images,
            "receipts": receipts,
            "sources": ref(capsule),
            "actual_viewing": ref(ROOT / "actual-figure-viewing-v1.json"),
            "plotted_data": counts,
            "previous101_neural_sources_unchanged": True,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "new_RGB_arrays": 0,
            "scope": p["scope"],
        },
    )
    documents = [
        REPO / x
        for x in [
            "README.md",
            "docs/index.md",
            "docs/current-model.md",
            "docs/research.md",
            "docs/experiments.md",
            "docs/pooled-phase-wave-readout.md",
            "docs/spectral-selection-diversity.md",
            "diary/2026-11-08-08-02-47-spectral-selection-diversity.md",
        ]
    ]
    links = 0
    for path in documents:
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            actual = (path.parent / target.split("#")[0]).resolve()
            assert actual == PROOF or actual.is_file(), (path, target)
            links += 1
    final = read(INDEX)
    assert ref(REPORT) == report
    for pair in [*final["receipts"].values(), *final["figures"]]:
        for b in pair.values():
            assert ref(b["path"]) == b
        a, b = [Path(pair[k]["path"]) for k in ["original", "public"]]
        assert (a.stat().st_dev, a.stat().st_ino) == (b.stat().st_dev, b.stat().st_ino)
    save(
        PROOF,
        {
            "status": "pass-closed-diagnostic-sources-native-reference-bindings-plot-data-artifacts-current-guides-and-links",
            "publication": ref(INDEX),
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "exact_linked_receipts": len(receipts),
            "figure_files": len(images),
            "plotted_data": counts,
            "source_capsule": ref(capsule),
            "previous101_neural_sources_unchanged": True,
            "document_links": links,
            "documents": {str(p): ref(p) for p in documents},
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "new_model_quality_claim": False,
        },
    )
    print(
        "PASS diagnostic publication/",
        len(sources),
        "sources/",
        len(receipts),
        "receipts/6figurefiles/",
        counts,
        "/",
        links,
        "documentlinks",
        flush=True,
    )


if __name__ == "__main__":
    main()
