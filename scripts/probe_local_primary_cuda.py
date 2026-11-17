"""Compare IEEE FP32 CUDA replay against closed, matched local-primary CPU batches."""

import argparse
import math
import os
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash

from demosaic.archive_metrics import photometry
from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.prediction_archive import fingerprint

ARGUMENTS = ("packed", "variance", "colors", "wb", "matrix")
DN16 = 65535


@torch.inference_mode()
def probe(plan_path):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert reference(__file__) == plan["driver"]
    os.sched_setaffinity(0, plan["CPU_affinity"])
    torch.set_num_threads(len(plan["CPU_affinity"]))
    os.nice(10)
    device = torch.device("cuda:0")
    torch.cuda.set_per_process_memory_fraction(
        min(
            1.0,
            plan["cuda_allocator_max_GiB"]
            * 2**30
            / torch.cuda.get_device_properties(device).total_memory,
        ),
        device,
    )
    torch.backends.cudnn.benchmark = False
    output = Path(plan["root"]) / "output"
    output.mkdir()
    models, state_hashes, counters = {}, {}, {}
    for label, specification in plan["models"].items():
        model, payload = load_checkpoint(checked(specification["checkpoint"]), device)
        assert payload["loaded_sha256"] == specification["checkpoint"]["sha256"]
        assert payload["step"] == specification["step"]
        model.eval().requires_grad_(False).to(memory_format=torch.channels_last)
        actual = model.restoration_state_dict()
        assert len(actual) == len(payload["ema"]) == 91
        assert all(torch.equal(v.cpu(), payload["ema"][k]) for k, v in actual.items())
        assert model_hash(model.context.backbone) == plan["DINO_sha256"]
        state_hashes[label] = model_hash(model)
        models[label] = model
        counts = counters[label] = {"root": 0, "DINO": 0}
        model.register_forward_pre_hook(lambda *_, c=counts: c.__setitem__("root", c["root"] + 1))
        model.context.backbone.register_forward_pre_hook(
            lambda *_, c=counts: c.__setitem__("DINO", c["DINO"] + 1)
        )
        del payload

    rows = []
    began = time.monotonic()
    with amp_context(device, dtype="float32"):
        for index, entry in enumerate(plan["cases"]):
            if psutil.virtual_memory().available < 32 * 2**30:
                raise RuntimeError("Available memory fell below 32 GiB during CUDA probe")
            if time.monotonic() - began > plan["maximum_probe_seconds"]:
                raise TimeoutError("CUDA probe exceeded its time limit")
            record = entry["record"]
            stage = record["stage"]
            camera = stage in {"known", "unseen"}
            context = record["context"]
            noise = context["noise" if camera else "condition"]
            case = read_json(checked(entry["CPU_case"]))
            assert case["canonical_arrays"] == record["arrays"]
            with np.load(checked(record["arrays"]), allow_pickle=False) as data:
                arrays = dict(data)
            args = [torch.from_numpy(arrays[key]).to(device) for key in ARGUMENTS]
            args = [
                t.contiguous(memory_format=torch.channels_last) if t.ndim == 4 else t for t in args
            ]
            witnesses = dict(zip(ARGUMENTS, map(fingerprint, args), strict=True))
            assert witnesses == case["input_fingerprints"]
            for variant in case["variants"]:
                label = variant["arm"]
                model = models[label]
                assert variant["checkpoint"] == plan["models"][label]["checkpoint"]
                model.set_noise(noise["shot"], noise["read"])
                torch.cuda.synchronize(device)
                start = time.monotonic()
                prediction = model(*args)
                torch.cuda.synchronize(device)
                elapsed = time.monotonic() - start
                value = prediction.cpu().numpy()
                cpu = np.load(checked(variant["prediction"]), allow_pickle=False)
                assert value.dtype == cpu.dtype == np.float32 and value.shape == cpu.shape
                assert np.isfinite(value).all()
                delta = (value.astype(np.float64) - cpu.astype(np.float64)) * DN16
                maximum, rms = float(np.abs(delta).max()), float(np.sqrt(np.mean(delta**2)))
                border = 32 if camera else 8
                c = photometry(cpu, arrays, border=border, camera=camera)
                g = photometry(value, arrays, border=border, camera=camera)
                primary = "sensor_psnr" if camera else "srgb_psnr"
                changes = {}
                for key in c:
                    finite = np.isfinite(c[key])
                    assert np.array_equal(finite, np.isfinite(g[key]))
                    changes[key] = [
                        float(right - left) if ok else None
                        for left, right, ok in zip(c[key], g[key], finite, strict=True)
                    ]
                assert all(x is not None and math.isfinite(x) for x in changes[primary])
                path = output / f"{index:02d}-{label}.npy"
                with path.open("xb") as stream:
                    np.save(stream, value, allow_pickle=False)
                row = {
                    "stage": stage,
                    "batch": record["batch"],
                    "model": label,
                    "condition": noise.get("name", stage),
                    "pattern": context["pattern"],
                    "CPU_case": entry["CPU_case"],
                    "checkpoint": variant["checkpoint"],
                    "CPU_prediction": variant["prediction"],
                    "CUDA_prediction": reference(path),
                    "batch_size": len(cpu),
                    "shape": list(cpu.shape),
                    "max_DN16": maximum,
                    "RMS_DN16": rms,
                    "within_pixel_bounds": maximum <= 0.25 and rms <= 0.025,
                    "primary_metric": primary,
                    "metric_differences": changes,
                    "CPU_inference_seconds": variant["inference_seconds"],
                    "CUDA_inference_seconds": elapsed,
                }
                rows.append(row)
                write_json(output / f"{index:02d}-{label}.json", row)
                print(stage, record["batch"], label, maximum, rms, elapsed, flush=True)
            assert dict(zip(ARGUMENTS, map(fingerprint, args), strict=True)) == witnesses
    assert {k: model_hash(v) for k, v in models.items()} == state_hashes
    assert all(
        x == {"root": len(plan["cases"]), "DINO": len(plan["cases"])} for x in counters.values()
    )
    write_json(
        output / "result.json",
        {
            "plan": reference(plan_path),
            "rows": rows,
            "calls": counters,
            "all_pixel_bounds_pass": all(r["within_pixel_bounds"] for r in rows),
            "maximum_DN16": max(r["max_DN16"] for r in rows),
            "maximum_RMS_DN16": max(r["RMS_DN16"] for r in rows),
            "maximum_primary_metric_difference_dB": max(
                abs(delta)
                for row in rows
                for delta in row["metric_differences"][row["primary_metric"]]
            ),
            "peak_cuda_allocated_GiB": torch.cuda.max_memory_allocated(device) / 2**30,
            "peak_cuda_reserved_GiB": torch.cuda.max_memory_reserved(device) / 2**30,
            "probe_wall_seconds_excluding_load": time.monotonic() - began,
            "state_hashes": state_hashes,
            "scope": "Same immutable inputs/checkpoints; both models run independently on CUDA."
            " Concurrent training and CPU work affect timing. Pixel bounds are numerical"
            " compatibility checks. Full primary or model quality claims require all cases.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    probe(parser.parse_args().plan)
