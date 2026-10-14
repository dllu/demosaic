"""Command-line data preparation, training, evaluation and RAW inference."""

import argparse
import json
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from .safety import writable_path


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    prepare = commands.add_parser(
        "prepare", help="Bin licensed Commons images to linear 16-bit caches"
    )
    prepare.add_argument("--source", type=Path, default=Path("/mnt/external/qi"))
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--limit", type=int, default=0)
    prepare.add_argument("--factor", type=int, default=8)
    prepare.add_argument("--min-size", type=int, default=256)
    prepare.add_argument("--workers", type=int, default=2)
    training = commands.add_parser("train")
    training.add_argument("config", type=Path)
    training.add_argument("--resume", type=Path)
    training.add_argument(
        "--initialize", type=Path, help="Warm-start model weights with a fresh optimizer"
    )
    training.add_argument(
        "--stop-after", type=int, help="Save and exit after this many additional steps"
    )
    evaluate = commands.add_parser(
        "evaluate", help="Fixed held-out camera-linear and rendered PSNR"
    )
    evaluate.add_argument("checkpoint", type=Path)
    evaluate.add_argument("--manifest", type=Path, required=True)
    evaluate.add_argument("--split", choices=("val", "test"), default="val")
    evaluate.add_argument("--patch-size", type=int, default=256)
    evaluate.add_argument("--batch-size", type=int, default=4)
    evaluate.add_argument("--max-batches", type=int, default=0)
    evaluate.add_argument("--output", type=Path, required=True)
    evaluate.add_argument("--device", default="cuda")
    evaluate.add_argument(
        "--rawnind", type=Path, help="Directory containing separately fetched reference"
    )
    infer = commands.add_parser("infer", help="Camera RAW or 16-bit Bayer NPY/TIFF to RGB16 TIFF")
    infer.add_argument("checkpoint", type=Path)
    infer.add_argument("input", type=Path)
    infer.add_argument("output", type=Path)
    infer.add_argument("--preview", type=Path, help="Optional color-managed sRGB16 TIFF")
    infer.add_argument("--pattern", choices=("RGGB", "BGGR", "GRBG", "GBRG"), default="RGGB")
    infer.add_argument("--black", type=float, default=0)
    infer.add_argument("--white", type=float, default=65535)
    infer.add_argument("--shot", type=float, required=True, help="Var(y|x) = shot*x + read")
    infer.add_argument("--read", type=float, required=True, help="Normalized read-noise variance")
    infer.add_argument("--tile", type=int, default=256)
    infer.add_argument("--overlap", type=int, default=64)
    infer.add_argument("--batch-size", type=int, default=4)
    infer.add_argument("--device", default="cuda")
    benchmark = commands.add_parser(
        "benchmark", help="Measure actual tiled large-image restoration"
    )
    benchmark.add_argument("checkpoint", type=Path)
    benchmark.add_argument("--height", type=int, default=10000)
    benchmark.add_argument("--width", type=int, default=10000)
    benchmark.add_argument("--tile", type=int, default=512)
    benchmark.add_argument("--overlap", type=int, default=64)
    benchmark.add_argument("--batch-size", type=int, default=8)
    benchmark.add_argument("--device", default="cuda")
    benchmark.add_argument("--output", type=Path, required=True)
    return root


def dump(path, data):
    path = writable_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(json.dumps(data, indent=2), flush=True)


