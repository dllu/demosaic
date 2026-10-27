"""Publish the audited retained-output feature diagnostic without neural work."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from train_directional_bank_trial import read, ref, save


def report(root, destination):
    plan = read(root / "plan-v1.json")
    analysis = read(root / "analysis-v1.json")
    audit = read(root / "independent-audit-v1.json")
    assert audit["status"] == "passed-independent-mirrored-FFT-fsum-feature-audit"
    assert audit["analysis"] == ref(root / "analysis-v1.json")
    destination.mkdir(parents=True, exist_ok=False)
    selected, ratios = [], []
    for case in plan["cases"]:
        rows = {
            r["objective"]: r
            for r in analysis["rows"]
            if r["case"] == case["id"] and r["variant"] == "V120"
        }
        base = rows["existing-reconstruction"]
        ratio = []
        for label in ("existing-reconstruction", "DINO-stride4-MSE", "DINO-stride8-MSE"):
            row = rows[label]
            value = (
                row["negative_gradient_target_gain_slope"]
                / base["negative_gradient_target_gain_slope"]
            )
            ratio.append(value)
            selected.append(
                {
                    "case": case["id"],
                    "reference_role": case["reference_role"],
                    "contrast_bin": case["contrast_bin"],
                    "blocks": case["blocks"],
                    "objective": label,
                    "target_band_gain": row["target_band_projection_gain"],
                    "descent_cosine": row["descent_cosine_to_true_band_correction"],
                    "negative_gradient_target_gain_slope": row[
                        "negative_gradient_target_gain_slope"
                    ],
                    "gain_slope_ratio_to_existing": value,
                }
            )
        ratios.append(ratio)
    with (destination / "V120-gradients.csv").open("x") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(selected[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(selected)
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), constrained_layout=True)
    labels = ["Bark\n≥20%", "Fur\n0–2%", "Grass estimate\n2–5%", "Wood estimate\n2–5%"]
    x = np.arange(4)
    colors = ("#62666a", "#1f77b4", "#d98222")
    for j, (label, color) in enumerate(
        zip(("Existing loss", "DINO stride4", "DINO stride8"), colors, strict=True)
    ):
        axes[0].bar(
            x + (j - 1) * 0.24,
            [selected[i * 3 + j]["descent_cosine"] for i in range(4)],
            0.24,
            label=label,
            color=color,
        )
        axes[1].bar(x + (j - 1) * 0.24, np.asarray(ratios)[:, j], 0.24, label=label, color=color)
    axes[0].set_ylabel("Cosine toward correcting the full band error")
    axes[0].set_ylim(0, 0.8)
    axes[1].set_ylabel("Target-gain slope / existing-loss slope")
    axes[1].set_ylim(0, 1.1)
    for ax in axes:
        ax.set_xticks(x, labels)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    axes[0].legend(fontsize=8, loc="upper left")
    fig.suptitle(
        "V120 output-gradient diagnosis · native DCT16 annulus 1/8–1/3 cycles/pixel\nUnit objective weights; finite selected support, not a trained quality result",
        fontsize=10,
    )
    fig.savefig(destination / "feature-gradient-diagnostic.png", dpi=160)
    fig.savefig(destination / "feature-gradient-diagnostic.svg")
    svg = destination / "feature-gradient-diagnostic.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    plt.close(fig)
    payload = {
        "status": "audited-feature-gradient-diagnostic-not-trained-quality",
        "plan": ref(root / "plan-v1.json"),
        "analysis": ref(root / "analysis-v1.json"),
        "audit": ref(root / "independent-audit-v1.json"),
        "backbone": plan["backbone"],
        "collection": ref(root / "collection-v1.json"),
        "new_encoder_forwards_in_probe": 26,
        "new_restoration_forwards": 0,
        "new_noise_observations": 0,
        "new_neural_work_in_report": 0,
        "native_context": [256, 256],
        "analysis_ROI_xywh": [48, 48, 160, 160],
        "CFA": "RGGB",
        "shot": 0.00256,
        "read": 2.62144e-5,
        "ADC_bits": 16,
        "black_level": 0.03,
        "display_exposure": 1,
        "feature_input": "Same WB/matrix to clamped sRGB, ImageNet normalization, no resize",
        "cases": plan["cases"],
        "rows": analysis["rows"],
        "V120_summary": selected,
        "finite_differences": analysis["finite_differences"],
        "scope": plan["scope"],
        "report_source": ref(__file__),
    }
    save(destination / "result.json", payload)
    print({"destination": str(destination), "summary_rows": len(selected)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    report(args.root.resolve(), args.destination.resolve())
