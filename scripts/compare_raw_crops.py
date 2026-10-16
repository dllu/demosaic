"""Compare specified private RAW crops locally without ground-truth claims.

Selection JSON: [{"source": "/read-only/photo.raf", "x": 0.2, "y": 0.3,
                  "size": 512, "display_exposure": 2.0}]
x/y give fractional top-left sensor coordinates; crops are snapped to even phase.
Optional regions name native xywh ROIs inside each context. With RawNIND,
native triplets compare methods on the same noisy capture; no panel is GT.
"""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from report_raw_pair import rawnind_comparators

from demosaic.cfa import bilinear, color_indices, malvar, pack
from demosaic.color import render
from demosaic.inference import load_checkpoint
from demosaic.io import read_raw
from demosaic.noise import Sensor
from demosaic.nonlocal_reference import load_nonlocal_reference
from demosaic.precision import COMPUTE_DTYPES, amp_context
from demosaic.prior import wiener_packed
from demosaic.reference import RawNind, publisher_input_scale
from demosaic.reporting import center_crop, display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("checkpoint", nargs="+", type=Path)
    parser.add_argument("--rawnind", type=Path)
    parser.add_argument("--nonlocal-reference", type=Path)
    parser.add_argument(
        "--rawnind-gain-modes", nargs="+", choices=("cfa-ls", "cfa-channel"), default=["cfa-ls"]
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cuda")
    parser.add_argument("--precision", choices=COMPUTE_DTYPES, default="bfloat16")
    args = parser.parse_args()
    if args.device == "cpu" and args.precision != "float32":
        raise ValueError("CPU qualitative comparisons require --precision float32")
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "selection-and-metadata.json").exists():
        raise ValueError("Comparison already exists; choose a new output directory")
    archive = output / "source"
    archive.mkdir(exist_ok=True)
    for path in [
        Path(__file__),
        Path(__file__).with_name("report_raw_pair.py"),
        *sorted(Path("src/demosaic").glob("*.py")),
    ]:
        (archive / path.name).write_bytes(path.read_bytes())
    (archive / "selection.json").write_bytes(args.selection.read_bytes())
    torch.set_num_threads(4)
    models, weights = [], []
    for path in args.checkpoint:
        frozen, digest = freeze_checkpoint(path, output / "weights")
        model, state = load_checkpoint(frozen, args.device)
        model.eval().to(memory_format=torch.channels_last)
        run_name = Path(state.get("config", {}).get("run", path.parent)).name
        label = f"{run_name}, step {state['step']}"
        models.append((label, model, args.precision))
        weights.append(
            {
                "label": label,
                "source": str(path),
                "sha256": digest,
                "snapshot": str(frozen),
                "compute_precision": args.precision,
                "device": args.device,
                "memory_format": "channels_last",
                "model_config": model.config.to_dict(),
            }
        )
        del state
    if args.rawnind:
        references, receipts = rawnind_comparators(
            args.rawnind, args.rawnind_gain_modes, device=args.device
        )
        models = references + models
        weights += receipts
    if args.nonlocal_reference:
        reference = load_nonlocal_reference(
            args.nonlocal_reference, device=args.device, archive=output
        )
        models.append((reference.receipt["label"], reference, "float32"))
        weights.append(reference.receipt)
    selections = json.loads(args.selection.read_text())
    figure, axes = plt.subplots(
        len(selections),
        len(models) + 3,
        figsize=(4 * (len(models) + 3), 4 * len(selections)),
        squeeze=False,
    )
    records, crops, float_contexts = [], [], []
    for row, selection in enumerate(selections):
        source = Path(selection["source"])
        with source.open("rb") as reader:
            source_sha = hashlib.file_digest(reader, "sha256").hexdigest()
        if selection.get("source_sha256", source_sha) != source_sha:
            raise ValueError("Qualitative source hash differs from the fixed selection")
        raw, metadata = read_raw(selection["source"])
        if selection.get("camera", metadata.camera) != metadata.camera:
            raise ValueError("Qualitative camera differs from the fixed selection")
        h, w = raw.shape
        size = selection.get("size", 512)
        if size < 32 or size % 2 or size > min(h, w):
            raise ValueError("RAW context must be even, at least32 and fit the capture")
        y = min(h - size, int(h * selection["y"])) // 2 * 2
        x = min(w - size, int(w * selection["x"])) // 2 * 2
        crop = torch.from_numpy(raw[y : y + size, x : x + size].copy()).to(args.device)
        del raw
        colors = color_indices(metadata.pattern, device=args.device)[None]
        packed = pack(crop[None, None]).contiguous(memory_format=torch.channels_last)
        # These priors are disclosed assumptions, not camera calibration.
        shot, read = Sensor(iso=metadata.iso or 100).coefficients()
        if ("shot" in selection) != ("read" in selection):
            raise ValueError("A crop noise override requires both shot and read")
        shot, read = selection.get("shot", shot), selection.get("read", read)
        variance = packed.clamp_min(0) * shot + read
        wb = torch.tensor(metadata.white_balance, device=args.device)[None]
        matrix = torch.tensor(metadata.camera_to_srgb, device=args.device)[None]
        print(
            json.dumps({"event": "camera-start", "camera": metadata.camera, "device": args.device}),
            flush=True,
        )
        images = [
            ("Bilinear", bilinear(packed, colors)),
            ("Malvar 2004, WB", malvar(packed, colors, wb)),
            ("Variance prior + Malvar", malvar(wiener_packed(packed, variance), colors, wb)),
        ]
        for label, model, precision in models:
            if isinstance(model, RawNind):
                model.input_scale = torch.tensor(
                    publisher_input_scale(
                        metadata.white_levels, metadata.black_levels, metadata.adc_white_level
                    ),
                    device=args.device,
                    dtype=torch.float32,
                )
            if hasattr(model, "set_noise"):
                model.set_noise(shot, read)
            with amp_context(args.device, dtype=precision):
                prediction = model(packed, variance, colors, wb, matrix)
            if not torch.isfinite(prediction).all():
                raise ValueError(f"Nonfinite qualitative prediction: {label}")
            images.append((label, prediction))
        rendered = dict(images)
        regions = selection.get(
            "regions", [{"name": "center", "xywh": center_crop((size, size), size=160)}]
        )
        for region in regions:
            roi = region["xywh"]
            rx, ry, rw, rh = roi
            if min(rx, ry) < 0 or min(rw, rh) < 1 or rx + rw > size or ry + rh > size:
                raise ValueError("Native ROI must fit its fixed RAW context")
            for label, model, precision in models:
                if isinstance(model, RawNind):
                    continue
                model_receipt = next(r for r in weights if r["label"] == label)
                for baseline, reference, _ in models:
                    if not isinstance(reference, RawNind):
                        continue
                    reference_receipt = next(r for r in weights if r["label"] == baseline)
                    caption = f"{metadata.camera} / {selection.get('purpose', row)} / {region['name']} / {label} / {baseline}"
                    panels = [
                        ("Noisy (Malvar)", rendered["Malvar 2004, WB"]),
                        ("Restored", rendered[label]),
                        ("RawNIND (not GT)", rendered[baseline]),
                    ]
                    crops.append(
                        save_triplet(
                            output,
                            f"{row}:{region['name']}:{label}:{baseline}",
                            [
                                (
                                    name,
                                    display_crop(
                                        rgb,
                                        wb,
                                        matrix,
                                        roi,
                                        exposure=selection.get("display_exposure", 1),
                                    ),
                                )
                                for name, rgb in panels
                            ],
                            caption=caption,
                            metadata={
                                "source": str(source),
                                "source_sha256": source_sha,
                                "raw_metadata": asdict(metadata),
                                "context_xywh": [x, y, size, size],
                                "sensor_roi_xywh": [x + rx, y + ry, rw, rh],
                                "context_roi_xywh": roi,
                                "region": region["name"],
                                "model_label": label,
                                "checkpoint_sha256": model_receipt["sha256"],
                                "compute_precision": precision,
                                "device": args.device,
                                "baseline": reference_receipt,
                                "conditioning": {
                                    "shot": shot,
                                    "read": read,
                                    "source": selection.get("noise_source", "declared prior"),
                                },
                                "white_balance": metadata.white_balance,
                                "camera_to_srgb": metadata.camera_to_srgb,
                                "display_exposure": selection.get("display_exposure", 1),
                                "reference": "RawNIND on the same noisy capture; comparator, not GT; no pixelwise score",
                            },
                        )
                    )
        for col, (label, rgb) in enumerate(images):
            path = output / f"capture-{row}-method-{col}-linear-f32.npy"
            values = rgb.float().cpu().numpy()
            np.save(path, values, allow_pickle=False)
            with path.open("rb") as reader:
                digest = hashlib.file_digest(reader, "sha256").hexdigest()
            float_contexts.append(
                {
                    "image": path.name,
                    "source": str(source),
                    "model": label,
                    "context_xywh": [x, y, size, size],
                    "shape": list(values.shape),
                    "dtype": "float32",
                    "sha256": digest,
                    "encoding": "Unquantized linear camera RGB before display exposure/clipping",
                }
            )
            display = render(rgb * selection.get("display_exposure", 1), wb, matrix)
            axes[row, col].imshow(display[0].permute(1, 2, 0).cpu().numpy())
            axes[row, col].set_title(metadata.camera + " / " + label)
            axes[row, col].axis("off")
        records.append(
            {
                "raw": asdict(metadata),
                "crop_xywh": [x, y, size, size],
                "shot_prior": shot,
                "read_prior": read,
                "source_sha256": source_sha,
                **selection,
            }
        )
        print(
            json.dumps(
                {
                    "event": "camera-complete",
                    "camera": metadata.camera,
                    "native_crops_so_far": len(crops),
                }
            ),
            flush=True,
        )
    figure.tight_layout()
    figure.savefig(output / "comparison.png", dpi=140)
    plt.close(figure)
    (output / "selection-and-metadata.json").write_text(json.dumps(records, indent=2) + "\n")
    (output / "checkpoints.json").write_text(json.dumps(weights, indent=2) + "\n")
    result = {
        "scope": "Single-capture qualitative comparisons; no clean reference or pixelwise quality score.",
        "selection": records,
        "models": weights,
        "native_crops": crops,
        "float_contexts": float_contexts,
        "source_files": {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in archive.glob("*.py")
        },
        "runtime": {
            "device": args.device,
            "neural_precision": args.precision,
            "torch": str(torch.__version__),
            "cuda_initialized": torch.cuda.is_initialized(),
        },
    }
    if args.device == "cpu" and result["runtime"]["cuda_initialized"]:
        raise RuntimeError("CPU comparison unexpectedly initialized CUDA")
    (output / "report.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [
        "# Cross-camera qualitative comparison",
        "",
        "Single noisy captures; no clean reference or quality scores.",
        "When present, RawNIND is a comparator, **not GT**.",
        "Native panels use identical coordinates/WB/matrix/exposure with no resizing.",
        "The separate [overview](comparison.png) is resized and is not a 100% view.",
        "",
    ]
    for crop in crops:
        lines += [crop["caption"], "", f"![Native method comparison]({crop['image']})", ""]
    lines += ["[Complete source, checkpoint, noise and ROI records](report.json).", ""]
    (output / "report.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
