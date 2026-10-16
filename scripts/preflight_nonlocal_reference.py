"""Check actual pinned CPU/CUDA reference numerics after an owned workflow exits."""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import psutil
import torch

from demosaic.nonlocal_reference import load_nonlocal_reference
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def owner_alive(controller):
    try:
        process = psutil.Process(controller["pid"])
        return (
            abs(process.create_time() - controller["created"]) < 0.01
            and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def main(directory, output, controller_path, workflow_path):
    # No CUDA availability queries, allocations, output creation or model imports
    # that execute kernels may precede the live owner and completion checks.
    assert not torch.cuda.is_initialized()
    controller = read(controller_path)
    if owner_alive(controller):
        print(
            json.dumps(
                {
                    "status": "rejected-owned-workflow-still-live",
                    "controller": controller,
                    "CUDA_initialized": torch.cuda.is_initialized(),
                }
            ),
            flush=True,
        )
        raise SystemExit(2)
    workflow = read(workflow_path)
    if workflow["status"] != "completed-to10000-and-evaluation-awaiting-manual-review":
        raise ValueError("Preceding V58 workflow did not complete its original schedule/evaluation")
    if psutil.virtual_memory().available < 24e9:
        raise RuntimeError("Less than24GB available; leave GPU preflight pending")
    os.nice(5)
    torch.set_num_threads(2)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    snapshot = output / "source"
    snapshot.mkdir()
    sources = {p.name: sha(p) for p in Path("src/demosaic").glob("*.py")}
    for p in [Path(__file__), *Path("src/demosaic").glob("*.py")]:
        (snapshot / p.name).write_bytes(p.read_bytes())
    model = load_nonlocal_reference(directory, device="cpu", archive=output)
    from deform_neighbourhood_sampling.ops import deform_neighbourhood

    assert torch.cuda.is_available()
    torch.backends.cudnn.benchmark = False
    torch.set_float32_matmul_precision("highest")
    torch.cuda.reset_peak_memory_stats()
    operator_checks = []
    generator = torch.Generator().manual_seed(20261016)
    for kh, kw in [(3, 3), (3, 5), (5, 5)]:
        cpu_input = torch.randn(1, 4, 13, 17, generator=generator, requires_grad=True)
        cpu_offsets = (
            torch.rand(1, 2 * kh * kw, 13, 17, generator=generator) * 3 - 1.5
        ).requires_grad_()
        gpu_input = cpu_input.detach().cuda().requires_grad_()
        gpu_offsets = cpu_offsets.detach().cuda().requires_grad_()
        arguments = ((kh, kw), 1, (kh // 2, kw // 2), 1, 1)
        cpu = deform_neighbourhood(cpu_input, cpu_offsets, *arguments)
        gpu = deform_neighbourhood(gpu_input, gpu_offsets, *arguments)
        torch.cuda.synchronize()
        torch.testing.assert_close(gpu.cpu(), cpu, rtol=1e-5, atol=1e-5)
        gradients = torch.randn(cpu.shape, generator=generator)
        cpu_grads = torch.autograd.grad(cpu, (cpu_input, cpu_offsets), gradients)
        gpu_grads = torch.autograd.grad(gpu, (gpu_input, gpu_offsets), gradients.cuda())
        errors = []
        for a, b in zip(cpu_grads, gpu_grads, strict=True):
            torch.testing.assert_close(b.cpu(), a, rtol=1e-4, atol=1e-4)
            errors.append(float((a - b.cpu()).abs().max()))
        operator_checks.append(
            {
                "neighborhood": [kh, kw],
                "forward_max_abs_CPU_CUDA": float((cpu.detach() - gpu.detach().cpu()).abs().max()),
                "input_and_offset_gradient_max_abs_CPU_CUDA": errors,
            }
        )
        print(json.dumps(operator_checks[-1]), flush=True)
    model = model.cuda()
    base = Path("/mnt/external/demosaic/evaluation")
    old = read(base / "nonlocal-matchfilter-two-photos-cpu-v1/report.json")
    old_plan = read(old["plan"])
    cases = []
    for index, record in enumerate(old_plan["sources"]):
        expected = next(
            i
            for i in old["arrays"]
            if i["source_index"] == index and i["kind"] == "RGB-camera-Malvar"
        )
        cases.append(
            {
                "input": record["path"],
                "input_sha256": record["sha256"],
                "expected": expected["path"],
                "expected_sha256": expected["sha256"],
                "condition": record["source_crop"]["condition"],
                "label": f"photo-{index}",
            }
        )
    checks = []
    for case in cases:
        assert sha(case["input"]) == case["input_sha256"]
        assert sha(case["expected"]) == case["expected_sha256"]
        with np.load(case["input"], allow_pickle=False) as data:
            batch = {k: torch.from_numpy(data[k].copy()).cuda() for k in data.files}
        expected = torch.from_numpy(np.load(case["expected"], allow_pickle=False))
        model.set_noise(case["condition"]["shot"], case["condition"]["read"])
        predictions = []
        for precision in [None, torch.float16, torch.bfloat16]:
            with (
                torch.inference_mode(),
                torch.autocast(
                    "cuda", enabled=precision is not None, dtype=precision or torch.float16
                ),
            ):
                prediction = model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                )
            assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
            predictions.append(prediction.cpu())
        torch.testing.assert_close(predictions[0], expected, rtol=1e-4, atol=1e-4)
        assert torch.equal(predictions[0], predictions[1]) and torch.equal(
            predictions[0], predictions[2]
        )
        path = output / f"{case['label']}-CUDA-camera-RGB-f32.npy"
        np.save(path, predictions[0].numpy(), allow_pickle=False)
        checks.append(
            {
                **case,
                "CUDA_prediction": str(path),
                "CUDA_prediction_sha256": sha(path),
                "shape": list(predictions[0].shape),
                "max_abs_CPU_CUDA": float((predictions[0] - expected).abs().max()),
                "outer_FP16_BF16_predictions_bit_exact_to_FP32": True,
            }
        )
        print(json.dumps(checks[-1]), flush=True)
    with torch.cuda.stream(torch.cuda.Stream()):
        raw = torch.full((1, 4, 8, 8), 0.2, device="cuda")
        colors = torch.tensor([[0, 1, 1, 2]], device="cuda")
        try:
            model(raw, raw, colors)
        except ValueError as error:
            assert "default CUDA stream" in str(error)
        else:
            raise AssertionError("Nondefault stream was not rejected")
    assert not owner_alive(controller)
    assert all(sha(Path("src/demosaic") / name) == expected for name, expected in sources.items())
    result = {
        "status": "completed-genuine-reference-default-stream-CPU-CUDA-numerical-preflight-only",
        "preceding_controller": controller,
        "preceding_workflow_sha256": sha(workflow_path),
        "model": model.receipt,
        "operator_checks": operator_checks,
        "actual_author_network_checks": checks,
        "nondefault_stream_rejected_before_native_call": True,
        "network_tolerances": {"rtol": 1e-4, "atol": 1e-4},
        "torch": torch.__version__,
        "hardware": torch.cuda.get_device_name(),
        "max_allocated_bytes": torch.cuda.max_memory_allocated(),
        "source_files": sources,
        "driver_sha256": sha(__file__),
        "limitations": "Numerical engineering checks only, fixed batch1/defaultstream FP32. No complete quality panel, new trained model, GB10 speed benchmark, 102MP result or promotion.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(result, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--controller", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, required=True)
    args = parser.parse_args()
    main(args.directory, args.output, args.controller, args.workflow)
