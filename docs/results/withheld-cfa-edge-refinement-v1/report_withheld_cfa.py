"""Source-cluster uncertainty and a static detail/false-correction curve."""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def run(source, output, *, step_label="Grid-step background"):
    binding = reference(source)
    result = read_json(source)
    checked(result["script"])
    checked(result["implementation"])
    output.mkdir(parents=True, exist_ok=False)
    groups = defaultdict(list)
    for row in result["rows"]:
        groups[row["cohort"], row["kind"], row["nuisance"]].append(row)
    rng = np.random.default_rng(202611160301)
    summaries = []
    for (cohort, kind, nuisance), group in sorted(groups.items()):
        for threshold in (0.0, 1.0, 2.0, 3.0, 4.0):
            clusters = defaultdict(list)
            for row in group:
                active = row["min_validation_z"] > threshold
                clusters[row["source_seed"]].append(
                    [
                        float(active),
                        active * row["correction_RMS_DN16"],
                        active * (row["template_gain"] or 0),
                        active * row.get("direction_gains", [0.0, 0.0])[-1]
                        if "two-wave" in kind
                        else 0.0,
                    ]
                )
            values = np.array([np.mean(v, axis=0) for v in clusters.values()])
            estimates = values.mean(axis=0)
            bootstrap = values[rng.integers(len(values), size=(5000, len(values)))].mean(axis=1)
            intervals = np.quantile(bootstrap, [0.025, 0.975], axis=0).T
            summaries.append(
                {
                    "cohort": cohort,
                    "kind": kind,
                    "nuisance": nuisance,
                    "threshold": threshold,
                    "sources": len(values),
                    "patches": len(group),
                    "metrics": {
                        name: {"mean": float(mean), "source_bootstrap_95": interval.tolist()}
                        for name, mean, interval in zip(
                            (
                                "activation_rate",
                                "correction_RMS_DN16",
                                "template_gain",
                                "weak_direction_gain",
                            ),
                            estimates,
                            intervals,
                            strict=True,
                        )
                    },
                }
            )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axis = plt.subplots(figsize=(7, 4.4), layout="constrained")
    for nuisance, color, label in (
        ("affine", "#ae3b2c", "Affine background"),
        ("step", "#176d9c", step_label),
    ):

        def metric(kind, threshold, name, nuisance=nuisance):
            return next(
                r
                for r in summaries
                if (r["cohort"], r["kind"], r["nuisance"], r["threshold"])
                == ("test", kind, nuisance, threshold)
            )["metrics"][name]

        xs, ys = [], []
        for threshold in (0.0, 1.0, 2.0, 3.0, 4.0):
            x = metric("edge-offgrid", threshold, "correction_RMS_DN16")
            y = metric("two-wave-edge", threshold, "template_gain")
            xs.append(x["mean"])
            ys.append(y["mean"] * 100)
            xi, yi = np.asarray(x["source_bootstrap_95"]), np.asarray(y["source_bootstrap_95"])
            axis.errorbar(
                x["mean"],
                y["mean"] * 100,
                xerr=np.abs(xi - x["mean"]).reshape(2, 1),
                yerr=np.abs(yi - y["mean"]).reshape(2, 1) * 100,
                fmt="o",
                color=color,
                capsize=2,
                alpha=0.7,
            )
            if nuisance == "step":
                axis.annotate(
                    f"t={threshold:g}",
                    (x["mean"], y["mean"] * 100),
                    xytext=(6, -10),
                    textcoords="offset points",
                    fontsize=8,
                )
        axis.plot(xs, ys, color=color, label=label)
    axis.set(
        xlabel="False periodic correction on off-grid edge-only targets (DN16 RMS)",
        ylabel="Two-wave template gain beside grid edges (%)",
        title="Withheld CFA samples: edge-model mismatch still predicts across subsets",
    )
    axis.set_xlim(left=0)
    axis.set_ylim(bottom=0)
    axis.grid(alpha=0.2)
    axis.legend(loc="lower left")
    figure.savefig(output / "curve.png", dpi=150)
    plt.close(figure)
    checked(binding)
    write_json(
        output / "summary.json",
        {
            "source": binding,
            "report_script": reference(__file__),
            "summaries": summaries,
            "plot": reference(output / "curve.png"),
            "uncertainty": "5000 source-cluster percentile bootstrap draws; two noise repeats averaged inside each source. Descriptive, no simultaneous or formal risk guarantee.",
            "scope": "Curve x and y use different procedural families, not one combined task score. "
            "False-correction RMS measures the delivered periodic correction against the exact zero "
            "increment on no-wave controls; it is not total reconstruction error. Template gain "
            "is a signed projection and does not isolate the weak second direction. Thresholds "
            "were fixed; this expanded panel followed an eight-source exploratory pilot.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--step-label", default="Grid-step background")
    args = parser.parse_args()
    run(args.source, args.output, step_label=args.step_label)
