"""Independently check synthetic noise-fit arithmetic and summarize its scope."""

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch

from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def main(root, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    result = read(root / "result.json")
    assert (
        result["status"]
        == "completed-current-noise-estimator-synthetic-stress-awaiting-independent-summary"
    )
    assert sha(result["plan"]) == result["plan_sha256"]
    assert sha(result["cases"]) == result["cases_sha256"]
    plan = read(result["plan"])
    rows = [json.loads(line) for line in Path(result["cases"]).read_text().splitlines()]
    profiles = {v["name"]: v for v in plan["profiles"]}
    keys = [(v["scene"], v["seed"], v["profile"]) for v in rows]
    assert len(rows) == len(set(keys)) == result["case_count"] == plan["cases"] == 240
    assert set(keys) == {
        (s, seed, p) for s in plan["scenes"] for seed in plan["seeds"] for p in profiles
    }
    assert len({v["noise_seed"] for v in rows}) == 240
    assert plan["variance_probe_levels"] == [0.001, 0.005, 0.02, 0.08, 0.2, 0.6]
    assert plan["flag_threshold_absolute_variance_dB"] == 1
    for path, digest in plan["source_files"].items():
        assert sha(path) == digest
    clean_cache, case_checks, groups = {}, [], defaultdict(list)
    maximum_error, fields = 0.0, 0
    for row in rows:
        assert (row["shot"], row["read"]) == (
            profiles[row["profile"]]["shot"],
            profiles[row["profile"]]["read"],
        )
        record = row["clean"]
        if record["path"] not in clean_cache:
            assert sha(record["path"]) == record["sha256"]
            array = np.load(record["path"], allow_pickle=False)
            assert array.dtype == np.float32 and array.shape == (1024, 1024)
            assert np.isfinite(array).all() and array.min() >= 0
            clean_cache[record["path"]] = torch.from_numpy(array).double()
        clean = clean_cache[record["path"]]
        record = row["noisy"]
        assert sha(record["path"]) == record["sha256"]
        array = np.load(record["path"], allow_pickle=False)
        assert (
            array.dtype == np.float32 and array.shape == (1024, 1024) and np.isfinite(array).all()
        )
        assert (
            array.min() >= -plan["ADC_black"] / (1 - plan["ADC_black"]) - 1e-7 and array.max() <= 1
        )
        noisy = torch.from_numpy(array).double()
        valid = (clean > 0.03) & (clean < 0.85)
        residual = ((noisy - clean) / (clean * row["shot"] + row["read"]).sqrt())[valid]
        moments = {
            "standardized_mean": residual.mean().item(),
            "standardized_variance": residual.var(correction=0).item(),
        }
        assert int(valid.sum()) == row["noise_moments"]["uncensored_interior_samples"]
        for name, value in moments.items():
            error = abs(value - row["noise_moments"][name])
            assert error < 1e-10
            maximum_error = max(maximum_error, error)
            fields += 1
        estimate, recorded = row["estimate"], row["variance_diagnostics"]
        assert type(estimate["reliable"]) is bool
        check = {
            "scene": row["scene"],
            "seed": row["seed"],
            "profile": row["profile"],
            "reliable": estimate["reliable"],
            "reason": estimate["reason"],
            "maximum_absolute_variance_dB_full_probe": None,
            "maximum_absolute_variance_dB_within_bin_means": None,
        }
        if estimate["shot"] is None or estimate["read"] is None:
            assert recorded is None and not estimate["reliable"]
        else:
            assert math.isfinite(estimate["shot"]) and math.isfinite(estimate["read"])
            assert estimate["shot"] >= 0 and estimate["read"] >= 0
            signed = [
                10
                * math.log10(
                    (estimate["shot"] * x + estimate["read"]) / (row["shot"] * x + row["read"])
                )
                for x in plan["variance_probe_levels"]
            ]
            assert recorded["finite_positive"] and len(recorded["signed_dB"]) == 6
            for value, old in zip(signed, recorded["signed_dB"], strict=True):
                error = abs(value - old)
                assert error < 1e-12
                maximum_error = max(maximum_error, error)
                fields += 1
            lower, upper = (
                min(b["mean"] for b in estimate["bins"]),
                max(b["mean"] for b in estimate["bins"]),
            )
            inside = [
                abs(error)
                for level, error in zip(plan["variance_probe_levels"], signed, strict=True)
                if lower <= level <= upper
            ]
            check.update(
                accepted_bin_mean_range=[lower, upper],
                signed_variance_dB=signed,
                maximum_absolute_variance_dB_full_probe=max(map(abs, signed)),
                maximum_absolute_variance_dB_within_bin_means=max(inside) if inside else None,
            )
        case_checks.append(check)
        groups[row["scene"], row["profile"]].append(check)
    assert len(clean_cache) == result["clean_arrays"] == 40
    summary = []
    for scene in plan["scenes"]:
        for profile in profiles:
            values = groups[scene, profile]
            assert len(values) == 8
            trusted = [v for v in values if v["reliable"]]
            measures = {}
            for scope in ["full_probe", "within_bin_means"]:
                errors = [
                    v["maximum_absolute_variance_dB_" + scope]
                    for v in trusted
                    if v["maximum_absolute_variance_dB_" + scope] is not None
                ]
                measures[scope] = {
                    "cases": len(errors),
                    "median_worst_absolute_dB": statistics.median(errors) if errors else None,
                    "maximum_absolute_dB": max(errors) if errors else None,
                    "cases_above_1dB": sum(v > 1 for v in errors),
                }
            summary.append(
                {
                    "scene": scene,
                    "profile": profile,
                    "cases": 8,
                    "reliable": len(trusted),
                    "reasons": dict(Counter(v["reason"] for v in values)),
                    **measures,
                }
            )
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    figure, axes = plt.subplots(1, 2, figsize=(13, 5.5), layout="constrained")
    lookup = {(v["scene"], v["profile"]): v for v in summary}
    for axis, scope, title in zip(
        axes,
        ["full_probe", "within_bin_means"],
        ["All probe levels: .001 to .6", "Levels inside accepted bin-mean range"],
        strict=True,
    ):
        data = np.full((6, 5), np.nan)
        for y, profile in enumerate(profiles):
            for x, scene in enumerate(plan["scenes"]):
                value = lookup[scene, profile][scope]["median_worst_absolute_dB"]
                if value is not None:
                    data[y, x] = value
        palette = plt.colormaps["magma"].copy()
        palette.set_bad("#cccccc")
        artist = axis.imshow(
            data, vmin=0, vmax=3, cmap=palette, interpolation="nearest", aspect="auto"
        )
        axis.set_xticks(
            range(5), ["Flat", "Shading", "Texture", "Clip/dark", "Narrow"], rotation=30, ha="right"
        )
        axis.set_yticks(range(6), list(profiles))
        axis.set_title(title)
        for y, profile in enumerate(profiles):
            for x, scene in enumerate(plan["scenes"]):
                value = data[y, x]
                label = f"{value:.2f}" if np.isfinite(value) else "—"
                axis.text(
                    x,
                    y,
                    f"{label}\n{lookup[scene, profile]['reliable']}/8",
                    ha="center",
                    va="center",
                    color="white" if np.isfinite(value) and value < 1.7 else "black",
                    fontsize=9,
                )
        figure.colorbar(artist, ax=axis, label="Median worst |variance error|, dB", extend="max")
    figure.suptitle(
        "Current estimator: 240 synthetic cases; cells show value and reliable count\nGray cells have no reliable fit. No real-camera or restoration-quality result."
    )
    figure.savefig(output / "variance-fit-scope.png", dpi=160)
    figure.savefig(output / "variance-fit-scope.svg")
    plt.close(figure)
    with (output / "group-summary.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            [
                "scene",
                "profile",
                "cases",
                "reliable",
                "full_median_dB",
                "full_max_dB",
                "full_above1dB",
                "in_span_median_dB",
                "in_span_max_dB",
                "in_span_above1dB",
            ]
        )
        for v in summary:
            writer.writerow(
                [
                    v["scene"],
                    v["profile"],
                    v["cases"],
                    v["reliable"],
                    *[
                        v[s][k]
                        for s in ["full_probe", "within_bin_means"]
                        for k in [
                            "median_worst_absolute_dB",
                            "maximum_absolute_dB",
                            "cases_above_1dB",
                        ]
                    ],
                ]
            )
    audit = {
        "status": "completed-independent-current-noise-estimator-stress-arithmetic",
        "result": str(root / "result.json"),
        "result_sha256": sha(root / "result.json"),
        "cases_sha256": result["cases_sha256"],
        "arrays_checked": 280,
        "independent_metric_fields": fields,
        "maximum_arithmetic_difference": maximum_error,
        "case_checks": case_checks,
        "groups": summary,
        "reliable_cases": sum(v["reliable"] for v in case_checks),
        "reliable_above1dB_full_probe": sum(v["full_probe"]["cases_above_1dB"] for v in summary),
        "reliable_above1dB_within_bin_means": sum(
            v["within_bin_means"]["cases_above_1dB"] for v in summary
        ),
        "CUDA_initialized": False,
        "driver_sha256": sha(__file__),
        "scope": "All saved synthetic arrays and scalar arithmetic checked independently, moments in Torch64 and variance ratios with Python math. No rerun/reproduction of estimator selection or bootstrap. Full probe includes extrapolation; within-bin checks use accepted mean range, not a guaranteed calibration interval. Eight draws/group and artificial fields do not establish real-camera calibration, general uncertainty coverage or restored quality.",
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2, allow_nan=False) + "\n")
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps(
            {
                "audit": str(output / "audit.json"),
                "reliable": audit["reliable_cases"],
                "full_above1dB": audit["reliable_above1dB_full_probe"],
                "in_span_above1dB": audit["reliable_above1dB_within_bin_means"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
