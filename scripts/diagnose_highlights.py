"""Controlled physical-clipping diagnostic; run with uv run --extra eval."""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch
from torch.nn import functional as F

from demosaic.cfa import bilinear, color_indices, mosaic
from demosaic.color import render
from demosaic.data import camera_pair
from demosaic.inference import load_checkpoint
from demosaic.losses import psnr
from demosaic.noise import add_noise
from demosaic.safety import writable_path


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    device = torch.device(args.device)
    y, x = torch.meshgrid(
        torch.linspace(-1, 1, 256, device=device),
        torch.linspace(-1, 1, 512, device=device),
        indexing="ij",
    )
    scene = 0.03 + 3.5 * torch.sigmoid((0.2 - x.square() - y.square()) * 60)
    scene = (scene + 0.04 * (70 * x + 90 * y).sin()).clamp_min(0)
    scene = scene[None, None].expand(1, 3, -1, -1)
    wb = torch.tensor([[2.0, 1.0, 1.5]], device=device)
    inverse = torch.tensor(
        [[[0.9, 0.05, 0.05], [0.05, 0.9, 0.05], [0.05, 0.05, 0.9]]], device=device
    )
    matrix = torch.linalg.inv(inverse)
    clean, target = camera_pair(scene, inverse, wb, reconstruct_highlights=True)
    colors = color_indices("RGGB", device=device)[None]
    packed = add_noise(
        mosaic(clean, colors),
        0.00002,
        1.6e-9,
        generator=torch.Generator(device=device).manual_seed(7),
    )
    variance = packed.clamp_min(0) * 0.00002 + 1.6e-9
    truth = render(target, wb, matrix)
    mask = F.max_pool2d((scene[:, :1] > 0.9).float(), 7, 1, 3)
    panels = [
        ("Reference", truth),
        ("Noisy bilinear", render(bilinear(packed, colors), wb, matrix)),
    ]
    for path in args.checkpoint:
        model, checkpoint = load_checkpoint(path, device)
        display = render(model(packed, variance, colors, wb, matrix), wb, matrix)
        panels.append((f"{path.parent.name} step {checkpoint.get('step')}", display))
        del model
    scores = {}
    figure, axes = plt.subplots(
        len(panels), 2, figsize=(12, 3 * len(panels)), gridspec_kw={"width_ratios": [2, 1]}
    )
    for row, (label, display) in enumerate(panels):
        error = display - truth
        chroma = error - error.mean(1, keepdim=True)
        scores[label] = {
            "rendered_psnr": float(psnr(display, truth).mean()),
            "highlight_chroma_mae": float((chroma.abs() * mask).sum() / (3 * mask.sum())),
            "highlight_rgb_mae": float((error.abs() * mask).sum() / (3 * mask.sum())),
        }
        axes[row, 0].imshow(display[0].permute(1, 2, 0).cpu().numpy())
        axes[row, 0].set_title(label)
        axes[row, 0].axis("off")
        for channel, color in enumerate(("r", "g", "b")):
            axes[row, 1].plot(display[0, channel, 128].cpu().numpy(), color=color)
        axes[row, 1].set_ylim(-0.05, 1.05)
        axes[row, 1].set_title("RGB across highlight center")
    figure.tight_layout()
    figure.savefig(output / "highlights.png", dpi=140)
    plt.close(figure)
    (output / "metrics.json").write_text(json.dumps(scores, indent=2) + "\n")
    print(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
