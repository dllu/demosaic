"""Compare immutable edge-response observations across three noise profiles."""

import argparse
from pathlib import Path

import numpy as np
from report_edge_response import statistics

from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def summarize(output):
    output.mkdir(parents=True, exist_ok=False)
    profiles = [("iso6400", Path(".cache/experiments/near-edge-response-v1"))]
    profiles += [
        (p, Path(f".cache/experiments/near-edge-response-{p}-v1")) for p in ["iso1600", "iso400"]
    ]
    summary, comparisons, snr, inputs = [], [], [], []
    original = read_json(profiles[0][1] / "cache.json")["rows"]
    pairs = 0
    for profile, root in profiles:
        scores = read_json(root / "scores.json")
        cache = read_json(root / "cache.json")
        inputs.extend([reference(root / "scores.json"), reference(root / "cache.json")])
        s, c = statistics(scores)
        summary.extend([dict(r, profile=profile) for r in s])
        comparisons.extend([dict(r, profile=profile) for r in c])
        for item, old in zip(cache["rows"], original, strict=True):
            with np.load(checked(item["arrays"]), allow_pickle=False) as a:
                arrays = dict(a)
            if profile != "iso6400":
                with np.load(checked(old["arrays"]), allow_pickle=False) as a:
                    for key in ["target", "wb", "matrix", "colors", "quiet", "edge_band"]:
                        np.testing.assert_array_equal(arrays[key], a[key])
                pairs += 1
            packed = np.stack(
                [
                    np.stack([rgb[int(c), p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
                    for rgb, colors in zip(
                        arrays["target"].astype(np.float64), arrays["colors"], strict=True
                    )
                ]
            )
            noise = item["metadata"]["noise"]
            for label, first, second in [("strong", 0, 1), ("weak", 1, 2)]:
                variance = (
                    noise["shot"] * (packed[first] + packed[second])
                    + 2 * noise["read"]
                    + 2 / (12 * (0.97 * 65535) ** 2)
                )
                snr.append(
                    {
                        "profile": profile,
                        "index": item["index"],
                        "source": item["metadata"]["recipe"]["source"],
                        "placement": item["metadata"]["placement"],
                        "component": label,
                        "oracle_sensor_pair_SNR": float(
                            np.sqrt(np.sum((packed[second] - packed[first]) ** 2 / variance))
                        ),
                    }
                )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figure, axes = plt.subplots(1, 2, figsize=(10, 4.2), layout="constrained")
    for placement, axis in zip(["near", "far"], axes, strict=True):
        for method, style in [("V200-ema", "-"), ("shared-ema", "--")]:
            for component, color in [("strong", "#b53c2e"), ("weak", "#176d9c")]:
                values = [
                    next(
                        r
                        for r in summary
                        if r["profile"] == profile
                        and r["placement"] == placement
                        and r["method"] == method
                        and r["gain_scale"] == 1.0
                    )["metrics"][component + "_gain"]
                    for profile, _ in profiles
                ]
                means = np.array([v["mean"] for v in values]) * 100
                ci = np.array([v["source_bootstrap_95"] for v in values]) * 100
                axis.errorbar(
                    range(3),
                    means,
                    yerr=np.abs(ci - means[:, None]).T,
                    color=color,
                    linestyle=style,
                    marker="o",
                    label=f"{method} {component}",
                    capsize=2,
                )
        axis.set(
            title=placement + " edge",
            xticks=range(3),
            xticklabels=["6400 prior", "1600 prior", "400 prior"],
            xlabel="Synthetic noise profile (identical clean targets)",
            ylabel="Conditional increment response (%)",
            ylim=(-5, 105),
        )
        axis.axhline(100, color="#999999", linewidth=0.7)
        axis.grid(alpha=0.2)
    axes[0].legend(fontsize=7)
    figure.savefig(output / "response.png", dpi=150)
    plt.close(figure)
    write_json(
        output / "summary.json",
        {
            "inputs": inputs,
            "summaries": summary,
            "paired_differences": comparisons,
            "oracle_sensor_pair_SNR": snr,
            "exact_clean_batch_pairs_across_lower_noise_profiles": pairs,
            "plot": reference(output / "response.png"),
            "script": reference(__file__),
            "uncertainty": "5000source-cluster percentile bootstrap draws; eight sources, CFA/repeat views averaged within source.",
            "scope": "Exact clean/camera/mask equality checked over both lower-noise caches. Oracle SNR uses hidden templates and approximate ADC variance, not unknown-candidate detection power. No new inference/noise or trained weights.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    summarize(args.output)
