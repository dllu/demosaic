"""Physical clipping diagnostic with paired observations and boundary-ring scores."""

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

from demosaic.cfa import PATTERNS, bilinear, malvar
from demosaic.color import render
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import COMPUTE_DTYPES, amp_context
from demosaic.prior import wiener_packed
from demosaic.reference import load_rawnind
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint, observation


def scenes(device):
    y, x = torch.meshgrid(
        torch.linspace(-1, 1, 256, device=device),
        torch.linspace(-1, 1, 512, device=device),
        indexing="ij",
    )
    circle = 0.03 + 3.5 * torch.sigmoid((0.2 - x.square() - y.square()) * 60)
    circle = (circle + 0.04 * (70 * x + 90 * y).sin()).clamp_min(0)
    slant = 0.025 + 3.2 * torch.sigmoid((x + 0.43 * y) * 150)
    lamp = lambda cx, cy: torch.sigmoid((0.10 - (x - cx).square() - (y - cy).square()) * 100)
    colored = 0.025 + torch.stack(
        (3.5 * lamp(-0.2, 0.0), 2.2 * lamp(0.15, 0.10), 4.0 * lamp(0.1, -0.25))
    )
    sign = 0.12 + 2.4 * torch.sigmoid((0.5 - x.abs()) * 100) * torch.sigmoid((0.5 - y.abs()) * 100)
    sign = (sign - 0.16 * (180 * x + 60 * y).cos()).clamp_min(0)
    return {
        "neutral-circle": circle[None, None].expand(1, 3, -1, -1),
        "neutral-slanted-edge": slant[None, None].expand(1, 3, -1, -1),
        "colored-emission": colored[None],
        "fine-detail-sign": sign[None, None].expand(1, 3, -1, -1),
    }


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", nargs="+", type=Path)
    parser.add_argument("--rawnind", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--precision", choices=COMPUTE_DTYPES, default="bfloat16")
    args = parser.parse_args()
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    device = torch.device(args.device)
    models, weights = [], []
    for path in args.checkpoint:
        frozen, digest = freeze_checkpoint(path, output / "weights")
        model, state = load_checkpoint(frozen, device)
        model.eval()
        if device.type == "cuda":
            model.to(memory_format=torch.channels_last)
        label = f"{Path(state.get('config', {}).get('run', path.parent)).name}:step-{state['step']}"
        models.append((label, model, True))
        weights.append(
            {
                "label": label,
                "sha256": digest,
                "snapshot": str(frozen),
                "model_config": model.config.to_dict(),
            }
        )
        del state
    if args.rawnind:
        models.insert(
            0,
            (
                "RawNIND:CFA-LS",
                load_rawnind(args.rawnind, gain_mode="cfa-ls", device=device),
                False,
            ),
        )
        weights.append(
            {
                "label": "RawNIND:CFA-LS",
                "sha256": hashlib.sha256(
                    (args.rawnind / "utnet2-bayer.pt").read_bytes()
                ).hexdigest(),
            }
        )
    matrix = [
        [1.1176470588, -0.0588235294, -0.0588235294],
        [-0.0588235294, 1.1176470588, -0.0588235294],
        [-0.0588235294, -0.0588235294, 1.1176470588],
    ]
    balances = [[2.0, 1.0, 1.5], [1.2, 1.0, 2.4]]
    condition = {"name": "physical-clipping", "shot": 0.00002, "read": 1.6e-9, "exposure": 1.0}
    rows, panels = [], {}
    for name, rgb in scenes(device).items():
        for wb_index, wb in enumerate(balances):
            for pattern in PATTERNS:
                batch = observation(
                    rgb, [f"{name}:wb-{wb_index}"], condition, pattern, wb, matrix, 7
                )
                if device.type == "cuda":
                    for key in ("packed", "variance"):
                        batch[key] = batch[key].contiguous(memory_format=torch.channels_last)
                packed, variance, colors, balance, transform = (
                    batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")
                )
                predictions = [
                    ("Bilinear", bilinear(packed, colors)),
                    ("Malvar2004:WB", malvar(packed, colors, balance)),
                    (
                        "Wiener7+Malvar2004:WB",
                        malvar(wiener_packed(packed, variance), colors, balance),
                    ),
                ]
                for label, model, amp in models:
                    with amp_context(device, amp, dtype=args.precision):
                        prediction = model(packed, variance, colors, balance, transform)
                    predictions.append((label, prediction))
                for label, prediction in predictions:
                    scores = quality_metrics(
                        prediction[:, :, 8:-8, 8:-8],
                        batch["target"][:, :, 8:-8, 8:-8],
                        balance,
                        transform,
                    )
                    rows.append(
                        {
                            "scene": name,
                            "white_balance": wb,
                            "pattern": pattern,
                            "model": label,
                            "metrics": {
                                k: float(v[0]) if torch.isfinite(v[0]) else None
                                for k, v in scores.items()
                            },
                        }
                    )
                if wb_index == 0 and pattern == "RGGB":
                    panels[name] = [
                        ("Reference", render(batch["target"], balance, transform).cpu())
                    ] + [
                        (label, render(prediction, balance, transform).cpu())
                        for label, prediction in predictions
                    ]
    figure, axes = plt.subplots(
        len(panels),
        len(next(iter(panels.values()))),
        figsize=(4 * len(next(iter(panels.values()))), 3.2 * len(panels)),
        squeeze=False,
    )
    for row, (name, images) in enumerate(panels.items()):
        for col, (label, display) in enumerate(images):
            axes[row, col].imshow(display[0].permute(1, 2, 0).numpy())
            axes[row, col].set_title(name + " / " + label, fontsize=8)
            axes[row, col].axis("off")
    figure.tight_layout()
    figure.savefig(output / "highlights.png", dpi=140)
    plt.close(figure)
    source = Path(__file__).read_bytes()
    (output / "diagnose_highlights.py").write_bytes(source)
    means = {}
    for label in sorted({r["model"] for r in rows}):
        cases = [r for r in rows if r["model"] == label]
        means[label] = {
            k: sum(r["metrics"][k] for r in cases) / len(cases)
            for k in (
                "srgb_psnr",
                "srgb_ssim",
                "highlight_boundary_chroma_mae",
                "highlight_boundary_rgb_mae",
            )
        }
    result = {
        "format_version": 2,
        "checkpoint_records": weights,
        "cases_per_model": 32,
        "seed": 7,
        "condition": condition,
        "camera_to_srgb": matrix,
        "white_balances": balances,
        "compute_precision": args.precision if device.type == "cuda" else "float32",
        "memory_format": "channels_last" if device.type == "cuda" else "contiguous",
        "torch": str(torch.__version__),
        "border": 8,
        "adc_black": 0.03,
        "adc_bits": 16,
        "script_sha256": hashlib.sha256(source).hexdigest(),
        "overall": means,
        "cases": rows,
    }
    (output / "metrics.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps(means, indent=2), flush=True)


if __name__ == "__main__":
    main()
