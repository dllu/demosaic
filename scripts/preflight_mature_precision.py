"""Freeze and run genuine mature-weight CPU precision engineering checks."""

import argparse
import gc
import os
import random
import shutil
from pathlib import Path

import numpy as np
import psutil
import yaml
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
ORIGINAL = Path("/mnt/external/demosaic/benchmarks/mature-cudnn-autotune-v2/plan.json")
KEYS = ("packed", "variance", "colors", "wb", "matrix")


def prepare(root):
    import torch

    from demosaic.suite import observation

    assert not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    root = root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    root.mkdir(parents=True, exist_ok=False)
    work = root / "work"
    for directory in ["src/demosaic", "scripts"]:
        for source in (REPO / directory).glob("*.py"):
            target = work / directory / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for name in [
        "pyproject.toml",
        "uv.lock",
        "configs/evaluation.yaml",
        "docs/mature-mixed-precision-pilot.md",
        "tests/test_mature_precision_tools.py",
    ]:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    inputs_dir = work / "inputs"
    inputs_dir.mkdir()
    protocol = yaml.safe_load((work / "configs/evaluation.yaml").read_text())
    y, x = torch.meshgrid(torch.arange(64), torch.arange(80), indexing="ij")
    rgb = torch.stack(
        (
            0.02 + 0.4 * (x + y / 64) / 80,
            0.03 + 0.35 * y / 64,
            0.18 * (1 + 0.02 * torch.cos(2 * torch.pi * x / 4)),
        )
    )[None]
    conditions = [
        protocol["conditions"][0],
        next(c for c in protocol["conditions"] if c["name"] == "iso12800-prior"),
    ]
    assert conditions[0]["name"] == "adc-only"
    fixtures = []
    for pattern in ["RGGB", "BGGR", "GRBG", "GBRG"]:
        for condition in conditions:
            batch = observation(
                rgb,
                ["fixed-mature-precision-engineering"],
                condition,
                pattern,
                protocol["white_balance"],
                protocol["camera_to_srgb"],
                20261020,
            )
            variants = [("base", batch)]
            if condition["name"] == "adc-only":
                shifted = dict(batch, packed=batch["packed"] + 1 / 65535)
                assert shifted["packed"].max() < 1
                variants.append(("plus-one-DN", shifted))
            for variant, values in variants:
                label = pattern + "-" + condition["name"] + "-" + variant
                path = inputs_dir / (label + ".npz")
                np.savez(path, **{k: values[k].numpy() for k in KEYS})
                fixtures.append(
                    {
                        "id": label,
                        "pattern": pattern,
                        "condition": condition,
                        "variant": variant,
                        "arrays": ref(path),
                    }
                )
    old = read(ORIGINAL)
    output = work / "CPU-output"
    plan = {
        "root": str(root),
        "work": str(work),
        "output": str(output),
        "models": old["models"],
        "fixtures": fixtures,
        "python": str(REPO / ".venv/bin/python3"),
        "HF_HOME": str(REPO / ".cache/huggingface"),
        "worker": ref(work / "scripts/preflight_mature_precision.py"),
        "protocol": ref(work / "docs/mature-mixed-precision-pilot.md"),
        "inputs": [
            ref(ORIGINAL),
            *old["models"].values(),
            *old["pinned_offline_backbone_files"],
            ref("/mnt/external/demosaic/mature-precision-policy-tests-v2.xml"),
        ],
        "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
        "scope": "Genuine CPU FP32/explicit half emulation only; no CUDA inference, timing or model-quality claim.",
    }
    # Model records also carry the expected historical step; guards use path/hash only.
    plan["inputs"] = [{"path": r["path"], "sha256": r["sha256"]} for r in plan["inputs"]]
    guard(plan)
    save(root / "plan.json", plan)
    print({"plan": ref(root / "plan.json"), "fixtures": len(fixtures)})


