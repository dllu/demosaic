"""Plot absolute residual power from diagnose_flat_scales.py without rerunning models."""

import argparse
import json
import math
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from demosaic.safety import writable_path


def short(label):
    match = re.search(r"v(\d+):step-(\d+)", label)
    return f"V{match[1]} / step{match[2]}" if match else label


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    output = writable_path(args.result.parent)
    data = json.loads(args.result.read_text())
    levels = sorted({row["scene_level"] for row in data["rows"]})
    figure, axes = plt.subplots(1, len(levels), figsize=(11, 3.5), sharey=True, squeeze=False)
    for axis, level in zip(axes[0], levels):
        for row in data["rows"]:
            if row["scene_level"] != level:
                continue
            axis.plot(
                [s["block"] for s in row["scales"]],
                [math.sqrt(s["centered_error_power"]) * 65535 for s in row["scales"]],
                marker="o",
                markersize=3,
                label=short(row["model"]),
            )
        axis.set_xscale("log", base=2)
        axis.set_yscale("log")
        axis.set_xlabel("Averaging block side (sensor pixels)")
        axis.set_title(f"Scene-linear sRGB level {level:g}")
        axis.grid(alpha=0.25, which="both")
    axes[0, 0].set_ylabel("RMS error (equivalent 16-bit codes)")
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncol=len(labels), fontsize=7)
    figure.suptitle(
        "Exact flat targets / ISO6400 prior / 512-pixel input, 64-pixel trim", fontsize=10
    )
    figure.tight_layout(rect=[0, 0.11, 1, 0.94])
    figure.savefig(output / "residual-scales.png", dpi=160)
    figure.savefig(output / "residual-scales.pdf")
    plt.close(figure)
    lines = [
        "# Residual spatial-scale diagnostic",
        "",
        "Exact synthetic flat targets, one fixed noise realization per level; no photographic quality score.",
        "The input uses GFX metadata and disclosed ISO6400 priors, not a measured camera profile.",
        "Error is centered separately per RGB channel before projecting onto constant blocks.",
        "Values below are unquantized camera-RGB RMS errors expressed in equivalent 16-bit codes.",
        "Absolute coarse error matters: a larger retained-power fraction can simply mean fine noise was removed.",
        "",
        "![Absolute projected residuals](residual-scales.png)",
        "",
        "| Model / scene level | Total sigma | 8-pixel mean | 32-pixel mean | 64-pixel mean |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for row in data["rows"]:
        scales = {s["block"]: math.sqrt(s["centered_error_power"]) * 65535 for s in row["scales"]}
        lines.append(
            f"| {short(row['model'])} / {row['scene_level']} | {row['camera_centered_sigma'] * 65535:.3f} | {scales[8]:.3f} | {scales[32]:.3f} | {scales[64]:.3f} |"
        )
    lines += [
        "",
        "Native 160×160 noisy/denoised/exact-GT triplets, shared +2 EV display; open at 100%.",
        "",
    ]
    for crop in data["native_crops"]:
        lines += [crop["caption"], "", f"![Native flat comparison]({crop['image']})", ""]
    lines += [
        "[Full numerical/source/weight receipt](result.json). [PDF figure](residual-scales.pdf).",
        "",
    ]
    (output / "report.md").write_text("\n".join(lines))
    (output / "source" / Path(__file__).name).write_bytes(Path(__file__).read_bytes())


if __name__ == "__main__":
    main()
