"""Input-only proposal closure above cached V200, preserving the original bank."""

import argparse
from pathlib import Path

import numpy as np
import torch
from diagnose_competing_phase import score_closed

from demosaic.cfa import mosaic
from demosaic.competing_phase import competing_phase_bins, exclude_nearby_bins
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.native import load_native
from demosaic.prediction_archive import fingerprint


def run(output):
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    prior_binding = reference(".cache/experiments/competing-phase-diagnostic-v1/selections.json")
    prior = read_json(checked(prior_binding))
    previous = {(r["profile"], r["index"]): r for r in prior["rows"]}
    roots = [("iso6400", Path(".cache/experiments/near-edge-response-v1"))]
    roots += [
        (p, Path(f".cache/experiments/near-edge-response-{p}-v1")) for p in ["iso1600", "iso400"]
    ]
    records, inputs, bridges, counts = [], [], [], []
    for profile, root in roots:
        cache = read_json(root / "cache.json")
        scores = read_json(root / "scores.json")
        inputs += [reference(root / "cache.json"), reference(root / "scores.json")]
        for item in cache["rows"]:
            old = previous[profile, item["index"]]
            assert item["arrays"] == old["arrays"]
            with np.load(checked(item["arrays"]), allow_pickle=False) as a:
                packed, variance, colors = [
                    torch.from_numpy(a[k]) for k in ["packed", "variance", "colors"]
                ]
            v195 = torch.from_numpy(load_native(old["anchor"]))
            assert fingerprint((packed - mosaic(v195, colors)).numpy()) == old["field"]
            anchor = scores["native_predictions"][str(item["index"])]["V200-ema"]
            field = packed - mosaic(torch.from_numpy(load_native(anchor)), colors)
            original = old["choices"]["current"]
            occupied = torch.tensor(original["bins_yx"])
            occupied_valid = torch.tensor(original["valid"])
            bins, proposed, _ = competing_phase_bins(field, variance, colors)
            valid = exclude_nearby_bins(bins, proposed, occupied, occupied_valid, field.shape[-2:])
            if item["index"] == 0:
                gb, gv, _ = competing_phase_bins(field.cuda(), variance.cuda(), colors.cuda())
                extra = exclude_nearby_bins(
                    gb, gv, occupied.cuda(), occupied_valid.cuda(), field.shape[-2:]
                )
                assert torch.equal(bins, gb.cpu()) and torch.equal(valid, extra.cpu())
                bridges.append(
                    {"profile": profile, "integer_coordinates": bins.numel(), "exact": True}
                )
            choices = {
                "current": original,
                "complementary": {
                    "bins_yx": torch.cat((occupied, bins), 2).tolist(),
                    "valid": torch.cat((occupied_valid, valid), 2).tolist(),
                },
                "additional-only": {"bins_yx": bins.tolist(), "valid": valid.tolist()},
            }
            records.append(
                {
                    "profile": profile,
                    "index": item["index"],
                    "arrays": item["arrays"],
                    "anchor": anchor,
                    "field": fingerprint(field.numpy()),
                    "choices": choices,
                }
            )
            counts.append(
                {
                    "profile": profile,
                    "index": item["index"],
                    "extra_per_role": valid.flatten(1).sum(1).tolist(),
                }
            )
        print(profile, "closed all128 input-only selections", flush=True)
    write_json(
        output / "selections.json",
        {
            "inputs": inputs,
            "prior": prior_binding,
            "rows": records,
            "CPU_GPU_bridges": bridges,
            "script": reference(__file__),
            "selection_source": reference("src/demosaic/competing_phase.py"),
            "scope": "Frozen original8 carriers plus up to8 nonduplicate carriers selected on RAW-minus-V200EMA. Full parent reuses RAW; nominal scores are not independent confidence. All384 selections close before target geometry scoring. No neural forward or new source/noise.",
        },
    )
    write_json(
        output / "counts.json",
        {
            "rows": counts,
            "scope": "Proposed additional valid carriers per zero/one/two-direction role; not detected structures.",
        },
    )
    score_closed(output / "selections.json", output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.output.absolute())