def main(argv=None):
    args = parser().parse_args(argv)
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("high")
    if args.command == "prepare":
        from .prepare import prepare_commons

        prepare_commons(
            args.source,
            args.output,
            limit=args.limit,
            factor=args.factor,
            min_size=args.min_size,
            workers=args.workers,
        )
    elif args.command == "train":
        from .train import train

        train(
            args.config, resume=args.resume, initialize=args.initialize, stop_after=args.stop_after
        )
    elif args.command == "evaluate":
        from torch.utils.data import DataLoader

        from .data import CleanDataset
        from .inference import load_checkpoint
        from .train import evaluate

        model, checkpoint = load_checkpoint(args.checkpoint, args.device)
        loader = DataLoader(
            CleanDataset(args.manifest, args.split, args.patch_size), batch_size=args.batch_size
        )
        scores = evaluate(model, loader, args.device, max_batches=args.max_batches)
        if args.rawnind:
            from .reference import load_rawnind

            for gain_mode in ("input-mean", "cfa-ls"):
                baseline = load_rawnind(args.rawnind, gain_mode=gain_mode, device=args.device)
                reference_scores = evaluate(
                    baseline, loader, args.device, max_batches=args.max_batches, amp=False
                )
                scores[f"rawnind_{gain_mode}"] = reference_scores
                del baseline
        dump(
            args.output,
            {
                "checkpoint": str(args.checkpoint),
                "step": checkpoint["step"],
                "manifest": str(args.manifest),
                "split": args.split,
                "patch_size": args.patch_size,
                "sources": len(loader.dataset),
                "batch_size": args.batch_size,
                "evaluated_images": min(len(loader.dataset), args.max_batches * args.batch_size)
                if args.max_batches > 0
                else len(loader.dataset),
                "max_batches": args.max_batches,
                "noise": {"shot": 0.001, "read": 1e-6, "seed": 20261014},
                **scores,
            },
        )
    elif args.command == "infer":
        end_to_end_started = time.perf_counter()
        from .cfa import color_indices
        from .color import render
        from .inference import load_checkpoint, restore_tiled
        from .io import read_raw, write_rgb16

        # Validate all destinations before performing expensive inference.
        output = writable_path(args.output)
        if output == args.input.resolve() or (
            args.preview and args.preview.resolve() == args.input.resolve()
        ):
            raise ValueError("Inference output must not overwrite its input")
        if args.preview:
            writable_path(args.preview)
            if args.preview.resolve() == output:
                raise ValueError("Linear and sRGB output paths must differ")
        if output == args.checkpoint.resolve() or (
            args.preview and args.preview.resolve() == args.checkpoint.resolve()
        ):
            raise ValueError("Inference output must not overwrite its checkpoint")
        suffix = args.input.suffix.lower()
        metadata = None
        if suffix in (".npy", ".tif", ".tiff"):
            if suffix == ".npy":
                raw = np.load(args.input, allow_pickle=False)
            else:
                import tifffile

                raw = tifffile.imread(args.input)
            if args.white <= args.black:
                raise ValueError("White level must exceed black level")
            if raw.ndim != 2:
                raise ValueError("Expected single-channel Bayer data")
            raw = (raw.astype(np.float32) - args.black) / (args.white - args.black)
            pattern, wb, matrix, flip = args.pattern, None, None, 0
        else:
            raw, metadata = read_raw(args.input)
            pattern, wb, matrix, flip = (
                metadata.pattern,
                metadata.white_balance,
                metadata.camera_to_srgb,
                metadata.flip,
            )
        model, checkpoint = load_checkpoint(args.checkpoint, args.device)
        rgb, stats = restore_tiled(
            model,
            raw,
            color_indices(pattern),
            shot=args.shot,
            read=args.read,
            tile=args.tile,
            overlap=args.overlap,
            batch_size=args.batch_size,
            device=args.device,
            wb=wb,
            matrix=matrix,
        )
        write_rgb16(output, rgb.permute(1, 2, 0).numpy(), metadata=metadata, flip=flip)
        if args.preview:
            preview = render(
                rgb[None],
                None if wb is None else torch.tensor(wb)[None],
                None if matrix is None else torch.tensor(matrix)[None],
            )[0]
            write_rgb16(
                args.preview,
                preview.permute(1, 2, 0).numpy(),
                metadata=metadata,
                color_space="sRGB",
                flip=flip,
            )
        dump(
            output.with_suffix(".json"),
            {
                "input": str(args.input),
                "checkpoint": str(args.checkpoint),
                "step": checkpoint.get("step"),
                "shot": args.shot,
                "read": args.read,
                "pattern": pattern,
                "raw_metadata": asdict(metadata) if metadata else None,
                "end_to_end_seconds": time.perf_counter() - end_to_end_started,
                **stats,
            },
        )
    elif args.command == "benchmark":
        from .cfa import color_indices
        from .inference import load_checkpoint, restore_tiled

        writable_path(args.output)
        model, checkpoint = load_checkpoint(args.checkpoint, args.device)
        # Warm kernels before timing; benchmark records hardware and dimensions.
        raw = torch.rand(args.height, args.width, generator=torch.Generator().manual_seed(42))
        kwargs = {
            "shot": 0.001,
            "read": 1e-6,
            "tile": args.tile,
            "overlap": args.overlap,
            "batch_size": args.batch_size,
            "device": args.device,
        }
        restore_tiled(model, raw[: args.tile, : args.tile], color_indices("RGGB"), **kwargs)
        rgb, stats = restore_tiled(model, raw, color_indices("RGGB"), **kwargs)
        dump(
            args.output,
            {
                "checkpoint": str(args.checkpoint),
                "step": checkpoint.get("step"),
                "hardware": torch.cuda.get_device_name()
                if args.device.startswith("cuda")
                else "cpu",
                "torch": str(torch.__version__),
                "height": args.height,
                "width": args.width,
                "finite": bool(torch.isfinite(rgb).all()),
                "target_seconds": 10,
                "warmed": True,
                **stats,
            },
        )


if __name__ == "__main__":
    main()
