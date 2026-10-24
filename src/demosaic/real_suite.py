"""Paired real-RAW evaluation with measured-sensor and auxiliary RGB references."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import torch

from .cfa import bilinear, color_indices, malvar, pack
from .color import render
from .gaussian import load_gaussian_prior
from .inference import load_checkpoint
from .metrics import quality_metrics
from .nonlocal_reference import load_nonlocal_reference
from .precision import COMPUTE_DTYPES, amp_context
from .prior import wiener_packed
from .reference import RawNind, load_rawnind, publisher_input_scale
from .reporting import center_crop, display_crop, save_triplet, write_report
from .safety import writable_path
from .self_ensemble import predict_dihedral8
from .suite import freeze_checkpoint, summarize


def measured_sensor_psnr(prediction, reference, mask):
    count = mask.flatten(1).sum(1)
    mse = ((prediction.float().clamp(0, 1) - reference).square() * mask).flatten(1).sum(
        1
    ) / count.clamp_min(1)
    score = -10 * mse.clamp_min(1e-12).log10()
    return torch.where(count >= 1024, score, score.new_full((), float("nan"))), count


@torch.inference_mode()
def evaluate_pairs(
    checkpoints,
    prepared,
    output,
    *,
    rawnind=None,
    precision="float16",
    batch_size=4,
    gallery=False,
    device="cuda",
    noise_multiplier=1.0,
    prior_window=None,
    refinement_precision="float32",
    gaussian_reference=None,
    nonlocal_reference=None,
    self_ensemble="none",
    prediction_callback=None,
):
    if self_ensemble not in ("none", "dihedral8"):
        raise ValueError(f"Unknown self-ensemble policy {self_ensemble!r}")
    if (
        precision not in COMPUTE_DTYPES
        or batch_size < 1
        or not math.isfinite(noise_multiplier)
        or noise_multiplier <= 0
        or (prior_window is not None and (prior_window < 3 or prior_window % 2 == 0))
    ):
        raise ValueError("Invalid precision, batch size, variance multiplier or prior window")
    output = writable_path(output)
    if any((output / name).exists() for name in ("per-crop.jsonl", "summary.json")):
        raise ValueError("Evaluation output already contains results; choose a new directory")
    output.mkdir(parents=True, exist_ok=True)
    prepared = Path(prepared)
    payload = prepared.read_bytes()
    data = json.loads(payload)
    if not any(case["crops"] for case in data["cases"]):
        raise ValueError("Prepared data has no usable crops")
    archive = output / "source"
    archive.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    for path in sorted(Path(__file__).parent.glob("*.py")):
        content = path.read_bytes()
        digest.update(path.name.encode() + content)
        (archive / path.name).write_bytes(content)
    source_sha256 = digest.hexdigest()
    (archive / "prepared-manifest.json").write_bytes(payload)
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("high")
    models, receipts, ensemble_labels = [], [], set()
    for index, source in enumerate(checkpoints):
        frozen, digest = freeze_checkpoint(source, output / "weights")
        model, state = load_checkpoint(frozen, device, refinement_precision=refinement_precision)
        if prior_window is not None:
            if model.config.baseline != "wiener-malvar":
                raise ValueError("A prior-window override requires the Wiener-Malvar model")
            model.config.prior_window = prior_window
        model.eval()
        if torch.device(device).type == "cuda":
            model.to(memory_format=torch.channels_last)
        name = Path(state.get("config", {}).get("run", Path(source).parent)).name
        label = f"{index}:{name}:step-{state['step']}"
        if self_ensemble == "dihedral8":
            label += ":dihedral8"
            ensemble_labels.add(label)
        models.append((label, model, precision))
        receipts.append(
            {
                "label": label,
                "snapshot": str(frozen),
                "sha256": digest,
                "step": state["step"],
                "model_config": model.config.to_dict(),
                "checkpoint_model_config": state["model_config"],
                "self_ensemble": self_ensemble,
                "model_views_per_tile": 8 if self_ensemble == "dihedral8" else 1,
                "compute_precision": precision,
                "refinement_compute_precision": refinement_precision
                if torch.device(device).type == "cuda"
                else "float32",
            }
        )
        del state
    if gaussian_reference:
        gaussian = load_gaussian_prior(gaussian_reference, device=device, archive=output)
        models.append((gaussian.receipt["label"], gaussian, "float32"))
        receipts.append(gaussian.receipt)
    if nonlocal_reference:
        reference = load_nonlocal_reference(nonlocal_reference, device=device, archive=output)
        models.append((reference.receipt["label"], reference, "float32"))
        receipts.append(reference.receipt)
    reference = load_rawnind(rawnind, gain_mode="cfa-ls", device=device) if rawnind else None
    if reference:
        receipts.append(
            {
                "label": "RawNIND",
                "model_config": getattr(reference, "reference_config", None),
                "weight_sha256": hashlib.sha256(
                    (Path(rawnind) / "utnet2-bayer.pt").read_bytes()
                ).hexdigest(),
                "input": "Publisher global-ADC normalization; signed/unclipped",
                "gain": "Observed original-unit CFA, global and per-channel variants; no clean target",
                "precision": "IEEE float32",
            }
        )
    rows, pair_rows, pictures, baseline_scales, crops = [], [], [], [], []
    high_cases = {}
    for case in data["cases"]:
        previous = high_cases.get(case["scene"])
        if previous is None or (case["metadata"].get("iso") or 0) > (
            previous["metadata"].get("iso") or 0
        ):
            high_cases[case["scene"]] = case
    crop_scenes = set(sorted(high_cases)[:2])
    with (output / "per-crop.jsonl").open("w") as stream:
        for case in data["cases"]:
            meta = case["metadata"]
            colors = color_indices(meta["pattern"], device=device)
            shot, read = case["conditioning"]["shot"], case["conditioning"]["read"]
            current_models = list(models)
            if reference:
                adc = meta.get("adc_white_level")
                if adc is None:
                    import rawpy

                    # Older prepared receipts did not retain global ADC white.
                    with rawpy.imread(case["noisy"]["path"]) as decoder:
                        adc = float(decoder.white_level)
                scale = publisher_input_scale(meta["white_levels"], meta["black_levels"], adc)
                baseline_scales.append(
                    {
                        "noisy_sha256": case["noisy"]["sha256"],
                        "adc_white_level": adc,
                        "phase_input_scale": scale,
                    }
                )
                for mode in ("cfa-ls", "cfa-channel"):
                    adapter = RawNind(reference.network, mode, input_scale=scale).to(device).eval()
                    current_models.append((f"RawNIND:{mode}:publisher", adapter, "float32"))
            case_records = []
            for start in range(0, len(case["crops"]), batch_size):
                crop_records = case["crops"][start : start + batch_size]
                arrays = []
                for crop in crop_records:
                    path = prepared.parent / crop["path"]
                    with path.open("rb") as handle:
                        digest = hashlib.file_digest(handle, "sha256").hexdigest()
                    if digest != crop["sha256"]:
                        raise ValueError(f"Prepared crop checksum mismatch: {path}")
                    with np.load(path, allow_pickle=False) as values:
                        arrays.append(
                            {
                                k: values[k]
                                for k in ("raw", "reference_rgb", "sensor_reference", "sensor_mask")
                            }
                        )
                tensors = {
                    k: torch.from_numpy(np.stack([a[k] for a in arrays])).to(device)
                    for k in arrays[0]
                }
                packed = pack(tensors["raw"][:, None])
                if torch.device(device).type == "cuda":
                    packed = packed.contiguous(memory_format=torch.channels_last)
                variance = packed.clamp_min(0) * shot + read
                count = len(crop_records)
                labels = colors[None].expand(count, -1)
                wb = packed.new_tensor(meta["white_balance"])[None].expand(count, -1)
                matrix = packed.new_tensor(meta["camera_to_srgb"])[None].expand(count, -1, -1)
                predictions = [
                    ("Bilinear", bilinear(packed, labels)),
                    ("Malvar2004:WB", malvar(packed, labels, wb)),
                    ("Wiener7+Malvar2004:WB", malvar(wiener_packed(packed, variance), labels, wb)),
                ]
                for label, model, compute in current_models:
                    if hasattr(model, "set_noise"):
                        multiplier = (
                            noise_multiplier
                            if getattr(
                                getattr(model, "config", None), "variance_stabilization", False
                            )
                            else 1.0
                        )
                        model.set_noise(shot * multiplier, read * multiplier)
                    with amp_context(device, dtype=compute):
                        arguments = (packed, variance * noise_multiplier, labels, wb, matrix)
                        prediction = (
                            predict_dihedral8(model, *arguments)
                            if label in ensemble_labels
                            else model(*arguments)
                        )
                    predictions.append((label, prediction))
                    if prediction_callback is not None:
                        prediction_callback(label, {"ids": [c["id"] for c in crop_records],
                                                    "scene": case["scene"], "conditioning": case["conditioning"],
                                                    "noise_multiplier": noise_multiplier,
                                                    "pattern": meta["pattern"]}, prediction,
                                            {**tensors, "packed": packed, "variance": arguments[1],
                                             "colors": labels, "wb": wb, "matrix": matrix})
                border = 32
                region = (..., slice(border, -border), slice(border, -border))
                for label, prediction in predictions:
                    if not torch.isfinite(prediction).all():
                        raise ValueError(f"Nonfinite prediction from {label}")
                    sensor_psnr, samples = measured_sensor_psnr(
                        prediction[region],
                        tensors["sensor_reference"][region],
                        tensors["sensor_mask"][region],
                    )
                    auxiliary = quality_metrics(
                        prediction[region], tensors["reference_rgb"][region], wb, matrix
                    )
                    metrics = {
                        "sensor_psnr": sensor_psnr,
                        "reference_samples": samples,
                        "ahd_srgb_psnr": auxiliary["srgb_psnr"],
                        "ahd_srgb_ssim": auxiliary["srgb_ssim"],
                        "ahd_chroma_mae": auxiliary["chroma_mae"],
                        "ahd_gradient_mae": auxiliary["gradient_mae"],
                    }
                    values = {k: v.cpu().tolist() for k, v in metrics.items()}
                    for i, crop in enumerate(crop_records):
                        row = {
                            "scene": case["scene"],
                            "pair": case["noisy"]["sha256"],
                            "tile_id": crop["id"],
                            "iso": meta.get("iso"),
                            "model": label,
                            "pattern": meta["pattern"],
                            "metrics": {
                                k: float(v[i]) if np.isfinite(v[i]) else None
                                for k, v in values.items()
                            },
                        }
                        rows.append(row)
                        case_records.append(row)
                        stream.write(json.dumps(row, allow_nan=False) + "\n")
                    center = len(case["crops"]) // 2
                    if (
                        label in {item[0] for item in current_models}
                        and case["scene"] in crop_scenes
                        and case is high_cases[case["scene"]]
                        and start <= center < start + count
                    ):
                        i = center - start
                        xywh = center_crop(prediction.shape, border=border)
                        images = [
                            (
                                name,
                                display_crop(
                                    rgb[i : i + 1], wb[i : i + 1], matrix[i : i + 1], xywh
                                ),
                            )
                            for name, rgb in [
                                ("Noisy (Malvar)", predictions[1][1]),
                                ("Denoised", prediction),
                                ("AHD reference", tensors["reference_rgb"]),
                            ]
                        ]
                        crops.append(
                            save_triplet(
                                output,
                                f"{case['scene']}:{label}",
                                images,
                                caption=f"{case['scene']} / ISO {meta.get('iso')} / {label}",
                                metadata={
                                    "scene": case["scene"],
                                    "conditioning": case["conditioning"],
                                    "white_balance": meta["white_balance"],
                                    "camera_to_srgb": meta["camera_to_srgb"],
                                    "checkpoint_sha256": next(
                                        r.get("sha256", r.get("weight_sha256"))
                                        for r in receipts
                                        if r["label"] == label
                                        or (r["label"] == "RawNIND" and label.startswith("RawNIND"))
                                    ),
                                    "noisy_sha256": case["noisy"]["sha256"],
                                    "prepared_crop": crop_records[i],
                                    "evaluation_tile_xywh": xywh,
                                    "model_label": label,
                                    "display_exposure": 1.0,
                                    "variance_multiplier": noise_multiplier,
                                    "reference": "Registered low-noise RAW, auxiliary LibRaw AHD RGB; primary scores use measured CFA",
                                },
                            )
                        )
                if gallery and case is high_cases[case["scene"]]:
                    center = len(case["crops"]) // 2
                    if start <= center < start + count:
                        index = center - start
                        panels = [
                            ("AHD reference (auxiliary)", tensors["reference_rgb"])
                        ] + predictions
                        images = [
                            (label, render(rgb, wb, matrix)[index].permute(1, 2, 0).cpu().numpy())
                            for label, rgb in panels
                        ]
                        pictures.append(
                            (case["scene"], meta.get("iso"), crop_records[index]["xywh"], images)
                        )
            for label in sorted({r["model"] for r in case_records}):
                records = [r for r in case_records if r["model"] == label]
                means = {}
                for key in records[0]["metrics"]:
                    values = [r["metrics"][key] for r in records if r["metrics"][key] is not None]
                    means[key] = float(np.mean(values)) if values else None
                pair_rows.append(
                    {
                        "id": case["scene"],
                        "kind": "real",
                        "condition": case["noisy"]["sha256"],
                        "pattern": meta["pattern"],
                        "model": label,
                        "metrics": means,
                    }
                )
            stream.flush()
            print(
                json.dumps(
                    {
                        "event": "real-quality",
                        "scene": case["scene"],
                        "iso": meta.get("iso"),
                        "crops": len(case["crops"]),
                    }
                ),
                flush=True,
            )
    aggregate = summarize(
        pair_rows, comparison_metrics=("sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim")
    )
    result = {
        "format_version": 1,
        "prepared_manifest": str(prepared),
        "prepared_sha256": hashlib.sha256(payload).hexdigest(),
        "models": receipts,
        "reference_input_scales": baseline_scales,
        "precision": precision,
        "border": 32,
        "batch_size": batch_size,
        "learned_model_variance_multiplier": noise_multiplier,
        "prior_window_override": prior_window,
        "learned_model_self_ensemble": self_ensemble,
        "source_sha256": source_sha256,
        "torch": str(torch.__version__),
        "scenes": len({c["scene"] for c in data["cases"]}),
        "pairs": len(data["cases"]),
        "split": data["split"],
        "protocol": "Mean crops within each noisy capture, mean captures within scene, mean scenes. Bootstrap scenes, not crops.",
        "reference": "Primary: measured clean CFA samples after shared integer alignment/gain. Auxiliary RGB: calibrated LibRaw AHD.",
        "caveats": data["notes"],
        "dataset_license": data["dataset_license"],
        "attribution": data["attribution"],
        "per_pair": pair_rows,
        "native_crops": crops,
        **aggregate,
    }
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    write_report(
        output,
        result,
        crops,
        title="Paired real RAW evaluation",
        note="Primary scores use measured clean CFA samples. The displayed reference is auxiliary LibRaw AHD, not exact RGB ground truth.",
        metrics=("sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim"),
    )
    if pictures:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        for scene, iso, crop, panels in pictures:
            cols = 3
            figure, axes = plt.subplots(
                (len(panels) + cols - 1) // cols, cols, figsize=(12, 12), squeeze=False
            )
            for axis in axes.flat:
                axis.axis("off")
            for axis, (label, image) in zip(axes.flat, panels):
                axis.imshow(image)
                axis.set_title(label, fontsize=7)
            figure.suptitle(
                f"{scene} / ISO {iso} / crop {crop}; auxiliary AHD reference", fontsize=10
            )
            figure.tight_layout()
            name = hashlib.sha256(scene.encode()).hexdigest()[:12]
            figure.savefig(output / f"comparison-{name}.png", dpi=140)
            plt.close(figure)
    return result
