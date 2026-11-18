"""Matched whole-scene context continuation with replayed observations and crop boxes."""

import argparse
import json
import math
import os
import random
import time
from pathlib import Path

import psutil
import torch
from profile_raw_kernel_inference import model_hash

from demosaic.cfa import mosaic
from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json
from demosaic.experiments.runtime import owner_identity
from demosaic.losses import reconstruction_loss
from demosaic.models import load_model
from demosaic.precision import amp_context
from demosaic.scene_restoration import WholeSceneRestorer
from demosaic.scene_training_data import ScenePhotoDataset


def make_model(plan, mode):
    torch.manual_seed(plan["model_seed"])
    parent_binding = plan["parent"]
    base, payload = load_model(
        "v120",
        checkpoint=checked(parent_binding),
        expected_sha256=parent_binding["sha256"],
        device="cuda",
    )
    assert len(base.restoration_state_dict()) == 91
    parent = payload.get("ema", payload["model"])
    assert all(torch.equal(v.cpu(), parent[k]) for k, v in base.restoration_state_dict().items())
    model = WholeSceneRestorer(base, mode=mode, adapter_width=plan["adapter_width"]).cuda()
    model.to(memory_format=torch.channels_last)
    assert model_hash(base.context.backbone) == plan["DINO_sha256"]
    model.train()
    return model


def sample_forward(model, sample, plan):
    batch = {k: v.cuda() for k, v in sample.crops.items()}
    observation = sample.observation
    model.base.set_noise(observation.recipe.shot, observation.recipe.read)
    with amp_context("cuda", dtype=plan["precision"]):
        encoded = (
            None
            if model.mode == "none"
            else model.encode_scene(
                observation.packed.cuda(),
                observation.colors.cuda(),
                observation.wb.cuda(),
                observation.matrix.cuda(),
                long_side=plan["preview_long_side"],
                exposure=plan["preview_exposure"],
            )
        )
        prediction = model(
            batch["packed"],
            batch["variance"],
            batch["colors"],
            batch["wb"],
            batch["matrix"],
            scene=encoded,
            boxes_xywh=sample.metadata["boxes_xywh"],
        )
        loss, terms = reconstruction_loss(
            prediction,
            batch,
            auxiliary=mosaic(prediction, batch["colors"]),
            camera_supervision="sensor-valid-v1",
            reconstruction_charbonnier_epsilon=0.0003,
        )
    return prediction, loss, terms


def optimizer_for(model, plan):
    return torch.optim.AdamW(
        [
            {
                "params": [p for p in model.base.parameters() if p.requires_grad],
                "lr": plan["base_lr"],
            },
            {"params": list(model.adapter.parameters()), "lr": plan["adapter_lr"]},
        ],
        weight_decay=plan["weight_decay"],
    )


def checkpoint(model, plan, step, ema, target, *, optimizer):
    temporary = target.with_suffix(".incomplete")
    assert not target.exists() and not temporary.exists()
    torch.save(
        {
            "model": {k: v.detach().cpu() for k, v in model.restoration_state_dict().items()},
            "ema": {k: v.detach().cpu() for k, v in ema.items()},
            "step": step,
            "optimizer": optimizer.state_dict(),
            "torch_rng": torch.get_rng_state(),
            "python_rng": random.getstate(),
            "cuda_rng": torch.cuda.get_rng_state_all(),
            "scene_draw_index": step * plan["scenes_per_step"],
            "mode": model.mode,
            "plan": reference(Path(plan["root"]) / "plan.json"),
            "base_parent": plan["parent"],
            "DINO_sha256": plan["DINO_sha256"],
            "adapter_width": plan["adapter_width"],
            "precision": plan["precision"],
            "preview_long_side": plan["preview_long_side"],
            "preview_exposure": plan["preview_exposure"],
        },
        temporary,
    )
    temporary.rename(target)
    return reference(target)


def training_dataset(plan):
    order = plan.get("photo_epoch_order")
    dataset = ScenePhotoDataset(
        checked(plan["train_manifest"]),
        seed=plan["data_seed"],
        patch_size=plan["patch_size"],
        crops_per_scene=plan["crops_per_scene"],
        local_contrast_fraction=plan.get("local_contrast_fraction", 0.0),
        photo_epoch_order=checked(order) if order is not None else None,
        photo_epoch_order_sha256=order["sha256"] if order is not None else None,
    )
    if dataset.photo_epoch_order is not None:
        dataset.photo_epoch_order.require_training(
            {"steps": plan["steps"], "batch_size": plan["scenes_per_step"]}
        )
    return dataset


