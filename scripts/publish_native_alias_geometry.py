"""Publish closed V190 geometry with audited coordinates and actual plot viewing."""

import argparse
import json
import math
import os
import re
import sys
import time
from pathlib import Path

import numpy as np
from phase_admission_protocol import owner_live, read, ref
from report_native_alias_geometry import REPO, ROOT, guard, lines, save

STEM = "v190-native-alias-geometry-v1"
REPORT = REPO / "docs/native-wave-alias-geometry.md"
INDEX = REPO / "docs/results" / (STEM + ".json")
PROOF = REPO / "docs/results/v190-native-alias-geometry-publication-verification-v1.json"
IMAGES = REPO / "docs/images" / STEM
EVIDENCE = REPO / "docs/results" / STEM


def context():
    plan, result = read(ROOT / "plan-v1.json"), read(ROOT / "result-v1.json")
    guard(plan)
    seal = read(ROOT / "publication-source-v1.json")
    assert seal["publisher"] == ref(__file__)
    assert seal["plan"] == result["plan"] == ref(ROOT / "plan-v1.json")
    audit = read(ROOT / "verification-v1.json")
    assert audit["result"] == ref(ROOT / "result-v1.json") and audit["status"].startswith("pass-")
    assert not owner_live(result["owner"]) and not owner_live(audit["owner"])
    assert result["status"] == "completed-closed-input-native-template-alias-geometry-not-quality"
    return plan, result, lines(result["template_journal"]["path"])


def cdf_series(rows):
    series = []
    for present in [True, False]:
        for method in ["V187_actual8", "V189_actual8"]:
            group = [
                r
                for r in rows
                if r["present"] == present
                and r["method"] == method
                and r["neighborhood"] == "localwidth"
            ]
            assert len(group) == 256
            for field in ["principal_carrier_proximity", "four_lift_carrier_proximity"]:
                series.append(
                    {
                        "present": present,
                        "method": method,
                        "field": field,
                        "x_percent": sorted(100 * r[field] for r in group),
                        "y_fraction": ((np.arange(256) + 1) / 256).tolist(),
                    }
                )
    return series


def render():
    _plan, result, rows = context()
    directory = ROOT / "figures-v1"
    directory.mkdir(exist_ok=False)
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    series = cdf_series(rows)
    absent_max = max(max(s["x_percent"]) for s in series if not s["present"])
    absent_limit = max(10, 10 * math.ceil(absent_max / 10))
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    ):
        fig, axes = plt.subplots(1, 2, figsize=(11.4, 4.6), layout="constrained")
        for present, ax in zip([True, False], axes, strict=True):
            for item in series:
                if item["present"] != present:
                    continue
                version = item["method"].split("_")[0]
                principal = item["field"].startswith("principal")
                ax.plot(
                    item["x_percent"],
                    item["y_fraction"],
                    color="#2563a6" if version == "V187" else "#bd5425",
                    linestyle="-" if principal else "--",
                    linewidth=1.7,
                    label=version + (" principal" if principal else " four lifts"),
                )
            ax.set(
                title="Present mesh (256 records)"
                if present
                else "Absent mesh: hypothetical template (256 records)",
                xlabel="Native RGB template power near selected carriers (%)",
                ylabel="Fraction of records at or below value",
                ylim=(0, 1.01),
                xlim=(0, 100 if present else absent_limit),
            )
            ax.grid(alpha=0.18)
            ax.legend(loc="lower right", frameon=False, fontsize=9)
        fig.suptitle(
            "Native carrier geometry after frozen input-only selection\nSquare radius 4 native FFT bins; descriptive proximity, not restoration capacity",
            fontsize=12,
        )
        files = []
        for suffix in ["png", "svg", "pdf"]:
            path = directory / ("native-carrier-proximity." + suffix)
            fig.savefig(path, dpi=160)
            files.append(ref(path))
        plt.close(fig)
    # Explicit limits must not hide outlying data.
    assert absent_max <= absent_limit
    save(
        ROOT / "plots-v1.json",
        {
            "status": "rendered-audited-native-geometry-CDF-no-restored-images",
            "result": ref(ROOT / "result-v1.json"),
            "source": ref(__file__),
            "figure_files": files,
            "series": series,
            "CDF_points": 2048,
            "native_crop_resizing": False,
            "absent_max_percent": absent_max,
            "absent_axis_limit_percent": absent_limit,
        },
    )
    print("Rendered1scientificfigure/3formats/2048CDFpoints;no restored images")


