"""Freeze local photo/RAW fixtures for an inference-only compilation benchmark."""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.io import read_raw
from demosaic.noise import add_noise, variance_map
from demosaic.safety import writable_path

BASE = Path("/mnt/external/demosaic")
REPO = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def main(output, photo_folder, gfx_report):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2)
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    files, photos = {}, []
    summary = read(photo_folder / "summary.json")
    files[str(photo_folder / "summary.json")] = sha(photo_folder / "summary.json")
    for index in range(2):
        path = photo_folder / f"observation-{index}-cpu.npz"
        crop = next(
            c
            for c in summary["native_crops"]
            if c["validation_index"] == index
            and c["condition"]["name"] == "iso12800-prior"
            and c["pattern"] == "RGGB"
        )
        metadata = {
            key: crop[key]
            for key in [
                "source_id",
                "source",
                "validation_index",
                "validation_seed",
                "evaluation_tile_xywh",
                "condition",
                "pattern",
                "display_exposure",
                "reference",
            ]
        }
        with np.load(path, allow_pickle=False) as arrays:
            assert arrays["packed"].shape == (1, 4, 128, 128)
            assert arrays["target"].shape == (1, 3, 256, 256)
            expected = np.maximum(arrays["packed"], 0) * np.float32(
                crop["condition"]["shot"]
            ) + np.float32(crop["condition"]["read"])
            assert np.array_equal(expected, arrays["variance"])
            metadata.update(
                white_balance=arrays["wb"][0].tolist(),
                camera_to_srgb=arrays["matrix"][0].tolist(),
                noise_draw="Existing fixed CPU-generated Poisson/read/ADC observation; unchanged across policies",
            )
        files[str(path)] = sha(path)
        photos.append({"observation": ref(path), "metadata": metadata})
    gfx = read(gfx_report)
    noisy = next(s for s in gfx["sources"] if s["role"] == "noisy")
    source = Path(noisy["metadata"]["source"]).resolve()
    assert source.is_relative_to(REPO / ".cache/gfx-qualitative-20231231")
    assert sha(source) == noisy["sha256"]
    raw, meta = read_raw(source)
    assert asdict(meta) == noisy["metadata"]
    assert raw.shape == (8746, 11662) and raw.dtype == np.float32
    raw_path = output / "DSCF3879-normalized-camera-RAW-f32.npy"
    np.save(raw_path, raw, allow_pickle=False)
    conditioning = gfx["conditioning"]
    contexts, regions = [], []
    for entry in gfx["float_contexts"]:
        path = gfx_report.parent / entry["image"]
        assert sha(path) == entry["sha256"]
        files[str(path)] = entry["sha256"]
        if entry["role"] != "noisy-packed":
            continue
        x, y, width, height = entry["context_xywh"]
        tile = raw[y : y + height, x : x + width]
        packed = np.stack([tile[i // 2 :: 2, i % 2 :: 2] for i in range(4)])[None]
        stored = np.load(path, allow_pickle=False)
        assert np.array_equal(packed, stored)
        contexts.append(torch.from_numpy(stored.copy()))
        reference = next(
            r
            for r in gfx["float_contexts"]
            if r["role"] == "reference-rgb" and r["region"]["name"] == entry["region"]["name"]
        )
        regions.append(
            {
                "region": entry["region"],
                "context_xywh": entry["context_xywh"],
                "noisy_packed": ref(path),
                "reference_RGB": ref(gfx_report.parent / reference["image"]),
                "reference": "Separate ISO100 f/5.6 capture and independently demosaiced reference, not GT",
            }
        )
    assert len(contexts) == 4
    packed = torch.cat(contexts)
    colors = color_indices(meta.pattern)[None].expand(4, -1)
    real = output / "GFX-four-contexts-native512.npz"
    np.savez(
        real,
        packed=packed.numpy(),
        variance=variance_map(packed, conditioning["shot"], conditioning["read"]).numpy(),
        colors=colors.numpy(),
        wb=np.broadcast_to(np.float32(meta.white_balance), (4, 3)),
        matrix=np.broadcast_to(np.float32(meta.camera_to_srgb), (4, 3, 3)),
    )
    y, x = torch.meshgrid(torch.arange(512).float(), torch.arange(512).float(), indexing="ij")
    texture = 1 + 0.2 * torch.sin(x * 0.43 + y * 0.11) + 0.1 * torch.cos(y * 0.71)
    target = torch.stack(
        [
            torch.stack((texture * 0.8, texture, texture * 0.6)) * level
            for level in [0.003, 0.03, 0.18, 0.6]
        ]
    )
    labels = torch.stack([color_indices(p) for p in PATTERNS])
    shot, read_noise = 0.00256, 2.62144e-5
    observed = add_noise(
        mosaic(target, labels),
        shot,
        read_noise,
        black_level=0.03,
        generator=torch.Generator().manual_seed(902284),
    )
    analytic = output / "analytic-four-CFA-native512.npz"
    np.savez(
        analytic,
        packed=observed.numpy(),
        variance=variance_map(observed, shot, read_noise).numpy(),
        colors=labels.numpy(),
        target=target.numpy(),
        wb=np.broadcast_to(np.float32([2, 1, 1.5]), (4, 3)),
        matrix=np.broadcast_to(np.eye(3, dtype=np.float32), (4, 3, 3)),
    )
    for path in [source, gfx_report, raw_path, real, analytic]:
        files[str(path)] = sha(path)
    result = {
        "status": "completed-local-compilation-fixtures-no-model-inference",
        "files": files,
        "photos": photos,
        "serving_probes": [
            {"name": "Four natural GFX contexts, unchanged native512", "observation": ref(real)},
            {
                "name": "Analytic native512, all four CFAs and low/high signal",
                "observation": ref(analytic),
            },
        ],
        "full_raw": ref(raw_path),
        "gfx_metadata": asdict(meta),
        "gfx_source_report": ref(gfx_report),
        "gfx_sources": gfx["sources"],
        "conditioning": conditioning,
        "display_exposure": 4,
        "gfx_regions": regions,
        "analytic_condition": {
            "shot": shot,
            "read": read_noise,
            "ADC_bits": 16,
            "black": 0.03,
            "seed": 902284,
        },
        "scope": "Inference-only fixtures. Two existing held-out synthetic photo observations, "
        "four existing GFX native512 contexts verified against the locally decoded full RAW, "
        "and generated analytic CFA probes. No image resizing or training. Personal source "
        "is the cached RAF only; originals remain read-only and untouched. GFX reference is not GT.",
        "CUDA_initialized": torch.cuda.is_initialized(),
    }
    (output / "inputs.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    (output / "prepare.py").write_bytes(Path(__file__).read_bytes())
    print(json.dumps({"inputs": ref(output / "inputs.json"), "files": len(files)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--photo-folder",
        type=Path,
        default=BASE / "evaluation/two-fixed-examples-v43-none10k-cpu-v1",
    )
    parser.add_argument(
        "--gfx-report",
        type=Path,
        default=BASE / "evaluation/packed-isotropic-first32000-gfx-v2/report.json",
    )
    args = parser.parse_args()
    main(args.output, args.photo_folder, args.gfx_report)