def preflight(plan, output):
    output.mkdir()
    dataset = training_dataset(plan)
    first = 0 if dataset.photo_epoch_order is not None else 2**30
    first_update = first if dataset.photo_epoch_order is not None else first + 1
    results = []
    for mode in plan["modes"]:
        model = make_model(plan, mode)
        calls = {"wrapper": 0, "DINO": 0}
        hooks = [
            model.register_forward_pre_hook(
                lambda *_, count=calls: count.__setitem__("wrapper", count["wrapper"] + 1)
            ),
            model.base.context.backbone.register_forward_pre_hook(
                lambda *_, count=calls: count.__setitem__("DINO", count["DINO"] + 1)
            ),
        ]
        sample = dataset[first]
        obs = sample.observation
        batch = {k: v.cuda() for k, v in sample.crops.items()}
        model.base.set_noise(obs.recipe.shot, obs.recipe.read)
        with torch.no_grad(), amp_context("cuda", dtype="float32"):
            encoded = (
                None
                if mode == "none"
                else model.encode_scene(
                    obs.packed.cuda(),
                    obs.colors.cuda(),
                    obs.wb.cuda(),
                    obs.matrix.cuda(),
                    long_side=plan["preview_long_side"],
                    exposure=plan["preview_exposure"],
                )
            )
            base = model.base(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
            initial = model(
                batch["packed"],
                batch["variance"],
                batch["colors"],
                batch["wb"],
                batch["matrix"],
                scene=encoded,
                boxes_xywh=sample.metadata["boxes_xywh"],
            )
            initial_max_DN16 = float((base - initial).abs().max() * 65535)
            assert initial_max_DN16 <= 1.0
        optimizer = optimizer_for(model, plan)
        began = time.monotonic()
        losses = []
        observations = []
        for step in range(2):
            optimizer.zero_grad(set_to_none=True)
            for j in range(plan["scenes_per_step"]):
                sample = dataset[first_update + step * plan["scenes_per_step"] + j]
                observations.append(sample.metadata)
                _, loss, _ = sample_forward(model, sample, plan)
                assert torch.isfinite(loss)
                (loss / plan["scenes_per_step"]).backward()
                losses.append(float(loss.detach()))
            if mode != "none":
                assert model.adapter.output.weight.grad.abs().sum() > 0
                if step == 1:
                    assert model.adapter.projections[0].weight.grad.abs().sum() > 0
            norm = torch.nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], 1.0
            )
            assert torch.isfinite(norm)
            optimizer.step()
        assert all(p.grad is None for p in model.base.context.backbone.parameters())
        assert model_hash(model.base.context.backbone) == plan["DINO_sha256"]
        temporary = output / (mode + "-discarded-step2.pt")
        state = model.restoration_state_dict()
        bound = checkpoint(model, plan, 2, state, temporary, optimizer=optimizer)
        loaded = torch.load(checked(bound), map_location="cpu", weights_only=True)
        model.load_restoration_state_dict(loaded["ema"])
        optimizer.load_state_dict(loaded["optimizer"])
        assert all(s["step"] == 2 for s in optimizer.state.values())
        assert loaded["scene_draw_index"] == 2 * plan["scenes_per_step"]
        assert all(
            torch.equal(v.cpu(), loaded["ema"][k])
            for k, v in model.restoration_state_dict().items()
        )
        for hook in hooks:
            hook.remove()
        results.append(
            {
                "mode": mode,
                "initial_max_DN16": initial_max_DN16,
                "actual_calls": calls,
                "discarded_updates": 2,
                "losses": losses,
                "training_observations": observations,
                "seconds": time.monotonic() - began,
                "roundtrip_checkpoint": bound,
                "DINO_unchanged": True,
                "scope": "Actual native256/B4 source scenes, shared RAW/crop lineage. Discarded optimizer checks, not quality scores or production initialization.",
            }
        )
        del optimizer, model, base, initial, loaded, state
        torch.cuda.empty_cache()
    write_json(
        output / "result.json",
        {
            "plan": reference(Path(plan["root"]) / "plan.json"),
            "results": results,
            "all_modes_passed": True,
            "script": reference(__file__),
            "owner": owner_identity(),
            "scope": "All declared model, optimizer and roundtrip checks passed. These discarded updates are separate from production initialization and quality evaluation.",
        },
    )
    print(
        [{k: v for k, v in row.items() if k != "training_observations"} for row in results],
        flush=True,
    )


