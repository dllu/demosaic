"""CPU operand-precision feasibility, not a Tensor Core/GPU accuracy emulator.

Three FP32 convolutions use high/low TF32 operands and omit low*low. CPU
accumulation/order differs from Triton MMA; actual kernel accuracy and speed
remain separate mandatory measurements. No production inference path is changed.
"""

import argparse
import hashlib
import json
import os
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import psutil
import torch
from torch import nn
from torch.nn import functional as F

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def round_tf32(value, *, nearest=True):
    """CPU finite normal/zero F32 -> 10 fraction bits, RNA or toward zero.

    RNA rounds a halfway value away from zero, matching the high conversion
    selected by the inspected Triton3.8 TF32x3 lowering. Low operands here use
    truncation, as a declared proxy for their reduced-precision MMA operands.
    Subnormals/overflow are rejected rather than assigning hardware semantics.
    """
    if value.device.type != "cpu" or value.dtype != torch.float32:
        raise ValueError("CPU float32 operands required")
    if not torch.isfinite(value).all():
        raise ValueError("Only finite operands are covered")
    if ((value != 0) & (value.abs() < torch.finfo(torch.float32).tiny)).any():
        raise ValueError("Subnormal operand semantics are outside this CPU proxy")
    bits = value.contiguous().view(torch.int32)
    rounded = ((bits + (4096 if nearest else 0)) & -8192).view(torch.float32)
    if not torch.isfinite(rounded).all():
        raise ValueError("TF32 rounding overflow is outside this CPU proxy")
    return rounded


def split_tf32(value):
    high = round_tf32(value)
    return high, round_tf32(value - high, nearest=False)


def operand_convolution(value, high, low, *, stride=1, padding=0, three=True):
    """Three rounded-operand CPU convolutions, with FP32 outputs throughout."""
    a, b = split_tf32(value)
    big = F.conv2d(a, high, stride=stride, padding=padding)
    if not three:
        return big
    small = F.conv2d(b, high, stride=stride, padding=padding)
    small = small + F.conv2d(a, low, stride=stride, padding=padding)
    return big + small


@contextmanager
def hidden_operand_precision(network, *, three=True):
    """Temporarily replace hidden dense Conv2d calls; retain parameters/keys."""
    if torch.is_grad_enabled() or network.training:
        raise ValueError("This CPU inference probe requires eval and disabled gradients")
    selected = [
        (name, layer)
        for name, layer in network.named_modules()
        if isinstance(layer, nn.Conv2d) and name not in ("m_head", "m_tail")
    ]
    for _, layer in selected:
        if (
            layer.weight.device.type != "cpu"
            or layer.weight.dtype != torch.float32
            or layer.groups != 1
            or layer.bias is not None
            or layer.dilation != (1, 1)
            or layer.padding_mode != "zeros"
            or "forward" in layer.__dict__
        ):
            raise ValueError("Only unmodified dense bias-free CPU FP32 convolutions are covered")
    changed = []
    try:
        for name, layer in selected:
            high, low = split_tf32(layer.weight)

            def forward(value, high=high, low=low, stride=layer.stride, padding=layer.padding):
                return operand_convolution(
                    value, high, low, stride=stride, padding=padding, three=three
                )

            layer.forward = forward
            changed.append(layer)
        yield [name for name, _ in selected]
    finally:
        for layer in reversed(changed):
            del layer.forward


def model_digest(model):
    digest = hashlib.sha256()
    for name, value in model.state_dict().items():
        digest.update(name.encode())
        digest.update(value.detach().contiguous().numpy().tobytes())
    return digest.hexdigest()


def difference(actual, reference):
    error = (actual.double() - reference.double()) * 65535
    return {"maximum_DN16": error.abs().max().item(), "RMS_DN16": error.square().mean().sqrt().item()}


