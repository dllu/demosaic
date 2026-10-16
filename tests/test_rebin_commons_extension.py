import copy
import fcntl
import hashlib
import importlib.util
import json
from collections import Counter
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

spec = importlib.util.spec_from_file_location(
    "rebin_commons_extension",
    Path(__file__).resolve().parents[1] / "scripts/rebin_commons_extension.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def write_rows(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def refresh_audit(expanded, base):
    rows = module.records(expanded)
    module.atomic_json(
        expanded.parent / "audit.json",
        {
            "base_sha256": module.digest(base),
            "manifest_sha256": module.digest(expanded),
            "counts": dict(Counter(r["split"] for r in rows)),
        },
    )


@pytest.fixture
def corpus(tmp_path):
    source = tmp_path / "originals"
    source.mkdir()
    pixels = np.arange(2048 * 2048 * 3, dtype=np.uint32).reshape(2048, 2048, 3) % 251
    Image.fromarray(pixels.astype(np.uint8)).save(source / "new.png")
    original_hash = hashlib.sha1((source / "new.png").read_bytes()).hexdigest()

    def row(name, split):
        identity = original_hash if name == "new" else hashlib.sha1(name.encode()).hexdigest()
        cache = tmp_path / "eight" / (identity + ".npy")
        cache.parent.mkdir(exist_ok=True)
        np.save(cache, np.full((256, 256, 3), 10000, np.uint16))
        return {
            "id": identity,
            "sha1": identity,
            "sha1_hex": identity,
            "split": split,
            "author": "Fixture author",
            "license": "CC BY-SA 4.0",
            "download_path": "new.png",
            "width": 2048,
            "height": 2048,
            "cache": str(cache),
            "cache_sha256": module.digest(cache),
            "shape": [256, 256, 3],
            "bin_factor": 8,
            "color_space": "linear-sRGB",
            "dtype": "uint16",
        }

    old = [row(s, s) for s in ["train", "val", "test", "excluded"]]
    base = tmp_path / "base/manifest.jsonl"
    write_rows(base, old)
    expanded = tmp_path / "expanded/manifest.jsonl"
    write_rows(
        expanded,
        old + [row("new", "train"), row("held", "reserved"), row("duplicate", "excluded")],
    )
    refresh_audit(expanded, base)
    base_four = []
    for original in old:
        if original["split"] == "excluded":
            continue
        r = copy.deepcopy(original)
        cache = tmp_path / "old-four" / (r["id"] + ".npy")
        cache.parent.mkdir(exist_ok=True)
        np.save(cache, np.full((512, 512, 3), 10000, np.uint16))
        r.update(
            cache=str(cache), cache_sha256=module.digest(cache), shape=[512, 512, 3], bin_factor=4
        )
        base_four.append(r)
    frozen_base = tmp_path / "base-four/manifest.jsonl"
    write_rows(frozen_base, base_four)
    module.atomic_json(
        frozen_base.parent / "audit.json",
        {
            "base_sha256": module.digest(base),
            "manifest_sha256": module.digest(frozen_base),
            "recipe": {"factor": 4},
        },
    )
    output = tmp_path / "new-four"
    return base, expanded, frozen_base, output, source


def test_prepare_only_new_train_and_merge_reuses_original_caches(corpus):
    base, expanded, frozen_base, output, source = corpus
    before = {p: module.digest(p) for p in [base, expanded, frozen_base]}
    assert module.prepare_extension(base, expanded, output, source)["selected"] == 1
    assert len(list((output / "prepared4/images").rglob("*.npy"))) == 1
    assert not (output / "audit/manifest.jsonl").exists()
    report = module.freeze_extension(base, expanded, frozen_base, output)
    assert report["counts"] == {"train": 2, "val": 1, "test": 1}
    assert report["new_training_caches"] == 1 and report["reused_base_caches"] == 3
    assert len(report["reserved_ids"]) == 1 and len(report["excluded_ids"]) == 2
    assert report["membership_sha256"] == module.digest(expanded)
    assert report["manifest_sha256"] == module.digest(output / "audit/manifest.jsonl")
    actual = module.records(output / "audit/manifest.jsonl")
    assert actual[:3] == module.records(frozen_base)
    assert all(module.digest(r["cache"]) == r["cache_sha256"] for r in actual)
    for path, identity in before.items():
        assert module.digest(path) == identity
    with pytest.raises(ValueError, match="already exists"):
        module.freeze_extension(base, expanded, frozen_base, output)


@pytest.mark.parametrize(
    "change", ["partial-base", "partial-new", "split", "author", "duplicate", "wrong-pixels"]
)
def test_partial_or_changed_rebinning_cannot_publish(corpus, change):
    base, expanded, frozen_base, output, source = corpus
    module.prepare_extension(base, expanded, output, source)
    path = frozen_base if change == "partial-base" else output / "prepared4/manifest.jsonl"
    rows = module.records(path)
    if change.startswith("partial"):
        rows.pop()
    elif change == "split":
        rows[0]["split"] = "val"
    elif change == "author":
        rows[0]["author"] = "Lost credit"
    elif change == "wrong-pixels":
        np.save(rows[0]["cache"], np.zeros((256, 256, 3), np.uint16))
    else:
        rows.append(copy.deepcopy(rows[0]))
    write_rows(path, rows)
    if change == "partial-base":
        audit = json.loads((path.parent / "audit.json").read_text())
        audit["manifest_sha256"] = module.digest(path)
        module.atomic_json(path.parent / "audit.json", audit)
    with pytest.raises(ValueError):
        module.freeze_extension(base, expanded, frozen_base, output)
    assert not (output / "audit/manifest.jsonl").exists()


@pytest.mark.parametrize("change", ["old-split", "new-heldout"])
def test_even_consistent_receipts_cannot_change_old_or_add_active_holdout(corpus, change):
    base, expanded, _, output, source = corpus
    rows = module.records(expanded)
    if change == "old-split":
        rows[1]["split"] = "train"
    else:
        rows[-2]["split"] = "test"
    write_rows(expanded, rows)
    refresh_audit(expanded, base)
    with pytest.raises(ValueError, match="protected split|must remain reserved"):
        module.prepare_extension(base, expanded, output, source)
    assert not (output / "audit/manifest.jsonl").exists()


@pytest.mark.parametrize("lockfile", [".rebin.lock", "prepared4/.prepare.lock"])
def test_running_producer_or_competing_merge_cannot_publish(corpus, lockfile):
    base, expanded, frozen_base, output, source = corpus
    module.prepare_extension(base, expanded, output, source)
    with (output / lockfile).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match="owns|still running"):
            module.freeze_extension(base, expanded, frozen_base, output)
    assert not (output / "audit/manifest.jsonl").exists()
