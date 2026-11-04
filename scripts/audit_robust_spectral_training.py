"""Check three robust spectral states and replay the matched relative control."""

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
    fields = set(journal[0]["arms"]["mse-control"])
    for step, (row, archived, batch) in enumerate(
        zip(journal, old["trace"], cache["batches"], strict=True), 1
    ):
        assert row["step"] == archived["step"] == batch["step"] == step
        assert row["batch"] == archived["batch"] == batch["arrays"]
        assert row["domain"] == archived["domain"] == batch["metadata"]["domain"]
        assert row["arms"]["mse-control"] == archived["arms"]["delivered-RGB"]
        assert len({v["lr"] for v in row["arms"].values()}) == 1
        assert all(
            set(v) == fields and all(np.isfinite(x) for x in v.values())
            for v in row["arms"].values()
        )
    assert result["steps"] == 1000 and result["initial_outputs_exact_parent"]
    assert (
        result["counts"]
        == result["updates"]
        == {"mse-control": 1000, "charb-0p01": 1000, "charb-0p003": 1000}
    )
    assert result["new_parent_DINO_forwards"] == result["new_noise_draws"] == 0
    assert result["loss_floors_DN16"] == dict.fromkeys(
        ["mse-control", "charb-0p01", "charb-0p003"], 16
    )
    assert result["supervised_batches"] == dict.fromkeys(
        ["mse-control", "charb-0p01", "charb-0p003"], 882
    )
    assert result["zero_ADC_gradient_batches"] == dict.fromkeys(
        ["mse-control", "charb-0p01", "charb-0p003"], 118
    )
    assert result["peak_weight_evaluations"] == dict.fromkeys(
        ["mse-control", "charb-0p01", "charb-0p003"], 0
    )
    for row, batch in zip(journal, cache["batches"], strict=True):
        noise = batch["metadata"]["noise"]
        if noise["shot"] == noise["read"] == 0:
            assert all(
                row["arms"][arm]["loss"] == row["arms"][arm]["gradient_norm"] == 0
                for arm in ["mse-control", "charb-0p01", "charb-0p003"]
            )
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    assert ref(old["checkpoint"]["path"]) == old["checkpoint"]
    state = torch.load(result["checkpoint"]["path"], map_location="cpu", weights_only=True)
    old_state = torch.load(old["checkpoint"]["path"], map_location="cpu", weights_only=True)
    assert state["step"] == state["horizon"] == 1000
    for arm, number, tensors in (
        ("mse-control", 33713, 13),
        ("charb-0p01", 33713, 13),
        ("charb-0p003", 33713, 13),
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
        native, archived = state[key]["mse-control"], old_state[key]["delivered-RGB"]
        assert native.keys() == archived.keys()
        assert all(torch.equal(v, archived[k]) for k, v in native.items())
    new_adam = state["optimizers"]["mse-control"]
    old_adam = old_state["optimizers"]["delivered-RGB"]
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
                "status": "pass-three-finite-states-and-exact-relative-state-reproduction",
                "auditor": ref(__file__),
                "plan": ref(root / "plan-v1.json"),
                "training_result": ref(root / "train-result-v1.json"),
                "checkpoint": result["checkpoint"],
                "steps_per_arm": 1000,
                "finite_Adam_states_at1000": 39,
                "control_all1000_loss_gradient_LR_rows_exact": True,
                "control_raw_EMA_and_Adam_states_exact": True,
                "new_forwards": 0,
                "new_noise_draws": 0,
                "CUDA_initialized": False,
                "scope": "Final training-state check while endpoint collection is in progress. Exact RGB-MSE control trace/model/EMA/Adam and finite states of all three arms; this does not inspect endpoint quality or claim pixel replay before it exists.",
            },
        )
        print("PASS3x1k finite states; relative trace/model/EMA/Adam exactV153")
        return
    review = read(root / "review-result-v1.json")
    old_review = read(previous / "review-result-v1.json")
    exact = 0
    for endpoint in ("raw", "EMA"):
        current_label, old_label = (
            f"mse-control-{endpoint}-step1000",
            f"delivered-RGB-{endpoint}-step1000",
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
            "status": "pass-three-finite-states-and-exact-relative-control-reproduction",
            "auditor": ref(__file__),
            "plan": ref(root / "plan-v1.json"),
            "training_result": ref(root / "train-result-v1.json"),
            "training_journal": ref(root / "train-trace-v1.jsonl"),
            "adopted_cache": plan["cache"],
            "checkpoint": result["checkpoint"],
            "old_V153_training": ref(previous / "train-result-v1.json"),
            "review": ref(root / "review-result-v1.json"),
            "steps_per_arm": 1000,
            "arms": 3,
            "finite_Adam_states_at1000": 39,
            "control_all1000_loss_gradient_LR_rows_exact": True,
            "control_raw_EMA_and_Adam_states_exact": True,
            "MSE_control_predictions_exact": 1644,
            "all_named_tensor_gradients_nonzero_finite_each_arm": True,
            "batch_domains": dict(Counter(row["domain"] for row in journal)),
            "new_forwards": 0,
            "new_noise_draws": 0,
            "CUDA_initialized": False,
            "scope": "Final matched trial state/binding audit using archived V153 delivered-RGB as exact delivered-RGB MSE control. All1000 adopted refs/domains,39 finite Adam states,complete control model/EMA/Adam equality and all1644 raw/EMA control arrays. All822 cases including ADC controls have the V153 archive. No neural,parent/DINO/noise call. State reproduction alone does not establish robust-loss quality.",
        },
    )
    print("PASS3x1k finite states and1644 exact relative-control predictions")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--states-only", action="store_true")
    args = parser.parse_args()
    main(args.root.absolute(), args.states_only)
