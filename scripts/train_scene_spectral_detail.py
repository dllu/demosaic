"""Train matched pooled and aligned scene gates on a frozen V120 RAW residual."""

import argparse
import json
import math
import os
import time
from pathlib import Path

import psutil
import torch
from profile_raw_kernel_inference import model_hash
from torch.nn import functional as F

from demosaic.cfa import mosaic
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.objectives.dc_regret import regional_dc_excess
from demosaic.experiments.runtime import owner_identity
from demosaic.losses import reconstruction_loss
from demosaic.models import load_model
from demosaic.precision import amp_context, ieee_fp32
from demosaic.scene_restoration import encode_scene
from demosaic.scene_spectral_detail import SceneSpectralDetail
from demosaic.scene_training_data import ScenePhotoDataset

MODES = ("pooled", "spatial")


def prepare(root, earlier):
    earlier = reference(earlier)
    parent = read_json(checked(earlier))
    root.mkdir()
    work, sources = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "sources": str(earlier["path"]),
            "inputs": [
                earlier,
                parent["parent"],
                parent["train_manifest"],
                parent["development_manifest"],
            ],
            "frozen_files": sources,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "parent": parent["parent"],
            "DINO_sha256": parent["DINO_sha256"],
            "train_manifest": parent["train_manifest"],
            "development_manifest": parent["development_manifest"],
            "training_sources": parent["training_sources"],
            "data_seed": 202611171625,
            "model_seed": 202611171624,
            "steps": 800,
            "crops_per_scene": 4,
            "patch_size": 256,
            "max_window": 32,
            "adapter_width": 16,
            "preview_long_side": 1024,
            "preview_exposure": 1.0,
            "max_cuda_allocation_GiB": 9,
            "min_available_RAM_GiB": 36,
            "learning_rate": 0.00025,
            "ema_decay": 0.99,
            "weak_band_weight": 0.0002,
            "regional_dc_weight": 0.0002,
            "device": "cuda",
            "parent_precision": "bfloat16",
            "scope": "Matched trainable spectral readouts and scene adapters, pooled versus aligned spatial. "
            "A shared untouched V120 parent and frozen scene encoding serve both arms. Fixed 800 independent scene draws, "
            "four native crops from each, same observation and supervision. Scope is an experimental component pilot.",
        },
    )


class WeakBands:
    """Signed RGB band errors in locally low-contrast clean-target blocks."""

    def __init__(self, device):
        axis = torch.arange(32, device=device, dtype=torch.float32)
        self.basis = torch.cos(math.pi / 32 * axis[:, None] * (axis[None, :] + 0.5)) * 0.25
        self.basis[0] *= math.sqrt(0.5)
        radial = torch.hypot(axis[:, None], axis[None, :]) / 64
        self.masks = ((1 / 32 <= radial) & (radial < 1 / 8), (1 / 8 <= radial) & (radial < 1 / 3))

    def spectrum(self, values):
        blocks = values.unfold(-2, 32, 32).unfold(-2, 32, 32)
        return self.basis @ blocks @ self.basis.T

    def targets(self, target):
        valid = F.avg_pool2d(((target >= 0) & (target < 0.98)).float(), 32) == 1
        mean = F.avg_pool2d(target, 32)
        coeff = self.spectrum(target)
        masks = []
        for band in self.masks:
            rms = coeff[..., band].square().sum(-1).sqrt() / 32
            # Keep flat blocks as zero-coefficient targets. The floor bounds
            # pressure on channels whose physical target is almost featureless.
            selected = valid & (mean >= 16 / 65535) & (rms <= 0.03 * mean)
            masks.append((selected, rms.clamp_min(16 / 65535)))
        return coeff, masks

    def loss(self, value, prepared):
        target, masks = prepared
        error = self.spectrum(value.float()) - target
        terms = []
        for band, (selected, scale) in zip(self.masks, masks, strict=True):
            mse = error[..., band].square().sum(-1) / (1024 * scale.square())
            terms.append(
                (((mse + 0.01).sqrt() - 0.1) * selected).sum() / selected.sum().clamp_min(1)
            )
        return torch.stack(terms).mean()


