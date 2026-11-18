"""Prepare and audit a larger whole-scene corpus from checked Commons caches."""

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch

from demosaic.experiments.artifacts import reference, write_json
from demosaic.photo_epoch_order import reader_policy, shuffled_photo_rows, training_policy
from demosaic.scene_context import scene_preview
from demosaic.scene_data import sample_scene_recipe
from demosaic.scene_training_data import ScenePhotoDataset, scene_seed


def read_catalogue(path):
    with path.open() as stream:
        rows = [json.loads(line) for line in stream if line.strip()]
    if not rows or len({row["id"] for row in rows}) != len(rows):
        raise ValueError("Require unique source IDs in each catalogue")
    return rows


def select_rows(source, pilot_train, pilot_development, output):
    previous = {row["id"] for row in read_catalogue(pilot_train)}
    held = {row["id"] for row in read_catalogue(pilot_development)}
    rows = read_catalogue(source)
    pool = {row["id"] for row in rows if row["split"] == "train"}
    if previous & held or not (previous | held) <= pool:
        raise ValueError("Pilot splits differ from the curated training cohort")

    excluded = Counter()
    selected = []
    path = output / "manifest-train.jsonl"
    with path.open("x") as stream:
        for row in rows:
            if row["split"] != "train":
                excluded[row["split"]] += 1
                continue
            if row["id"] in held:
                excluded["pilot-development"] += 1
                continue
            h, w, _ = row["shape"]
            if min(h, w) < 512 or h * w > 4_000_000:
                excluded["scene-size"] += 1
                continue
            cache = str((source.parent / row["cache"]).absolute())
            selected.append(row | {"cache": cache})
            stream.write(json.dumps(selected[-1], sort_keys=True) + "\n")
    retained = {row["id"] for row in selected}
    if not previous <= retained:
        raise ValueError("Expanded source cohort lost an eligible pilot training source")
    return path, selected, excluded, len(previous)


def write_order(path, rows, *, seed, steps, scenes_per_step):
    manifest = reference(path)
    count = len(rows)
    slots = steps * scenes_per_step
    values = np.empty(slots, dtype=np.int32)
    for epoch, start in enumerate(range(0, slots, count)):
        permutation = shuffled_photo_rows(count, seed, epoch, manifest["sha256"])
        end = min(start + count, slots)
        values[start:end] = permutation[: end - start]
    payload = path.parent / "ordinary-photo-order.npy"
    np.save(payload, values, allow_pickle=False)
    order = path.parent / "photo-epoch-order.json"
    write_json(
        order,
        {
            "format": "photo-epoch-order-v1",
            "source_manifest": manifest,
            "ordered_train_ids_sha256": hashlib.sha256(
                ("\n".join(row["id"] for row in rows) + "\n").encode()
            ).hexdigest(),
            "reader_policy": reader_policy(seed, 0, 0, 0, None),
            "training_policy": training_policy({"batch_size": scenes_per_step}),
            "horizon_steps": steps,
            "order": {"path": payload.name, "sha256": reference(payload)["sha256"]},
            "scope": "Every slot selects one whole photo observation. All of its native crops share that observation.",
        },
    )
    return order


def coverage(epoch, replacement, previous, *, steps, scenes_per_step):
    seen = [set(), set(), set()]
    milestones = {}
    requested = {step * scenes_per_step for step in (2_000, 20_000, steps)}
    first_pass = None
    for index in range(steps * scenes_per_step):
        for ids, dataset in zip(seen, (epoch, replacement, previous), strict=True):
            ids.add(dataset.source_row(index)["id"])
        slots = index + 1
        if first_pass is None and len(seen[0]) == len(epoch.rows):
            first_pass = slots
        if slots in requested:
            milestones[slots // scenes_per_step] = {
                "scene_draws": slots,
                "expanded_shuffled_epochs": len(seen[0]),
                "expanded_replacement": len(seen[1]),
                "pilot_replacement": len(seen[2]),
            }
    total = steps * scenes_per_step
    for start in range(0, total, len(epoch.rows)):
        ids = {
            epoch.source_row(index)["id"]
            for index in range(start, min(start + len(epoch.rows), total))
        }
        if len(ids) != min(len(epoch.rows), total - start):
            raise ValueError("Repeated source inside a photographic epoch")
    return milestones, first_pass


