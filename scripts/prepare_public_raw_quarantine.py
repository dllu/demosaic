"""Prepare resumable camera-linear public RAW targets for review, never training.

Uses the existing phase-aligned native binning. Source/decode/cache provenance,
clipping statistics and inspection previews are retained in quarantine. A
separate pinned admission remains mandatory before a training loader accepts it.
"""

import argparse
import fcntl
import hashlib
import json
import re
import subprocess
from dataclasses import asdict
from pathlib import Path

import numpy as np
import psutil
import rawpy
from PIL import Image

from demosaic.io import orient, read_raw
from demosaic.paired import verify_file
from demosaic.raw_clean import bin_bayer
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def normalized_camera(camera):
    return re.sub(r"[^A-Z0-9]", "", camera.upper())


def protected_identity(camera, metadata):
    camera = normalized_camera(camera)
    if camera.endswith(("EOSM100", "DMCGH1")):
        return "camera-held-out-for-unseen-development"
    text = json.dumps(metadata)
    if re.search(r"DSCF(?:3835|3842|3879|3880|3883)", text, re.IGNORECASE):
        return "standing-GFX-capture-identifier"
    if "GFX100S" in camera and "2023:12:31" in text:
        return "standing-GFX-capture-date-family"
    return None


def qualitative_capture_hashes(config):
    """Keep the extra RAW/JPEG comparison out even when capture metadata is absent."""
    hashes = set()
    roots = [
        Path(".cache/gfx-green-mesh-20231231").resolve(),
        Path(".cache/gfx-qualitative-20231231").resolve(),
    ]
    for item in json.loads(Path(config).read_text())["sources"].values():
        path = Path(item["path"]).resolve()
        if not any(path.is_relative_to(root) for root in roots):
            raise ValueError("Use locally cached green-mesh qualitative sources")
        digest = sha(path)
        if digest != item["sha256"]:
            raise ValueError("Green-mesh qualitative source hash differs")
        hashes.add(digest)
    return hashes


def protected_hashes():
    base = Path("/mnt/external/demosaic/references")
    names = ["rawnind-dataset/manifest-test.json", "rawnind-dataset/manifest-development.json", "rawnind-unseen-development/manifest-development.json", "rawnind-train32/manifest-train.json"]
    hashes, sources = set(), {}
    for name in names:
        path = base / name
        sources[str(path)] = sha(path)
        data = json.loads(path.read_text())
        for scene in data["selection"]:
            for role in ["clean", "noisy"]:
                hashes.update(r["sha256"] for r in scene[role])
    config = Path("configs/gfx-qualitative-20231231.json")
    sources[str(config)] = sha(config)
    data = json.loads(config.read_text())
    for role in ["noisy", "reference"]:
        path = Path(data[role])
        if not str(path).startswith(".cache/gfx-qualitative-20231231/"):
            raise ValueError("Use locally cached standing RAWs")
        hashes.add(sha(path))
    mesh_config = Path("configs/gfx-green-mesh-20231231.json")
    if mesh_config.exists():
        sources[str(mesh_config)] = sha(mesh_config)
        hashes.update(qualitative_capture_hashes(mesh_config))
    return hashes, sources


