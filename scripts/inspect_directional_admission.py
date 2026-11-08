"""CPU-only inspection of all four terminal V195 probe checkpoints."""

import argparse
from pathlib import Path

from directional_trial_protocol import ADMISSION as ROOT
from directional_trial_protocol import factory, guard, read, ref, save
from phase_admission_protocol import owner_live


def inspect(output):
    result = read(ROOT / "admission-result-v1.json")
    assert result["status"] == "pass-V195-V187-EMA-parity-both-response-gradients-and-restoration"
    assert not owner_live(result["owner"])
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    import torch
    from phase_wave_training_state import clocks, fresh_state, inherited_hash, load_ema
    from profile_raw_kernel_inference import model_hash
    from spatial_wave_training_state import expand_checkpoint
    from train_local_noise_matching_trial import tree_equal

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    inherited = torch.load(
        plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )["state_dict"]
    assert len(inherited) == 189
    original = torch.nn.Module._call_impl

    def forbidden(*args, **kwargs):
        raise RuntimeError("CPU inspection cannot perform module forwards")

    torch.nn.Module._call_impl = forbidden
    rows = []
    try:
        for binding, record in zip(result["checkpoints"], result["records"], strict=True):
            assert ref(binding["path"]) == binding
            state = expand_checkpoint(
                torch.load(binding["path"], map_location="cpu", weights_only=True)
            )
            assert state["mode"] == record["mode"] and state["updates"] == record["update"]
            module = factory(plan["module_config"])
            module.load_state_dict(state["models"], strict=True)
            assert len(module.state_dict()) == 193 and model_hash(module) == record["module_hash"]
            raw_hash = model_hash(module)
            optimizer, _ = fresh_state(module, lr=plan["lr"], weight_decay=plan["weight_decay"])
            optimizer.load_state_dict(state["optimizer"])
            assert tree_equal(optimizer.state_dict(), state["optimizer"])
            assert clocks(module, optimizer) == {
                "tensors": 4,
                "states": 4,
                "steps": [float(record["update"])],
            }
            for endpoint in ["raw", "EMA"]:
                if endpoint == "EMA":
                    load_ema(module, state["ema"])
                assert all(
                    torch.equal(module.state_dict()[name], value)
                    for name, value in inherited.items()
                )
                assert inherited_hash(module) == plan["initializer"]["module_hash"]
            rows.append(
                {
                    "checkpoint": binding,
                    "mode": record["mode"],
                    "update": record["update"],
                    "raw_module_hash": raw_hash,
                    "EMA_module_hash": model_hash(module),
                    "Adam": clocks(module, optimizer),
                    "inherited_tensors_each_state": 189,
                }
            )
    finally:
        torch.nn.Module._call_impl = original
    assert not torch.cuda.is_initialized() and len(rows) == 4
    save(
        output,
        {
            "status": "pass-V195-four-probes-eight-CPU-raw-EMA-loads-and-Adam",
            "admission": ref(ROOT / "admission-result-v1.json"),
            "plan": ref(ROOT / "plan-v1.json"),
            "checkpoints": rows,
            "strict_CPU_raw_EMA_loads": 8,
            "inherited_tensor_comparisons": 1512,
            "new_module_forwards": 0,
            "CUDA_initialized": False,
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
        },
    )
    print("PASS: four probes / eight raw-EMA loads /1512 inherited checks / no forwards")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    inspect(parser.parse_args().output)
