"""Paired, source-traceable evaluation across CFA, noise and exposure conditions."""

import hashlib
import json
import math
import random
from pathlib import Path

import numpy as np
import torch
import yaml

from .cfa import PATTERNS, bilinear, color_indices, malvar, mosaic
from .checkpoint_cache import freeze_checkpoint
from .data import CleanDataset, camera_pair, synthetic
from .gaussian import load_gaussian_prior
from .inference import load_checkpoint
from .metrics import quality_metrics
from .noise import add_noise, variance_map
from .nonlocal_reference import load_nonlocal_reference
from .precision import COMPUTE_DTYPES, amp_context
from .prior import wiener_packed
from .reference import RawNind, load_rawnind
from .reporting import center_crop, display_crop, save_triplet, write_report
from .safety import writable_path


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
        # Camera channels may exceed one when a WB gain is below one. Preserve
        # the reference-white target through WB/matrix rendering; clipping here
        # would create a color cast even for a perfect reconstruction.
        "target": target,
    }


def _number(value):
    value = float(value)
    return value if math.isfinite(value) else None


@torch.inference_mode()
def evaluate_panel(
    model, dataset, config, device, *, images=16, batch_size=4, amp=True, precision="bfloat16"
):
    """Small balanced monitor for training; full-suite evaluation remains separate."""
    model.eval()
    protocol = yaml.safe_load(Path(config).read_text())
    count = min(images, len(dataset))
    if count < 1 or batch_size < 1:
        raise ValueError("Validation panel requires positive image/batch counts")
    groups = {}
    border = protocol.get("border", 8)
    for start in range(0, count, batch_size):
        indices = list(range(start, min(start + batch_size, count)))
        rgb = torch.stack([dataset[i]["rgb"] for i in indices]).to(device)
        ids = [dataset.rows[i]["id"] for i in indices]
        for condition in protocol["conditions"]:
            for pattern in protocol["patterns"]:
                batch = observation(
                    rgb,
                    ids,
                    condition,
                    pattern,
                    protocol["white_balance"],
                    protocol["camera_to_srgb"],
                    protocol.get("seed", 42),
                )
                if hasattr(model, "set_noise"):
                    model.set_noise(condition["shot"], condition["read"])
                with amp_context(device, amp or precision == "float32", dtype=precision):
                    prediction = model(
                        batch["packed"],
                        batch["variance"],
                        batch["colors"],
                        batch["wb"],
                        batch["matrix"],
                    )
                trim = (
                    (slice(None), slice(None), slice(border, -border), slice(border, -border))
                    if border
                    else (...,)
                )
                scores = quality_metrics(
                    prediction[trim], batch["target"][trim], batch["wb"], batch["matrix"]
                )
                group = groups.setdefault((condition["name"], pattern), {})
                for name, values in scores.items():
                    group.setdefault(name, []).extend(
                        v for v in values.cpu().tolist() if math.isfinite(v)
                    )
    cases = [
        {
            "condition": key[0],
            "pattern": key[1],
            "images": count,
            "metrics": {
                name: float(np.mean(values)) if values else None for name, values in scores.items()
            },
        }
        for key, scores in sorted(groups.items())
    ]
    return {
        "panel_images": count,
        "panel_srgb_psnr": float(np.mean([c["metrics"]["srgb_psnr"] for c in cases])),
        "panel_srgb_ssim": float(np.mean([c["metrics"]["srgb_ssim"] for c in cases])),
        "panel_cases": cases,
    }


