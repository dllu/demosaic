"""Independent full CFA trace, five factored checkpoints, fresh clocks and193frozen tensors."""

import json
import math
import time

from directional_trial_protocol import guard, read, ref, save
from directional_trial_protocol import objective_total as loss_from_terms
from phase_admission_protocol import owner_live
from train_cfa_innovation_wave import MODES, ROOT, factory


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
                f"cfa_readout.{p}.{s}" for p in ["context", "gates"] for s in ["weight", "bias"]
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


def audit():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert ref(__file__) == plan["auditor"]
    import torch
    from cfa_innovation_state import anchor_hash, clocks, restore
    from profile_raw_kernel_inference import model_hash
    from train_local_noise_matching_trial import tree_equal

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    source = torch.load(plan["anchor"]["export"]["path"], map_location="cpu", weights_only=True)[
        "state_dict"
    ]
    cache = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    old = read(plan["previous_trace"]["path"])["trace"]
    checks, starts, traces, states = {}, {}, {}, []
    frozen_comparisons = 0
    results = {}
    for mode in MODES:
        launch = read(ROOT / f"{mode}-launch-v1.json")
        assert not owner_live(launch["owner"])
        assert not (ROOT / f"{mode}-train-failure-v1.json").exists()
        result = read(ROOT / f"{mode}-train-result-v1.json")
        assert result["status"] == "completed-V198-CFA-wave-head-above-frozen-V195-WholeEMA"
        assert result["owner"] == launch["owner"] and result["mode"] == mode
        assert result["plan"] == ref(ROOT / "plan-v1.json")
        assert result["donor"] == plan["anchor"]["export"]
        results[mode] = ref(ROOT / f"{mode}-train-result-v1.json")
        start = read(ROOT / f"{mode}-initial-state-v1.json")
        assert start["module_hash"] == plan["CPU_initialization"]["full_module_hash"]
        assert start["EMA_equals_fresh_head"] and start["Adam"] == {
            "tensors": 4,
            "states": 0,
            "steps": [],
        }
        assert start["anchor_hash"] == plan["anchor"]["module_hash"]
        starts[mode] = start
        trace = [
            json.loads(line)
            for line in (ROOT / f"{mode}-train-trace-v1.jsonl").read_text().splitlines()
        ]
        assert trace == result["trace"]
        traces[mode] = trace
        checks[mode] = validate_trace(trace, cache, units, old, plan)
        assert checks[mode]["updates"] == result["updates"] == 900
        assert checks[mode]["images"] == result["training_images"] == 3600
        assert (
            result["ADC_skips"] == 100
            and result["counts"] == plan["expected_training_counts_per_arm"]
        )
        assert result["anchor193_tensors_unchanged"] and result["RNG_unchanged"]
        assert result["restoration"] == read(ROOT / f"{mode}-restoration-v1.json")
        assert result["restoration"]["model_Adam_EMA_CPU_CUDA_RNG_exact"]
        assert (
            result["restoration"]["continued_at_row"] == 9
            and result["restoration"]["repeated_prefix_forwards"] == 0
        )
        assert len(result["checkpoints"]) == 5
        rng = None
        for step, binding in zip([8, 250, 500, 750, 1000], result["checkpoints"], strict=True):
            assert ref(binding["path"]) == binding
            saved = torch.load(binding["path"], map_location="cpu", weights_only=True)
            assert (
                saved["mode"] == mode
                and saved["step"] == step
                and saved["plan"] == ref(ROOT / "plan-v1.json")
            )
            assert (
                saved["updates"] == trace[step - 1]["updates"]
                and saved["counts"] == trace[step - 1]["counts"]
            )
            module = factory(plan, mode)
            optimizer, ema = restore(
                module,
                {**saved, "CUDA_RNG": None},
                lr=plan["lr"],
                weight_decay=plan["weight_decay"],
            )
            assert tree_equal(optimizer.state_dict(), saved["optimizer"]) and tree_equal(
                ema, saved["ema"]
            )
            assert clocks(module, optimizer) == {
                "tensors": 4,
                "states": 4,
                "steps": [float(saved["updates"])],
            }
            for endpoint in ["raw", "EMA"]:
                if endpoint == "EMA":
                    module.load_state_dict(dict(module.state_dict(), **ema), strict=True)
                assert (
                    len(module.state_dict()) == 197
                    and anchor_hash(module) == plan["anchor"]["module_hash"]
                )
                for name, value in source.items():
                    assert torch.equal(module.state_dict()[name], value)
                    frozen_comparisons += 1
                states.append(
                    {
                        "mode": mode,
                        "step": step,
                        "updates": saved["updates"],
                        "endpoint": endpoint,
                        "module_hash": model_hash(module),
                        "anchor193_unchanged": True,
                        "checkpoint": binding,
                    }
                )
            if rng is None:
                rng = (saved["CPU_RNG"], saved["CUDA_RNG"])
            assert torch.equal(rng[0], saved["CPU_RNG"]) and torch.equal(rng[1], saved["CUDA_RNG"])
        assert result["final_Adam"] == {"tensors": 4, "states": 4, "steps": [900.0]}
    assert len(checks) == 1 and checks["CFA"]["updates"] == 900
    assert frozen_comparisons == 1930 and len(states) == 10 and not torch.cuda.is_initialized()
    save(
        ROOT / "training-audit-v1.json",
        {
            "status": "pass-V198-full-CFA-trace-five-factored-checkpoints-1930anchor-tensors",
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v1.json"),
            "training": results,
            "checks": checks,
            "starts": starts,
            "checkpoint_states": states,
            "frozen_tensor_comparisons": frozen_comparisons,
            "new_neural_forwards": 0,
            "CUDA_initialized": False,
        },
    )
    print("PASS1000rows/900FP32losses/5checkpoints/10rawEMAstates/1930frozenanchorcomparisons")


if __name__ == "__main__":
    audit()
