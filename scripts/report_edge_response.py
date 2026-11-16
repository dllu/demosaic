"""Source-cluster curves and native views from a completed edge-response panel."""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from demosaic.cfa import malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.crops import display_pixels, write_triplet
from demosaic.experiments.evaluation.edge_response import measure
from demosaic.experiments.evaluation.native import load_native


def statistics(scores, *, candidate="shared", baseline="V200"):
    groups = defaultdict(lambda: defaultdict(list))
    identities = set()
    for row in scores["rows"]:
        identity = tuple(row[k] for k in ["index", "method", "gain_scale"])
        if identity in identities:
            raise ValueError("Duplicate response metric identity")
        identities.add(identity)
        groups[row["method"], row["gain_scale"], row["placement"]][row["source"]].append(row)
    rng = np.random.default_rng(202611160600)
    names = [k for k in scores["rows"][0] if k.endswith(("DN16", "gain"))]
    summary, source_values = [], {}
    for (method, gain, placement), sources in sorted(groups.items()):
        if len(sources) != 8 or any(len(v) != 8 for v in sources.values()):
            raise ValueError("Expected eight sources, each four CFAs by two repeats")
        values = np.array(
            [[np.mean([r[k] for r in rows]) for k in names] for _, rows in sorted(sources.items())]
        )
        source_values[method, gain, placement] = values
        draws = rng.integers(len(values), size=(5000, len(values)))
        intervals = np.quantile(values[draws].mean(1), [0.025, 0.975], axis=0).T
        summary.append(
            {
                "method": method,
                "gain_scale": gain,
                "placement": placement,
                "sources": 8,
                "observations": 64,
                "images": 192,
                "metrics": {
                    name: {"mean": float(v), "source_bootstrap_95": ci.tolist()}
                    for name, v, ci in zip(names, values.mean(0), intervals, strict=True)
                },
            }
        )
    comparisons = []
    for state in ["raw", "ema"]:
        for placement in ["near", "far"]:
            delta = (
                source_values[f"{candidate}-{state}", 1.0, placement]
                - source_values[f"{baseline}-{state}", 1.0, placement]
            )
            draws = rng.integers(8, size=(5000, 8))
            intervals = np.quantile(delta[draws].mean(1), [0.025, 0.975], axis=0).T
            comparisons.append(
                {
                    "state": state,
                    "placement": placement,
                    "metrics": {
                        name: {"difference": float(v), "paired_source_bootstrap_95": ci.tolist()}
                        for name, v, ci in zip(names, delta.mean(0), intervals, strict=True)
                    },
                }
            )
    return summary, comparisons


def plot(summary, output, *, candidate="shared", baseline="V200"):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.1), layout="constrained")
    for placement, axis in zip(["near", "far"], axes, strict=True):
        for method, color, style in [
            (f"{baseline}-raw", "#ba6b25", "--"),
            (f"{baseline}-ema", "#b83c2e", "-"),
            (f"{candidate}-raw", "#5c8baf", "--"),
            (f"{candidate}-ema", "#176d9c", "-"),
        ]:
            points = sorted(
                [r for r in summary if r["method"] == method and r["placement"] == placement],
                key=lambda r: r["gain_scale"],
            )
            xs = [p["metrics"]["quiet_error_RMS_DN16"]["mean"] for p in points]
            ys = [100 * p["metrics"]["weak_gain"]["mean"] for p in points]
            axis.plot(xs, ys, marker="o", linestyle=style, color=color, label=method)
        axis.set(
            title=placement + " edge",
            xlabel="Actual quiet error (DN16 RMS)",
            ylabel="Weaker increment response (%)",
        )
        axis.grid(alpha=0.2)
    axes[1].legend(fontsize=8)
    figure.savefig(output / "curve.png", dpi=150)
    plt.close(figure)


