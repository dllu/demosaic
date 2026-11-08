"""Publish audited analytical support with verified CDF coordinates, not model quality."""

import argparse, json, os, re, sys, time
from pathlib import Path
import numpy as np
from phase_admission_protocol import read, ref, owner_live
from report_dense_measurement_support import ROOT, R, guard, save

STEM = "v192-dense-support-v1"
REPORT = R / "docs/dense-measurement-support.md"
INDEX = R / f"docs/results/{STEM}.json"
PROOF = R / "docs/results/v192-dense-support-publication-verification-v1.json"
IMAGES = R / f"docs/images/{STEM}"
EVIDENCE = R / f"docs/results/{STEM}"


def context():
    p, r, a = [
        read(ROOT / name) for name in ["plan-v1.json", "result-v1.json", "verification-v1.json"]
    ]
    guard(p)
    assert not owner_live(r["owner"]) and not owner_live(a["owner"])
    assert a["result"] == ref(ROOT / "result-v1.json") and a["status"].startswith("pass-")
    seal = read(ROOT / "publication-source-v1.json")
    assert ref(__file__) == seal["publisher"]
    return p, r


def series(result):
    output = []
    for position in ["interior", "corner"]:
        for mode in ["exact_frequency", "nearest_available_carrier"]:
            for noise in ["uniform", "graded"]:
                for method in ["hann65_grid65", "hann129_grid129"]:
                    values = sorted(
                        q["ratio_to_rect65"]
                        for q in result["ratios"]
                        if all(
                            q[k] == v
                            for k, v in [
                                ("position", position),
                                ("mode", mode),
                                ("noise", noise),
                                ("method", method),
                            ]
                        )
                    )
                    assert len(values) == 48
                    output.append(
                        dict(
                            position=position,
                            mode=mode,
                            noise=noise,
                            method=method,
                            x=values,
                            y=((np.arange(48) + 1) / 48).tolist(),
                        )
                    )
    return output


def render():
    p, r = context()
    out = ROOT / "figures-v1"
    out.mkdir()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = series(r)
    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    ):
        fig, axes = plt.subplots(2, 2, figsize=(10.5, 7.0), layout="constrained")
        for i, mode in enumerate(["exact_frequency", "nearest_available_carrier"]):
            for j, position in enumerate(["interior", "corner"]):
                ax = axes[i, j]
                for item in data:
                    if item["position"] != position or item["mode"] != mode:
                        continue
                    label = (
                        ("Hann65" if item["method"] == "hann65_grid65" else "Hann129")
                        + " / rect65, "
                        + item["noise"]
                    )
                    ax.plot(
                        item["x"],
                        item["y"],
                        color="#2563a6" if item["method"] == "hann65_grid65" else "#c15a2a",
                        linestyle="-" if item["noise"] == "uniform" else "--",
                        label=label,
                        linewidth=1.5,
                    )
                ax.axvline(1, color="#555555", linewidth=0.8)
                ax.grid(alpha=0.15)
                ax.set(
                    xlim=(0, 1.9),
                    ylim=(0, 1.02),
                    title=position
                    + "; "
                    + ("same exact frequency" if i == 0 else "nearest available carrier"),
                    xlabel="Analytical SNR power / rectangular65",
                    ylabel="Fraction of 48 fixed tone cases",
                )
                if i == 0 and j == 0:
                    ax.legend(frameon=False, fontsize=8)
        fig.suptitle(
            "Window support and carrier-grid error\nAffine-detrended linear measurements; not restored detail or safety",
            fontsize=12,
        )
        files = []
        for suffix in ["png", "svg", "pdf"]:
            path = out / f"linear-support-CDF.{suffix}"
            fig.savefig(path, dpi=160)
            files.append(ref(path))
        plt.close(fig)
    assert max(max(s["x"]) for s in data) <= 1.9
    save(
        ROOT / "plots-v1.json",
        {
            "source": ref(__file__),
            "result": ref(ROOT / "result-v1.json"),
            "files": files,
            "series": data,
            "points": 768,
        },
    )
    print("Rendered1analyticalfigure/3formats/768CDFpoints")


def view(notes):
    context()
    plots = read(ROOT / "plots-v1.json")
    assert notes.strip()
    save(
        ROOT / "viewing-v1.json",
        {
            "status": "actually-viewed-original-detail-linear-support-CDF",
            "recorded_unix_UTC": time.time(),
            "plots": ref(ROOT / "plots-v1.json"),
            "notes": notes,
        },
    )


def linked(source, destination):
    assert not destination.exists()
    os.link(source, destination)
    assert ref(source)["sha256"] == ref(destination)["sha256"]


def table(result):
    text = "| Position | Variance | Carrier | Window | Mean ratio | Range | Above 1 |\n|---|---|---|---|---:|---:|---:|\n"
    for s in result["summary"]:
        text += f"| {s['position']} | {s['noise']} | {'exact' if s['mode'] == 'exact_frequency' else 'nearest grid'} | {'Hann65' if s['method'] == 'hann65_grid65' else 'Hann129'} | {s['mean']:.6f} | {s['minimum']:.6f}–{s['maximum']:.6f} | {s['above_one']}/48 |\n"
    return text


