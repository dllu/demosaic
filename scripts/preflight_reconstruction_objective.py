"""Discarded mixed-domain CPU checks of a new objective on a genuine RGB parent."""

import argparse
import gc
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

import psutil
import torch
import yaml
from audit_flat_palette import identical, train_rows
from profile_raw_kernel_inference import model_hash

import demosaic.train as training
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main(config_path, parent, output):
    os.nice(5)
    torch.set_num_threads(2)
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    assert psutil.virtual_memory().available / 2**30 > 32
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    assert shutil.disk_usage(output).free > 128 * 2**30
    parent_sha = sha(parent)
    source = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    template = yaml.safe_load(Path(config_path).read_text())
    template.update(
        device="cpu",
        precision="float32",
        amp=False,
        channels_last=False,
        batch_size=1,
        patch_size=64,
        cpu_threads=2,
        workers=0,
        paired_workers=0,
        raw_clean_workers=0,
        steps=4000,
        warmup_steps=100,
        seed=48,
        log_every=1,
        trace_observations=True,
        checkpoint_every=4,
        validation_images=1,
        val_batches=1,
        min_available_gb=24,
        data_seed_per_step=True,
        experiment_notes="Discarded reconstruction-objective CPU engineering fixture only",
    )
    assert template["paired_fraction"] == template["raw_clean_fraction"] == 0.25
    template.pop("normalization_augmentation", None)
    plan = {
        "config": {"path": str(config_path), "sha256": sha(config_path)},
        "parent": {"path": str(parent), "sha256": parent_sha},
        "source_files": source,
        "driver_sha256": sha(__file__),
        "template": template,
        "scope": "Four discarded updates per arm/B1/native64/CPU FP32/workers0 on the cleaned84867-source corpus. "
        "Real parent, frozen genuine DINO, actual Commons/native/paired data. "
        "Uninterrupted vs2+2 resume and matched policy-off observation hashes. "
        "No GPU, production launch, convergence, timing or quality claim.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    shutil.copyfile(__file__, output / "source.py")
    parent_state = torch.load(parent, map_location="cpu", weights_only=True, mmap=True)
    constructor = training.JointDemosaic
    current, expected, starts = {}, {}, []

    def instrument(config):
        net = constructor(config)
        current["model"] = net
        seen = False

        def first_forward(module, args, kwargs):
            nonlocal seen
            if seen:
                return
            seen = True
            actual = module.restoration_state_dict()
            assert actual.keys() == expected["weights"].keys()
            for key in actual:
                assert torch.equal(actual[key], expected["weights"][key]), key
            assert all(
                not p.requires_grad and p.grad is None for p in module.context.backbone.parameters()
            )
            current["DINO_hash"] = model_hash(module.context.backbone)
            starts.append(
                {
                    "leg": expected["leg"],
                    "initial_weights_exact": True,
                    "DINO_hash": current["DINO_hash"],
                }
            )

        net.register_forward_pre_hook(first_forward, with_kwargs=True)
        return net

    rows, checkpoints = {}, {}
    try:
        training.JointDemosaic = instrument
        for label, policy, resumed in [
            ("control", "charbonnier-v1", False),
            ("logmse-full", "image-log-mse-v1", False),
            ("logmse-resumed", "image-log-mse-v1", True),
        ]:
            cfg = {**template, "run": str(output / label), "reconstruction_objective": policy}
            path = output / (label + ".yaml")
            path.write_text(yaml.safe_dump(cfg))
            expected.update(weights=parent_state["ema"], leg=label + "-initial")
            checkpoint = training.train(path, initialize=parent, stop_after=2 if resumed else 4)
            net = current.pop("model")
            assert model_hash(net.context.backbone) == current["DINO_hash"]
            assert all(p.grad is None for p in net.context.backbone.parameters())
            del net
            gc.collect()
            if resumed:
                step2 = output / "logmse-resumed-step2.pt"
                shutil.copyfile(checkpoint, step2)
                middle = torch.load(step2, map_location="cpu", weights_only=True, mmap=True)
                expected.update(weights=middle["model"], leg=label + "-resume-model")
                checkpoint = training.train(path, resume=step2, stop_after=2)
                net = current.pop("model")
                assert model_hash(net.context.backbone) == current["DINO_hash"]
                assert all(p.grad is None for p in net.context.backbone.parameters())
                del net, middle
                gc.collect()
            state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
            assert state["step"] == 4 and state["config"]["steps"] == 4000
            assert len(state["model"]) == len(state["ema"]) == 91
            assert len(state["optimizer"]["state"]) == 89
            for group in ["model", "ema"]:
                assert all(torch.isfinite(v).all() for v in state[group].values())
            for item in state["optimizer"]["state"].values():
                assert float(item["step"]) == 4
                assert all(
                    torch.isfinite(v).all() for v in item.values() if isinstance(v, torch.Tensor)
                )
            rows[label] = train_rows(output / label)
            assert [r["domain"] for r in rows[label]] == [
                "synthetic",
                "synthetic",
                "native-RAW-synthetic",
                "paired-RAW",
            ]
            assert all(
                math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"]) for r in rows[label]
            )
            assert state["config"]["reconstruction_objective"] == policy
            assert all("normalization_mask" not in r for r in rows[label])
            checkpoints[label] = {"path": str(checkpoint), "sha256": sha(checkpoint)}
            del state
            gc.collect()
    finally:
        training.JointDemosaic = constructor
    full, resumed = [
        torch.load(checkpoints[label]["path"], map_location="cpu", weights_only=True, mmap=True)
        for label in ["logmse-full", "logmse-resumed"]
    ]
    exact = [
        "model_config",
        "model",
        "ema",
        "optimizer",
        "python_rng",
        "torch_rng",
        "cuda_rng",
        "best",
        "step",
    ]
    for field in exact:
        identical(full[field], resumed[field])
    for label, values in rows.items():
        assert [r["batch_sha256"] for r in values] == [r["batch_sha256"] for r in rows["control"]]
    for a, b in zip(rows["logmse-full"], rows["logmse-resumed"], strict=True):
        identical(
            {k: v for k, v in a.items() if k != "seconds_per_step"},
            {k: v for k, v in b.items() if k != "seconds_per_step"},
        )
    assert source == {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    assert sha(parent) == parent_sha and not torch.cuda.is_initialized()
    receipt = {
        "status": "completed-genuine-parent-CPU-reconstruction-objective-preflight",
        "plan": {"path": str(output / "plan.json"), "sha256": sha(output / "plan.json")},
        "initial_weight_and_DINO_checks": starts,
        "exact_resume_fields": exact,
        "all_four_observation_hashes_match_control": True,
        "default_objective": "charbonnier-v1",
        "new_objective": "image-log-mse-v1",
        "finite_state_counts": {"model": 91, "EMA": 91, "AdamW": 89},
        "observations": rows,
        "checkpoints": checkpoints,
        "CUDA_initialized": False,
        "production_training_started": False,
        "limits": plan["scope"],
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": str(output / "receipt.json"), "status": receipt["status"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--initialize", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.config, args.initialize, args.output)
