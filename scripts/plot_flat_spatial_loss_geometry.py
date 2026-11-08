"""Plot the audited training-only V182 gradient measurements without inference."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from phase_admission_protocol import read, ref
from probe_flat_spatial_loss_geometry import ROOT, guard, save


def main():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert ref(__file__) == read(ROOT / "plot-source-v2.json")["plotter"]
    audit = read(ROOT / "independent-audit-v2.json")
    assert audit["status"].startswith("pass-V182-")
    assert audit["result"] == ref(ROOT / "result-v1.json")
    result = read(ROOT / "result-v1.json")
    paired = [r for r in result["rows"] if r["pair_target_energies"]]
    out = ROOT / "plot-v2"
    out.mkdir(exist_ok=False)
    fig, axes = plt.subplots(
        1, 2, figsize=(13, 6.5), layout="constrained", gridspec_kw={"width_ratios": [1.35, 1]}
    )
    for offset, label, color, key, group in [
        (-0.20, "Output coordinates", "#64748b", "output_geometry", None),
        (0, "Parameters: Euclidean", "#d97706", "parameter_geometry", "all"),
        (0.20, "Parameters: fixed Adam denominator", "#0f766e", "fixed_Adam_geometry", "all"),
    ]:
        values = [(r[key] if group is None else r[key][group])["cosines"][1][2] for r in paired]
        axes[0].scatter(values, np.arange(12) + offset, label=label, color=color, s=25)
    axes[0].axvline(0, color="#555555", lw=0.8)
    axes[0].set(
        yticks=np.arange(12),
        yticklabels=[
            f"{'V180' if r['method'].startswith('V180') else 'V181'} / {r['domain']} / row{r['step']}"
            for r in paired
        ],
        xlabel="Cosine: added spatial loss vs paired-difference loss",
        title="Output alignment can conceal parameter conflict",
        xlim=(-0.40, 0.15),
    )
    axes[0].invert_yaxis()
    axes[0].set_ylim(14, -0.6)
    axes[0].legend(loc="lower right", fontsize=8)
    for method, color, shift in [
        ("V180-local-phase-raw", "#d97706", -0.12),
        ("V181-flat-spatial-raw", "#0f766e", 0.12),
    ]:
        rows = [r for r in result["rows"] if r["method"] == method]
        axes[1].scatter(
            [r["fixed_Adam_geometry"]["all"]["spatial_to_baseline_norm"] for r in rows],
            np.arange(10) + shift,
            label=method.split("-")[0] + " raw",
            color=color,
            s=28,
        )
    axes[1].axvline(1, color="#555555", lw=0.8)
    axes[1].set(
        xscale="log",
        yticks=np.arange(10),
        yticklabels=[f"{r['domain']} / row{r['step']}" for r in result["rows"][:10]],
        xlabel="Added spatial / original total gradient norm",
        title="Large added pressure on mixed and flat batches",
    )
    axes[1].invert_yaxis()
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.grid(axis="x", alpha=0.2)
        ax.tick_params(labelsize=8)
    fig.suptitle("V182: fixed cached training batches; zero optimizer updates", fontsize=13)
    for extension in ["png", "svg"]:
        fig.savefig(out / f"training-gradient-geometry.{extension}", dpi=160)
    plt.close(fig)
    save(
        ROOT / "plot-result-v2.json",
        {
            "status": "rendered-audited-training-gradient-plot-awaiting-actual-viewing",
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "audit": ref(ROOT / "independent-audit-v2.json"),
            "images": [ref(out / f"training-gradient-geometry.{ext}") for ext in ["png", "svg"]],
            "neural_forwards": 0,
            "optimizer_updates": 0,
            "scope": "Diagnostic plot only. Fixed saved-Adam denominator is not an actual Adam update. No model-quality gain is claimed.",
        },
    )


if __name__ == "__main__":
    main()