def viewing(notes):
    context()
    plots = read(ROOT / "plots-v1.json")
    assert notes.strip()
    for binding in plots["figure_files"]:
        assert ref(binding["path"]) == binding
    save(
        ROOT / "plot-viewing-v1.json",
        {
            "status": "actually-viewed-original-detail-native-alias-CDF-figure",
            "created_unix_UTC": time.time(),
            "plots": ref(ROOT / "plots-v1.json"),
            "notes": notes,
        },
    )


def copy_link(source, target):
    assert not target.exists()
    os.link(source, target)
    assert ref(source)["sha256"] == ref(target)["sha256"]


def summary_table(result):
    text = "| Input | Selector | Neighborhood | Principal carrier | Four lifts | Added aliases |\n|---|---|---|---:|---:|---:|\n"
    for s in result["summary"]:
        values = [
            100 * s[f]["mean"]
            for f in [
                "principal_carrier_proximity",
                "four_lift_carrier_proximity",
                "added_alias_proximity",
            ]
        ]
        text += f"| {'Present' if s['present'] else 'Absent (hypothetical)'} | {s['method'].split('_')[0]} | {'±1 bin' if s['neighborhood'] == 'near1' else '±4 bins'} | {values[0]:.6f}% | {values[1]:.6f}% | {values[2]:.6f} pp |\n"
    return text


def publish(notes):
    plan, result, _rows = context()
    assert notes.is_file() and len(notes.read_text()) > 300
    for path in [REPORT, INDEX, EVIDENCE, IMAGES]:
        assert not path.exists()
    assert read(ROOT / "plot-viewing-v1.json")["plots"] == ref(ROOT / "plots-v1.json")
    EVIDENCE.mkdir()
    IMAGES.mkdir()
    files = {}
    for name in [
        "plan-v1.json",
        "launch-v1.json",
        "input-bindings-v1.jsonl.gz",
        "input-completion-v1.json",
        "native-template-v1.jsonl.gz",
        "result-v1.json",
        "run-v1.log",
        "verification-v1.json",
        "audit-v1.log",
        "audit-progress-v1.jsonl",
        "import-preflight-v1.log",
        "plots-v1.json",
        "plot-viewing-v1.json",
        "publication-source-v1.json",
    ]:
        source, target = ROOT / name, EVIDENCE / name
        copy_link(source, target)
        files[name] = {"original": ref(source), "public": ref(target)}
    for label, source in [
        ("CPU-tests-v1.log", REPO / ".cache/v190-native-alias-CPU-tests-v1.log"),
        ("CPU-tests-v2.log", Path(plan["CPU_tests"]["path"])),
        ("human-notes-v1.md", notes),
        (
            "pre-main-import-failure-inspection-v1.json",
            Path(plan["preserved_pre_main_import_failure"]["path"]),
        ),
    ]:
        target = EVIDENCE / label
        copy_link(source, target)
        files[label] = {"original": ref(source), "public": ref(target)}
    figure_files = []
    for binding in read(ROOT / "plots-v1.json")["figure_files"]:
        source = Path(binding["path"])
        assert ref(source) == binding
        target = IMAGES / source.name
        copy_link(source, target)
        figure_files.append({"original": binding, "public": ref(target)})
    text = "# Native wave alias geometry\n\n" + notes.read_text().strip() + "\n\n"
    text += summary_table(result)
    text += f"\nEach entry is the mean over 256 case records. Present/absent records share targets; there are {result['unique_template_values']} distinct native template values across 512 records, not 512 independent examples. All frequency distances refer to native FFT bins in 512×512 contexts. Both neighborhoods are descriptive conventions, not measured synthesis support or recovery bounds.\n\n"
    text += f"![Native carrier proximity distributions](images/{STEM}/native-carrier-proximity.png)\n\n[SVG](images/{STEM}/native-carrier-proximity.svg) · [PDF](images/{STEM}/native-carrier-proximity.pdf). All 2,048 CDF points are checked against the audited rows.\n\n"
    text += "The native template is clipped camera-RGB present minus clipped empty GT, in FP64 after the original FP32 clipping. Each color removes its own Hann-weighted affine plane before an orthonormal native FFT; powers are summed across RGB. Principal centers use signed packed-bin coordinates lifted to the native FFT. Their conjugates and ±1/±4 neighborhoods are formed on the native torus before unioning the four possible half-cycle aliases. This avoids wrapping a neighborhood at the packed Nyquist boundary. Strict principal support excludes ±1/4-cycle boundaries; those boundaries are reported separately. No real ISO100/AHD/JPEG reference enters this diagnostic.\n\n"
    text += "All 550 saved input selections and 1,650 RAW/variance/CFA fingerprints close before target reads. Actual V189 selections match the previously closed V188 spaced counterfactual; actual V187 selections match its V187 records. No new bins, fitted coefficients, network, checkpoint or restored image is produced. The independent audit uses QR rather than normal-equation detrending, sparse native coordinate sets rather than the production masks, and Decimal summary means. Twenty CPU tests include four-CFA alias ambiguity, exact synthetic carriers, Nyquist boundaries and malformed inputs. An initial import-only failure omitted a frozen helper; its terminal attempt is preserved. The corrected package passes isolated imports and completes scientific work once.\n\n"
    text += "This is a geometry diagnostic, not an improved-model performance report. The [completed V189 comparison](spaced-pooled-wave-comparison.md) retains all 60 native figures / 12 triplets, both protected GFX scenes and the [eighteen-state viewer](images/v189-spaced-pooled-v1/native-viewer.html). V187 remains the preferred wave model; V120 Small remains the general recommendation. Originals/captures/JPEGs/siblings and unavailable dataz were untouched. All 102 neural sources and previous evidence remain preserved.\n\n"
    text += "[Exact evidence](results/v190-native-alias-geometry-v1.json) · [Publication verification](results/v190-native-alias-geometry-publication-verification-v1.json).\n"
    REPORT.write_text(text.rstrip() + "\n")
    save(
        INDEX,
        {
            "status": "completed-audited-native-alias-geometry-no-model-quality-change",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "verification": ref(ROOT / "verification-v1.json"),
            "report": ref(REPORT),
            "files": files,
            "figures": figure_files,
            "summary": result["summary"],
            "publication_source": ref(ROOT / "publication-source-v1.json"),
            "scope": plan["scope"],
        },
    )
    print("PublishedV190native-geometry/2048rows/1figure/3formats;no quality promotion")


