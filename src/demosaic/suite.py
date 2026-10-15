"""Paired, source-traceable evaluation across CFA, noise and exposure conditions."""

import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import torch
import yaml

from .cfa import PATTERNS, bilinear, color_indices, mosaic
from .data import CleanDataset, camera_pair, synthetic
from .inference import load_checkpoint
from .metrics import quality_metrics
from .noise import add_noise, variance_map
from .reference import load_rawnind
from .safety import writable_path
from .train import amp_context


def freeze_checkpoint(source, destination):
    """Copy one opened inode, so an atomic training update cannot mix versions."""
    source, destination = Path(source), writable_path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    temporary = destination / "checkpoint.tmp"
    digest = hashlib.sha256()
    with source.open("rb") as reader, temporary.open("wb") as writer:
        while chunk := reader.read(1 << 20):
            digest.update(chunk)
            writer.write(chunk)
    frozen = destination / f"weights-{digest.hexdigest()}.pt"
    temporary.replace(frozen)
    return frozen, digest.hexdigest()


def observation(rgb, identities, condition, pattern, wb, matrix, seed):
    """Noise is keyed by source and case, independent of model/batch ordering."""
    batch = len(rgb)
    balance = rgb.new_tensor(wb)[None].expand(batch, -1)
    transform = rgb.new_tensor(matrix)[None].expand(batch, -1, -1)
    inverse = torch.linalg.inv(transform)
    clean, target = camera_pair(
        rgb * condition["exposure"], inverse, balance, reconstruct_highlights=True
    )
    colors = color_indices(pattern, device=rgb.device)[None].expand(batch, -1)
    sampled = mosaic(clean.clamp_min(0), colors)
    shot, read = float(condition["shot"]), float(condition["read"])
    samples = []
    for sample, identity in zip(sampled, identities):
        key = f"{seed}:{identity}:{condition['name']}:{pattern}"
        value = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") % (2**63)
        generator = torch.Generator(device=rgb.device).manual_seed(value)
        samples.append(add_noise(sample, shot, read, black_level=0.03, generator=generator))
    packed = torch.stack(samples)
    return {
        "packed": packed,
        "variance": variance_map(packed, shot, read),
        "colors": colors,
        "wb": balance,
        "matrix": transform,
        "target": target.clamp(0, 1),
    }


def _number(value):
    value = float(value)
    return value if math.isfinite(value) else None


def summarize(records):
    """Balanced group means and paired source-level bootstrap differences."""
    groups, by_image = {}, {}
    for row in records:
        key = (row["model"], row["kind"], row["condition"], row["pattern"])
        groups.setdefault(key, []).append(row)
        key = (row["model"], row["kind"], row["id"])
        by_image.setdefault(key, []).append(row)

    def means(rows):
        names = rows[0]["metrics"]
        output = {}
        for name in names:
            values = [r["metrics"][name] for r in rows if r["metrics"][name] is not None]
            output[name] = {
                "mean": float(np.mean(values)) if values else None,
                "count": len(values),
            }
        return output

    grouped = [
        {"model": k[0], "kind": k[1], "condition": k[2], "pattern": k[3], "metrics": means(rows)}
        for k, rows in sorted(groups.items())
    ]
    image_means = {key: means(rows) for key, rows in by_image.items()}
    overall = []
    for model, kind in sorted({k[:2] for k in image_means}):
        rows = [
            {"metrics": {name: value["mean"] for name, value in metrics.items()}}
            for (m, k, _), metrics in image_means.items()
            if m == model and k == kind
        ]
        overall.append({"model": model, "kind": kind, "metrics": means(rows)})
    comparisons = []
    for first, second in (
        (a, b)
        for a in sorted({k[0] for k in image_means})
        for b in sorted({k[0] for k in image_means})
        if a < b
    ):
        for kind in sorted({k[1] for k in image_means}):
            ids = sorted(
                {k[2] for k in image_means if k[:2] == (first, kind)}
                & {k[2] for k in image_means if k[:2] == (second, kind)}
            )
            for metric in ("linear_psnr", "srgb_psnr", "srgb_ssim"):
                delta = np.array(
                    [
                        image_means[first, kind, identity][metric]["mean"]
                        - image_means[second, kind, identity][metric]["mean"]
                        for identity in ids
                    ]
                )
                rng = np.random.default_rng(42)
                boot = delta[rng.integers(len(delta), size=(1000, len(delta)))].mean(1)
                comparisons.append(
                    {
                        "first": first,
                        "second": second,
                        "kind": kind,
                        "metric": metric,
                        "sources": len(delta),
                        "mean_first_minus_second": float(delta.mean()),
                        "source_bootstrap_95_interval": np.quantile(boot, [0.025, 0.975]).tolist(),
                    }
                )
    return {"groups": grouped, "overall": overall, "paired_comparisons": comparisons}


