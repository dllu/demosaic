"""Reuse the two predeclared native mesh geometries for a completed head trial."""

import argparse
from pathlib import Path

import numpy as np
from audit_mesh_orientation_response import reference as spatial_reference
from mesh_orientation_response import project

from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.experiments.evaluation.native import load_native


def breakdown(run, previous, output):
    result = read_json(run / "result.json")
    if result["status"] != "evaluated-awaiting-native-viewing":
        raise ValueError("Expected completed matched review")
    prior = read_json(previous)
    rows, maximum = [], 0.0
    for state in ["raw", "ema"]:
        scores = read_json(checked(result["scores"][state]))
        indexed = {r["id"]: r for r in scores["rows"]}
        retained = [r for r in prior["rows"] if r["state"] == state]
        if len(retained) != 2:
            raise ValueError("Expected the same two predeclared V200 examples")
        for old in retained:
            case = next(
                f["case"]
                for f in read_json(checked(result["figures"]))["images"]
                if f["case"]["id"] == old["id"]
            )
            binding = scores["native_predictions"][old["id"]]
            with np.load(checked(case["arrays"]), allow_pickle=False) as a:
                present, empty = [
                    a[k][0].astype(np.float64) for k in ["target_present", "target_empty"]
                ]
            value = load_native(binding)[0].astype(np.float64)
            angles = old["geometry"]["native_normals_radians"]
            actual = project(value, present, empty, angles)
            whole, expected = spatial_reference(value, present, empty, angles)
            np.testing.assert_allclose(actual["whole_template_gain"], whole, rtol=0, atol=2e-12)
            np.testing.assert_allclose(
                whole, indexed[old["id"]]["template_gain"], rtol=0, atol=2e-12
            )
            for a, b in zip(actual["sectors"], expected, strict=True):
                for key in [
                    "gain",
                    "template_energy_fraction",
                    "template_energy",
                    "projection_numerator",
                ]:
                    np.testing.assert_allclose(a[key], b[key], rtol=2e-8, atol=2e-12)
                maximum = max(maximum, abs(a["gain"] - b["gain"]))
            rows.append(
                dict(
                    id=old["id"],
                    method="competing-" + state,
                    prediction=binding,
                    geometry=old["geometry"],
                    **actual,
                )
            )
    write_json(
        output,
        {
            "status": "pass-four-closed-candidate-projections-and-independent-spatial-checks",
            "result": reference(run / "result.json"),
            "previous": reference(previous),
            "rows": rows,
            "maximum_region_gain_difference": maximum,
            "sector_scalar_checks": 48,
            "whole_metric_bridges": 4,
            "new_neural_forwards": 0,
            "new_noise_source_draws": 0,
            "script": reference(__file__),
            "scope": "Same two predeclared native512 RGGB cases and recipe-normal spectral sectors. Envelope/harmonic/intersection leakage remains; not isolated wire-family amplitudes, independent sources or population quality. No protected input or real-reference scoring.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("previous", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    breakdown(args.run.absolute(), args.previous.absolute(), args.output.absolute())
