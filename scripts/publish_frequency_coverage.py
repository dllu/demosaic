"""Render and publish the verified V186 diagnostic without changing any model."""

import argparse
import json
import os
from pathlib import Path

import numpy as np
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V186-frequency-coverage-v1"
STEM = "v186-frequency-coverage-v1"
INDEX = REPO / "docs/results" / f"{STEM}.json"
REPORT = REPO / "docs/frequency-selection-coverage.md"
METHODS = [
    ("actual_high4", "Current: 8 phase-direction slots", "#333333", "o"),
    ("broad4", "Broader band: 8 slots", "#0072b2", "s"),
    ("balanced8", "Separate lower bank: 16 slots", "#d55e00", "^"),
]


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write("\n")


def ready():
    result = read(ROOT / "result-v1.json")
    verification = read(ROOT / "verification-v2.json")
    reduction = read(ROOT / "summary-reduction-v2.json")
    assert not owner_live(result["owner"]) and not owner_live(result["original_owner"])
    assert verification["status"].startswith("pass-retained-prefix") and verification[
        "result"
    ] == ref(ROOT / "result-v1.json")
    assert verification["summary_reduction"] == ref(
        ROOT / "summary-reduction-v2.json"
    ) and reduction["original_result"] == ref(ROOT / "result-v1.json")
    seal = read(ROOT / "publication-source-v2.json")
    assert ref(__file__) == seal["publisher"]
    for b in seal["helpers"]:
        assert ref(b["path"]) == b
    return result, verification, reduction


