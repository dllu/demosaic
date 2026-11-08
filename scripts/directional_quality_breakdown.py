"""Repeat the pre-existing two-example V194 diagnostic on V195 saved predictions."""

import argparse
import sys
import time

import numpy as np
from audit_mesh_orientation_response import reference
from directional_trial_protocol import MODES, REPO, TRIAL, freeze, guard, read, ref, save
from lossless_native import load_native
from mesh_orientation_response import project
from phase_admission_protocol import owner_live

ROOT = TRIAL / "directional-breakdown-v2"
PREVIOUS = REPO / ".cache/quality-20261108/V194-orientation-response-v1"


def prepare():
    plan = read(TRIAL / "plan-v1.json")
    guard(plan)
    old = read(PREVIOUS / "plan-v2.json")
    assert not ROOT.exists()
    ROOT.mkdir()
    work, sources = freeze(ROOT, ["directional_quality_breakdown.py"])
    prepared = {
        "status": "prepared-same-two-directional-examples-four-new-endpoints-no-quality-yet",
        "created_unix_UTC": time.time(),
        "runner": ref(work / "scripts/directional_quality_breakdown.py"),
        "frozen_files": sources,
        "training_plan": ref(TRIAL / "plan-v1.json"),
        "previous_plan": ref(PREVIOUS / "plan-v2.json"),
        "previous_result": ref(PREVIOUS / "result-v1.json"),
        "previous_audit": ref(PREVIOUS / "audit-v1.json"),
        "methods": [m for mode in MODES for m in plan["methods"][mode].values()],
        "cases": [{"case": item["case"], "geometry": item["geometry"]} for item in old["cases"]],
        "scope": "Exactly the same two V194 native development examples and transported recipe normals; four future saved V195 endpoints. Full-context affine-detrended Fourier-region gains, independently checked using real spatial projectors. Envelope/harmonic/intersection leakage remains; not isolated wire-family amplitudes, independent confidence, population quality or flat safety. No neural work, target inference features, new noise/source draws or RAW decode. No new large array outputs.",
    }
    prepared["inputs"] = [
        prepared[k] for k in ["training_plan", "previous_plan", "previous_result", "previous_audit"]
    ]
    prepared["inputs"] += [item["case"]["arrays"] for item in prepared["cases"]]
    save(ROOT / "plan-v1.json", prepared)
    print("Prepared same two fixed directional examples / four saved endpoints")


def run():
    plan = read(ROOT / "plan-v1.json")
    guard(plan, __file__)
    scores = read(TRIAL / "scores-v1.json")
    assert not owner_live(scores["owner"])
    assert scores["status"] == "completed-V195-four-endpoint-quality-awaiting-native-viewing"
    assert read(TRIAL / "quality-audit-v1.json")["status"].startswith("pass-V195-four-endpoint")
    (ROOT / "run.claim").open("x").close()
    score_rows = {(r["id"], r["method"]): r for r in scores["rows"]}
    rows = []
    maximum = 0.0
    for item in plan["cases"]:
        case, geometry = item["case"], item["geometry"]
        with np.load(case["arrays"]["path"], allow_pickle=False) as arrays:
            present, empty = [
                arrays[k][0].astype(np.float64) for k in ["target_present", "target_empty"]
            ]
        angles = geometry["native_normals_radians"]
        for method in plan["methods"]:
            binding = scores["native_predictions"][case["id"]][method]
            value = load_native(binding)[0].astype(np.float64)
            actual = project(value, present, empty, angles)
            whole, expected = reference(value, present, empty, angles)
            assert abs(actual["whole_template_gain"] - whole) < 2e-12
            assert abs(whole - score_rows[case["id"], method]["template_gain"]) < 2e-12
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
            print(
                case["id"],
                method,
                actual["whole_template_gain"],
                [s["gain"] for s in actual["sectors"][:2]],
                flush=True,
            )
    assert len(rows) == 8 and "torch" not in sys.modules
    previous = read(plan["previous_result"]["path"])
    context = [
        row
        for row in previous["rows"]
        if row["method"]
        in [
            "V183-coherent-pair-EMA",
            "V187-pooled-wave-raw",
            "V187-pooled-wave-EMA",
            "V193-large-dense-EMA",
        ]
    ]
    assert len(context) == 8
    save(
        ROOT / "result-v1.json",
        {
            "status": "pass-eight-new-native-directional-projections-independent-spatial-checks",
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v1.json"),
            "scores": ref(TRIAL / "scores-v1.json"),
            "rows": rows,
            "previous_context_rows": context,
            "maximum_region_gain_difference": maximum,
            "sector_scalar_checks": 96,
            "whole_metric_bridges": 8,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "Torch_imported": False,
            "scope": plan["scope"],
        },
    )
    print("PASS: eight new projections /96 region scalars /eight whole-gain bridges")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "run"])
    prepare() if parser.parse_args().phase == "prepare" else run()
