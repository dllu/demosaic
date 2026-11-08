"""Independently inspect terminal readout probe states on CPU, without forwards."""

import argparse
import json
from pathlib import Path

from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V193-large-dense-admission-v1"


def inspect(output):
    result = read(ROOT / "admission-result-v1.json")
    assert (
        result["status"]
        == "pass-V193-frozen-baseline-native-CUDA-parity-head-gradients-and-restoration"
    )
    assert not owner_live(result["owner"])
    plan = read(result["plan"]["path"])
    assert ref(result["plan"]["path"]) == result["plan"]
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for path, digest in plan["frozen_files"].items():
        assert ref(path)["sha256"] == digest
    assert not output.exists()
    import torch
    from phase_wave_training_state import clocks, fresh_state, inherited_hash, load_ema
    from profile_raw_kernel_inference import model_hash
    from spatial_wave_training_state import expand_checkpoint
    from train_local_noise_matching_trial import tree_equal

    from demosaic.late_dense_local_spectrum import LateDenseLocalSpectrumDetail

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    initializer = torch.load(
        plan["initializer"]["export"]["path"], map_location="cpu", weights_only=True
    )
    original_call = torch.nn.Module._call_impl

    def forbidden(*args, **kwargs):
        raise RuntimeError("No module forward in CPU inspection")

    torch.nn.Module._call_impl = forbidden
    rows = []
    try:
        for update, (binding, record) in enumerate(
            zip(result["checkpoints"], result["records"], strict=True), 1
        ):
            assert ref(binding["path"]) == binding
            checkpoint = expand_checkpoint(
                torch.load(binding["path"], map_location="cpu", weights_only=True)
            )
            module = LateDenseLocalSpectrumDetail(**plan["module_config"])
            module.load_state_dict(checkpoint["models"], strict=True)
            assert len(module.state_dict()) == 193 and len(initializer["state_dict"]) == 189
            assert all(
                torch.equal(module.state_dict()[n], v) for n, v in initializer["state_dict"].items()
            )
            assert model_hash(module) == record["model_hash"]
            optimizer, _ = fresh_state(module, lr=plan["lr"], weight_decay=plan["weight_decay"])
            optimizer.load_state_dict(checkpoint["optimizer"])
            assert tree_equal(optimizer.state_dict(), checkpoint["optimizer"])
            assert clocks(module, optimizer) == {
                "tensors": 4,
                "states": 4,
                "steps": [float(update)],
            }
            raw_hash = model_hash(module)
            load_ema(module, checkpoint["ema"])
            assert (
                inherited_hash(module)
                == checkpoint["inherited_hash"]
                == plan["initializer"]["module_hash"]
            )
            assert all(
                torch.equal(module.state_dict()[n], v) for n, v in initializer["state_dict"].items()
            )
            assert set(checkpoint["ema"]) == {
                n for n, p in module.named_parameters() if p.requires_grad
            }
            assert all(torch.isfinite(v).all() for v in checkpoint["ema"].values())
            rows.append(
                {
                    "checkpoint": binding,
                    "update": update,
                    "strict_state_tensors": 193,
                    "inherited_tensors_exact": 189,
                    "Adam": clocks(module, optimizer),
                    "raw_module_hash": raw_hash,
                    "EMA_module_hash": model_hash(module),
                }
            )
    finally:
        torch.nn.Module._call_impl = original_call
    assert not torch.cuda.is_initialized()
    proof = {
        "status": "pass-V193-readout-probe-CPU-raw-EMA-Adam-and-inherited-state",
        "admission": ref(ROOT / "admission-result-v1.json"),
        "plan": result["plan"],
        "checkpoints": rows,
        "strict_CPU_raw_EMA_loads": 4,
        "inherited_tensor_comparisons": 756,
        "new_module_forwards": 0,
        "CUDA_initialized": False,
        "source": dict(ref(__file__), text=Path(__file__).read_text()),
    }
    with output.open("x") as stream:
        json.dump(proof, stream, indent=2, allow_nan=False)
        stream.write("\n")
    print("PASS2probecheckpoints/4strictRawEMAloads/756inheritedTensorChecks/4AdamClocks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    inspect(parser.parse_args().output)
