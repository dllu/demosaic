"""Check a saved experimental RAW-head EMA on CPU, without further training."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


@torch.inference_mode()
def main(checkpoint, output):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    output = writable_path(output)
    assert not output.exists()
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert state["model_config"]["raw_kernel_reconstruction"]
    source = Path(__file__).resolve().parents[1] / "src/demosaic"
    for path in source.glob("*.py"):
        assert sha(path) == sha(Path(state["config"]["source_snapshot"]) / path.name)
    manual = JointDemosaic(ModelConfig.from_checkpoint(state["model_config"]))
    loaded = manual.load_state_dict(state["ema"], strict=False)
    assert not loaded.unexpected_keys and all(
        k.startswith("context.backbone.") for k in loaded.missing_keys
    )
    portable, _ = load_checkpoint(checkpoint, "cpu")
    for model in [manual, portable]:
        model.eval()
        if state["config"].get("channels_last"):
            model.to(memory_format=torch.channels_last)
    a, b = manual.state_dict(), portable.state_dict()
    assert a.keys() == b.keys() and all(torch.equal(a[k], b[k]) for k in a)
    output.mkdir(parents=True, exist_ok=False)
    observations = Path("/mnt/external/demosaic/evaluation/two-fixed-examples-v43-none10k-cpu-v1")
    photos = []
    for i in range(2):
        path = observations / f"observation-{i}-cpu.npz"
        with np.load(path, allow_pickle=False) as data:
            batch = {
                k: torch.from_numpy(data[k].copy())
                for k in ["packed", "variance", "colors", "wb", "matrix"]
            }
        predictions = []
        for model in [manual, portable]:
            model.set_noise(0.00256, 0.0000262144)
            predictions.append(
                model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                )
            )
        assert torch.equal(*predictions) and torch.isfinite(predictions[0]).all()
        saved = output / f"portable-photo-{i}-f32.npy"
        np.save(saved, predictions[0].numpy(), allow_pickle=False)
        photos.append(
            {
                "source": str(path),
                "source_sha256": sha(path),
                "prediction": str(saved),
                "prediction_sha256": sha(saved),
                "exact_manual_vs_portable_EMA": True,
            }
        )
    palette = torch.tensor([[0.02, 0.18, 0.9], [1.4, -0.02, 0.00001], [0, 0, 0], [0.9, 0.2, 0.1]])
    colors = torch.stack([color_indices(p) for p in PATTERNS]).repeat_interleave(4, 0)
    target = palette.repeat(4, 1)[..., None, None].expand(-1, -1, 64, 64)
    raw = mosaic(target, colors)
    wb = torch.tensor([2.0, 1.0, 1.5])[None].expand(16, -1)
    matrix = torch.eye(3)[None].expand(16, -1, -1)
    cases = []
    for shot, read in [(0.0, 0.0), (0.00256, 0.0000262144)]:
        portable.set_noise(shot, read)
        for precision in ["float32", "bfloat16"]:
            with torch.autocast("cpu", dtype=torch.bfloat16, enabled=precision == "bfloat16"):
                restored = portable(raw, raw.clamp_min(0) * shot + read, colors, wb, matrix)
            error = float((restored - target).abs().max())
            assert (
                restored.dtype == torch.float32 and torch.isfinite(restored).all() and error <= 3e-7
            )
            cases.append(
                {
                    "conditioning": {"shot": shot, "read": read},
                    "CPU_autocast": precision,
                    "clean_constant_fields": 16,
                    "max_absolute_error": error,
                }
            )
    result = {
        "status": "completed-saved-CPU-EMA-portability-and-constant-field-check",
        "checkpoint": str(checkpoint),
        "checkpoint_sha256": sha(checkpoint),
        "all_manual_and_portable_tensors_including_DINO_backbone_exact": True,
        "photo_predictions": photos,
        "constant_field_cases": cases,
        "constant_RGBs": palette.tolist(),
        "CFA_patterns": list(PATTERNS),
        "total_clean_constant_cases": 64,
        "CUDA_initialized": torch.cuda.is_initialized(),
        "driver_sha256": sha(__file__),
        "scope": "Saved discarded4-update EMA, no training or GPU.64clean analytic fields, all CFA/color combinations, two conditioning profiles/two CPU precisions. Includes numerical negative/above-white range tests. Noise is not added to these fields; this does not establish unbiased noisy outputs or restoration quality. Two natural photos compare identical EMA implementations, not quality against GT.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(
        json.dumps({"receipt": str(output / "receipt.json"), "clean_constant_cases": 64}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
