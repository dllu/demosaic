"""Bound coherent-response engine; only the training objective import changes.

The eight helper/train bodies originate in the completed matched engine. The
wrapper supplies module-local root/factory/guard/prerequisites. Use the wrapper
CLI; this module cannot launch a trial by itself.
"""

import gc
import json
import math
import os
import shutil
import time
from pathlib import Path

import psutil
from phase_admission_protocol import read, ref

REPO = Path("/home/dllu/proj/demosaic")
ROOT = REPO / ".cache/quality-20261107/V183-coherent-pair-evidence-trial-v1"


def factory(*args):
    raise RuntimeError("Configure the bound continuation engine through its wrapper")


def guard(*args):
    raise RuntimeError("Configure the bound continuation engine through its wrapper")


def prerequisites(*args):
    raise RuntimeError("Configure the bound continuation engine through its wrapper")


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def progress(name, value):
    path = ROOT / f"{name}-status-v1.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(dict(value, observed_unix_UTC=time.time()), indent=2) + "\n")
    temporary.replace(path)


def own():
    return {"pid": os.getpid(), "created": psutil.Process().create_time()}


def require_worker_launch(plan, name, owner):
    assert Path(__file__).is_relative_to(Path(plan["work"]))
    prerequisites(plan, name)
    for _ in range(60):
        try:
            if read(ROOT / f"{name}-launch-v1.json")["owner"] == owner:
                return
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(1)
    raise RuntimeError("Worker launch identity is not observable;no CUDA initialized")


def resources(plan, name, owner):
    while True:
        available = {
            "RAM": psutil.virtual_memory().available,
            "local": shutil.disk_usage(REPO).free,
            "external": shutil.disk_usage("/mnt/external").free,
        }
        if all(available[k] > v * 2**30 for k, v in plan["minimum_GiB"].items()):
            return
        progress(
            name,
            {"status": "waiting-before-next-forward", "owner": owner, "available_bytes": available},
        )
        time.sleep(2)