def render():
    result, _, _ = ready()
    os.environ["MPLCONFIGDIR"] = str(REPO / ".cache/v186-matplotlib")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = ROOT / "figures-v2"
    out.mkdir()
    present = [r for r in result["rows"] if r["present"]]
    mean = [
        np.mean([r[k] for r in present]) * 100
        for k in [
            "below_lower_octave_power_fraction",
            "lower_octave_power_fraction",
            "high_band_power_fraction",
        ]
    ]
    mean.append(100 - sum(mean))
    labels = ["Below 1/32", "1/32 to <1/16", "1/16 to 1/3", "Above 1/3"]
    colors = ["#bdbdbd", "#d55e00", "#0072b2", "#cc79a7"]
    figure, axes = plt.subplots(1, 2, figsize=(12.8, 4.6), gridspec_kw={"width_ratios": [1, 1.5]})
    figure.subplots_adjust(bottom=0.25, wspace=0.34, top=0.86)
    left = 0
    for value, label, color in zip(mean, labels, colors, strict=True):
        axes[0].barh([0], value, left=left, color=color, label=label)
        if value > 4:
            axes[0].text(
                left + value / 2,
                0.55 if value < 15 else 0,
                f"{value:.2f}%",
                ha="center",
                va="center",
                color="black" if value < 15 else "white",
                fontsize=10,
            )
        left += value
    axes[0].set(
        xlim=(0, 100),
        ylim=(-1, 1),
        yticks=[],
        xlabel="Mean clean green-CFA template power (%)",
        title="A. Most power is already in the existing band",
    )
    axes[0].legend(loc="upper left", bbox_to_anchor=(0, -0.14), ncol=2, fontsize=9, frameon=False)
    points = []
    for method, label, color, marker in METHODS:
        values = np.sort([r[method + "_localwidth_template_fraction"] * 100 for r in present])
        cdf = np.arange(1, len(values) + 1) / len(values)
        axes[1].step(values, cdf, where="post", color=color, label=label)
        points.append({"method": method, "fraction_percent": values.tolist(), "CDF": cdf.tolist()})
    axes[1].set(
        xlim=(0, 100),
        ylim=(0, 1.01),
        xlabel="Clean power near selected bins (%)",
        ylabel="Fraction of present cases",
        title="B. Selection misses most weak-template power",
    )
    axes[1].grid(alpha=0.2)
    axes[1].legend(loc="lower right", fontsize=9)
    figure.suptitle("Descriptive frequency coverage — no new RGB restoration", fontsize=13)
    figure.text(
        0.01,
        0.02,
        "256 correlated present observations; FFT neighborhoods have radius ceil(packed size / 65). Fractions are not recovery bounds.",
        fontsize=9,
    )
    files = []
    for suffix in ["png", "svg", "pdf"]:
        p = out / f"frequency-coverage-v1.{suffix}"
        figure.savefig(p, dpi=140)
        files.append(ref(p))
    plt.close(figure)
    control = read(result["control_measurements"]["path"])["rows"]
    figure, ax = plt.subplots(figsize=(11.6, 5.4))
    figure.subplots_adjust(left=0.10, right=0.70, bottom=0.22, top=0.86)
    quiet_points = []
    for method, label, color, marker in METHODS:
        rows = [r for r in control if r["kind"] == "mixed-quiet" and r["method"] == method]
        x = [max(v["other_phase_power"] for v in r["measurements"]) for r in rows]
        y = [max(v["ROI_center_local_other_power"] for v in r["measurements"]) for r in rows]
        ax.scatter(x, y, color=color, marker=marker, s=35, alpha=0.65, label=label)
        quiet_points.append(
            {
                "method": method,
                "ids": [r["id"] for r in rows],
                "global_max_other_power": x,
                "ROI_center_max_other_power": y,
            }
        )
    ax.set(
        xscale="log",
        yscale="log",
        xlabel="Global maximum descriptive other-phase power",
        ylabel="Quiet ROI center maximum local power",
        title="Nearby structure gives strong global peaks in all 32 quiet contexts",
    )
    ax.grid(alpha=0.2)
    ax.legend(fontsize=9, loc="upper left", bbox_to_anchor=(1.02, 1.0))
    figure.text(
        0.02,
        0.04,
        "65-packed-pixel local windows fit inside each fixed 160 × 160 quiet ROI.\nBoth phase directions and overlapping statistics are reused; no power threshold is calibrated.",
        fontsize=9,
    )
    for suffix in ["png", "svg", "pdf"]:
        p = out / f"quiet-global-local-v1.{suffix}"
        figure.savefig(p, dpi=140)
        files.append(ref(p))
    plt.close(figure)
    previous = read(ROOT / "figures-v1.json")
    assert points == previous["coverage_CDF_points"]
    assert quiet_points == previous["quiet_points"]
    assert dict(zip(labels, mean, strict=True)) == previous["band_mean_power_percent"]
    save(
        ROOT / "figures-v2.json",
        {
            "status": "rendered-scientific-diagnostic-awaiting-actual-viewing",
            "files": files,
            "coverage_CDF_points": points,
            "band_mean_power_percent": dict(zip(labels, mean, strict=True)),
            "quiet_points": quiet_points,
            "result": ref(ROOT / "result-v1.json"),
            "verification": ref(ROOT / "verification-v2.json"),
            "prior_layout": ref(ROOT / "figures-v1.json"),
            "identical_plot_data_as_v1": True,
            "renderer": dict(ref(__file__), text=Path(__file__).read_text()),
            "new_neural_forwards": 0,
            "new_RGB_restorations": 0,
        },
    )
    print("Rendered 2 diagnostic plots with all CDF/scatter points, PNG/SVG/PDF; no model output")