def summarize(records, *, comparison_metrics=("linear_psnr", "srgb_psnr", "srgb_ssim")):
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
            if not ids:
                continue
            for metric in comparison_metrics:
                valid_ids = [
                    identity
                    for identity in ids
                    if image_means[first, kind, identity].get(metric, {}).get("mean") is not None
                    and image_means[second, kind, identity].get(metric, {}).get("mean") is not None
                ]
                if not valid_ids:
                    continue
                delta = np.array(
                    [
                        image_means[first, kind, identity][metric]["mean"]
                        - image_means[second, kind, identity][metric]["mean"]
                        for identity in valid_ids
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
    precision="bfloat16",
    refinement_precision="float32",
    gaussian_reference=None,
    nonlocal_reference=None,
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
    if precision not in COMPUTE_DTYPES:
        raise ValueError(f"Unknown compute precision {precision!r}")
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
        model, state = load_checkpoint(frozen, device, refinement_precision=refinement_precision)
        model.eval()
        if torch.device(device).type == "cuda":
            model.to(memory_format=torch.channels_last)
        run_name = Path(state.get("config", {}).get("run", Path(source).parent)).name
        label = f"{index}:{run_name}:step-{state['step']}"
        models.append((label, model, True))
        model_records.append(
            {
                "label": label,
                "source": str(source),
                "training_run": state.get("config", {}).get("run"),
                "snapshot": str(frozen),
                "sha256": digest,
                "step": state["step"],
                "model_config": state["model_config"],
                "effective_model_config": model.config.to_dict(),
                "training_manifest_sha256": state["config"].get("manifest_sha256"),
                "compute_precision": precision
                if torch.device(device).type == "cuda"
                else "float32",
                "refinement_compute_precision": refinement_precision
                if torch.device(device).type == "cuda"
                else "float32",
                "memory_format": "channels_last"
                if torch.device(device).type == "cuda"
                else "contiguous",
            }
        )
    if gaussian_reference:
        gaussian = load_gaussian_prior(gaussian_reference, device=device, archive=output)
        models.append((gaussian.receipt["label"], gaussian, False))
        model_records.append(gaussian.receipt)
    if nonlocal_reference:
        reference = load_nonlocal_reference(nonlocal_reference, device=device, archive=output)
        models.append((reference.receipt["label"], reference, False))
        model_records.append(reference.receipt)
    if rawnind:
        reference = load_rawnind(rawnind, gain_mode="cfa-ls", device=device)
        models.append(("RawNIND:CFA-LS", reference, False))
        model_records.append(
            {
                "label": "RawNIND:CFA-LS",
                "directory": str(rawnind),
                "model_config": getattr(reference, "reference_config", None),
                "weight_sha256": hashlib.sha256(
                    (Path(rawnind) / "utnet2-bayer.pt").read_bytes()
                ).hexdigest(),
                "gain": "observed-CFA-least-squares",
                "precision": "IEEE float32",
                "input": "Signed/unclipped synthetic sensor units; no camera/global-ADC scale difference",
            }
        )
        models.append(("RawNIND:CFA-channel", RawNind(reference.network, "cfa-channel"), False))
        model_records.append(
            {
                "label": "RawNIND:CFA-channel",
                "directory": str(rawnind),
                "model_config": getattr(reference, "reference_config", None),
                "weight_sha256": model_records[-1]["weight_sha256"],
                "gain": "per-channel-observed-CFA-least-squares",
                "precision": "IEEE float32",
                "input": "Signed/unclipped synthetic sensor units; no camera/global-ADC scale difference",
            }
        )
    source_payloads = {
        source.name: source.read_bytes() for source in sorted(Path(__file__).parent.glob("*.py"))
    }
    source_digest = hashlib.sha256()
    for name, contents in sorted(source_payloads.items()):
        source_digest.update(name.encode() + contents)
    snapshot = output / "source" / source_digest.hexdigest()
    snapshot.mkdir(parents=True, exist_ok=True)
    for name, contents in source_payloads.items():
        (snapshot / name).write_bytes(contents)
    (snapshot / "manifest.jsonl").write_bytes(payload)
    (snapshot / "protocol.yaml").write_bytes(Path(config).read_bytes())
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
        "reference_target": "Reference-white clipping in linear sRGB; retain camera values through WB/matrix. Camera PSNR clips both arrays to sensor range [0,1].",
        "classical_baselines": [
            "Bilinear:IEEE-FP32",
            "Malvar2004:white-balanced:IEEE-FP32",
            "Wiener7+Malvar2004:white-balanced:IEEE-FP32",
        ],
        "torch": str(torch.__version__),
        "inference_source_sha256": source_digest.hexdigest(),
        "inference_source_snapshot": str(snapshot),
        "observation_and_metrics_precision": "IEEE FP32",
        "noise_pairing": "per-source/condition/CFA seed; independent of model and batch size",
    }
    (output / "protocol.json").write_text(json.dumps(metadata, indent=2) + "\n")
    records, crops = [], []
    entries = [("photo", data.rows[i]["id"], i) for i in range(count)] + [
        ("synthetic", f"synthetic-{i}", i) for i in range(synthetic_count)
    ]
    crop_ids = {identity for _, identity, _ in entries[:2]}
    crop_condition = max(conditions, key=lambda c: c["shot"] + c["read"])["name"]
    crop_models = {row["label"]: row for row in model_records}
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
                    if torch.device(device).type == "cuda":
                        for name in ("packed", "variance"):
                            batch[name] = batch[name].contiguous(memory_format=torch.channels_last)
                    predictions = [
                        ("Bilinear", bilinear(batch["packed"], batch["colors"])),
                        ("Malvar2004:WB", malvar(batch["packed"], batch["colors"], batch["wb"])),
                        (
                            "Wiener7+Malvar2004:WB",
                            malvar(
                                wiener_packed(batch["packed"], batch["variance"]),
                                batch["colors"],
                                batch["wb"],
                            ),
                        ),
                    ]
                    for label, model, amp in models:
                        if hasattr(model, "set_noise"):
                            model.set_noise(condition["shot"], condition["read"])
                        with amp_context(device, dtype=precision if amp else "float32"):
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
                        if (
                            label in crop_models
                            and condition["name"] == crop_condition
                            and pattern == patterns[0]
                        ):
                            xywh = center_crop(prediction.shape, border=border)
                            for i, (kind, identity, source_index) in enumerate(current):
                                if identity not in crop_ids:
                                    continue
                                panels = [
                                    ("Noisy (Malvar)", predictions[1][1]),
                                    ("Denoised", prediction),
                                    ("GT (synthetic)", batch["target"]),
                                ]
                                images = [
                                    (
                                        name,
                                        display_crop(
                                            rgb[i : i + 1],
                                            batch["wb"][i : i + 1],
                                            batch["matrix"][i : i + 1],
                                            xywh,
                                        ),
                                    )
                                    for name, rgb in panels
                                ]
                                crops.append(
                                    save_triplet(
                                        output,
                                        f"{identity}:{label}",
                                        images,
                                        caption=f"{identity} / {condition['name']} / {pattern} / {label}",
                                        metadata={
                                            "source_id": identity,
                                            "source": data.rows[source_index]
                                            if kind == "photo"
                                            else {},
                                            "validation_index": source_index,
                                            "validation_seed": data.seed,
                                            "evaluation_tile_xywh": xywh,
                                            "condition": condition,
                                            "pattern": pattern,
                                            "model": crop_models[label],
                                            "display_exposure": 1.0,
                                            "reference": "Exact synthetic clean target",
                                        },
                                    )
                                )
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
    result = {**metadata, **summarize(records), "native_crops": crops}
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    write_report(
        output,
        result,
        crops,
        title="Synthetic quality evaluation",
        note="Synthetic noisy observations with exact clean targets; real RAW quality is assessed separately.",
        metrics=("srgb_psnr", "srgb_ssim", "linear_psnr"),
    )
    return result
