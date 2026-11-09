"""Audit saved gate crops with independent energy identities; no neural calls."""

import math

import numpy as np
from diagnose_cfa_wave_gates import ROOT
from directional_trial_protocol import guard, read, ref, save
from lossless_native import fingerprint, load_native
from phase_admission_protocol import owner_live
from readout_gate_interventions import POLICIES, local_intervention


def norm_stats(value):
    a = value.astype(np.float64)
    energy = float(np.square(a).sum(dtype=np.float64)) / a.size
    means = a.mean((-2, -1))
    spatial = max(0, energy - float(np.mean(means**2)))
    gray = a.mean(1, keepdims=True)
    orthogonal = max(0, energy - float(np.mean(gray**2)))
    return {
        "RMS_DN16": math.sqrt(energy) * 65535,
        "spatial_RMS_DN16": math.sqrt(spatial) * 65535,
        "equal_RGB_orthogonal_RMS_DN16": math.sqrt(orthogonal) * 65535,
    }


def audit():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert ref(__file__) == plan["auditor"]
    result = read(ROOT / "result-v1.json")
    assert result["owner"] == read(ROOT / "run-launch-v1.json")["owner"] and not owner_live(
        result["owner"]
    )
    assert not (ROOT / "run-failure-v1.json").exists()
    assert result["isolated_module_calls"] == {"head": 28, "context": 28, "gates": 28}
    assert (
        result["RNG_unchanged"]
        and not result["CUDA_initialized"]
        and result["optimizer_steps"] == 0
    )
    assert result["full_anchor_matching_parent_DINO_forwards"] == 0
    assert (
        len(result["rows"]) == 196
        and len(result["observations"]) == 28
        and len(result["crop_artifacts"]) == 19
    )
    observations = {(o["case"], o["state"]): o for o in result["observations"]}
    rows = {(r["case"], r["state"], r["policy"]): r for r in result["rows"]}
    assert len(rows) == 196 and {r["policy"] for r in rows.values()} == set(POLICIES)
    displays = {d["index"]: d for d in plan["displays"]}
    channels = scalar_checks = matches = 0
    for artifact in result["crop_artifacts"]:
        assert ref(artifact["arrays"]["path"]) == artifact["arrays"]
        with np.load(artifact["arrays"]["path"], allow_pickle=False) as archive:
            bundle = dict(archive)
        assert {k: fingerprint(v) for k, v in bundle.items()} == artifact["fingerprints"]
        d = displays[artifact["display"]]
        case = d["case"]["id"]
        x, y, w, h = d["ROI_xywh"]
        assert bundle["basis"].shape == (1, 8, 3, 160, 160)
        assert bundle["mask"].shape == (1, 1, 160, 160) and bundle["mask"].dtype == np.bool_
        for state in ["raw", "EMA"]:
            o = observations[case, state]
            actual = load_native(o["actual_wave"])[..., y : y + h, x : x + w]
            rebuilt = local_intervention(bundle, state, "actual", o["constants"])
            np.testing.assert_allclose(rebuilt, actual, **plan["wave_tolerance"])
            channels += actual.size
            for policy in POLICIES:
                row = rows[case, state, policy]
                wave = (
                    actual
                    if policy == "actual"
                    else local_intervention(
                        bundle, state, policy, o["constants"], row["normalization"]["scale"]
                    )
                )
                expected = next(r for r in row["rois"] if r["display"] == d["index"])
                for key, value in norm_stats(wave).items():
                    assert abs(value - expected[key]) < 1e-6, (
                        case,
                        state,
                        policy,
                        key,
                        value,
                        expected[key],
                    )
                    scalar_checks += 1
                if policy.endswith("-RMS") and row["normalization"]["possible"]:
                    assert np.isclose(
                        row["whole_correction"]["RMS_DN16"],
                        row["normalization"]["reference_RMS_DN16"],
                        rtol=2e-6,
                        atol=1e-8,
                    )
                    matches += 1
    for name, digest in plan["all105_neural_hashes"].items():
        from directional_trial_protocol import REPO

        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    save(
        ROOT / "audit-v1.json",
        {
            "status": "pass-saved19native-gate-bundles-independent-ROI-energies-and-RMS-controls",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "independent_native_reconstruction_channels": channels,
            "independent_ROI_energy_checks": scalar_checks,
            "RMS_control_ROI_checks": matches,
            "new_neural_forwards": 0,
            "scope": "Independent cropped-basis reconstruction and energy/variance identities. Original28CPUheads already checked against evaluated GPU waves. Whole-case counterfactual metrics are source-bound single-pass measurements,not independently rerun or population-quality evidence. No training,new data/noise or RAW decode.",
            "source": ref(__file__),
        },
    )
    print(
        "PASS19nativebundles/",
        channels,
        "reconstructionchannels/",
        scalar_checks,
        "ROIenergies/",
        matches,
        "RMScontrols",
    )


if __name__ == "__main__":
    audit()
