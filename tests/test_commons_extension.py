import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

spec = importlib.util.spec_from_file_location(
    "expand_commons", Path(__file__).resolve().parents[1] / "scripts/expand_commons.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def picture(seed):
    rng = np.random.default_rng(seed)
    image = Image.new("RGB", (128, 128), (20, 30, 50))
    draw = ImageDraw.Draw(image)
    for _ in range(20):
        x, y, w, h = rng.integers(0, 95, 4).tolist()
        draw.rectangle((x, y, x + w, y + h), fill=tuple(rng.integers(20, 240, 3).tolist()))
    return np.asarray(image).astype(np.uint16) * 257


def manifest(tmp_path, name, samples):
    directory = tmp_path / name
    directory.mkdir()
    rows = []
    for identity, split, array in samples:
        cache = directory / (identity + ".npy")
        np.save(cache, array)
        rows.append(
            {
                "id": identity,
                "split": split,
                "cache": cache.name,
                "cache_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
                "bin_factor": 8,
                "color_space": "linear-sRGB",
                "dtype": "uint16",
                "license": "CC BY 4.0",
                "credit": "Fixture author",
            }
        )
    path = directory / "manifest.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_extension_preserves_old_sets_and_reserves_new_holdout_clusters(tmp_path):
    base = manifest(
        tmp_path,
        "base",
        [(s, s, picture(i)) for i, s in enumerate(["train", "val", "test", "excluded"], 1)],
    )
    added = manifest(
        tmp_path,
        "new",
        [
            ("duplicate-train", "train", np.rot90(picture(1)[:, ::-1])),
            ("duplicate-val", "train", np.rot90(picture(2))),
            ("duplicate-test", "train", picture(3)),
            ("duplicate-excluded", "train", picture(4)),
            ("fresh-a", "train", picture(10)),
            ("fresh-z", "train", picture(10)),
            ("z-train", "train", picture(12)),
            ("a-test", "test", picture(12)),
            ("fresh-val", "val", picture(13)),
            ("fresh-test", "test", picture(14)),
            ("flat", "train", np.full((128, 128, 3), 1000, np.uint16)),
            ("train", "train", picture(1)),
        ],
    )
    before = base.read_bytes()
    cache = tmp_path / "fingerprints.sqlite3"
    report = module.audit_extension(base, added, tmp_path / "expanded", cache)
    actual = {r["id"]: r for r in module.rows(tmp_path / "expanded/manifest.jsonl")}
    for old in module.rows(base):
        row = actual[old["id"]]
        assert (
            row["split"] == old["split"]
            and row["cache_sha256"] == old["cache_sha256"]
            and row["credit"] == old["credit"]
        )
    for identity in [
        "duplicate-train",
        "duplicate-val",
        "duplicate-test",
        "duplicate-excluded",
        "fresh-z",
        "z-train",
        "flat",
    ]:
        assert actual[identity]["split"] == "excluded"
    assert actual["fresh-a"]["split"] == "train"
    assert all(actual[s]["split"] == "reserved" for s in ["a-test", "fresh-val", "fresh-test"])
    assert report["counts"] == {"train": 2, "val": 1, "test": 1, "excluded": 8, "reserved": 3}
    assert report["added_train"] == 1 and report["new_reserved"] == 3
    assert report["skipped_existing_ids"] == ["train"]
    assert base.read_bytes() == before
    second = module.audit_extension(base, added, tmp_path / "expanded-again", cache)
    assert second["cache"]["computed"] == 0 and second["cache"]["reused"] > 0
    with pytest.raises(ValueError, match="already exists"):
        module.audit_extension(base, added, tmp_path / "expanded", cache)


def test_new_bridge_cannot_admit_a_cluster_linked_to_old_validation(tmp_path):
    rng = np.random.default_rng(7)
    a = rng.normal(size=(32, 32))
    a -= a.mean()
    a /= a.std()
    b = rng.normal(size=a.shape)
    b -= b.mean()
    b -= np.mean(a * b) * a
    b /= b.std()

    def field(angle):
        grey = np.rint((0.5 + 0.1 * (np.cos(angle) * a + np.sin(angle) * b)) * 65535).astype(
            np.uint16
        )
        return np.repeat(grey[..., None], 3, axis=-1)

    base = manifest(tmp_path, "base", [("protected", "val", field(0))])
    added = manifest(
        tmp_path, "new", [("early", "train", field(0.2)), ("bridge", "train", field(0.1))]
    )
    report = module.audit_extension(
        base, added, tmp_path / "expanded", tmp_path / "fp.sqlite3", max_hamming=32
    )
    actual = {r["id"]: r["split"] for r in module.rows(tmp_path / "expanded/manifest.jsonl")}
    assert actual == {"protected": "val", "early": "excluded", "bridge": "excluded"}
    assert len(report["verified_union_edges"]) == 2


def test_fingerprint_cache_detects_changed_pixels_and_rejects_mixed_recipes(tmp_path):
    base = manifest(tmp_path, "base", [("base", "val", picture(1))])
    added = manifest(tmp_path, "new", [("new", "train", picture(20))])
    cache = tmp_path / "fp.sqlite3"
    module.audit_extension(base, added, tmp_path / "one", cache)
    image = base.parent / "base.npy"
    stamp = image.stat()
    with image.open("r+b") as handle:
        handle.seek(-2, 2)
        handle.write(b"\x01\x02")
    os.utime(image, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1000000000))
    with pytest.raises(ValueError, match="checksum changed"):
        module.audit_extension(base, added, tmp_path / "two", cache)
    records = module.rows(added)
    records[0]["bin_factor"] = 4
    added.write_text("".join(json.dumps(r) + "\n" for r in records))
    with pytest.raises(ValueError, match="mix cache recipes"):
        module.audit_extension(base, added, tmp_path / "three", cache)


def test_extension_output_lock_prevents_competing_audits(tmp_path):
    base = manifest(tmp_path, "base", [("base", "val", picture(1))])
    added = manifest(tmp_path, "new", [("new", "train", picture(20))])
    output = tmp_path / "output"
    output.mkdir()
    with (output / ".extension.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="owns this extension"):
            module.audit_extension(base, added, output, tmp_path / "fp.sqlite3")
    assert not (output / "manifest.jsonl").exists()
