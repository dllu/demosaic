"""Native-pixel qualitative comparisons of two independently framed RAW captures.

Selection JSON specifies noisy/reference paths and regions with name, noisy_xy,
reference_xy and size (default 160). Coordinates are unrotated visible-sensor
pixels. A 512-pixel noisy context tile is restored, then cropped without scaling.
The low-ISO frame is a reference, never exact GT; no paired quality scores.
"""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from demosaic.calibration import estimate_noise
from demosaic.cfa import color_indices, malvar, pack
from demosaic.color import render
from demosaic.gaussian import load_gaussian_prior
from demosaic.inference import load_checkpoint, restore_tiled
from demosaic.io import read_raw, write_rgb16
from demosaic.noise import Sensor
from demosaic.nonlocal_reference import load_nonlocal_reference
from demosaic.precision import COMPUTE_DTYPES, REFINEMENT_DTYPES, amp_context
from demosaic.realdata import read_reference
from demosaic.reference import RawNind, load_rawnind, publisher_input_scale
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint


def rawnind_comparators(directory, modes, *, device="cuda"):
    """Separate gain adapters share the same immutable upstream network weights."""
    labels = {"cfa-ls": "RawNIND:CFA-LS", "cfa-channel": "RawNIND:CFA-channel"}
    modes = list(dict.fromkeys(modes))
    first = load_rawnind(directory, gain_mode=modes[0], device=device)
    digest = hashlib.sha256((directory / "utnet2-bayer.pt").read_bytes()).hexdigest()
    models, receipts = [], []
    for index, mode in enumerate(modes):
        adapter = first if index == 0 else RawNind(first.network, gain_mode=mode)
        adapter.eval()
        models.append((labels[mode], adapter, "float32"))
        receipts.append(
            {
                "label": labels[mode],
                "model_config": getattr(first, "reference_config", None),
                "gain_mode": mode,
                "precision": "IEEE float32",
                "device": str(device),
                "sha256": digest,
            }
        )
    return models, receipts


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("checkpoint", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rawnind", type=Path)
    parser.add_argument(
        "--rawnind-gain-modes",
        nargs="+",
        choices=("cfa-ls", "cfa-channel"),
        default=["cfa-ls"],
        help="Input-only calibration variants; defaults to the historical global CFA-LS",
    )
    parser.add_argument("--gaussian-reference", type=Path)
    parser.add_argument("--nonlocal-reference", type=Path)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--precision", choices=COMPUTE_DTYPES, default="float16")
    parser.add_argument("--refinement-precision", choices=REFINEMENT_DTYPES, default="float32")
    parser.add_argument(
        "--full-frame",
        action="store_true",
        help="Restore the complete photo before cropping; also save linear/sRGB16 TIFFs",
    )
    args = parser.parse_args()
    if args.device == "cpu" and (
        args.precision != "float32" or args.refinement_precision != "float32"
    ):
        raise ValueError("CPU paired-capture comparisons require explicit float32 precision")
    torch.set_num_threads(4)
    selection = json.loads(args.selection.read_text())
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "report.json").exists():
        raise ValueError("Report already exists; choose a new directory")
    archive = output / "source"
    archive.mkdir(exist_ok=True)
    for path in [Path(__file__), *sorted(Path("src/demosaic").glob("*.py"))]:
        (archive / path.name).write_bytes(path.read_bytes())
    (archive / "selection.json").write_bytes(args.selection.read_bytes())
    models, weights = [], []
    for i, path in enumerate(args.checkpoint):
        frozen, digest = freeze_checkpoint(path, output / "weights")
        model, state = load_checkpoint(
            frozen, args.device, refinement_precision=args.refinement_precision
        )
        model.eval().to(memory_format=torch.channels_last)
        name = Path(state.get("config", {}).get("run", path.stem)).name
        label = f"{i}:{name}:step-{state['step']}"
        models.append((label, model, args.precision))
        weights.append(
            {
                "label": label,
                "sha256": digest,
                "snapshot": str(frozen),
                "precision": args.precision,
                "device": args.device,
                "refinement_compute_precision": args.refinement_precision,
                "model_config": model.config.to_dict(),
            }
        )
        del state
    if args.rawnind:
        references, receipts = rawnind_comparators(
            args.rawnind, args.rawnind_gain_modes, device=args.device
        )
        models.extend(references)
        weights.extend(receipts)
    if args.gaussian_reference:
        gaussian = load_gaussian_prior(args.gaussian_reference, device=args.device, archive=output)
        models.append((gaussian.receipt["label"], gaussian, "float32"))
        weights.append(gaussian.receipt)
    if args.nonlocal_reference:
        reference = load_nonlocal_reference(
            args.nonlocal_reference, device=args.device, archive=output
        )
        models.append((reference.receipt["label"], reference, "float32"))
        weights.append(reference.receipt)
    raw, meta = read_raw(selection["noisy"])
    reference_raw, reference, refmeta, calibration = read_reference(selection["reference"])
    del reference_raw
    if meta.camera != refmeta.camera:
        raise ValueError("This qualitative report requires the same camera")
    estimate = estimate_noise(raw)
    shot, read = (
        (estimate.shot, estimate.read)
        if estimate.reliable
        else Sensor(iso=meta.iso or 100).coefficients()
    )
    colors = color_indices(meta.pattern, device=args.device)[None]
    wb = torch.tensor(meta.white_balance, device=args.device)[None]
    matrix = torch.tensor(meta.camera_to_srgb, device=args.device)[None]
    exposure = selection.get("display_exposure", 4.0)
    crops, contexts, full_frames, float_contexts = [], [], [], []

    def save_float(values, name, **metadata):
        path = output / name
        array = values.detach().float().cpu().numpy()
        if not np.isfinite(array).all():
            raise ValueError(f"Nonfinite qualitative float artifact: {name}")
        np.save(path, array, allow_pickle=False)
        with path.open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        float_contexts.append(
            {
                "image": path.name,
                "sha256": digest,
                "shape": list(array.shape),
                "dtype": "float32",
                **metadata,
            }
        )

    for region in selection["regions"]:
        x, y = region["noisy_xy"]
        rx, ry = region["reference_xy"]
        size = region.get("size", 160)
        tile = 512
        margin = (tile - size) // 2
        tx, ty = (x - margin) // 2 * 2, (y - margin) // 2 * 2
        if (
            size > tile - 64
            or min(tx, ty, rx, ry) < 0
            or ty + tile > raw.shape[0]
            or tx + tile > raw.shape[1]
            or ry + size > reference.shape[0]
            or rx + size > reference.shape[1]
        ):
            raise ValueError("Region/context outside the visible sensor")
        packed = pack(
            torch.from_numpy(raw[ty : ty + tile, tx : tx + tile].copy())[None, None].to(args.device)
        )
        packed = packed.contiguous(memory_format=torch.channels_last)
        variance = packed.clamp_min(0) * shot + read
        xywh = [x - tx, y - ty, size, size]
        noisy = display_crop(malvar(packed, colors, wb), wb, matrix, xywh, exposure=exposure)
        # Shared noisy-capture WB/matrix/exposure; no per-panel automatic adjustment.
        clean = (
            torch.from_numpy(reference[ry : ry + size, rx : rx + size].copy())
            .permute(2, 0, 1)[None]
            .to(args.device)
        )
        reference_display = display_crop(clean, wb, matrix, [0, 0, size, size], exposure=exposure)
        save_float(
            packed,
            f"{region['name']}-noisy-packed-f32.npy",
            role="noisy-packed",
            region=region,
            context_xywh=[tx, ty, tile, tile],
            pattern=meta.pattern,
            encoding="Four packed CFA phases, black-subtracted/white-normalized sensor units",
        )
        save_float(
            clean,
            f"{region['name']}-reference-rgb-f32.npy",
            role="reference-rgb",
            region=region,
            source_roi_xywh=[rx, ry, size, size],
            encoding="Independent LibRaw AHD camera RGB calibrated against its own CFA; not GT",
        )
        contexts.append((region, tx, ty, packed, variance, xywh, noisy, reference_display))
    for model_index, (label, model, precision) in enumerate(models):
        if hasattr(model, "set_noise"):
            model.set_noise(shot, read)
        if isinstance(model, RawNind):
            model.input_scale = torch.tensor(
                publisher_input_scale(meta.white_levels, meta.black_levels, meta.adc_white_level),
                device=args.device,
            )
        if args.full_frame:
            restored, timing = restore_tiled(
                model,
                raw,
                colors[0],
                shot=shot,
                read=read,
                tile=512,
                overlap=64,
                batch_size=4,
                wb=meta.white_balance,
                matrix=meta.camera_to_srgb,
                precision=precision,
                device=args.device,
            )
            paths = [
                output / f"restored-{model_index}-linear16.tiff",
                output / f"restored-{model_index}-srgb16.tiff",
            ]
            write_rgb16(paths[0], restored.permute(1, 2, 0).numpy(), metadata=meta, flip=meta.flip)
            preview = render(restored[None] * exposure, wb.cpu(), matrix.cpu())[0]
            write_rgb16(
                paths[1],
                preview.permute(1, 2, 0).numpy(),
                metadata={"raw": asdict(meta), "display_exposure": exposure},
                color_space="sRGB",
                flip=meta.flip,
            )
            files = []
            for path in paths:
                with path.open("rb") as handle:
                    digest = hashlib.file_digest(handle, "sha256").hexdigest()
                files.append({"path": path.name, "bytes": path.stat().st_size, "sha256": digest})
            full_frames.append(
                {
                    "model_label": label,
                    "timing": timing,
                    "files": files,
                    "display_exposure": exposure,
                    "crop_source": "Blended FP32 full frame before RGB16 encoding",
                }
            )
            del preview
            print(json.dumps({"event": "full-frame", "model": label, **timing}), flush=True)
        for region, tx, ty, packed, variance, xywh, noisy, reference_display in contexts:
            if args.full_frame:
                x, y = region["noisy_xy"]
                size = region.get("size", 160)
                denoised = display_crop(
                    restored[None], wb.cpu(), matrix.cpu(), [x, y, size, size], exposure=exposure
                )
            else:
                with amp_context(args.device, dtype=precision):
                    prediction = model(packed, variance, colors, wb, matrix)
                save_float(
                    prediction,
                    f"{region['name']}-method-{model_index}-rgb-f32.npy",
                    role="restored-context",
                    region=region,
                    model_label=label,
                    checkpoint_sha256=weights[model_index].get("sha256"),
                    context_xywh=[tx, ty, tile, tile],
                    encoding="Unquantized linear camera RGB before display exposure/clipping",
                )
                denoised = display_crop(prediction, wb, matrix, xywh, exposure=exposure)
            crops.append(
                save_triplet(
                    output,
                    f"{region['name']}:{label}",
                    [
                        ("Noisy (Malvar)", noisy),
                        ("Denoised", denoised),
                        (
                            f"ISO{refmeta.iso:g} ref (not GT)"
                            if refmeta.iso
                            else "Low-ISO ref (not GT)",
                            reference_display,
                        ),
                    ],
                    caption=f"{region['name']} / {label}",
                    metadata={
                        "region": region,
                        "model_label": label,
                        "checkpoint_sha256": weights[model_index].get("sha256"),
                        "compute_precision": precision,
                        "device": args.device,
                        "conditioning": {"shot": shot, "read": read},
                        "context_xywh": None if args.full_frame else [tx, ty, tile, tile],
                        "full_frame": args.full_frame,
                        "display_exposure": exposure,
                        "shared_wb": meta.white_balance,
                        "shared_matrix": meta.camera_to_srgb,
                        "reference": "Separately framed low-ISO exposure; not exact GT; no resampling/warping",
                    },
                )
            )
            print(
                json.dumps(
                    {
                        "event": "context-crop",
                        "model": label,
                        "region": region["name"],
                        "device": args.device,
                    }
                ),
                flush=True,
            )
        if args.full_frame:
            del restored
    sources = []
    for key, metadata in (("noisy", meta), ("reference", refmeta)):
        with Path(selection[key]).open("rb") as handle:
            digest = hashlib.file_digest(handle, "sha256").hexdigest()
        sources.append({"role": key, "sha256": digest, "metadata": asdict(metadata)})
    receipt = {
        "selection": selection,
        "sources": sources,
        "models": weights,
        "noise_estimate": estimate.to_dict(),
        "conditioning": {
            "shot": shot,
            "read": read,
            "source": "input Haar fit"
            if estimate.reliable
            else "nominal ISO prior (not calibrated)",
        },
        "reference_calibration": calibration,
        "native_crops": crops,
        "full_frames": full_frames,
        "float_contexts": float_contexts,
        "runtime": {
            "device": args.device,
            "neural_precision": args.precision,
            "torch": str(torch.__version__),
            "cuda_initialized": torch.cuda.is_initialized(),
        },
        "usage": "Qualitative evaluation only; never training",
        "quality_scores": None,
    }
    if args.device == "cpu" and receipt["runtime"]["cuda_initialized"]:
        raise RuntimeError("CPU paired-capture comparison unexpectedly initialized CUDA")
    (output / "report.json").write_text(json.dumps(receipt, indent=2) + "\n")
    lines = [
        "# GFX native-pixel qualitative comparison",
        "",
        selection.get("notes", "Independently captured low-ISO reference; not exact GT."),
        "",
        "Each panel is native resolution. Open the PNG at 100%; no resizing or warping.",
        f"Common display exposure: ×{exposure:g}. Shared noisy-capture WB/matrix; no automatic brightness.",
        "Noise conditioning: "
        + receipt["conditioning"]["source"]
        + ". No PSNR/SSIM against this reference.",
        "",
    ]
    for crop in crops:
        lines += [crop["caption"], "", f"![Native pixel comparison]({crop['image']})", ""]
    lines += ["[Coordinates, settings and source/model hashes](report.json)", ""]
    (output / "report.md").write_text("\n".join(lines))
    print(str(output / "report.md"))


if __name__ == "__main__":
    main()
