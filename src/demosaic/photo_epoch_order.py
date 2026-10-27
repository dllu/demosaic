"""Bind ordinary photographic draws to an immutable per-epoch permutation."""

import hashlib
import json
from pathlib import Path

import numpy as np


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def reader_policy(seed, flat, synthetic, reviewed, catalogue_hash):
    return {
        "seed": seed,
        "flat_fraction": flat,
        "synthetic_fraction": synthetic,
        "reviewed_roi_fraction": reviewed,
        "reviewed_roi_catalogue_sha256": catalogue_hash if reviewed else None,
    }


def training_policy(config):
    return {
        "batch_size": config.get("batch_size", 4),
        "paired_fraction": config.get("paired_fraction", 0.0),
        "raw_clean_fraction": config.get("raw_clean_fraction", 0.0),
        "optimizer_batch_groups": config.get("optimizer_batch_groups", 1),
    }


class PhotoEpochOrder:
    """O(1) random access, independent of loader workers, visit order or resume.

    Payload entries index the exact ordered active training rows; -1 marks all
    procedural, reviewed-ROI and non-Commons slots. Only ordinary photographs
    consume the permutations. Missing/misrouted slots fail instead of falling
    back to sampling with replacement.
    """

    def __init__(self, path, manifest, rows, policy, *, expected_sha256=None):
        self.path = Path(path)
        self.sha256 = file_hash(self.path)
        if expected_sha256 is not None and self.sha256 != expected_sha256:
            raise ValueError("Photographic epoch order changed after its snapshot")
        self.header = json.loads(self.path.read_bytes())
        if self.header["format"] != "photo-epoch-order-v1":
            raise ValueError("Unknown photographic epoch order format")
        if file_hash(manifest) != self.header["source_manifest"]["sha256"]:
            raise ValueError("Photographic epoch order source manifest differs")
        identities = [r["id"] for r in rows]
        ids_hash = hashlib.sha256(("\n".join(identities) + "\n").encode()).hexdigest()
        if (
            not rows
            or len(set(identities)) != len(rows)
            or any(r["split"] != "train" for r in rows)
            or ids_hash != self.header["ordered_train_ids_sha256"]
        ):
            raise ValueError("Photographic epoch order training rows differ")
        if policy != self.header["reader_policy"]:
            raise ValueError("Photographic epoch order reader policy differs")
        payload = self.header["order"]
        if Path(payload["path"]).name != payload["path"]:
            raise ValueError("Photographic epoch order payload must be a sibling file")
        payload_path = self.path.parent / payload["path"]
        if file_hash(payload_path) != payload["sha256"]:
            raise ValueError("Photographic epoch order payload hash differs")
        self.values = np.load(payload_path, mmap_mode="r", allow_pickle=False)
        horizon = self.header["horizon_steps"]
        batch = self.header["training_policy"]["batch_size"]
        if (
            type(horizon) is not int
            or horizon <= 0
            or type(batch) is not int
            or batch <= 0
            or self.values.dtype != np.int32
            or self.values.shape != (horizon * batch,)
            or np.any(self.values < -1)
            or np.any(self.values >= len(rows))
        ):
            raise ValueError("Photographic epoch order shape, dtype or bounds differ")
        self.rows = rows

    def ordinary(self, index):
        if not 0 <= index < len(self.values) or self.values[index] < 0:
            raise ValueError("No planned ordinary photograph at this dataset index")
        return self.rows[int(self.values[index])]

    def require_training(self, config):
        if (
            training_policy(config) != self.header["training_policy"]
            or config.get("optimizer_batch_groups", 1) != 1
            or config["steps"] != self.header["horizon_steps"]
        ):
            raise ValueError("Photographic epoch order training layout/horizon differs")


def bind_photo_epoch_order(config, records):
    path = config.get("photo_epoch_order")
    if path is None:
        if config.get("photo_epoch_order_sha256") is not None:
            raise ValueError("Photographic epoch order hash requires its header")
        return None
    policy = reader_policy(
        config.get("seed", 42),
        config.get("flat_fraction", 0.0),
        config.get("synthetic_fraction", 0.2),
        config.get("reviewed_roi_fraction", 0.0),
        config.get("reviewed_roi_catalogue_sha256"),
    )
    order = PhotoEpochOrder(
        path,
        config["manifest"],
        [r for r in records if r["split"] == "train"],
        policy,
        expected_sha256=config.get("photo_epoch_order_sha256"),
    )
    order.require_training(config)
    config["photo_epoch_order_sha256"] = order.sha256
    return order


def require_resume_photo_epoch_order(previous, current):
    if previous.get("photo_epoch_order_sha256") != current.get("photo_epoch_order_sha256"):
        raise ValueError("Resume photographic epoch order differs; initialize a new run")