def train(plan, mode, output):
    output.mkdir(parents=True)
    write_json(output / "owner.json", owner_identity())
    dataset = training_dataset(plan)
    model = make_model(plan, mode)
    optimizer = optimizer_for(model, plan)
    ema = {k: v.detach().clone() for k, v in model.restoration_state_dict().items()}
    checkpoints = []
    began = time.monotonic()
    with (
        (output / "observations.jsonl").open("x") as observations,
        (output / "train.jsonl").open("x") as log,
    ):
        for step in range(plan["steps"]):
            if psutil.virtual_memory().available < plan["minimum_runtime_RAM_GiB"] * 2**30:
                raise RuntimeError("Training RAM reserve unavailable")
            if time.monotonic() - began > plan["maximum_arm_seconds"]:
                raise TimeoutError("Training arm deadline reached; no automatic restart")
            ramp = min(1.0, (step + 1) / plan["warmup_steps"])
            decay = 0.5 * (
                1
                + math.cos(
                    math.pi
                    * max(0, step - plan["warmup_steps"])
                    / (plan["steps"] - plan["warmup_steps"])
                )
            )
            for group, lr in zip(
                optimizer.param_groups, [plan["base_lr"], plan["adapter_lr"]], strict=True
            ):
                group["lr"] = lr * ramp * decay
            optimizer.zero_grad(set_to_none=True)
            terms_sum = {}
            for j in range(plan["scenes_per_step"]):
                index = step * plan["scenes_per_step"] + j
                sample = dataset[index]
                observations.write(json.dumps(sample.metadata, sort_keys=True) + "\n")
                _, loss, terms = sample_forward(model, sample, plan)
                if not torch.isfinite(loss):
                    raise FloatingPointError("Nonfinite supervised scene/crop loss")
                (loss / plan["scenes_per_step"]).backward()
                for k, v in terms.items():
                    terms_sum[k] = (
                        terms_sum.get(k, 0.0) + float(v.detach()) / plan["scenes_per_step"]
                    )
            gradient = torch.nn.utils.clip_grad_norm_(
                [p for p in model.parameters() if p.requires_grad], 1.0
            )
            if not torch.isfinite(gradient):
                raise FloatingPointError("Nonfinite scene gradient")
            optimizer.step()
            with torch.no_grad():
                for k, v in model.restoration_state_dict().items():
                    if v.is_floating_point():
                        ema[k].lerp_(v, 1 - plan["ema_decay"])
                    else:
                        ema[k].copy_(v)
            entry = {
                "step": step + 1,
                "seconds": time.monotonic() - began,
                "gradient_norm": float(gradient),
                "terms": terms_sum,
                "learning_rates": [g["lr"] for g in optimizer.param_groups],
            }
            log.write(json.dumps(entry) + "\n")
            if (step + 1) % plan["log_every"] == 0:
                observations.flush()
                log.flush()
                print(mode, entry, flush=True)
                write_json(
                    output / "progress.json", entry | {"owner": owner_identity()}, replace=True
                )
            if (step + 1) % plan["checkpoint_every"] == 0 or step + 1 == plan["steps"]:
                checkpoints.append(
                    checkpoint(
                        model,
                        plan,
                        step + 1,
                        ema,
                        output / f"step{step + 1:06d}.pt",
                        optimizer=optimizer,
                    )
                )
        observations.flush()
        log.flush()
    assert model_hash(model.base.context.backbone) == plan["DINO_sha256"]
    write_json(
        output / "completed.json",
        {
            "mode": mode,
            "steps": plan["steps"],
            "seconds": time.monotonic() - began,
            "checkpoints": checkpoints,
            "observations": reference(output / "observations.jsonl"),
            "script": reference(__file__),
            "plan": reference(Path(plan["root"]) / "plan.json"),
            "DINO_unchanged": True,
            "scope": "Complete fixed matched continuation horizon; no quality-based stopping/restarts. Scene/crop input/target fingerprints retained for every update; context and local paths share frozen DINO weights. Whole-scene semantics effectiveness/false-detail quality review remains required.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["preflight", "train"])
    parser.add_argument("plan", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--mode", choices=["none", "pooled", "spatial"])
    args = parser.parse_args()
    plan = read_json(args.plan)
    verify_plan(plan)
    assert reference(__file__) == plan["training_script"]
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = True
    torch.cuda.set_per_process_memory_fraction(
        min(1.0, plan["maximum_GPU_GiB"] * 2**30 / torch.cuda.get_device_properties(0).total_memory)
    )
    os.nice(10)
    if args.action == "preflight":
        preflight(plan, args.output)
    else:
        assert args.mode is not None
        train(plan, args.mode, args.output)
