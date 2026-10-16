"""Fixed-parameter diagnostic on eight photos and all sixteen procedural sources."""

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

import psutil
import torch
import yaml
from torch.nn import functional as F

from demosaic.cfa import malvar, mosaic
from demosaic.data import CleanDataset, synthetic
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import amp_context, ieee_fp32
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import observation, summarize


def box_sum(values, window):
    """Zero-extended box sums with FP64 accumulation and no synthetic samples."""
    if type(window) is not int or window < 3 or window % 2 != 1:
        raise ValueError("Consistency window must be an odd integer >=3")
    radius = window // 2
    integral = F.pad(values.double(), (radius, radius, radius, radius))
    integral = F.pad(integral.cumsum(-2).cumsum(-1), (1, 0, 1, 0))
    return (
        integral[..., window:, window:]
        - integral[..., :-window, window:]
        - integral[..., window:, :-window]
        + integral[..., :-window, :-window]
    )


def cfa_mean_consistency(rgb, packed, variance, colors, *, window=63, threshold=3.0):
    """Soft-threshold local per-color measured residual means in sensor space.

    The threshold uses the supplied independent input-noise mean variance. It is
    a heuristic scale, not a confidence interval for correlated model residuals.
    Samples near ADC clipping are excluded using both observations and model
    predictions. No output clamp, target fitting or reference image is used.
    """
    if threshold < 0 or not torch.isfinite(torch.tensor(threshold)):
        raise ValueError("Consistency threshold must be finite and nonnegative")
    if packed.ndim != 4 or packed.shape[1] != 4 or variance.shape != packed.shape:
        raise ValueError("Expected four packed phases and matching variance")
    batch, _, height, width = packed.shape
    if rgb.shape != (batch, 3, 2 * height, 2 * width):
        raise ValueError("RGB shape does not match packed CFA")
    with torch.autocast(device_type=rgb.device.type, enabled=False), ieee_fp32():
        rgb, packed, variance = rgb.float(), packed.float(), variance.float()
        predicted = mosaic(rgb, colors)
        margin = 4 * variance.clamp_min(0).sqrt() + 1 / 65535
        valid = (predicted > margin) & (predicted < 1 - margin)
        valid &= (packed > 0) & (packed < 1)
        if colors.ndim == 1:
            colors = colors[None].expand(batch, -1)
        labels = F.one_hot(colors, 3).permute(0, 2, 1)[..., None, None]

        def scatter(values):
            return F.pixel_shuffle((values[:, None] * labels).reshape(batch, 12, height, width), 2)

        residual = scatter((packed - predicted) * valid)
        counts = scatter(valid.float())
        noise = scatter(variance.clamp_min(0) * valid)
        summed = box_sum(torch.cat((residual, counts, noise), dim=1), window)
        residual_sum, count, variance_sum = summed.chunk(3, dim=1)
        denominator = count.clamp_min(1)
        mean = residual_sum / denominator
        scale = variance_sum.clamp_min(0).sqrt() / denominator
        correction = mean.sign() * (mean.abs() - threshold * scale).clamp_min(0)
        # Avoid painting a neighboring correction into clipped/predicted HDR regions.
        dense_margin = 1 / 65535
        eligible = (rgb > dense_margin) & (rgb < 1 - dense_margin)
        correction = torch.where((count > 0) & eligible, correction, 0)
        return rgb + correction.float()


BASE = Path("/mnt/external/demosaic")
DEFAULT_OUTPUT = BASE / "evaluation/cfa-mean-consistency-probe-v1"
PARENT = BASE / "models/v43-step2000.pt"


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


