"""Freeze a training-only Commons subset supporting native320 after final area2."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from demosaic.data import CleanDataset
from demosaic.safety import writable_path


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def prepare(manifest, output, expected_sha256):
    manifest = Path(manifest).resolve()
    master = ref(manifest)
    if master["sha256"] != expected_sha256:
        raise ValueError("Master manifest differs from the declared source")
    records = [json.loads(line) for line in manifest.read_text().splitlines()]
    selected, rejected = [], []
    redirected = 0
    for row in records:
        if row["split"] != "train":
            continue
        if row.get("bin_factor") != 4:
            raise ValueError("Context preparation requires the original 4x caches")
        if len(row["shape"]) != 3 or row["shape"][2] != 3:
            raise ValueError("Expected an HWC RGB cache shape")
        if min(row["shape"][:2]) < 640:
            rejected.append(row["id"])
            continue
        copied = row.copy()
        if not Path(copied["cache"]).is_absolute():
            copied["cache"] = str((manifest.parent / copied["cache"]).absolute())
            redirected += 1
        selected.append(copied)
    ids = [row["id"] for row in selected]
    if not selected or len(set(ids)) != len(ids):
        raise ValueError("Expected a nonempty unique training-only selection")
    output = writable_path(output)
    if output.exists():
        raise ValueError("Choose a fresh output directory")
    output.mkdir(parents=True)
    target = output / "manifest4.jsonl"
    target.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in selected))
    torch.set_num_threads(2)
    if torch.cuda.is_initialized():
        raise RuntimeError("CPU cohort preparation must not initialize CUDA")
    # Deterministic coverage of both marginal-size and larger caches; never select
    # using a trained model or an image-quality score.
    marginal = sorted(selected, key=lambda row: (min(row["shape"][:2]), row["id"]))[:16]
    spaced = [selected[i * (len(selected) - 1) // 15] for i in range(16)]
    samples = []
    for row in marginal + spaced:
        cache = Path(row["cache"])
        observed = ref(cache)
        if observed["sha256"] != row["cache_sha256"]:
            raise ValueError("Sampled prepared cache differs from its manifest")
        array = np.load(cache, mmap_mode="r", allow_pickle=False)
        if array.dtype != np.uint16 or tuple(array.shape) != tuple(row["shape"]):
            raise ValueError("Sampled cache dtype/shape differs")
        data = CleanDataset(target, patch_size=320, seed=54, synthetic_fraction=0,
                            flat_fraction=0, augmentation_downsample=2, records=[row])
        value = data[0]["rgb"]
        if value.shape != (3, 320, 320) or value.dtype != torch.float32 or not value.is_contiguous():
            raise ValueError("Actual augmented context has an unexpected representation")
        if not torch.isfinite(value).all() or value.min() < 0 or value.max() > 1 + 8 * torch.finfo(value.dtype).eps:
            raise ValueError("Actual augmented context is outside the declared finite range")
        samples.append({"id": row["id"], "cache": observed, "shape": row["shape"],
                        "augmented_F32_sha256": hashlib.sha256(value.numpy().tobytes()).hexdigest()})
    assert ref(manifest) == master and not torch.cuda.is_initialized()
    receipt = {
        "status": "prepared-training-only-native320-context-cohort-no-quality-claim",
        "driver": ref(__file__), "master": master, "manifest": ref(target),
        "original_splits": dict(Counter(row["split"] for row in records)),
        "selection": "Existing train split only; bin4 HWC caches with both dimensions >=640; no image resizing or new source admission.",
        "selected_train_sources": len(selected), "rejected_small_train_sources": len(rejected),
        "selected_IDs_newline_SHA256": hashlib.sha256(("\n".join(sorted(ids))+"\n").encode()).hexdigest(),
        "rejected_IDs_newline_SHA256": hashlib.sha256(("\n".join(sorted(rejected))+"\n").encode()).hexdigest(),
        "relative_cache_paths_made_absolute": redirected, "source_native_size": 320,
        "common_loss_native_size": 256, "candidate_extra_native_border": 32,
        "actual_CPU_photo_samples": samples, "sampled_cache_SHA_dtype_shape_exact": True,
        "CUDA_initialized": False, "source_HDD_reads": False,
        "limits": "Metadata-only membership selection plus 32 actual CPU photo/geometry/PSF/area2 checks. Does not rehash all selected caches, train a model, establish generalization or replace the full corpus/default.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"receipt": ref(output / "receipt.json"), "selected": len(selected),
                      "CPU_samples": len(samples)}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest4", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args()
    prepare(args.manifest4, args.output, args.expected_sha256)
