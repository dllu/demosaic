"""Fixed ADC-only CFA backprojection probe; no training or promotion."""

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

import torch
import yaml

from demosaic.cfa import malvar, mosaic
from demosaic.data import CleanDataset, synthetic
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import amp_context, ieee_fp32
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import observation, summarize

BASE = Path("/mnt/external/demosaic")
DEFAULT_OUTPUT = BASE / "evaluation/adc-cfa-projection-probe-v2"
DEFAULT_CHECKPOINT = BASE / "models/v43-step2000.pt"


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def adc_cfa_projection(prediction, packed, colors, wb):
    """Experimental noiseless-CFA correction; caller must supply ADC-only data.

    Near-black/clipped samples have zero residual. This preserves their measured
    channel predictions while allowing neighboring RGB interpolation to change.
    No target, fit, output clamp or noise-uncertainty claim is involved.
    """
    if packed.ndim != 4 or packed.shape[1] != 4:
        raise ValueError("Expected four packed CFA phases")
    if prediction.shape != (packed.shape[0], 3, packed.shape[2] * 2, packed.shape[3] * 2):
        raise ValueError("Prediction and CFA dimensions disagree")
    with torch.autocast(device_type=prediction.device.type, enabled=False), ieee_fp32():
        prediction, packed = prediction.float(), packed.float()
        valid = (packed > 1 / 65535) & (packed < 1 - 1 / 65535)
        residual = (packed - mosaic(prediction, colors)) * valid
        return prediction + malvar(residual, colors, wb)


@torch.inference_mode()
def main(output, checkpoint, protocol_path, *, device="cpu", precision="float32", limit_photos=8):
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    device = torch.device(device)
    if device.type == "cpu" and precision != "float32":
        raise ValueError("CPU probe uses FP32; compare CUDA policies separately")
    code = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    (output / "source").mkdir()
    for name, value in code.items():
        (output / "source" / name).write_bytes(value)
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    torch.set_num_threads(2)
    model, state = load_checkpoint(checkpoint, device)
    del state
    if device.type == "cuda":
        model.to(memory_format=torch.channels_last)
        torch.set_float32_matmul_precision("high")
        torch.backends.cudnn.benchmark = True
    model.eval().set_noise(0.0, 0.0)
    assert all(p.device.type == device.type for p in model.parameters())
    protocol = yaml.safe_load(Path(protocol_path).read_text())
    condition = next(c for c in protocol["conditions"] if c["name"] == "adc-only")
    assert condition["shot"] == condition["read"] == 0
    manifest = BASE / "evaluation/manifests/common-8192-44732-val-v1.jsonl"
    data = CleanDataset(manifest, split="val", patch_size=256, native_crop=True)
    assert len(data) == 427
    ids = [r["id"] for r in data.rows] + [f"synthetic-{i}" for i in range(16)]
    count = len(data) if limit_photos == 0 else min(limit_photos, len(data))
    selected = set(ids[:count] + ids[427:])
    rows, crops = [], []
    max_cfa_error = 0.0
    border = protocol.get("border", 8)
    trim = (slice(None), slice(None), slice(border, -border), slice(border, -border))
    for first in range(0, len(ids), 2):
        names = ids[first : first + 2]
        if not selected.intersection(names):
            continue
        rgb = torch.stack(
            [
                data[i]["rgb"] if i < 427 else synthetic(256, random.Random(1_000_000 + i - 427))
                for i in range(first, min(first + 2, len(ids)))
            ]
        ).to(device)
        for pattern in protocol["patterns"]:
            batch = observation(
                rgb,
                names,
                condition,
                pattern,
                protocol["white_balance"],
                protocol["camera_to_srgb"],
                protocol.get("seed", 42),
            )
            if device.type == "cuda":
                for field in ["packed", "variance"]:
                    batch[field] = batch[field].contiguous(memory_format=torch.channels_last)
            with amp_context(device, dtype=precision):
                original = model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                )
            assert torch.isfinite(original).all()
            corrected = adc_cfa_projection(original, batch["packed"], batch["colors"], batch["wb"])
            classical = malvar(batch["packed"], batch["colors"], batch["wb"])
            valid = (batch["packed"] > 1 / 65535) & (batch["packed"] < 1 - 1 / 65535)
            error = (mosaic(corrected, batch["colors"]) - batch["packed"]).abs()
            if valid.any():
                max_cfa_error = max(max_cfa_error, float(error[valid].max()))
            assert max_cfa_error < 2e-7
            torch.testing.assert_close(
                adc_cfa_projection(
                    original, mosaic(original, batch["colors"]), batch["colors"], batch["wb"]
                ),
                original,
                rtol=0,
                atol=0,
            )
            for label, prediction in [
                ("parent", original),
                ("ADC-MHC-backprojection", corrected),
                ("Malvar2004:WB", classical),
            ]:
                scores = quality_metrics(
                    prediction[trim], batch["target"][trim], batch["wb"], batch["matrix"]
                )
                for i, identity in enumerate(names):
                    if identity not in selected:
                        continue
                    rows.append(
                        {
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
                    )
                    if pattern == "RGGB" and identity in [*ids[:2], "synthetic-0", "synthetic-13"]:
                        noisy = classical
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
                                caption=f"{identity}/ADC-only/{label}",
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
                                    "checkpoint_sha256": sha(checkpoint),
                                    "policy": label,
                                    "reference": "Exact synthetic clean target; selected ADC-only development probe",
                                },
                            )
                        )
        print(json.dumps({"done": names, "cases": len(rows)}), flush=True)
    assert len(rows) == len(selected) * len(protocol["patterns"]) * 3
    assert len(crops) == (min(count, 2) + 2) * 3
    assert all(Path("src/demosaic", n).read_bytes() == v for n, v in code.items())
    result = {
        "scope": f"Fixed ADC-only probe: {count} photographs/all16 procedural sources, four CFAs. Parent reused within each case; {device}/{precision}. No real-noise validation, trained model, target fitting, parameter sweep or promotion.",
        "policy": "P+MHC(y-A(P)) at nonclipped CFA samples, using shared WB; clipped/near-black residuals zero. Proposed only when supplied shot=read=0; no noisy-case claim.",
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha(checkpoint),
        "manifest": str(manifest),
        "manifest_sha256": sha(manifest),
        "protocol": protocol,
        "device": str(device),
        "precision": precision,
        "photo_sources": count,
        "cases": len(rows),
        "native_crops": crops,
        "max_valid_cfa_error": max_cfa_error,
        **summarize(rows),
        "source_files": {n: hashlib.sha256(v).hexdigest() for n, v in code.items()},
        "driver_sha256": sha(__file__),
        "cuda_initialized": torch.cuda.is_initialized(),
    }
    if device.type == "cpu":
        assert not result["cuda_initialized"]
    (output / "per-case.jsonl").write_text(
        "".join(json.dumps(r, allow_nan=False) + "\n" for r in rows)
    )
    (output / "summary.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": "complete",
                "summary": str(output / "summary.json"),
                "max_valid_cfa_error": max_cfa_error,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--protocol", type=Path, default=Path("configs/evaluation.yaml"))
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument(
        "--precision", choices=["float32", "bfloat16", "float16"], default="float32"
    )
    parser.add_argument(
        "--limit-photos", type=int, default=8, help="0 selects all427 frozen validation photos"
    )
    args = parser.parse_args()
    if args.limit_photos < 0:
        parser.error("Photo limit must be nonnegative")
    main(
        args.output,
        args.checkpoint,
        args.protocol,
        device=args.device,
        precision=args.precision,
        limit_photos=args.limit_photos,
    )
