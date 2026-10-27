"""Plot descriptive contrast coverage from retained training targets."""

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from train_directional_bank_trial import read, ref, save

LABELS = {
    "commons-photographic": "Commons photographs",
    "commons-reviewed-photo": "Reviewed material regions",
    "commons-weak-texture": "Procedural weak texture",
    "commons-procedural": "Other procedural shapes",
    "commons-smooth-field": "Smooth-field controls*",
    "native": "Native-camera targets",
    "paired": "Paired-camera references*",
    "bark": "Bark (synthetic GT)",
    "raccoon-fur": "Fur (synthetic GT)",
    "pixls-5002-fine": "Grass (reference estimate)",
    "pixls-1951-field": "Wood (reference estimate)",
}
COLORS = ["#1b9e77", "#66c2a5", "#e6ab02", "#e67e22", "#7b6b9d"]
BINS = ["0–2%", "2–5%", "5–10%", "10–20%", "≥20%"]


def panel(axis, rows, title, *, training):
    positions = np.arange(len(rows))
    left = np.zeros(len(rows))
    fractions = np.asarray(
        [np.asarray(row["counts"]) / max(row["valid_blocks"], 1) for row in rows]
    )
    for index, (label, color) in enumerate(zip(BINS, COLORS, strict=True)):
        widths = fractions[:, index] * 100
        axis.barh(positions, widths, left=left, label=label, color=color, height=0.65)
        for y, width, start in zip(positions, widths, left, strict=True):
            if width >= 11:
                axis.text(
                    start + width / 2,
                    y,
                    f"{width:.1f}",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white" if index in (0, 3, 4) else "#202020",
                )
        left += widths
    descriptions = []
    for row in rows:
        label = LABELS[row["family"] if training else row["id"]]
        detail = f"{row['context_slots']} contexts, " if training else ""
        descriptions.append(f"{label}\n{detail}{row['valid_blocks']:,} eligible blocks")
    axis.set_yticks(positions, descriptions, fontsize=10)
    axis.invert_yaxis()
    axis.set_xlim(0, 100)
    axis.set_xticks(np.arange(0, 101, 20), [f"{value}%" for value in range(0, 101, 20)])
    axis.set_title(title, loc="left", pad=13, fontsize=12, weight="bold")
    axis.set_axisbelow(True)
    axis.grid(axis="x", color="#dddddd", linewidth=0.7)
    axis.spines[["top", "right", "left"]].set_visible(False)
    axis.tick_params(axis="y", length=0)


def plot(analysis_path, output):
    analysis = read(analysis_path)
    output.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "svg.hashsalt": "training-target-contrast-v1",
        }
    )
    figure, axes = plt.subplots(2, 1, figsize=(11.5, 9.2), gridspec_kw={"height_ratios": [7, 4]})
    figure.subplots_adjust(left=0.30, right=0.98, top=0.855, bottom=0.14, hspace=0.42)
    panel(
        axes[0],
        analysis["family_summaries"],
        "Retained training-check prefix: 288 clean target slots",
        training=True,
    )
    panel(
        axes[1],
        analysis["diagnostic_references"],
        "Fixed independent-noise diagnostic references",
        training=False,
    )
    axes[1].set_xlabel("Share of eligible blocks by relative fine-band RMS contrast")
    figure.suptitle(
        "Faint-band target support is present; counts alone do not establish useful texture",
        fontsize=14,
        y=0.975,
    )
    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(
        handles, labels, loc="upper center", bbox_to_anchor=(0.63, 0.925), ncol=5, frameon=False
    )
    figure.text(
        0.02,
        0.065,
        "Native160 center • DCT16 radial band 1/8–1/3 cycles/pixel • target luma .02–.9 • band RMS ≥ 1e−5",
        fontsize=9,
    )
    figure.text(
        0.02,
        0.041,
        "*Smooth gradients can contribute band energy. Paired/native references retain source noise and optics.",
        fontsize=9,
    )
    figure.text(
        0.02,
        0.017,
        "First18 discarded check steps, unequal domain counts; no corpus prevalence, model-quality or noiseless-texture claim.",
        fontsize=9,
    )
    png, svg = output / "training-target-contrast.png", output / "training-target-contrast.svg"
    figure.savefig(png, dpi=160, facecolor="white")
    figure.savefig(svg, facecolor="white")
    plt.close(figure)
    # Normalize formatting before hashing these new generated SVG bytes.
    svg.write_text(re.sub(r"[ \t]+(?=\n)", "", svg.read_text()))
    save(
        output / "plot-v1.json",
        {
            "analysis": ref(analysis_path),
            "plot_source": ref(__file__),
            "PNG": ref(png),
            "SVG": ref(svg),
            "model_quality_claim": False,
        },
    )
    return png


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(plot(args.analysis.resolve(), args.output.resolve()))
