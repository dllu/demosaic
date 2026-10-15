"""Compare RGB correction precision on captured decoder features and exact flats.

This times only the correction branch, not end-to-end restoration. Other GPU
work can affect CUDA event times. The full Bayer/DINO body runs once in FP16;
physical maps, high-pass normalization and final scaling stay IEEE FP32.
"""

import argparse
import hashlib
import json
import statistics
from pathlib import Path

import torch

from demosaic.cfa import malvar
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import amp_context
from demosaic.reporting import center_crop, display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint, observation


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--camera", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--samples", type=int, default=8)
    args = parser.parse_args()
    if args.samples < 3:
        raise ValueError("Use at least three timing samples")
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "result.json").exists():
        raise ValueError("Choose a new output directory")
    source = output / "source"
    source.mkdir(exist_ok=True)
    for p in [Path(__file__), *sorted(Path("src/demosaic").glob("*.py"))]:
        (source / p.name).write_bytes(p.read_bytes())
    camera_bytes = args.camera.read_bytes()
    (source / "camera.json").write_bytes(camera_bytes)
    camera = json.loads(camera_bytes)
    meta = camera.get("raw", camera)
    frozen, digest = freeze_checkpoint(args.checkpoint, output / "weights")
    torch.set_num_threads(4)
    model, state = load_checkpoint(frozen, "cuda")
    if model.refiner is None or model.coarse_refiner is not None:
        raise ValueError("Use a checkpoint with a fine RGB correction and no coarse branch")
    model.eval().to(memory_format=torch.channels_last)
    levels = [0.002, 0.01, 0.05, 0.2]
    rgb = torch.tensor(levels, device="cuda")[:, None, None, None].expand(-1, 3, 512, 512)
    condition = {"name": "iso6400-prior", "exposure": 1.0, "shot": 0.00128, "read": 6.5536e-6}
    batch = observation(
        rgb,
        [f"flat-{x}" for x in levels],
        condition,
        meta["pattern"],
        meta["white_balance"],
        meta["camera_to_srgb"],
        20261015,
    )
    for key in ("packed", "variance"):
        batch[key] = batch[key].contiguous(memory_format=torch.channels_last)
    captured = []
    hook = model.refiner.register_forward_pre_hook(lambda m, a: captured.append(a))
    with amp_context("cuda", dtype="float16"):
        full = model(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
    hook.remove()
    values = captured[0]
    predictions, timings = {}, {p: [] for p in ("float32", "float16")}
    for precision in timings:
        model.set_refinement_precision(precision)
        predictions[precision] = values[0] + model.refiner(*values)
    assert torch.equal(predictions["float32"], full)
    for i in range(args.samples + 2):
        order = ("float32", "float16") if i % 2 else ("float16", "float32")
        for precision in order:
            model.set_refinement_precision(precision)
            start, end = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
            start.record()
            model.refiner(*values)
            end.record()
            end.synchronize()
            if i >= 2:
                timings[precision].append(start.elapsed_time(end))
    difference = predictions["float16"] - predictions["float32"]
    noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
    crops, metrics = [], {}
    xywh = center_crop(full.shape, border=64)
    for precision, prediction in predictions.items():
        scores = quality_metrics(
            prediction[..., 64:-64, 64:-64],
            batch["target"][..., 64:-64, 64:-64],
            batch["wb"],
            batch["matrix"],
        )
        metrics[precision] = {k: v.cpu().tolist() for k, v in scores.items()}
        for index in (1, 2):
            images = [
                (
                    label,
                    display_crop(
                        image[index : index + 1],
                        batch["wb"][index : index + 1],
                        batch["matrix"][index : index + 1],
                        xywh,
                    ),
                )
                for label, image in [
                    ("Noisy (Malvar)", noisy),
                    ("Denoised", prediction),
                    ("GT (synthetic)", batch["target"]),
                ]
            ]
            crops.append(
                save_triplet(
                    output,
                    f"{precision}:flat-{levels[index]}",
                    images,
                    caption=f"Refinement {precision}, flat {levels[index]}",
                    metadata={
                        "checkpoint_sha256": digest,
                        "refinement_compute_precision": precision,
                        "base_compute_precision": "float16",
                        "source": "Exact synthetic flat",
                        "level": levels[index],
                        "condition": condition,
                        "pattern": meta["pattern"],
                        "white_balance": meta["white_balance"],
                        "camera_to_srgb": meta["camera_to_srgb"],
                        "seed": 20261015,
                        "evaluation_tile_xywh": xywh,
                        "display_exposure": 1.0,
                    },
                )
            )
    result = {
        "checkpoint": str(frozen),
        "checkpoint_sha256": digest,
        "step": state["step"],
        "camera_sha256": hashlib.sha256(camera_bytes).hexdigest(),
        "hardware": torch.cuda.get_device_name(),
        "torch": str(torch.__version__),
        "shape": [4, 3, 512, 512],
        "levels": levels,
        "condition": condition,
        "branch_cuda_ms": timings,
        "median_branch_cuda_ms": {p: statistics.median(v) for p, v in timings.items()},
        "difference_rms": difference.square().mean().sqrt().item(),
        "difference_max_abs": difference.abs().max().item(),
        "difference_rms_uint16_codes": difference.square().mean().sqrt().item() * 65535,
        "metrics": metrics,
        "native_crops": crops,
        "timing_scope": "RGB correction only, captured Bayer/DINO decoder context; physical maps included. Two warmup calls per mode, alternating order; concurrent GPU work can affect event times. Not an idle or full-frame benchmark.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps({k: v for k, v in result.items() if k not in ("metrics", "native_crops")}),
        flush=True,
    )


if __name__ == "__main__":
    main()
