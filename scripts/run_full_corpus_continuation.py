"""Execute a declared full-model phase with complete resume and bounded data witnesses."""

import argparse
import hashlib
import json
import os
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import yaml
from profile_raw_kernel_inference import model_hash

from demosaic import train as training
from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json
from demosaic.experiments.runtime import owner_identity


def run(plan_path, arm, updates):
    plan = read_json(plan_path)
    verify_plan(read_json(checked(plan["profile_plan"])))
    assert reference(__file__) == plan["worker_script"]
    config_path = checked(plan["configs"][arm])
    config = yaml.safe_load(config_path.read_text())
    run_dir = Path(config["run"])
    run_dir.mkdir(parents=True, exist_ok=True)
    last = run_dir / "last.pt"
    resume = last.exists()
    initial = torch.load(
        last if resume else checked(plan["parent"]), map_location="cpu", weights_only=True
    )
    first = initial["step"] if resume else 0
    expected = initial["model"] if resume else initial.get("ema", initial["model"])
    target = min(config["steps"], first + updates)
    assert first < target
    del initial
    phase = run_dir / f"phase-{first + 1:06d}-{target:06d}"
    phase.mkdir()
    write_json(phase / "owner.json", owner_identity() | {"production_plan": reference(plan_path)})
    raw_ctor, raw_prepare, raw_save, raw_selected = (
        training.JointDemosaic,
        training.prepare_training_batch,
        training.save_checkpoint,
        training.selected_batches,
    )
    calls = {"root": 0, "DINO": 0}
    models = []
    initial_checks = []
    conditions = []
    condition_files = []
    sources = Counter()
    crop_boxes = set()
    domains = Counter()
    full_witnesses = []
    timings = {
        "loader_wait_seconds": 0.0,
        "prepare_dispatch_seconds": 0.0,
        "checkpoint_seconds": 0.0,
    }
    checkpoints = []

    def construct(options):
        model = raw_ctor(options)
        models.append(model)

        def forward_check(*_):
            if not initial_checks:
                actual = model.restoration_state_dict()
                assert len(actual) == len(expected) == 91
                assert all(torch.equal(v.detach().cpu(), expected[k]) for k, v in actual.items())
                assert model_hash(model.context.backbone) == plan["DINO_sha256"]
                initial_checks.append(
                    {
                        "before_first_neural_forward": True,
                        "all91_tensors_exact": True,
                        "from_step": first,
                        "fresh_optimizer": not resume,
                    }
                )
            calls["root"] += 1

        model.register_forward_pre_hook(forward_check)
        model.context.backbone.register_forward_pre_hook(
            lambda *_: calls.__setitem__("DINO", calls["DINO"] + 1)
        )
        return model

    def flush_conditions():
        if not conditions:
            return
        steps = [r[0] for r in conditions]
        path = phase / f"conditions-{steps[0]:06d}-{steps[-1]:06d}.npz"
        values = torch.stack([r[2] for r in conditions]).cpu().numpy()
        with path.open("xb") as stream:
            np.savez_compressed(
                stream,
                steps=np.array(steps),
                domains=np.array([r[1] for r in conditions]),
                values=values,
            )
        condition_files.append(reference(path))
        conditions.clear()

    observations = (phase / "source-crop-observations.jsonl").open("x")

    def prepare(step, domain, clean, **kwargs):
        began = time.perf_counter()
        batch = raw_prepare(step, domain, clean, **kwargs)
        timings["prepare_dispatch_seconds"] += time.perf_counter() - began
        domains[domain] += 1
        source = clean.get("source", [])
        parsed = [json.loads(v) if isinstance(v, str) else v for v in source]
        for item in parsed:
            if isinstance(item, dict) and item.get("source_id"):
                identity = item["source_id"]
                sources[identity] += 1
                if item.get("cache_xywh"):
                    crop_boxes.add((identity, tuple(item["cache_xywh"])))
        seed = int.from_bytes(
            hashlib.sha256(f"data:{config['seed']}:{step}".encode()).digest()[:8], "little"
        ) % (2**63)
        observations.write(
            json.dumps(
                {
                    "step": step,
                    "domain": domain,
                    "global_draw_start": (step - 1) * config["batch_size"],
                    "data_RNG_seed": seed,
                    "sources": parsed,
                },
                sort_keys=True,
            )
            + "\n"
        )
        size = len(batch["packed"])
        condition = (
            torch.cat(
                [
                    batch["shot"].reshape(size, -1),
                    batch["read"].reshape(size, -1),
                    batch["wb"].reshape(size, -1),
                    batch["matrix"].reshape(size, -1),
                ],
                dim=1,
            )
            .detach()
            .float()
            .clone()
        )
        conditions.append((step, domain, condition))
        if len(conditions) >= 250:
            flush_conditions()
            observations.flush()
        if step == first + 1 or step % 1000 == 0:
            full_witnesses.append(
                {"step": step, "domain": domain, "batch_sha256": training.batch_fingerprint(batch)}
            )
        return batch

    def selected(*args, **kwargs):
        iterator = iter(raw_selected(*args, **kwargs))
        while True:
            began = time.perf_counter()
            try:
                item = next(iterator)
            except StopIteration:
                return
            timings["loader_wait_seconds"] += time.perf_counter() - began
            yield item

    def save(path, model, optimizer, ema, step, cfg, best):
        began = time.perf_counter()
        result = raw_save(path, model, optimizer, ema, step, cfg, best)
        timings["checkpoint_seconds"] += time.perf_counter() - began
        if Path(path).name == "last.pt" and step in plan["retained_steps"]:
            target_file = run_dir / f"step{step:06d}.pt"
            if not target_file.exists():
                os.link(path, target_file)
                checkpoints.append(reference(target_file))
                write_json(
                    run_dir / f"step{step:06d}-receipt.json",
                    {
                        "checkpoint": checkpoints[-1],
                        "global_step": step,
                        "LR_horizon": cfg["steps"],
                        "config": reference(config_path),
                        "scope": "Immutable optimizer/EMA/RNG/source-order checkpoint on the original declared schedule.",
                    },
                )
        return result

    training.JointDemosaic = construct
    training.prepare_training_batch = prepare
    training.save_checkpoint = save
    training.selected_batches = selected
    began = time.monotonic()
    result = training.train(
        config_path,
        resume=last if resume else None,
        initialize=None if resume else checked(plan["parent"]),
        stop_after=target - first,
    )
    phase_checkpoint = phase / "end.pt"
    os.link(result, phase_checkpoint)
    flush_conditions()
    observations.close()
    state = torch.load(phase_checkpoint, map_location="cpu", weights_only=True)
    assert state["step"] == target and len(state["model"]) == len(state["ema"]) == 91
    assert all(item["step"] == target for item in state["optimizer"]["state"].values())
    assert all(model_hash(m.context.backbone) == plan["DINO_sha256"] for m in models)
    summary = {
        "arm": arm,
        "from_step": first,
        "to_step": target,
        "LR_horizon": config["steps"],
        "optimizer_EMA_RNG_preserved_on_resume": resume,
        "initial_checks": initial_checks,
        "actual_calls_including_monitoring": calls,
        "training_updates": target - first,
        "examples": (target - first) * config["batch_size"],
        "domains": dict(domains),
        "distinct_photo_sources": len(sources),
        "photo_draws": sum(sources.values()),
        "unique_source_crop_boxes": len(crop_boxes),
        "corruption_condition_files": condition_files,
        "condition_columns": [
            "shot",
            "read",
            "wbR",
            "wbG",
            "wbB",
            *[f"matrix{i}{j}" for i in range(3) for j in range(3)],
        ],
        "source_crop_observations": reference(phase / "source-crop-observations.jsonl"),
        "source_visit_counts": dict(sources),
        "full_batch_witnesses": full_witnesses,
        "seconds": time.monotonic() - began,
        "timings": timings,
        "retained_checkpoints": checkpoints,
        "last": reference(phase_checkpoint),
        "live_resume_path": str(result),
        "DINO_unchanged": True,
        "production_plan": reference(plan_path),
        "scope": "Declared phase of one continuation, complete Adam/EMA/RNG/global-index resume. CPU source/crop metadata every update; actual shot/read/WB/matrix records transferred in250-update batches; full GPU batch hashes only initial/every1000. Crop-box diversity is not disjoint native-pixel coverage. RNG keys include ADC/noise-free recipes, not all positive-noise observations. Larger-run milestone quality remains separate.",
    }
    write_json(phase / "completed.json", summary)
    if target == config["steps"]:
        write_json(
            run_dir / "completed.json",
            {
                "phase": reference(phase / "completed.json"),
                "steps": target,
                "checkpoint": reference(phase_checkpoint),
                "DINO_unchanged": True,
            },
        )
    print(
        {
            k: v
            for k, v in summary.items()
            if k in ["arm", "from_step", "to_step", "examples", "seconds", "distinct_photo_sources"]
        },
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("arm")
    parser.add_argument("--updates", type=int, required=True)
    args = parser.parse_args()
    assert args.updates > 0
    os.nice(10)
    torch.cuda.set_per_process_memory_fraction(
        16 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    run(args.plan, args.arm, args.updates)
