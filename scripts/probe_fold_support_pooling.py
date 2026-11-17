"""Compare minimum and pooled predictive support on the same phase fits."""

import argparse
import os
from pathlib import Path

import numpy as np
from probe_phase_fit_shrinkage import collect

from demosaic.experiments.artifacts import freeze_sources, read_json, reference, write_json
from demosaic.local_validated_waves import restore_local_waves

THRESHOLDS = (0.0, 0.25, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0)
SCOPE = (
    "Compare minimum and mean positive predictive support on the same shrunken"
    " phase fit, using eight fixed score thresholds on all 384 retained query views"
    " and eight real cases. Threshold zero agrees exactly between modes. Three fixed"
    " excess quiet RMS budgets are calibrated leave-one-geometry-out. Threshold 2 is"
    " shown on the standing camera crops with the same parent, ROI and display."
)


def prepare(
    root,
    source,
    *,
    driver="probe_fold_support_pooling.py",
    reporter="report_fold_support_pooling.py",
    scope=SCOPE,
):
    plan = read_json(source / "plan.json")
    closure_path = source / "output/collection.json"
    closed = read_json(closure_path)
    assert closed["plan"] == reference(source / "plan.json") and closed["query_roles"] == 384
    assert len(closed["synthetic"]) == 128 and len(closed["camera"]) == 8
    root.mkdir()
    work, files = freeze_sources(
        Path.cwd(),
        root,
        [driver, reporter],
    )
    write_json(
        root / "plan.json",
        {
            **plan,
            "root": str(root),
            "work": str(work),
            "frozen_files": files,
            "driver": reference(work / "scripts" / driver),
            "adopted_plan": reference(source / "plan.json"),
            "adopted_collection": reference(closure_path),
            "adopted_report": reference(source / "review/result.json"),
            "inputs": [
                *plan["inputs"],
                reference(closure_path),
                reference(source / "plan.json"),
                reference(source / "review/result.json"),
            ],
            "thresholds": THRESHOLDS,
            "positive_quiet_RMS_budgets_DN16": [0.02, 0.1, 0.3],
            "scope": scope,
        },
    )


def restore(parent, packed, colors, frequencies, noise, config):
    restored, statistics = restore_local_waves(
        parent,
        packed,
        colors,
        guide_frequencies_xy=frequencies,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=THRESHOLDS,
    )
    np.testing.assert_array_equal(restored["local", 0], restored["pooled-local", 0])
    outputs = {
        f"{name}-t{t:g}": restored[mode, t]
        for name, mode in (("minimum", "local"), ("pooled", "pooled-local"))
        for t in THRESHOLDS
        if t or name == "minimum"
    }
    assert all(v.shape == parent.shape and np.isfinite(v).all() for v in outputs.values())
    return outputs, statistics


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
