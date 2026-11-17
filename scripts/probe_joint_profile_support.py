"""Compare per-color and joint Bayer evidence for locally fitted phase profiles."""

import argparse
import os
from pathlib import Path

from probe_fold_support_pooling import THRESHOLDS
from probe_oriented_raw_support import prepare
from probe_phase_fit_shrinkage import collect

from demosaic.local_validated_waves import restore_local_waves

SCOPE = (
    "Compare per-color and joint held-out RAW evidence with and without a per-color veto."
    " Pool actual Bayer samples after accounting for discovery reliability and RAW noise."
    " Use the same phase fits, disjoint folds, square footprints, parents and corrected guides."
    " All 384 synthetic views and 8 GFX cases. Sweep the same eight thresholds."
    " Report fixed t2 crops and leave-one-geometry-out quiet-budget results."
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
        compare_joint_colour_support=True,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=THRESHOLDS,
    )
    out = {
        f"{mode}-t{t:g}": values[mode, t] for mode in ("joint", "joint-veto") for t in THRESHOLDS
    }
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
        prepare(
            args.path.resolve(),
            args.adopt.resolve(),
            driver=__file__,
            reporter="report_joint_profile_support.py",
            scope=SCOPE,
        )
    else:
        collect(args.path.resolve(), restore_view=restore, driver=__file__)
