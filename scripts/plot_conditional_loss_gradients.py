"""Plot fixed fine-band gradient projections from the saved CPU loss replay."""

import argparse
import sys
from pathlib import Path

import numpy as np
from train_directional_bank_trial import guard, read, ref, save


def main(root, version=2):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    root = root.resolve()
    plan = read(root / "plan-v1.json")
    guard(plan)
    analysis = read(root / "analysis-v1.json")
    assert analysis["plan"] == ref(root / "plan-v1.json") and not analysis["Torch_imported"]
    output = Path(plan["work"]) / f"artifacts/plots-v{version}"
    output.mkdir(exist_ok=False)
    cases = [
        ("bark", "Bark / ≥20%"),
        ("raccoon-fur", "Fur / 0–2%"),
        ("pixls-5002-fine", "Grass estimate / 2–5%"),
        ("pixls-1951-field", "Wood estimate / 2–5%"),
    ]
    plt.rcParams.update({"font.size": 9, "svg.hashsalt": "conditional-loss-gradients-v1"})
    figure, axes = plt.subplots(2, 4, figsize=(12.6, 7.3))
    rows = []
    for row, method in enumerate(("V120", "V117")):
        for column, (case, title) in enumerate(cases):
            selected = next(
                s
                for s in analysis["summaries"]
                if s["method"] == method
                and s["case_id"] == case
                and s["scope"] == f"band-contrast-{plan['selected_contrast_bins'][case]}"
                and s["term"] == "total"
            )
            rows.append(selected)
            ax = axes[row, column]
            x = np.arange(2)
            for offset, key, label, color in (
                (-0.18, "control", "Per-view control", "#3374ac"),
                (0.18, "mixture", ".75 per-view + .25 mean", "#dd8430"),
            ):
                values = [
                    selected["projections"][key][field] * 1e8
                    for field in ("heldout_bias_projection", "noise_covariance_projection")
                ]
                ax.bar(x + offset, values, width=0.34, label=label, color=color)
            before = selected["projections"]["control"]
            after = selected["projections"]["mixture"]
            bias = 100 * (after["heldout_bias_projection"] / before["heldout_bias_projection"] - 1)
            noise = 100 * (
                after["noise_covariance_projection"] / before["noise_covariance_projection"] - 1
            )
            ax.set_title(f"{method} · {title}\n{selected['reference_blocks']} reference blocks")
            ax.text(
                0.5,
                0.97,
                f"bias {bias:+.2f}% · covariance {noise:+.2f}%",
                ha="center",
                va="top",
                transform=ax.transAxes,
                fontsize=8,
            )
            ax.set_xticks(x, ["Held-out\nerror", "Noise\ncovariance"])
            ax.axhline(0, color="#777777", linewidth=0.6)
            maximum = max(
                selected["projections"][objective][field] * 1e8
                for objective in ("control", "mixture")
                for field in ("heldout_bias_projection", "noise_covariance_projection")
            )
            ax.set_ylim(bottom=0, top=maximum * 1.18)
            ax.grid(axis="y", alpha=0.18)
            ax.set_axisbelow(True)
            if column == 0:
                ax.set_ylabel("Gradient/error projection (×10⁻⁸)")
            ax.spines[["top", "right"]].set_visible(False)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="upper center", bbox_to_anchor=(0.5, 0.945), ncol=2)
    figure.suptitle(
        "Mean-loss gradients: a modest shift in the detail/noise balance", y=0.995, fontsize=14
    )
    figure.text(
        0.5,
        0.952,
        "Existing outputs · 8 independent draws per CFA · 4 CFAs · fine band 1/8–1/3 cycles/pixel",
        ha="center",
        fontsize=10,
    )
    figure.text(
        0.5,
        0.025,
        "Output-space loss diagnostics only. No neural parameter update or new inference; finite-draw uncertainty remains.",
        ha="center",
        fontsize=9,
    )
    figure.subplots_adjust(top=0.82, bottom=0.12, hspace=0.65, wspace=0.32)
    png, svg = output / "gradient-projections.png", output / "gradient-projections.svg"
    figure.savefig(png, dpi=180)
    figure.savefig(svg, metadata={"Date": None})
    plt.close(figure)
    assert "torch" not in sys.modules
    save(
        root / f"plot-v{version}.json",
        {
            "plan": ref(root / "plan-v1.json"),
            "analysis": ref(root / "analysis-v1.json"),
            "plot_source": ref(__file__),
            "PNG": ref(png),
            "SVG": ref(svg),
            "selected_rows": rows,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "Torch_imported": False,
        },
    )
    print(ref(png))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--version", type=int, default=2)
    args = parser.parse_args()
    main(args.root, args.version)
