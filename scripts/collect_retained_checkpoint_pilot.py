"""Bounded new-checkpoint inference on predeclared retained observations.

The preparation plan supplies immutable input bindings, reference/control
bindings and the exact midpoint identity. No input generation, old-model
inference, automatic retry or checkpoint selection happens in this collector.
"""

import argparse
import json
import os
import random
import shutil
from pathlib import Path

import numpy as np
import psutil
from train_directional_bank_trial import guard, read, ref, save

NAMES = ("packed", "variance", "colors", "wb", "matrix")


def verify_progress_checkpoint(state, plan):
    """Validate a retained training prefix before constructing its neural model."""
    import torch

    step, horizon = plan["step"], plan["training_horizon"]
    spatial = plan["raw_spatial_features"]
    tensors, optimizer_states = (114, 112) if spatial else (91, 89)
    if not (
        0 < step < horizon
        and state["step"] == step
        and state["config"]["steps"] == horizon
        and state["model_config"].get("raw_spatial_features", False) is spatial
        and state["config"]["initialized_from"] == plan["expected_lineage"]
        and len(state["model"]) == len(state["ema"]) == plan["EMA_tensors"] == tensors
        and state["model"].keys() == state["ema"].keys()
    ):
        raise ValueError("Progress checkpoint step, horizon, architecture or lineage differs")
    states = state["optimizer"]["state"]
    if len(states) != optimizer_states or any(float(s["step"]) != step for s in states.values()):
        raise ValueError("Progress optimizer state count or update step differs")
    values = [*state["model"].values(), *state["ema"].values()]
    values += [v for s in states.values() for v in s.values() if isinstance(v, torch.Tensor)]
    if any(not torch.isfinite(v).all() for v in values):
        raise ValueError("Nonfinite progress model, EMA or optimizer state")
    branch = [k for k in state["model"] if k.startswith("pretrained_rgb.raw_spatial.")]
    if len(branch) != (23 if spatial else 0):
        raise ValueError("Progress spatial state coverage differs")


