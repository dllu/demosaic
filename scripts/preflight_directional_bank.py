"""Discarded genuine-parent checks for candidate-bank context in directional mixing."""

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
from audit_flat_palette import identical, train_rows
from preflight_camera_supervision import sha
from profile_raw_kernel_inference import model_hash

import demosaic.train as training
from demosaic.model import ModelConfig
from demosaic.safety import writable_path


def main(config_path, parent_path, output, device_name, cpu_receipt=None):
    os.nice(5)
    torch.set_num_threads(2 if device_name == "cpu" else 4)
    assert psutil.virtual_memory().available > 40 * 2**30
    assert shutil.disk_usage(Path.cwd()).free > 128 * 2**30
    cpu = device_name == "cpu"
    if cpu:
        assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    else:
        assert (
            json.loads(cpu_receipt.read_text())["status"]
            == "completed-directional-bank-CPU-preflight"
        )
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    source = {str(p.resolve()): sha(p) for p in Path("src/demosaic").glob("*.py")}
    cfg = yaml.safe_load(config_path.read_text())
    assert cfg["model"]["raw_directional_residual"] is True
    assert cfg["camera_supervision"] == "sensor-valid-v1"
    assert cfg["raw_directional_lr_multiplier"] == 20
    cfg.update(
        log_every=1,
        checkpoint_every=4 if cpu else 6,
        validation_images=1,
        val_batches=1,
        min_available_gb=24,
        training_execution="deterministic-v1",
    )
    if cpu:
        cfg.update(
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
            seed=48,
        )
    else:
        assert (cfg["batch_size"], cfg["patch_size"], cfg["precision"], cfg["seed"]) == (
            16,
            256,
            "bfloat16",
            51,
        )
    inputs = [config_path, parent_path] + [
        Path(cfg[k])
        for k in (
            "manifest",
            "validation_manifest",
            "paired_manifest",
            "raw_clean_manifest",
            "validation_protocol",
        )
    ]
    if cpu_receipt:
        inputs.append(cpu_receipt)
    prior_checkpoint = (
        Path(".cache/benchmarks/training-execution-mixed-v1/work/runs")
        / ("cpu-strict" if cpu else "cuda-strict-a")
        / "last.pt"
    )
    inputs.append(prior_checkpoint)
    plan = {
        "source_files": source,
        "inputs": [{"path": str(p.resolve()), "sha256": sha(p)} for p in inputs],
        "worker_sha256": sha(__file__),
        "template": cfg,
        "scope": "Discarded genuine V63 EMA mixed Commons/native/paired bank-context engineering. "
        + (
            "CPU B1/native64/FP32, four updates and exact2+2 restart. "
            if cpu
            else "CUDA B16/native256/BF16, six updates per arm. "
        )
        + "No convergence, restoration-quality or stable throughput claim.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    shutil.copyfile(__file__, output / "source.py")
    parent = torch.load(parent_path, map_location="cpu", weights_only=True, mmap=True)
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    previous_quota = None
    if not cpu:
        device = torch.device("cuda", torch.cuda.current_device())
        previous_quota = torch.cuda.get_per_process_memory_fraction(device)
        total = torch.cuda.get_device_properties(device).total_memory
        torch.cuda.set_per_process_memory_fraction(min(previous_quota, 24 * 2**30 / total), device)
    constructor, optimizer_for, prepare = (
        training.JointDemosaic,
        training.make_optimizer,
        training.prepare_training_batch,
    )
    current, starts, gradients, results, observations = {}, [], [], {}, {}
    clip = torch.nn.utils.clip_grad_norm_
    common_first_gradients = {}

    def checked_clip(parameters, *args, **kwargs):
        parameters = list(parameters)
        if not current["resuming"] and len(observations[current["label"]]) == 1:
            for name, parameter in current["model"].named_parameters():
                if not parameter.requires_grad or name.startswith(
                    "pretrained_rgb.raw_directional.bank."
                ):
                    continue
                value = parameter.grad.detach().cpu().clone()
                if current["label"] == "control":
                    common_first_gradients[name] = value
                else:
                    assert torch.equal(value, common_first_gradients[name]), name
            if current["bank_enabled"]:
                assert (
                    current["model"]
                    .pretrained_rgb.raw_directional.bank[-1]
                    .weight.grad.count_nonzero()
                )
        return clip(parameters, *args, **kwargs)

    def instrument(options):
        net = constructor(options)
        current["model"] = net

        def first_forward(model, args, kwargs, result):
            handle.remove()
            actual = model.restoration_state_dict()
            expected = current["expected"]
            assert all(torch.equal(actual[k].cpu(), v) for k, v in expected.items())
            assert len(actual) == 99 + 6 * current["bank_enabled"]
            if not current["resuming"]:
                branch = model.pretrained_rgb.raw_directional
                assert all(
                    p.count_nonzero() == 0
                    for n, p in branch.named_parameters()
                    if not n.startswith(("local.", "bank."))
                )
                if branch.bank is not None:
                    assert all(p.count_nonzero() == 0 for p in branch.bank[-1].parameters())
                model.pretrained_rgb.raw_directional = None
                try:
                    with torch.no_grad():
                        baseline = model(*args, **kwargs)
                finally:
                    model.pretrained_rgb.raw_directional = branch
                pairs = (
                    zip(result, baseline, strict=True)
                    if isinstance(result, tuple)
                    else [(result, baseline)]
                )
                assert all(torch.equal(a, b) for a, b in pairs)
            current["DINO_hash"] = model_hash(model.context.backbone)
            starts.append(
                {
                    "case": current["label"],
                    "resume": current["resuming"],
                    "actual_common_weights_exact": True,
                    "initial_output_exact_parent": not current["resuming"],
                    "branch_sha256": model_hash(model.pretrained_rgb.raw_directional),
                    "local_sha256": model_hash(model.pretrained_rgb.raw_directional.local),
                    "bank_enabled": current["bank_enabled"],
                    "DINO_sha256": current["DINO_hash"],
                }
            )

        handle = net.register_forward_hook(first_forward, with_kwargs=True)
        return net

    def make_optimizer(model, options):
        optimizer = optimizer_for(model, options)
        assert [g["lr_multiplier"] for g in optimizer.param_groups] == [1, 20]

        def before_step(*args):
            active = [p for p in model.parameters() if p.requires_grad]
            assert len(active) == 97 + 6 * current["bank_enabled"]
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in active)
            assert all(
                not p.requires_grad and p.grad is None for p in model.context.backbone.parameters()
            )
            gradients.append({"case": current["label"], "finite_gradients": len(active)})

        optimizer.register_step_pre_hook(before_step)
        return optimizer

    def observe(*args, **kwargs):
        batch = prepare(*args, **kwargs)
        observations[current["label"]].append(
            {
                "step": args[0],
                "domain": args[1],
                "legacy_sha256": training.batch_fingerprint(
                    {k: v for k, v in batch.items() if k != "sensor_target"}
                ),
                "input_sha256": training.batch_fingerprint(
                    {
                        k: batch[k]
                        for k in ["packed", "variance", "colors", "wb", "matrix", "shot", "read"]
                    }
                ),
            }
        )
        return batch

    def finish_model():
        net = current.pop("model")
        assert model_hash(net.context.backbone) == current["DINO_hash"]
        assert all(
            not p.requires_grad and p.grad is None for p in net.context.backbone.parameters()
        )

    try:
        training.JointDemosaic, training.make_optimizer, training.prepare_training_batch = (
            instrument,
            make_optimizer,
            observe,
        )
        torch.nn.utils.clip_grad_norm_ = checked_clip
        cases = [("control", False, False), ("bank", True, False)]
        if cpu:
            cases.append(("resumed", True, True))
        for label, bank_enabled, resume in cases:
            observations[label] = []
            current.update(
                label=label, expected=parent["ema"], resuming=False, bank_enabled=bank_enabled
            )
            options = {
                **cfg,
                "model": {**cfg["model"], "raw_directional_bank_context": bank_enabled},
                "run": str(output / label),
            }
            path = output / (label + ".yaml")
            path.write_text(yaml.safe_dump(options))
            if not cpu:
                torch.cuda.reset_peak_memory_stats()
            with (output / (label + ".log")).open("w") as log, redirect_stdout(log):
                checkpoint = training.train(
                    path, initialize=parent_path, stop_after=2 if resume else 4 if cpu else 6
                )
                finish_model()
                gc.collect()
                if resume:
                    middle_path = output / "step2.pt"
                    shutil.copyfile(checkpoint, middle_path)
                    middle = torch.load(
                        middle_path, map_location="cpu", weights_only=True, mmap=True
                    )
                    current.update(expected=middle["model"], resuming=True)
                    checkpoint = training.train(path, resume=middle_path, stop_after=2)
                    finish_model()
                    del middle
                    gc.collect()
            state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
            steps = 4 if cpu else 6
            assert state["step"] == steps and state["config"]["steps"] == 4000
            assert len(state["model"]) == len(state["ema"]) == 99 + 6 * bank_enabled
            assert len(state["optimizer"]["state"]) == 97 + 6 * bank_enabled
            assert state["config"]["reference_interval_weight"] == 0
            assert state["model_config"]["raw_directional_bank_context"] is bank_enabled
            for field in ("model", "ema"):
                assert all(torch.isfinite(v).all() for v in state[field].values())
            for item in state["optimizer"]["state"].values():
                assert int(item["step"]) == steps
                assert all(
                    torch.isfinite(v).all() for v in item.values() if isinstance(v, torch.Tensor)
                )
            rows = train_rows(output / label)
            assert len(rows) == steps and {r["domain"] for r in rows} == {
                "synthetic",
                "native-RAW-synthetic",
                "paired-RAW",
            }
            assert all(math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"]) for r in rows)
            results[label] = {
                "checkpoint": {"path": str(checkpoint), "sha256": sha(checkpoint)},
                "rows": rows,
                "finite_states": {
                    "model": 99 + 6 * bank_enabled,
                    "EMA": 99 + 6 * bank_enabled,
                    "AdamW": 97 + 6 * bank_enabled,
                },
                "peak_CUDA_bytes": 0 if cpu else torch.cuda.max_memory_allocated(),
            }
            del state
            gc.collect()
            if not cpu:
                torch.cuda.empty_cache()
        if cpu:
            states = [
                torch.load(
                    results[k]["checkpoint"]["path"],
                    map_location="cpu",
                    weights_only=True,
                    mmap=True,
                )
                for k in ("bank", "resumed")
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
            for key in exact:
                identical(states[0][key], states[1][key])
            for a, b in zip(results["bank"]["rows"], results["resumed"]["rows"], strict=True):
                identical(
                    {k: v for k, v in a.items() if k != "seconds_per_step"},
                    {k: v for k, v in b.items() if k != "seconds_per_step"},
                )
            results["exact_resume_fields"] = exact
        prior = torch.load(prior_checkpoint, map_location="cpu", weights_only=True, mmap=True)
        actual = torch.load(
            results["control"]["checkpoint"]["path"],
            map_location="cpu",
            weights_only=True,
            mmap=True,
        )
        default_exact = [
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
        for key in default_exact:
            if key == "model_config":
                assert (
                    ModelConfig.from_checkpoint(actual[key]).to_dict()
                    == ModelConfig.from_checkpoint(prior[key]).to_dict()
                )
            else:
                identical(actual[key], prior[key])
        results["disabled_default_exact_fields"] = default_exact
    finally:
        torch.nn.utils.clip_grad_norm_ = clip
        training.JointDemosaic, training.make_optimizer, training.prepare_training_batch = (
            constructor,
            optimizer_for,
            prepare,
        )
        if previous_quota is not None:
            torch.cuda.set_per_process_memory_fraction(previous_quota, device)
    for values in observations.values():
        assert values == observations["control"]
    assert len({s["local_sha256"] for s in starts if not s["resume"]}) == 1
    assert len({s["DINO_sha256"] for s in starts}) == 1
    assert source == {str(p.resolve()): sha(p) for p in Path("src/demosaic").glob("*.py")}
    assert all(sha(i["path"]) == i["sha256"] for i in plan["inputs"])
    receipt = {
        "status": "completed-directional-bank-" + ("CPU" if cpu else "CUDA-B16") + "-preflight",
        "plan": {"path": str(output / "plan.json"), "sha256": sha(output / "plan.json")},
        "initializations": starts,
        "gradient_checks": gradients,
        "initial_unclipped_common_gradients_exact": len(common_first_gradients),
        "cases": results,
        "matched_observations": observations,
        "scope": plan["scope"],
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--initialize", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], required=True)
    parser.add_argument("--cpu-receipt", type=Path)
    args = parser.parse_args()
    main(args.config, args.initialize, args.output, args.device, args.cpu_receipt)
