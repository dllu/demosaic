"""Native photographic and larger procedural checks of the actual tiled serving path."""

import argparse
import hashlib
import json
import math
from itertools import pairwise
from pathlib import Path

import torch
import yaml

from demosaic.cfa import malvar, unpack
from demosaic.color import render
from demosaic.data import CleanDataset
from demosaic.inference import load_checkpoint, positions, restore_tiled
from demosaic.metrics import quality_metrics
from demosaic.precision import COMPUTE_DTYPES
from demosaic.prior import wiener_packed
from demosaic.reference import load_rawnind
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint, observation, summarize


def procedural_scenes(size, device):
    y, x = torch.meshgrid(
        torch.arange(size, device=device) / size,
        torch.arange(size, device=device) / size,
        indexing="ij",
    )
    chirp = 0.18 + 0.1 * torch.sin(2 * math.pi * (64 * x + 30 * y + 50 * x.square()))
    hdr = 0.03 + 3.5 * torch.sigmoid((0.075 - (x - 0.5).square() - (y - 0.5).square()) * 100)
    hdr = (hdr + 0.02 * torch.sin(2 * math.pi * (100 * x + 70 * y))).clamp_min(0)
    return {
        "flat-0.01": torch.full((1, 3, size, size), 0.01, device=device),
        "chirp": chirp[None, None].expand(1, 3, -1, -1),
        "clipped-disc": hdr[None, None].expand(1, 3, -1, -1),
    }


