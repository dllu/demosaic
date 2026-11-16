"""One cached-head training loop for checked observations and composed models."""

import math
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch

from .artifacts import checked, read_json, reference, verify_plan, write_json
from .checkpoints import (
    fresh_state,
    frozen_hash,
    load_torch,
    restore_checkpoint,
    save_checkpoint,
    trainable_parameters,
    update_ema,
)
from .data.cache import CachedBatches
from .objectives.directional import objective
from .runtime import RuntimePolicy, exclusive_run


@dataclass(frozen=True)
class TrainingConfig:
    steps: int = 1000
    warmup: int = 50
    lr: float = 0.001
    weight_decay: float = 0.01
    gradient_clip: float = 1.0
    response: str = "whole"

    def __post_init__(self):
        if type(self.steps) is not int or self.steps < 1:
            raise ValueError("steps must be a positive integer")
        if type(self.warmup) is not int or not 0 < self.warmup < self.steps:
            raise ValueError("warmup must lie between zero and steps")
        if self.response not in ("whole", "directional"):
            raise ValueError("Unknown response loss")
        for value in (self.lr, self.weight_decay, self.gradient_clip):
            if not math.isfinite(value) or value < 0:
                raise ValueError("Optimizer settings must be finite and nonnegative")
        if self.lr == 0 or self.gradient_clip == 0:
            raise ValueError("Learning rate and gradient clip must be positive")

    def learning_rate(self, step):
        phase = max(0, step - self.warmup) / (self.steps - self.warmup)
        return (
            self.lr * min(1, step / self.warmup) * (0.1 + 0.9 * (1 + math.cos(math.pi * phase)) / 2)
        )

    def to_dict(self):
        return asdict(self)


def initialize_model(spec):
    from demosaic.models.compat import build_component
    from demosaic.models.wave import legacy_state_dict, load_legacy_state_dict

    model = build_component(spec["kind"], spec.get("config"))
    payload = load_torch(spec["initializer"])
    state = payload["state_dict"]
    if spec.get("initialization", "component") == "anchor":
        current = legacy_state_dict(model)
        expected = {n for n in current if not n.startswith("cfa_readout.")}
        if set(state) != expected:
            raise ValueError("Anchor initializer must contain exactly the frozen pooled component")
        state = dict(current, **state)
    load_legacy_state_dict(model, state)
    values = trainable_parameters(model)
    if any(not name.startswith("readout.") for name in values):
        raise ValueError("Cached-head training may update only the final readout")
    return model


