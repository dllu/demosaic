"""Compare post-validation RAW refits with averaging the discovery-fold corrections."""

import argparse
import os
from pathlib import Path

from probe_fold_support_pooling import THRESHOLDS
from probe_oriented_raw_support import prepare
from probe_phase_fit_shrinkage import collect

from demosaic.local_validated_waves import restore_local_waves

SCOPE = (
    "Use the same full eight-knot fit for admission on the same two disjoint query folds."
    " For delivery, compare their existing mean with refits using all CFA samples."
    " Refit both fold-specific fixed designs either uniformly in inverse noise variance,"
    " or with an extra spatial factor of 0.25 + 0.75 times pooled support at threshold 1."
    " Preserve the fold shrinkage, direction and color gates, and thresholds for delivery."
    " All 384 synthetic views and 8 GFX cases with corrected donor frequencies. Eight fixed"
    " thresholds, leave-one-geometry-out quiet budgets and fixed threshold 2 real crops."
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
        compare_pooled_refit=True,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=THRESHOLDS,
    )
    outputs = {
        f"{mode}-t{threshold:g}": value
        for (mode, threshold), value in values.items()
        if mode in ("all-site-refit", "weighted-refit")
    }
    outputs["square-t2"] = values["pooled-local", 2]
    return outputs, stats


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
            reporter="report_phase_refit_delivery.py",
            scope=SCOPE,
        )
    else:
        collect(args.path.resolve(), restore_view=restore, driver=__file__)