def runtime(plan):
    import torch

    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True, warn_only=True)
    torch.cuda.set_per_process_memory_fraction(
        plan["CUDA_quota_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    torch.ops.load_library(plan["sampling_library"]["path"])


def instrument(module, counts):
    for name, child in [
        ("wrapper", module),
        ("frozen", module.frozen),
        ("network", module.network),
    ]:
        child.register_forward_pre_hook(
            lambda *args, name=name: counts.__setitem__(name, counts[name] + 1)
        )
    for child in module.network.modules():
        if type(child).__name__ == "NonlocalBlock":
            child.register_forward_pre_hook(
                lambda *args: counts.__setitem__("sampler", counts["sampler"] + 1)
            )
    if hasattr(module, "phase_evidence_in"):
        module.phase_evidence_in.register_forward_pre_hook(
            lambda *args: counts.__setitem__("projection", counts["projection"] + 1)
        )
    return module


def train(arm):
    import numpy as np
    import torch
    from coherent_pair_objective import objective
    from phase_evidence_training_state import (
        adam_clocks,
        matching_parameters,
        restore_matching_state,
        update_matching_ema,
        warm_start_matching,
    )
    from profile_raw_kernel_inference import model_hash

    from demosaic.prediction_archive import fingerprint

    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    name = arm + "-train"
    owner = own()
    require_worker_launch(plan, name, owner)
    (ROOT / f"{name}.claim").open("x").close()
    runtime(plan)
    counts = {k: 0 for k in ["wrapper", "frozen", "network", "sampler", "projection"]}
    initial = torch.load(plan["initial_checkpoint"]["path"], map_location="cpu", weights_only=True)
    module = instrument(factory(arm, plan["module_config"]).cuda(), counts)
    optimizer, ema, warmstart = warm_start_matching(
        module, initial, lr=plan["lr"], weight_decay=plan["weight_decay"]
    )
    del initial
    save(ROOT / f"{arm}-warmstart-v1.json", warmstart)
    frozen = model_hash(module.frozen)
    assert frozen == plan["frozen_component"]["module_hash"]
    CPU_RNG, CUDA_RNG = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    rows = read(plan["cache"]["path"])["batches"]
    units = read(plan["pair_units"]["path"])["rows"]
    updates = skipped = images = 0
    trace = []
    checkpoints = []
    restoration = None
    maximum = {name: 0.0 for name in matching_parameters(module)}
    with (ROOT / f"{arm}-train-trace-v1.jsonl").open("x") as journal:
        for step, item in enumerate(rows, 1):
            resources(plan, name, owner)
            assert (
                ref(item["arrays"]["path"]) == item["arrays"]
                and ref(item["parent"]["path"]) == item["parent"]
            )
            arrays = dict(np.load(item["arrays"]["path"], allow_pickle=False))
            parent = np.load(item["parent"]["path"], allow_pickle=False)
            assert {k: fingerprint(v) for k, v in arrays.items()} == item["inputs"] and fingerprint(
                parent
            ) == item["parent_values"]
            assert units[step - 1]["step"] == step and units[step - 1]["batch"] == item["arrays"]
            p = max(0, step - plan["warmup"]) / (plan["steps"] - plan["warmup"])
            lr = (
                plan["lr"]
                * min(1, step / plan["warmup"])
                * (0.1 + 0.9 * (1 + math.cos(math.pi * p)) / 2)
            )
            row = {
                "step": step,
                "batch": item["arrays"],
                "parent": item["parent"],
                "domain": item["metadata"]["domain"],
                "noisy": bool(np.any(arrays["variance"] > 0)),
                "lr": lr,
            }
            if row["noisy"]:
                batch = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
                base = torch.from_numpy(parent).cuda()
                pair_units = torch.tensor(
                    units[step - 1]["candidate_units_FP32"], device="cuda", dtype=torch.float32
                ).reshape(-1, 1, 1, 1)
                optimizer.zero_grad(set_to_none=True)
                for group in optimizer.param_groups:
                    group["lr"] = lr
                output, aux = module(
                    base,
                    *(batch[k] for k in ["packed", "variance", "colors", "wb"]),
                    return_aux=True,
                )
                loss, terms, mask = objective(
                    output,
                    aux["frozen_output"],
                    batch,
                    pair_units,
                    plan["domain_weights"][row["domain"]],
                )
                assert torch.isfinite(loss)
                loss.backward()
                zero = []
                for key, parameter in matching_parameters(module).items():
                    assert parameter.grad is not None and torch.isfinite(parameter.grad).all(), key
                    maximum[key] = max(maximum[key], float(parameter.grad.abs().max()))
                    if parameter.grad.count_nonzero() == 0:
                        zero.append(key)
                assert not any(p.grad is not None for p in module.frozen.parameters())
                norm = torch.nn.utils.clip_grad_norm_(
                    matching_parameters(module).values(),
                    plan["gradient_clip"],
                    error_if_nonfinite=True,
                )
                optimizer.step()
                updates += 1
                images += len(base)
                decay = update_matching_ema(
                    module,
                    ema,
                    total_updates=plan["initial_updates"] + updates,
                    maximum_decay=plan["EMA_decay"],
                )
                row.update(
                    loss=float(loss.detach()),
                    terms={k: float(v.detach()) for k, v in terms.items()},
                    gradient_norm=float(norm),
                    zero_gradient_tensors=zero,
                    flat_mask=fingerprint(mask.cpu().numpy()),
                    flat_eligible_pixels=int(mask.sum()),
                    correction_RMS_DN16=float(aux["correction"].detach().square().mean().sqrt())
                    * 65535,
                    EMA_decay=decay,
                )
                del batch, base, pair_units, output, aux, loss, terms, mask
            else:
                skipped += 1
                row["skipped"] = "zero variance;no matching,projection or optimizer call"
            assert model_hash(module.frozen) == frozen
            row.update(
                updates=updates,
                total_network_updates=plan["initial_updates"] + updates,
                counts=dict(counts),
            )
            trace.append(row)
            journal.write(json.dumps(row, allow_nan=False) + "\n")
            journal.flush()
            if step == 1 or step % 10 == 0:
                progress(
                    name,
                    {
                        "status": "training",
                        "owner": owner,
                        "arm": arm,
                        "step": step,
                        "updates": updates,
                        "counts": counts,
                        "peak_CUDA_bytes": torch.cuda.max_memory_allocated(),
                    },
                )
            if step in [8, 250, 500, 750, 1000]:
                clocks = adam_clocks(module, optimizer)
                assert clocks["network"]["steps"] == [float(plan["initial_updates"] + updates)]
                assert clocks["adapter"]["steps"] == ([float(updates)] if arm == "evidence" else [])
                checkpoint = Path(plan["artifacts"]) / "checkpoints" / f"{arm}-step{step:04d}.pt"
                payload = {
                    "models": module.state_dict(),
                    "ema": ema,
                    "optimizer": optimizer.state_dict(),
                    "arm": arm,
                    "module_config": plan["module_config"],
                    "step": step,
                    "updates": updates,
                    "initial_updates": plan["initial_updates"],
                    "CPU_RNG": torch.get_rng_state(),
                    "CUDA_RNG": torch.cuda.get_rng_state(),
                    "counts": dict(counts),
                    "plan": ref(ROOT / "plan-v1.json"),
                }
                with checkpoint.open("xb") as stream:
                    torch.save(payload, stream)
                checkpoints.append(ref(checkpoint))
                del payload
                if step == 8:
                    before = model_hash(module)
                    saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
                    del module, optimizer
                    gc.collect()
                    module = instrument(factory(arm, plan["module_config"]).cuda(), counts)
                    optimizer, ema, restoration = restore_matching_state(
                        module, saved, lr=plan["lr"], weight_decay=plan["weight_decay"]
                    )
                    assert model_hash(module) == before
                    restoration.update(
                        checkpoint=ref(checkpoint), continued_at_row=9, repeated_prefix_forwards=0
                    )
                    save(ROOT / f"{arm}-restoration-v1.json", restoration)
                    del saved
            del arrays, parent
    assert len(trace) == 1000 and updates == 900 and skipped == 100 and images == 3600
    assert counts == {
        "wrapper": 900,
        "frozen": 900,
        "network": 900,
        "sampler": 4500,
        "projection": 900 if arm == "evidence" else 0,
    }
    assert torch.equal(CPU_RNG, torch.get_rng_state()) and torch.equal(
        CUDA_RNG, torch.cuda.get_rng_state()
    )
    if arm == "evidence":
        assert maximum["phase_evidence_in.weight"] > 0
    assert any(value > 0 for key, value in maximum.items() if key.startswith("network."))
    guard(plan)
    save(
        ROOT / f"{arm}-train-result-v1.json",
        {
            "status": "completed-matched-warmstart-one-pass",
            "owner": owner,
            "arm": arm,
            "plan": ref(ROOT / "plan-v1.json"),
            "trace": trace,
            "checkpoints": checkpoints,
            "final_checkpoint": checkpoints[-1],
            "updates": updates,
            "skipped_ADC": skipped,
            "training_images": images,
            "counts": counts,
            "initial_updates": 900,
            "final_Adam_clocks": adam_clocks(module, optimizer),
            "restoration": restoration,
            "frozen_module_hash": frozen,
            "frozen_unchanged": True,
            "RNG_unchanged": True,
            "parameter_maximum_gradients": maximum,
            "peak_CUDA_allocated_bytes": torch.cuda.max_memory_allocated(),
            "new_parent_DINO_forwards": 0,
            "new_noise_source_draws": 0,
            "scope": plan["scope"],
        },
    )
    progress(
        name,
        {
            "status": "completed-training",
            "owner": owner,
            "arm": arm,
            "step": 1000,
            "updates": 900,
            "counts": counts,
        },
    )


if __name__ == "__main__":
    raise SystemExit("Use train_flat_spatial_evidence_trial.py")