def train(root, *, resume=False, stop_after=None, model_factory=initialize_model):
    """Commit each completed row with state, EMA, Adam and RNG in one artifact.

    Recovery adopts the highest complete checkpoint and starts at the next row.
    No parent inference, target construction or noise resampling occurs here.
    """
    root = Path(root)
    plan_path = root / "plan.json"
    plan = read_json(plan_path)
    verify_plan(plan)
    spec = plan["recipe"]
    config = TrainingConfig(**spec["training"])
    runtime = RuntimePolicy(**spec["runtime"])
    cache = CachedBatches(spec["cache"], spec["pair_units"])
    if config.steps != len(cache):
        raise ValueError("LR horizon must equal the complete cached schedule")
    if stop_after is not None and (type(stop_after) is not int or stop_after < 1):
        raise ValueError("stop_after must be a positive number of additional rows")
    with exclusive_run(root):
        if (root / "result.json").exists():
            raise ValueError("Experiment already completed")
        checkpoint_dir = root / "checkpoints"
        checkpoint_dir.mkdir(exist_ok=True)
        existing = sorted(checkpoint_dir.glob("row-*.pt"))
        if bool(existing) != bool(resume):
            raise ValueError("Use resume only when completed row checkpoints exist")
        runtime.resources(root)
        runtime.apply()
        if spec.get("sampling_library"):
            torch.ops.load_library(str(checked(spec["sampling_library"])))
        model = model_factory(spec["model"]).to(runtime.device).train()
        anchor_hash = frozen_hash(model)
        identity = reference(plan_path)
        updates = skipped = start = 0
        if resume:
            optimizer, ema, payload = restore_checkpoint(
                existing[-1], model, plan=identity, lr=config.lr, weight_decay=config.weight_decay
            )
            start, updates, skipped = payload["row"]["step"], payload["updates"], payload["skipped"]
            expected_prefix = [
                checkpoint_dir / f"row-{step:06d}.pt" for step in range(1, start + 1)
            ]
            if existing != expected_prefix:
                raise ValueError("Resume prefix has missing or unexpected row checkpoints")
        else:
            optimizer, ema = fresh_state(model, lr=config.lr, weight_decay=config.weight_decay)
        end = min(config.steps, start + stop_after) if stop_after else config.steps
        for index in range(start, end):
            runtime.resources(root)
            item, arrays, parent, units = cache.load(index)
            step = index + 1
            rate = config.learning_rate(step)
            row = {
                "step": step,
                "domain": item["metadata"]["domain"],
                "batch": item["arrays"],
                "parent": item["parent"],
                "lr": rate,
                "noisy": bool(np.any(arrays["variance"] > 0)),
            }
            if row["noisy"]:
                batch = {k: torch.from_numpy(v).to(runtime.device) for k, v in arrays.items()}
                base = torch.from_numpy(parent).to(runtime.device)
                pair_units = torch.from_numpy(units).to(runtime.device)
                optimizer.zero_grad(set_to_none=True)
                for group in optimizer.param_groups:
                    group["lr"] = rate
                output, aux = model(
                    base,
                    *(batch[k] for k in ("packed", "variance", "colors", "wb")),
                    return_aux=True,
                )
                frozen = aux.get("anchor_aux", aux)["frozen_output"]
                loss, terms, mask = objective(
                    output,
                    frozen,
                    batch,
                    pair_units,
                    spec["domain_weights"][row["domain"]],
                    mode=config.response,
                )
                if not torch.isfinite(loss):
                    raise ValueError(f"Nonfinite loss at row {step}")
                loss.backward()
                values = trainable_parameters(model)
                for name, parameter in values.items():
                    if parameter.grad is None or not torch.isfinite(parameter.grad).all():
                        raise ValueError(f"Missing/nonfinite gradient: {name}")
                if any(p.grad is not None for p in model.parameters() if not p.requires_grad):
                    raise ValueError("Frozen parameter received a gradient")
                norm = torch.nn.utils.clip_grad_norm_(
                    values.values(), config.gradient_clip, error_if_nonfinite=True
                )
                optimizer.step()
                updates += 1
                decay = update_ema(model, ema, updates)
                row.update(
                    loss=float(loss.detach()),
                    terms={n: float(v.detach()) for n, v in terms.items()},
                    gradient_norm=float(norm),
                    EMA_decay=decay,
                    flat_eligible_pixels=int(mask.sum()),
                )
            else:
                skipped += 1
                row["skipped"] = "zero variance; no forward or optimizer call"
            row.update(updates=updates, ADC_skips=skipped)
            checkpoint = checkpoint_dir / f"row-{step:06d}.pt"
            save_checkpoint(
                checkpoint,
                model,
                optimizer,
                ema,
                plan=identity,
                row=row,
                updates=updates,
                skipped=skipped,
                anchor_hash=anchor_hash,
            )
            write_json(
                root / "progress.json", dict(row, checkpoint=reference(checkpoint)), replace=True
            )
        verify_plan(plan)
        result = {
            "status": "completed" if end == config.steps else "stopped-at-checkpoint",
            "plan": identity,
            "rows": end,
            "updates": updates,
            "ADC_skips": skipped,
            "checkpoint": reference(checkpoint_dir / f"row-{end:06d}.pt"),
            "frozen_hash": frozen_hash(model),
            "new_parent_forwards": 0,
            "new_source_or_noise_draws": 0,
        }
        if end == config.steps:
            write_json(root / "result.json", result)
        return result
