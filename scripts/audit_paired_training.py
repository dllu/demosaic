"""Screen paired training references against protected Commons photographs."""

import os

os.environ.setdefault("OMP_NUM_THREADS", "4")

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import rawpy

from demosaic.audit import fingerprint, orientations, thumbnail
from demosaic.paired import verify_file
from demosaic.safety import writable_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paired_manifest", type=Path)
    parser.add_argument("commons_manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paired_bytes, commons_bytes = (
        args.paired_manifest.read_bytes(),
        args.commons_manifest.read_bytes(),
    )
    data = json.loads(paired_bytes)
    if data["split"] != "train":
        raise ValueError("Only screen a separate paired training manifest")
    rows = [json.loads(line) for line in commons_bytes.splitlines()]
    rows = [row for row in rows if row["split"] in ("val", "test")]
    thumbs, hashes, ratios, valid = [], [], [], []
    for index, row in enumerate(rows):
        array = np.load(args.commons_manifest.parent / row["cache"], mmap_mode="r")
        thumb = thumbnail(array)
        thumbs.append(thumb)
        hashes.append(np.stack([fingerprint(t) for t in orientations(thumb)]))
        ratios.append(array.shape[1] / array.shape[0])
        valid.append(thumb.std() > 1e-6)
        if (index + 1) % 500 == 0:
            print(json.dumps({"event": "protected-fingerprint", "sources": index + 1}), flush=True)
    if not rows:
        raise ValueError("No protected Commons sources")
    hashes, ratios, valid = np.stack(hashes), np.asarray(ratios), np.asarray(valid)
    matches, references = [], []
    for scene in data["selection"]:
        record = scene["clean"][0]  # Predeclared filename order, no quality selection.
        verify_file(record["path"], record)
        with rawpy.imread(record["path"]) as decoder:
            rgb = decoder.postprocess(
                half_size=True,
                output_bps=16,
                gamma=(1, 1),
                use_camera_wb=True,
                no_auto_bright=True,
                adjust_maximum_thr=0,
                user_flip=0,
                output_color=rawpy.ColorSpace.sRGB,
            )
        thumb = thumbnail(rgb)
        ratio = rgb.shape[1] / rgb.shape[0]
        informative = bool(thumb.std() > 1e-6)
        distances = np.bitwise_count(hashes ^ fingerprint(thumb)).sum(-1)
        candidates = np.flatnonzero((distances.min(1) <= 16) & valid) if informative else []
        references.append(
            {
                "scene": scene["scene"],
                "reference_sha256": record["sha256"],
                "informative": informative,
                "hash_candidates": len(candidates),
            }
        )
        for index in candidates:
            for orientation in np.flatnonzero(distances[index] <= 16):
                candidate_ratio = ratios[index] if orientation % 2 == 0 else 1 / ratios[index]
                if abs(np.log(candidate_ratio / ratio)) > 0.08:
                    continue
                candidate = orientations(thumbs[index])[orientation]
                correlation = float(
                    np.mean(
                        (candidate - candidate.mean())
                        / candidate.std()
                        * (thumb - thumb.mean())
                        / thumb.std()
                    )
                )
                if correlation >= 0.98:
                    matches.append(
                        {
                            "scene": scene["scene"],
                            "commons_id": rows[index]["id"],
                            "commons_split": rows[index]["split"],
                            "commons_title": rows[index]["title"],
                            "hamming": int(distances[index, orientation]),
                            "correlation": correlation,
                            "orientation": int(orientation),
                        }
                    )
        print(
            json.dumps(
                {"event": "paired-screen", "scene": scene["scene"], "matches_so_far": len(matches)}
            ),
            flush=True,
        )
    report = {
        "paired_manifest_sha256": hashlib.sha256(paired_bytes).hexdigest(),
        "commons_manifest_sha256": hashlib.sha256(commons_bytes).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protected_sources": len(rows),
        "references": references,
        "matches": matches,
        "method": "Linear sRGB LibRaw half-size reference, 32x32 luminance, dihedral dHash256 <=16, aspect log delta <=.08, correlation >=.98",
        "limitation": "Conservative near-duplicate screen. Arbitrary crops, edits, viewpoints and shared scene backgrounds can evade it. No proof of complete scene separation.",
    }
    output = writable_path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"event": "paired-screen-complete", "matches": len(matches)}), flush=True)


if __name__ == "__main__":
    main()
