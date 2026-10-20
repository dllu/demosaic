"""Deferred CUDA component parity/timing after the exact earlier inverse probe."""

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
    with (root / "controller.claim").open("x") as file:
        file.write(str(os.getpid()))
    state = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
    }

    def record(status, **fields):
        state.update(status=status, updated_unix=time.time(), **fields)
        save(root / "status.json", state)

    try:
        launch = read(plan["predecessor_launch"]["path"])
        previous = read(plan["predecessor_plan"]["path"])
        record("waiting-for-exact-prior-inverse-probe-after-training-and-quality")
        deadline = time.monotonic() + 28800
        while alive(launch):
            assert time.monotonic() < deadline, "Eight-hour wait bound exhausted"
            status = read(Path(previous["root"]) / "status.json")
            assert not status["status"].startswith("failed-"), "Preceding work failed; no retry"
            time.sleep(5)
        status = read(Path(previous["root"]) / "status.json")
        assert status["controller"]["pid"] == launch["pid"]
        assert status["controller"]["created"] == launch["created"]
        assert (
            status["status"]
            == "completed-isolated-VST-inverse-CUDA-numerical-and-resident-timing-probe"
        )
        assert ref(status["result"]["path"]) == status["result"]
        guard(plan)
        assert psutil.virtual_memory().available > 40 * 2**30
        import torch

        from demosaic.cfa import PATTERNS, color_indices, malvar
        from demosaic.precision import ieee_fp32
        from demosaic.pretrained_rgb import physical_rgb_features
        from demosaic.vst import GeneralizedAnscombe

        torch.set_num_threads(2)
        torch.use_deterministic_algorithms(True)
        device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(
            min(
                torch.cuda.get_per_process_memory_fraction(device),
                16 * 2**30 / torch.cuda.get_device_properties(device).total_memory,
            ),
            device,
        )
        spec = importlib.util.spec_from_file_location(
            "legacy_physical", plan["legacy_fixture"]["path"]
        )
        legacy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(legacy)
        functions = {
            "original": legacy.original_anchored_features,
            "candidate": physical_rgb_features,
        }
        colors = torch.stack([color_indices(p, device=device) for p in PATTERNS])
        wb = torch.tensor(
            [[2.0, 1.0, 1.5], [0.7, 1.0, 2.0], [1.0, 1.0, 1.0], [4.0, 0.8, 1.5]], device=device
        )
        matrix = torch.eye(3, device=device)[None].expand(4, -1, -1)
        profiles = [
            (GeneralizedAnscombe(0.00256, 0.0000262144).to(device), 1.0, True),
            (None, 1.0, False),
            (None, 0.01, True),
            (GeneralizedAnscombe(1e-10, 0.0001).to(device), 1.0, True),
        ]
        cpu_rng, cuda_rng = torch.get_rng_state(), torch.cuda.get_rng_state_all()
        results = []
        deadline = time.monotonic() + 300
        record("running-isolated-anchored-physical-feature-CUDA-parity-and-timing")
        with torch.inference_mode(), ieee_fp32():
            for size in [64, 512]:
                source = torch.linspace(
                    -0.02, 1.2, 4 * 4 * (size // 2) ** 2, device=device
                ).reshape(4, 4, size // 2, size // 2)
                transformed, proxies, interpolated = [], [], []
                for b, (transform, scale, stochastic) in enumerate(profiles):
                    z = (
                        transform(source[b : b + 1])
                        if transform is not None
                        else (source[b : b + 1].double() / scale).float()
                    )
                    transformed.append(z)
                    proxies.append(torch.ones_like(z) if stochastic else torch.zeros_like(z))
                    interpolated.append(
                        malvar(
                            z, colors[b : b + 1], None if transform is not None else wb[b : b + 1]
                        )
                    )
                for layout in [torch.contiguous_format, torch.channels_last]:
                    packed, variance, rgb = (
                        torch.cat(v).contiguous(memory_format=layout)
                        for v in [transformed, proxies, interpolated]
                    )
                    kwargs = {"rgb": rgb, "stabilized": True, "photometry_profiles": profiles}
                    args = [packed, variance, colors, wb, matrix]
                    first, second = (function(*args, **kwargs) for function in functions.values())
                    for x, y in zip(first, second, strict=True):
                        assert torch.isfinite(x).all() and torch.isfinite(y).all()
                        assert x.stride() == y.stride()
                        assert torch.equal(
                            x.flatten().view(torch.uint8), y.flatten().view(torch.uint8)
                        )
                    values = sum(x.numel() for x in first)
                    del first, second
                    for _ in range(2):
                        for function in functions.values():
                            function(*args, **kwargs)
                    samples = {name: [] for name in functions}
                    for repeat in range(5):
                        assert time.monotonic() < deadline
                        order = list(functions) if repeat % 2 == 0 else list(reversed(functions))
                        for name in order:
                            start, end = (
                                torch.cuda.Event(enable_timing=True),
                                torch.cuda.Event(enable_timing=True),
                            )
                            start.record()
                            functions[name](*args, **kwargs)
                            end.record()
                            end.synchronize()
                            samples[name].append(start.elapsed_time(end))
                    results.append(
                        {
                            "native_size": size,
                            "batch": 4,
                            "layout": "channels_last"
                            if layout == torch.channels_last
                            else "contiguous",
                            "all_six_output_fields_bytes_and_strides_exact": True,
                            "values_compared": values,
                            "CUDA_ms": samples,
                            "median_ms": {k: statistics.median(v) for k, v in samples.items()},
                        }
                    )
        assert torch.equal(cpu_rng, torch.get_rng_state())
        assert all(
            torch.equal(x, y) for x, y in zip(cuda_rng, torch.cuda.get_rng_state_all(), strict=True)
        )
        guard(plan)
        result = {
            "status": "completed-isolated-anchored-physical-feature-CUDA-parity-and-timing",
            "plan": ref(plan_path),
            "predecessor_result": status["result"],
            "results": results,
            "all_output_bytes_and_strides_exact": True,
            "CPU_CUDA_RNG_unchanged": True,
            "scope": "Physical feature component only, deterministic nonphotographic all-CFA fields and mixed noise families. IEEE FP32 physical work with the unchanged FP64 GAT anchors. Five alternating CUDA-event samples after two warmups. No neural model, optimizer, training, reference, quality or full-frame speed claim; shared-machine workloads are not excluded.",
        }
        save(root / "result.json", result)
        record(result["status"], result=ref(root / "result.json"))
    except BaseException as error:
        record("failed-physical-feature-CUDA-probe-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    main(args.plan.resolve())