def verify(diary):
    plan, result, rows = context()
    final, plots = read(INDEX), read(ROOT / "plots-v1.json")
    assert not PROOF.exists()
    assert ref(final["report"]["path"]) == final["report"]
    assert plots["series"] == cdf_series(rows) and plots["CDF_points"] == 2048
    # Separate rank calculation checks both axes of every plotted coordinate.
    coordinates = 0
    for s in plots["series"]:
        group = [
            r[s["field"]]
            for r in rows
            if r["present"] == s["present"]
            and r["method"] == s["method"]
            and r["neighborhood"] == "localwidth"
        ]
        for n, value in enumerate(sorted(group)):
            assert s["x_percent"][n] == value * 100 and s["y_fraction"][n] == (n + 1) / len(group)
            coordinates += 2
    for pair in list(final["files"].values()) + final["figures"]:
        for b in pair.values():
            assert ref(b["path"]) == b
        original, public = [Path(pair[k]["path"]) for k in ["original", "public"]]
        assert (
            original.stat().st_ino == public.stat().st_ino
            and original.stat().st_dev == public.stat().st_dev
        )
    assert final["summary"] == result["summary"] and summary_table(result) in REPORT.read_text()
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
            "docs/phase-evidence-matching.md",
            "docs/pooled-phase-wave-readout.md",
            "docs/native-wave-alias-geometry.md",
        ]
    ] + [diary]
    links = 0
    for path in documents:
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            assert resolved == PROOF or resolved.is_file(), (path, target)
            links += 1
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    save(
        PROOF,
        {
            "status": "pass-native-geometry-audit-plotted-coordinates-linked-bytes-102sources-and-current-documents",
            "publication": ref(INDEX),
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "scientific_audit": ref(ROOT / "verification-v1.json"),
            "plotted_CDF_points": 2048,
            "independent_coordinate_checks": coordinates,
            "linked_evidence_files": len(final["files"]),
            "figure_files": 3,
            "unchanged_neural_sources": len(plan["neural102_hashes"]),
            "documents": {str(p): ref(p) for p in documents},
            "document_links": links,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "scope": "Publication integrity for descriptive native-frequency geometry. No model/quality change, recovered-amplitude bound or safety promotion.",
        },
    )
    print(f"PASS2048CDFpoints/{coordinates}coordinatechecks/3figurefiles/102sources/{links}links")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    sub.add_parser("render")
    view = sub.add_parser("record-viewing")
    view.add_argument("--notes", required=True)
    publication = sub.add_parser("publish")
    publication.add_argument("--notes", type=Path, required=True)
    verification = sub.add_parser("verify")
    verification.add_argument("--diary", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "render":
        render()
    elif args.phase == "record-viewing":
        viewing(args.notes)
    elif args.phase == "publish":
        publish(args.notes)
    else:
        verify(args.diary)
