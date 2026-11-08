"""Publish completed V196 geometry and V197 engineering admission, never quality."""

import re
import shutil
import time
from pathlib import Path

from directional_trial_protocol import REPO, read, ref, save
from phase_admission_protocol import owner_live


def publish():
    root = REPO / ".cache/quality-20261108/V196-innovation-selection-v1"
    admission = REPO / ".cache/quality-20261108/V197-innovation-wave-admission-v1"
    result = read(root / "result-v1.json")
    audit = read(root / "audit-v1.json")
    plan = read(root / "plan-v2.json")
    probe = read(admission / "admission-result-v1.json")
    inspection = read(admission / "CPU-inspection-v1.json")
    assert audit["result"] == ref(root / "result-v1.json") and audit["status"].startswith("pass")
    assert not owner_live(probe["owner"]) and inspection["admission"] == ref(
        admission / "admission-result-v1.json"
    )
    targets = {}
    for stem, base, names in [
        (
            "v196-innovation-selection-v1",
            root,
            [
                "plan-v1.json",
                "plan-v2.json",
                "result-v1.json",
                "audit-v1.json",
                "input-completion-v1.json",
                "input-selections-v1.jsonl.gz",
                "input-selections-v2.jsonl.gz",
                "selection-failure-v1.json",
                "selection-v1.log",
                "selection-v2.log",
                "plot-v1.json",
            ],
        ),
        (
            "v197-innovation-wave-admission-v1",
            admission,
            [
                "plan-v1.json",
                "probe-launch-v1.json",
                "admission-result-v1.json",
                "CPU-inspection-v1.json",
                "probe-v1.log",
                "CPU-inspection-v1.log",
            ],
        ),
    ]:
        dest = REPO / "docs/results" / stem
        dest.mkdir()
        copies = {}
        for name in names:
            source = base / name
            target = dest / name
            shutil.copyfile(source, target)
            assert ref(source)["sha256"] == ref(target)["sha256"]
            copies[name] = {"original": ref(source), "public": ref(target)}
        targets[stem] = copies
    image_dir = REPO / "docs/images/v196-innovation-selection-v1"
    image_dir.mkdir()
    figures = {}
    for ext in ["png", "svg", "pdf"]:
        source = root / f"selection-proximity-v1.{ext}"
        target = image_dir / source.name
        shutil.copyfile(source, target)
        assert ref(source)["sha256"] == ref(target)["sha256"]
        figures[ext] = ref(target)
    # Check all eight visible table rows against both source neighborhoods.
    report = REPO / "docs/innovation-frequency-selection.md"
    lines = [s for s in report.read_text().splitlines() if re.match(r"\| 230[29] \|", s)]
    assert len(lines) == 8
    names = {
        "RAW current": "RAW_current",
        "Innovation current": "innovation_current",
        "RAW wide": "RAW_wide",
        "Innovation wide": "innovation_wide",
    }
    for line in lines:
        seed, name, a, b, d = [part.strip() for part in line.strip("|").split("|")]
        rows = [
            r
            for r in result["rows"]
            if r["id"].split("seed")[1][:10].endswith(seed) and r["view"] == names[name]
        ]
        rows.sort(key=lambda r: r["radius_native_bins"])
        expected = [100 * r["regions"][0]["principal_proximity"] for r in rows] + [
            rows[0]["fundamentals"][0]["minimum_distance_native_bins"]
        ]
        assert [a, b, d] == [f"{v:.6f}" for v in expected]
    plot = read(root / "plot-v1.json")
    assert len(plot["points"]) == 48
    for point in plot["points"]:
        row = next(
            r
            for r in result["rows"]
            if r["id"] == point["id"]
            and r["view"] == point["view"]
            and r["radius_native_bins"] == point["radius"]
        )
        value = (
            row["principal_proximity"]
            if point["region"] is None
            else row["regions"][point["region"]]["principal_proximity"]
        )
        assert point["proximity_percent"] == 100 * value
    documents = [
        report,
        REPO / "docs/innovation-wave-readout.md",
        REPO / "diary/2026-11-08-14-02-17-innovation-selection-geometry.md",
    ]
    links = []
    # Index files are created below; defer resolving those exact known paths.
    deferred = {
        "v196-innovation-selection-completed-v1.json",
        "v197-innovation-wave-admission-completed-v1.json",
    }
    for doc in documents:
        for value in re.findall(r"\]\(([^)]+)\)", doc.read_text()):
            path = value.split("#")[0]
            if path and "://" not in path:
                target = (doc.parent / path).resolve()
                assert target.exists() or target.name in deferred, (doc, path)
                links.append(str(target))
    common = {
        "created_unix_UTC": time.time(),
        "publisher": ref(__file__),
        "new_source_noise_draws": 0,
        "new_quality_inference": 0,
    }
    save(
        REPO / "docs/results/v196-innovation-selection-completed-v1.json",
        {
            **common,
            "status": "completed-audited-144input-selectors-two-template-geometry-diagnostic-not-quality",
            "report": ref(report),
            "plan": ref(root / "plan-v2.json"),
            "result": ref(root / "result-v1.json"),
            "audit": ref(root / "audit-v1.json"),
            "copies": targets["v196-innovation-selection-v1"],
            "figures": figures,
            "inspected_original_detail_plot": True,
            "plot_points": 48,
            "report_numeric_cells": 24,
            "input_contexts": 36,
            "input_only_selectors": 144,
            "independent_QR_coordinates": 4481024,
            "all103_previous_neural_hashes_unchanged": plan["neural103"],
            "scope": plan["scope"],
        },
    )
    save(
        REPO / "docs/results/v197-innovation-wave-admission-completed-v1.json",
        {
            **common,
            "status": "completed-engineering-admission-two-fresh-heads-not-trained-quality",
            "report": ref(REPO / "docs/innovation-wave-readout.md"),
            "copies": targets["v197-innovation-wave-admission-v1"],
            "source": ref(REPO / "src/demosaic/late_innovation_wave.py"),
            "CPU_contracts": ref(REPO / ".cache/v197-innovation-wave-CPU-tests-v1.log"),
            "GPU_admission": ref(admission / "admission-result-v1.json"),
            "CPU_inspection": ref(admission / "CPU-inspection-v1.json"),
            "probe_owner_terminal": probe["owner"],
            "anchor_parities": 14,
            "nonzero_CPU_GPU_head_checks": 12,
            "probe_updates": 4,
            "actual_restorations": 2,
            "strict_CPU_loads": 8,
            "frozen_tensor_comparisons": 1544,
            "scope": read(admission / "plan-v1.json")["scope"],
        },
    )
    for target in links:
        assert Path(target).exists(), target
    print(
        "PASS24reportcells/48plotpoints/publicbytecopies/links;V196diagnosticandV197admissionpublished"
    )


if __name__ == "__main__":
    publish()
