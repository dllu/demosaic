"""Publish a descriptive, GT-conditional diagnostic; never render restored RGB."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V176-template-information-v1"
EXTERNAL = Path("/mnt/external/demosaic/quality-20261107/V176-template-information-v1")


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(Path(path).absolute()), "sha256": digest}


def stats(values):
    values = np.asarray(values, dtype=np.float64)
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
    plan = read(ROOT / "plan-v1.json")
    result = read(result_path)
    verification_path = ROOT / "independent-verification-v1.json"
    verification = read(verification_path)
    assert result["plan"] == ref(ROOT / "plan-v1.json")
    assert verification["result"] == ref(result_path)
    assert verification["status"] == "pass-independent-QR-and-all-result-variance-identities"
    for binding in plan["sources"]:
        assert ref(binding["path"])["sha256"] == binding["sha256"]
        assert Path(binding["path"]).read_text() == binding["text"]
    rows = result["rows"]
    assert len(rows) == 1228
    journal = EXTERNAL / "rows-v1.jsonl"
    assert [json.loads(line) for line in journal.read_text().splitlines()] == rows
    assert len({(r["step"], r["pair"]) for r in rows}) == 614
    groups = {}
    points = []
    for phase_group in plan["phase_groups"]:
        selected = [r for r in rows if r["phase_group"] == phase_group]
        assert len(selected) == 614
        widths = {}
        for index, width in enumerate(plan["native_contexts"]):
            assert all(r["windows"][index]["native_context"] == width for r in selected)
            snr = np.array([r["windows"][index]["known_template_SNR"] for r in selected])
            widths[str(width)] = {
                "known_template_SNR": stats(snr),
                "below_1": int((snr < 1).sum()),
                "at_least_3": int((snr >= 3).sum()),
                "at_least_5": int((snr >= 5).sum()),
            }
        full = [r["windows"][-1] for r in selected]
        amplitudes = {
            name: stats([w["amplitudes"][name] for w in full])
            for name in ["raw_present", "raw_absent", "parent_present", "parent_absent"]
        }
        standardized = {}
        for name, target in [("raw_present", 1), ("raw_absent", 0)]:
            values = np.array(
                [
                    (w["amplitudes"][name] - target) / w["raw_amplitude_standard_errors"][name]
                    for w in full
                ]
            )
            standardized[name] = dict(stats(values), RMS=float(np.sqrt(np.mean(values**2))))
        groups[phase_group] = {
            "widths": widths,
            "full_context_amplitudes": amplitudes,
            "full_context_standardized_raw_residuals": standardized,
        }
        points.extend(
            {
                "step": r["step"],
                "pair": r["pair"],
                "phase_group": phase_group,
                "fine_ladder": r["fine_ladder"],
                "SNR_by_width": [w["known_template_SNR"] for w in r["windows"]],
                "full_context_amplitudes": r["windows"][-1]["amplitudes"],
            }
            for r in selected
        )

    output.mkdir(exist_ok=False)
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), layout="constrained")
    colors = {"green": "#1c7c54", "all-CFA": "#315cbd"}
    widths = plan["native_contexts"]
    for name, group in groups.items():
        values = [group["widths"][str(w)]["known_template_SNR"] for w in widths]
        axes[0].plot(
            widths, [v["median"] for v in values], marker="o", color=colors[name], label=name
        )
        axes[0].fill_between(
            widths,
            [v["p10"] for v in values],
            [v["p90"] for v in values],
            color=colors[name],
            alpha=0.12,
        )
    axes[0].set(
        xscale="log",
        yscale="log",
        xlabel="Native window width (pixels)",
        ylabel="Conditional known-template SNR",
        title="Median and 10th–90th percentiles",
    )
    axes[0].set_xticks(widths, labels=[str(w) for w in widths])
    axes[0].xaxis.set_minor_locator(matplotlib.ticker.NullLocator())
    axes[0].legend(frameon=False)
    for axis, name in zip(axes[1:], ["green", "all-CFA"], strict=True):
        selected = [p for p in points if p["phase_group"] == name]
        for fine, label, color in [
            (False, "Legacy (292)", "#8b8b8b"),
            (True, "Fine ladder (322)", "#237c83"),
        ]:
            subset = [p for p in selected if p["fine_ladder"] == fine]
            axis.scatter(
                [p["SNR_by_width"][-1] for p in subset],
                [p["full_context_amplitudes"]["parent_present"] for p in subset],
                s=12,
                alpha=0.5,
                color=color,
                label=label,
                linewidths=0,
            )
        axis.axhline(
            1, color="#9c3b39", linewidth=1, linestyle="--", label="Exact template amplitude"
        )
        axis.set(
            xscale="log",
            yscale="symlog",
            xlabel="Conditional SNR, native 512 context",
            ylabel="V143 matched Bayer-sample amplitude",
            title=f"{name}: all 614 training pairs",
        )
        axis.set_yscale("symlog", linthresh=0.01)
        axis.legend(frameon=False, fontsize=8)
    fig.suptitle(
        "Exact hidden template/background supplied — training diagnostic, not inference quality",
        fontsize=12,
    )
    for suffix in ["png", "svg", "pdf"]:
        fig.savefig(output / f"context-evidence-v1.{suffix}", dpi=150)
    plt.close(fig)
    summary = {
        "status": "completed-GT-conditional-training-diagnostic-no-model-quality-claim",
        "plan": dict(ref(ROOT / "plan-v1.json"), contents=plan),
        "full_result": ref(result_path),
        "row_journal": ref(journal),
        "independent_verification": dict(ref(verification_path), contents=verification),
        "publication_source": dict(ref(Path(__file__)), text=Path(__file__).read_text()),
        "counts": {
            key: value
            for key, value in result.items()
            if key not in ["rows", "source", "scope", "plan", "owner", "status"]
        },
        "groups": groups,
        "plot_points": points,
        "figures": [
            ref(output / f"context-evidence-v1.{suffix}") for suffix in ["png", "svg", "pdf"]
        ],
        "scope": plan["scope"],
        "interpretation": "Each member's marginal RAW is projected separately; never cancel coupled noise by subtracting present/absent observations. Best windows use hidden GT. SNR=1/linear pre-ADC present-amplitude standard error,with exact variances and per-phase affine nuisance. Related phase groups and coupled pairs are not independent replications. Descriptive bins1,3,5 are not significance gates. Parent amplitudes use Bayer-sample projection on training targets,not held-out RGB mesh metrics; no parent uncertainty or flat-safety claim. Plot includes every point,with symlog y scale. No restored RGB or new model is produced; V175 fixed training/quality remains separate.",
    }
    with (output / "summary-v1.json").open("x") as stream:
        json.dump(summary, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"output": str(output), "rows": len(points), "groups": list(groups)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=EXTERNAL / "publication-v2")
    main(parser.parse_args().output)
