"""Probe a frozen Gaussian denoiser on exact physical flat targets.

This is an independent-phase RAW diagnostic, not Noise2VST adaptation or a
photographic quality claim. Source and weights are verified against a receipt.
"""

import argparse
import hashlib
import importlib.util
import json
import shutil
from pathlib import Path

import torch
from torch.nn import functional as F

from demosaic.cfa import malvar
from demosaic.precision import ieee_fp32
from demosaic.reporting import center_crop, display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import freeze_checkpoint, observation

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, required=True)
parser.add_argument("--camera", type=Path, required=True)
parser.add_argument(
    "--reference", type=Path, default=Path("docs/results/noise2vst-source-and-weights.json")
)
args = parser.parse_args()
torch.set_num_threads(4)
output = writable_path(args.output)
output.mkdir(parents=True, exist_ok=True)
if (output / "result.json").exists():
    raise ValueError("Choose a new diagnostic directory")
receipt = json.loads(args.reference.read_text())
record = next(m for m in receipt["models"] if m["model"] == "DRUNet")
source = Path(receipt["checkout"]) / "src/noise2vst/models/drunet.py"
if hashlib.sha256(source.read_bytes()).hexdigest() != record["source_sha256"]:
    raise ValueError("External source differs from verified receipt")
weights, digest = freeze_checkpoint(Path(record["weights"]), output / "weights")
if digest != record["sha256"]:
    raise ValueError("External weights differ from verified receipt")
archive = output / "source"
archive.mkdir()
for origin, name in [
    (Path(__file__), "probe_gaussian_flat.py"),
    (source, "drunet.py"),
    (Path(receipt["checkout"]) / "LICENSE", "Noise2VST-LICENSE"),
    (Path(receipt["kair_license"]), "KAIR-LICENSE"),
    (args.camera, "camera.json"),
    (args.reference, "reference.json"),
]:
    shutil.copyfile(origin, archive / name)
for origin in Path("src/demosaic").glob("*.py"):
    shutil.copyfile(origin, archive / origin.name)
spec = importlib.util.spec_from_file_location("gaussian_drunet_reference", source)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
model = module.DRUNet(color=False)
model.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True), strict=True)
model.cuda().eval().requires_grad_(False).to(memory_format=torch.channels_last)
camera = args.camera
meta = json.loads(camera.read_text()).get("raw", json.loads(camera.read_text()))
levels = [0.002, 0.01, 0.05]
condition = {"name": "iso6400-prior", "exposure": 1.0, "shot": 0.00128, "read": 6.5536e-6}
rgb = torch.tensor(levels, device="cuda")[:, None, None, None].expand(-1, 3, 512, 512)
batch = observation(
    rgb,
    [f"flat-{x}" for x in levels],
    condition,
    meta["pattern"],
    meta["white_balance"],
    meta["camera_to_srgb"],
    20261015,
)
restored = torch.empty_like(batch["packed"])
sigmas = []
with torch.inference_mode(), torch.autocast("cuda", enabled=False), ieee_fp32():
    for b in range(3):
        values = []
        for phase in range(4):
            original = batch["packed"][b : b + 1, phase : phase + 1].contiguous(
                memory_format=torch.channels_last
            )
            sigma = (original.mean().clamp_min(0) * condition["shot"] + condition["read"]).sqrt()
            restored[b : b + 1, phase : phase + 1] = model(original, sigma=sigma, norm_equiv=True)
            values.append(sigma.item())
        sigmas.append(values)
    prediction = malvar(restored, batch["colors"], batch["wb"])
    noisy = malvar(batch["packed"], batch["colors"], batch["wb"])
    error = (prediction - batch["target"])[..., 64:-64, 64:-64]
    bias = error.mean((-2, -1), keepdim=True)
    centered = error - bias
    rows = []
    crops = []
    for b, level in enumerate(levels):
        row = {
            "scene_level": level,
            "camera_centered_sigma": centered[b].square().mean().sqrt().item(),
            "camera_abs_bias": bias[b].abs().mean().item(),
            "scales": {
                str(k): F.avg_pool2d(centered, k, k)[b].square().mean().sqrt().item()
                for k in [8, 32, 64]
            },
        }
        rows.append(row)
        if b < 2:
            xywh = center_crop(prediction.shape)
            panels = [
                (
                    name,
                    display_crop(
                        value[b : b + 1],
                        batch["wb"][b : b + 1],
                        batch["matrix"][b : b + 1],
                        xywh,
                        exposure=4,
                    ),
                )
                for name, value in [
                    ("Noisy (Malvar)", noisy),
                    ("DRUNet + Malvar", prediction),
                    ("GT (synthetic flat)", batch["target"]),
                ]
            ]
            crops.append(
                save_triplet(
                    output,
                    f"flat-{level}",
                    panels,
                    caption=f"DRUNet-gray independent CFA phases + Malvar, exact flat {level}",
                    metadata={
                        "xywh": xywh,
                        "scene_level": level,
                        "display_exposure": 4.0,
                        "condition": condition,
                        "phase_sigmas": sigmas[b],
                        "weights_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
                    },
                )
            )
result = {
    "protocol": "Diagnostic on exact synthetic flats only; independent grayscale DRUNet per packed CFA phase, then WB-aware Malvar. Sigma from known synthetic shot/read and observed phase mean; no target used for inference. Per-phase input normalization is the inspected source default norm_equiv=True. IEEEFP32. Not Noise2VST adaptation, not a trained joint/DINO model, not a photographic score.",
    "source": str(source),
    "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "weights": str(weights),
    "weights_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
    "source_receipt": str(args.reference),
    "source_archive": str(archive),
    "probe_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "camera_receipt_sha256": hashlib.sha256(camera.read_bytes()).hexdigest(),
    "camera": meta,
    "levels": levels,
    "condition": condition,
    "seed": 20261015,
    "phase_sigmas": sigmas,
    "rows": rows,
    "native_crops": crops,
}
(output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
print(json.dumps(rows), flush=True)
