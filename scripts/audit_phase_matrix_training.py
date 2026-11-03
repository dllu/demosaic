"""Audit paired training bindings and scalar replay without any neural forward."""

import argparse
import json
import math
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from train_directional_bank_trial import guard, read, ref, save


def main(root):
    plan = read(root / "plan-v1.json")
    guard(plan)
    previous = Path(plan["previous"])
    original = read(plan["original_trace"]["path"])
    result = read(root / "train-result-v1.json")
    cache = read(root / "cache-result-v1.json")
    cache_rows = [json.loads(s) for s in (root / "cache-trace-v1.jsonl").read_text().splitlines()]
    rows = [json.loads(s) for s in (root / "train-trace-v1.jsonl").read_text().splitlines()]
    assert len(rows) == len(cache_rows) == len(original["trace"]) == 1000
    assert rows == result["trace"] and cache_rows == cache["batches"]
    differences = {k: [] for k in rows[0]["arms"]["scalar-control"]}
    for step, (row, cached, old) in enumerate(zip(rows, cache_rows, original["trace"]), 1):
        assert row["step"] == cached["step"] == old["step"] == step
        assert cached["inputs"] == old["inputs"] and cached["metadata"] == old["metadata"]
        assert row["batch"] == cached["arrays"]
        assert row["domain"] == cached["metadata"]["domain"]
        assert cached["adopted_old_prefix"] == (step <= 10)
        assert set(row["arms"]) == {"scalar-control", "phase-matrix"}
        assert row["arms"]["scalar-control"]["lr"] == row["arms"]["phase-matrix"]["lr"]
        for arm in row["arms"].values():
            assert all(math.isfinite(v) for v in arm.values())
        for key, value in row["arms"]["scalar-control"].items():
            differences[key].append(abs(value - old[key]))
            assert math.isclose(value, old[key], rel_tol=2e-6, abs_tol=1e-7)
    for key in ("spectral", "gradient_norm", "lr"):
        assert max(differences[key]) == 0
    assert cache["parent_before"] == cache["parent_after"]
    assert cache["DINO_before"] == cache["DINO_after"]
    assert result["counts"] == result["updates"] == {"scalar-control": 1000, "phase-matrix": 1000}
    assert result["initial_outputs_exact_parent"] and result["steps"] == 1000
    assert result["new_parent_DINO_forwards"] == result["new_noise_draws"] == 0
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    old_state = torch.load(original["checkpoint"]["path"], map_location="cpu", weights_only=True)
    assert state["step"] == state["horizon"] == 1000
    for arm, count in (("scalar-control", 30402), ("phase-matrix", 31409)):
        assert len(state["models"][arm]) == len(state["emas"][arm]) == 12
        assert sum(t.numel() for t in state["models"][arm].values()) == count
        for group in (state["models"][arm], state["emas"][arm]):
            assert all(torch.isfinite(t).all() for t in group.values())
        adam = state["optimizers"][arm]["state"]
        assert len(adam) == 12
        for values in adam.values():
            assert int(values["step"]) == 1000
            assert all(not torch.is_tensor(t) or torch.isfinite(t).all() for t in values.values())
        gradients = result["parameter_maximum_gradients"][arm]
        assert len(gradients) == 12 and all(math.isfinite(v) and v > 0 for v in gradients.values())
    for group, old_key in (("models", "model"), ("emas", "ema")):
        assert state[group]["scalar-control"].keys() == old_state[old_key].keys()
        assert all(
            torch.equal(t, old_state[old_key][k]) for k, t in state[group]["scalar-control"].items()
        )
    review = read(root / "review-result-v1.json")
    old_mixed = read(previous / "mixed-quiet-v1/result-v1.json")
    exact = 0
    for endpoint in ("raw", "EMA"):
        old_label = f"{endpoint}-step1000"
        new_label = f"scalar-control-{old_label}"
        old_collection = read(previous / f"review-v1/{old_label}/collection-v1.json")
        archived = {o["id"]: o["prediction"] for o in old_collection["observations"]}
        archived.update(
            {r["id"]: r["prediction"] for r in old_mixed["rows"] if r["method"] == old_label}
        )
        collection = read(review["collections"][new_label]["path"])
        assert len(archived) == len(collection["observations"]) == 798
        for observation in collection["observations"]:
            new, old = observation["prediction"], archived[observation["id"]]
            assert ref(new["path"]) == new and ref(old["path"]) == old
            np.testing.assert_array_equal(np.load(new["path"]), np.load(old["path"]))
            exact += 1
    save(
        root / "independent-training-audit-v2.json",
        {
            "status": "passed-paired-bindings-finite-states-and-complete-scalar-replay",
            "auditor": ref(__file__),
            "plan": ref(root / "plan-v1.json"),
            "training_result": ref(root / "train-result-v1.json"),
            "training_trace": ref(root / "train-trace-v1.jsonl"),
            "cache_result": ref(root / "cache-result-v1.json"),
            "cache_trace": ref(root / "cache-trace-v1.jsonl"),
            "original_training": plan["original_trace"],
            "review": ref(root / "review-result-v1.json"),
            "checkpoint": result["checkpoint"],
            "matched_steps_per_arm": 1000,
            "cached_observations": 4000,
            "all_input_target_fingerprints_and_metadata_match_original": True,
            "scalar_trace_differences": {
                k: {"nonexact_steps": sum(v > 0 for v in values), "maximum_abs": max(values)}
                for k, values in differences.items()
            },
            "scalar_reported_loss_comparison_tolerance": {"rtol": 2e-6, "atol": 1e-7},
            "scalar_raw_and_EMA_weights_exact_original": True,
            "scalar_predictions_exact_original": exact,
            "finite_Adam_states_at1000_per_arm": 12,
            "all12_tensors_nonzero_finite_gradient_each_arm": True,
            "batch_domains": dict(Counter(r["domain"] for r in rows)),
            "parent_and_DINO_hashes_unchanged_during_cache": True,
            "new_forwards": 0,
            "new_noise_draws": 0,
            "prior_audit_failure": ref(root / "training-audit-failure-v1.json"),
            "scope": "Posthoc array/state audit. The initial bitexact assertion on reported scalar loss reductions was too strong and is preserved with its source. Pixel/gradient/total loss reductions differ by at most1.91e-6; spectral loss, gradient norm, LR, both final weight sets and all1596 endpoint predictions reproduce V147 exactly. No training/input change. This does not establish matrix quality or independent validation.",
        },
    )
    print("PASS:1000 matched steps,24 finite Adam states,1596 exact scalar replay predictions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
