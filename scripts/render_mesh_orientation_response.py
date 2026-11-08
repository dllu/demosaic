"""Render all audited native directional values with legends outside data axes."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from phase_admission_protocol import read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261108/V194-orientation-response-v1"


def render():
    plan = read(ROOT / "plan-v2.json")
    result = read(ROOT / "result-v1.json")
    audit = read(ROOT / "audit-v1.json")
    assert audit["result"] == ref(ROOT / "result-v1.json") and audit["status"].startswith("pass-")
    images = REPO / "docs/images/v194-orientation-response-v1"
    methods = [r["method"] for r in plan["cases"][0]["methods"]]
    fig, axes = plt.subplots(1, 2, figsize=(11.2, 5.1), layout="constrained")
    points = []
    for ax, item in zip(axes, plan["cases"], strict=True):
        case = item["case"]
        rows = [
            next(r for r in result["rows"] if r["id"] == case["id"] and r["method"] == m)
            for m in methods
        ]
        labels = [
            m.replace("-coherent-pair", "")
            .replace("-pooled-wave", "")
            .replace("-dense-spectrum", "")
            .replace("-large-dense", "")
            for m in methods
        ]
        y = np.arange(len(methods))
        for series, offset, color, marker in [
            ("Region A", -0.16, "#1769aa", "o"),
            ("Region B", 0.16, "#b44b18", "s"),
            ("Whole", 0, "#202020", "|"),
        ]:
            values = [
                100
                * (
                    r["whole_template_gain"]
                    if series == "Whole"
                    else r["sectors"][0 if series == "Region A" else 1]["gain"]
                )
                for r in rows
            ]
            ax.scatter(values, y + offset, label=series, c=color, marker=marker, s=28, zorder=3)
            points += [
                {"id": case["id"], "method": m, "series": series, "response_percent": v}
                for m, v in zip(methods, values, strict=True)
            ]
        ax.set_yticks(y, labels, fontsize=8)
        ax.invert_yaxis()
        ax.axvline(0, c="#777", lw=0.6)
        ax.set_xlabel("Response (% of exact constructed regional template)")
        shares = rows[0]["sectors"]
        ax.set_title(
            f"Mesh{str(case['seed'])[-4:]}: GT energy A {100 * shares[0]['template_energy_fraction']:.2f}% / B {100 * shares[1]['template_energy_fraction']:.2f}%",
            fontsize=10,
        )
        ax.grid(axis="x", alpha=0.2)
    fig.suptitle(
        "Directional response on two fixed native examples · separate linear x scales", fontsize=12
    )
    fig.legend(*axes[0].get_legend_handles_labels(), loc="outside lower center", ncol=3, fontsize=9)
    figures = {}
    for extension in ["png", "svg", "pdf"]:
        path = images / f"orientation-response-v2.{extension}"
        assert not path.exists()
        fig.savefig(path, dpi=150)
        figures[extension] = ref(path)
    plt.close(fig)
    old = read(REPO / "docs/results/v194-orientation-response-v1/plot-v1.json")
    assert old["points"] == points and len(points) == 48
    receipt = {
        "status": "same48auditedpoints-legend-outside-axes-no-model-or-metric-repetition",
        "source": dict(ref(__file__), text=Path(__file__).read_text()),
        "result": ref(ROOT / "result-v1.json"),
        "previous_plot": ref(REPO / "docs/results/v194-orientation-response-v1/plot-v1.json"),
        "figures": figures,
        "points": points,
        "reason": "Actual original-detail inspection found V1 legend occluding the final dominant-direction point. V2 changes presentation only. V1 files and receipt preserved.",
    }
    with (REPO / "docs/results/v194-orientation-response-v1/plot-v2.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print("Rendered same48points inPNG/SVG/PDF with legend outside axes; V1 preserved")


if __name__ == "__main__":
    render()
