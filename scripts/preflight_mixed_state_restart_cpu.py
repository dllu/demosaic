"""Exercise actual mixed16 parent states through four CPU updates versus 2+2.

Uses cropped, already generated training-only fixtures and production optimizer,
grouped backward, EMA and checkpoint operators. All learned weights are discarded.
This is not a loader/degradation, CUDA restart, production continuation or quality test.
"""

import argparse
import copy
import gc
import hashlib
import json
import math
import os
import random
from pathlib import Path

import numpy as np
import psutil
import torch
from review_mixed_packed_trial import read, ref, sha

from demosaic.inference import load_checkpoint
from demosaic.optimizer_batches import backward_groups
from demosaic.train import (
    batch_fingerprint,
    make_optimizer,
    save_checkpoint,
    set_learning_rate,
    update_ema,
)

BASE = Path("/mnt/external/demosaic")
REVIEW = BASE / "benchmarks/packed-isotropic-mixed16-first32000-review-workflow-v1/plan.json"
FIXTURES = BASE / "benchmarks/packed-isotropic-production-replay-v1/fixtures.json"


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def guard(plan):
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path


def tensors_digest(items):
    value = hashlib.sha256()
    for name, tensor in items:
        value.update(str(name).encode())
        value.update(str(tensor.dtype).encode())
        value.update(str(tuple(tensor.shape)).encode())
        value.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return value.hexdigest()


def optimizer_digest(optimizer):
    state = optimizer.state_dict()
    values = [
        (f"{i}/{key}", value)
        for i, row in state["state"].items()
        for key, value in sorted(row.items())
    ]
    assert all(torch.is_tensor(value) for _, value in values)
    return {"tensors": tensors_digest(values), "param_groups": copy.deepcopy(state["param_groups"])}


def prepare(output):
    assert not torch.cuda.is_initialized()
    assert sha(REVIEW) == "77435a0e0f3b255a52751c4caaaecc4c9cef2e969730af1c12288d9874a1841d"
    review = read(REVIEW)
    guard(review)
    workflow = read(review["training_workflow"])
    assert (
        workflow["status"]
        == "completed-matched-mixed16-first32000-examples-awaiting-full-quality-review"
    )
    fixtures = read(FIXTURES)
    assert [x["production_step"] for x in fixtures] == list(range(8001, 8017))
    inputs = {str(REVIEW): sha(REVIEW), str(FIXTURES): sha(FIXTURES)}
    for entry in fixtures:
        item = entry["fixture"]
        assert sha(item["path"]) == item["sha256"]
        inputs[item["path"]] = item["sha256"]
    arms = []
    for name in ("no-dino", "dino"):
        parent = workflow["completed"]["finish-" + name]["checkpoint"]
        assert sha(parent["path"]) == parent["sha256"]
        inputs[parent["path"]] = parent["sha256"]
        arms.append({"arm": name, "parent": parent})
    import demosaic

    guards = {**review["inputs"], **review["guards"]}
    guards.update(
        {
            str(path.resolve()): sha(path)
            for path in [Path(__file__), *Path(demosaic.__file__).parent.glob("*.py")]
        }
    )
    output = Path(output).resolve()
    assert output.parent == BASE / "benchmarks" and not output.exists()
    output.mkdir()
    (output / "driver.py").write_bytes(Path(__file__).read_bytes())
    guards[str(output / "driver.py")] = sha(output / "driver.py")
    plan = {
        "root": str(output),
        "arms": arms,
        "fixtures": ref(FIXTURES),
        "inputs": inputs,
        "guards": guards,
        "protocol": "Each genuine 2k/32000-example parent: four IEEE-FP32 CPU mixed updates versus 2+2 with a real save/reload, effective16 through four B4 forwards. Use native64 top-left crops of existing production training-only fixtures8001-8016, without loading or augmenting unselected data. Restore model, Adam, EMA, best, optimizer/source/example counters and Python/Torch CPU RNG. Sentinel draws make RNG restoration observable. Preserve original40000-update schedule,500warmup,LR/EMA/grouping/precision/loss; model capacity and genuine frozen DINO unchanged. Compare exact final tensors, Adam groups/moments, EMA, counters, RNG and all losses/observations. Delete only this test's midpoint checkpoint after success; no learned weights admitted. Does not test the full train() loader/degradation loop, CUDA RNG/kernels, production-size performance, photographic quality or authorize a longer run.",
    }
    save(output / "plan.json", plan)
    print(
        json.dumps(
            {"prepared": ref(output / "plan.json"), "inputs": len(inputs), "guards": len(guards)}
        ),
        flush=True,
    )