def collect(path):
    import torch
    from frozen_backbone_identity import verify_backbone_identity
    from profile_raw_kernel_inference import model_hash

    from demosaic.inference import load_checkpoint
    from demosaic.prediction_archive import fingerprint

    plan = read(path)
    guard(plan)
    root, work = Path(plan["root"]), Path(plan["work"])
    if not Path(load_checkpoint.__code__.co_filename).resolve().is_relative_to(work / "src"):
        raise RuntimeError("Use the plan's frozen inference source")
    if ref(__file__) != plan["collector"] or os.environ.get("CUDA_VISIBLE_DEVICES") != "0":
        raise RuntimeError("Collector source/device differs")
    observations = plan["observations"]
    if len(observations) != plan["planned_new_root_forwards"] or len(
        {o["id"] for o in observations}
    ) != len(observations):
        raise ValueError("Declare distinct observations and an exact forward budget")
    with (root / "collect.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = True

    def resources(initial=False):
        reserve = plan["launch_RAM_GiB"] if initial else plan["runtime_RAM_GiB"]
        if psutil.virtual_memory().available < reserve * 2**30:
            raise RuntimeError("Host memory reserve reached")
        for location, key in ((root, "internal"), (Path("/mnt/external"), "external")):
            reserve = plan[("launch_" if initial else "runtime_") + key + "_reserve_GiB"]
            if shutil.disk_usage(location).free < reserve * 2**30:
                raise RuntimeError("Disk reserve reached")

    resources(initial=True)
    torch.cuda.set_per_process_memory_fraction(
        plan["CUDA_quota_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    python_rng, numpy_rng = random.getstate(), np.random.get_state()
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    counts = {"root": 0, "encoder": 0}
    rows = []
    witness = {}
    if plan.get("progress_checkpoint", False):
        state = torch.load(
            plan["checkpoint"]["path"], map_location="cpu", weights_only=True, mmap=True
        )
        verify_progress_checkpoint(state, plan)
        del state
    with torch.random.fork_rng(devices=[0]):
        model, state = load_checkpoint(plan["checkpoint"]["path"], "cuda")
        if (
            state["loaded_sha256"] != plan["checkpoint"]["sha256"]
            or state["step"] != plan["step"]
            or state["config"]["initialized_from"] != plan["expected_lineage"]
            or model.config.raw_frequency_features != plan.get("raw_frequency_features", True)
            or (model.pretrained_rgb.raw_frequency is not None)
            != plan.get("raw_frequency_features", True)
            or (
                "raw_spatial_features" in plan
                and getattr(model.config, "raw_spatial_features", False)
                is not plan["raw_spatial_features"]
            )
        ):
            raise ValueError("Loaded checkpoint identity or frequency-adapter setting differs")
        actual = model.restoration_state_dict()
        if len(actual) != plan["EMA_tensors"] or any(
            not torch.equal(v.cpu(), state["ema"][k]) for k, v in actual.items()
        ):
            raise ValueError("Model did not load the exact preserved EMA")
        backbone_before = model_hash(model.context.backbone)
        verify_backbone_identity(
            model.config.to_dict(),
            backbone_before,
            {"expected_backbone": plan["expected_backbone"]},
            legacy_sha256=plan["expected_backbone"]["sha256"],
        )
        del actual, state
        model.eval().to(memory_format=torch.channels_last)
        before = model_hash(model)
        if plan.get("expected_full_model_sha256", before) != before:
            raise ValueError("Loaded model differs from its retained identity")
        save(
            root / "loaded-model-v1.json",
            {
                "plan": ref(path),
                "full_model_sha256": before,
                "backbone_sha256": backbone_before,
                "new_forwards_so_far": 0,
            },
        )

        def pre_hook(module, args):
            resources()
            if (
                module.training
                or torch.is_autocast_enabled("cuda")
                or (torch.backends.cuda.matmul.allow_tf32 or torch.backends.cudnn.allow_tf32)
            ):
                raise RuntimeError("Pilot requires evaluation in IEEE FP32")
            if counts["root"] >= len(observations):
                raise RuntimeError("Prospective forward budget exhausted")
            if {k: fingerprint(v) for k, v in zip(NAMES, args, strict=True)} != witness["inputs"]:
                raise ValueError("Actual forward arguments differ from retained bytes")
            counts["root"] += 1

        def encoder_hook(*args):
            counts["encoder"] += 1
            if counts["encoder"] > len(observations):
                raise RuntimeError("Encoder forward budget exhausted")

        handles = [
            model.register_forward_pre_hook(pre_hook),
            model.context.backbone.register_forward_hook(encoder_hook),
        ]
        destination = work / "artifacts/predictions"
        destination.mkdir(parents=True, exist_ok=False)
        journal = root / "predictions-v1.jsonl"
        with journal.open("x") as stream, torch.inference_mode():
            for index, observation in enumerate(observations):
                with np.load(observation["arrays"]["path"], allow_pickle=False) as data:
                    arrays = {k: data[k] for k in NAMES}
                witness["inputs"] = observation["input_fingerprints"]
                if {k: fingerprint(v) for k, v in arrays.items()} != witness["inputs"]:
                    raise ValueError("Stored input bytes differ")
                batch = {k: torch.from_numpy(v).to("cuda") for k, v in arrays.items()}
                model.set_noise(observation["noise"]["shot"], observation["noise"]["read"])
                value = model(*(batch[k] for k in NAMES))
                if (
                    value.dtype != torch.float32
                    or list(value.shape) != observation["output_shape"]
                    or not torch.isfinite(value).all()
                ):
                    raise ValueError("Invalid native FP32 prediction")
                if {k: fingerprint(v) for k, v in batch.items()} != witness["inputs"]:
                    raise ValueError("Inference mutated input observations")
                prediction = value.cpu().numpy()
                output = destination / f"prediction-{index:03d}.npy"
                with output.open("xb") as handle:
                    np.save(handle, prediction, allow_pickle=False)
                row = {
                    "id": observation["id"],
                    "prediction": ref(output),
                    "values": fingerprint(prediction),
                    "counts": dict(counts),
                }
                stream.write(json.dumps(row, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
                rows.append(row)
                print(json.dumps({"completed": index + 1, "id": row["id"], **counts}), flush=True)
                del value, prediction, batch
        for handle in handles:
            handle.remove()
        after, backbone_after = model_hash(model), model_hash(model.context.backbone)
        if before != after or backbone_before != backbone_after:
            raise ValueError("Inference mutated model state")
    if (
        not torch.equal(cpu_rng, torch.get_rng_state())
        or not torch.equal(cuda_rng, torch.cuda.get_rng_state())
        or random.getstate() != python_rng
        or any(
            not np.array_equal(a, b) for a, b in zip(numpy_rng, np.random.get_state(), strict=True)
        )
    ):
        raise ValueError("Pilot changed RNG state")
    guard(plan)
    if counts != {"root": len(observations), "encoder": len(observations)}:
        raise ValueError("Actual forward counts differ")
    save(
        root / "collection-v1.json",
        {
            "status": "completed-declared-checkpoint-retained-input-pilot",
            "plan": ref(path),
            "predictions": ref(journal),
            "counts": counts,
            "full_model_before": before,
            "full_model_after": after,
            "backbone_before": backbone_before,
            "backbone_after": backbone_after,
            "new_reference_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "optimizer_updates": 0,
            "RNG_unchanged": True,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "torch": torch.__version__,
            "cuda": torch.version.cuda,
            "progress_checkpoint_verified": plan.get("progress_checkpoint", False),
            "training_horizon": plan.get("training_horizon"),
            "scope": plan["scope"],
            "observations": rows,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    collect(parser.parse_args().plan)
