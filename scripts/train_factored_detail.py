"""Compare direct and post-gate band-limited corrections on a shared frozen parent."""

import argparse
import json
import math
import random
import time
from itertools import product
from pathlib import Path

import psutil
import torch
from profile_raw_kernel_inference import model_hash
from train_local_paired_continuation import (
    CORE,
    FORWARD_ARGS,
    PROFILES,
    PairedBands,
    gap_projection,
    observations,
)

from demosaic.cfa import PATTERNS, mosaic
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.runtime import owner_identity
from demosaic.factored_detail import FactoredLuminanceDetail
from demosaic.inference import _stage_tiled_cuda
from demosaic.losses import reconstruction_loss
from demosaic.precision import amp_context, ieee_fp32
from demosaic.scene_inference import load_scene_checkpoint

ARMS = {"direct": False, "band-limited": True}
SEED = 202611191447


def ancestor_plans(end):
    plans = {}
    pending = [end]
    while pending:
        path = pending.pop()
        ref = read_json(path)["plan"]
        if ref["sha256"] in plans:
            continue
        plan = read_json(checked(ref))
        plans[ref["sha256"]] = (ref, plan)
        pending.extend(
            checked(plan[key])
            for key in ("parent_completion", "comparison_completion")
            if key in plan
        )
    return plans.values()


def prepare(root, parent_completion, scene_path):
    prior_end = read_json(parent_completion)
    prior = read_json(checked(prior_end["plan"]))
    manifest = read_json(scene_path)["train_manifest"]
    if (
        prior_end["qualification"]
        or not prior_end["DINO_unchanged"]
        or prior_end["updates_per_arm"] != prior["steps_per_arm"]
        or set(prior_end["checkpoints"]) != {"wire-aligned", "strong-gap"}
        or manifest not in prior["inputs"]
    ):
        raise ValueError("Require the matched continuing-wire endpoints and bound train split")
    parent = prior_end["checkpoints"]["wire-aligned"]
    checked(parent)
    ancestors = ancestor_plans(parent_completion)
    schedule_refs = [
        plan[key] for _, plan in ancestors for key in ("schedule", "qualification_schedule")
    ]
    excluded = {
        case["source"]["id"] for binding in schedule_refs for case in read_json(checked(binding))
    }
    rows = [json.loads(line) for line in checked(manifest).read_text().splitlines() if line]
    assert len(rows) == 90692 and all(row["split"] == "train" for row in rows)
    eligible = [row for row in rows if row["id"] not in excluded]

    rng = random.Random(SEED)
    cells = list(product(("natural", "wire"), PROFILES, PATTERNS, ("coupled", "independent")))
    recipes = cells * 15
    rng.shuffle(recipes)
    preflight = [cells[i] for i in (0, 3, 8, 11, 17, 18, 25, 26)]
    selected = rng.sample(eligible, len(recipes) + len(preflight))
    root.mkdir(parents=True)
    work, frozen = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    schedules = {}
    for name, split, draws in (
        ("schedule", selected[: len(recipes)], recipes),
        ("qualification_schedule", selected[len(recipes) :], preflight),
    ):
        visits = dict.fromkeys(cells, 0)
        cases = []
        for row, cell in zip(split, draws, strict=True):
            kind, iso, pattern, law = cell
            case = {"source": row, "kind": kind, "iso": iso, "pattern": pattern, "law": law}
            if kind == "wire":
                case["strong_continues"] = (
                    visits[cell] % 5 != 0 if name == "schedule" else len(cases) % 2 == 0
                )
                visits[cell] += 1
            cases.append(case)
        path = root / (name + ".json")
        write_json(path, cases)
        schedules[name] = reference(path)

    write_json(
        root / "plan.json",
        {
            "id": root.name,
            "parent_completion": reference(parent_completion),
            "parent": parent,
            "parent_step": prior_end["updates_per_arm"],
            "DINO_sha256": prior["DINO_sha256"],
            "train_manifest": manifest,
            "inputs": [
                parent,
                reference(parent_completion),
                reference(scene_path),
                manifest,
                *(ref for ref, _ in ancestors),
                *schedule_refs,
                *schedules.values(),
            ],
            "frozen_files": frozen,
            "driver": reference(work / "scripts" / Path(__file__).name),
            **schedules,
            "excluding_distinct_prior_ids": len(excluded),
            "seed": SEED,
            "steps_per_arm": len(recipes),
            "arms": ARMS,
            "pair_bands_cycles_per_pixel": prior["pair_bands_cycles_per_pixel"],
            "loss_weights": {
                "pair": 0.8,
                "repeat": 0.5,
                "weak_response": 1.6,
                "strong_gap": 1.6,
                "quiet_lift": 0.15,
            },
            "optimizer": {
                "peak_lr": 0.001,
                "warmup": 24,
                "minimum_factor": 0.2,
                "ema": 0.985,
                "weight_decay": 0.0001,
            },
            "scope": "Frozen aligned-control EMA. Same zero start, features, updates, and losses. "
            "Only the delivered signed correction's band filtering differs. "
            "Inference uses one Bayer frame; no waveform, reference or scene oracle.",
        },
    )