def restore(path):
    # Deliberately unrelated ambient states make an omitted RNG restore fail.
    torch.manual_seed(918273)
    random.seed(182736)
    model, state = load_checkpoint(path, "cpu")
    assert state["step"] in (2000, 2002)
    cfg = copy.deepcopy(state["config"])
    assert cfg["steps"] == 40000 and cfg["warmup_steps"] == 500
    assert cfg["precision"] == "float32" and cfg["optimizer_batch_groups"] == 4
    assert cfg["optimizer_forward_groups"] == 1 and cfg["batch_size"] == 4
    model.to(memory_format=torch.channels_last)
    missing = model.load_state_dict(state["model"], strict=False)
    assert not missing.unexpected_keys
    assert all(k.startswith("context.backbone.") for k in missing.missing_keys)
    assert all(torch.equal(v, state["model"][k]) for k, v in model.restoration_state_dict().items())
    optimizer = make_optimizer(model, cfg)
    optimizer.load_state_dict(state["optimizer"])
    actual = optimizer.state_dict()
    assert actual["param_groups"] == state["optimizer"]["param_groups"]
    assert actual["state"].keys() == state["optimizer"]["state"].keys()
    assert all(
        torch.equal(value, state["optimizer"]["state"][i][key])
        for i, row in actual["state"].items()
        for key, value in row.items()
    )
    ema = {k: v.clone() for k, v in state["ema"].items()}
    assert all(torch.equal(v, state["ema"][k]) for k, v in ema.items())
    torch.set_rng_state(state["torch_rng"])
    random.setstate(state["python_rng"])
    assert torch.equal(torch.get_rng_state(), state["torch_rng"])
    assert random.getstate() == state["python_rng"]
    first, best = state["step"], state["best"]
    assert state["data_step"] == first * 4 and state["example_draws"] == first * 16
    context = tensors_digest(model.context.backbone.state_dict().items()) if model.context else None
    del state
    return model, optimizer, ema, cfg, first, best, context


def snapshot(model, optimizer, ema, step, best):
    return {
        "model": tensors_digest(model.restoration_state_dict().items()),
        "ema": tensors_digest(ema.items()),
        "optimizer": optimizer_digest(optimizer),
        "torch_rng": hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest(),
        "python_rng": hashlib.sha256(repr(random.getstate()).encode()).hexdigest(),
        "step": step,
        "data_step": step * 4,
        "example_draws": step * 16,
        "best": best,
    }


