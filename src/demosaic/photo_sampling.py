"""Preserve photographic source draws when curating a subset of a frozen corpus."""

import hashlib
import json
import os
from pathlib import Path


class PhotoSamplingReference:
    """Uniform rejection sampling from an immutable, ordered training-source list.

    Draw the initial identity before checking a reviewed ROI override. Only a
    non-overridden excluded identity consumes retry draws; every other source
    and subsequent geometry RNG state remain identical to the original reader.
    """

    def __init__(self, reference, manifest, rows, *, expected_sha256=None):
        self.path = Path(reference)
        payload = self.path.read_bytes()
        self.sha256 = hashlib.sha256(payload).hexdigest()
        if expected_sha256 is not None and self.sha256 != expected_sha256:
            raise ValueError("Photo sampling reference changed after its training snapshot")
        self.rows = {row["id"]: row for row in rows}
        if not self.rows or len(self.rows) != len(rows):
            raise ValueError("Photo sampling requires nonempty unique active training sources")
        if any(row["split"] != "train" for row in rows):
            raise ValueError("Photo sampling reference is only for training sources")
        identities, seen = [], set()
        for line in payload.splitlines():
            row = json.loads(line)
            identity = row["id"]
            if identity in seen:
                raise ValueError("Photo sampling reference contains duplicate source identities")
            seen.add(identity)
            if row["split"] != "train":
                continue
            identities.append(identity)
            current = self.rows.get(identity)
            if current is not None and (
                row != current
                or os.path.abspath(self.path.parent / row["cache"])
                != os.path.abspath(Path(manifest).parent / current["cache"])
            ):
                raise ValueError("Photo sampling reference changes an active source or cache path")
        if not identities or not self.rows.keys() <= set(identities):
            raise ValueError("Active photo sources must be a subset of the sampling reference")
        self.identities = tuple(identities)

    def initial(self, rng):
        return self.identities[rng.randrange(len(self.identities))]

    def eligible(self, identity, rng):
        while identity not in self.rows:
            identity = self.initial(rng)
        return self.rows[identity]


def require_resume_photo_sampling(previous, current):
    if previous.get("photo_sampling_reference_sha256") != current.get(
        "photo_sampling_reference_sha256"
    ):
        raise ValueError("Resume photo sampling reference differs; initialize a new run")
