"""Capture fixed mature precision outputs and resident timings after prior jobs exit."""

import argparse
import gc
import os
import random
import time
from pathlib import Path

import numpy as np
import psutil
from mature_precision_execution import FIXED_EXECUTION, execution_snapshot, fixed_execution
from mature_precision_tools import POLICIES, precision_policy
from preflight_mature_precision import KEYS
from train_directional_bank_trial import guard, read, ref, save


def main(plan_path):
    policy = read(plan_path).get("execution_policy")
    if policy == FIXED_EXECUTION:
        previous = execution_snapshot()
        with fixed_execution():
            capture(plan_path)
        assert execution_snapshot() == previous
        save(
            Path(read(plan_path)["output"]) / "fixed-execution-restoration.json",
            {
                "plan": ref(plan_path),
                "receipt": ref(Path(read(plan_path)["output"]) / "receipt.json"),
                "outer_backend_settings_restored_exact": True,
                "before": previous,
                "after": execution_snapshot(),
            },
        )
        return
    if policy is not None:
        raise ValueError("Unknown research execution policy")
    return capture(plan_path)


def capture(plan_path):
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.precision import amp_context
    from demosaic.train import batch_fingerprint

    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["worker"]
    assert os.environ.get("CUDA_VISIBLE_DEVICES") != ""
    device = torch.device("cuda", torch.cuda.current_device())
    torch.set_num_threads(4)
    previous = {
        "benchmark": torch.backends.cudnn.benchmark,
        "limit": torch.backends.cudnn.benchmark_limit,
        "quota": torch.cuda.get_per_process_memory_fraction(device),
    }
    torch.cuda.set_per_process_memory_fraction(
        min(previous["quota"], 16 * 2**30 / torch.cuda.get_device_properties(device).total_memory),
        device,
    )
    torch.backends.cudnn.benchmark, torch.backends.cudnn.benchmark_limit = (
        plan.get("execution_policy") != FIXED_EXECUTION,
        10,
    )
    execution = execution_snapshot()
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    cpu_proof = read(plan["CPU_preflight"]["path"])
    models = []
    try:
        with torch.inference_mode():
            for index, (label, checkpoint) in enumerate(plan["models"].items()):
                model, state = load_checkpoint(checkpoint["path"], device)
                assert (
                    state["loaded_sha256"] == checkpoint["sha256"]
                    and state["step"] == checkpoint["step"]
                )
                del state
                model.eval().to(memory_format=torch.channels_last)
                before, dino = model_hash(model), model_hash(model.context.backbone)
                expected = next(r for r in cpu_proof["models"] if r["label"] == label)
                assert before == expected["model_sha256"] and dino == expected["DINO_sha256"]
                identities, config = [id(p) for p in model.parameters()], model.config.to_dict()
                cpu_rng, python_rng = torch.get_rng_state().clone(), random.getstate()
                cuda_rng = [r.clone() for r in torch.cuda.get_rng_state_all()]
                events, calls, captures, timings = [], [], [], []
                network = model.pretrained_rgb.network

                def hooks(model=model, network=network, calls=calls, events=events):
                    handles = [
                        model.context.backbone.register_forward_hook(
                            lambda *_, calls=calls: calls.append(True)
                        )
                    ]
                    for key, layer in [
                        ("physical_head", network.m_head),
                        ("first_encoder", network.m_down1),
                        ("middle", network.m_body),
                        ("physical_tail", network.m_tail),
                    ]:
                        handles.append(
                            layer.register_forward_pre_hook(
                                lambda _m, inputs, key=key, events=events: events.append(
                                    (key, str(inputs[0].dtype))
                                )
                            )
                        )
                    return handles

                def forward(args, policy, model=model, network=network, config=config):
                    with precision_policy(model, policy, device):
                        result = model(*args)
                    assert result.dtype == torch.float32 and torch.isfinite(result).all()
                    assert not network.hidden_autocast and model.config.to_dict() == config
                    return result

                policy_order = list(POLICIES) if index == 0 else list(reversed(POLICIES))
                handles = hooks()
                try:
                    for fixture_index, fixture in enumerate(plan["fixtures"]):
                        with np.load(fixture["arrays"]["path"], allow_pickle=False) as arrays:
                            cpu = {k: torch.from_numpy(arrays[k].copy()) for k in KEYS}
                        digest = batch_fingerprint(cpu)
                        args = [cpu[k].to(device) for k in KEYS]
                        args = [
                            v.contiguous(memory_format=torch.channels_last) if v.ndim == 4 else v
                            for v in args
                        ]
                        assert batch_fingerprint(dict(zip(KEYS, args, strict=True))) == digest
                        model.set_noise(fixture["condition"]["shot"], fixture["condition"]["read"])
                        reference = {}
                        for policy in policy_order:
                            start = len(events)
                            torch.cuda.synchronize()
                            began = time.perf_counter()
                            prediction = forward(args, policy)
                            torch.cuda.synchronize()
                            elapsed = time.perf_counter() - began
                            observed = dict(events[start:])
                            assert observed == {
                                "physical_head": "torch.float32",
                                "first_encoder": "torch.float16"
                                if policy == "fp16-hidden"
                                else "torch.float32",
                                "middle": "torch.float32",
                                "physical_tail": "torch.float32",
                            }, observed
                            assert prediction.shape[-2:] == (
                                args[0].shape[-2] * 2,
                                args[0].shape[-1] * 2,
                            )
                            array = prediction.cpu().numpy()
                            path = output / f"{label}-{policy}-fixture{fixture_index:02d}.npy"
                            np.save(path, array, allow_pickle=False)
                            captures.append(
                                {
                                    "model": label,
                                    "policy": policy,
                                    "fixture": fixture["id"],
                                    "RGB": ref(path),
                                    "dtypes": observed,
                                    "input_sha256": digest,
                                }
                            )
                            reference[policy] = array
                            if fixture["kind"] == "gfx":
                                timings.append(
                                    {
                                        "kind": "first-policy-call-in-this-process",
                                        "policy": policy,
                                        "seconds": elapsed,
                                        "includes_dtype_hooks_and_checks": True,
                                    }
                                )
                                for _ in range(2):
                                    forward(args, policy)
                        if fixture["kind"] == "gfx":
                            assert fixture_index == 0 and len(calls) == 9
                            for handle in handles:
                                handle.remove()
                            handles = []
                            # Four samples per policy; first/reverse and a balanced rotation.
                            sequence = [0, 1, 2, 2, 1, 0, 2, 0, 1, 1, 0, 2]
                            for sample, item in enumerate(sequence):
                                policy = policy_order[item]
                                torch.cuda.synchronize()
                                began = time.perf_counter()
                                with precision_policy(model, policy, device):
                                    prediction = model(*args)
                                torch.cuda.synchronize()
                                seconds = time.perf_counter() - began
                                assert (
                                    prediction.dtype == torch.float32
                                    and torch.isfinite(prediction).all()
                                )
                                array = prediction.cpu().numpy()
                                path = output / f"{label}-timed{sample:02d}-{policy}.npy"
                                np.save(path, array, allow_pickle=False)
                                timings.append(
                                    {
                                        "kind": "synchronized-resident-unhooked-sample",
                                        "policy": policy,
                                        "sample": sample,
                                        "seconds": seconds,
                                        "RGB": ref(path),
                                        "byte_equal_first_capture": np.array_equal(
                                            array, reference[policy]
                                        ),
                                    }
                                )
                            handles = hooks()
                        if fixture["kind"] == "photo" and fixture_index == 1:
                            with (
                                precision_policy(model, "fp16-hidden", device),
                                amp_context(device, dtype="float32"),
                            ):
                                identity = model(*args).cpu().numpy()
                            assert np.array_equal(identity, reference["fp32"])
                        assert batch_fingerprint(dict(zip(KEYS, args, strict=True))) == digest
                        del args, cpu, reference
                finally:
                    for handle in handles:
                        handle.remove()
                assert model_hash(model) == before and model_hash(model.context.backbone) == dino
                assert [
                    id(p) for p in model.parameters()
                ] == identities and model.config.to_dict() == config
                assert (
                    torch.equal(cpu_rng, torch.get_rng_state()) and random.getstate() == python_rng
                )
                assert all(
                    torch.equal(a, b)
                    for a, b in zip(cuda_rng, torch.cuda.get_rng_state_all(), strict=True)
                )
                assert all(
                    not p.requires_grad and p.grad is None
                    for p in model.context.backbone.parameters()
                )
                assert execution_snapshot() == execution
                assert len(captures) == len(plan["fixtures"]) * 3
                assert len(calls) == 9 + (len(plan["fixtures"]) - 1) * 3 + 1
                models.append(
                    {
                        "model": label,
                        "checkpoint": checkpoint,
                        "model_sha256": before,
                        "DINO_sha256": dino,
                        "captures": captures,
                        "timings": timings,
                        "instrumented_encoder_calls": len(calls),
                        "unhooked_timing_forwards": 12,
                        "FP32_hidden_identity_exact": True,
                        "model_config_parameter_RNG_exact": True,
                    }
                )
                save(output / (label + "-receipt.json"), models[-1])
                del model, network, hooks, forward
                gc.collect()
                torch.cuda.empty_cache()
    finally:
        torch.backends.cudnn.benchmark = previous["benchmark"]
        torch.backends.cudnn.benchmark_limit = previous["limit"]
        torch.cuda.set_per_process_memory_fraction(previous["quota"], device)
    assert torch.backends.cudnn.benchmark == previous["benchmark"]
    assert torch.backends.cudnn.benchmark_limit == previous["limit"]
    assert torch.cuda.get_per_process_memory_fraction(device) == previous["quota"]
    guard(plan)
    save(
        output / "receipt.json",
        {
            "status": "completed-mature-precision-GPU-arrays-awaiting-native-and-independent-scalar-review",
            "plan": ref(plan_path),
            "models": models,
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "backend_settings_restored": True,
            "execution_policy": plan.get("execution_policy", "original-autotune"),
            "execution_backend_settings": execution,
            "scope": "Fixed existing-weight precision outputs and resident timings only. First policy calls share per-process library caches; not isolated cold starts or pure search cost. Quality, numeric gates and timing interpretation await actual native views. No full-frame result, training, export, default change or promotion.",
        },
    )
    print(
        {
            "receipt": ref(output / "receipt.json"),
            "status": "awaiting-native-and-independent-scalar-review",
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
