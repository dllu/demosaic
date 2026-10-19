"""Isolated mature-model CUDA accuracy gate, then resident-only timing.

Refuse unfinished exact training/review owners before initializing CUDA. Never
integrate into the CLI, run full-frame exports, alter weights, or train here.
"""

import argparse
import json
import os
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import psutil
import torch
from experimental_tf32x3_conv import convolution
from probe_tf32x3_cpu import difference, ref

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context, cudnn_autotune
from demosaic.safety import writable_path


def alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def require_idle(plan):
    if any(alive(owner) for owner in plan["blocking_owners"]):
        raise RuntimeError("Exact training/review owners are live; no CUDA preflight")
    for dependency in plan["completed_dependencies"]:
        state = json.loads(Path(dependency["path"]).read_text())
        if state["status"] != dependency["status"] or state["controller"] != dependency["controller"]:
            raise RuntimeError("Successful exact training/review closure is required")
        if state["plan"] != dependency["plan"] or ref(state["plan"]["path"]) != state["plan"]:
            raise RuntimeError("Dependency plan changed")
        if state.get("child") and alive(state["child"]):
            raise RuntimeError("Dependency child is still live")
    for dependency in plan.get("required_completed_receipts", []):
        state = json.loads(Path(dependency["path"]).read_text())
        if state["status"] != dependency["status"]:
            raise RuntimeError("Completed retained-reference boards are required")


@contextmanager
def accelerated_hidden(network):
    if torch.is_grad_enabled() or network.training:
        raise ValueError("Inference eval mode with disabled gradients required")
    layers = [(name, layer) for name, layer in network.named_modules()
              if isinstance(layer, torch.nn.Conv2d) and name not in ("m_head", "m_tail")]
    for _, layer in layers:
        if (layer.groups != 1 or layer.bias is not None or layer.dilation != (1, 1)
                or layer.padding_mode != "zeros" or "forward" in layer.__dict__):
            raise ValueError("Unsupported or already modified hidden convolution")
    changed = []
    try:
        for _, layer in layers:
            def forward(value, layer=layer):
                return convolution(value, layer.weight, stride=layer.stride, padding=layer.padding)
            layer.forward = forward
            changed.append(layer)
        yield len(changed)
    finally:
        for layer in reversed(changed):
            del layer.forward


def tensors(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: torch.from_numpy(data[key].copy()) for key in data.files}


def args_on_device(batch):
    return [batch[key].cuda().contiguous(memory_format=torch.channels_last) if key in ("packed", "variance")
            else batch[key].cuda() for key in ("packed", "variance", "colors", "wb", "matrix")]