def prepare(acquisition, output):
    acquisition = Path(acquisition).resolve()
    data = json.loads(acquisition.read_text())
    files = data["files"]
    identities = [r["sha256"] for r in files]
    if not files or len(identities) != len(set(identities)) or any(
        r["license"] != "CC0-1.0"
        or r["license_url"] != "https://creativecommons.org/publicdomain/zero/1.0/"
        or r["publisher_checksum"] != {"type": "SHA-256", "value": r["sha256"]}
        for r in files
    ):
        raise ValueError("Expected unique, checksum-verified, explicitly CC0 sources")
    excluded, protection_sources = protected_hashes()
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".prepare.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Another quarantine producer owns this output") from None
        source_paths = [Path(__file__), *[Path("src/demosaic") / name for name in ["raw_clean.py", "io.py", "color.py", "cfa.py"]]]
        recipe = {"acquisition_sha256": sha(acquisition), "source_sha256": {p.name: sha(p) for p in source_paths}, "rawpy": rawpy.__version__, "libraw": list(rawpy.libraw_version), "numpy": np.__version__, "factors": [4, 8], "trim": 1, "protected_sources": protection_sources}
        path = output / "recipe.json"
        if path.exists() and json.loads(path.read_text()) != recipe:
            raise ValueError("Quarantine recipe changed; choose a new output")
        path.write_text(json.dumps(recipe, indent=2) + "\n")
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for source in source_paths:
            (archive / source.name).write_bytes(source.read_bytes())
        (archive / "acquisition-manifest.json").write_bytes(acquisition.read_bytes())
        captures = output / "captures"
        captures.mkdir(exist_ok=True)
        rows, rejected = [], []
        for index, source in enumerate(files):
            if psutil.virtual_memory().available / 1e9 < 16:
                raise RuntimeError("Insufficient RAM for the next RAW decode")
            checked = verify_file(source["path"], source)
            if checked["sha256"] != source["sha256"]:
                raise ValueError("Source checksum differs from acquisition")
            outcome = captures / f"{source['file_id']}.json"
            if outcome.exists():
                saved = json.loads(outcome.read_text())
                if saved["source_sha256"] != checked["sha256"]:
                    raise ValueError("Cached capture source changed")
                if "row" in saved:
                    row = saved["row"]
                    for cache in [*row["caches"], {"path": row["screen_cache"], "sha256": row["screen_sha256"]}, {"path": row["preview"], "sha256": row["preview_sha256"]}]:
                        if sha(cache["path"]) != cache["sha256"]:
                            raise ValueError("Previously prepared quarantine cache changed")
                    rows.append(row)
                else:
                    rejected.append(saved["rejection"])
                print(json.dumps({"event": "quarantine-reused", "file_id": source["file_id"], "done": index + 1, "total": len(files)}), flush=True)
                continue
            reason = "existing-or-protected-source-hash" if checked["sha256"] in excluded else None
            raw, meta = None, None
            if not reason:
                try:
                    raw, meta = read_raw(checked["path"])
                except (ValueError, rawpy.LibRawError) as exc:
                    reason = f"unsupported-or-invalid-RAW: {exc}"
            if not reason:
                exif = json.loads(subprocess.run(["exiftool", "-j", "-DateTimeOriginal", "-OriginalFileName", "-OriginalRawFileName", "-Artist", "-Copyright", str(checked["path"])], check=True, capture_output=True, text=True, timeout=30).stdout)[0]
                reason = protected_identity(meta.camera, exif)
                if meta.iso is None or not 0 < meta.iso <= 200 or meta.iso != source["scouted_iso"]:
                    reason = "actual-ISO-invalid-or-differs-from-survey"
                if min(raw.shape) // 8 - 2 < 256:
                    reason = "actual-visible-sensor-too-small"
                if not np.isfinite(raw).all():
                    reason = "nonfinite-RAW-values"
            if reason:
                rejection = {"file_id": source["file_id"], "source": checked, "reason": reason}
                saved = {"source_sha256": checked["sha256"], "rejection": rejection}
                rejected.append(rejection)
            else:
                caches, quality = [], {}
                for factor in [4, 8]:
                    rgb = bin_bayer(raw, meta.pattern, factor=factor)
                    pixels = np.rint(np.clip(rgb, 0, 1) * 65535).astype(np.uint16)
                    cache = output / f"bin{factor}" / f"{checked['sha256']}.npy"
                    cache.parent.mkdir(exist_ok=True)
                    with cache.with_suffix(".npy.tmp").open("wb") as stream:
                        np.save(stream, pixels, allow_pickle=False)
                    cache.with_suffix(".npy.tmp").replace(cache)
                    caches.append({"path": str(cache), "sha256": sha(cache), "shape": list(pixels.shape), "dtype": "uint16", "bin_factor": factor, "color_space": "linear-camera-RGB", "unique_codes": len(np.unique(pixels))})
                    if factor == 4:
                        quality = {"bin4_any_channel_near_white_fraction": float((pixels.max(-1) >= 65500).mean()), "sampled_camera_quantiles_1_50_99": np.quantile(pixels[::4, ::4].astype(np.float32) / 65535, [.01, .5, .99], axis=(0, 1)).tolist(), "bin4_source_clipping_gate_passed": bool((pixels.max(-1) >= 65500).mean() <= .001)}
                    else:
                        linear = np.clip((pixels.astype(np.float32) / 65535 * np.array(meta.white_balance, np.float32)) @ np.array(meta.camera_to_srgb, np.float32).T, 0, 1)
                        screen = output / f"screen-{source['file_id']}.npy"
                        np.save(screen, np.rint(linear * 65535).astype(np.uint16), allow_pickle=False)
                        srgb = np.where(linear <= .0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - .055)
                        preview = output / f"preview-{source['file_id']}.png"
                        Image.fromarray(orient(np.rint(srgb * 255).astype(np.uint8), meta.flip)).save(preview)
                row = {"id": checked["sha256"], "file_id": source["file_id"], "split": "quarantine", "source": checked, "raw_shape": list(raw.shape), "raw_metadata": asdict(meta), "exif": exif, "caches": caches, "source_quality": quality, "screen_cache": str(screen), "screen_sha256": sha(screen), "preview": str(preview), "preview_sha256": sha(preview), "preview_display_exposure": 1.0}
                rows.append(row)
                saved = {"source_sha256": checked["sha256"], "row": row}
                del rgb, pixels, linear, srgb
            temporary = outcome.with_suffix(".json.tmp")
            temporary.write_text(json.dumps(saved, indent=2, allow_nan=False) + "\n")
            temporary.replace(outcome)
            del raw
            print(json.dumps({"event": "quarantine-prepared" if not reason else "quarantine-rejected", "file_id": source["file_id"], "done": index + 1, "total": len(files), "reason": reason}), flush=True)
        result = {"format_version": 1, "split": "quarantine", "usage": "QUARANTINE ONLY; not a training manifest. Camera-linear low-noise estimates, not exact GT. Clipping, content and scene-overlap review remain required before separate pinned admission.", "acquisition": str(acquisition), "acquisition_sha256": sha(acquisition), "recipe": recipe, "rows": rows, "rejected": rejected}
        temporary = output / "manifest.json.tmp"
        temporary.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        temporary.replace(output / "manifest.json")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    data = prepare(**vars(parser.parse_args()))
    print(json.dumps({"prepared": len(data["rows"]), "rejected": len(data["rejected"])}), flush=True)
