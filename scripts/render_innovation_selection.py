"""Plot audited two-example measurement geometry, never restoration quality."""

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from innovation_frequency_selection import VIEWS
from report_innovation_selection import ROOT, checked_plan, read, ref, save


def render():
    plan = checked_plan()
    assert ref(__file__) == plan["renderer"]
    result = read(ROOT / "result-v1.json")
    audit = read(ROOT / "audit-v1.json")
    assert audit["result"] == ref(ROOT / "result-v1.json") and audit["status"].startswith("pass")
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.5), layout="constrained")
    points = []
    for row, case_id in enumerate(plan["geometry"]):
        seed = case_id.split("seed")[1][:10]
        for col, region in enumerate([None, 0, 1]):
            ax = axes[row, col]
            for radius, offset, color, marker in [
                (1, -0.11, "#1769aa", "o"),
                (4, 0.11, "#b44b18", "s"),
            ]:
                values = []
                for name in VIEWS:
                    record = next(
                        r
                        for r in result["rows"]
                        if r["id"] == case_id
                        and r["view"] == name
                        and r["radius_native_bins"] == radius
                    )
                    value = 100 * (
                        record["principal_proximity"]
                        if region is None
                        else record["regions"][region]["principal_proximity"]
                    )
                    values.append(value)
                    points.append(
                        {
                            "id": case_id,
                            "view": name,
                            "radius": radius,
                            "region": region,
                            "proximity_percent": value,
                        }
                    )
                ax.scatter(
                    values,
                    np.arange(4) + offset,
                    c=color,
                    marker=marker,
                    label=f"radius {radius} native DFT bins",
                    s=30,
                )
            ax.set_yticks(
                np.arange(4),
                ["RAW current", "Innovation current", "RAW wider band", "Innovation wider band"]
                if col == 0
                else [],
            )
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            ax.set_xlabel("GT spectral power near selected carriers (%)", fontsize=8)
            ax.set_title(
                f"Mesh{seed[-4:]} · "
                + ("whole template" if region is None else f"region {'AB'[region]}"),
                fontsize=10,
            )
            ax.grid(axis="x", alpha=0.2)
    fig.suptitle(
        "Input-only selection geometry on two reused development examples\nProximity is not recovered amplitude or a quality/safety result",
        fontsize=12,
    )
    fig.legend(*axes[0, 0].get_legend_handles_labels(), loc="outside lower center", ncol=2)
    outputs = {}
    for extension in ["png", "svg", "pdf"]:
        path = ROOT / f"selection-proximity-v1.{extension}"
        assert not path.exists()
        fig.savefig(path, dpi=160)
        outputs[extension] = ref(path)
    plt.close(fig)
    save(
        ROOT / "plot-v1.json",
        {
            "status": "rendered48auditedgeometrypoints-no-restoration-quality",
            "renderer": ref(__file__),
            "result": ref(ROOT / "result-v1.json"),
            "audit": ref(ROOT / "audit-v1.json"),
            "figures": outputs,
            "points": points,
        },
    )
    print("Rendered48auditedpoints PNG/SVG/PDF")


if __name__ == "__main__":
    render()