@torch.inference_mode()
def main(plan_path):
    os.nice(10)
    torch.set_num_threads(2)
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    plan_path = Path(plan_path).resolve()
    plan = json.loads(plan_path.read_text())
    assert ref(__file__) == plan["worker"]
    for item in [*plan["runtime_files"], *plan["observations"], plan["inspected_compiler_source"]]:
        assert ref(item["path"]) == item
    assert psutil.virtual_memory().available > 48 * 2**30
    output = writable_path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    (output / "source").mkdir()
    for item in [plan["worker"], *plan["runtime_files"], plan["inspected_compiler_source"]]:
        source = Path(item["path"])
        (output / "source" / source.name).write_bytes(source.read_bytes())
    (output / "plan.json").write_bytes(plan_path.read_bytes())
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    (output / "status.json").write_text(json.dumps({"status": "running-CPU-operand-proxy", "owner": owner}) + "\n")
    cases = []
    for label, checkpoint in plan["checkpoints"].items():
        assert ref(checkpoint["path"]) == checkpoint
        model, state = load_checkpoint(checkpoint["path"], "cpu")
        model.eval()
        assert model.config.restoration_backbone == "pretrained-rgb"
        step = state["step"]
        del state
        before = model_digest(model)
        identities = {name: id(value) for name, value in model.named_parameters()}
        keys = list(model.state_dict())
        for index, observation in enumerate(plan["observations"]):
            with np.load(observation["path"], allow_pickle=False) as arrays:
                batch = {key: torch.from_numpy(arrays[key].copy()) for key in arrays.files}
            args = [batch[key] for key in ("packed", "variance", "colors", "wb", "matrix")]
            assert batch["target"].shape == (1, 3, 256, 256)
            model.set_noise(plan["conditioning"]["shot"], plan["conditioning"]["read"])
            rng = torch.get_rng_state().clone()
            with amp_context("cpu", dtype="float32"):
                baseline = model(*args)
                predictions = {"IEEE": baseline}
                for mode, three in [("high-only", False), ("three-products", True)]:
                    with hidden_operand_precision(model.pretrained_rgb.network, three=three) as names:
                        assert len(names) == 59
                        prediction = model(*args)
                        if three:
                            assert torch.equal(prediction, model(*args))
                    assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
                    predictions[mode] = prediction
                assert torch.equal(baseline, model(*args))
            assert torch.equal(rng, torch.get_rng_state())
            assert identities == {name: id(value) for name, value in model.named_parameters()}
            assert keys == list(model.state_dict()) and model_digest(model) == before
            target = output / f"{label}-photo{index}-CPU-proxies.npz"
            np.savez(target, **{key: value.numpy() for key, value in predictions.items()})
            result = {"model": label, "checkpoint": checkpoint, "step": step, "observation": observation,
                      "arrays": ref(target), "high_only": difference(predictions["high-only"], baseline),
                      "three_products": difference(predictions["three-products"], baseline),
                      "hidden_convolutions_replaced": names, "head_tail_transpose_context_physics_unchanged": True,
                      "exact_three_product_repeat": True, "exact_original_after_context": True,
                      "parameter_keys_identities_and_state_unchanged": True, "Torch_RNG_unchanged": True}
            cases.append(result)
            with (output / "cases.jsonl").open("a") as stream:
                stream.write(json.dumps(result, allow_nan=False) + "\n")
            print(json.dumps({key: result[key] for key in ("model", "step", "high_only", "three_products")}), flush=True)
        assert ref(checkpoint["path"]) == checkpoint
        del model
    for item in [*plan["runtime_files"], plan["worker"], *plan["observations"]]:
        assert ref(item["path"]) == item
    assert not torch.cuda.is_initialized()
    receipt = {"status": "completed-genuine-mature-CPU-operand-precision-proxy-not-GPU-parity", "plan": ref(plan_path), "owner": owner, "cases": cases,
               "maximum_three_product_DN16": max(case["three_products"]["maximum_DN16"] for case in cases),
               "maximum_three_product_RMS_DN16": max(case["three_products"]["RMS_DN16"] for case in cases),
               "CUDA_initialized": False, "scope": plan["scope"]}
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    (output / "status.json").write_text(json.dumps({"status": receipt["status"], "owner": owner}) + "\n")
    print(json.dumps({"receipt": ref(output / "receipt.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
