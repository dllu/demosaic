"""Check all3 fixed training states and replay the matched native control."""

import argparse
import json
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from train_directional_bank_trial import guard, read, ref, save


def main(root, states_only=False):
    plan = read(root / "plan-v1.json")
    guard(plan)
    previous = Path(plan["previous"])
    result = read(root / "train-result-v1.json")
    old = read(previous / "train-result-v1.json")
    cache = read(plan["cache"]["path"])
    journal = [json.loads(s) for s in (root / "train-trace-v1.jsonl").read_text().splitlines()]
    assert (
        journal == result["trace"]
        and len(journal) == len(cache["batches"]) == len(old["trace"]) == 1000
    )
    fields = set(journal[0]["arms"]["native-matrix"])
    for step, (row, archived, batch) in enumerate(
        zip(journal, old["trace"], cache["batches"], strict=True), 1
    ):
        assert row["step"] == archived["step"] == batch["step"] == step
        assert row["batch"] == archived["batch"] == batch["arrays"]
        assert row["domain"] == archived["domain"] == batch["metadata"]["domain"]
        assert row["arms"]["native-matrix"] == archived["arms"]["phase-matrix"]
        assert len({v["lr"] for v in row["arms"].values()}) == 1
        assert all(
            set(v) == fields and all(np.isfinite(x) for x in v.values())
            for v in row["arms"].values()
        )
    assert result["steps"] == 1000 and result["initial_outputs_exact_parent"]
    assert (
        result["counts"]
        == result["updates"]
        == {
            "native-matrix": 1000,
            "aligned-matrix": 1000,
            "coherent-context": 1000,
        }
    )
    assert result["new_parent_DINO_forwards"] == result["new_noise_draws"] == 0
    assert result["extra_context_input_maximum_gradient"] > 0
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    assert ref(old["checkpoint"]["path"]) == old["checkpoint"]
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    old_state = torch.load(old["checkpoint"]["path"], map_location="cpu", weights_only=True)
    assert state["step"] == state["horizon"] == 1000
    for arm, number in (
        ("native-matrix", 31409),
        ("aligned-matrix", 31409),
        ("coherent-context", 33353),
    ):
        assert len(state["models"][arm]) == len(state["emas"][arm]) == 12
        assert sum(v.numel() for v in state["models"][arm].values()) == number
        for key in ("models", "emas"):
            assert all(torch.isfinite(v).all() for v in state[key][arm].values())
        adam = state["optimizers"][arm]["state"]
        assert len(adam) == 12
        for values in adam.values():
            assert int(values["step"]) == 1000
            assert all(not torch.is_tensor(v) or torch.isfinite(v).all() for v in values.values())
        gradients = result["parameter_maximum_gradients"][arm]
        assert len(gradients) == 12 and all(np.isfinite(v) and v > 0 for v in gradients.values())
    for key in ("models", "emas"):
        native, archived = state[key]["native-matrix"], old_state[key]["phase-matrix"]
        assert native.keys() == archived.keys()
        assert all(torch.equal(v, archived[k]) for k, v in native.items())
    new_adam = state["optimizers"]["native-matrix"]
    old_adam = old_state["optimizers"]["phase-matrix"]
    assert new_adam["param_groups"] == old_adam["param_groups"]
    assert new_adam["state"].keys() == old_adam["state"].keys()
    for key, fields in new_adam["state"].items():
        assert all(
            torch.equal(v, old_adam["state"][key][name])
            if torch.is_tensor(v)
            else v == old_adam["state"][key][name]
            for name, v in fields.items()
        )
    extra_columns = state["models"]["coherent-context"]["local_in.weight"][:, 28:]
    assert extra_columns.count_nonzero() > 0
    if states_only:
        assert not torch.cuda.is_initialized()
        save(
            root / "independent-training-state-audit-v1.json",
            {
                "status": "pass-all3-finite-states-and-exact-native-state-reproduction",
                "auditor": ref(__file__),
                "plan": ref(root / "plan-v1.json"),
                "training_result": ref(root / "train-result-v1.json"),
                "checkpoint": result["checkpoint"],
                "steps_per_arm": 1000,
                "finite_Adam_states_at1000": 36,
                "native_control_all1000_loss_gradient_LR_rows_exact": True,
                "native_raw_EMA_and_Adam_states_exact": True,
                "context_extra_weight_entries_nonzero": int(extra_columns.count_nonzero()),
                "new_forwards": 0,
                "new_noise_draws": 0,
                "CUDA_initialized": False,
                "scope": "Final training-state check while endpoint collection is in progress. Exact native control trace/model/EMA/Adam and finite states of all3 arms; this does not inspect endpoint quality or claim pixel replay before it exists.",
            },
        )
        print("PASS3x1k finite states; native trace/model/EMA/Adam exactV148")
        return
    review = read(root / "review-result-v1.json")
    old_review = read(previous / "review-result-v1.json")
    exact = 0
    for endpoint in ("raw", "EMA"):
        current_label, old_label = (
            f"native-matrix-{endpoint}-step1000",
            f"phase-matrix-{endpoint}-step1000",
        )
        current = read(review["collections"][current_label]["path"])
        archived = read(old_review["collections"][old_label]["path"])
        assert len(current["observations"]) == len(archived["observations"]) == 798
        for one, two in zip(current["observations"], archived["observations"], strict=True):
            assert (
                one["id"] == two["id"]
                and one["parent"] == two["parent"]
                and one["inputs"] == two["inputs"]
            )
            assert ref(one["prediction"]["path"]) == one["prediction"]
            assert ref(two["prediction"]["path"]) == two["prediction"]
            np.testing.assert_array_equal(
                np.load(one["prediction"]["path"]), np.load(two["prediction"]["path"])
            )
            exact += 1
    assert exact == 1596 and not torch.cuda.is_initialized()
    save(
        root / "independent-training-audit-v1.json",
        {
            "status": "pass-all3-finite-states-and-exact-native-control-reproduction",
            "auditor": ref(__file__),
            "plan": ref(root / "plan-v1.json"),
            "training_result": ref(root / "train-result-v1.json"),
            "training_journal": ref(root / "train-trace-v1.jsonl"),
            "adopted_cache": plan["cache"],
            "checkpoint": result["checkpoint"],
            "old_V148_training": ref(previous / "train-result-v1.json"),
            "review": ref(root / "review-result-v1.json"),
            "steps_per_arm": 1000,
            "arms": 3,
            "finite_Adam_states_at1000": 36,
            "native_control_all1000_loss_gradient_LR_rows_exact": True,
            "native_raw_EMA_and_Adam_states_exact": True,
            "native_control_predictions_exact": 1596,
            "all12_tensor_gradients_nonzero_finite_each_arm": True,
            "extra_context_maximum_gradient": result["extra_context_input_maximum_gradient"],
            "context_extra_weight_entries_nonzero": int(extra_columns.count_nonzero()),
            "batch_domains": dict(Counter(row["domain"] for row in journal)),
            "new_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_initialized": False,
            "scope": "Final fixed matched trial state/binding audit, using the archived V148 native matrix as exact control. Checks all1000 adopted batch refs/domains, all3 states, complete native optimizer/model/EMA equality and all1596 native pixel arrays. No neural, parent/DINO or noise call. This does not establish useful quality for either new estimator.",
        },
    )
    print("PASS3x1k finite states and1596 exact native-control predictions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--states-only", action="store_true")
    args = parser.parse_args()
    main(args.root.absolute(), args.states_only)
