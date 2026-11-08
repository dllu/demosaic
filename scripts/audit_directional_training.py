"""Independent V195 matched trace, initialization and ten-checkpoint CPU audit."""

import argparse
import json
import math
from pathlib import Path

from directional_trial_protocol import (
    MODES,
    factory,
    guard,
    read,
    ref,
    save,
)
from directional_trial_protocol import (
    TRIAL as ROOT,
)
from directional_trial_protocol import (
    objective_total as loss_from_terms,
)
from phase_admission_protocol import owner_live


def validate_trace(trace, cache, units, old_trace, plan):
    assert len(trace) == len(cache) == len(units) == len(old_trace) == plan["steps"]
    updates = skips = images = 0
    counts = dict.fromkeys(["wrapper", "frozen", "network", "sampler", "projection"], 0)
    for step, (row, item, unit, old) in enumerate(
        zip(trace, cache, units, old_trace, strict=True), 1
    ):
        assert row["step"] == item["step"] == unit["step"] == old["step"] == step
        assert row["batch"] == item["arrays"] == unit["batch"] == old["batch"]
        assert row["parent"] == item["parent"] == old["parent"]
        assert row["domain"] == item["metadata"]["domain"] == old["domain"]
        assert type(row["noisy"]) is bool and row["noisy"] == old["noisy"]
        p = max(0, step - plan["warmup"]) / (plan["steps"] - plan["warmup"])
        lr = (
            plan["lr"]
            * min(1, step / plan["warmup"])
            * (0.1 + 0.9 * (1 + math.cos(math.pi * p)) / 2)
        )
        assert row["lr"] == lr
        if row["noisy"]:
            updates += 1
            images += item["inputs"]["packed"]["shape"][0]
            assert row["loss"] == loss_from_terms(
                row["terms"], plan["domain_weights"][row["domain"]]
            )
            assert (
                row["flat_mask"] == old["flat_mask"]
                and row["flat_eligible_pixels"] == old["flat_eligible_pixels"]
            )
            assert row["EMA_decay"] == min(0.999, (1 + updates) / (10 + updates))
            assert math.isfinite(row["gradient_norm"]) and row["gradient_norm"] >= 0
            assert math.isfinite(row["wave_RMS_DN16"]) and row["wave_RMS_DN16"] >= 0
            assert set(row["zero_gradient_tensors"]) <= {
                f"wave_readout.{p}.{s}" for p in ["context", "mixing"] for s in ["weight", "bias"]
            }
        else:
            skips += 1
            assert row["skipped"] == "zero variance;no matching,readout or optimizer call"
            assert "loss" not in row and "terms" not in row
        counts = {k: (5 * updates if k == "sampler" else updates) for k in counts}
        assert row["counts"] == counts and row["updates"] == updates
    return {
        "rows": len(trace),
        "FP32_ten_term_totals": updates,
        "clean_masks": updates,
        "updates": updates,
        "ADC_skips": skips,
        "images": images,
        "counts": counts,
    }


def terminal(mode):
    launch = read(ROOT / f"{mode}-launch-v1.json")
    assert not owner_live(launch["owner"])
    assert not (ROOT / f"{mode}-train-failure-v1.json").exists()
    result = read(ROOT / f"{mode}-train-result-v1.json")
    assert result["status"] == "completed-V195-matched-response-head-from-V187-EMA"
    assert result["owner"] == launch["owner"] and result["mode"] == mode
    return result


