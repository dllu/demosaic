"""Prepare a deterministic ordinary-photo epoch order for one frozen recipe."""

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import numpy as np
import yaml

from demosaic.data import CleanDataset
from demosaic.photo_epoch_order import file_hash, reader_policy, training_policy
from demosaic.train import training_domain

READER_KEYS = (
    "seed",
    "patch_size",
    "synthetic_fraction",
    "flat_fraction",
    "augmentation_downsample",
    "weak_texture_fraction",
    "fine_weak_texture_fraction",
    "flat_chroma_stops",
    "optical_blur_probability",
    "photographic_low_contrast_fraction",
    "reviewed_roi_catalogue",
    "reviewed_roi_fraction",
    "reviewed_roi_catalogue_sha256",
    "photo_sampling_reference_manifest",
    "photo_sampling_reference_sha256",
)


def build_order(reader, config):
    """Enumerate selection metadata only; never load/augment a sample."""
    steps, batch = config["steps"], config.get("batch_size", 4)
    if type(steps) is not int or steps <= 0 or type(batch) is not int or batch <= 0:
        raise ValueError("Photo epoch preparation needs positive integer steps/batch")
    if config.get("optimizer_batch_groups", 1) != 1 or reader.photo_epoch_order is not None:
        raise ValueError("Prepare an ordinary-photo order from an unmodified single-group reader")
    count = len(reader.rows)
    if count > np.iinfo(np.int32).max:
        raise ValueError("Photographic epoch order exceeds int32 source indices")
    manifest_hash = file_hash(reader.manifest)
    order = np.full(steps * batch, -1, dtype=np.int32)
    domains, families, old_visits, new_visits, ordinary_visits = (Counter() for _ in range(5))
    permutation, offset, epoch = [], count, -1
    first_full_step = None
    for step in range(1, steps + 1):
        domain = training_domain(
            step, reader.seed, config.get("paired_fraction", 0), config.get("raw_clean_fraction", 0)
        )
        domains[domain] += 1
        if domain != "commons":
            continue
        for index in range((step - 1) * batch, step * batch):
            rng = random.Random(reader.seed + index)
            draw = rng.random()
            if draw < reader.flat_fraction + reader.synthetic_fraction:
                families["procedural"] += 1
                continue
            initial = (
                reader.photo_sampling_reference.initial(rng)
                if reader.photo_sampling_reference
                else reader.rows[rng.randrange(count)]
            )
            region = reader.reviewed_roi_for_index(index)
            if region is not None:
                identity = region.record["id"]
                old_visits[identity] += 1
                new_visits[identity] += 1
                families["reviewed"] += 1
                continue
            previous = (
                reader.photo_sampling_reference.eligible(initial, rng)
                if reader.photo_sampling_reference
                else initial
            )
            old_visits[previous["id"]] += 1
            if offset == count:
                epoch += 1
                permutation = list(range(count))
                random.Random(f"photo-epoch-v1:{reader.seed}:{epoch}:{manifest_hash}").shuffle(
                    permutation
                )
                offset = 0
            position = permutation[offset]
            offset += 1
            order[index] = position
            identity = reader.rows[position]["id"]
            ordinary_visits[identity] += 1
            new_visits[identity] += 1
            families["ordinary"] += 1
            if first_full_step is None and len(ordinary_visits) == count:
                first_full_step = step
    summary = {
        "domains": dict(domains),
        "Commons_families": dict(families),
        "available_train_photos": count,
        "with_replacement_unique_photos": len(old_visits),
        "epoch_order_unique_photos": len(new_visits),
        "ordinary_unique_photos": len(ordinary_visits),
        "first_complete_ordinary_epoch_step": first_full_step,
        "complete_ordinary_epochs": families["ordinary"] // count,
        "partial_epoch_draws": families["ordinary"] % count,
        "ordinary_visit_histogram_including_zero": dict(
            sorted(Counter(ordinary_visits.get(r["id"], 0) for r in reader.rows).items())
        ),
    }
    return order, summary


def prepare(recipe_path, output):
    output.mkdir(parents=True, exist_ok=False)
    recipe_payload = recipe_path.read_bytes()
    config = yaml.safe_load(recipe_payload)
    (output / "reader-recipe.yaml").write_bytes(recipe_payload)
    reader = CleanDataset(config["manifest"], **{k: config[k] for k in READER_KEYS if k in config})
    values, summary = build_order(reader, config)
    path = output / "ordinary-photo-order.npy"
    np.save(path, values, allow_pickle=False)
    manifest = {"path": str(reader.manifest.resolve()), "sha256": file_hash(reader.manifest)}
    header = {
        "format": "photo-epoch-order-v1",
        "source_manifest": manifest,
        "ordered_train_ids_sha256": hashlib.sha256(
            ("\n".join(r["id"] for r in reader.rows) + "\n").encode()
        ).hexdigest(),
        "reader_policy": reader_policy(
            reader.seed,
            reader.flat_fraction,
            reader.synthetic_fraction,
            reader.reviewed_roi_fraction,
            reader.reviewed_rois.sha256 if reader.reviewed_rois else None,
        ),
        "training_policy": training_policy(config),
        "horizon_steps": config["steps"],
        "order": {"path": path.name, "sha256": file_hash(path)},
        "algorithm": "Python Random.shuffle of active row indices for each epoch; independent seed string photo-epoch-v1:{reader_seed}:{zero_based_epoch}:{manifest_sha256}. Only ordinary-photo slots advance the epoch.",
        "summary": summary,
        "scope": "Prepared future ordering only; no trained-quality result. Family/domain/reviewed selection remains fixed. No __getitem__, augmentation, sensor observation or neural execution; reviewed catalogue constructor validates its caches.",
    }
    header_path = output / "photo-epoch-order.json"
    header_path.write_text(json.dumps(header, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"header": str(header_path), "sha256": file_hash(header_path), **summary}))
    return header_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recipe", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    prepare(args.recipe, args.output)
