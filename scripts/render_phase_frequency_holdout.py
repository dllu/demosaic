"""Describe the fixed CFA phase split; no calibrated detector or RGB output."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V177-phase-frequency-holdout-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V177-phase-frequency-holdout-v1")


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(Path(path).absolute()), "sha256": digest}


def stats(values):
    values = np.asarray(values, dtype=float)
    assert np.isfinite(values).all()
    return {
        "count": values.size,
        "mean": float(values.mean()),
        "median": float(np.median(values)),
        "p10": float(np.quantile(values, 0.1)),
        "p90": float(np.quantile(values, 0.9)),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
    }


def main(output):
    result_path = EXTERNAL / "result-v1.json"
    result = read(result_path)
    plan = read(result["plan"]["path"])
    verification = ROOT / "independent-verification-v1.json"
    assert read(verification)["result"] == ref(result_path)
    assert read(verification)["status"].startswith("pass-independent-QR")
    template_path = Path(
        "/mnt/external/demosaic/quality-20261107/V176-template-information-v1/result-v1.json"
    )
    templates = {
        (r["step"], r["pair"]): r["windows"][-1]["known_template_SNR"]
        for r in read(template_path)["rows"]
        if r["phase_group"] == "green"
    }
    points = []
    for row in result["rows"]:
        primary = row["directions"][0]["peaks"][0]
        all_peaks = [p for d in row["directions"] for p in d["peaks"]]
        assert len(all_peaks) == 8
        points.append(
            {
                "step": row["step"],
                "pair": row["pair"],
                "member": row["member"],
                "fine_ladder": row["fine_ladder"],
                "conditional_template_SNR": templates[(row["step"], row["pair"])],
                "primary": primary,
                "maximum_other_phase_power_over8": max(p["other_phase_power"] for p in all_peaks),
                "counts_other_power_at_least": {
                    str(edge): sum(p["other_phase_power"] >= edge for p in all_peaks)
                    for edge in plan["descriptive_other_power_edges"]
                },
            }
        )
    groups = {}
    for member in ["present", "absent"]:
        selected = [p for p in points if p["member"] == member]
        original = [r for r in result["rows"] if r["member"] == member]
        peaks = [p for r in original for d in r["directions"] for p in d["peaks"]]
        assert len(selected) == 614 and len(peaks) == 4912
        edges = {}
        for edge in plan["descriptive_other_power_edges"]:
            passing = [p for p in peaks if p["other_phase_power"] >= edge]
            high_template = [p for p in selected if p["conditional_template_SNR"] >= 5]
            edges[str(edge)] = {
                "primary_cases": sum(p["primary"]["other_phase_power"] >= edge for p in selected),
                "any_of8_cases": sum(
                    p["maximum_other_phase_power_over8"] >= edge for p in selected
                ),
                "all_peaks": len(passing),
                "passing_peaks_clean_other_power_below1": sum(
                    p["clean_other_power"] < 1 for p in passing
                ),
                "passing_peaks_negative_principal_agreement": sum(
                    p["signed_principal_phase_agreement"] < 0 for p in passing
                ),
                "primary_high_conditional_SNR_cases": sum(
                    p["primary"]["other_phase_power"] >= edge for p in high_template
                ),
                "high_conditional_SNR_cases": len(high_template),
            }
        groups[member] = {
            "observations": 614,
            "peaks": 4912,
            "primary_selection_power": stats([p["primary"]["selection_power"] for p in selected]),
            "primary_other_phase_power": stats(
                [p["primary"]["other_phase_power"] for p in selected]
            ),
            "maximum_other_phase_power_over8": stats(
                [p["maximum_other_phase_power_over8"] for p in selected]
            ),
            "other_proxy_over_actual_variance": stats(
                [p["other_proxy_over_actual_variance"] for p in peaks]
            ),
            "descriptive_edges": edges,
        }
    output.mkdir(exist_ok=False)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.5), layout="constrained")
    for member, color, label in [
        ("absent", "#888888", "Absent (614)"),
        ("present", "#227c83", "Present (614)"),
    ]:
        selected = [p for p in points if p["member"] == member]
        axes[0].scatter(
            [p["primary"]["selection_power"] for p in selected],
            [p["primary"]["other_phase_power"] for p in selected],
            s=12,
            alpha=0.45,
            color=color,
            label=label,
            linewidths=0,
        )
    selected = [p for p in points if p["member"] == "present"]
    for fine, label, color in [
        (False, "Legacy (292)", "#888888"),
        (True, "Fine ladder (322)", "#227c83"),
    ]:
        subset = [p for p in selected if p["fine_ladder"] == fine]
        axes[1].scatter(
            [p["conditional_template_SNR"] for p in subset],
            [p["primary"]["other_phase_power"] for p in subset],
            s=12,
            alpha=0.5,
            color=color,
            label=label,
            linewidths=0,
        )
    for axis in axes:
        axis.set(xscale="log", yscale="log", ylabel="Other green phase: nominal Fourier power")
        axis.axhline(16, color="#9b4945", linewidth=1, linestyle="--")
        axis.legend(frameon=False, fontsize=9)
    axes[0].set(
        xlabel="Selection green phase: nominal Fourier power",
        title="First phase's strongest peak, measured in the other",
    )
    axes[1].set(
        xlabel="V176 conditional known-template SNR, native512",
        title="Present members: same input-only selected peak",
    )
    fig.suptitle(
        "Within-image CFA sample split — descriptive power, no calibrated detection threshold",
        fontsize=11,
    )
    for ext in ["png", "svg", "pdf"]:
        p = output / f"phase-frequency-v1.{ext}"
        fig.savefig(p, dpi=150)
        if ext == "svg":
            p.write_text("\n".join(line.rstrip() for line in p.read_text().splitlines()) + "\n")
    plt.close(fig)
    summary = {
        "status": "completed-within-image-CFA-selection-diagnostic-no-restoration",
        "plan": dict(result["plan"], contents=plan),
        "full_result": ref(result_path),
        "independent_verification": dict(ref(verification), contents=read(verification)),
        "V176_template_result": ref(template_path),
        "sources": {"publication": dict(ref(Path(__file__)), text=Path(__file__).read_text())},
        "groups": groups,
        "plot_points": points,
        "counts": {
            k: v for k, v in result.items() if k not in ["rows", "scope", "owner", "plan", "status"]
        },
        "figures": [ref(output / f"phase-frequency-v1.{ext}") for ext in ["png", "svg", "pdf"]],
        "scope": plan["scope"],
        "interpretation": "Primary point=rank1 selected from lower-index green CFA phase only;other-phase measurement never changes that selection. Each row also retains4 peaks in both directions (8 total),whose combined maxima reuse both phases and are not independent tests. Bins1,4,16,64 are descriptive,not calibrated probabilities/gates. Exact clean/template information enters scoring only. The V176 SNR supplies a posthoc diagnostic x axis,not an inference feature or comparable Fourier-power bound. Both phase directions,members,frequencies and related training cases are dependent. Negative principal-band agreement can reflect native aliases,not absence of signal. No image restored or learned-model quality result.",
    }
    with (output / "summary-v1.json").open("x") as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps(groups, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EXTERNAL / "publication-v1")
    main(parser.parse_args().output)
