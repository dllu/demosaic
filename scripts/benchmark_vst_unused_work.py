"""Deferred isolated CUDA inverse check/timing; no full-model speed claim."""

import argparse
import importlib.util
import os
import statistics
import time
from pathlib import Path

import psutil
from train_context_trial import alive
from train_directional_bank_trial import guard, read, ref, save


def main(plan_path):
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as f:
        f.write(str(os.getpid()))
    state = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
    }

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        save(root / "status.json", state)

    try:
        review = read(plan["review_plan"]["path"])
        q = read(plan["queue"]["path"])
        package = read(plan["package_launch"]["path"])
        owners = [q[k] for k in ["review_owner", "closure_owner", "reference_owner"]] + [package]
        deadline = time.monotonic() + 28800
        record("waiting-for-exact-training-review-closure-reference-and-package-exits")
        while any(alive(o) for o in owners):
            assert time.monotonic() < deadline, "Eight-hour wait bound exhausted"
            for name in ["status.json", "closure-status.json", "report-package-status.json"]:
                status = read(Path(review["root"]) / name)
                if status["status"].startswith("failed-"):
                    raise RuntimeError("Preceding quality work failed; no benchmark or retry")
            time.sleep(5)
        from prepare_spectral_report_assets import ready

        ready(review)
        status = read(Path(review["root"]) / "report-package-status.json")
        assert status["status"] == "prepared-native-report-assets-awaiting-manual-inspection"
        guard(plan)
        import torch

        from demosaic.precision import ieee_fp32
        from demosaic.vst import GeneralizedAnscombe

        assert psutil.virtual_memory().available > 40 * 2**30
        torch.set_num_threads(2)
        device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(
            min(
                torch.cuda.get_per_process_memory_fraction(device),
                16 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
            ),
            device,
        )
        spec = importlib.util.spec_from_file_location(
            "legacy_inverse", plan["legacy_inverse"]["path"]
        )
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        functions = {
            "original": legacy.inverse_before_elimination,
            "candidate": GeneralizedAnscombe.inverse,
        }
        torch.cuda.synchronize(device)
        rng = torch.cuda.get_rng_state_all()
        cpu_rng = torch.get_rng_state()
        results = []
        total_values = 0
        record("running-isolated-VST-inverse-CUDA-numerical-and-timing-probes")
        with ieee_fp32():
            for shot, read_noise in plan["profiles"]:
                transform = GeneralizedAnscombe(shot, read_noise).to(device)
                for size in plan["native_sizes"]:
                    raw = torch.linspace(-0.02, 1.5, 3 * size * size, device=device).reshape(
                        1, 3, size, size
                    )
                    with torch.inference_mode():
                        z = transform(raw)
                        z.flatten()[:3] = transform.expected[-1]
                        z.flatten()[3:6] = torch.nextafter(
                            transform.expected[-1].float(),
                            torch.tensor(float("inf"), device=device),
                        )
                        a = functions["original"](transform, z)
                        b = functions["candidate"](transform, z)
                        assert torch.isfinite(a).all() and torch.equal(
                            a.flatten().view(torch.uint8), b.flatten().view(torch.uint8)
                        )
                        total_values += a.numel()
                        for _ in range(2):
                            for f in functions.values():
                                f(transform, z)
                        samples = {name: [] for name in functions}
                        for repeat in range(5):
                            order = (
                                list(functions) if repeat % 2 == 0 else list(reversed(functions))
                            )
                            for name in order:
                                start = torch.cuda.Event(enable_timing=True)
                                end = torch.cuda.Event(enable_timing=True)
                                start.record()
                                functions[name](transform, z)
                                end.record()
                                end.synchronize()
                                samples[name].append(start.elapsed_time(end))
                    small = z.flatten()[:: max(1, z.numel() // 64)][:64].detach()
                    gradients = []
                    for f in functions.values():
                        inputs = small.clone().requires_grad_()
                        output = f(transform, inputs)
                        gradients.append(torch.autograd.grad(output.sum(), inputs)[0])
                    assert torch.equal(
                        gradients[0].view(torch.uint8), gradients[1].view(torch.uint8)
                    )
                    results.append(
                        {
                            "shot": shot,
                            "read_variance": read_noise,
                            "native_size": size,
                            "RGB_values": a.numel(),
                            "all_output_bytes_exact": True,
                            "sampled_input_gradient_bytes_exact": True,
                            "CUDA_ms": samples,
                            "median_ms": {k: statistics.median(v) for k, v in samples.items()},
                        }
                    )
        assert torch.equal(cpu_rng, torch.get_rng_state())
        for a, b in zip(rng, torch.cuda.get_rng_state_all(), strict=True):
            assert torch.equal(a, b)
        guard(plan)
        result = {
            "status": "completed-isolated-VST-inverse-CUDA-numerical-and-resident-timing-probe",
            "plan": ref(plan_path),
            "results": results,
            "values_compared": total_values,
            "all_output_and_sampled_gradient_bytes_exact": True,
            "unchanged_CPU_CUDA_RNG": True,
            "scope": "Inverse component only on deterministic nonphotographic fields, IEEE FP64 physical arithmetic/F32 return. Five alternating CUDA-event samples after two warmups per method. No neural model, training, new held-out quality, sensor calibration or full100MP timing; other shared-machine workloads are not excluded. No automatic model promotion.",
        }
        save(root / "result.json", result)
        record(result["status"], result=ref(root / "result.json"))
    except BaseException as error:
        record("failed-isolated-inverse-CUDA-probe-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    a = p.parse_args()
    main(a.plan.resolve())
