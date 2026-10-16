import fcntl
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "freeze_rebinned_manifest",
    Path(__file__).resolve().parents[1] / "scripts/freeze_rebinned_manifest.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture(tmp_path):
    base = tmp_path / "base.jsonl"
    base.write_text(
        "".join(
            json.dumps({"id": s, "split": s}) + "\n" for s in ["train", "val", "test", "excluded"]
        )
    )
    producer = tmp_path / "producer"
    producer.mkdir()
    (producer / ".prepare.lock").touch()
    rows = []
    for split in ["train", "val", "test"]:
        cache = producer / f"{split}.npy"
        np.save(cache, np.zeros((64, 64, 3), np.uint16))
        rows.append(
            {
                "id": split,
                "split": split,
                "cache": cache.name,
                "bin_factor": 4,
                "dtype": "uint16",
                "color_space": "linear-sRGB",
                "shape": [64, 64, 3],
                "cache_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
            }
        )
    prepared = producer / "manifest.jsonl"
    prepared.write_text("".join(json.dumps(r) + "\n" for r in rows))
    (producer / "recipe.json").write_text(
        json.dumps(
            {
                "factor": 4,
                "selection_manifest_sha256": hashlib.sha256(base.read_bytes()).hexdigest(),
            }
        )
    )
    return base, prepared, rows


def test_frozen_rebinning_preserves_membership_and_cannot_overwrite(tmp_path):
    base, prepared, rows = fixture(tmp_path)
    original = base.read_bytes()
    output = tmp_path / "frozen"
    report = module.freeze(base, prepared, output, min_size=64)
    assert report["counts"] == {"train": 1, "val": 1, "test": 1}
    assert report["base_excluded_ids"] == ["excluded"]
    actual = [json.loads(s) for s in (output / "manifest.jsonl").read_text().splitlines()]
    assert [(r["id"], r["split"]) for r in actual] == [(r["id"], r["split"]) for r in rows]
    assert all(Path(r["cache"]).is_absolute() for r in actual)
    assert base.read_bytes() == original
    with pytest.raises(ValueError, match="already exists"):
        module.freeze(base, prepared, output, min_size=64)


@pytest.mark.parametrize("change", ["partial", "split", "producer-running"])
def test_incomplete_or_changed_rebinning_never_creates_frozen_manifest(tmp_path, change):
    base, prepared, rows = fixture(tmp_path)
    output = tmp_path / "frozen"
    if change == "partial":
        rows.pop()
    if change == "split":
        rows[0]["split"] = "test"
    prepared.write_text("".join(json.dumps(r) + "\n" for r in rows))
    with (prepared.parent / ".prepare.lock").open("r") as lock:
        if change == "producer-running":
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises((ValueError, RuntimeError)):
            module.freeze(base, prepared, output, min_size=64)
    assert not (output / "manifest.jsonl").exists()
