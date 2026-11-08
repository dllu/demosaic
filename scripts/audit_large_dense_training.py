"""Independent complete-trace and five-checkpoint audit of head-only training."""

import json
import math
from pathlib import Path

from audit_coherent_pair_evidence_trial import loss_from_terms
from phase_admission_protocol import owner_live, read, ref
from train_large_dense_trial import ROOT, factory, guard, save


def terminal(root):
    launch = read(root / "wave-train-launch-v1.json")
    if owner_live(launch["owner"]):
        raise RuntimeError("Original training owner is still live; no Torch import")
    assert not (root / "wave-train-failure-v1.json").exists()
    result = read(root / "wave-train-result-v1.json")
    assert result["status"] == "completed-isolated-readout-one-pass-frozen-V183-EMA"
    assert result["owner"] == launch["owner"]
    return result


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
        "FP32_nine_term_totals": updates,
        "clean_masks": updates,
        "updates": updates,
        "ADC_skips": skips,
        "images": images,
        "counts": counts,
    }


def audit():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    seal = read(ROOT / "training-audit-source-v1.json")
    assert ref(__file__) == seal["auditor"] and seal["plan"] == ref(ROOT / "plan-v1.json")
    for binding in seal["helpers"]:
        assert ref(binding["path"]) == binding
    result = terminal(ROOT)
    assert result["plan"] == ref(ROOT / "plan-v1.json")
    assert not (ROOT / "training-audit-v1.json").exists()
    tracepath = ROOT / "wave-train-trace-v1.jsonl"
    trace = [json.loads(line) for line in tracepath.read_text().splitlines()]
    assert trace == result["trace"]
    previous = read(Path(plan["baseline_plan"]["path"]).parent / "evidence-train-result-v1.json")
    previous_plan = read(plan["baseline_plan"]["path"])
    assert (
        previous_plan["cache"] == plan["cache"]
        and previous_plan["pair_units"] == plan["pair_units"]
    )
    check = validate_trace(
        trace,
        read(plan["cache"]["path"])["batches"],
        read(plan["pair_units"]["path"])["rows"],
        previous["trace"],
        plan,
    )
    matched_plan = read(ROOT.parent / "V191-dense-spectrum-trial-v1/plan-v1.json")
    matched = read(ROOT.parent / "V191-dense-spectrum-trial-v1/wave-train-result-v1.json")
    assert all(
        plan[k] == matched_plan[k]
        for k in [
            "cache",
            "pair_units",
            "design",
            "domain_weights",
            "steps",
            "warmup",
            "gradient_clip",
            "lr",
            "weight_decay",
            "EMA_decay",
        ]
    )
    matched_check = validate_trace(
        trace,
        read(plan["cache"]["path"])["batches"],
        read(plan["pair_units"]["path"])["rows"],
        matched["trace"],
        plan,
    )
    assert matched_check == check
    assert (
        check["updates"] == result["updates"] == 900
        and check["ADC_skips"] == result["ADC_skips"] == 100
    )
    assert (
        check["images"] == result["training_images"] == 3600 and check["counts"] == result["counts"]
    )
    assert result["inherited189_tensors_unchanged"] and result["RNG_unchanged"]
    restoration = read(ROOT / "wave-restoration-v1.json")
    assert restoration == result["restoration"] and restoration["model_Adam_EMA_CPU_CUDA_RNG_exact"]
    assert restoration["continued_at_row"] == 9 and restoration["repeated_prefix_forwards"] == 0
    import torch
    from phase_wave_training_state import clocks, inherited_hash, load_ema, restore_state
    from profile_raw_kernel_inference import model_hash
    from spatial_wave_training_state import expand_checkpoint
    from train_local_noise_matching_trial import tree_equal

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    initial = torch.load(
        plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )
    checkpoints = []
    rng = None
    assert len(result["checkpoints"]) == 5
    for step, binding in zip([8, 250, 500, 750, 1000], result["checkpoints"], strict=True):
        assert ref(binding["path"]) == binding
        state = expand_checkpoint(
            torch.load(binding["path"], map_location="cpu", weights_only=True)
        )
        assert state["step"] == step and state["updates"] == trace[step - 1]["updates"]
        assert state["counts"] == trace[step - 1]["counts"] and state["plan"] == ref(
            ROOT / "plan-v1.json"
        )
        module = factory(plan["module_config"])
        optimizer, ema = restore_state(
            module, {**state, "CUDA_RNG": None}, lr=plan["lr"], weight_decay=plan["weight_decay"]
        )
        assert tree_equal(module.state_dict(), state["models"]) and tree_equal(
            optimizer.state_dict(), state["optimizer"]
        )
        assert tree_equal(ema, state["ema"]) and len(module.state_dict()) == 193
        assert all(torch.equal(module.state_dict()[n], v) for n, v in initial["state_dict"].items())
        raw_hash = model_hash(module)
        load_ema(module, ema)
        assert all(torch.equal(module.state_dict()[n], v) for n, v in initial["state_dict"].items())
        assert (
            inherited_hash(module)
            == state["inherited_hash"]
            == result["inherited_hash"]
            == plan["initializer"]["module_hash"]
        )
        if rng is None:
            rng = (state["CPU_RNG"].clone(), state["CUDA_RNG"].clone())
        assert torch.equal(rng[0], state["CPU_RNG"]) and torch.equal(rng[1], state["CUDA_RNG"])
        checkpoints.append(
            {
                "checkpoint": binding,
                "step": step,
                "updates": state["updates"],
                "raw_module_hash": raw_hash,
                "EMA_module_hash": model_hash(module),
                "Adam": clocks(module, optimizer),
                "inherited189_tensors_exact_both_states": True,
            }
        )
    assert (
        checkpoints[-1]["Adam"]
        == result["final_Adam"]
        == {"tensors": 4, "states": 4, "steps": [900.0]}
    )
    assert result["final_checkpoint"] == result["checkpoints"][-1]
    assert all(math.isfinite(v) and v > 0 for v in result["parameter_maximum_gradients"].values())
    assert not torch.cuda.is_initialized()
    save(
        ROOT / "training-audit-v1.json",
        {
            "status": "pass-isolated-readout-full-trace-five-checkpoints-inherited189-and-new-Adam-EMA",
            "plan": ref(ROOT / "plan-v1.json"),
            "training": ref(ROOT / "wave-train-result-v1.json"),
            "trace": ref(tracepath),
            "trace_checks": check,
            "matched_V191_training_trace": ref(
                ROOT.parent / "V191-dense-spectrum-trial-v1/wave-train-result-v1.json"
            ),
            "checkpoint_format": "frozen-V183-plus-spatial-head-v1",
            "checkpoints": checkpoints,
            "inherited_tensor_comparisons": 1890,
            "actual_neural_forwards": 0,
            "new_sensor_source_draws": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print("PASS1000rows/900nineTermTotals/5checkpoints/1890inheritedTensors/headAdam900")


if __name__ == "__main__":
    audit()
