"""Input-only proposal comparison on the closed three-noise finite-wire panel."""

import argparse
import math
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from demosaic.cfa import mosaic
from demosaic.competing_phase import competing_phase_bins
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.native import load_native
from demosaic.late_innovation_wave import innovation_phase_bins
from demosaic.prediction_archive import fingerprint


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    roots = [("iso6400", ".cache/experiments/near-edge-response-v1")]
    roots += [(p, f".cache/experiments/near-edge-response-{p}-v1") for p in ["iso1600", "iso400"]]
    records, inputs, bridges = [], [], []
    selectors = {"current": innovation_phase_bins, "competing": competing_phase_bins}
    for profile, directory in roots:
        root = Path(directory)
        scores = read_json(root / "scores.json")
        cache = read_json(root / "cache.json")
        inputs.extend([reference(root / "scores.json"), reference(root / "cache.json")])
        for item in cache["rows"]:
            # No target arrays or recipe parameters are loaded by this phase.
            with np.load(checked(item["arrays"]), allow_pickle=False) as a:
                packed, variance, colors = [
                    torch.from_numpy(a[k]) for k in ["packed", "variance", "colors"]
                ]
            anchor_binding = scores["native_predictions"][str(item["index"])]["V195-ema"]
            anchor = torch.from_numpy(load_native(anchor_binding))
            field = packed - mosaic(anchor, colors)
            choices = {}
            for name, selector in selectors.items():
                bins, valid, _ = selector(field, variance, colors)
                choices[name] = {"bins_yx": bins.tolist(), "valid": valid.tolist()}
                if item["index"] == 0:
                    gb, gv, _ = selector(field.cuda(), variance.cuda(), colors.cuda())
                    assert torch.equal(bins, gb.cpu()) and torch.equal(valid, gv.cpu())
                    bridges.append(
                        {"profile": profile, "selector": name, "integer_coordinates": bins.numel()}
                    )
            records.append(
                {
                    "profile": profile,
                    "index": item["index"],
                    "arrays": item["arrays"],
                    "anchor": anchor_binding,
                    "field": fingerprint(field.numpy()),
                    "choices": choices,
                }
            )
        print(profile, "all128 batches selected without target arrays", flush=True)
    write_json(
        output / "selections.json",
        {
            "inputs": inputs,
            "rows": records,
            "CPU_GPU_bridges": bridges,
            "selectors": [
                reference("src/demosaic/late_innovation_wave.py"),
                reference("src/demosaic/competing_phase.py"),
            ],
            "scope": "All selections close before recipe geometry scoring. Parent has seen all RAW; empirical, not independent validation.",
        },
    )
    score_closed(output / "selections.json", output)


def score_closed(selections, output):
    document = read_json(checked(reference(selections)))
    for binding in document["inputs"]:
        checked(binding)
    records = document["rows"]
    roots = [("iso6400", ".cache/experiments/near-edge-response-v1")]
    roots += [(p, f".cache/experiments/near-edge-response-{p}-v1") for p in ["iso1600", "iso400"]]
    output.mkdir(parents=True, exist_ok=True)
    # Only the scoring phase reads the known procedural geometry.
    scored = []
    for profile, directory in roots:
        cache = read_json(Path(directory) / "cache.json")
        for record in [r for r in records if r["profile"] == profile]:
            item = cache["rows"][record["index"]]
            recipe = item["metadata"]["recipe"]
            target_bins = [
                np.array([math.sin(a), math.cos(a)]) * recipe["size"] / p
                for a, p in zip(recipe["wire_angles"], recipe["periods"], strict=True)
            ]
            for selector, selection in record["choices"].items():
                bins = np.array(selection["bins_yx"]).reshape(3, -1, 2)
                valid = np.array(selection["valid"]).reshape(3, -1)
                signed = np.where(bins >= recipe["size"] // 4, bins - recipe["size"] // 2, bins)
                for role in range(3):
                    for direction, target in enumerate(target_bins):
                        d = np.minimum(
                            np.linalg.norm(signed[role] - target, axis=-1),
                            np.linalg.norm(signed[role] + target, axis=-1),
                        )
                        distance = float(np.min(np.where(valid[role], d, np.inf)))
                        scored.append(
                            {
                                "profile": profile,
                                "index": item["index"],
                                "source": recipe["source"],
                                "placement": item["metadata"]["placement"],
                                "role": role,
                                "selector": selector,
                                "direction": direction,
                                "nearest_fundamental_native_bins": distance,
                            }
                        )
    groups = defaultdict(list)
    for row in scored:
        groups[
            row["profile"], row["selector"], row["placement"], row["role"], row["direction"]
        ].append(row)
    summaries = []
    for (profile, selector, placement, role, direction), group in sorted(groups.items()):
        distances = np.array([r["nearest_fundamental_native_bins"] for r in group])
        summaries.append(
            {
                "profile": profile,
                "selector": selector,
                "placement": placement,
                "role": role,
                "direction": direction,
                "observations": len(group),
                "fraction_within1": float(np.mean(distances <= 1)),
                "fraction_within3": float(np.mean(distances <= 3)),
                "median_distance": float(np.median(distances)),
            }
        )
    write_json(
        output / "result.json",
        {
            "selections": reference(selections),
            "rows": scored,
            "summaries": summaries,
            "script": reference(__file__),
            "new_neural_forwards": 0,
            "new_noise_draws": 0,
            "scope": "Native carrier proximity to known Gaussian-wire fundamentals, not a reconstruction bound. "
            "Finite envelopes, harmonics and spatial modulation matter. Proposals do not detect structure; "
            "absent-role proximity is retained. No GT in selection, no model-quality or flat-safety claim.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--selections", type=Path, help="Score an already closed selection stream; no remeasurement"
    )
    args = parser.parse_args()
    if args.selections:
        score_closed(args.selections, args.output)
    else:
        run(args.output)