def state_hash(model):
    import hashlib
    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        digest.update(name.encode() + value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


@torch.inference_mode()
def main(plan_path):
    os.nice(10)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    require_idle(plan)
    assert ref(__file__) == plan["worker"]
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    assert psutil.virtual_memory().available > 48 * 2**30
    assert psutil.disk_usage('/mnt/external').free > 500 * 2**30
    output = writable_path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    (output / "plan.json").write_bytes(plan_path.read_bytes())
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    cases = []
    status_path = output / "status.json"

    def record(status, **fields):
        status_path.write_text(json.dumps({"status": status, "owner": owner, **fields}, allow_nan=False) + "\n")

    record("starting-isolated-CUDA-accuracy-gates")
    try:
        torch.cuda.set_per_process_memory_fraction(16 * 2**30 / torch.cuda.get_device_properties(0).total_memory, 0)
        generator = torch.Generator().manual_seed(73)
        # Fresh CPU-known inputs, exact FP64 reference, no device RNG/noisy redraw.
        for n, (shape, oc, kernel, stride, padding) in enumerate([
            ((1, 3, 7, 11), 5, 3, 1, 1), ((2, 4, 9, 5), 7, 2, 2, 0),
            ((1, 8, 4, 6), 3, 3, 1, 1), ((2, 3, 2, 2), 2, 2, 2, 0),
            ((1, 64, 3, 5), 65, 3, 1, 1),
        ]):
            x = torch.randn(shape, generator=generator).contiguous(memory_format=torch.channels_last)
            w = torch.randn((oc, shape[1], kernel, kernel), generator=generator).contiguous(memory_format=torch.channels_last)
            expected = torch.nn.functional.conv2d(x.double(), w.double(), stride=stride, padding=padding).float()
            actual = convolution(x.cuda(), w.cuda(), stride=stride, padding=padding).cpu()
            torch.testing.assert_close(actual, expected, atol=1e-4, rtol=1e-5)
            print(json.dumps({"operator_case": n, "FP64_reference_pass": True}), flush=True)
        for label, checkpoint in plan["checkpoints"].items():
            model, state = load_checkpoint(checkpoint["path"], "cuda")
            model.eval().to(memory_format=torch.channels_last)
            step = state["step"]
            del state
            before, identities = state_hash(model), {k: id(v) for k, v in model.named_parameters()}
            for fixture in plan["fixtures"]:
                batch = tensors(fixture["observation"]["path"])
                args = args_on_device(batch)
                model.set_noise(fixture["conditioning"]["shot"], fixture["conditioning"]["read"])
                rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
                with cudnn_autotune("cuda", enabled=True), amp_context("cuda", dtype="float32"):
                    baseline = model(*args)
                    with accelerated_hidden(model.pretrained_rgb.network) as count:
                        assert count == 59
                        predicted = model(*args)
                        assert torch.equal(predicted, model(*args))
                    assert torch.equal(baseline, model(*args))
                error = difference(predicted, baseline)
                target = output / f"{label}-{fixture['label']}-RGB-f32.npz"
                np.savez(target, IEEE=baseline.cpu().numpy(), candidate=predicted.cpu().numpy())
                assert torch.equal(rng, torch.get_rng_state()) and torch.equal(cuda_rng, torch.cuda.get_rng_state())
                assert torch.isfinite(predicted).all() and predicted.dtype == torch.float32
                assert state_hash(model) == before and identities == {k: id(v) for k, v in model.named_parameters()}
                case = {"model": label, "checkpoint": checkpoint, "step": step, "fixture": fixture,
                        "arrays": ref(target), "difference": error, "exact_repeat": True,
                        "exact_original_after_context": True, "RNG_unchanged": True,
                        "full_model_state_and_parameter_identities_unchanged": True}
                cases.append(case)
                with (output / "accuracy-cases.jsonl").open("a") as stream:
                    stream.write(json.dumps(case) + "\n")
                print(json.dumps({"model": label, "fixture": fixture["label"], **error}), flush=True)
                if error["maximum_DN16"] > 1 or error["RMS_DN16"] > .25:
                    record("rejected-CUDA-RGB-accuracy-no-timing-or-fullframe", cases=cases)
                    return
                del args, baseline, predicted
            assert state_hash(model) == before and identities == {k: id(v) for k, v in model.named_parameters()}
            del model
        # All six full output arrays must pass before any resident timing.
        record("all-CUDA-array-gates-passed-starting-resident-only-timing", cases=cases)
        timings = []
        serving = next(f for f in plan["fixtures"] if f["label"] == "GFX-four-native512")
        for label, checkpoint in plan["checkpoints"].items():
            model, state = load_checkpoint(checkpoint["path"], "cuda")
            model.eval().to(memory_format=torch.channels_last)
            del state
            args = args_on_device(tensors(serving["observation"]["path"]))
            model.set_noise(serving["conditioning"]["shot"], serving["conditioning"]["read"])
            before = state_hash(model)
            with cudnn_autotune("cuda", enabled=True), amp_context("cuda", dtype="float32"):
                # Warm both policies, excluding JIT/search and device startup.
                for _ in range(3):
                    model(*args)
                    with accelerated_hidden(model.pretrained_rgb.network):
                        model(*args)
                for policy in ["IEEE", "candidate", "candidate", "IEEE", "candidate", "IEEE", "IEEE", "candidate"]:
                    torch.cuda.synchronize()
                    start = time.perf_counter()
                    if policy == "candidate":
                        with accelerated_hidden(model.pretrained_rgb.network):
                            model(*args)
                    else:
                        model(*args)
                    torch.cuda.synchronize()
                    timings.append({"model": label, "policy": policy, "seconds": time.perf_counter() - start})
            assert state_hash(model) == before
            del model, args
        for item in plan["inputs"]:
            assert ref(item["path"]) == item
        receipt = {"status": "completed-isolated-TF32x3-CUDA-array-gates-and-resident-timing-awaiting-native-review",
                   "plan": ref(plan_path), "owner": owner, "cases": cases, "resident_timings": timings,
                   "scope": plan["scope"]}
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
        record(receipt["status"], receipt=ref(output / "receipt.json"))
    except BaseException as error:
        record("failed-TF32x3-CUDA-preflight-no-automatic-retry", error=repr(error), cases=cases)
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