@torch.inference_mode()
def run_suite(
    checkpoints,
    manifest,
    output,
    config,
    *,
    split="val",
    patch_size=256,
    batch_size=4,
    limit=0,
    synthetic_count=8,
    rawnind=None,
    device="cuda",
):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    protocol = yaml.safe_load(Path(config).read_text())
    patterns = protocol["patterns"]
    if any(p not in PATTERNS for p in patterns) or len(set(patterns)) != len(patterns):
        raise ValueError("Unknown or duplicate Bayer patterns")
    conditions = protocol["conditions"]
    if len({c["name"] for c in conditions}) != len(conditions):
        raise ValueError("Condition names must be unique")
    if any(min(c["shot"], c["read"]) < 0 or c["exposure"] <= 0 for c in conditions):
        raise ValueError("Invalid noise/exposure condition")
    if batch_size < 1 or limit < 0 or synthetic_count < 0:
        raise ValueError("Invalid evaluation counts")
    border = protocol.get("border", 8)
    if border < 0 or patch_size - 2 * border < 11:
        raise ValueError("Border leaves too few pixels for SSIM")
    payload = Path(manifest).read_bytes()
    data = CleanDataset(
        manifest,
        split=split,
        patch_size=patch_size,
        native_crop=True,
        records=[json.loads(line) for line in payload.splitlines()],
    )
    count = min(limit, len(data)) if limit else len(data)
    models, model_records = [], []
    for index, source in enumerate(checkpoints):
        frozen, digest = freeze_checkpoint(source, output / "weights")
        model, state = load_checkpoint(frozen, device)
        model.eval()
        label = f"{index}:{Path(source).parent.name}:step-{state['step']}"
        models.append((label, model, True))
        model_records.append(
            {
                "label": label,
                "source": str(source),
                "snapshot": str(frozen),
                "sha256": digest,
                "step": state["step"],
                "model_config": state["model_config"],
                "training_manifest_sha256": state["config"].get("manifest_sha256"),
            }
        )
    if rawnind:
        reference = load_rawnind(rawnind, gain_mode="cfa-ls", device=device)
        models.append(("RawNIND:CFA-LS", reference, False))
        model_records.append(
            {
                "label": "RawNIND:CFA-LS",
                "directory": str(rawnind),
                "weight_sha256": hashlib.sha256(
                    (Path(rawnind) / "utnet2-bayer.pt").read_bytes()
                ).hexdigest(),
                "gain": "observed-CFA-least-squares",
                "precision": "float32",
            }
        )
    metadata = {
        "format_version": 1,
        "protocol": protocol,
        "models": model_records,
        "manifest": str(manifest),
        "manifest_sha256": hashlib.sha256(payload).hexdigest(),
        "split": split,
        "sources": count,
        "synthetic_sources": synthetic_count,
        "patch_size": patch_size,
        "native_crop": True,
        "batch_size": batch_size,
        "adc_bits": 16,
        "adc_black": 0.03,
        "torch": str(torch.__version__),
        "noise_pairing": "per-source/condition/CFA seed; independent of model and batch size",
    }
    (output / "protocol.json").write_text(json.dumps(metadata, indent=2) + "\n")
    records = []
    entries = [("photo", data.rows[i]["id"], i) for i in range(count)] + [
        ("synthetic", f"synthetic-{i}", i) for i in range(synthetic_count)
    ]
    with (output / "per-image.jsonl").open("w") as stream:
        for start in range(0, len(entries), batch_size):
            current = entries[start : start + batch_size]
            rgb = torch.stack(
                [
                    data[i]["rgb"]
                    if kind == "photo"
                    else synthetic(patch_size, random.Random(1_000_000 + i))
                    for kind, _, i in current
                ]
            ).to(device)
            ids = [identity for _, identity, _ in current]
            for condition in conditions:
                for pattern in patterns:
                    batch = observation(
                        rgb,
                        ids,
                        condition,
                        pattern,
                        protocol["white_balance"],
                        protocol["camera_to_srgb"],
                        protocol.get("seed", 42),
                    )
                    predictions = [("Bilinear", bilinear(batch["packed"], batch["colors"]))]
                    for label, model, amp in models:
                        with amp_context(device, amp):
                            prediction = model(
                                batch["packed"],
                                batch["variance"],
                                batch["colors"],
                                batch["wb"],
                                batch["matrix"],
                            )
                        predictions.append((label, prediction))
                    trim = (
                        (slice(None), slice(None), slice(border, -border), slice(border, -border))
                        if border
                        else (...,)
                    )
                    for label, prediction in predictions:
                        metrics = quality_metrics(
                            prediction[trim], batch["target"][trim], batch["wb"], batch["matrix"]
                        )
                        values = {k: v.cpu().tolist() for k, v in metrics.items()}
                        for i, (kind, identity, _) in enumerate(current):
                            record = {
                                "id": identity,
                                "kind": kind,
                                "condition": condition["name"],
                                "pattern": pattern,
                                "model": label,
                                "metrics": {
                                    key: _number(value[i]) for key, value in values.items()
                                },
                            }
                            stream.write(json.dumps(record, allow_nan=False) + "\n")
                            records.append(record)
            stream.flush()
            print(
                json.dumps(
                    {
                        "event": "quality",
                        "sources_done": min(start + batch_size, len(entries)),
                        "total_sources": len(entries),
                        "rows": len(records),
                    }
                ),
                flush=True,
            )
    result = {**metadata, **summarize(records)}
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    return result
