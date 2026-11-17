"""Compare square, along-wire and across-wire held-out RAW support."""

import argparse
import os
from pathlib import Path

from probe_fold_support_pooling import THRESHOLDS
from probe_phase_fit_shrinkage import collect

from demosaic.experiments.artifacts import checked, freeze_sources, read_json, reference, write_json
from demosaic.local_validated_waves import restore_local_waves


def prepare(root, source):
    plan_path, collection, report = (
        source / name for name in ("plan.json", "output/collection.json", "review/result.json")
    )
    plan, closed = read_json(plan_path), read_json(collection)
    assert closed["plan"] == reference(plan_path)
    assert closed["synthetic_roles_refit"] + closed["synthetic_roles_adopted"] == 384
    donor = read_json(checked(plan["donor_assessment"]))
    root.mkdir()
    work, files = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_oriented_raw_support.py"]
    )
    write_json(
        root / "plan.json",
        {
            **plan,
            "root": str(root),
            "work": str(work),
            "frozen_files": files,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "adopted_plan": reference(plan_path),
            "adopted_collection": reference(collection),
            "adopted_report": reference(report),
            "inputs": [
                *plan["inputs"],
                reference(plan_path),
                reference(collection),
                reference(report),
            ],
            "groups": [
                {**group, "frequencies": donor["synthetic"][group["guide_key"]]["revised"]}
                for group in plan["groups"]
            ],
            "camera_cases": [
                {**case, "guide": donor["camera"][case["id"]]["revised"]}
                for case in plan["camera_cases"]
            ],
            "scope": "Compare equal continuous area support footprints: original square, two-to-one"
            " rectangles along and across the revised guides. Native lattice, no rotation of"
            " image data. Same fits, disjoint folds, predictor, parent and correction."
            " All 384 synthetic views and 8 GFX cases. Sweep the same eight thresholds;"
            " report fixed t2 crops and leave-one-geometry-out quiet-budget results.",
        },
    )


def restore(parent, packed, colors, frequencies, noise, config):
    values, stats = restore_local_waves(
        parent,
        packed,
        colors,
        guide_frequencies_xy=frequencies,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_oriented_support=True,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=THRESHOLDS,
    )
    out = {f"{mode}-t{t:g}": values[mode, t] for mode in ("along", "across") for t in THRESHOLDS}
    out["square-t2"] = values["pooled-local", 2]
    return out, stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--adopt", type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    if args.adopt:
        prepare(args.path.resolve(), args.adopt.resolve())
    else:
        collect(args.path.resolve(), restore_view=restore, driver=__file__)
