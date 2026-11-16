"""Check every closed carrier choice on CUDA without model construction or GT."""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.runtime import RuntimePolicy, owner_identity

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").is_file())


def prepare(root):
    selections = REPO / ".cache/experiments/complementary-phase-diagnostic-v1/selections.json"
    closed = read_json(selections)
    prior = read_json(checked(closed["prior"]))
    candidate = REPO / ".cache/experiments/complementary-edge-review-corrected-v1/work"
    root.mkdir(parents=True, exist_ok=False)
    work, files = freeze_sources(candidate, root)
    source = work / "scripts" / Path(__file__).name
    source.parent.mkdir()
    shutil.copyfile(__file__, source)
    files[str(source)] = reference(source)["sha256"]
    expected = {
        (profile, index) for profile in ["iso6400", "iso1600", "iso400"] for index in range(128)
    }
    assert {(r["profile"], r["index"]) for r in closed["rows"]} == expected
    assert len(closed["rows"]) == len(prior["rows"]) == 384
    # The older diagnostic also bound its unused competing-bank comparator.
    # This check replays only the inherited selector and the later extra bank.
    required = [
        closed["selection_source"],
        next(x for x in prior["selectors"] if Path(x["path"]).name == "late_innovation_wave.py"),
    ]
    for item in required:
        path = Path(item["path"])
        target = work / "src" / path.relative_to(REPO / "src")
        assert reference(target)["sha256"] == item["sha256"]
    plan = {
        "root": str(root),
        "work": str(work),
        "script": reference(source),
        "python": sys.executable,
        "selections": reference(selections),
        "prior": closed["prior"],
        "used_selector_sources": required,
        "rows": 384,
        "selector_calls": 768,
        "neural_forwards": 0,
        "model_constructions": 0,
        "runtime": RuntimePolicy(
            cuda_quota_gib=2, minimum_ram_gib=32, minimum_disk_gib=96
        ).to_dict(),
        "maximum_seconds": 3600,
        "inputs": [reference(selections), closed["prior"], *closed["inputs"], *prior["inputs"]],
        "frozen_files": files,
        "scope": "All384 already-closed input-only selections, both inherited and complementary selectors, checked on the actual CUDA backend. Same frozen package as trained quality evaluation. Targets/geometry never loaded, no model/readout/parent/DINO calls, no source/noise draws or updates. Require every integer bin and validity mask exact; never alter or repair a closed choice. This verification follows existing scoring/quality interpretation, not a new independent discovery experiment.",
    }
    write_json(root / "plan.json", plan)
    verify_plan(plan)
    return root / "plan.json"


def run(root):
    import torch

    from demosaic.cfa import mosaic
    from demosaic.competing_phase import competing_phase_bins, exclude_nearby_bins
    from demosaic.experiments.evaluation.native import load_native
    from demosaic.late_innovation_wave import innovation_phase_bins
    from demosaic.prediction_archive import fingerprint

    plan = read_json(root / "plan.json")
    verify_plan(plan)
    assert reference(__file__) == plan["script"]
    (root / "worker.claim").open("x").close()
    write_json(root / "owner.json", owner_identity())
    os.nice(10)
    allowed = sorted(os.sched_getaffinity(0))
    os.sched_setaffinity(0, allowed[-2:])
    policy = RuntimePolicy(**plan["runtime"])
    policy.resources(root)
    policy.apply()
    closed = read_json(checked(plan["selections"]))
    prior = read_json(checked(plan["prior"]))
    previous = {(r["profile"], r["index"]): r for r in prior["rows"]}
    counts = {
        "batches": 0,
        "selector_calls": 0,
        "integer_coordinates": 0,
        "validity_values": 0,
        "exact_field_channels": 0,
        "model_constructions": 0,
        "neural_forwards": 0,
    }

    def forbidden(*args, **kwargs):
        raise RuntimeError("No neural construction or forward permitted in carrier verification")

    torch.nn.Module.__init__ = forbidden
    torch.nn.Module._call_impl = forbidden
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state().clone()
    began = time.monotonic()
    try:
        with (root / "checks.jsonl").open("x") as journal, torch.inference_mode():
            for row in closed["rows"]:
                assert time.monotonic() - began < plan["maximum_seconds"]
                policy.resources(root)
                old = previous[row["profile"], row["index"]]
                assert row["arrays"] == old["arrays"]
                with np.load(checked(row["arrays"]), allow_pickle=False) as data:
                    packed, variance, colors = [
                        torch.from_numpy(data[k]).cuda() for k in ["packed", "variance", "colors"]
                    ]
                fields = []
                for entry in [old, row]:
                    anchor = torch.from_numpy(load_native(entry["anchor"])).cuda()
                    field = packed - mosaic(anchor, colors)
                    assert fingerprint(field.cpu().numpy()) == entry["field"]
                    counts["exact_field_channels"] += field.numel()
                    fields.append(field)
                bins, valid, _ = innovation_phase_bins(fields[0], variance, colors)
                extra, proposed, _ = competing_phase_bins(fields[1], variance, colors)
                accepted = exclude_nearby_bins(extra, proposed, bins, valid, fields[1].shape[-2:])
                for actual, mask, name in [
                    (bins, valid, "current"),
                    (extra, accepted, "additional-only"),
                ]:
                    choice = row["choices"][name]
                    assert torch.equal(actual.cpu(), torch.tensor(choice["bins_yx"]))
                    assert torch.equal(mask.cpu(), torch.tensor(choice["valid"]))
                    counts["integer_coordinates"] += actual.numel()
                    counts["validity_values"] += mask.numel()
                    counts["selector_calls"] += 1
                counts["batches"] += 1
                journal.write(
                    json.dumps(
                        {
                            "profile": row["profile"],
                            "index": row["index"],
                            "integer_bins_and_masks_exact": True,
                        }
                    )
                    + "\n"
                )
                journal.flush()
                if counts["batches"] % 16 == 0:
                    write_json(
                        root / "progress.json", dict(owner=owner_identity(), **counts), replace=True
                    )
                    print(counts["batches"], "of384 exact", flush=True)
        assert counts["batches"] == 384 and counts["selector_calls"] == 768
        assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
            cuda_rng, torch.cuda.get_rng_state()
        )
        verify_plan(plan)
        write_json(
            root / "result.json",
            {
                "status": "all-closed-choices-exact-on-CUDA",
                "plan": reference(root / "plan.json"),
                "counts": counts,
                "checks": reference(root / "checks.jsonl"),
                "RNG_unchanged": True,
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "elapsed_seconds": time.monotonic() - began,
                "new_source_noise_draws": 0,
                "new_parent_DINO_forwards": 0,
                "optimizer_updates": 0,
                "scope": plan["scope"],
            },
        )
    except BaseException as error:
        write_json(
            root / "failure.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "error": repr(error),
                "counts": counts,
                "plan": reference(root / "plan.json"),
            },
        )
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        print(prepare(args.root.resolve()))
    else:
        run(args.root.resolve())
