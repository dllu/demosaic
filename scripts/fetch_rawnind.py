"""Fetch a pinned, separately licensed reference model for local comparison.

Run from the repository root: source scripts/env.sh; uv run python scripts/fetch_rawnind.py
"""

import hashlib
import json
import urllib.request

from demosaic.safety import writable_path

ROOT = "https://raw.githubusercontent.com/trougnouf/rawnind_jddc/"
REVISION = "e80fb7b14dc440bba38c01f312fd3cc02deb566c"
FILES = [
    (
        f"{ROOT}{REVISION}/LICENSE",
        "LICENSE",
        "3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986",
    ),
    (
        f"{ROOT}{REVISION}/src/rawnind/models/raw_denoiser.py",
        "raw_denoiser.py",
        "154868a016cc83a74f8efc54675a2c4ffd120e3f30c159d10f11e012e8ca8d65",
    ),
    (
        "https://drive.usercontent.google.com/download?id=1dFTLeljWi9wwojcZUsam8bE31JdYy3oM&export=download&confirm=t",
        "utnet2-bayer.pt",
        "c1f7de3de24cb12f4803ee65e11cfb467e9a5b80c3cb7126746ef026106c15e0",
    ),
]


def main():
    destination = writable_path("/mnt/external/demosaic/references/rawnind")
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for url, name, expected in FILES:
        output = destination / name
        if not output.exists():
            temporary = output.with_suffix(".tmp")
            with (
                urllib.request.urlopen(url, timeout=60) as response,
                temporary.open("wb") as handle,
            ):
                while chunk := response.read(1 << 20):
                    handle.write(chunk)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
                raise ValueError(f"Unexpected reference checksum for {name}: original preserved")
            temporary.replace(output)
        actual = hashlib.sha256(output.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"Existing reference checksum differs for {output}")
        records.append({"name": name, "url": url, "sha256": actual})
        print(f"Verified {name}: {actual}")
    manifest = {
        "repository": "https://github.com/trougnouf/rawnind_jddc",
        "revision": REVISION,
        "license": "GPL-3.0; author additionally offers weights CC-BY-4.0",
        "checkpoint": "Bayer UtNet2 half-resolution, iteration 4350000",
        "files": records,
    }
    (destination / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main()
