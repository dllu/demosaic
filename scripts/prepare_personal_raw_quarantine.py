"""Cache authorized personal RAWs and phase-bin targets for data review only."""

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import psutil
import rawpy
from PIL import Image
from prepare_public_raw_quarantine import protected_hashes, protected_identity, sha

from demosaic.io import orient, read_raw
from demosaic.raw_clean import bin_bayer
from demosaic.safety import writable_path

PERSONAL_ROOTS = (Path("/home/dllu/pictures/raw"), Path("/mnt/dataz/pictures/raw"))


def reference(path):
    return {"path": str(Path(path).absolute()), "sha256": sha(path)}


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def cache_source(source, output):
    """Copy once while verifying the library's import SHA1; originals stay read-only."""
    source = Path(source).resolve()
    if not any(root in source.parents for root in PERSONAL_ROOTS):
        raise ValueError("Expected an explicitly authorized personal RAW source root")
    match = re.fullmatch(
        r".+_([a-f0-9]{40})\.(?:raf|arw|dng|nef|cr2|rw2)", source.name, re.IGNORECASE
    )
    if match is None:
        raise ValueError("Expected the library's import-hashed RAW filename")
    output.mkdir(exist_ok=True)
    target = output / source.name
    if target.exists():
        with target.open("rb") as stream:
            assert hashlib.file_digest(stream, "sha1").hexdigest() == match[1]
    else:
        before = source.stat()
        temporary = target.with_suffix(target.suffix + ".partial")
        digest = hashlib.sha1()
        with source.open("rb") as reader, temporary.open("xb") as writer:
            for chunk in iter(lambda: reader.read(8 * 2**20), b""):
                digest.update(chunk)
                writer.write(chunk)
        assert digest.hexdigest() == match[1], "Original differs from import SHA1"
        after = source.stat()
        assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns)
        temporary.replace(target)
    return {
        **reference(target),
        "original_path": str(source),
        "import_sha1": match[1],
        "bytes": target.stat().st_size,
    }


