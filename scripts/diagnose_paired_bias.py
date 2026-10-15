"""Decompose real RAW center-crop error and test input-only gain correction.

This is a development diagnostic on one preselected center tile per noisy
capture, not the complete quality suite or an official-test score.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from demosaic.cfa import color_indices, mosaic, pack
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import amp_context
from demosaic.real_suite import measured_sensor_psnr
from demosaic.reference import load_rawnind, publisher_input_scale
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint, summarize


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--prepared", type=Path, nargs="+", required=True)
    parser.add_argument("--rawnind", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(4)
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    frozen, digest = freeze_checkpoint(args.checkpoint, output / "weights")
    model, state = load_checkpoint(frozen, "cuda")
    model.eval().to(memory_format=torch.channels_last)
    reference = load_rawnind(args.rawnind, gain_mode="cfa-ls", device="cuda")
    archive = output / "source"
    archive.mkdir(exist_ok=True)
    for path in [Path(__file__), *sorted(Path("src/demosaic").glob("*.py"))]:
        (archive / path.name).write_bytes(path.read_bytes())
    rows, details, manifests = [], [], []
    for path in args.prepared:
        payload = path.read_bytes()
        data = json.loads(payload)
        manifests.append({"path": str(path), "sha256": hashlib.sha256(payload).hexdigest()})
        for case in data["cases"]:
            crop = case["crops"][len(case["crops"]) // 2]
            crop_path = path.parent / crop["path"]
            if hashlib.sha256(crop_path.read_bytes()).hexdigest() != crop["sha256"]:
                raise ValueError("Prepared crop checksum mismatch")
            with np.load(crop_path, allow_pickle=False) as a:
                tensors = {
                    k: torch.from_numpy(a[k].copy())[None].cuda()
                    for k in ("raw", "reference_rgb", "sensor_reference", "sensor_mask")
                }
            packed = pack(tensors["raw"][:, None]).contiguous(memory_format=torch.channels_last)
            meta = case["metadata"]
            colors = color_indices(meta["pattern"], device="cuda")[None]
            wb = packed.new_tensor(meta["white_balance"])[None]
            matrix = packed.new_tensor(meta["camera_to_srgb"])[None]
            variance = (
                packed.clamp_min(0) * case["conditioning"]["shot"] + case["conditioning"]["read"]
            )
            adc = meta.get("adc_white_level")
            if adc is None:
                import rawpy

                with rawpy.imread(case["noisy"]["path"]) as decoder:
                    adc = float(decoder.white_level)
            reference.input_scale = packed.new_tensor(
                publisher_input_scale(meta["white_levels"], meta["black_levels"], adc)
            )
            with amp_context("cuda", dtype="float16"):
                prediction = model(packed, variance, colors, wb, matrix)
            with amp_context("cuda", dtype="float32"):
                baseline = reference(packed, variance, colors, wb, matrix)
            sampled = mosaic(prediction, colors)
            valid = (packed >= 0) & (packed < 0.98)
            products = sampled * packed * valid
            squares = sampled.square() * valid
            gain = products.sum() / squares.sum().clamp_min(1e-12)
            gains = torch.stack(
                [
                    (products * (colors == c)[..., None, None]).sum()
                    / (squares * (colors == c)[..., None, None]).sum().clamp_min(1e-12)
                    for c in range(3)
                ]
            )
            for label, rgb in [
                ("Model", prediction),
                ("Model:gain", prediction * gain),
                ("Model:channel-gain", prediction * gains[None, :, None, None]),
                ("RawNIND", baseline),
            ]:
                trim = (..., slice(32, -32), slice(32, -32))
                p, target, mask = (
                    rgb[trim],
                    tensors["sensor_reference"][trim],
                    tensors["sensor_mask"][trim].bool(),
                )
                error = p.clamp(0, 1) - target
                count = mask.sum((-2, -1)).clamp_min(1)
                bias = (error * mask).sum((-2, -1)) / count
                mse = (error.square() * mask).sum((-2, -1)) / count
                primary, _ = measured_sensor_psnr(p, target, mask)
                auxiliary = quality_metrics(p, tensors["reference_rgb"][trim], wb, matrix)
                metrics = {
                    "sensor_psnr": primary.item(),
                    "srgb_psnr": auxiliary["srgb_psnr"].item(),
                    "srgb_ssim": auxiliary["srgb_ssim"].item(),
                }
                rows.append(
                    {
                        "id": case["scene"],
                        "kind": "real-center",
                        "model": label,
                        "condition": case["noisy"]["sha256"],
                        "pattern": meta["pattern"],
                        "metrics": metrics,
                    }
                )
                details.append(
                    {
                        "scene": case["scene"],
                        "iso": meta.get("iso"),
                        "model": label,
                        "crop": crop,
                        "channel_bias": bias[0].tolist(),
                        "channel_mse": mse[0].tolist(),
                        "fraction_mse_from_channel_dc": (
                            bias.square().sum() / mse.sum().clamp_min(1e-12)
                        ).item(),
                        "input_only_global_gain": gain.item(),
                        "input_only_channel_gains": gains.tolist(),
                    }
                )
    result = {
        "checkpoint_sha256": digest,
        "checkpoint_step": state["step"],
        "checkpoint_run": state["config"]["run"],
        "rawnind_weight_sha256": hashlib.sha256(
            (args.rawnind / "utnet2-bayer.pt").read_bytes()
        ).hexdigest(),
        "precision": "Model float16; RawNIND and gains IEEE float32",
        "manifests": manifests,
        "protocol": __doc__,
        "details": details,
        **summarize(rows, comparison_metrics=("sensor_psnr", "srgb_psnr", "srgb_ssim")),
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for row in result["overall"]:
        print(row["model"], {k: v["mean"] for k, v in row["metrics"].items()})


if __name__ == "__main__":
    main()
