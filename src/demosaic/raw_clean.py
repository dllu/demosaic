"""Licensed training-only Bayer binning and camera-linear synthetic observations."""

import hashlib
import inspect
import json
import random
from dataclasses import asdict
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import Dataset

from .cfa import PATTERNS, color_indices, mosaic
from .data import homography, optical_blur
from .io import read_raw
from .noise import add_noise, sample_coefficients, variance_map
from .paired import TRAINING_SCENES, verify_file
from .precision import ieee_fp32
from .safety import writable_path


def _align_phase(phase, row, col):
    # A phase's ordinary block centroid is offset by +/- half a sensor pixel.
    # Shift its sampling location by +/- quarter of a phase-grid pixel before
    # averaging. This reproduces the same centroid and second moments for all
    # four phases; it is not independent R/G/B box binning at offset locations.
    for axis, offset in ((0, row), (1, col)):
        indices = np.arange(phase.shape[axis]) + (1 if offset == 0 else -1)
        neighbor = np.take(phase, indices.clip(0, phase.shape[axis] - 1), axis=axis)
        phase = 0.75 * phase + 0.25 * neighbor
    return phase


def bin_bayer(raw, pattern, *, factor=8, trim=1):
    """Return phase-aligned linear camera RGB, with no demosaicer/gamma/8-bit step.

    Four phase images are shifted by quarter phase-grid pixels, then area binned
    by factor/2. Their physical centroids coincide with dense-RGB factor-bin
    centers. Green phases are averaged. Trim removes interpolation border cells.
    Low-ISO source noise is reduced, not eliminated.
    """
    raw = np.asarray(raw, dtype=np.float32)
    if raw.ndim != 2 or factor < 2 or factor % 2 or trim < 1 or pattern not in PATTERNS:
        raise ValueError("Use a Bayer array, even factor>=2, trim>=1 and a known CFA")
    h, w = (n // factor * factor for n in raw.shape)
    bh, bw = h // factor, w // factor
    if min(bh, bw) <= 2 * trim or not np.isfinite(raw).all():
        raise ValueError("RAW too small/nonfinite for the requested binning")
    channels = [[] for _ in range(3)]
    block = factor // 2
    for phase, color in enumerate(PATTERNS[pattern]):
        y, x = divmod(phase, 2)
        aligned = _align_phase(raw[y:h:2, x:w:2], y, x)
        binned = aligned.reshape(bh, block, bw, block).mean((1, 3), dtype=np.float32)
        channels[color].append(binned)
    rgb = np.stack([np.mean(values, axis=0, dtype=np.float32) for values in channels], axis=-1)
    return rgb[trim:-trim, trim:-trim].copy()


def prepare_raw_clean(manifest, output, *, factor=8, min_size=256):
    """Prepare only predeclared clean captures from the verified train32 selection."""
    import fcntl

    from . import io

    manifest = Path(manifest)
    payload = manifest.read_bytes()
    source = json.loads(payload)
    if source["split"] != "train" or any(
        s["scene"] not in TRAINING_SCENES or s.get("unknown_sensor") for s in source["selection"]
    ):
        raise ValueError("RAW clean preparation requires the protected-scene-free train selection")
    if source["dataset_license"].get("rightsIdentifier") != "CC-BY-SA-4.0":
        raise ValueError("Expected the licensed RawNIND publisher selection")
    permissions = [r for r in source.get("auxiliary", []) if r["filename"] == "permissions.txt"]
    if len(permissions) != 1:
        raise ValueError("Expected publisher permissions.txt for scene attribution")
    checked_permissions = verify_file(permissions[0]["path"], permissions[0])
    if checked_permissions["sha256"] != permissions[0]["sha256"]:
        raise ValueError("Scene attribution checksum mismatch")
    permission_bytes = Path(checked_permissions["path"]).read_bytes()
    if factor < 2 or factor % 2 or min_size < 32:
        raise ValueError("Invalid bin factor/minimum size")
    algorithm = hashlib.sha256(
        (inspect.getsource(_align_phase) + inspect.getsource(bin_bayer)).encode()
        + Path(io.__file__).read_bytes()
    ).hexdigest()
    recipe = {
        "version": 1,
        "factor": factor,
        "trim": 1,
        "min_size": min_size,
        "source_sha256": hashlib.sha256(payload).hexdigest(),
        "algorithm_sha256": algorithm,
        "color_space": "linear-camera-RGB",
        "dtype": "uint16",
    }
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".prepare.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another RAW preparation owns this output") from None
        if (output / "recipe.json").exists() and json.loads(
            (output / "recipe.json").read_text()
        ) != recipe:
            raise ValueError("RAW clean cache recipe differs; choose a new destination")
        (output / "recipe.json").write_text(json.dumps(recipe, indent=2) + "\n")
        (output / "permissions.txt").write_bytes(permission_bytes)
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for p in [Path(__file__), Path(io.__file__)]:
            (archive / p.name).write_bytes(p.read_bytes())
        (archive / "acquisition-manifest.json").write_bytes(payload)
        previous = {}
        if (output / "manifest.json").exists():
            previous = {
                r["id"]: r for r in json.loads((output / "manifest.json").read_text())["rows"]
            }
        rows, rejected, seen = [], [], set()
        for scene in source["selection"]:
            for record in scene["clean"]:
                if record["role"] != "reference":
                    raise ValueError("Clean targets require reference captures")
                checked = verify_file(record["path"], record)
                if checked["sha256"] != record["sha256"]:
                    raise ValueError("Source RAW SHA256 changed")
                identity = checked["sha256"]
                if identity in seen:
                    continue
                seen.add(identity)
                cache = output / (identity + ".npy")
                old = previous.get(identity)
                if (
                    old
                    and cache.exists()
                    and hashlib.sha256(cache.read_bytes()).hexdigest() == old["cache_sha256"]
                ):
                    rows.append(old)
                    continue
                raw, meta = read_raw(checked["path"])
                rgb = bin_bayer(raw, meta.pattern, factor=factor)
                if min(rgb.shape[:2]) < min_size:
                    rejected.append(
                        {
                            "source": checked,
                            "scene": scene["scene"],
                            "shape": list(rgb.shape),
                            "reason": "too_small_after_binning",
                        }
                    )
                    continue
                values = np.rint(np.clip(rgb, 0, 1) * 65535).astype(np.uint16)
                temporary = cache.with_suffix(".npy.tmp")
                with temporary.open("wb") as handle:
                    np.save(handle, values, allow_pickle=False)
                temporary.replace(cache)
                rows.append(
                    {
                        "id": identity,
                        "split": "train",
                        "scene": scene["scene"],
                        "source": checked,
                        "raw_metadata": asdict(meta),
                        "raw_shape": list(raw.shape),
                        "cache": cache.name,
                        "cache_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
                        "shape": list(values.shape),
                        "color_space": "linear-camera-RGB",
                        "bin_factor": factor,
                        "dtype": "uint16",
                        "license": source["dataset_license"],
                        "attribution": source["attribution"],
                    }
                )
                print(
                    json.dumps(
                        {
                            "event": "raw-clean-prepared",
                            "scene": scene["scene"],
                            "shape": list(values.shape),
                        }
                    ),
                    flush=True,
                )
        result = {
            "format_version": 1,
            "split": "train",
            "recipe": recipe,
            "rows": rows,
            "rejected": rejected,
            "notes": [
                "Phase-aligned sensor averages, not exact noiseless RGB ground truth.",
                "All development/official-test/unknown-sensor and GFX qualitative scenes excluded.",
                "No AHD, tone curve, white balance, color matrix or 8-bit stage applied to the cache.",
            ],
        }
        temporary = output / "manifest.json.tmp"
        temporary.write_text(json.dumps(result, indent=2) + "\n")
        temporary.replace(output / "manifest.json")
    return result


