"""Reference-check the green-phase statistic using retained photographic inputs.

The fixed bins are descriptive, not signal detection or restoration thresholds.
No model execution, random sampling, RAW decoding or camera-profile fitting.
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib
import numpy as np
from green_phase_spectrum import cross_decomposition, green_pair
from report_green_phase_spectrum import binding, choose_peaks, verify

matplotlib.use("Agg")
from matplotlib import pyplot as plt

CROSS_EDGES = (-np.inf, 0, 1, 4, 16, np.inf)
POWER_EDGES = (-np.inf, 1, 4, 16, np.inf)


def reference_phases(rgb):
    """Sample the reference green field at all four physical phase positions."""
    field = rgb[0, 1]
    return np.stack([field[y::2, x::2] for y, x in ((0, 0), (0, 1), (1, 0), (1, 1))])


def band_mask(result):
    fx, fy = result["native_fx"], result["native_fy"]
    radius = np.hypot(fx, fy)
    return (radius >= 1 / 16) & (radius <= 1 / 3) & ((fy > 0) | ((fy == 0) & (fx > 0)))


def aggregate(rows):
    """Pool regions/CFAs inside capture, then give captures equal row weight."""
    output = []
    for domain in sorted({row["domain"] for row in rows}):
        for condition in ("iso100-prior", "iso12800-prior"):
            matching = [r for r in rows if r["domain"] == domain and r["condition"] == condition]
            sources = sorted({r["source_id"] for r in matching})
            histograms = []
            for source in sources:
                case_rows = [r for r in matching if r["source_id"] == source]
                histograms.append(np.sum([r["bin_counts"] for r in case_rows], axis=0))
            histograms = np.stack(histograms)
            totals = histograms.sum(-1)
            fractions = np.divide(
                histograms,
                totals[..., None],
                out=np.zeros_like(histograms, dtype=float),
                where=totals[..., None] > 0,
            )
            support = np.sum(totals > 0, axis=0)
            means = np.divide(
                fractions.sum(0), support[:, None], out=np.zeros((5, 4)), where=support[:, None] > 0
            )
            reference_supported = sum(r["reference_power_at_least4_bins"] for r in matching)
            negative = sum(
                r["reference_power_at_least4_nonpositive_observed_cross_bins"] for r in matching
            )
            selected = [p for r in matching for p in r["peaks"] if p["observed_cross"] > 4]
            output.append(
                {
                    "domain": domain,
                    "condition": condition,
                    "sources": sources,
                    "observations": len(matching),
                    "total_band_bins": int(histograms.sum()),
                    "source_counts_by_cross_bin": support.tolist(),
                    "source_balanced_reference_power_fractions_by_cross_bin": means.tolist(),
                    "per_source_bin_counts": {
                        source: histograms[i].tolist() for i, source in enumerate(sources)
                    },
                    "reference_power_at_least4_bins": reference_supported,
                    "reference_power_at_least4_nonpositive_observed_cross_bins": negative,
                    "selected_peaks_observed_cross_above4": len(selected),
                    "selected_peaks_above4_reference_power_at_most1": sum(
                        p["reference_power"] <= 1 for p in selected
                    ),
                    "selected_peaks_above4_nonpositive_reference_cross": sum(
                        p["reference_cross"] <= 0 for p in selected
                    ),
                }
            )
    return output


def execute(plan_path, output):
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    if plan["algorithm"] != "green-phase-reference-check-v1":
        raise ValueError("Unexpected frozen protocol")
    paths = {verify(record).resolve() for record in plan["code"]}
    executed = {
        Path(__file__).resolve(),
        Path(sys.modules[cross_decomposition.__module__].__file__).resolve(),
        Path(sys.modules[choose_peaks.__module__].__file__).resolve(),
    }
    if not executed <= paths:
        raise ValueError("Unbound executing code")
    for record in plan["receipts"]:
        verify(record)
    output = Path(output).resolve()
    output.mkdir(exist_ok=False)
    (output / "maps").mkdir()
    (output / "input-only-peaks").mkdir()
    rows = []
    for index, case in enumerate(plan["cases"]):
        with np.load(verify(case["inputs"]), allow_pickle=False) as source:
            packed, variance, colors = (
                source["packed"][0],
                source["variance"][0],
                source["colors"][0],
            )
            observed = green_pair(packed, variance, colors)
            peaks = choose_peaks(observed)
            (output / "input-only-peaks" / f"{index:03d}.json").write_text(json.dumps(peaks) + "\n")
            if case["domain"] == "Commons exact synthetic target":
                # Exposure1 target matches the clean source; physical sampling
                # floors negative sensor channels, exactly as the original suite.
                rgb = source["target"].copy()
            else:
                rgb = np.load(verify(case["reference"]), allow_pickle=False)
        reference = reference_phases(np.maximum(rgb, 0))
        result = cross_decomposition(packed, reference, variance, colors)
        obs, ref = result["observed"], result["reference"]
        components = result["noise_units_components"]
        mask = band_mask(obs)
        cross = obs["noise_units_signed_cross"]
        power = ref["noise_units_mean_phase_power"]
        # Right-closed descriptive bins: <=0, (0,1], (1,4], (4,16], >16.
        a = np.searchsorted(CROSS_EDGES[1:-1], cross[mask], side="left")
        b = np.searchsorted(POWER_EDGES[1:-1], power[mask], side="left")
        counts = np.zeros((5, 4), dtype=np.int64)
        np.add.at(counts, (a, b), 1)
        row = {
            k: case[k] for k in ("id", "domain", "source_id", "condition", "pattern", "target_role")
        }
        row.update(
            {
                "index": index,
                "bin_counts": counts.tolist(),
                "reference_power_at_least4_bins": int(np.sum(mask & (power >= 4))),
                "reference_power_at_least4_nonpositive_observed_cross_bins": int(
                    np.sum(mask & (power >= 4) & (cross <= 0))
                ),
                "maximum_component_identity_error": float(
                    np.max(np.abs(sum(components.values()) - cross))
                ),
                "peaks": [],
            }
        )
        for peak in peaks:
            y, x = peak["bin_yx"]
            row["peaks"].append(
                {
                    **peak,
                    "observed_cross": float(cross[y, x]),
                    "reference_power": float(power[y, x]),
                    "reference_cross": float(components["reference"][y, x]),
                    "residual_cross": float(components["residual"][y, x]),
                    "mixed_cross": float(components["mixed"][y, x]),
                    "reference_signed_coherence": float(ref["signed_coherence"][y, x]),
                }
            )
        path = output / "maps" / f"{index:03d}.npz"
        np.savez_compressed(
            path,
            observed_cross=cross,
            reference_power=power,
            band_mask=mask,
            **{f"{name}_cross": values for name, values in components.items()},
        )
        row["maps"] = binding(path)
        with (output / "cases.jsonl").open("a") as stream:
            stream.write(json.dumps(row, allow_nan=False) + "\n")
        rows.append(row)
    summaries = aggregate(rows)
    figure, axes = plt.subplots(2, 2, figsize=(11, 8.3), squeeze=False)
    for axis, group in zip(axes.ravel(), summaries, strict=True):
        values = np.asarray(group["source_balanced_reference_power_fractions_by_cross_bin"])
        image = axis.imshow(values, vmin=0, vmax=1, cmap="viridis")
        for y in range(5):
            for x in range(4):
                axis.text(
                    x,
                    y,
                    f"{100 * values[y, x]:.1f}%",
                    color="white" if values[y, x] < 0.45 else "black",
                    ha="center",
                    va="center",
                    fontsize=9,
                )
        axis.set_xticks(range(4), ("≤1", "1–4", "4–16", ">16"))
        axis.set_yticks(range(5), ("≤0", "0–1", "1–4", "4–16", ">16"))
        axis.set_xlabel("Reference phase power / conditional noise")
        axis.set_ylabel("Observed signed cross / conditional noise")
        axis.set_title(
            f"{group['domain']}\n{group['condition']}; {len(group['sources'])} sources", fontsize=10
        )
        figure.colorbar(image, ax=axis, shrink=0.8)
    figure.suptitle(
        "Reference-checking shared green-phase structure\nSource-balanced row fractions; descriptive bins, not calibrated detection",
        fontsize=12,
    )
    figure.tight_layout()
    for extension in ("png", "pdf"):
        figure.savefig(output / f"reference-check.{extension}", dpi=150)
    plt.close(figure)
    if any(
        name.split(".")[0] in {"torch", "rawpy", "transformers", "demosaic"} for name in sys.modules
    ):
        raise RuntimeError("Neural/camera library imported")
    result = {
        "status": "complete-reference-diagnostic",
        "plan": binding(plan_path),
        "case_count": len(rows),
        "summaries": summaries,
        "artifacts": [
            binding(output / name)
            for name in ("cases.jsonl", "reference-check.png", "reference-check.pdf")
        ],
        "maximum_component_identity_error": max(
            r["maximum_component_identity_error"] for r in rows
        ),
        "new_neural_forwards": 0,
        "RAW_decodes": 0,
        "new_noise_observations": 0,
        "optimizer_updates": 0,
        "limitations": plan["limitations"],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "result": binding(output / "result.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    execute(args.plan, args.output)
