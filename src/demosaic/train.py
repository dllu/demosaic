"""Resumable bounded-memory training with EMA and deterministic held-out crops."""

import hashlib
import json
import math
import random
import shutil
import time
from contextlib import nullcontext
from pathlib import Path

import psutil
import torch
import yaml
from torch.utils.data import DataLoader

from .cfa import bilinear
from .color import render
from .data import CleanDataset, degrade
from .losses import psnr, reconstruction_loss
from .model import JointDemosaic, ModelConfig
from .safety import writable_path


def amp_context(device, enabled=True):
    return (
        torch.autocast("cuda", dtype=torch.bfloat16)
        if (enabled and torch.device(device).type == "cuda")
        else nullcontext()
    )


@torch.inference_mode()
def evaluate(model, loader, device, *, max_batches=16, amp=True):
    model.eval()
    generator = torch.Generator(device=device).manual_seed(20261014)
    scores = {
        "linear_psnr": [],
        "srgb_psnr": [],
        "bilinear_linear_psnr": [],
        "bilinear_srgb_psnr": [],
    }
    for i, clean in enumerate(loader):
        if max_batches and i >= max_batches:
            break
        batch = degrade(clean["rgb"].to(device), training=False, generator=generator)
        with amp_context(device, amp):
            output = model(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
        baseline = bilinear(batch["packed"], batch["colors"])
        target = batch["target"]
        for prefix, rgb in (("", output), ("bilinear_", baseline)):
            scores[prefix + "linear_psnr"].extend(psnr(rgb.clamp(0, 1), target).tolist())
            scores[prefix + "srgb_psnr"].extend(
                psnr(
                    render(rgb, batch["wb"], batch["matrix"]),
                    render(target, batch["wb"], batch["matrix"]),
                ).tolist()
            )
    return {key: sum(values) / len(values) for key, values in scores.items()}


def update_ema(model, ema, decay):
    with torch.no_grad():
        for name, value in model.restoration_state_dict().items():
            if value.is_floating_point():
                ema[name].lerp_(value.detach(), 1 - decay)
            else:
                ema[name].copy_(value)


def save_checkpoint(path, model, optimizer, ema, step, config, best):
    state = {
        "format_version": 1,
        "model": model.restoration_state_dict(),
        "ema": ema,
        "model_config": model.config.to_dict(),
        "optimizer": optimizer.state_dict(),
        "step": step,
        "config": config,
        "best": best,
        "torch_rng": torch.get_rng_state(),
        "python_rng": random.getstate(),
        "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
        "torch_version": str(torch.__version__),
    }
    path = writable_path(path)
    temporary = path.with_suffix(".tmp")
    torch.save(state, temporary)
    temporary.replace(path)


def train(config_path, *, resume=None, initialize=None, stop_after=None):
    if resume and initialize:
        raise ValueError("Choose resume or initialize, not both")
    config = yaml.safe_load(Path(config_path).read_text())
    manifest_hash = hashlib.sha256(Path(config["manifest"]).read_bytes()).hexdigest()
    config["manifest_sha256"] = manifest_hash
    run = writable_path(config["run"])
    run.mkdir(parents=True, exist_ok=True)
    # Capture the actual code, including uncommitted research changes, so a
    # later edit cannot obscure what produced this run's weights.
    snapshot = run / "source"
    snapshot.mkdir(exist_ok=True)
    code_hash = hashlib.sha256()
    for source in sorted(Path(__file__).parent.glob("*.py")):
        payload = source.read_bytes()
        code_hash.update(source.name.encode() + payload)
        if not resume:
            (snapshot / source.name).write_bytes(payload)
    config["source_sha256"] = code_hash.hexdigest()
    repository = Path(__file__).resolve().parents[2]
    if not resume:
        for name in ("pyproject.toml", "uv.lock"):
            shutil.copyfile(repository / name, snapshot / name)
    device = torch.device(config.get("device", "cuda"))
    torch.set_num_threads(config.get("cpu_threads", 4))
    torch.set_float32_matmul_precision("high")
    torch.backends.cudnn.benchmark = True
    seed = config.get("seed", 42)
    random.seed(seed)
    torch.manual_seed(seed)
    model = JointDemosaic(ModelConfig(**config.get("model", {}))).to(device)
    if config.get("reconstruct_highlights", False) and not model.config.camera_conditioning:
        raise ValueError("Highlight training requires white-balance/color-matrix conditioning")
    if initialize:
        initial = torch.load(initialize, map_location="cpu", weights_only=True)
        weights = initial.get("ema", initial["model"])
        if model.config.camera_conditioning and weights["stem.weight"].shape[1] == 20:
            # Preserve the prior mapping while adding 12 zero-weight metadata maps.
            expanded = torch.zeros_like(model.stem.weight, device="cpu")
            expanded[:, :20] = weights["stem.weight"]
            weights["stem.weight"] = expanded
        incompatible = model.load_state_dict(weights, strict=False)
        if incompatible.unexpected_keys or any(
            not k.startswith("context.") for k in incompatible.missing_keys
        ):
            raise ValueError(f"Incompatible initialization: {incompatible}")
        config["initialized_from"] = {
            "path": str(Path(initialize).resolve()),
            "sha256": hashlib.sha256(Path(initialize).read_bytes()).hexdigest(),
            "step": initial.get("step"),
        }
        del initial
    # Keep just one frozen DINO backbone: EMA contains restoration weights only.
    ema = {key: value.detach().clone() for key, value in model.restoration_state_dict().items()}
    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=config.get("lr", 2e-4),
        weight_decay=0.01,
    )
    first, best = 0, -math.inf
    if resume:
        state = torch.load(resume, map_location="cpu", weights_only=True)
        previous_manifest_hash = state["config"].get("manifest_sha256")
        if previous_manifest_hash and previous_manifest_hash != manifest_hash:
            raise ValueError("Resume manifest differs from the checkpoint's training data")
        if ModelConfig(**state["model_config"]).to_dict() != model.config.to_dict():
            raise ValueError("Resume model configuration differs from checkpoint")
        incompatible = model.load_state_dict(state["model"], strict=False)
        if incompatible.unexpected_keys or any(
            not k.startswith("context.backbone.") for k in incompatible.missing_keys
        ):
            raise ValueError(f"Incompatible restoration checkpoint: {incompatible}")
        optimizer.load_state_dict(state["optimizer"])
        ema = {k: v.to(device) for k, v in state["ema"].items()}
        first, best = state["step"], state["best"]
        torch.set_rng_state(state["torch_rng"])
        random.setstate(state["python_rng"])
        if state["cuda_rng"] and device.type == "cuda":
            torch.cuda.set_rng_state_all(state["cuda_rng"])
    (run / "config.yaml").write_text(yaml.safe_dump(config, sort_keys=False))
    steps, batch_size = config["steps"], config.get("batch_size", 4)
    data = CleanDataset(
        config["manifest"],
        patch_size=config.get("patch_size", 256),
        seed=seed,
        synthetic_fraction=config.get("synthetic_fraction", 0.2),
    )
    workers = config.get("workers", 2)
    loader = DataLoader(
        data,
        batch_size=batch_size,
        sampler=range(first * batch_size, steps * batch_size),
        num_workers=workers,
        # Pinning duplicates memory on UMA; enable only if profiling justifies it.
        pin_memory=False,
        persistent_workers=workers > 0,
        generator=torch.Generator().manual_seed(seed),
        **({"prefetch_factor": 2} if workers else {}),
    )
    validation = DataLoader(
        CleanDataset(config["manifest"], split="val", patch_size=config.get("patch_size", 256)),
        batch_size=batch_size,
        num_workers=0,
        generator=torch.Generator().manual_seed(seed),
    )
    total_parameters = sum(p.numel() for p in model.parameters())
    print(
        json.dumps(
            {
                "event": "start",
                "parameters": total_parameters,
                "train_sources": len(data),
                "validation_sources": len(validation.dataset),
                "start_step": first,
                "steps": steps,
                "dino": model.config.dino,
            }
        ),
        flush=True,
    )
    started = time.perf_counter()
    checkpoint_interval = config.get("checkpoint_every", 500)
    amp = config.get("amp", True)
    for step, clean in enumerate(loader, start=first + 1):
        if step == first + 1 or step % 50 == 0:
            available_gb = psutil.virtual_memory().available / 1e9
            if available_gb < config.get("min_available_gb", 12):
                save_checkpoint(run / "last.pt", model, optimizer, ema, step - 1, config, best)
                raise RuntimeError(
                    f"Stopping safely: only {available_gb:.1f} GB system memory available"
                )
        warmup = min(1, step / config.get("warmup_steps", 200))
        progress = max(0, step - config.get("warmup_steps", 200)) / max(
            1, steps - config.get("warmup_steps", 200)
        )
        lr = config.get("lr", 2e-4) * warmup * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
        for group in optimizer.param_groups:
            group["lr"] = lr
        model.train()
        batch = degrade(
            clean["rgb"].to(device),
            reconstruct_highlights=config.get("reconstruct_highlights", False),
            preserve_negative_read_noise=config.get("preserve_negative_read_noise", False),
        )
        optimizer.zero_grad(set_to_none=True)
        with amp_context(device, amp):
            prediction, auxiliary = model(
                batch["packed"],
                batch["variance"],
                batch["colors"],
                batch["wb"],
                batch["matrix"],
                auxiliary=True,
            )
            loss, terms = reconstruction_loss(prediction, batch, auxiliary)
        if not torch.isfinite(loss):
            raise RuntimeError(f"Nonfinite loss at step {step}; last checkpoint retained")
        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1, error_if_nonfinite=True)
        optimizer.step()
        update_ema(model, ema, min(config.get("ema_decay", 0.999), (1 + step) / (10 + step)))
        if step == first + 1 or step % config.get("log_every", 25) == 0:
            metrics = {
                "event": "train",
                "step": step,
                "loss": loss.item(),
                "lr": lr,
                "grad_norm": float(grad_norm),
                "seconds_per_step": (time.perf_counter() - started) / (step - first),
                "cuda_gb": torch.cuda.max_memory_allocated() / 1e9 if device.type == "cuda" else 0,
                **{key: value.item() for key, value in terms.items()},
            }
            with (run / "metrics.jsonl").open("a") as log:
                log.write(json.dumps(metrics) + "\n")
            print(json.dumps(metrics), flush=True)
        if step % checkpoint_interval == 0 or step == steps:
            # Temporarily apply EMA in-place; do not duplicate the frozen model.
            current = {k: v.detach().clone() for k, v in model.restoration_state_dict().items()}
            model.load_state_dict(ema, strict=False)
            scores = evaluate(
                model, validation, device, max_batches=config.get("val_batches", 16), amp=amp
            )
            model.load_state_dict(current, strict=False)
            del current
            metrics = {"event": "validation", "step": step, **scores}
            with (run / "metrics.jsonl").open("a") as log:
                log.write(json.dumps(metrics) + "\n")
            print(json.dumps(metrics), flush=True)
            improved = scores["srgb_psnr"] > best
            best = max(best, scores["srgb_psnr"])
            save_checkpoint(run / "last.pt", model, optimizer, ema, step, config, best)
            if improved:
                save_checkpoint(run / "best.pt", model, optimizer, ema, step, config, best)
        if stop_after and step - first >= stop_after:
            save_checkpoint(run / "last.pt", model, optimizer, ema, step, config, best)
            break
    return run / "last.pt"