@torch.inference_mode()
def main(output):
    output = writable_path(output)
    assert not output.exists()
    assert psutil.virtual_memory().available / 1e9 > 24
    assert sha(PARENT) == "0d74cf31fb1c7e3f97fc692c855a2ca0ee3ebf562b454e4f8b135c28fc0aa5c5"
    output.mkdir()
    code = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    (output / "source").mkdir()
    for name, payload in code.items():
        (output / "source" / name).write_bytes(payload)
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    protocol = yaml.safe_load(Path("configs/evaluation.yaml").read_text())
    manifest = BASE / "evaluation/manifests/common-8192-44732-val-v1.jsonl"
    data = CleanDataset(manifest, split="val", patch_size=256, native_crop=True)
    assert len(data) == 427
    torch.set_num_threads(2)
    torch.set_float32_matmul_precision("high")
    torch.backends.cudnn.benchmark = True
    model, checkpoint = load_checkpoint(PARENT)
    del checkpoint
    model = model.eval().cuda().to(memory_format=torch.channels_last)
    identities = [r["id"] for r in data.rows] + [f"synthetic-{i}" for i in range(16)]
    selected = set(identities[:8] + identities[427:])
    rows, crops = [], []
    border = protocol.get("border", 8)
    trim = (slice(None), slice(None), slice(border, -border), slice(border, -border))
    for first in range(0, len(identities), 2):
        ids = identities[first : first + 2]
        if not selected.intersection(ids):
            continue
        rgb = torch.stack(
            [
                data[i]["rgb"] if i < 427 else synthetic(256, random.Random(1_000_000 + i - 427))
                for i in range(first, min(first + 2, len(identities)))
            ]
        ).cuda()
        for condition in protocol["conditions"]:
            for pattern in protocol["patterns"]:
                batch = observation(
                    rgb,
                    ids,
                    condition,
                    pattern,
                    protocol["white_balance"],
                    protocol["camera_to_srgb"],
                    protocol.get("seed", 42),
                )
                model.set_noise(condition["shot"], condition["read"])
                with amp_context("cuda", dtype="float16"):
                    original = model(
                        batch["packed"],
                        batch["variance"],
                        batch["colors"],
                        batch["wb"],
                        batch["matrix"],
                    )
                    corrected = cfa_mean_consistency(
                        original,
                        batch["packed"],
                        batch["variance"],
                        batch["colors"],
                        window=63,
                        threshold=3,
                    )
                for label, prediction in [
                    ("parent", original),
                    ("local-CFA-mean-w63-sigma3", corrected),
                ]:
                    scores = quality_metrics(
                        prediction[trim], batch["target"][trim], batch["wb"], batch["matrix"]
                    )
                    for i, identity in enumerate(ids):
                        if identity not in selected:
                            continue
                        row = {
                            "id": identity,
                            "kind": "synthetic" if identity.startswith("synthetic-") else "photo",
                            "condition": condition["name"],
                            "pattern": pattern,
                            "model": label,
                            "metrics": {
                                k: float(v[i]) if math.isfinite(float(v[i])) else None
                                for k, v in scores.items()
                            },
                        }
                        rows.append(row)
                        chosen = (
                            identity in ["synthetic-0", "synthetic-13"]
                            and condition["name"] == "adc-only"
                        ) or (identity in identities[:2] and condition["name"] == "iso12800-prior")
                        if chosen and pattern == "RGGB":
                            noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
                            panels = [
                                (
                                    name,
                                    display_crop(
                                        value[i : i + 1],
                                        batch["wb"][i : i + 1],
                                        batch["matrix"][i : i + 1],
                                        [48, 48, 160, 160],
                                    ),
                                )
                                for name, value in [
                                    ("Noisy (Malvar)", noisy),
                                    ("Restored", prediction),
                                    ("GT (synthetic)", batch["target"]),
                                ]
                            ]
                            crops.append(
                                save_triplet(
                                    output,
                                    f"{identity}:{label}",
                                    panels,
                                    caption=f"{identity}/{condition['name']}/{label}",
                                    metadata={
                                        "source_id": identity,
                                        "source": data.rows[first + i]
                                        if first + i < 427
                                        else {"generation_seed": 1_000_000 + first + i - 427},
                                        "evaluation_tile_xywh": [48, 48, 160, 160],
                                        "condition": condition,
                                        "pattern": pattern,
                                        "white_balance": protocol["white_balance"],
                                        "camera_to_srgb": protocol["camera_to_srgb"],
                                        "display_exposure": 1.0,
                                        "parent_checkpoint_sha256": sha(PARENT),
                                        "policy": label,
                                        "reference": "Exact synthetic clean target; development diagnostic only",
                                    },
                                )
                            )
        print(json.dumps({"processed": ids, "cases": len(rows)}), flush=True)
    assert len(rows) == 1344 and len(crops) == 8
    for name, payload in code.items():
        assert Path("src/demosaic", name).read_bytes() == payload
    (output / "per-case.jsonl").write_text(
        "".join(json.dumps(r, allow_nan=False) + "\n" for r in rows)
    )
    summary = {
        "scope": "Development probe only: first8 protocol photos and all16 procedural sources. Fixed window63/threshold3 chosen before scores, no parameter sweep, no reference fitting. Not a full suite, trained model, real-photo validation or promoted method.",
        "parent_checkpoint_sha256": sha(PARENT),
        "manifest": str(manifest),
        "manifest_sha256": sha(manifest),
        "protocol": protocol,
        "policy": {
            "window": 63,
            "threshold": 3,
            "accumulation": "float64",
            "sensor_arithmetic": "float32",
        },
        "native_crops": crops,
        "cases": len(rows),
        "sources": len(selected),
        **summarize(rows),
        "source_sha256": {n: hashlib.sha256(b).hexdigest() for n, b in code.items()},
        "driver_sha256": sha(__file__),
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": "complete", "summary": str(output / "summary.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    main(parser.parse_args().output)
