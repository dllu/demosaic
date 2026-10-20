"""Independent NumPy replay of saved execution diagnostics; no model inference."""

import argparse
import os
from pathlib import Path

import numpy as np
from qualify_mature_precision import alive
from train_directional_bank_trial import guard, read, ref, save


def main(plan_path, output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    terminal = root / "controller-status.json"
    status = read(terminal)
    assert status["status"] == "completed-execution-diagnostics-awaiting-review"
    assert status["completed"] == plan["arms"] and status["plan"] == ref(plan_path)
    assert not any(alive(status[k]) for k in ("controller", "child"))
    prior = {k: np.load(v["path"], allow_pickle=False) for k, v in plan["pilot_RGB"].items()}
    summaries, evidence = [], []
    audited_values, actual_forwards, max_error = 0, 0, 0.0
    for arm in plan["arms"]:
        path = root / "outputs" / arm / "receipt.json"
        receipt = read(path)
        evidence.append(ref(path))
        assert receipt["plan"] == ref(plan_path) and receipt["arm"] == arm
        assert receipt["backend_settings_restored"] and not alive(receipt["owner"])
        invariant = receipt["invariants"]
        forwards = 13 if arm.startswith("history") else 4
        assert (
            invariant["actual_forwards"]
            == invariant["encoder_calls"]
            == invariant["five_physical_argument_boundaries"]
            == forwards
        )
        assert invariant["policy_observations"] == 4 * forwards
        assert invariant["model_sha256"] == plan["expected_model"]
        assert invariant["DINO_sha256"] == plan["expected_DINO"]
        assert invariant["original_state_config_parameters_RNG_exact"]
        rows = receipt["captures"]
        assert len(rows) == forwards and len({(r["label"], r["policy"]) for r in rows}) == forwards
        assert sum(r["label"].startswith("history") for r in rows) == forwards - 4
        first, comparisons = {}, []
        for row in rows:
            item = row["RGB"]
            assert ref(item["path"]) == item
            values = np.load(item["path"], allow_pickle=False)
            assert values.dtype == np.float32 and values.shape == (4, 3, 512, 512)
            assert np.isfinite(values).all()
            audited_values += values.size
            policy = row["policy"]

            def compare(reference, saved, values=values):
                nonlocal max_error
                difference = values.astype(np.float64) - reference.astype(np.float64)
                assert len(saved) == len(difference)
                checked = []
                for delta, recorded in zip(difference, saved, strict=True):
                    measured = {
                        "RGB_values": delta.size,
                        "max_abs_DN16": float(np.max(np.abs(delta))) * 65535,
                        "RMS_DN16": float(np.sqrt(np.mean(delta * delta))) * 65535,
                    }
                    for key, number in measured.items():
                        error = abs(number - recorded[key])
                        max_error = max(max_error, error)
                        assert error <= 1e-9
                    checked.append(measured)
                return checked

            measured = compare(prior[policy], row["versus_matching_pilot"])
            passed = all(r["max_abs_DN16"] <= 1 and r["RMS_DN16"] <= 0.25 for r in measured)
            assert passed == row["pilot_parity_pass"]
            same = None
            if policy in first:
                compare(first[policy], row["versus_first_same_process"])
                same = first[policy].tobytes() == values.tobytes()
                assert same == row["first_same_process_bytes_exact"]
            else:
                first[policy] = values
            comparisons.append(
                {
                    "label": row["label"],
                    "policy": policy,
                    "RGB": item,
                    "matching_pilot_pass": passed,
                    "max_abs_DN16": max(r["max_abs_DN16"] for r in measured),
                    "max_crop_RMS_DN16": max(r["RMS_DN16"] for r in measured),
                    "same_process_bytes_exact": same,
                }
            )
        summaries.append({"arm": arm, "actual_forwards": forwards, "captures": comparisons})
        actual_forwards += forwards
    assert actual_forwards == 34 and audited_values == 106954752
    guard(plan)
    output.mkdir(parents=True, exist_ok=False)
    save(
        output / "independent-audit.json",
        {
            "status": "completed-independent-execution-difference-audit",
            "executed_source": ref(__file__),
            "plan": ref(plan_path),
            "terminal": ref(terminal),
            "receipts": evidence,
            "actual_forwards": actual_forwards,
            "audited_RGB_values": audited_values,
            "max_scalar_replay_error_DN16": max_error,
            "arms": summaries,
            "scope": "Independent NumPy float64 replay of all saved physical differences and SHA/byte identities. Diagnostic comparisons only, without new inference, quality-population metrics, timing claims, parity relaxation, full-frame continuation or production adoption.",
        },
    )
    print(ref(output / "independent-audit.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    main(args.plan.resolve(), args.output.resolve())
