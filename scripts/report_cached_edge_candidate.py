"""Paired source-cluster summaries and native views of a closed cached trial."""

import argparse
import math
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from report_edge_response import plot, statistics

from demosaic.cfa import malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.crops import display_pixels, write_triplet
from demosaic.experiments.evaluation.native import load_native


def paired_rows(candidate, baseline):
    """Bind every new metric to the same observation, conditions and anchor."""
    old = {}
    for row in baseline:
        key = row["index"], row["method"], row["gain_scale"]
        if key in old:
            raise ValueError("Duplicate baseline identity")
        old[key] = row
    seen = set()
    for row in candidate:
        state = row["method"].removeprefix("competing-")
        if state not in ("raw", "ema") or row["method"] != "competing-" + state:
            raise ValueError("Unknown candidate endpoint")
        key = row["index"], "V200-" + state, row["gain_scale"]
        if key in seen or key not in old:
            raise ValueError("Duplicate or missing paired observation")
        seen.add(key)
        control = old[key]
        if any(row[k] != control[k] for k in ["source", "placement", "pattern", "repeat"]):
            raise ValueError("Mismatched paired conditions")
        for name, value in row.items():
            if not name.endswith(("DN16", "gain")):
                continue
            if not math.isfinite(value) or not math.isfinite(control[name]):
                raise ValueError("Nonfinite paired metric")
            if row["gain_scale"] == 0 and value != control[name]:
                raise ValueError("Different zero-gain anchor")
    expected = {k for k in old if k[1] in ("V200-raw", "V200-ema")}
    if seen != expected:
        raise ValueError("Incomplete paired coverage")
    return [r for r in baseline if r["method"] in ("V195-ema", "V200-raw", "V200-ema")] + candidate


def render(profile, scores, baseline, cache, output):
    figures = []
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
            with np.load(checked(item["arrays"]), allow_pickle=False) as a:
                arrays = dict(a)
            old = baseline["native_predictions"][str(item["index"])]
            new = scores["native_predictions"][profile][str(item["index"])]
            values = {m: load_native(old[m])[2:3] for m in ["V195-ema", "V200-ema"]}
            values["competing-ema"] = load_native(new["ema"])[2:3]
            noisy = malvar(
                torch.from_numpy(arrays["packed"][2:3]), torch.from_numpy(arrays["colors"][2:3])
            ).numpy()
            calibration = {k: arrays[k][2:3] for k in ["wb", "matrix"]}
            target = arrays["target"][2:3]
            stem = f"{profile}-source{source}-{placement}"
            metadata = write_triplet(
                output / (stem + "-triplet.png"),
                noisy,
                values["competing-ema"],
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
                checkpoint=scores["exports"]["ema"],
                noise=dict(
                    item["metadata"]["noise"], pattern="RGGB", black_level=0.03, ADC_bits=16
                ),
                reference_kind="exact-GT",
            )
            ordered = [
                ("noisy Malvar", noisy),
                ("V195-ema", values["V195-ema"]),
                ("V200-ema", values["V200-ema"]),
                ("competing-ema", values["competing-ema"]),
                ("exact-GT", target),
            ]
            image = output / (stem + "-comparison.png")
            cells = [
                display_pixels(value, calibration, [176, 176, 160, 160], 2.0)
                for _, value in ordered
            ]
            Image.fromarray(np.concatenate(cells, axis=1)).save(image)
            figures.append(
                {
                    "profile": profile,
                    "source": source,
                    "placement": placement,
                    "triplet": metadata,
                    "comparison": reference(image),
                    "columns": [label for label, _ in ordered],
                    "no_resize": True,
                }
            )
    return figures


def report(run, output):
    binding = reference(run / "scores.json")
    scores = read_json(checked(binding))
    if (
        scores["status"] != "completed-three-noise-cached-edge-candidate"
        or len(scores["rows"]) != 3840
        or not scores["weights_and_RNG_unchanged"]
    ):
        raise ValueError("Incomplete cached candidate evaluation")
    plan = read_json(checked(scores["plan"]))
    output.mkdir(parents=True, exist_ok=False)
    summaries, comparisons, figures, inputs = [], [], [], []
    torch.set_num_threads(1)
    for cohort in plan["baselines"]:
        profile = cohort["profile"]
        baseline = read_json(checked(cohort["scores"]))
        cache = read_json(checked(cohort["cache"]))
        inputs.extend([cohort["scores"], cohort["cache"]])
        if len(baseline["rows"]) != 2688 or len(cache["rows"]) != 128:
            raise ValueError("Incomplete baseline panel")
        new = [r for r in scores["rows"] if r["profile"] == profile]
        merged = paired_rows(new, baseline["rows"])
        summary, comparison = statistics({"rows": merged}, candidate="competing")
        folder = output / profile
        folder.mkdir()
        plot(summary, folder, candidate="competing")
        summaries.extend([dict(r, profile=profile) for r in summary])
        comparisons.extend([dict(r, profile=profile) for r in comparison])
        figures.extend(render(profile, scores, baseline, cache, output))
    checked(binding)
    write_json(
        output / "analysis.json",
        {
            "scores": binding,
            "inputs": inputs,
            "summaries": summaries,
            "paired_differences": comparisons,
            "figures": figures,
            "native_viewed": False,
            "script": reference(__file__),
            "statistics_script": reference(Path(__file__).with_name("report_edge_response.py")),
            "uncertainty": "5000 paired source-cluster percentile resamples. Eight sources; four CFAs/two repeats averaged within each source. Exploratory intervals, no formal risk control.",
            "scope": "Exact same cached observations, conditions and zero-gain anchors. No new inference, noise, source construction or trained weights. Native160 crops never resized. Proposal-informed development panel, not blind generalization or calibrated confidence.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report(args.run.absolute(), args.output.absolute())