def prepare(selection_path, output):
    selection_path = Path(selection_path).absolute()
    selection = json.loads(selection_path.read_text())
    assert (
        selection["status"] == "personally-authorized-source-inspection-selection-quarantine-only"
    )
    assert (
        selection["permission"]["quote"]
        == "I hereby grant permission to use my photos (so don't worry about licensing)."
    )
    assert reference(selection["permission"]["PROMPT"]["path"]) == selection["permission"]["PROMPT"]
    assert Path(selection["permission"]["PROMPT"]["path"]).resolve() == Path("PROMPT.md").resolve()
    assert selection["permission"]["quote"] in Path("PROMPT.md").read_text()
    assert selection["files"] and len({f["source"] for f in selection["files"]}) == len(
        selection["files"]
    )
    excluded, protection = protected_hashes()
    for filename in [
        "configs/real-camera-qualitative.json",
        "/mnt/external/demosaic/raw-clean-public-extension-v2/bin4/manifest.json",
    ]:
        p = Path(filename)
        protection[str(p.absolute())] = sha(p)
        data = json.loads(p.read_text())
        if isinstance(data, list):
            excluded.update(x["source_sha256"] for x in data)
        else:
            excluded.update(x["id"] for x in data["rows"])
    days = set()
    for filename in [
        "configs/real-camera-qualitative.json",
        "configs/gfx-qualitative-20231231.json",
    ]:
        for year, month, day in re.findall(
            r"(20\d\d)-(\d\d)-(\d\d)-\d\d-\d\d-\d\d", Path(filename).read_text()
        ):
            date = datetime(int(year), int(month), int(day)).date()
            days.update(str(date + timedelta(days=i)) for i in range(-7, 8))
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / ".prepare.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        source_paths = [
            Path(__file__),
            Path("scripts/prepare_public_raw_quarantine.py"),
            *[Path("src/demosaic") / n for n in ("raw_clean.py", "io.py", "color.py", "cfa.py")],
        ]
        recipe = {
            "selection": reference(selection_path),
            "source_files": [reference(p) for p in source_paths],
            "protection_sources": protection,
            "excluded_days_plus_minus7": sorted(days),
            "factors": [4, 8],
            "max_ISO": 200,
            "source_near_white_limit": 0.001,
            "rawpy": rawpy.__version__,
            "libraw": list(rawpy.libraw_version),
            "numpy": np.__version__,
        }
        recipe_path = output / "recipe.json"
        if recipe_path.exists():
            assert json.loads(recipe_path.read_text()) == recipe, (
                "Recipe changed; choose a new output"
            )
        else:
            save(recipe_path, recipe)
        archive = output / "source"
        archive.mkdir(exist_ok=True)
        for path in source_paths:
            destination = archive / path.name
            if not destination.exists():
                shutil.copyfile(path, destination)
            assert sha(destination) == sha(path)
        shutil.copyfile(selection_path, archive / "selection.json")
        (output / "captures").mkdir(exist_ok=True)
        rows = []
        for entry in selection["files"]:
            assert psutil.virtual_memory().available > 40 * 2**30
            assert shutil.disk_usage(output).free > 128 * 2**30
            index = entry["candidate_index"]
            assert Path(entry["source"]).name[:10] not in days
            record_path = output / "captures" / f"{index:03d}.json"
            if record_path.exists():
                row = json.loads(record_path.read_text())
                for item in [row["source"], *row["caches"], row["screen"], row["preview"]]:
                    assert sha(item["path"]) == item["sha256"]
                rows.append(row)
                continue
            source = cache_source(entry["source"], output / "sources")
            assert source["sha256"] not in excluded
            exif = json.loads(
                subprocess.run(
                    [
                        "exiftool",
                        "-j",
                        "-n",
                        "-DateTimeOriginal",
                        "-ISO",
                        "-Model",
                        "-FNumber",
                        "-ExposureTime",
                        source["path"],
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).stdout
            )[0]
            date = datetime.strptime(exif["DateTimeOriginal"][:19], "%Y:%m:%d %H:%M:%S")
            assert date.strftime("%Y-%m-%d-%H-%M-%S") == Path(entry["source"]).name[:19]
            assert str(date.date()) not in days and protected_identity(exif["Model"], exif) is None
            raw, meta = read_raw(source["path"])
            assert meta.camera == "GFX100S" and 0 < meta.iso <= 200 and meta.iso == exif["ISO"]
            assert np.isfinite(raw).all() and min(raw.shape) // 8 - 2 >= 256
            caches = []
            for factor in (4, 8):
                rgb = bin_bayer(raw, meta.pattern, factor=factor)
                pixels = np.rint(np.clip(rgb, 0, 1) * 65535).astype(np.uint16)
                path = output / f"bin{factor}" / f"{source['sha256']}.npy"
                path.parent.mkdir(exist_ok=True)
                with path.with_suffix(".npy.tmp").open("wb") as stream:
                    np.save(stream, pixels, allow_pickle=False)
                path.with_suffix(".npy.tmp").replace(path)
                caches.append(
                    {
                        **reference(path),
                        "shape": list(pixels.shape),
                        "bin_factor": factor,
                        "dtype": "uint16",
                        "color_space": "linear-camera-RGB",
                    }
                )
                if factor == 4:
                    fraction = float((pixels.max(-1) >= 65500).mean())
                else:
                    linear = np.clip(
                        (
                            pixels.astype(np.float32)
                            / 65535
                            * np.array(meta.white_balance, np.float32)
                        )
                        @ np.array(meta.camera_to_srgb, np.float32).T,
                        0,
                        1,
                    )
                    screen = output / f"screen-{index:03d}.npy"
                    np.save(screen, np.rint(linear * 65535).astype(np.uint16), allow_pickle=False)
                    srgb = np.where(
                        linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055
                    )
                    preview = output / f"preview-{index:03d}.png"
                    Image.fromarray(orient(np.rint(srgb * 255).astype(np.uint8), meta.flip)).save(
                        preview
                    )
            row = {
                "id": source["sha256"],
                "candidate_index": index,
                "scene_group": entry["scene_group"],
                "split": "quarantine",
                "source_family": "personally-authorized-RAW",
                "source": source,
                "permission": selection["permission"],
                "raw_metadata": asdict(meta),
                "raw_shape": list(raw.shape),
                "exif_without_GPS": exif,
                "caches": caches,
                "source_quality": {
                    "bin4_any_channel_near_white_fraction": fraction,
                    "bin4_source_clipping_gate_passed": fraction <= 0.001,
                },
                "screen": reference(screen),
                "preview": reference(preview),
                "preview_display_exposure": 1,
                "source_inspection": entry["source_inspection"],
                "target_label": "Phase-binned low-noise camera RGB estimate, not exact noiseless GT",
            }
            save(record_path, row)
            rows.append(row)
            del raw, rgb, pixels, linear, srgb
            print(
                json.dumps(
                    {
                        "event": "personal-RAW-quarantine",
                        "candidate": index,
                        "done": len(rows),
                        "total": len(selection["files"]),
                        "near_white_fraction": fraction,
                        "source_gate_pass": fraction <= 0.001,
                    }
                ),
                flush=True,
            )
        result = {
            "status": "completed-personal-RAW-quarantine-no-training-admission",
            "split": "quarantine",
            "recipe": recipe,
            "rows": rows,
            "scope": "Private user-permitted source copies and4x/8x phase-binned camera RGB. No demosaicer, WB/matrix, gamma or8bit step enters target caches. Inspection screens only use WB/matrix/sRGB. Low-noise estimates, not exact GT. Protected/content/overlap and full source-quality review plus separate loader admission remain required; no active training dataset changed.",
        }
        save(output / "manifest.json", result)
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    os.nice(10)
    prepare(args.selection, args.output)