def segment(parent, batches, fixtures, end, midpoint=None):
    model, optimizer, ema, cfg, start, best, context = restore(parent)
    trace = []
    for step in range(start + 1, end + 1):
        selected = [
            (x["production_step"], x["domain"], batches[x["production_step"]])
            for x in fixtures[(step - 2001) * 4 : (step - 2000) * 4]
        ]
        assert len(selected) == 4 and selected[-1][0] == step * 4
        sentinel = [torch.rand(()).item(), random.random()]
        warm = min(1, step / cfg["warmup_steps"])
        progress = max(0, step - cfg["warmup_steps"]) / (cfg["steps"] - cfg["warmup_steps"])
        lr = cfg["lr"] * warm * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
        set_learning_rate(optimizer, lr)
        model.train()
        optimizer.zero_grad(set_to_none=True)
        loss, _, grad_norm, observations = backward_groups(
            model,
            selected,
            lambda _step, _domain, values: values,
            cfg,
            fingerprint=batch_fingerprint,
        )
        assert torch.isfinite(loss) and torch.isfinite(grad_norm)
        assert all(
            p.grad is not None and torch.isfinite(p.grad).all()
            for p in model.parameters()
            if p.requires_grad
        )
        optimizer.step()
        update_ema(model, ema, min(cfg["ema_decay"], (1 + step) / (10 + step)))
        trace.append(
            {
                "step": step,
                "loss": loss.item(),
                "grad_norm": grad_norm.item(),
                "lr": lr,
                "RNG_sentinels": sentinel,
                "source_groups": observations,
            }
        )
        print(json.dumps({"step": step, "loss": loss.item()}), flush=True)
    if context:
        assert not model.context.backbone.training
        assert context == tensors_digest(model.context.backbone.state_dict().items())
        assert all(
            not p.requires_grad and p.grad is None for p in model.context.backbone.parameters()
        )
    assert all(
        int(row["step"]) == end and all(torch.isfinite(v).all() for v in row.values())
        for row in optimizer.state.values()
    )
    final = snapshot(model, optimizer, ema, end, best)
    if midpoint:
        assert not midpoint.exists()
        save_checkpoint(midpoint, model, optimizer, ema, end, cfg, best)
    del model, optimizer, ema
    gc.collect()
    return final, trace


def run(plan_path):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    os.nice(10)
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    with (root / "run.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    fixtures = read(plan["fixtures"]["path"])
    batches, evidence = {}, []
    for row in fixtures:
        with np.load(row["fixture"]["path"], allow_pickle=False) as data:
            values = {k: torch.from_numpy(data[k].copy()) for k in data.files}
        assert batch_fingerprint(values) == row["batch_fingerprint"]
        cropped = {}
        for key, value in values.items():
            if value.ndim == 4 and value.shape[-2:] == (256, 256):
                value = value[..., :64, :64].clone()
            elif value.ndim == 4 and value.shape[-2:] == (128, 128):
                value = value[..., :32, :32].clone()
            cropped[key] = value
        assert cropped["packed"].shape == (4, 4, 32, 32)
        assert cropped["target"].shape == (4, 3, 64, 64)
        batches[row["production_step"]] = cropped
        evidence.append(
            {
                "source_data_step": row["production_step"],
                "domain": row["domain"],
                "original_fixture": row["fixture"],
                "full_fixture_fingerprint_verified": True,
                "cropped_fingerprint": batch_fingerprint(cropped),
            }
        )
    arms = []
    for arm in plan["arms"]:
        full, full_trace = segment(arm["parent"]["path"], batches, fixtures, 2004)
        midpoint = root / (arm["arm"] + "-discarded-CPU-midpoint.pt")
        _, first_trace = segment(arm["parent"]["path"], batches, fixtures, 2002, midpoint)
        midpoint_hash = sha(midpoint)
        resumed, second_trace = segment(midpoint, batches, fixtures, 2004)
        assert full == resumed and full_trace == first_trace + second_trace
        assert all(
            batch_fingerprint(batches[x["source_data_step"]]) == x["cropped_fingerprint"]
            for x in evidence
        )
        midpoint.unlink()
        arms.append(
            {
                "arm": arm["arm"],
                "parent": arm["parent"],
                "full_four_equals_two_plus_two_bitwise": True,
                "final_state_hashes": full,
                "all_four_trace_rows_exact": True,
                "trace": full_trace,
                "midpoint_checkpoint_discarded_SHA256": midpoint_hash,
                "all_learned_weights_discarded": True,
            }
        )
    guard(plan)
    assert not torch.cuda.is_initialized()
    save(
        root / "result.json",
        {
            "status": "completed-genuine-mixed16-2k-state-CPU-four-versus-two-plus-two-restart",
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "plan": ref(plan_path),
            "driver": ref(__file__),
            "arms": arms,
            "training_fixtures": evidence,
            "CUDA_initialized": False,
            "scope": plan["protocol"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", type=Path)
    mode.add_argument("--run", type=Path)
    args = parser.parse_args()
    if args.prepare:
        prepare(args.prepare)
    else:
        run(args.run)