def batch_for(base, sample, plan):
    batch = {k: v.cuda() for k, v in sample.crops.items()}
    observation = sample.observation
    base.set_noise(observation.recipe.shot, observation.recipe.read)
    with torch.no_grad(), amp_context("cuda", dtype=plan["parent_precision"]):
        parent = base(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
        context = encode_scene(
            base.context,
            observation.packed,
            observation.colors,
            observation.wb,
            observation.matrix,
            long_side=plan["preview_long_side"],
            exposure=plan["preview_exposure"],
        )
    return batch, parent, context


def save_checkpoint(path, model, ema, opt, plan, mode, updates):
    temporary = path.with_suffix(".incomplete")
    assert not temporary.exists() and not path.exists()
    torch.save(
        {
            "mode": mode,
            "step": updates,
            "plan": reference(Path(plan["root"]) / "plan.json"),
            "parent": plan["parent"],
            "DINO_sha256": plan["DINO_sha256"],
            "model": {k: v.cpu() for k, v in model.state_dict().items()},
            "ema": {k: v.cpu() for k, v in ema.items()},
            "optimizer": opt.state_dict(),
            "torch_cpu_rng": torch.get_rng_state(),
            "torch_cuda_rng": torch.cuda.get_rng_state_all(),
            "data_draw_index": updates,
            "max_window": plan["max_window"],
            "adapter_width": plan["adapter_width"],
        },
        temporary,
    )
    temporary.rename(path)
    return reference(path)


def train(path, output, preflight):
    plan = read_json(path)
    verify_plan(plan)
    assert reference(__file__) == plan["driver"]
    torch.set_num_threads(2)
    torch.manual_seed(plan["model_seed"])
    torch.set_float32_matmul_precision("highest")
    torch.backends.cudnn.allow_tf32 = False
    reserve = plan["min_available_RAM_GiB"] * 2**30
    cuda_cap = plan["max_cuda_allocation_GiB"] * 2**30
    torch.cuda.set_per_process_memory_fraction(
        min(1.0, cuda_cap / torch.cuda.get_device_properties(0).total_memory)
    )
    assert psutil.virtual_memory().available >= reserve
    if not preflight:
        probe = read_json(Path(plan["root"]) / "preflight/completed.json")
        assert probe["plan"] == reference(path) and probe["discarded_preflight"]
    dataset = ScenePhotoDataset(
        checked(plan["train_manifest"]),
        seed=plan["data_seed"],
        patch_size=plan["patch_size"],
        crops_per_scene=plan["crops_per_scene"],
    )
    output.mkdir()
    write_json(output / "owner.json", owner_identity())
    base, payload = load_model("v120", checkpoint=checked(plan["parent"]), device="cuda")
    assert payload["loaded_sha256"] == plan["parent"]["sha256"]
    del payload
    base.eval().requires_grad_(False).to(memory_format=torch.channels_last)
    base_digest = model_hash(base)
    assert model_hash(base.context.backbone) == plan["DINO_sha256"]
    channels = base.context.backbone.config.hidden_sizes
    heads = {
        mode: SceneSpectralDetail(
            channels, max_window=plan["max_window"], adapter_width=plan["adapter_width"]
        ).cuda()
        for mode in MODES
    }
    heads["spatial"].load_state_dict(heads["pooled"].state_dict())
    initial_digest = model_hash(heads["pooled"])
    assert model_hash(heads["spatial"]) == initial_digest
    opts = {
        mode: torch.optim.AdamW(head.parameters(), lr=plan["learning_rate"], weight_decay=1e-4)
        for mode, head in heads.items()
    }
    ema = {
        mode: {k: v.detach().clone() for k, v in model.state_dict().items()}
        for mode, model in heads.items()
    }
    bands = WeakBands("cuda")
    steps = 3 if preflight else plan["steps"]
    offset = 2**30 if preflight else 0
    began = time.monotonic()
    cases = set()
    with (
        (output / "train.jsonl").open("x") as log,
        (output / "observations.jsonl").open("x") as observations,
    ):
        for i in range(steps):
            if psutil.virtual_memory().available < reserve:
                raise RuntimeError("Shared host memory below declared training reserve")
            sample = dataset[i + offset]
            cases.add(sample.metadata["source_id"])
            batch, parent, encoded = batch_for(base, sample, plan)
            target = batch["sensor_target"].float()
            prepared = bands.targets(target)
            scale = (
                batch["variance"].mean((1, 2, 3), keepdim=True).clamp_min((16 / 65535) ** 2).sqrt()
            )
            terms = {}
            first_predictions = []
            for mode, head in heads.items():
                opt = opts[mode]
                progress = max(0, i - 20) / max(1, steps - 20)
                opt.param_groups[0]["lr"] = (
                    plan["learning_rate"]
                    * min((i + 1) / 20, 1)
                    * (0.5 + 0.5 * math.cos(math.pi * progress))
                )
                opt.zero_grad(set_to_none=True)
                with ieee_fp32():
                    prediction = head(
                        parent,
                        *(batch[k] for k in ("packed", "variance", "colors", "wb")),
                        scene=encoded,
                        boxes_xywh=sample.metadata["boxes_xywh"],
                        mode=mode,
                    )
                    if i == 0:
                        assert torch.equal(prediction, parent)
                        first_predictions.append(model_hash(head))
                    baseline, _ = reconstruction_loss(
                        prediction,
                        batch,
                        auxiliary=mosaic(prediction, batch["colors"]),
                        camera_supervision="sensor-valid-v1",
                        reconstruction_charbonnier_epsilon=0.0003,
                    )
                    weak = bands.loss(prediction, prepared)
                    valid = ((target >= 0) & (target < 0.98)).all(1, keepdim=True)
                    safe_value = torch.where(valid, prediction, parent)
                    dc = regional_dc_excess(safe_value, parent, target, scale)
                    loss = (
                        baseline + plan["weak_band_weight"] * weak + plan["regional_dc_weight"] * dc
                    )
                    loss.backward()
                gradient = torch.nn.utils.clip_grad_norm_(head.parameters(), 1)
                if not torch.isfinite(loss) or not torch.isfinite(gradient):
                    raise FloatingPointError(f"Nonfinite {mode} loss or gradient at update {i + 1}")
                gate_grad = float(head.scene_adapter.output.weight.grad.abs().sum())
                if preflight and i == 2:
                    assert gate_grad > 0
                opt.step()
                with torch.no_grad():
                    for name, value in head.state_dict().items():
                        ema[mode][name].lerp_(value, 1 - plan["ema_decay"])
                terms[mode] = {
                    "loss": float(loss.detach()),
                    "reconstruction": float(baseline.detach()),
                    "weak_band": float(weak.detach()),
                    "dc": float(dc.detach()),
                    "grad_norm": float(gradient),
                    "scene_gate_gradient_L1": gate_grad,
                }
            if first_predictions:
                assert first_predictions == [initial_digest] * 2
            observations.write(json.dumps(sample.metadata, sort_keys=True) + "\n")
            event = {
                "step": i + 1,
                "seconds": time.monotonic() - began,
                "terms": terms,
                "distinct_source_ids": len(cases),
                "cuda_peak_GiB": torch.cuda.max_memory_allocated() / 2**30,
            }
            log.write(json.dumps(event) + "\n")
            if (i + 1) % 10 == 0 or preflight:
                observations.flush()
                log.flush()
                print(event, flush=True)
                write_json(output / "progress.json", event, replace=True)
    seconds = time.monotonic() - began
    assert model_hash(base) == base_digest
    endpoints = {
        mode: save_checkpoint(
            output / f"{mode}-step{steps:06d}.pt", head, ema[mode], opts[mode], plan, mode, steps
        )
        for mode, head in heads.items()
    }
    if preflight:
        for mode in MODES:
            recovered = torch.load(checked(endpoints[mode]), map_location="cpu", weights_only=True)
            heads[mode].load_state_dict(recovered["model"], strict=True)
            opts[mode].load_state_dict(recovered["optimizer"])
            assert len(recovered["ema"]) == len(heads[mode].state_dict())
            assert recovered["step"] == steps
    write_json(
        output / "completed.json",
        {
            "plan": reference(path),
            "driver": reference(__file__),
            "parent": plan["parent"],
            "discarded_preflight": preflight,
            "steps_per_mode": steps,
            "examples_per_mode": steps * plan["crops_per_scene"],
            "endpoints_raw_and_ema": endpoints,
            "start_head": initial_digest,
            "parent_untouched": True,
            "observations": reference(output / "observations.jsonl"),
            "training_log": reference(output / "train.jsonl"),
            "seconds_for_both_modes": seconds,
            "distinct_source_ids": len(cases),
            "cuda_peak_GiB": torch.cuda.max_memory_allocated() / 2**30,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--prepare-from", type=Path)
    action.add_argument("--preflight", action="store_true")
    action.add_argument("--train", action="store_true")
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve())
    else:
        os.sched_setaffinity(0, (6, 7))
        os.nice(11)
        train(
            args.path.resolve(),
            args.path.parent.resolve() / ("preflight" if args.preflight else "training"),
            args.preflight,
        )
