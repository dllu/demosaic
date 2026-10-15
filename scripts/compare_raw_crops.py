"""Compare specified private RAW crops locally without ground-truth claims.

Selection JSON: [{"source": "/read-only/photo.raf", "x": 0.2, "y": 0.3,
                  "size": 512, "display_exposure": 2.0}]
x/y give fractional top-left sensor coordinates; crops are snapped to even phase.
"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

from demosaic.cfa import bilinear, color_indices, malvar, pack
from demosaic.color import render
from demosaic.inference import load_checkpoint
from demosaic.io import read_raw
from demosaic.noise import Sensor
from demosaic.precision import amp_context
from demosaic.reference import load_rawnind
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selection", type=Path)
    parser.add_argument("checkpoint", nargs="+", type=Path)
    parser.add_argument("--rawnind", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    models, weights = [], []
    for path in args.checkpoint:
        frozen, digest = freeze_checkpoint(path, output / "weights")
        model, state = load_checkpoint(frozen, "cuda")
        label = f"{path.parent.name}, step {state['step']}"
        models.append((label, model, True))
        weights.append({"label": label, "source": str(path), "sha256": digest, "amp": "BF16"})
        del state
    if args.rawnind:
        models.insert(
            0,
            (
                "RawNIND CFA-LS",
                load_rawnind(args.rawnind, gain_mode="cfa-ls", device="cuda"),
                False,
            ),
        )
    selections = json.loads(args.selection.read_text())
    figure, axes = plt.subplots(
        len(selections),
        len(models) + 2,
        figsize=(4 * (len(models) + 2), 4 * len(selections)),
        squeeze=False,
    )
    records = []
    for row, selection in enumerate(selections):
        raw, metadata = read_raw(selection["source"])
        h, w = raw.shape
        size = selection.get("size", 512)
        y = min(h - size, int(h * selection["y"])) // 2 * 2
        x = min(w - size, int(w * selection["x"])) // 2 * 2
        crop = torch.from_numpy(raw[y : y + size, x : x + size].copy()).to("cuda")
        del raw
        colors = color_indices(metadata.pattern, device="cuda")[None]
        packed = pack(crop[None, None])
        # These priors are disclosed assumptions, not camera calibration.
        shot, read = Sensor(iso=metadata.iso or 100).coefficients()
        if ("shot" in selection) != ("read" in selection):
            raise ValueError("A crop noise override requires both shot and read")
        shot, read = selection.get("shot", shot), selection.get("read", read)
        variance = packed.clamp_min(0) * shot + read
        wb = torch.tensor(metadata.white_balance, device="cuda")[None]
        matrix = torch.tensor(metadata.camera_to_srgb, device="cuda")[None]
        images = [
            ("Bilinear", bilinear(packed, colors)),
            ("Malvar 2004, WB", malvar(packed, colors, wb)),
        ]
        for label, model, amp in models:
            with amp_context("cuda", amp):
                images.append((label, model(packed, variance, colors, wb, matrix)))
        for col, (label, rgb) in enumerate(images):
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
                **selection,
            }
        )
    figure.tight_layout()
    figure.savefig(output / "comparison.png", dpi=140)
    plt.close(figure)
    (output / "selection-and-metadata.json").write_text(json.dumps(records, indent=2) + "\n")
    (output / "checkpoints.json").write_text(json.dumps(weights, indent=2) + "\n")


if __name__ == "__main__":
    main()