class RawCleanDataset(Dataset):
    """Scene-balanced camera RGB with deterministic crops and physical metadata."""

    def __init__(self, manifest, *, patch_size=256, seed=42):
        self.path = Path(manifest)
        self.payload = self.path.read_bytes()
        data = json.loads(self.payload)
        if data["split"] != "train":
            raise ValueError("Native RAW targets require a train manifest")
        if patch_size < 32 or patch_size % 16:
            raise ValueError("Patch must be >=32 and divisible by16")
        self.sha256 = hashlib.sha256(self.payload).hexdigest()
        self.size = patch_size
        self.seed = seed
        self.scenes = {}
        for row in data["rows"]:
            if (
                row["split"] != "train"
                or row["scene"] not in TRAINING_SCENES
                or row["color_space"] != "linear-camera-RGB"
            ):
                raise ValueError("RAW clean manifest includes a protected/non-camera source")
            path = self.path.parent / row["cache"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != row["cache_sha256"]:
                raise ValueError("RAW clean cache checksum mismatch")
            if min(row["shape"][:2]) < patch_size:
                raise ValueError("Native cache is smaller than the training patch")
            self.scenes.setdefault(row["scene"], []).append(row)
        self.names = sorted(self.scenes)
        if not self.names:
            raise ValueError("No native training sources")

    def __len__(self):
        return len(self.names)

    def __getitem__(self, index):
        rng = random.Random(self.seed + index)
        row = rng.choice(self.scenes[rng.choice(self.names)])
        array = np.load(self.path.parent / row["cache"], mmap_mode="r", allow_pickle=False)
        h, w = array.shape[:2]
        size = self.size
        ch, cw = (rng.randint(size, min(n, int(size * 1.4))) for n in (h, w))
        y, x = rng.randrange(h - ch + 1), rng.randrange(w - cw + 1)
        rgb = (
            torch.from_numpy(array[y : y + ch, x : x + cw].copy().astype(np.float32)).permute(
                2, 0, 1
            )
            / 65535
        )
        rgb = F.interpolate(rgb[None], size=(size, size), mode="area")[0]
        rgb = torch.rot90(rgb, rng.randrange(4), (-2, -1))
        if rng.random() < 0.5:
            rgb = rgb.flip(-1)
        if rng.random() < 0.25:
            rgb = optical_blur(rgb, rng)
        if rng.random() < 0.2:
            rgb = homography(rgb, rng)
        meta = row["raw_metadata"]
        return {
            "camera_rgb": rgb.contiguous(),
            "wb": torch.tensor(meta["white_balance"]),
            "matrix": torch.tensor(meta["camera_to_srgb"]),
        }


def raw_clean_step(step, seed, fraction, paired_fraction):
    """Conditional native fraction preserves the existing paired step sequence."""
    return random.Random(f"raw-clean:{seed}:{step}").random() < fraction / max(
        1 - paired_fraction, 1e-12
    )


def degrade_raw_clean(
    batch,
    *,
    reconstruct_highlights=False,
    noise_free_fraction=0.0,
    preserve_negative_read_noise=False,
):
    """Apply fresh Poisson/read/ADC noise directly to true camera-linear targets."""
    if not 0 <= noise_free_fraction <= 1:
        raise ValueError("Noise-free fraction must be in [0,1]")
    rgb = batch["camera_rgb"]
    device = rgb.device
    count = len(rgb)
    with torch.autocast(device_type=device.type, enabled=False), ieee_fp32():
        wb, matrix = batch["wb"].float(), batch["matrix"].float()
        clean = rgb.float() * torch.empty(count, 1, 1, 1, device=device).uniform_(-3, 2).exp2()
        if reconstruct_highlights:
            linear = torch.einsum("bij,bjhw->bihw", matrix, clean * wb[..., None, None]).clamp(0, 1)
            target = (
                torch.einsum("bij,bjhw->bihw", torch.linalg.inv(matrix), linear)
                / wb[..., None, None]
            )
        else:
            target = clean.clamp(0, 1)
        labels = torch.stack([color_indices(p, device=device) for p in PATTERNS])[
            torch.randint(4, (count,), device=device)
        ]
        shot, read = sample_coefficients(count, device)
        if noise_free_fraction:
            keep = torch.rand_like(shot) >= noise_free_fraction
            shot, read = shot * keep, read * keep
        black = (
            torch.empty(count, 1, 1, 1, device=device).uniform_(0.002, 0.06)
            if preserve_negative_read_noise
            else 0.0
        )
        observed = add_noise(mosaic(clean, labels), shot, read, black_level=black)
        return {
            "packed": observed,
            "variance": variance_map(observed, shot, read),
            "colors": labels,
            "target": target,
            "wb": wb,
            "matrix": matrix,
            "shot": shot,
            "read": read,
        }
