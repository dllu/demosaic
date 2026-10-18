"""Six discarded B16/native256 BF16 updates per objective on genuine V63."""

import argparse
import gc
import json
import math
import os
import shutil
from contextlib import redirect_stdout
from pathlib import Path

import psutil
import torch
import yaml
from audit_flat_palette import train_rows
from preflight_reconstruction_objective import sha
from profile_raw_kernel_inference import model_hash

import demosaic.train as training
from demosaic.safety import writable_path


def main(config_path, parent_path, cpu_receipt, output):
    os.nice(5)
    torch.set_num_threads(4)
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(Path.cwd()).free > 128 * 2**30
    assert json.loads(cpu_receipt.read_text())["status"] == (
        "completed-genuine-parent-CPU-reconstruction-objective-preflight"
    )
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    cfg = yaml.safe_load(config_path.read_text())
    assert (cfg["batch_size"], cfg["patch_size"], cfg["precision"], cfg["seed"]) == (
        16, 256, "bfloat16", 51
    )
    source = {str(p.resolve()): sha(p) for p in Path("src/demosaic").glob("*.py")}
    inputs = [config_path, parent_path, cpu_receipt] + [Path(cfg[k]) for k in (
        "manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest",
        "validation_protocol",
    )]
    plan = {
        "source_files": source,
        "inputs": [{"path": str(p.resolve()), "sha256": sha(p)} for p in inputs],
        "worker_sha256": sha(__file__),
        "template": cfg,
        "scope": "Two fresh six-update model/optimizer instances run serially in one CUDA worker: "
        "genuine V63 EMA, fresh AdamW/EMA/RNG, B16/native256/BF16/workers4+2+2, "
        "actual cleaned84867 Commons/native128/paired32 data. Engineering only, "
        "not a throughput or quality result. CPU exact restart checked separately.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    shutil.copyfile(__file__, output / "source.py")
    parent = torch.load(parent_path, weights_only=True, map_location="cpu", mmap=True)
    expected = parent["ema"]
    assert parent["step"] == 20000 and len(expected) == 91
    device = torch.device("cuda", torch.cuda.current_device())
    previous_quota = torch.cuda.get_per_process_memory_fraction(device)
    total = torch.cuda.get_device_properties(device).total_memory
    torch.cuda.set_per_process_memory_fraction(min(previous_quota, 24 * 2**30 / total), device)
    constructor, make_optimizer = training.JointDemosaic, training.make_optimizer
    current, starts, gradients, results = {}, [], [], {}

    def instrument(config):
        net = constructor(config)
        current["model"] = net
        seen = False

        def first_forward(model, args):
            nonlocal seen
            if seen:
                return
            seen = True
            assert args[0].shape == (16, 4, 128, 128)
            assert torch.is_autocast_enabled("cuda")
            for name, tensor in model.restoration_state_dict().items():
                assert torch.equal(tensor.cpu(), expected[name]), name
            current["DINO_hash"] = model_hash(model.context.backbone)
            starts.append({"policy": current["policy"], "actual_initial_EMA_exact": True,
                           "DINO_hash": current["DINO_hash"]})

        net.register_forward_pre_hook(first_forward)
        return net

    def optimizer_for(model, config):
        optimizer = make_optimizer(model, config)

        def before_step(*args):
            active = [p for p in model.parameters() if p.requires_grad]
            assert len(active) == 89
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in active)
            assert all(not p.requires_grad and p.grad is None
                       for p in model.context.backbone.parameters())
            gradients.append({"policy": current["policy"], "finite_gradients": len(active)})

        optimizer.register_step_pre_hook(before_step)
        return optimizer

    try:
        training.JointDemosaic, training.make_optimizer = instrument, optimizer_for
        for policy in ["charbonnier-v1", "image-log-mse-v1"]:
            current["policy"] = policy
            fixture = {**cfg, "run": str(output / policy), "checkpoint_every": 6,
                       "log_every": 1, "validation_images": 1, "val_batches": 1,
                       "min_available_gb": 32, "reconstruction_objective": policy}
            path = output / (policy + ".yaml")
            path.write_text(yaml.safe_dump(fixture))
            torch.cuda.reset_peak_memory_stats()
            with (output / (policy + ".log")).open("w") as log, redirect_stdout(log):
                checkpoint = training.train(path, initialize=parent_path, stop_after=6)
            net = current.pop("model")
            assert model_hash(net.context.backbone) == current["DINO_hash"]
            assert all(p.grad is None for p in net.context.backbone.parameters())
            del net
            state = torch.load(checkpoint, weights_only=True, map_location="cpu", mmap=True)
            assert state["step"] == 6 and state["config"]["steps"] == 4000
            assert len(state["model"]) == len(state["ema"]) == 91
            assert len(state["optimizer"]["state"]) == 89
            for field in ["model", "ema"]:
                assert all(torch.isfinite(v).all() for v in state[field].values())
            for item in state["optimizer"]["state"].values():
                assert int(item["step"]) == 6
                assert all(torch.isfinite(v).all() for v in item.values()
                           if isinstance(v, torch.Tensor))
            rows = train_rows(output / policy)
            assert len(rows) == 6
            assert {r["domain"] for r in rows} == {
                "synthetic", "native-RAW-synthetic", "paired-RAW"}
            assert all(math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"]) for r in rows)
            results[policy] = {"checkpoint": {"path": str(checkpoint), "sha256": sha(checkpoint)},
                               "observations": rows,
                               "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                               "finite_states": {"model": 91, "EMA": 91, "AdamW": 89}}
            del state
            gc.collect()
            torch.cuda.empty_cache()
    finally:
        training.JointDemosaic, training.make_optimizer = constructor, make_optimizer
        torch.cuda.set_per_process_memory_fraction(previous_quota, device)
    a, b = [r["observations"] for r in results.values()]
    assert [r["batch_sha256"] for r in a] == [r["batch_sha256"] for r in b]
    assert source == {str(p.resolve()): sha(p) for p in Path("src/demosaic").glob("*.py")}
    assert all(sha(i["path"]) == i["sha256"] for i in plan["inputs"])
    receipt = {"status": "completed-genuine-V63-CUDA-B16-objective-engineering-check",
               "plan": {"path": str(output / "plan.json"), "sha256": sha(output / "plan.json")},
               "cases": results, "initializations": starts, "gradient_checks": gradients,
               "all_six_observation_hashes_match": True, "allocator_quota_restored": True,
               "scope": plan["scope"]}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--initialize", type=Path, required=True)
    parser.add_argument("--cpu-receipt", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.config, args.initialize, args.cpu_receipt, args.output)
