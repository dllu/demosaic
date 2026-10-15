"""Measure spatial scales of residual noise on exact synthetic flat targets.

Block-average error power is an orthogonal piecewise-constant projection, not a
photographic quality score. A spatially independent zero-mean residual has an
expected retained power of 1/k^2 after averaging k-by-k blocks.
"""

import argparse
import hashlib
import json
from pathlib import Path

import torch
from torch.nn import functional as F

from demosaic.cfa import malvar
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.reference import load_rawnind
from demosaic.reporting import center_crop, display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint, observation


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path, nargs="+")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--camera", type=Path, required=True, help="Cached read-only metadata receipt"
    )
    parser.add_argument("--rawnind", type=Path, required=True)
    args = parser.parse_args()
    torch.set_num_threads(4)
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "result.json").exists():
        raise ValueError("Choose a new diagnostic directory")
    source = output / "source"
    source.mkdir(exist_ok=True)
    for p in [Path(__file__), *sorted(Path("src/demosaic").glob("*.py"))]:
        (source / p.name).write_bytes(p.read_bytes())
    camera = json.loads(args.camera.read_text())
    meta = camera.get("raw", camera)
    levels = [0.002, 0.01, 0.05]
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
    for name in ("packed", "variance"):
        batch[name] = batch[name].contiguous(memory_format=torch.channels_last)
    noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
    predictions, models = [("Noisy:Malvar", noisy)], []
    for i, checkpoint in enumerate(args.checkpoint):
        frozen, digest = freeze_checkpoint(checkpoint, output / "weights")
        model, state = load_checkpoint(frozen, "cuda")
        model.eval().to(memory_format=torch.channels_last)
        label = f"{i}:{Path(state['config']['run']).name}:step-{state['step']}"
        with amp_context("cuda", dtype="float16"):
            prediction = model(
                *(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix"))
            )
        predictions.append((label, prediction))
        models.append(
            {
                "label": label,
                "step": state["step"],
                "sha256": digest,
                "snapshot": str(frozen),
                "model_config": model.config.to_dict(),
            }
        )
        del state, model
    reference = load_rawnind(args.rawnind, gain_mode="cfa-ls", device="cuda")
    with amp_context("cuda", dtype="float32"):
        predictions.append(
            (
                "RawNIND:CFA-LS",
                reference(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix"))),
            )
        )
    rows, crops = [], []
    for label, prediction in predictions:
        error = (prediction - batch["target"])[..., 64:-64, 64:-64].float()
        bias = error.mean((-2, -1), keepdim=True)
        centered = error - bias
        total = centered.square().mean((1, 2, 3))
        for i, level in enumerate(levels):
            row = {
                "model": label,
                "scene_level": level,
                "camera_mse": error.square().mean((1, 2, 3))[i].item(),
                "camera_abs_bias": bias.abs().mean((1, 2, 3))[i].item(),
                "camera_centered_sigma": total[i].sqrt().item(),
                "scales": [],
            }
            for side in [1, 2, 4, 8, 16, 32, 64, 128]:
                power = F.avg_pool2d(centered, side, side).square().mean((1, 2, 3))[i]
                row["scales"].append(
                    {
                        "block": side,
                        "centered_error_power": power.item(),
                        "retained_power_fraction": (power / total[i].clamp_min(1e-20)).item(),
                    }
                )
            rows.append(row)
        if label != "Noisy:Malvar":
            xywh = center_crop(prediction.shape)
            for i in [0, 1]:
                panels = [
                    (
                        name,
                        display_crop(
                            value[i : i + 1],
                            batch["wb"][i : i + 1],
                            batch["matrix"][i : i + 1],
                            xywh,
                            exposure=4,
                        ),
                    )
                    for name, value in [
                        ("Noisy (Malvar)", noisy),
                        ("Denoised", prediction),
                        ("GT (flat)", batch["target"]),
                    ]
                ]
                crops.append(
                    save_triplet(
                        output,
                        f"{label}:{i}",
                        panels,
                        caption=f"{label} / scene level {levels[i]} / +2 EV display",
                        metadata={
                            "xywh": xywh,
                            "scene_level": levels[i],
                            "model_label": label,
                            "display_exposure": 4.0,
                        },
                    )
                )
    result = {
        "protocol": __doc__,
        "condition": condition,
        "size": 512,
        "border": 64,
        "camera_metadata": meta,
        "camera_receipt_sha256": hashlib.sha256(args.camera.read_bytes()).hexdigest(),
        "models": models,
        "rows": rows,
        "native_crops": crops,
        "rawnind_sha256": hashlib.sha256(
            (args.rawnind / "utnet2-bayer.pt").read_bytes()
        ).hexdigest(),
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for row in rows:
        if row["scene_level"] == 0.01:
            print(
                row["model"],
                row["camera_centered_sigma"],
                [
                    (s["block"], s["retained_power_fraction"])
                    for s in row["scales"]
                    if s["block"] in (8, 32, 64)
                ],
            )


if __name__ == "__main__":
    main()
