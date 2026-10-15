"""Measure flat-field bias and retained noise; not a photographic quality score."""

import argparse
import hashlib
import json
from pathlib import Path

import torch
import yaml

from demosaic.cfa import bilinear
from demosaic.inference import load_checkpoint
from demosaic.precision import COMPUTE_DTYPES, amp_context
from demosaic.reference import load_rawnind
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint, observation


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--rawnind", type=Path)
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation.yaml"))
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--border", type=int, default=32)
    parser.add_argument("--precision", choices=COMPUTE_DTYPES, default="bfloat16")
    args = parser.parse_args()
    if args.size < 64 or args.size % 16 or not 0 <= args.border < args.size // 2:
        raise ValueError("Use a size divisible by 16 and a border smaller than half the size")
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    protocol = yaml.safe_load(args.config.read_text())
    models, provenance = [], []
    for i, path in enumerate(args.checkpoint):
        frozen, digest = freeze_checkpoint(path, output / "weights")
        model, state = load_checkpoint(frozen, "cuda")
        run_name = Path(state.get("config", {}).get("run", path.parent)).name
        label = f"{i}:{run_name}:step-{state['step']}"
        model.to(memory_format=torch.channels_last)
        models.append((label, model.eval(), True))
        provenance.append(
            {
                "label": label,
                "sha256": digest,
                "config": model.config.to_dict(),
                "training_run": state.get("config", {}).get("run"),
                "snapshot": str(frozen),
                "compute_precision": args.precision,
                "memory_format": "channels_last",
            }
        )
        del state
    if args.rawnind:
        models.append(
            ("RawNIND:CFA-LS", load_rawnind(args.rawnind, gain_mode="cfa-ls", device="cuda"), False)
        )
        provenance.append(
            {
                "label": "RawNIND:CFA-LS",
                "gain": "observed-CFA-least-squares",
                "sha256": hashlib.sha256(
                    (args.rawnind / "utnet2-bayer.pt").read_bytes()
                ).hexdigest(),
            }
        )
    levels = [0.001, 0.01, 0.1, 0.5]
    rgb = torch.tensor(levels, device="cuda")[:, None, None, None].expand(
        -1, 3, args.size, args.size
    )
    rows = []
    for condition in protocol["conditions"]:
        batch = observation(
            rgb,
            [f"flat-{level}" for level in levels],
            condition,
            "RGGB",
            protocol["white_balance"],
            protocol["camera_to_srgb"],
            protocol.get("seed", 42),
        )
        for key in ("packed", "variance"):
            batch[key] = batch[key].contiguous(memory_format=torch.channels_last)
        predictions = [("Bilinear", bilinear(batch["packed"], batch["colors"]))]
        for label, model, amp in models:
            with amp_context("cuda", amp, dtype=args.precision):
                predictions.append(
                    (
                        label,
                        model(
                            batch["packed"],
                            batch["variance"],
                            batch["colors"],
                            batch["wb"],
                            batch["matrix"],
                        ),
                    )
                )
        border = args.border
        region = (..., slice(border, -border), slice(border, -border)) if border else (...,)
        baseline_sigma = predictions[0][1][region].flatten(2).std(-1).mean(1)
        for label, prediction in predictions:
            error = (prediction - batch["target"])[region].float().flatten(2)
            bias = error.mean(-1).abs().mean(1)
            sigma = error.std(-1).mean(1)
            psnr = -10 * error.square().mean((1, 2)).clamp_min(1e-12).log10()
            for i, level in enumerate(levels):
                rows.append(
                    {
                        "model": label,
                        "condition": condition["name"],
                        "scene_level": level,
                        "camera_abs_bias": bias[i].item(),
                        "unclamped_camera_psnr": psnr[i].item(),
                        "camera_sigma": sigma[i].item(),
                        "retained_sigma_fraction": (sigma[i] / baseline_sigma[i]).item()
                        if baseline_sigma[i] > 1e-9
                        else None,
                    }
                )
    result = {
        "protocol": protocol,
        "models": provenance,
        "size": args.size,
        "border": args.border,
        "pattern": "RGGB",
        "cases": rows,
        "note": "Constant scene-linear RGB. Measures bias/noise suppression, not detail fidelity.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(str(output / "result.json"))


if __name__ == "__main__":
    main()
