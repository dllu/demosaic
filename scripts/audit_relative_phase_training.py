"""Check both fixed training states and replay the matched native control."""

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
    fields = set(journal[0]["arms"]["noisy-control"])
    for step, (row, archived, batch) in enumerate(
        zip(journal, old["trace"], cache["batches"], strict=True), 1
    ):
        assert row["step"] == archived["step"] == batch["step"] == step
        assert row["batch"] == archived["batch"] == batch["arrays"]
        assert row["domain"] == archived["domain"] == batch["metadata"]["domain"]
        assert row["arms"]["noisy-control"] == archived["arms"]["noisy-only"]
        assert len({v["lr"] for v in row["arms"].values()}) == 1
        assert all(
            set(v) == fields and all(np.isfinite(x) for x in v.values())
            for v in row["arms"].values()
        )
    assert result["steps"] == 1000 and result["initial_outputs_exact_parent"]
    assert result["counts"] == result["updates"] == {"noisy-control": 1000, "relative-phase": 1000}
    assert result["new_parent_DINO_forwards"] == result["new_noise_draws"] == 0
    assert result["loss_floors_DN16"] == dict.fromkeys(["noisy-control", "relative-phase"], 16)
    assert result["supervised_batches"] == {
        "noisy-control": 882,
        "relative-phase": 882,
    }
    assert result["zero_ADC_gradient_batches"] == {
        "noisy-control": 118,
        "relative-phase": 118,
    }
    assert result["peak_weight_evaluations"] == {
        "noisy-control": 0,
        "relative-phase": 0,
    }
    for row, batch in zip(journal, cache["batches"], strict=True):
        noise = batch["metadata"]["noise"]
        if noise["shot"] == noise["read"] == 0:
            assert all(
                row["arms"][arm]["loss"] == row["arms"][arm]["gradient_norm"] == 0
                for arm in ["noisy-control", "relative-phase"]
            )
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    assert ref(old["checkpoint"]["path"]) == old["checkpoint"]
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    old_state = torch.load(old["checkpoint"]["path"], map_location="cpu", weights_only=True)
    assert state["step"] == state["horizon"] == 1000
    for arm, number, tensors in (
        ("noisy-control", 31409, 12),
        ("relative-phase", 33713, 13),
    ):
        assert len(state["models"][arm]) == len(state["emas"][arm]) == tensors
        assert sum(v.numel() for v in state["models"][arm].values()) == number
        for key in ("models", "emas"):
            assert all(torch.isfinite(v).all() for v in state[key][arm].values())
        adam = state["optimizers"][arm]["state"]
        assert len(adam) == tensors
        for values in adam.values():
            assert int(values["step"]) == 1000
            assert all(not torch.is_tensor(v) or torch.isfinite(v).all() for v in values.values())
        gradients = result["parameter_maximum_gradients"][arm]
        assert len(gradients) == tensors and all(
            np.isfinite(v) and v > 0 for v in gradients.values()
        )
    for key in ("models", "emas"):
        native, archived = state[key]["noisy-control"], old_state[key]["noisy-only"]
        assert native.keys() == archived.keys()
        assert all(torch.equal(v, archived[k]) for k, v in native.items())
    new_adam = state["optimizers"]["noisy-control"]
    old_adam = old_state["optimizers"]["noisy-only"]
    assert new_adam["param_groups"] == old_adam["param_groups"]
    assert new_adam["state"].keys() == old_adam["state"].keys()
    for key, fields in new_adam["state"].items():
        assert all(
            torch.equal(v, old_adam["state"][key][name])
            if torch.is_tensor(v)
            else v == old_adam["state"][key][name]
            for name, v in fields.items()
        )
    if states_only:
        assert not torch.cuda.is_initialized()
        save(
            root / "independent-training-state-audit-v1.json",
            {
                "status": "pass-both-finite-states-and-exact-native-state-reproduction",
                "auditor": ref(__file__),
                "plan": ref(root / "plan-v1.json"),
                "training_result": ref(root / "train-result-v1.json"),
                "checkpoint": result["checkpoint"],
                "steps_per_arm": 1000,
                "finite_Adam_states_at1000": 25,
                "control_all1000_loss_gradient_LR_rows_exact": True,
                "control_raw_EMA_and_Adam_states_exact": True,
                "new_forwards": 0,
                "new_noise_draws": 0,
                "CUDA_initialized": False,
                "scope": "Final training-state check while endpoint collection is in progress. Exact native control trace/model/EMA/Adam and finite states of both arms; this does not inspect endpoint quality or claim pixel replay before it exists.",
            },
        )
        print("PASS2x1k finite states; native trace/model/EMA/Adam exactV151")
        return
    review = read(root / "review-result-v1.json")
    old_review = read(previous / "review-result-v1.json")
    exact = 0
    for endpoint in ("raw", "EMA"):
        current_label, old_label = (
            f"noisy-control-{endpoint}-step1000",
            f"noisy-only-{endpoint}-step1000",
        )
        current = read(review["collections"][current_label]["path"])
        archived = read(old_review["collections"][old_label]["path"])
        assert len(current["observations"]) == len(archived["observations"]) == 822
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
    assert exact == 1644 and not torch.cuda.is_initialized()
    save(
        root / "independent-training-audit-v1.json",
        {
            "status": "pass-both-finite-states-and-exact-native-control-reproduction",
            "auditor": ref(__file__),
            "plan": ref(root / "plan-v1.json"),
            "training_result": ref(root / "train-result-v1.json"),
            "training_journal": ref(root / "train-trace-v1.jsonl"),
            "adopted_cache": plan["cache"],
            "checkpoint": result["checkpoint"],
            "old_V151_training": ref(previous / "train-result-v1.json"),
            "review": ref(root / "review-result-v1.json"),
            "steps_per_arm": 1000,
            "arms": 2,
            "finite_Adam_states_at1000": 25,
            "control_all1000_loss_gradient_LR_rows_exact": True,
            "control_raw_EMA_and_Adam_states_exact": True,
            "native_control_predictions_exact": 1644,
            "all_named_tensor_gradients_nonzero_finite_each_arm": True,
            "batch_domains": dict(Counter(row["domain"] for row in journal)),
            "new_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_initialized": False,
            "scope": "Final fixed matched trial state/binding audit, using the archived V151 noisy-only matrix as exact control. Checks all1000 adopted batch refs/domains, both states, complete native optimizer/model/EMA equality and all1644 native pixel arrays. Retained1644 control predictions are exact; All822 cases,including ADC controls,have the V151 archive. No neural,parent/DINO or noise call. This does not establish quality for the relative-phase estimator.",
        },
    )
    print("PASS2x1k finite states and1644 exact native-control predictions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--states-only", action="store_true")
    args = parser.parse_args()
    main(args.root.absolute(), args.states_only)
