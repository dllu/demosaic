"""CPU-only prospective Poisson/read-noise CFA holdout versus edge leakage.

Restricted sine/step targets diagnose the estimator, not final RGB quality.
Calibration and test have disjoint scene/noise seeds; fixed threshold curves
are descriptive and do not claim formal false-positive control.
"""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import reference, write_json
from demosaic.experiments.evaluation.withheld import (
    fit_candidate,
    stratified_split,
    validate_candidate,
)


def make_scene(kind, size, seed, *, components=False):
    rng = np.random.default_rng(seed)
    y, x = np.mgrid[:size, :size]
    colors = np.array([[0, 1], [1, 2]])[y % 2, x % 2]
    tint = np.array([0.8, 1.0, 0.6])[colors]
    background = np.full((size, size), 0.02) * tint
    angle = rng.integers(12) * np.pi / 12
    offset = rng.choice(np.linspace(-0.4, 0.4, 9))
    if "offgrid" in kind:
        angle += 0.037
        offset += 0.021
    if "edge" in kind:
        edge = (2 * (x + 0.5) / size - 1) * np.cos(angle) + (2 * (y + 0.5) / size - 1) * np.sin(
            angle
        ) > offset
        background += 0.06 * tint * edge
    increment = np.zeros_like(background)
    directions = []
    if "wave" in kind:
        # Unknown phases and two unequal directions; frequencies lie on the
        # diagnostic's native grid, with no template supplied to the estimator.
        phase = rng.uniform(0, 2 * np.pi, 2)
        directions.append(0.0014 * tint * np.cos(2 * np.pi * (5 * x + 3 * y) / size + phase[0]))
        if "two" in kind:
            directions.append(
                0.0007 * tint * np.cos(2 * np.pi * (-4 * x + 7 * y) / size + phase[1])
            )
        for direction in directions:
            increment += direction
    values = (background + increment, background, increment, colors)
    return (*values, directions) if components else values


def run(output, *, scenes=8, size=128, edge_refinements=0, offgrid_waves=False):
    output.mkdir(exist_ok=False, parents=True)
    shot, read = 0.00128, 6.5536e-6
    kinds = ("flat", "edge", "edge-offgrid", "one-wave", "two-wave", "two-wave-edge")
    if offgrid_waves:
        kinds += ("two-wave-edge-offgrid",)
    rows = []
    for cohort, base_seed in (("calibration", 202611160100), ("test", 202611160200)):
        for kind_index, kind in enumerate(kinds):
            for source in range(scenes):
                source_seed = base_seed + kind_index * 10000 + source
                target, _background, increment, colors, directions = make_scene(
                    kind, size, source_seed, components=True
                )
                for repeat in range(2):
                    noise_seed = source_seed * 100 + repeat
                    rng = np.random.default_rng(noise_seed)
                    raw = rng.poisson(target / shot) * shot + rng.normal(0, read**0.5, target.shape)
                    a = stratified_split(target.shape, source_seed)
                    for nuisance in ("affine", "step"):
                        candidates, validations = [], []
                        for mask in (a, ~a):
                            candidate = fit_candidate(
                                raw,
                                colors,
                                mask,
                                shot=shot,
                                read=read,
                                nuisance=nuisance,
                                edge_refinements=edge_refinements if nuisance == "step" else 0,
                            )
                            candidates.append(candidate)
                            validations.append(validate_candidate(candidate, raw, ~mask))
                        correction = np.mean(
                            [c.prediction - c.background for c in candidates], axis=0
                        )
                        energy = np.sum(increment**2)
                        row = {
                            "cohort": cohort,
                            "kind": kind,
                            "source_seed": source_seed,
                            "noise_seed": noise_seed,
                            "repeat": repeat,
                            "nuisance": nuisance,
                            "validation": validations,
                            "min_validation_z": min(v["validation_z"] for v in validations),
                            "selected_frequencies": [c.frequencies_xy for c in candidates],
                            "selected_edges": [c.edge_index for c in candidates],
                            "selected_edge_geometry": [c.edge_geometry for c in candidates],
                            "correction_RMS_DN16": float(np.sqrt(np.mean(correction**2)) * 65535),
                            "template_gain": float(np.sum(correction * increment) / energy)
                            if energy > 0
                            else None,
                            "direction_gains": [
                                float(np.sum(correction * d) / np.sum(d**2)) for d in directions
                            ],
                        }
                        rows.append(row)
            print(cohort, kind, "complete", flush=True)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["cohort"], row["kind"], row["nuisance"]].append(row)
    curves = []
    for (cohort, kind, nuisance), group in grouped.items():
        for threshold in (0.0, 1.0, 2.0, 3.0, 4.0):
            active = np.array([r["min_validation_z"] > threshold for r in group])
            rms = np.array([r["correction_RMS_DN16"] for r in group])
            curves.append(
                {
                    "cohort": cohort,
                    "kind": kind,
                    "nuisance": nuisance,
                    "threshold": threshold,
                    "patches": len(group),
                    "sources": scenes,
                    "active_patches": int(active.sum()),
                    "activation_rate": float(active.mean()),
                    "delivered_correction_RMS_DN16": float(np.mean(rms * active)),
                    "delivered_template_gain": float(
                        np.mean(
                            [
                                (r["template_gain"] or 0) * flag
                                for r, flag in zip(group, active, strict=True)
                            ]
                        )
                    )
                    if "wave" in kind
                    else None,
                    "delivered_weak_direction_gain": float(
                        np.mean(
                            [
                                r["direction_gains"][1] * flag
                                for r, flag in zip(group, active, strict=True)
                            ]
                        )
                    )
                    if "two-wave" in kind
                    else None,
                }
            )
    write_json(
        output / "result.json",
        {
            "status": "completed-analytic-CFA-holdout-diagnostic-not-model-quality",
            "script": reference(__file__),
            "implementation": reference(
                Path(__file__).resolve().parents[1]
                / "src/demosaic/experiments/evaluation/withheld.py"
            ),
            "native_size": size,
            "pattern": "RGGB",
            "shot": shot,
            "read": read,
            "edge_refinements": edge_refinements,
            "offgrid_wave_followup": offgrid_waves,
            "rows": rows,
            "curves": curves,
            "split": "Half of each native CFA phase; reverse and require both z>t",
            "selection": "Nuisance, variance estimate, frequency, phase and amplitude use discovery subset only",
            "threshold_selection": "Fixed descriptive sweep; no thresholds chosen on validation or test",
            "reference_role": "Exact procedural targets used only to draw sensor observations and score corrections",
            "scope": "Restricted grid sines and step family; misspecified off-grid edge stress. No neural baseline, "
            "DINO, target-assisted discovery, protected photo access, RAW decoding or GPU work. "
            "Noise is independent Poisson plus Gaussian read, without ADC/clipping/correlations. "
            "Nominal z uses discovery-only plug-in variances; not calibrated probabilities. "
            "Two repeat patches share a source; source-level uncertainty is not estimated here. "
            "Wave corrections are analytic scalar CFA predictions, not a restored RGB model.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scenes", type=int, default=8)
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--edge-refinements", type=int, choices=range(4), default=0)
    parser.add_argument("--include-offgrid-waves", action="store_true")
    args = parser.parse_args()
    run(
        args.output,
        scenes=args.scenes,
        size=args.size,
        edge_refinements=args.edge_refinements,
        offgrid_waves=args.include_offgrid_waves,
    )
