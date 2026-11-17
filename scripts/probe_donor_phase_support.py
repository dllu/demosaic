"""Test whether a separate RAW region can select query waveform harmonics."""

import argparse
import os
from pathlib import Path

import numpy as np
from probe_fold_support_pooling import THRESHOLDS
from probe_oriented_raw_support import prepare
from probe_phase_fit_shrinkage import collect

from demosaic.donor_phase_support import FUNDAMENTAL, PHASE_BINS, donor_harmonic_scores
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves

SCOPE = (
    "Compare unrestricted eight-knot phase profiles, the fundamental alone, and higher"
    " harmonics supported by an entirely disjoint donor RAW region. A donor harmonic"
    " must reach score 3 in both folds with all other modes in its null. Queries use the"
    " same corrected frequencies, fits of nuisance, independent color coefficients,"
    " discovery shrinkage, pooled fold scores and square support. The donor supplies only"
    " basis indices, so query phase and amplitude are unconstrained within each."
    " All 384 query views and eight GFX cases. Eight thresholds and held-out quiet budgets."
)
DONOR_THRESHOLD = 3.0


def assess_donors(path):
    plan = read_json(path)
    original = read_json(checked(plan["donor_assessment"]))
    config = LocalWaveConfig(**plan["config"])
    assessment = {}
    for domain in ("synthetic", "camera"):
        assessment[domain] = {}
        for key, entry in original[domain].items():
            with np.load(checked(entry["donor"])) as data:
                if domain == "synthetic":
                    packed, colors = data["packed"], data["colors"]
                else:
                    x, y, w, h = entry["donor_box"]
                    assert all(v % 2 == 0 for v in (x, y, w, h))
                    packed = data["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
                    colors = data["colors"][0]
            native = np.empty((2 * packed.shape[1], 2 * packed.shape[2]), dtype=np.float64)
            for i in range(4):
                native[i // 2 :: 2, i % 2 :: 2] = packed[i]
            layout = np.tile(colors.reshape(2, 2), packed.shape[1:])
            scores = donor_harmonic_scores(
                native,
                layout,
                entry["revised"],
                shot=entry["noise"]["shot"],
                read=entry["noise"]["read"],
                config=config,
            )
            pass_both = (scores >= DONOR_THRESHOLD).all(axis=0)
            orders = [
                [1, *(i for i, accept in enumerate(row, start=2) if accept)] for row in pass_both
            ]
            assessment[domain][key] = {
                "donor": entry["donor"],
                "donor_box": entry.get("donor_box"),
                "noise": entry["noise"],
                "frequencies": entry["revised"],
                "fold_by_direction_by_higher_harmonic": scores.tolist(),
                "orders": orders,
            }
    write_json(
        path.parent / "donor-harmonic-assessment.json",
        {
            "plan": reference(path),
            "driver": reference(__file__),
            "source": plan["donor_assessment"],
            "minimum_in_each_fold": DONOR_THRESHOLD,
            "higher_harmonics": [2, 3, 4],
            **assessment,
        },
    )
    return assessment


def restore(parent, packed, colors, specification, noise, config):
    frequencies, selected = specification
    variants = {"square": None, "fundamental": FUNDAMENTAL, "donor-basis": selected}
    outputs, stats, fitted = {}, {}, {}
    for name, orders in variants.items():
        if orders not in fitted:
            fitted[orders] = restore_local_waves(
                parent,
                packed,
                colors,
                guide_frequencies_xy=frequencies,
                phase_bins=PHASE_BINS,
                phase_harmonics=orders,
                shrink_phase_fit=True,
                compare_pooled_support=True,
                shot=noise["shot"],
                read=noise["read"],
                config=config,
                thresholds=(2,) if name == "square" else THRESHOLDS,
            )
        values, stats[name] = fitted[orders]
        outputs.update(
            {f"{name}-t{t:g}": a for (mode, t), a in values.items() if mode == "pooled-local"}
        )
    return outputs, stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--adopt", type=Path)
    args = parser.parse_args()
    path = args.path.resolve()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    if args.adopt:
        prepare(
            path,
            args.adopt.resolve(),
            driver=__file__,
            reporter="report_donor_phase_support.py",
            scope=SCOPE,
        )
    else:
        assessment = assess_donors(path)

        def select_guide(row, key):
            donor = (
                assessment["synthetic"][row["guide_key"]]
                if key == "frequencies"
                else assessment["camera"][row["id"]]
            )
            assert donor["frequencies"] == row[key]
            return row[key], tuple(tuple(v) for v in donor["orders"])

        collect(path, restore_view=restore, driver=__file__, select_guide=select_guide)
