"""Same two predeclared directional examples for two saved V198 endpoints."""

import sys

import numpy as np
from audit_mesh_orientation_response import reference
from directional_trial_protocol import read, ref, save
from lossless_native import load_native
from mesh_orientation_response import project
from phase_admission_protocol import owner_live
from review_cfa_innovation_wave import review_plan, source_guard
from train_cfa_innovation_wave import MODES, ROOT


def run():
    plan = review_plan()
    seal = source_guard(plan)
    assert ref(__file__) == seal["breakdown"]
    scores = read(ROOT / "scores-v1.json")
    assert not owner_live(scores["owner"])
    assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V198-two-endpoint")
    selected = read(plan["orientation_plan"]["path"])["cases"]
    previous = read(plan["previous_breakdown"]["path"])
    methods = [method for mode in MODES for method in plan["methods"][mode].values()]
    indexed = {(r["id"], r["method"]): r for r in scores["rows"]}
    rows = []
    maximum = 0.0
    for item in selected:
        case, geometry = item["case"], item["geometry"]
        with np.load(case["arrays"]["path"], allow_pickle=False) as a:
            present, empty = [
                a[k][0].astype(np.float64) for k in ["target_present", "target_empty"]
            ]
        for method in methods:
            binding = scores["native_predictions"][case["id"]][method]
            value = load_native(binding)[0].astype(np.float64)
            actual = project(value, present, empty, geometry["native_normals_radians"])
            whole, expected = reference(value, present, empty, geometry["native_normals_radians"])
            assert abs(actual["whole_template_gain"] - whole) < 2e-12
            assert abs(whole - indexed[case["id"], method]["template_gain"]) < 2e-12
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
                {
                    "id": case["id"],
                    "method": method,
                    "prediction": binding,
                    "geometry": geometry,
                    **actual,
                }
            )
            print(case["id"], method, [r["gain"] for r in actual["sectors"][:2]], flush=True)
    context = previous["rows"] + previous["previous_context_rows"]
    assert len(rows) == 4 and len(context) == 12 and "torch" not in sys.modules
    save(
        ROOT / "directional-breakdown-v1.json",
        {
            "status": "pass-four-V198-projections-independent-spatial-checks",
            "plan": ref(ROOT / "plan-v1.json"),
            "review_source": ref(ROOT / "review-source-v1.json"),
            "scores": ref(ROOT / "scores-v1.json"),
            "rows": rows,
            "previous_context_rows": context,
            "maximum_region_gain_difference": maximum,
            "sector_scalar_checks": 48,
            "whole_metric_bridges": 4,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "Torch_imported": False,
            "scope": "Same two predeclaredV194 native512RGGB examples,transportedD4recipe normals,fullcontext affine-detrended Fourier regions withindependent realspatialprojectors. Envelope/harmonic/intersectionleakage remains;not isolatedwire-family amplitude,confidence,populationquality orflatsafety. No target inferencefeatures,newselection,noise/source,RAWdecode ororiginal/datazaccess.",
        },
    )
    print("PASS4newprojections/48sectorscalars/4wholebridges")


if __name__ == "__main__":
    run()