def worker(plan_path):
    import torch
    from mature_precision_tools import POLICIES, precision_policy
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.precision import amp_context
    from demosaic.train import batch_fingerprint

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    os.nice(10)
    torch.set_num_threads(2)
    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["worker"]
    assert psutil.virtual_memory().available > 32 * 2**30
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    records = []
    for fixture in plan["fixtures"]:
        with np.load(fixture["arrays"]["path"], allow_pickle=False) as arrays:
            args = {k: torch.from_numpy(arrays[k].copy()) for k in KEYS}
        records.append((fixture, args, batch_fingerprint(args)))
    assert len(records) == 12
    results = []
    with torch.inference_mode():
        for label, checkpoint in plan["models"].items():
            model, state = load_checkpoint(checkpoint["path"], "cpu")
            assert (
                state["loaded_sha256"] == checkpoint["sha256"]
                and state["step"] == checkpoint["step"]
            )
            del state
            model.eval()
            before, dino_before = model_hash(model), model_hash(model.context.backbone)
            config = model.config.to_dict()
            identities = [id(p) for p in model.parameters()]
            rng, py_rng = torch.get_rng_state().clone(), random.getstate()
            events, encoder_calls = [], []
            network = model.pretrained_rgb.network
            handles = [
                model.context.backbone.register_forward_hook(
                    lambda *_, calls=encoder_calls: calls.append(True)
                )
            ]
            for key, module in [
                ("physical_head", network.m_head),
                ("first_encoder", network.m_down1),
                ("middle", network.m_body),
                ("physical_tail", network.m_tail),
            ]:
                handles.append(
                    module.register_forward_pre_hook(
                        lambda _m, args, key=key, events=events: events.append(
                            {"name": key, "dtype": str(args[0].dtype)}
                        )
                    )
                )
            arrays, policies, unique_codes, responses = {}, [], {}, []
            try:
                for policy in POLICIES:
                    for fixture, inputs, digest in records:
                        model.set_noise(fixture["condition"]["shot"], fixture["condition"]["read"])
                        start = len(events)
                        with precision_policy(model, policy, "cpu", cpu_probe=True) as active:
                            prediction = model(*(inputs[k] for k in KEYS))
                        assert (
                            prediction.shape == (1, 3, 64, 80)
                            and prediction.dtype == torch.float32
                            and torch.isfinite(prediction).all()
                        )
                        observed = {r["name"]: r["dtype"] for r in events[start:]}
                        assert observed == {
                            "physical_head": "torch.float32",
                            "first_encoder": "torch.float16"
                            if policy == "fp16-hidden"
                            else "torch.float32",
                            "middle": "torch.float32",
                            "physical_tail": "torch.float32",
                        }, observed
                        assert not network.hidden_autocast and model.config.to_dict() == config
                        assert batch_fingerprint(inputs) == digest
                        arrays[policy, fixture["id"]] = prediction.clone()
                        path = output / (label + "-" + policy + "-" + fixture["id"] + ".npy")
                        np.save(path, prediction.numpy(), allow_pickle=False)
                        policies.append(
                            {
                                "policy": policy,
                                "fixture": fixture["id"],
                                "prediction": ref(path),
                                "dtypes": observed,
                                "active_policy": active,
                                "input_sha256": digest,
                            }
                        )
                        if (
                            fixture["condition"]["name"] == "adc-only"
                            and fixture["variant"] == "base"
                        ):
                            count = torch.unique((prediction.clamp(0, 1) * 65535).round()).numel()
                            assert count > 256
                            unique_codes[policy + ":" + fixture["pattern"]] = count
                    for pattern in ["RGGB", "BGGR", "GRBG", "GBRG"]:
                        delta = (
                            arrays[policy, pattern + "-adc-only-plus-one-DN"]
                            - arrays[policy, pattern + "-adc-only-base"]
                        )
                        rms = float(delta.double().square().mean().sqrt())
                        assert rms > 0 and torch.isfinite(delta).all()
                        responses.append(
                            {"policy": policy, "pattern": pattern, "one_DN_response_RMS": rms}
                        )
                fixture, inputs, _ = records[0]
                model.set_noise(fixture["condition"]["shot"], fixture["condition"]["read"])
                with (
                    precision_policy(model, "fp16-hidden", "cpu", cpu_probe=True),
                    amp_context("cpu", dtype="float32"),
                ):
                    identity = model(*(inputs[k] for k in KEYS))
                assert torch.equal(identity, arrays["fp32", fixture["id"]])
                with precision_policy(model, "fp16-hidden", "cpu", cpu_probe=True):
                    repeat = model(*(inputs[k] for k in KEYS))
                assert torch.equal(repeat, arrays["fp16-hidden", fixture["id"]])
                assert len(encoder_calls) == 38
            finally:
                for handle in handles:
                    handle.remove()
            assert model_hash(model) == before and model_hash(model.context.backbone) == dino_before
            assert [
                id(p) for p in model.parameters()
            ] == identities and model.config.to_dict() == config
            assert torch.equal(torch.get_rng_state(), rng) and random.getstate() == py_rng
            assert all(
                not p.requires_grad and p.grad is None for p in model.context.backbone.parameters()
            )
            assert not torch.cuda.is_initialized()
            results.append(
                {
                    "label": label,
                    "checkpoint": checkpoint,
                    "model_sha256": before,
                    "DINO_sha256": dino_before,
                    "policies": policies,
                    "native_codes": unique_codes,
                    "one_DN_responses": responses,
                    "common_forwards": len(encoder_calls),
                    "explicit_FP32_hidden_identity_exact": True,
                    "CPU_repeat_exact": True,
                    "state_parameter_config_RNG_exact": True,
                }
            )
            save(output / (label + "-receipt.json"), results[-1])
            del model, arrays
            gc.collect()
    guard(plan)
    save(
        output / "receipt.json",
        {
            "status": "completed-genuine-mature-precision-CPU-engineering-no-quality-or-speed-result",
            "plan": ref(plan_path),
            "models": results,
            "common_forwards": sum(r["common_forwards"] for r in results),
            "CUDA_initialized": torch.cuda.is_initialized(),
            "owner": {"pid": psutil.Process().pid, "created": psutil.Process().create_time()},
            "scope": "CPU emulation and state/dtype/code-sensitivity proof only. No CUDA precision/performance claim, full-frame result, training or promotion.",
        },
    )
    print({"receipt": ref(output / "receipt.json"), "models": len(results), "forwards": 76})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="mode", required=True)
    p = modes.add_parser("prepare")
    p.add_argument("root", type=Path)
    p = modes.add_parser("worker")
    p.add_argument("plan", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root)
    else:
        worker(args.plan)