def audit():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert ref(__file__) == plan["auditor"]
    results = {mode: terminal(mode) for mode in MODES}
    import torch
    from phase_wave_training_state import clocks, inherited_hash, load_ema, restore_state
    from profile_raw_kernel_inference import model_hash
    from spatial_wave_training_state import expand_checkpoint
    from train_local_noise_matching_trial import tree_equal

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    initial = torch.load(
        plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )["state_dict"]
    donor = torch.load(plan["donor"]["export"]["path"], map_location="cpu", weights_only=True)[
        "state_dict"
    ]
    module = factory(plan["module_config"])
    module.load_state_dict(donor, strict=True)
    assert (
        model_hash(module)
        == plan["CPU_initialization"]["full_module_hash"]
        == plan["donor"]["module_hash"]
    )
    cache = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    old = read(Path(plan["V187_plan"]["path"]).parent / "wave-train-result-v1.json")["trace"]
    traces, starts, checks, saved = {}, {}, {}, []
    for mode in MODES:
        result = results[mode]
        assert (
            result["plan"] == ref(ROOT / "plan-v1.json")
            and result["donor"] == plan["donor"]["export"]
        )
        starts[mode] = read(ROOT / f"{mode}-initial-state-v1.json")
        start = starts[mode]
        assert (
            start["module_hash"] == plan["donor"]["module_hash"] and start["EMA_equals_donor_head"]
        )
        assert start["Adam"] == {"tensors": 4, "states": 0, "steps": []}
        assert start["inherited_hash"] == plan["initializer"]["module_hash"]
        path = ROOT / f"{mode}-train-trace-v1.jsonl"
        traces[mode] = [json.loads(line) for line in path.read_text().splitlines()]
        assert traces[mode] == result["trace"]
        checks[mode] = validate_trace(traces[mode], cache, units, old, plan)
        assert checks[mode]["updates"] == result["updates"] == 900
        assert result["counts"] == plan["expected_training_counts_per_arm"]
        assert result["training_images"] == 3600 and result["ADC_skips"] == 100
        assert result["RNG_unchanged"] and result["inherited189_tensors_unchanged"]
        restoration = read(ROOT / f"{mode}-restoration-v1.json")
        assert (
            restoration == result["restoration"]
            and restoration["model_Adam_EMA_CPU_CUDA_RNG_exact"]
        )
        assert restoration["continued_at_row"] == 9 and restoration["repeated_prefix_forwards"] == 0
        assert len(result["checkpoints"]) == 5
        rng = None
        for step, binding in zip([8, 250, 500, 750, 1000], result["checkpoints"], strict=True):
            assert ref(binding["path"]) == binding
            state = expand_checkpoint(
                torch.load(binding["path"], map_location="cpu", weights_only=True)
            )
            assert state["mode"] == mode and state["step"] == step
            assert state["updates"] == traces[mode][step - 1]["updates"]
            assert state["counts"] == traces[mode][step - 1]["counts"]
            module = factory(plan["module_config"])
            optimizer, ema = restore_state(
                module,
                {**state, "CUDA_RNG": None},
                lr=plan["lr"],
                weight_decay=plan["weight_decay"],
            )
            assert tree_equal(module.state_dict(), state["models"])
            assert tree_equal(optimizer.state_dict(), state["optimizer"]) and tree_equal(
                ema, state["ema"]
            )
            raw_hash = model_hash(module)
            for endpoint in ["raw", "EMA"]:
                if endpoint == "EMA":
                    load_ema(module, ema)
                assert all(
                    torch.equal(module.state_dict()[name], value) for name, value in initial.items()
                )
                assert inherited_hash(module) == plan["initializer"]["module_hash"]
            if rng is None:
                rng = (state["CPU_RNG"], state["CUDA_RNG"])
            assert torch.equal(rng[0], state["CPU_RNG"]) and torch.equal(rng[1], state["CUDA_RNG"])
            saved.append(
                {
                    "checkpoint": binding,
                    "mode": mode,
                    "step": step,
                    "updates": state["updates"],
                    "raw_module_hash": raw_hash,
                    "EMA_module_hash": model_hash(module),
                    "Adam": clocks(module, optimizer),
                    "inherited189_exact_both_states": True,
                }
            )
        assert (
            saved[-1]["Adam"]
            == result["final_Adam"]
            == {"tensors": 4, "states": 4, "steps": [900.0]}
        )
    assert checks["whole"] == checks["directional"]
    for field in ["module_hash", "inherited_hash", "Adam", "CPU_RNG", "CUDA_RNG", "seed"]:
        assert starts["whole"][field] == starts["directional"][field]
    for a, b in zip(traces["whole"], traces["directional"], strict=True):
        for key in [
            "step",
            "batch",
            "parent",
            "domain",
            "noisy",
            "lr",
            "updates",
            "counts",
            "flat_mask",
            "flat_eligible_pixels",
            "EMA_decay",
        ]:
            assert a.get(key) == b.get(key), (a["step"], key)
        if a["noisy"]:
            assert a["terms"]["response_addition"] == a["terms"]["coherent_response"]
    assert not torch.cuda.is_initialized()
    save(
        ROOT / "training-audit-v1.json",
        {
            "status": "pass-V195-two-matched-traces-ten-checkpoints-Adam-EMA-and-inherited189",
            "plan": ref(ROOT / "plan-v1.json"),
            "training": {mode: ref(ROOT / f"{mode}-train-result-v1.json") for mode in MODES},
            "initial_states": starts,
            "matched_fields_exact": True,
            "trace_checks": checks,
            "checkpoints": saved,
            "inherited_tensor_comparisons": 3780,
            "strict_CPU_raw_EMA_loads": 20,
            "new_module_forwards": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print("PASS: matched 2x1000rows/2x900totals/10checkpoints/3780 inherited comparisons")


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    audit()
