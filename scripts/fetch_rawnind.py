"""Fetch a pinned, separately licensed reference model for local comparison.

Run from the repository root: source scripts/env.sh; uv run python scripts/fetch_rawnind.py
"""

import argparse
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
VARIANTS = {
    "half": (
        FILES[-1][0],
        FILES[-1][2],
        "Bayer UtNet2 half-resolution, iteration 4350000",
        {"funit": 32, "preupsample": False},
    ),
    "preupsample": (
        "https://drive.usercontent.google.com/download?id=1xgHafgqRC8ZEGbbXtduSlx9WunD0mgS_&export=download&confirm=t",
        "3d8d5fab966f790f4adbaf1786ca1ee81cb027d9cd45220787247b0af99fd814",
        "Bayer UtNet2 pre-upsampled, iteration 4320000",
        {"funit": 32, "preupsample": True},
    ),
    "wide48": (
        "https://drive.usercontent.google.com/download?id=1uHWoRZQux2m4aAAGxxvTXA-25TzjtcQZ&export=download&confirm=t",
        "a13db60df69de2e107a9470bd419dbcc1bb4861f37e7127159f7ed774dc4ea99",
        "Bayer UtNet2 width48, iteration 5985000",
        {"funit": 48, "preupsample": False},
    ),
}


def main(variant="half", output=None):
    url, checksum, description, configuration = VARIANTS[variant]
    default = "/mnt/external/demosaic/references/rawnind"
    if variant != "half":
        default += "-" + variant
    destination = writable_path(output or default)
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    files = [*FILES[:-1], (url, "utnet2-bayer.pt", checksum)]
    for url, name, expected in files:
        output = destination / name
        if not output.exists():
            temporary = output.with_suffix(".tmp")
            with (
                urllib.request.urlopen(url, timeout=60) as response,
                temporary.open("xb") as handle,
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
        "checkpoint": description,
        "files": records,
    }
    if variant != "half":
        manifest.update(
            variant=variant,
            model_config={"in_channels": 4, "activation": "LeakyReLU", **configuration},
            checksum_scope="SHA256 pins observed publisher-linked bytes, not a separately published SHA256 claim",
        )
    provenance = destination / "provenance.json"
    payload = json.dumps(manifest, indent=2) + "\n"
    if provenance.exists():
        if provenance.read_text() != payload:
            raise ValueError("Existing provenance differs; choose a new reference destination")
    else:
        with provenance.open("x") as handle:
            handle.write(payload)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=VARIANTS, default="half")
    parser.add_argument("--output")
    args = parser.parse_args()
    main(args.variant, args.output)