def prepare_floor(root, replay_plan):
    """Track whether bounding the confidence below changes the same band-limited fit."""
    replay = reference(replay_plan)
    plan = read_json(checked(replay))
    verify_plan(plan)
    if plan["arms"] != ARMS or plan.get("gain_floor", 0.0) != 0.0:
        raise ValueError("Replay the original matched correction plan")
    root.mkdir(parents=True)
    work, sources = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        plan
        | {
            "id": root.name,
            "inputs": [replay, *plan["inputs"]],
            "sources_replayed_from": replay,
            "frozen_files": sources,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "arms": {"band-limited": True},
            "gain_floor": 0.25,
            "scope": "Repeat the original band-limited fit on the identical ordered schedule "
            "and with the same objective, adding a 0.25 confidence gain floor.",
        },
    )


def objective(prediction, delta, batch, bands, wire, projection, independent, weights):
    absolute, _ = reconstruction_loss(
        prediction,
        batch,
        auxiliary=mosaic(prediction, batch["colors"]),
        camera_supervision="sensor-valid-v1",
        reconstruction_charbonnier_epsilon=0.0003,
    )
    paired, valid = bands.redraw_losses(prediction, batch, align=wire is not None)
    quiet = delta[4:, :, CORE, CORE]
    penalties = {
        "absolute": absolute,
        "pair": paired["mean"],
        "quiet_lift": ((quiet.square() + 1e-8).sqrt() - 1e-4).mean(),
    }
    if independent:
        penalties["repeat"] = paired["repeat"]
    if wire is not None:
        penalties["weak_response"] = paired["aligned"]
        penalties["strong_gap"] = bands.continuing_wire_loss(prediction, batch, projection)
    loss = sum(weights.get(key, 1.0) * value for key, value in penalties.items())
    return loss, penalties, valid


