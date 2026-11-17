"""Actual V120 mixed-domain execution/loader profile with a valid resumed suffix."""

import argparse
import os
import time
from pathlib import Path

import torch
from profile_raw_kernel_inference import model_hash

from demosaic import train as training
from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json


def profile(plan, case):
    config = checked(plan["profiles"][case])
    output = Path(plan["root"]) / "profiles" / case
    output.mkdir(parents=True, exist_ok=False)
    timings = {"loader_wait_seconds": 0.0, "checkpoint_seconds": 0.0, "measured_steps": 0}
    current = {"step": 0}
    models = []
    calls = {"root": 0, "DINO": 0}
    witnesses = {}
    constructor, selected, update, save, prepare = (
        training.JointDemosaic,
        training.selected_batches,
        training.update_ema,
        training.save_checkpoint,
        training.prepare_training_batch,
    )

    def construct(options):
        model = constructor(options)
        model.register_forward_pre_hook(lambda *_: calls.__setitem__("root", calls["root"] + 1))
        model.context.backbone.register_forward_pre_hook(
            lambda *_: calls.__setitem__("DINO", calls["DINO"] + 1)
        )
        models.append(model)
        return model

    def batches(*args, **kwargs):
        iterator = iter(selected(*args, **kwargs))
        while True:
            if current["step"] == 25 and "start" not in timings:
                torch.cuda.synchronize()
                timings["start"] = time.perf_counter()
            began = time.perf_counter()
            try:
                item = next(iterator)
            except StopIteration:
                return
            current["step"] = item[0]
            if 26 <= item[0] <= 75:
                timings["loader_wait_seconds"] += time.perf_counter() - began
                timings["measured_steps"] += 1
            yield item

    def update_ema(*args, **kwargs):
        result = update(*args, **kwargs)
        if current["step"] == 75:
            torch.cuda.synchronize()
            timings["end"] = time.perf_counter()
        return result

    def save_checkpoint(*args, **kwargs):
        began = time.perf_counter()
        result = save(*args, **kwargs)
        timings["checkpoint_seconds"] += time.perf_counter() - began
        return result

    def prepare_batch(step, domain, *args, **kwargs):
        batch = prepare(step, domain, *args, **kwargs)
        if step in [1, 2, 6, 76, 77]:
            witnesses[str(step)] = {
                "domain": domain,
                "fingerprint": training.batch_fingerprint(batch),
            }
        return batch

    training.JointDemosaic = construct
    training.selected_batches = batches
    training.update_ema = update_ema
    training.save_checkpoint = save_checkpoint
    training.prepare_training_batch = prepare_batch
    checkpoint = training.train(config, initialize=checked(plan["parent"]), stop_after=75)
    kept = output / "discarded-step75.pt"
    os.link(checkpoint, kept)
    first = reference(kept)
    checkpoint = training.train(config, resume=checkpoint, stop_after=2)
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    assert state["step"] == 77 and len(state["model"]) == len(state["ema"]) == 91
    assert len(state["optimizer"]["state"]) == 89
    finite = 0
    for group in [state["model"], state["ema"]]:
        for value in group.values():
            assert torch.isfinite(value).all()
            finite += value.numel()
    for group in state["optimizer"]["state"].values():
        assert group["step"] == 77
        for value in group.values():
            assert torch.isfinite(value).all()
            finite += value.numel()
    assert calls == {"root": 77, "DINO": 77}
    assert all(model_hash(m.context.backbone) == plan["DINO_sha256"] for m in models)
    assert all(all(p.grad is None for p in m.context.backbone.parameters()) for m in models)
    assert timings["measured_steps"] == 50
    duration = timings["end"] - timings["start"]
    result = {
        "case": case,
        "config": reference(config),
        "script": reference(__file__),
        "plan": reference(Path(plan["root"]) / "plan.json"),
        "warmup_updates": 25,
        "measured_updates": 50,
        "native_patches_measured": 800,
        "measured_seconds": duration,
        "patches_per_second": 800 / duration,
        "loader_wait_seconds": timings["loader_wait_seconds"],
        "loader_wait_fraction": timings["loader_wait_seconds"] / duration,
        "checkpoint_seconds_outside_measurement": timings["checkpoint_seconds"],
        "step75": first,
        "resumed_step77": reference(checkpoint),
        "sampled_input_witnesses_outside_measurement": witnesses,
        "model_EMA_optimizer_finite_values": finite,
        "actual_calls": calls,
        "DINO_unchanged": True,
        "runtime": state["config"]["training_execution_runtime"],
        "scope": "Actual pinned V120 native256/B16/BF16 mixed-domain full-restoration updates.100k LR/order horizon preserved while discarding75+2 optimizer checks.25warm+50measured includes loaders/degradation/forward/backward/Adam/EMA; excludes initialization,warmup,final save/audit and resumed suffix. No GT/reference validation score, trained-quality or batch-size-optimum claim. Only5 full input witnesses outside timed window; production retains sampled standard logs, not every-step GPU readback.",
    }
    write_json(output / "result.json", result)
    print(
        {
            k: v
            for k, v in result.items()
            if k
            in [
                "case",
                "measured_seconds",
                "patches_per_second",
                "loader_wait_fraction",
                "actual_calls",
            ]
        },
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("case")
    args = parser.parse_args()
    plan = read_json(args.plan)
    verify_plan(plan)
    assert reference(__file__) == plan["profile_script"]
    torch.cuda.set_per_process_memory_fraction(
        16 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    profile(plan, args.case)
