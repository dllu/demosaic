"""Native RGB views of the restricted analytic CFA diagnostic, with exact GT."""

import argparse
from pathlib import Path

import numpy as np
import torch
from diagnose_withheld_cfa import make_scene
from PIL import Image

from demosaic.cfa import color_indices, malvar
from demosaic.experiments.artifacts import read_json, reference, write_json
from demosaic.experiments.evaluation.crops import display_pixels, write_triplet
from demosaic.experiments.evaluation.withheld import (
    fit_candidate,
    geometry,
    stratified_split,
    validate_candidate,
)
from demosaic.prediction_archive import fingerprint


def rgb_fit(candidate, raw, colors):
    """Evaluate the same per-color A-only least-squares coefficients off sensor sites."""
    xx, yy, basis, _ = geometry(raw.shape)
    if candidate.edge_geometry is not None:
        angle, offset = candidate.edge_geometry
        x, y = 2 * (xx + 0.5) / raw.shape[1] - 1, 2 * (yy + 0.5) / raw.shape[0] - 1
        basis = np.column_stack((basis, (x * np.cos(angle) + y * np.sin(angle) > offset).ravel()))
    waves = []
    for fx, fy in candidate.frequencies_xy:
        phase = 2 * np.pi * (xx * fx + yy * fy)
        waves.extend((np.cos(phase).ravel(), np.sin(phase).ravel()))
    design = np.column_stack((basis, *waves))
    base, full = [], []
    for color in range(3):
        selected = ((colors == color) & candidate.discovery_mask).ravel()
        values = raw.ravel()[selected]
        base.append(
            (basis @ np.linalg.lstsq(basis[selected], values, rcond=1e-10)[0]).reshape(raw.shape)
        )
        full.append(
            (design @ np.linalg.lstsq(design[selected], values, rcond=1e-10)[0]).reshape(raw.shape)
        )
    base, full = np.stack(base), np.stack(full)
    y, x = np.mgrid[: raw.shape[0], : raw.shape[1]]
    np.testing.assert_allclose(base[colors, y, x], candidate.background, rtol=0, atol=2e-15)
    np.testing.assert_allclose(full[colors, y, x], candidate.prediction, rtol=0, atol=2e-15)
    return base, full


def render(comparison, output):
    document = read_json(comparison)
    output.mkdir(parents=True, exist_ok=False)
    identity = output / "analytic-model.json"
    write_json(
        identity,
        {
            "kind": "analytic configurations; no trained checkpoint",
            "comparison": reference(comparison),
            "implementation": reference(
                Path(__file__).resolve().parents[1]
                / "src/demosaic/experiments/evaluation/withheld.py"
            ),
            "rgb_evaluation": reference(__file__),
            "refinements": {"grid": 0, "refined": 3},
            "threshold_policy": "calibration-null-maximum",
            "thresholds": document["thresholds"],
        },
    )
    calibration = {"wb": np.ones((1, 3)), "matrix": np.eye(3)[None]}
    figures = []
    torch.set_num_threads(1)
    for index in range(2):
        seed = 202611160200 + 60000 + index
        target, _, _, colors = make_scene("two-wave-edge-offgrid", 128, seed)
        rng = np.random.default_rng(seed * 100)
        raw = rng.poisson(target / 0.00128) * 0.00128 + rng.normal(
            0, (6.5536e-6) ** 0.5, target.shape
        )
        mask = stratified_split(raw.shape, seed)
        predictions = {}
        for method, refinements in (("grid", 0), ("refined", 3)):
            bases, values, scores = [], [], []
            for subset in (mask, ~mask):
                candidate = fit_candidate(
                    raw,
                    colors,
                    subset,
                    shot=0.00128,
                    read=6.5536e-6,
                    nuisance="step",
                    edge_refinements=refinements,
                )
                base, full = rgb_fit(candidate, raw, colors)
                bases.append(base)
                values.append(full)
                scores.append(validate_candidate(candidate, raw, ~subset)["validation_z"])
            active = min(scores) > document["thresholds"][method]
            predictions[method] = (
                np.mean(bases, axis=0)[None]
                + active * np.mean(np.asarray(values) - bases, axis=0)[None]
            )
        packed = np.stack([raw[y::2, x::2] for y in range(2) for x in range(2)])[None]
        noisy = malvar(
            torch.from_numpy(packed.astype(np.float32)), color_indices("RGGB")[None]
        ).numpy()
        tint = np.array([0.8, 1.0, 0.6])
        gt = target[None, None] / tint[colors][None, None] * tint[None, :, None, None]
        source = {
            "kind": "exact procedural two-wave/off-grid edge",
            "source_seed": seed,
            "noise_seed": seed * 100,
            "raw_values": fingerprint(raw),
            "first_two_sources": True,
            "context_wh": [128, 128],
            "RGB_GT_values": fingerprint(gt),
        }
        metadata = write_triplet(
            output / f"triplet-{index}.png",
            noisy,
            predictions["refined"],
            gt,
            calibration,
            roi=[16, 16, 96, 96],
            exposure=4.0,
            source=source,
            checkpoint=reference(identity),
            noise={"shot": 0.00128, "read": 6.5536e-6, "pattern": "RGGB", "ADC": False},
            reference_kind="exact-GT",
        )
        cells = [
            display_pixels(v, calibration, [16, 16, 96, 96], 4.0)
            for v in (noisy, predictions["grid"], predictions["refined"], gt)
        ]
        panel = output / f"comparison-{index}.png"
        Image.fromarray(np.concatenate(cells, axis=1)).save(panel)
        figures.append(
            {
                "triplet": metadata,
                "comparison": reference(panel),
                "comparison_columns": ["noisy Malvar", "grid", "refined", "exact-GT"],
            }
        )
    write_json(
        output / "manifest.json",
        {
            "figures": figures,
            "no_resize": True,
            "model_identity": reference(identity),
            "display": "Shared WB1/matrixI, exposure4, contrast1; native96 crop in128context",
            "scope": "Analytic RGB extension of A-only color fits, checked against every measured CFA site. "
            "Both subsets combine under the fixed rule. No GT in prediction; GT only in display/scoring. "
            "Restricted synthetic diagnostic, not neural or real-photo quality evidence.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("comparison", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    render(args.comparison, args.output)