def train(plan_path, output, *, qualification):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert checked(plan["driver"]) == Path(__file__)
    arms = plan["arms"]
    gain_floor = plan.get("gain_floor", 0.0)
    assert arms == (ARMS if gain_floor == 0.0 else {"band-limited": True})
    key = "qualification_schedule" if qualification else "schedule"
    schedule = read_json(checked(plan[key]))
    output.mkdir()
    write_json(output / "owner.json", owner_identity())
    torch.set_num_threads(2)
    torch.manual_seed(plan["seed"])
    started = time.monotonic()
    binding = plan["parent"]
    parent, state = load_scene_checkpoint(
        checked(binding),
        device="cpu",
        weights="ema",
        expected_sha256=binding["sha256"],
    )
    assert state["mode"] == "none" and state["step"] == plan["parent_step"]
    assert model_hash(parent.base.context.backbone) == plan["DINO_sha256"]
    del state
    parent.requires_grad_(False)
    _stage_tiled_cuda(parent, torch.device("cuda"))
    heads = {
        arm: FactoredLuminanceDetail(band_limited=filtered, gain_floor=gain_floor).to(
            "cuda", memory_format=torch.channels_last
        )
        for arm, filtered in arms.items()
    }
    first_head = next(iter(heads.values()))
    for head in list(heads.values())[1:]:
        head.load_state_dict(first_head.state_dict())
    policy = plan["optimizer"]
    optimizers = {
        arm: torch.optim.AdamW(head.parameters(), weight_decay=policy["weight_decay"], fused=True)
        for arm, head in heads.items()
    }
    averages = {
        arm: {k: v.detach().clone() for k, v in head.state_dict().items()}
        for arm, head in heads.items()
    }
    bands = PairedBands("cuda", plan["pair_bands_cycles_per_pixel"])
    valid_pairs = 0
    began = time.monotonic()
    with (
        (output / "observations.jsonl").open("x", buffering=1) as trace,
        (output / "train.jsonl").open("x", buffering=1) as log,
        ieee_fp32(),
    ):
        for step, example in enumerate(schedule, start=1):
            if psutil.virtual_memory().available < 24 * 2**30:
                raise RuntimeError("Insufficient unified memory for a full training step")
            values, about = observations(
                example,
                step + (plan["steps_per_arm"] if qualification else 0),
                pair_draws=2,
                seed=plan["seed"],
            )
            trace.write(json.dumps(about, sort_keys=True) + "\n")
            batch = {k: v.cuda() for k, v in values.items()}
            for key in ("packed", "variance", "target", "sensor_target"):
                batch[key] = batch[key].contiguous(memory_format=torch.channels_last)
            inputs = tuple(batch[k] for k in FORWARD_ARGS)
            wire = about["geometry"].get("wire")
            projection = gap_projection(wire, continuing=True).cuda() if wire else None
            parent.base.set_noise(about["camera"]["shot"], about["camera"]["read"])
            with torch.no_grad(), amp_context("cuda", dtype="bfloat16"):
                base = parent(*inputs)
                frames, scale, direction = first_head.features(base, *inputs)
            assert base.dtype == torch.float32
            warmup = policy["warmup"]
            progress = max(0, step - warmup) / (plan["steps_per_arm"] - warmup)
            floor = policy["minimum_factor"]
            lr = (
                policy["peak_lr"]
                * min(1.0, step / warmup)
                * (floor + (1 - floor) * (1 + math.cos(math.pi * progress)) / 2)
            )
            record = {"step": step, "lr": lr}
            for arm, head in heads.items():
                optimizer = optimizers[arm]
                optimizer.param_groups[0]["lr"] = lr
                optimizer.zero_grad(set_to_none=True)
                with amp_context("cuda", dtype="bfloat16"):
                    delta = head.correction(frames, scale)
                prediction = base + direction * delta
                if step == 1:
                    assert torch.equal(prediction, base)
                loss, penalties, valid = objective(
                    prediction,
                    delta,
                    batch,
                    bands,
                    wire,
                    projection,
                    about["law"] == "independent",
                    plan["loss_weights"],
                )
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(
                    head.parameters(), 1.0, error_if_nonfinite=True
                )
                optimizer.step()
                with torch.no_grad():
                    for name, value in head.state_dict().items():
                        averages[arm][name].lerp_(value, 1 - policy["ema"])
                record[arm] = {"loss": float(loss.detach()), "gradient": float(norm)} | {
                    name: float(value.detach()) for name, value in penalties.items()
                }
            valid_pairs += int(valid)
            log.write(json.dumps(record, sort_keys=True, allow_nan=False) + "\n")
            if step % 32 == 0 or step == len(schedule):
                print(step, valid_pairs, round(time.monotonic() - began, 2), record, flush=True)
    elapsed = time.monotonic() - began
    assert not any(param.requires_grad or param.grad is not None for param in parent.parameters())
    checkpoints = {}
    for arm, head in heads.items():
        path = output / f"{arm}.pt"
        temporary = path.with_suffix(".incomplete")
        torch.save(
            {
                "parent": binding,
                "parent_weights": "ema",
                "band_limited": head.band_limited,
                "gain_floor": head.gain_floor,
                "model": {k: v.detach().cpu() for k, v in head.state_dict().items()},
                "ema": {k: v.cpu() for k, v in averages[arm].items()},
                "optimizer": optimizers[arm].state_dict(),
                "step": len(schedule),
                "plan": reference(plan_path),
            },
            temporary,
        )
        temporary.rename(path)
        checkpoints[arm] = reference(path)
    write_json(
        output / "completed.json",
        {
            "plan": reference(plan_path),
            "parent": binding,
            "qualification": qualification,
            "checkpoints": checkpoints,
            "updates_per_arm": len(schedule),
            "source_photos_per_arm": len(schedule),
            "native_observations_per_arm": len(schedule) * 6,
            "valid_core_pairs": valid_pairs,
            "training_seconds": elapsed,
            "total_seconds": time.monotonic() - started,
            "weights": "Raw and EMA correction tensors.",
            "frozen_parent": True,
            "precision": "CUDA BF16 neural layers with FP32 residual and loss",
            "observations": reference(output / "observations.jsonl"),
            "log": reference(output / "train.jsonl"),
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    lock = sub.add_parser("prepare")
    for name in ("root", "parent_completion", "scene_plan"):
        lock.add_argument(name, type=Path)
    floor = sub.add_parser("prepare-floor")
    floor.add_argument("root", type=Path)
    floor.add_argument("replay_plan", type=Path)
    run = sub.add_parser("train")
    run.add_argument("plan", type=Path)
    run.add_argument("output", type=Path)
    run.add_argument("--qualification", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.root.absolute(), args.parent_completion, args.scene_plan)
    elif args.command == "prepare-floor":
        prepare_floor(args.root.absolute(), args.replay_plan)
    else:
        train(args.plan, args.output, qualification=args.qualification)
