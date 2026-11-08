"""Standalone plots of fixed spectral-allocation diagnostics, never image quality."""

import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from phase_admission_protocol import read, ref
from report_selection_diversity import ROOT, lines, save

METHODS = ["V185_actual8slots", "V187_actual8", "spaced8", "sector8"]
LABELS = ["V185 phase selection", "V187 pooled selection", "Wider separation", "Four-sector quota"]
COLORS = ["#777777", "#2573b5", "#25835c", "#d78321"]


def main():
    seal = read(ROOT / "render-source-v1.json")
    assert seal["renderer"] == ref(__file__)
    result = read(ROOT / "result-v1.json")
    proof = read(ROOT / "verification-v1.json")
    assert proof["result"] == ref(ROOT / "result-v1.json") and proof["status"].startswith(
        "pass-closed-inputs"
    )
    for b in seal["helpers"]:
        assert ref(b["path"]) == b
    assert not (ROOT / "figures-v1.json").exists()
    inputs = lines(result["input_journal"]["path"])
    rows = lines(result["template_journal"]["path"])
    controls = lines(result["control_journal"]["path"])
    out = ROOT / "figures-v1"
    out.mkdir()
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "svg.hashsalt": "v188-selection-diversity-v1",
        }
    )
    data = {
        "present_template_CDF": {},
        "minimum_sector_means": {},
        "present_footprint_overlap": {},
        "quiet_global_local_power": {},
    }
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), layout="constrained")
    for method, label, color in zip(METHODS, LABELS, COLORS, strict=True):
        group = [
            r
            for r in rows
            if r["method"] == method and r["present"] and r["neighborhood"] == "localwidth"
        ]
        assert len(group) == 256
        order = np.argsort([r["template_fraction"] for r in group], kind="stable")
        values = np.asarray([100 * group[i]["template_fraction"] for i in order])
        cdf = np.arange(1, 257) / 256
        axes[0].step(values, cdf, label=label, color=color, where="post", linewidth=1.6)
        data["present_template_CDF"][method] = {
            "x_percent": values.tolist(),
            "CDF": cdf.tolist(),
            "cases": [group[i]["id"] for i in order],
        }
    axes[0].set(
        xlabel="Clean template power near selected bins (%)",
        ylabel="Fraction of 256 present observations",
        xlim=(0, 100),
        ylim=(0, 1.01),
        title="Total spectral proximity (±4 packed FFT bins)",
    )
    axes[0].set_xscale("symlog", linthresh=0.5)
    axes[0].set_xticks(
        [0, 0.5, 1, 5, 10, 50, 100], labels=["0", "0.5", "1", "5", "10", "50", "100"]
    )
    axes[0].legend(loc="lower right", fontsize=9)
    x = np.arange(4)
    width = 0.34
    for j, (field, label) in enumerate(
        [
            ("minimum_substantial_sector_fraction_0", "0° sector partition"),
            ("minimum_substantial_sector_fraction_22p5", "22.5° rotated partition"),
        ]
    ):
        values = []
        for method in METHODS:
            group = [
                r
                for r in rows
                if r["method"] == method and r["present"] and r["neighborhood"] == "localwidth"
            ]
            values.append(100 * math.fsum(r[field] for r in group) / len(group))
        axes[1].bar(
            x + (j - 0.5) * width, values, width, label=label, color=["#315b81", "#a6c0d6"][j]
        )
        for at, value in zip(x + (j - 0.5) * width, values, strict=True):
            axes[1].text(at, value + 0.16, f"{value:.2f}", ha="center", fontsize=9)
        data["minimum_sector_means"][field] = {"methods": METHODS, "percent": values}
    axes[1].set_xticks(x, labels=["V185", "V187", "Wider\nseparation", "Sector\nquota"])
    axes[1].set(
        ylabel="Mean minimum within-sector proximity (%)",
        title="Weakly covered spectral sectors",
        ylim=(0, 12.5),
    )
    axes[1].legend(loc="upper left", fontsize=9)
    fig.suptitle(
        "Input-only selection, then hidden-template measurement\nEight slots; spectral proximity is not recovered image amplitude",
        fontsize=13,
    )
    files = []
    for ext in ["png", "svg", "pdf"]:
        path = out / f"template-proximity-v1.{ext}"
        fig.savefig(path, dpi=160)
        files.append(ref(path))
    plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), layout="constrained")
    for i, (method, label, color) in enumerate(zip(METHODS, LABELS, COLORS, strict=True)):
        group = [r for r in inputs if r["kind"] == "mesh" and r["present"]]
        values = np.asarray(
            [
                100 * r["stats"][method]["geometry_localwidth"]["overlap_fraction_of_unclipped_sum"]
                for r in group
            ]
        )
        # Fixed even jitter displays repeated Bayer/noise variants without RNG.
        jitter = (np.arange(len(values)) % 17 - 8) * 0.012
        axes[0].scatter(i + jitter, values, s=9, alpha=0.23, color=color, rasterized=False)
        axes[0].plot([i - 0.24, i + 0.24], [np.median(values)] * 2, color="black", linewidth=2)
        data["present_footprint_overlap"][method] = {
            "cases": [r["id"] for r in group],
            "percent": values.tolist(),
        }
        quiet = [r for r in controls if r["kind"] == "mixed-quiet" and r["method"] == method]
        assert len(quiet) == 32
        gx = [r["global_max_min_phase_power"] for r in quiet]
        ly = [r["local_max_min_phase_power"] for r in quiet]
        axes[1].scatter(
            gx, ly, label=label, color=color, s=24, alpha=0.7, marker=["o", "s", "^", "D"][i]
        )
        data["quiet_global_local_power"][method] = {
            "cases": [r["id"] for r in quiet],
            "global": gx,
            "local": ly,
        }
    axes[0].set_xticks(range(4), labels=["V185", "V187", "Wider\nseparation", "Sector\nquota"])
    axes[0].set(
        ylabel="Overlap of summed conjugate neighborhoods (%)",
        title="Repeated spectral neighborhoods (256 present inputs)",
        ylim=(-2, 100),
    )
    axes[1].set(
        xscale="log",
        yscale="log",
        xlabel="Global selected min-phase power (maximum over slots)",
        ylabel="Same statistic in a 65-packed-pixel quiet window",
        title="Global structure does not imply local quiet detail",
    )
    axes[1].legend(loc="best", fontsize=9)
    fig.suptitle(
        "Spatial redundancy and quiet-ROI controls\nBoth green phases affect selection; these powers are not calibrated confidence",
        fontsize=13,
    )
    for ext in ["png", "svg", "pdf"]:
        path = out / f"neighborhoods-and-quiet-v1.{ext}"
        fig.savefig(path, dpi=160)
        files.append(ref(path))
    plt.close(fig)
    save(ROOT / "plot-data-v1.json", data)
    save(
        ROOT / "figures-v1.json",
        {
            "status": "rendered-standalone-diagnostic-plots-awaiting-actual-viewing",
            "result": ref(ROOT / "result-v1.json"),
            "audit": ref(ROOT / "verification-v1.json"),
            "files": files,
            "plot_data": ref(ROOT / "plot-data-v1.json"),
            "renderer": dict(ref(__file__), text=Path(__file__).read_text()),
            "scope": "Four display methods; exact FP64 bridge retained in result, omitted when duplicating actual V187. 1024CDFpoints,8sectorbars,1024overlap samples,128pairedglobal/localquietpoints. These reused development observations are correlated,not scene replications. No restored image or quality gain.",
        },
    )
    print("Rendered two standalone figures/6files/1024CDFpoints/8bars/1024overlaps/128quietpoints")


if __name__ == "__main__":
    main()