def smoke(dataset, steps, scenes_per_step):
    # Choose the first new and old size-band example for each Bayer phase,
    # using only source rows and camera seeds until opening the eight caches.
    records = {}
    for index in range(steps * scenes_per_step):
        short = min(dataset.source_row(index)["shape"][:2])
        key = "short-512-to-767" if short < 768 else "short-at-least-768"
        recipe = sample_scene_recipe(scene_seed(dataset.seed, index, "camera-noise"))
        name = f"{key}/{recipe.pattern}"
        if name in records:
            continue
        began = time.perf_counter()
        sample = dataset[index]
        seconds = time.perf_counter() - began
        obs = sample.observation
        rgb_preview, grid = scene_preview(obs.packed, obs.colors, obs.wb, obs.matrix)
        if (
            tuple(sample.metadata["native_hw"]) != grid.native_hw
            or not torch.isfinite(rgb_preview).all()
        ):
            raise ValueError("Invalid preview for the sampled whole observation")
        for slot, (x, y, w, h) in enumerate(sample.metadata["boxes_xywh"]):
            raw = obs.packed[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            if not torch.equal(sample.crops["packed"][slot], raw):
                raise ValueError("Cropped RAW differs from the whole observation")
            if not torch.equal(sample.crops["target"][slot], obs.target[:, y : y + h, x : x + w]):
                raise ValueError("Cropped target differs from the whole observation")
        replay = dataset[index]
        if replay.metadata != sample.metadata:
            raise ValueError("Same-index scene replay differs")
        records[name] = sample.metadata | {"preview_hw": grid.preview_hw, "reader_seconds": seconds}
        if len(records) == 8:
            break
    return records


def prepare(source, pilot_train, pilot_development, output, *, seed, steps, scenes_per_step):
    if steps < 1 or scenes_per_step < 1:
        raise ValueError("Steps and scene draws per update must be positive")
    output.mkdir(parents=True)
    manifest, rows, excluded, old_size = select_rows(source, pilot_train, pilot_development, output)
    order = write_order(manifest, rows, seed=seed, steps=steps, scenes_per_step=scenes_per_step)
    order_binding = reference(order)
    baseline = ScenePhotoDataset(pilot_train, seed=seed)
    replacement = ScenePhotoDataset(manifest, seed=seed)
    epoch = ScenePhotoDataset(
        manifest,
        seed=seed,
        photo_epoch_order=order,
        photo_epoch_order_sha256=order_binding["sha256"],
    )
    milestones, first_pass = coverage(
        epoch, replacement, baseline, steps=steps, scenes_per_step=scenes_per_step
    )
    checks = smoke(epoch, steps, scenes_per_step)
    report = {
        "producer": reference(__file__),
        "input": reference(source),
        "pilot_train": reference(pilot_train),
        "pilot_development": reference(pilot_development),
        "train_manifest": reference(manifest),
        "photo_epoch_order": order_binding,
        "order_payload": reference(output / "ordinary-photo-order.npy"),
        "seed": seed,
        "steps": steps,
        "scenes_per_step": scenes_per_step,
        "crops_per_scene": epoch.crops_per_scene,
        "crop_native_side": epoch.patch_size,
        "eligible": len(rows),
        "added": len(rows) - old_size,
        "excluded": dict(excluded),
        "coverage": milestones,
        "first_complete_pass_scene_draw": first_pass,
        "first_complete_pass_update": (
            None if first_pass is None else (first_pass + scenes_per_step - 1) // scenes_per_step
        ),
        "sample_checks": checks,
        "scope": "Declared future source order and actual CPU reader/preview checks only. No model forwards, training, inference or quality measurement.",
    }
    write_json(output / "audit.json", report)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("pilot_train", type=Path)
    parser.add_argument("pilot_development", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--steps", type=int, default=50_000)
    parser.add_argument("--scenes-per-step", type=int, default=2)
    args = parser.parse_args()
    torch.set_num_threads(2)
    prepare(
        args.source,
        args.pilot_train,
        args.pilot_development,
        args.output,
        seed=args.seed,
        steps=args.steps,
        scenes_per_step=args.scenes_per_step,
    )
