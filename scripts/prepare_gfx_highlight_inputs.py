"""Freeze two extra GFX input/reference regions without loading a learned model."""

import argparse
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
from PIL import Image

from demosaic.cfa import color_indices, malvar, pack
from demosaic.io import read_raw
from demosaic.realdata import read_reference
from demosaic.reporting import display_crop
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def integer_offset(noisy_green, reference_green, x, y, radius=8):
    """Select translation from input and independent reference only; never warp."""
    size = noisy_green.shape[0]
    a = noisy_green[radius:-radius, radius:-radius].astype(np.float64)
    a -= a.mean()
    a_norm = np.linalg.norm(a)
    if a_norm == 0:
        raise ValueError("A featureless region cannot select a reference translation")
    scores = []
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            b = reference_green[
                y + radius + dy : y + size - radius + dy,
                x + radius + dx : x + size - radius + dx,
            ].astype(np.float64)
            b -= b.mean()
            denominator = a_norm * np.linalg.norm(b)
            score = float(np.sum(a * b) / denominator) if denominator else -1.0
            scores.append((score, dx, dy))
    score, dx, dy = max(scores, key=lambda v: (v[0], -abs(v[1]) - abs(v[2])))
    if not np.isfinite(score) or abs(dx) == radius or abs(dy) == radius:
        raise ValueError("Reference translation is invalid or reaches the search boundary")
    return dx, dy, score


@torch.inference_mode()
def main(selection, conditioning_report, output):
    os.nice(5)
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    base = read(selection)
    previous = read(conditioning_report)
    assert base == previous["selection"]
    root = Path.cwd().resolve()
    cache = root / ".cache/gfx-qualitative-20231231"
    expected = {r["role"]: r for r in previous["sources"]}
    inputs = {}
    for role in ["noisy", "reference"]:
        path = (root / base[role]).resolve()
        if path.parent != cache or sha(path) != expected[role]["sha256"]:
            raise ValueError("Only the existing, exact locally cached GFX pair is allowed")
        inputs[role] = path
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    raw, metadata = read_raw(inputs["noisy"])
    reference_raw, reference, reference_metadata, calibration = read_reference(inputs["reference"])
    assert raw.shape == reference_raw.shape == (8746, 11662)
    assert metadata.pattern == reference_metadata.pattern == "RGGB"
    del reference_raw
    wb = torch.tensor(metadata.white_balance)[None]
    matrix = torch.tensor(metadata.camera_to_srgb)[None]
    colors = color_indices(metadata.pattern)[None]
    condition = previous["conditioning"]
    shot, read_variance = condition["shot"], condition["read"]
    records, regions = [], []
    for name, x, y in [
        ("colored-neon-sign", 9060, 2050),
        ("illuminated-platform-boundary", 10320, 4520),
    ]:
        size, tile = 160, 512
        margin = (tile - size) // 2
        tx, ty = (x - margin) // 2 * 2, (y - margin) // 2 * 2
        packed = pack(torch.from_numpy(raw[ty : ty + tile, tx : tx + tile].copy())[None, None])
        variance = packed.clamp_min(0) * shot + read_variance
        noisy = malvar(packed, colors, wb)
        dx, dy, score = integer_offset(noisy[0, 1].numpy(), reference[:, :, 1], tx, ty)
        region = {
            "name": name,
            "noisy_xy": [x, y],
            "reference_xy": [x + dx, y + dy],
            "size": size,
            "selection_method": "Input-only locator selection, then maximum normalized green correlation in512px input/reference contexts; integer offsets within+/-8 only, no output-dependent selection or warp",
            "context_green_correlation": score,
        }
        regions.append(region)
        reference_crop = torch.from_numpy(
            reference[y + dy : y + dy + size, x + dx : x + dx + size].copy()
        ).permute(2, 0, 1)[None]
        roi = [x - tx, y - ty, size, size]
        arrays = output / (name + "-inputs.npz")
        np.savez(
            arrays,
            packed=packed.numpy(),
            variance=variance.numpy(),
            colors=colors.numpy(),
            wb=wb.numpy(),
            matrix=matrix.numpy(),
            noisy_rgb=noisy.numpy(),
            reference_rgb=reference_crop.numpy(),
        )
        previews = []
        for role, rgb, coordinates in [
            ("noisy-Malvar", noisy, roi),
            ("independent-ISO100-AHD-reference-not-GT", reference_crop, [0, 0, size, size]),
        ]:
            values = display_crop(rgb, wb, matrix, coordinates, exposure=base["display_exposure"])
            pixels = np.rint(np.clip(values, 0, 1) * 255).astype(np.uint8)
            image = output / (name + "-" + role + ".png")
            Image.fromarray(pixels).save(image)
            previews.append(
                {
                    "path": str(image),
                    "sha256": sha(image),
                    "role": role,
                    "shape": list(pixels.shape),
                }
            )
        records.append(
            {
                "region": region,
                "context_xywh": [tx, ty, tile, tile],
                "ROI_xywh": roi,
                "arrays": str(arrays),
                "sha256": sha(arrays),
                "previews": previews,
            }
        )
    supplementary = {
        **base,
        "regions": regions,
        "notes": base["notes"]
        + " Supplementary sign/platform regions selected without any learned output. Lights can vary between captures; no pixelwise reference scores. The original four standing regions remain unchanged.",
    }
    (output / "selection.json").write_text(json.dumps(supplementary, indent=2) + "\n")
    sources = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    archive = output / "source"
    archive.mkdir()
    for path in [Path(__file__), *map(Path, sources)]:
        (archive / path.name).write_bytes(path.read_bytes())
    result = {
        "status": "prepared-input-only-GFX-highlight-regions-awaiting-independent-and-native-review",
        "selection": str(output / "selection.json"),
        "selection_sha256": sha(output / "selection.json"),
        "parent_selection": str(selection),
        "parent_selection_sha256": sha(selection),
        "conditioning_report": str(conditioning_report),
        "conditioning_report_sha256": sha(conditioning_report),
        "sources": [
            {"role": role, "path": str(path), "sha256": sha(path)} for role, path in inputs.items()
        ],
        "metadata": asdict(metadata),
        "reference_metadata": asdict(reference_metadata),
        "reference_calibration": calibration,
        "conditioning": condition,
        "display_exposure": base["display_exposure"],
        "cases": records,
        "source_files": sources,
        "driver_sha256": sha(__file__),
        "CUDA_initialized": False,
        "scope": "Two native160px GFX regions/512px contexts, evaluation-only. Input-only selection and integer reference translation; independent AHD ISO100 reference has aperture/time/motion/light differences and is not GT. Original warm cached files read-only. No learned model, scores, output fitting, training, full-frame output or performance claim.",
    }
    (output / "plan.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"plan": str(output / "plan.json"), "regions": regions}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--selection", type=Path, default=Path("configs/gfx-qualitative-20231231.json")
    )
    parser.add_argument("--conditioning-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    main(**vars(parser.parse_args()))