def join_mask(size, device):
    """Shared eight-pixel strips centered on overlap regions of the 256/64 grid."""
    mask = torch.zeros(size, size, device=device, dtype=torch.bool)
    starts = positions(size, 256, 192)
    for left, right in pairwise(starts):
        center = (left + 256 + right) // 2
        mask[center - 4 : center + 4] = True
        mask[:, center - 4 : center + 4] = True
    mask[:16] = False
    mask[-16:] = False
    mask[:, :16] = False
    mask[:, -16:] = False
    return mask


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation.yaml"))
    parser.add_argument(
        "--images", type=int, default=0, help="0 uses all eligible validation photos"
    )
    parser.add_argument("--synthetic-size", type=int, default=1024)
    parser.add_argument("--precision", choices=COMPUTE_DTYPES, default="float16")
    parser.add_argument("--rawnind", type=Path)
    args = parser.parse_args()
    if args.images < 0 or args.synthetic_size < 512 or args.synthetic_size % 16:
        raise ValueError("Image count must be nonnegative; synthetic size must be >=512 and /16")
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("high")
    manifest = args.manifest.read_bytes()
    selected = [
        r
        for line in manifest.splitlines()
        if (r := json.loads(line))["split"] == "val" and min(r["shape"][:2]) >= 512
    ]
    if args.images:
        selected = selected[: args.images]
    if not selected:
        raise ValueError("No validation images support native 512-pixel crops")
    selected_payload = "".join(json.dumps(r) + "\n" for r in selected)
    (output / "selected.jsonl").write_text(selected_payload)
    data = CleanDataset(
        args.manifest, split="val", patch_size=512, records=selected, native_crop=True
    )
    frozen, digest = freeze_checkpoint(args.checkpoint, output / "weights")
    model, state = load_checkpoint(frozen, "cuda")
    model.eval().to(memory_format=torch.channels_last)
    reference = (
        load_rawnind(args.rawnind, gain_mode="cfa-ls", device="cuda") if args.rawnind else None
    )
    protocol = yaml.safe_load(args.config.read_text())
    entries = [("photo", r["id"], i) for i, r in enumerate(selected)] + [
        ("synthetic", name, rgb)
        for name, rgb in procedural_scenes(args.synthetic_size, "cuda").items()
    ]
    rows = []
    with (output / "per-image.jsonl").open("w") as stream:
        for kind, identity, source in entries:
            rgb = data[source]["rgb"][None].cuda() if kind == "photo" else source
            size = rgb.shape[-1]
            shared_mask = join_mask(size, "cuda")
            for condition in protocol["conditions"]:
                for pattern in protocol["patterns"]:
                    batch = observation(
                        rgb,
                        [identity],
                        condition,
                        pattern,
                        protocol["white_balance"],
                        protocol["camera_to_srgb"],
                        protocol.get("seed", 42),
                    )
                    packed, variance, colors, wb, matrix = (
                        batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")
                    )
                    raw = unpack(packed)[0, 0].cpu()
                    truth = render(batch["target"], wb, matrix)
                    predictions = [
                        (
                            "Wiener7+Malvar2004:WB",
                            malvar(wiener_packed(packed, variance), colors, wb),
                        )
                    ]
                    if reference:
                        predictions.append(
                            ("RawNIND:CFA-LS", reference(packed, variance, colors, wb, matrix))
                        )
                    for tile in sorted({256, 512, size}):
                        prediction, _ = restore_tiled(
                            model,
                            raw,
                            colors[0],
                            shot=condition["shot"],
                            read=condition["read"],
                            tile=tile,
                            overlap=64,
                            batch_size=4,
                            device="cuda",
                            wb=wb[0],
                            matrix=matrix[0],
                            precision=args.precision,
                        )
                        predictions.append((f"tile-{tile}-overlap64", prediction[None].cuda()))
                    for label, prediction in predictions:
                        scores = quality_metrics(
                            prediction[:, :, 16:-16, 16:-16],
                            batch["target"][:, :, 16:-16, 16:-16],
                            wb,
                            matrix,
                        )
                        error = (render(prediction, wb, matrix) - truth).abs()
                        scores["shared_join_rgb_mae"] = error[:, :, shared_mask].mean()[None]
                        interior = error[:, :, 16:-16, 16:-16]
                        scores["shared_nonjoin_rgb_mae"] = interior[
                            :, :, ~shared_mask[16:-16, 16:-16]
                        ].mean()[None]
                        record = {
                            "id": identity,
                            "kind": kind,
                            "condition": condition["name"],
                            "pattern": pattern,
                            "model": label,
                            "metrics": {
                                k: float(v[0]) if torch.isfinite(v[0]) else None
                                for k, v in scores.items()
                            },
                        }
                        rows.append(record)
                        stream.write(json.dumps(record, allow_nan=False) + "\n")
            stream.flush()
            print(
                json.dumps({"event": "tiling", "kind": kind, "id": identity, "rows": len(rows)}),
                flush=True,
            )
    source_root = Path(__file__).resolve().parents[1] / "src/demosaic"
    archive = output / "source"
    archive.mkdir(parents=True, exist_ok=True)
    source_digest = hashlib.sha256()
    for path in [Path(__file__), *sorted(source_root.glob("*.py"))]:
        payload = path.read_bytes()
        source_digest.update(path.name.encode() + payload)
        (archive / path.name).write_bytes(payload)
    (archive / "manifest.jsonl").write_bytes(manifest)
    (archive / "protocol.yaml").write_bytes(args.config.read_bytes())
    result = {
        "format_version": 1,
        "checkpoint": str(frozen),
        "sha256": digest,
        "step": state["step"],
        "model_config": model.config.to_dict(),
        "protocol": protocol,
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "selected_manifest_sha256": hashlib.sha256(selected_payload.encode()).hexdigest(),
        "sources": len(selected),
        "synthetic_sources": 3,
        "photo_size": 512,
        "synthetic_size": args.synthetic_size,
        "border": 16,
        "precision": args.precision,
        "memory_format": "channels_last",
        "torch": str(torch.__version__),
        "source_sha256": source_digest.hexdigest(),
        "join_note": "Shared 8px strips at 256/64 overlap centers; scene texture also affects these errors. Single-tile predictions are not ground truth.",
        **summarize(rows),
    }
    if args.rawnind:
        result["rawnind_sha256"] = hashlib.sha256(
            (args.rawnind / "utnet2-bayer.pt").read_bytes()
        ).hexdigest()
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
