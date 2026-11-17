"""Test agreement between independently fitted phase profiles as a delivery weight."""

import argparse
import os
from pathlib import Path

from probe_fold_support_pooling import THRESHOLDS, prepare
from probe_phase_fit_shrinkage import collect

from demosaic.local_validated_waves import restore_local_waves

SCOPE = (
    "Compare pooled support with the same pooled correction multiplied per color and direction"
    " by the positive part of the signed cosine of independent phase profiles. Leave RAW scores,"
    " fold veto, nuisance, guides, fits, thresholds, discovery shrinkage and parent unchanged."
    " Same 384 query views and eight GFX windows. Reproduce pooled threshold 2 on every view."
    " Shared quiet-budget analyses adopt exact earlier pooled moments."
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
        compare_phase_agreement=True,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=THRESHOLDS,
    )
    outputs = {f"agreement-t{t:g}": values["phase-agreement", t] for t in THRESHOLDS}
    outputs["pooled-t2"] = values["pooled-local", 2]
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
            driver=Path(__file__).name,
            reporter="report_phase_agreement.py",
            scope=SCOPE,
        )
    else:
        collect(args.path.resolve(), restore_view=restore, driver=__file__)
