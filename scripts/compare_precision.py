"""Matched BF16/FP16/FP32 inference and fine-contrast response diagnostic."""

import argparse
import hashlib
import json
import math
from pathlib import Path

import torch
import yaml

from demosaic.cfa import malvar
from demosaic.data import CleanDataset
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import COMPUTE_DTYPES, amp_context, ieee_fp32
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint, observation, summarize


@torch.inference_mode()
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkpoint", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--config", type=Path, default=Path("configs/evaluation.yaml"))
    parser.add_argument("--images", type=int, default=16)
    parser.add_argument("--batch-size", type=int, default=4)
    args = parser.parse_args()
    if args.images < 1 or args.batch_size < 1:
        raise ValueError("Image and batch counts must be positive")
    output = writable_path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    frozen, digest = freeze_checkpoint(args.checkpoint, output / "weights")
    model, state = load_checkpoint(frozen, "cuda")
    model.eval().to(memory_format=torch.channels_last)
    protocol = yaml.safe_load(args.config.read_text())
    manifest = args.manifest.read_bytes()
    data = CleanDataset(
        args.manifest,
        split="val",
        native_crop=True,
        records=[json.loads(line) for line in manifest.splitlines()],
    )
    count, rows = min(args.images, len(data)), []
    if not count:
        raise ValueError("Validation split is empty")
    border = protocol.get("border", 8)
    region = (..., slice(border, -border), slice(border, -border)) if border else (...,)
    with ieee_fp32():
        for start in range(0, count, args.batch_size):
            indices = range(start, min(start + args.batch_size, count))
            rgb = torch.stack([data[i]["rgb"] for i in indices]).cuda()
            identities = [data.rows[i]["id"] for i in indices]
            for condition in protocol["conditions"]:
                batch = observation(
                    rgb,
                    identities,
                    condition,
                    "RGGB",
                    protocol["white_balance"],
                    protocol["camera_to_srgb"],
                    protocol.get("seed", 42),
                )
                for key in ("packed", "variance"):
                    batch[key] = batch[key].contiguous(memory_format=torch.channels_last)
                for precision in COMPUTE_DTYPES:
                    with amp_context("cuda", dtype=precision):
                        prediction = model(
                            batch["packed"],
                            batch["variance"],
                            batch["colors"],
                            batch["wb"],
                            batch["matrix"],
                        )
                    metrics = quality_metrics(
                        prediction[region],
                        batch["target"][region],
                        batch["wb"],
                        batch["matrix"],
                    )
                    for i, identity in enumerate(identities):
                        rows.append(
                            {
                                "id": identity,
                                "kind": "photo",
                                "condition": condition["name"],
                                "pattern": "RGGB",
                                "model": precision,
                                "metrics": {
                                    k: float(v[i]) if torch.isfinite(v[i]) else None
                                    for k, v in metrics.items()
                                },
                            }
                        )
        # An ADC-only neutral sinusoid tests whether neural corrections respond
        # to fine contrasts. Response is not a measure of reconstruction accuracy.
        axis = torch.arange(256, device="cuda")[None, :].expand(256, -1)
        wave = (2 * math.pi * axis * 0.2).sin()[None, None]
        amplitudes = [0, 4, 16, 64, 256]
        rgb = torch.cat([(0.5 + wave * (a / 65535)).expand(1, 3, -1, -1) for a in amplitudes])
        condition = {"name": "low-contrast", "shot": 0.0, "read": 0.0, "exposure": 1.0}
        batch = observation(
            rgb,
            list(map(str, amplitudes)),
            condition,
            "RGGB",
            protocol["white_balance"],
            protocol["camera_to_srgb"],
            protocol.get("seed", 42),
        )
        for key in ("packed", "variance"):
            batch[key] = batch[key].contiguous(memory_format=torch.channels_last)
        baseline = malvar(batch["packed"], batch["colors"], batch["wb"])
        response = []
        for precision in COMPUTE_DTYPES:
            with amp_context("cuda", dtype=precision):
                prediction = model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                )
            correction = prediction - baseline
            for i, amplitude in enumerate(amplitudes):
                change = correction[i, :, 32:-32, 32:-32] - correction[0, :, 32:-32, 32:-32]
                response.append(
                    {
                        "compute_precision": precision,
                        "wave_amplitude_dn16": amplitude,
                        "correction_response_rms": float(change.square().mean().sqrt()),
                    }
                )
    result = {
        "checkpoint": str(frozen),
        "sha256": digest,
        "step": state["step"],
        "model_config": model.config.to_dict(),
        "protocol": protocol,
        "sources": count,
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
        "pattern": "RGGB",
        "patch_size": 256,
        "memory_format": "channels_last",
        "global_ieee_fp32": True,
        "torch": str(torch.__version__),
        "low_contrast_response": response,
        "response_note": "Learned correction relative to Malvar, not an accuracy score.",
        "cases": rows,
        **summarize(rows),
    }
    # Archive both this experiment and the imported implementation for replay.
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
    result["source_sha256"] = source_digest.hexdigest()
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    for group in result["overall"]:
        print(
            group["model"],
            {k: group["metrics"][k]["mean"] for k in ("linear_psnr", "srgb_psnr", "srgb_ssim")},
            flush=True,
        )


if __name__ == "__main__":
    main()
