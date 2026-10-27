"""Plot sensor-condition coverage and the bounded exposure preparation check."""

import argparse
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle
from train_directional_bank_trial import read, ref, save


def figures(analysis_path, proof_path, output):
    analysis, proof = read(analysis_path), read(proof_path)
    output.mkdir(parents=True, exist_ok=False)
    with np.load(analysis["sensor_block_arrays"]["path"], allow_pickle=False) as archive:
        values = {key: archive[key] for key in archive.files}
    contexts = read(analysis["contexts"]["path"])
    families = ["commons-photographic", "commons-reviewed-photo", "native"]
    names = ["Ordinary Commons photos", "Reviewed material regions", "Native-camera targets"]
    histograms = []
    for family in families:
        selected = np.asarray([row["family"] == family for row in contexts])
        valid = values["valid"][selected] & values["weak_band"][selected]
        x, y = (
            values["brightness_bin"][selected][valid],
            values["relative_noise_bin"][selected][valid],
        )
        histogram = np.zeros((7, 8), dtype=np.int64)
        np.add.at(histogram, (y, x), 1)
        histograms.append(histogram)
    plt.rcParams.update(
        {"font.family": "DejaVu Sans", "font.size": 10, "svg.hashsalt": "shadow-target-coverage-v1"}
    )
    figure, axes = plt.subplots(1, 3, figsize=(14, 5.6))
    figure.subplots_adjust(left=0.08, right=0.92, bottom=0.29, top=0.81, wspace=0.35)
    cmap = plt.get_cmap("viridis").copy()
    cmap.set_bad("#eeeeee")
    maximum = max(int(h.max()) for h in histograms)
    norm = LogNorm(vmin=1, vmax=max(maximum, 2))
    xlabels = ["<2⁻¹²", "2⁻¹²–2⁻¹⁰", "2⁻¹⁰–2⁻⁸", "2⁻⁸–2⁻⁶", "2⁻⁶–2⁻⁴", "2⁻⁴–2⁻²", "2⁻²–1", "≥1"]
    ylabels = ["<.125", ".125–.25", ".25–.5", ".5–1", "1–2", "2–4", "≥4"]
    cell = analysis["GFX_condition_cells"][0]
    assert all(
        (r["brightness_bin"], r["relative_noise_bin"])
        == (cell["brightness_bin"], cell["relative_noise_bin"])
        for r in analysis["GFX_condition_cells"]
    )
    for axis, histogram, family, name in zip(axes, histograms, families, names, strict=True):
        artist = axis.imshow(
            np.ma.masked_equal(histogram, 0), origin="lower", aspect="auto", cmap=cmap, norm=norm
        )
        for y in range(7):
            for x in range(8):
                count = histogram[y, x]
                axis.text(
                    x,
                    y,
                    str(count),
                    ha="center",
                    va="center",
                    fontsize=8,
                    color="#333333" if count == 0 or norm(max(count, 1)) > 0.65 else "white",
                )
        axis.add_patch(
            Rectangle(
                (cell["brightness_bin"] - 0.5, cell["relative_noise_bin"] - 0.5),
                1,
                1,
                fill=False,
                edgecolor="#e3342f",
                linewidth=2.5,
            )
        )
        axis.set_xticks(range(8), xlabels, rotation=55, ha="right", fontsize=9)
        axis.set_yticks(range(7), ylabels, fontsize=9)
        slots = sum(row["family"] == family for row in contexts)
        axis.set_title(f"{name}\n{slots} retained context slots", fontsize=11, pad=9)
        axis.set_xlabel("Mean measured-green target intensity")
    axes[0].set_ylabel("Pre-ADC pixel-noise RMS / green mean")
    figure.colorbar(
        artist,
        ax=list(axes),
        fraction=0.025,
        pad=0.025,
        label="Weak-target blocks (log color scale)",
    )
    figure.suptitle(
        "Shadow brightness and noise conditioning change the coverage picture", fontsize=14, y=0.98
    )
    figure.text(
        0.08,
        0.89,
        "Red cell: both existing GFX mesh regions/profiles. Counts use target relative luma-band RMS <5%, absolute RMS ≥1e−5.",
        fontsize=10,
    )
    figure.text(
        0.03,
        0.065,
        "First18 discarded-check steps; no corpus prevalence or true real-camera SNR claim. Near-boundary proxy membership is uncertain.",
        fontsize=9,
    )
    figure.text(
        0.03,
        0.035,
        "Native references retain source noise/optics. ADC-only and positive-noise targets share the first relative-noise bin.",
        fontsize=9,
    )
    paths = []
    for suffix in ["png", "svg"]:
        path = output / ("shadow-conditioning." + suffix)
        figure.savefig(path, dpi=160, facecolor="white")
        paths.append(path)
    plt.close(figure)

    figure, axis = plt.subplots(figsize=(7.6, 6.0))
    figure.subplots_adjust(left=0.13, right=0.96, top=0.86, bottom=0.22)
    axis.axhspan(2**-10, 2**-5, color="#d9f0e6", alpha=0.8)
    upper = 1.0
    for row, color, marker in zip(
        proof["device_proofs"], ["#2166ac", "#d95f02"], ["o", "x"], strict=True
    ):
        cases = [case for case in row["cases"] if case["kind"] == "reviewed"]
        x = [case["control_dense_green_mean"] for case in cases]
        y = [case["shadow_dense_green_mean"] for case in cases]
        upper = max(upper, max(x) * 1.2, max(y) * 1.2)
        axis.scatter(
            x,
            y,
            c=color,
            marker=marker,
            s=40,
            alpha=0.8,
            label=row["device"].upper() + " /20 regions",
            zorder=3,
        )
    axis.plot(
        [1e-4, upper], [1e-4, upper], "--", color="#888888", linewidth=1, label="Equal intensity"
    )
    axis.set(
        xscale="log",
        yscale="log",
        xlim=(1e-4, upper),
        ylim=(1e-4, upper),
        xlabel="Control mean camera-green intensity",
        ylabel="Shadow-policy mean camera-green intensity",
    )
    axis.grid(alpha=0.2)
    axis.legend(loc="upper left", frameon=False)
    axis.set_title("Scalar exposure moves reviewed texture into shadows", fontsize=13, pad=15)
    figure.text(
        0.13, 0.12, "Requested mean2⁻¹⁰–2⁻⁵ (shaded); applied gain is bounded to1/64–1.", fontsize=9
    )
    figure.text(
        0.13,
        0.085,
        "Native256/B16 + partialB12; source geometry is shared and camera/noise settings stay fixed.",
        fontsize=9,
    )
    figure.text(
        0.13,
        0.05,
        "Data-only CPU/CUDA proof, no model/encoder/optimizer call. Learned quality remains unmeasured.",
        fontsize=9,
    )
    for suffix in ["png", "svg"]:
        path = output / ("reviewed-shadow-exposure." + suffix)
        figure.savefig(path, dpi=160, facecolor="white")
        paths.append(path)
    plt.close(figure)
    for path in paths:
        if path.suffix == ".svg":
            path.write_text(re.sub(r"[ \t]+(?=\n)", "", path.read_text()))
    save(
        output / "plot-v1.json",
        {
            "analysis": ref(analysis_path),
            "proof": ref(proof_path),
            "plot_source": ref(__file__),
            "images": [ref(path) for path in paths],
            "model_quality_claim": False,
        },
    )
    return paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis", type=Path)
    parser.add_argument("proof", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(
        [
            str(path)
            for path in figures(
                args.analysis.resolve(), args.proof.resolve(), args.output.resolve()
            )
        ]
    )