def publish(notes):
    result, _verification, reduction = ready()
    figures = read(ROOT / "figures-v2.json")
    if not notes.strip():
        raise ValueError("Actual plot viewing notes required")
    assert not INDEX.exists() and not REPORT.exists()
    images = REPO / "docs/images" / STEM
    images.mkdir()
    evidence = REPO / "docs/results" / STEM
    evidence.mkdir()
    names = [
        "plan-v1.json",
        "launch-v1.json",
        "run-v1.log",
        "failure-v1.json",
        "input-completion-v1.json",
        "input-selections-v1.jsonl.gz",
        "postselection-template-v1.jsonl.gz",
        "control-resume-plan-v1.json",
        "control-resume-launch-v1.json",
        "control-resume-v1.log",
        "control-ROI-journal-v1.jsonl.gz",
        "control-ROI-measurements-v1.json",
        "result-v1.json",
        "summary-reduction-v2.json",
        "audit-source-v1.json",
        "verification-v1.log",
        "audit-source-v2.json",
        "verification-v2.log",
        "verification-v2.json",
        "figures-v1.json",
        "publication-source-v1.json",
        "figures-v2.json",
        "publication-source-v2.json",
    ]
    copies = {}
    for name in names:
        src = ROOT / name
        dst = evidence / name
        os.link(src, dst)
        copies[name] = {"original": ref(src), "public": ref(dst)}
    for b in figures["files"]:
        assert ref(b["path"]) == b
        src = Path(b["path"])
        os.link(src, images / src.name)
    text = """# Frequency selection misses weak crossed-wire measurements

V186 finds that broadening the current frequency band alone is unlikely to remove the main limitation. About **90.08% of clean green-CFA template power is already in the existing band**, but bins selected from noisy input lie near only **21.25% on average and 1.18% at the median**. This is a read-only diagnostic, not an improved denoiser or a recoverability bound. [V185](spatial-context-wave-comparison.md) remains the latest trained result, with its native fine-fence, sky, foliage and quiet-field comparisons unchanged.

![Template frequency coverage](images/v186-frequency-coverage-v1/frequency-coverage-v1.png)

The left panel averages principal packed-CFA spectral power. The right retains all 256 present observations. Noise and Bayer variants reuse 64 procedural scenes; they are not independent scene replications. The square Fourier neighborhoods have radius ceil(256/65)=4 bins, chosen from the existing local-window width. Windowed measurements and nonlinear contextual mixing can produce frequencies outside these neighborhoods, so the fractions are descriptive proximity measures, not a ceiling on model response.

## Matched and enlarged selections

| Input-only selection | Phase-direction slots | Mean template power near bins | Median |
| --- | ---: | ---: | ---: |
"""
    group = next(g for g in reduction["template_summary_by_presence"] if g["present"])
    for method, label in [
        ("actual_high4", "Existing 1/16–1/3 band"),
        ("broad4", "Broadened 1/32–1/3 band"),
        ("balanced8", "Existing bank plus separate 1/32–<1/16 bank"),
    ]:
        stat = group[method + "_localwidth_template_fraction"]
        text += f"| {label} | {16 if method == 'balanced8' else 8} | {100 * stat['mean']:.3f}% | {100 * stat['median']:.3f}% |\n"
    text += """
With a narrower ±1-bin neighborhood, mean proximity is 17.34%, 18.35% and 19.94%, respectively. Broadening at the same slot count gives only a small gain. Adding a separate lower-frequency bank helps more, but doubles the slots and increases chance alignment in absent inputs: mean hypothetical-template proximity rises from 1.70% to 5.84% for the wider neighborhood. Those absent templates are diagnostic construction data, not actual absent-scene signal.

Fifty of the 128 nominal line-family fundamentals have periods longer than 16 native pixels. Their first harmonics fall below the old cutoff, but narrow wires carry substantial power in higher harmonics: the omitted 1/32–<1/16 octave contains only 9.57% of mean clean CFA-template power. About 0.28% lies below 1/32; principal CFA aliases remain unresolved. The recipe count alone therefore overstates what a simple lower cutoff could fix.

Both existing and counterfactual selections use four peaks per green direction, selecting from that direction's green samples only and measuring the other green at those fixed bins. The added bank uses four extra peaks per direction. The FP64 reference reproduces all actual V185 high-band selections in all 550 contexts. No target, pair difference or model response enters a new selection. The complete input journal closes before clean arrays and saved V185 response rows are interpreted.

## Quiet-region warning

![Global versus local measurements in quiet contexts](images/v186-frequency-coverage-v1/quiet-global-local-v1.png)

Every quiet context contains real nearby structure. Global descriptive power can therefore be large while the fixed quiet ROI is uniform. The median maximum other-phase power is **212.95 globally versus 2.36 at the quiet ROI center** for the current selection. Broader-band selection gives **452.11 versus 2.25**; the separate lower bank gives **452.11 versus 2.70**. A 65-packed-pixel window fits inside each 160×160 quiet ROI. No fixed threshold from these selected, overlapping and correlated statistics establishes confidence or safe restoration.

For constructed present/absent mesh inputs, the current selection has maximum other-phase power at least 4 in 98/256 present and 29/256 absent cases. A separate lower bank changes those counts to 122/256 and 56/256. At 16 the counts are 36/0 and 38/0. These inherited descriptive bins are not deployment cutoffs; considering more candidates changes their distributions. All 32 quiet contexts exceed 16 globally even under the existing selection.

Eight real ROI measurements are included below for input interpretation only. The two cab noise profiles reuse the same capture, and these ROIs are not independent scene replications. No ISO100/AHD/JPEG reference is read or scored.

| Cached input / ROI | Current global maximum other-phase power | Local ROI-center maximum |
| --- | ---: | ---: |
"""
    for r in read(result["control_measurements"]["path"])["rows"]:
        if r["kind"] == "real" and r["method"] == "actual_high4":
            text += f"| {r['id']} / {r['region']} | {max(v['other_phase_power'] for v in r['measurements']):.3f} | {max(v['ROI_center_local_other_power'] for v in r['measurements']):.3f} |\n"
    text += """
## Implication for the next model

The evidence supports testing selection that pools the two green phases and nearby frequency bins to gather weaker structure before choosing a sparse wave basis. That is a hypothesis, not a measured improvement. Pooling changes selection bias; an other-phase statistic would no longer be an independent selection holdout. Spatial support, all quiet/absent/flat controls and both protected GFX scenes remain necessary. This diagnostic does not prove that loss weighting is harmless or that missing detail is recoverable from every input.

## Reproducibility and preserved failures

The scope is 550 cached contexts: 256 present and 256 matched absent mesh observations, 32 mixed quiet contexts and six protected real contexts. The 512 constructed template measurements use exact present-minus-empty clean camera-RGB samples mosaiced at their original CFA positions. This target information enters only after input-only selection. Existing V185 raw/EMA response scalars are reused, with no restored RGB produced.

Twenty-six focused CPU checks cover selection, four CFA layouts, conjugate suppression, tie behavior, scaling, target/other-phase isolation, numerical group labels, orthonormal QR covariance and explicit linear rows. The independent audit verifies 1,650 input fingerprints and 4,400 actual selected-frequency records. On the fixed first 12 cases it checks 288 independently ranked bins, 192 explicit complex DFT/variance rows and 132 template-fraction scalars. All 3,200 local control powers are checked by explicit patch QR; 130 means are checked with Decimal arithmetic. Maximum errors are 4.40e-16 for complex DFT coefficients, 2.21e-20 for variance, 2.78e-17 for template fractions and 2.11e-12 for local powers.

The original run completed and closed all 550 selections and all 512 template rows, then stopped on the cab metadata's two-ROI form. The control successor retained those byte-exact prefixes without replay and journals each control result; its 40 regions produce 160 region-method records. Original unpersisted control calculations could not be resumed. The first audit also caught a summary-format bug: a numeric grouping key had been replaced by its own statistics object. Corrected reduction preserves group labels; every original row and the primary presence-only summary remain unchanged. Both failed sources/logs and all successor bindings are preserved. Canonical code handles both forms and the corrected reduction.

All 100 neural source files remain unchanged. There are zero model/checkpoint loads, neural/parent/DINO/RAW-decoder calls, new RGB restorations, source/noise renders or real reference reads. Originals and unavailable `/mnt/dataz` were not accessed. Both GFX capture families, JPEGs and siblings remain held out from training. This repeatedly used development suite establishes no blind generalization or calibrated noisy-sky safety.

[Exact evidence, sources and viewing notes](results/v186-frequency-coverage-v1.json). [Latest trained native-pixel viewer](images/v185-spatial-context-v1/native-viewer.html).
"""
    with REPORT.open("x") as f:
        f.write(text)
    save(
        INDEX,
        {
            "status": "completed-verified-actually-viewed-frequency-diagnostic-not-new-model-quality",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "corrected_summary": ref(ROOT / "summary-reduction-v2.json"),
            "verification": ref(ROOT / "verification-v2.json"),
            "report": ref(REPORT),
            "copies": copies,
            "figures": [ref(images / Path(b["path"]).name) for b in figures["files"]],
            "viewing_notes": notes,
            "publisher": dict(ref(__file__), text=Path(__file__).read_text()),
            "latest_model_publication": ref(
                REPO / "docs/results/v185-spatial-context-final-v1.json"
            ),
            "new_neural_forwards": 0,
            "new_RGB_restorations": 0,
            "scope": result["scope"],
        },
    )
    print("Published verified V186 diagnostic; latest trained model remains V185")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["render", "publish"])
    p.add_argument("--notes", default="")
    a = p.parse_args()
    render() if a.phase == "render" else publish(a.notes)