def render(run, scores, cache, output):
    figures = []
    torch.set_num_threads(1)
    for source in [0, 1]:
        for placement in ["near", "far"]:
            item = next(
                r
                for r in cache["rows"]
                if r["metadata"]["recipe"]["source"] == source
                and r["metadata"]["placement"] == placement
                and r["metadata"]["pattern"] == "RGGB"
                and r["metadata"]["repeat"] == 0
            )
            with np.load(checked(item["arrays"]), allow_pickle=False) as archive:
                arrays = dict(archive)
            values = {
                m: load_native(b)[2:3]
                for m, b in scores["native_predictions"][str(item["index"])].items()
            }
            noisy = malvar(
                torch.from_numpy(arrays["packed"][2:3]), torch.from_numpy(arrays["colors"][2:3])
            ).numpy()
            calibration = {k: arrays[k][2:3] for k in ["wb", "matrix"]}
            target = arrays["target"][2:3]
            stem = f"source{source}-{placement}"
            metadata = write_triplet(
                output / (stem + "-triplet.png"),
                noisy,
                values["shared-ema"],
                target,
                calibration,
                roi=[176, 176, 160, 160],
                exposure=2.0,
                source={
                    "arrays": item["arrays"],
                    "metadata": item["metadata"],
                    "role": "two-directions",
                    "context": [512, 512],
                },
                checkpoint=scores["methods"]["shared-ema"],
                noise=dict(
                    item["metadata"]["noise"], pattern="RGGB", black_level=0.03, ADC_bits=16
                ),
                reference_kind="exact-GT",
            )
            ordered = [
                ("noisy Malvar", noisy),
                ("V195-ema", values["V195-ema"]),
                ("V200-ema", values["V200-ema"]),
                ("shared-ema", values["shared-ema"]),
                ("exact-GT", target),
            ]
            cells = [
                display_pixels(value, calibration, [176, 176, 160, 160], 2.0)
                for _, value in ordered
            ]
            image = output / (stem + "-comparison.png")
            Image.fromarray(np.concatenate(cells, axis=1)).save(image)
            figures.append(
                {
                    "triplet": metadata,
                    "comparison": reference(image),
                    "columns": [label for label, _ in ordered],
                    "no_resize": True,
                }
            )
    write_json(
        output / "figures.json",
        {
            "figures": figures,
            "no_resize": True,
            "viewed": False,
            "run": reference(run / "scores.json"),
        },
    )


def repeat_statistics(scores, cache):
    grouped = defaultdict(list)
    for row in cache["rows"]:
        m = row["metadata"]
        grouped[m["recipe"]["source"], m["placement"], m["pattern"]].append(row)
    results = []
    for (source, placement, pattern), group in sorted(grouped.items()):
        assert len(group) == 2 and {v["metadata"]["repeat"] for v in group} == {0, 1}
        with np.load(checked(group[0]["arrays"]), allow_pickle=False) as a:
            arrays = dict(a)
        with np.load(checked(group[1]["arrays"]), allow_pickle=False) as a:
            np.testing.assert_array_equal(arrays["target"], a["target"])
        for method in scores["native_predictions"][str(group[0]["index"])]:
            first, second = [
                load_native(scores["native_predictions"][str(r["index"])][method]).astype(
                    np.float64
                )
                for r in group
            ]
            mean = (first + second) / 2
            results.append(
                {
                    "source": source,
                    "placement": placement,
                    "pattern": pattern,
                    "method": method,
                    "repeat_mean_metrics": measure(arrays, mean),
                    "two_draw_sample_output_std_RMS_DN16": float(
                        np.sqrt(np.mean((first - second) ** 2) / 2) * 65535
                    ),
                }
            )
    return results


def report(run, output):
    binding = reference(run / "scores.json")
    scores = read_json(checked(binding))
    cache = read_json(run / "cache.json")
    if len(cache["rows"]) != 128 or len(scores["rows"]) != 2688:
        raise ValueError("Response panel is incomplete")
    output.mkdir(parents=True, exist_ok=False)
    summary, comparisons = statistics(scores)
    plot(summary, output)
    render(run, scores, cache, output)
    repeats = repeat_statistics(scores, cache)
    checked(binding)
    write_json(
        output / "analysis.json",
        {
            "scores": binding,
            "cache": reference(run / "cache.json"),
            "summaries": summary,
            "paired_differences": comparisons,
            "repeats": repeats,
            "plot": reference(output / "curve.png"),
            "figures": reference(output / "figures.json"),
            "report_script": reference(__file__),
            "uncertainty": "5000 paired source-cluster percentile resamples; CFA/repeat views averaged inside each of8source clusters",
            "scope": "Small exploratory constructed finite-wire panel, no generalization or formal risk guarantee. "
            "Weak response uses output(two)-output(one) against the actual clean weaker increment. "
            "All roles/repeats have independent noise; method differences share identical observations. "
            "Two-draw repeat statistics are descriptive sample mean/spread, not exact conditional bias/variance. "
            "No new inference or source/noise construction during analysis; real scenes remain in the prior full review.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report(args.run.absolute(), args.output.absolute())