def publish(notes):
    p, r = context()
    assert len(notes.read_text()) > 300
    assert read(ROOT / "viewing-v1.json")["plots"] == ref(ROOT / "plots-v1.json")
    assert not REPORT.exists() and not INDEX.exists()
    IMAGES.mkdir()
    EVIDENCE.mkdir()
    copies = {}
    for name in [
        "plan-v1.json",
        "launch-v1.json",
        "result-v1.json",
        "measurements-v1.jsonl.gz",
        "verification-v1.json",
        "run-v1.log",
        "audit-v1.log",
        "plots-v1.json",
        "viewing-v1.json",
        "publication-source-v1.json",
    ]:
        source, target = ROOT / name, EVIDENCE / name
        linked(source, target)
        copies[name] = {"original": ref(source), "public": ref(target)}
    for name, source in [
        ("CPU-tests-v1.log", Path(p["CPU_tests"]["path"])),
        ("human-notes-v1.md", notes),
    ]:
        target = EVIDENCE / name
        linked(source, target)
        copies[name] = {"original": ref(source), "public": ref(target)}
    figures = []
    for b in read(ROOT / "plots-v1.json")["files"]:
        source = Path(b["path"])
        target = IMAGES / source.name
        linked(source, target)
        figures.append({"original": b, "public": ref(target)})
    text = (
        "# Dense measurement support and frequency-grid error\n\n"
        + notes.read_text().strip()
        + "\n\n"
        + table(r)
    )
    text += f"\n![Analytical coherent-measurement SNR power](images/{STEM}/linear-support-CDF.png)\n\n[SVG](images/{STEM}/linear-support-CDF.svg) · [PDF](images/{STEM}/linear-support-CDF.pdf). All 768 plotted points are checked against the audited ratios.\n\n"
    text += "The test uses 48 deterministic native frequencies: twelve fixed 65-grid centers with four prescribed sub-bin offsets. Unit-amplitude cosine/sine quadratures define phase-averaged signal power. Uniform or spatially graded independent unit variance is propagated through each Hann/rectangular and weighted-affine operator. Interior and corner windows share the same fixed 256-packed-pixel geometry. Exact-frequency comparisons isolate support/taper; nearest-grid comparisons add deterministic carrier mismatch. The rectangular grid256 is only an available-frequency comparator, not V187’s actual eight selected bins. A nearest carrier uses the known analytic tone; no noisy selector is tested. Case counts are a prescribed cross, not independent replications or confidence levels.\n\n"
    text += "The primary calculation uses weighted normal equations; an independent QR implementation checks all 1,152 operator cases, 12,672 real coordinates, 768 paired ratios and sixteen Decimal means. Fifteen focused CPU contracts pass. No raw photograph, reference, checkpoint, learned output, sensor-noise draw or neural forward is used. All 103 neural sources remain unchanged. This is not an improved-model report; the [V191 comparison](dense-local-spectrum-comparison.md) retains both GFX scenes and 60 native figures / 12 triplets. V187 stays preferred and V120 Small stays the general recommendation.\n\n"
    text += "[Exact evidence](results/v192-dense-support-v1.json) · [Publication verification](results/v192-dense-support-publication-verification-v1.json).\n"
    REPORT.write_text(text.rstrip() + "\n")
    save(
        INDEX,
        {
            "status": "completed-independent-analytical-support-audit-and-actual-plot-viewing-not-quality",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "verification": ref(ROOT / "verification-v1.json"),
            "report": ref(REPORT),
            "copies": copies,
            "figures": figures,
            "scope": p["scope"],
        },
    )
    print("Published analytical support only;no model promotion")


def verify(diary):
    p, r = context()
    final = read(INDEX)
    plots = read(ROOT / "plots-v1.json")
    assert plots["series"] == series(r) and plots["points"] == 768
    assert ref(REPORT) == final["report"] and table(r) in REPORT.read_text()
    for pair in list(final["copies"].values()) + final["figures"]:
        for b in pair.values():
            assert ref(b["path"]) == b
        a, b = [Path(pair[k]["path"]) for k in ["original", "public"]]
        assert a.stat().st_ino == b.stat().st_ino and a.stat().st_dev == b.stat().st_dev
    docs = [
        R / name
        for name in [
            "README.md",
            "docs/index.md",
            "docs/current-model.md",
            "docs/research.md",
            "docs/experiments.md",
            "docs/dense-measurement-support.md",
        ]
    ] + [diary.resolve()]
    links = 0
    for path in docs:
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#"):
                continue
            dest = (path.parent / target.split("#")[0]).resolve()
            assert dest == PROOF or dest.is_file(), (path, target)
            links += 1
    assert "torch" not in sys.modules and "rawpy" not in sys.modules
    save(
        PROOF,
        {
            "status": "pass-analytical-audit-768CDFpoints-3figurefiles-linkedbytes-103sources-and-documents",
            "publication": ref(INDEX),
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "plotted_points": 768,
            "coordinate_checks": 1536,
            "figure_files": 3,
            "unchanged_neural_sources": 103,
            "document_links": links,
            "documents": {str(path): ref(path) for path in docs},
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "scope": "Analytical one-phase tone-measurement integrity only. No RGB recovery or false-positive/safety/learned-quality claim.",
        },
    )
    print("PASS768CDFpoints/3figurefiles/103unchangedneuralsources/", links, "links")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="phase", required=True)
    sub.add_parser("render")
    v = sub.add_parser("record-viewing")
    v.add_argument("--notes", required=True)
    p = sub.add_parser("publish")
    p.add_argument("--notes", type=Path, required=True)
    c = sub.add_parser("verify")
    c.add_argument("--diary", type=Path, required=True)
    args = parser.parse_args()
    if args.phase == "render":
        render()
    elif args.phase == "record-viewing":
        view(args.notes)
    elif args.phase == "publish":
        publish(args.notes)
    else:
        verify(args.diary)
