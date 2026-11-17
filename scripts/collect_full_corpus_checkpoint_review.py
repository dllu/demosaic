"""Matched CPU EMA review of a retained full-corpus checkpoint on fixed observations."""

import argparse
import os
import shutil
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash

from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json
from demosaic.frozen_encoder_replay import FrozenDinoReplay
from demosaic.inference import load_checkpoint
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint

ARGUMENTS = ("packed", "variance", "colors", "wb", "matrix")


@torch.inference_mode()
def collect(plan_path):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert reference(__file__) == plan["collector"]
    assert not torch.cuda.is_initialized()
    os.sched_setaffinity(0, plan["CPU_affinity"])
    os.nice(10)
    torch.set_num_threads(plan["CPU_threads"])
    root = Path(plan["root"])
    output = root / "collection"
    output.mkdir()
    write_json(output / "owner.json", {"pid": os.getpid(), "create_time": psutil.Process().create_time(), "plan": reference(plan_path)})
    if psutil.virtual_memory().available < 36 * 2**30 or shutil.disk_usage(root).free < 256 * 2**30:
        raise RuntimeError("CPU checkpoint review start reserves unavailable")
    models, before, counters = {}, {}, {}
    for label, specification in plan["models"].items():
        model, state = load_checkpoint(checked(specification["checkpoint"]), "cpu")
        assert state["loaded_sha256"] == specification["checkpoint"]["sha256"]
        assert state["step"] == specification["step"] and "ema" in state
        actual = model.restoration_state_dict()
        assert len(actual) == len(state["ema"]) == 91
        assert all(torch.equal(value, state["ema"][key]) for key, value in actual.items())
        if specification.get("retained_progress"):
            assert state["config"]["steps"] == specification["training_horizon"] == 20000
            assert len(state["optimizer"]["state"]) == 89
            assert all(value["step"] == state["step"] for value in state["optimizer"]["state"].values())
            assert all(torch.isfinite(value).all() for name in ["model", "ema"] for value in state[name].values())
            assert all(torch.isfinite(t).all() for value in state["optimizer"]["state"].values() for t in value.values() if isinstance(t, torch.Tensor))
            assert state["python_rng"] and state["cuda_rng"] and state["torch_rng"].numel()
        model.eval().to(memory_format=torch.contiguous_format)
        assert model_hash(model.context.backbone) == plan["DINO_sha256"]
        models[label] = model
        before[label] = model_hash(model)
        counters[label] = {"root": 0}
        model.register_forward_pre_hook(lambda *_, c=counters[label]: c.__setitem__("root", c["root"] + 1))
        del state, actual
    replay = FrozenDinoReplay([model.context.backbone for model in models.values()])
    torch_rng = torch.get_rng_state().clone()
    totals = {"requests": 0, "executions": 0, "replays": 0}
    records, began = [], time.monotonic()
    with ieee_fp32():
        for index, observation in enumerate(plan["observations"]):
            if psutil.virtual_memory().available < 24 * 2**30 or shutil.disk_usage(root).free < 192 * 2**30:
                raise RuntimeError("CPU checkpoint review runtime reserves unavailable")
            if time.monotonic() - began > plan["maximum_seconds"]:
                raise TimeoutError("CPU checkpoint review runtime bound reached; no automatic retry")
            with np.load(checked(observation["arrays"]), allow_pickle=False) as data:
                arguments = {name: torch.from_numpy(data[name].copy()) for name in ARGUMENTS}
            fingerprints = {name: fingerprint(value) for name, value in arguments.items()}
            assert fingerprints == observation["input_fingerprints"]
            variants = []
            with replay.group() as statistics:
                for label, model in models.items():
                    model.set_noise(observation["noise"]["shot"], observation["noise"]["read"])
                    tick = time.monotonic()
                    value = model(*(arguments[name] for name in ARGUMENTS))
                    seconds = time.monotonic() - tick
                    assert value.dtype == torch.float32 and list(value.shape) == observation["output_shape"]
                    assert torch.isfinite(value).all()
                    destination = output / label
                    destination.mkdir(exist_ok=True)
                    path = destination / f"prediction-{index:03d}.npy"
                    with path.open("xb") as stream:
                        np.save(stream, value.numpy(), allow_pickle=False)
                    variants.append({"label": label, "checkpoint": plan["models"][label]["checkpoint"],
                                     "prediction": reference(path), "inference_seconds": seconds})
            assert statistics == {"requests": 2, "executions": 1, "replays": 1}
            assert fingerprints == {name: fingerprint(value) for name, value in arguments.items()}
            for name, count in statistics.items():
                totals[name] += count
            record = {"id": observation["id"], "input_fingerprints": fingerprints, "variants": variants,
                      "local_DINO": dict(statistics)}
            path = output / f"case-{index:03d}.json"
            write_json(path, record)
            records.append(reference(path))
            write_json(output / "progress.json", {"completed": index + 1, "planned": len(plan["observations"]),
                       "seconds": time.monotonic() - began, "root_calls": counters, "local_DINO": totals}, replace=True)
            print(index + 1, observation["id"], flush=True)
    after = {label: model_hash(model) for label, model in models.items()}
    assert before == after and torch.equal(torch_rng, torch.get_rng_state())
    assert not torch.cuda.is_initialized()
    assert all(counter["root"] == len(plan["observations"]) for counter in counters.values())
    write_json(output / "result.json", {"plan": reference(plan_path), "records": records, "models": plan["models"],
               "weights": "EMA", "root_calls": counters, "local_DINO": totals,
               "full_model_before": before, "full_model_after": after, "CPU_rng_unchanged": True,
               "seconds": time.monotonic() - began,
               "scope": "Complete declared retained-observation CPU IEEE FP32 contiguous B1 review, fresh matched V120 and retained scaling EMA. Identical checked frozen local DINO requests shared; learned trunks still execute separately. Zero new GPU/RAW/noise/optimizer calls. Targets are not read by this collector. Partial training trajectory, not a completed20k/100k horizon or full427/camera score; numerical/native analysis separate."})
    print("Completed", len(records), "fixed inputs", counters, totals)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    collect(parser.parse_args().plan)
