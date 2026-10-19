import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from demosaic import prepare

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/prepare_commons_local_stage.py"
spec = importlib.util.spec_from_file_location("partial_cache_recovery", SCRIPT)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


@pytest.fixture
def partial(tmp_path, monkeypatch):
    monkeypatch.setattr(recovery.shutil, "disk_usage", lambda _: SimpleNamespace(free=1000 * 2**30))
    monkeypatch.setattr(
        recovery.psutil, "virtual_memory", lambda: SimpleNamespace(available=1000 * 2**30)
    )
    source, output = tmp_path / "failed/prepared4", tmp_path / "new/outputs"
    output.mkdir(parents=True)
    identity = "f" * 40
    expected = {field: "source-field" for field in recovery.PREPARE_FIELDS}
    expected.update(sha1_hex=identity, width=2048, height=2048, download_path="original.jpg")
    selection = output / "selection.jsonl"
    selection.write_text(json.dumps(expected) + "\n")
    relative = Path("images") / identity[:2] / f"{identity}.npy"
    cache = source / relative
    cache.parent.mkdir(parents=True)
    np.save(cache, np.full((512, 512, 3), 1234, dtype=np.uint16), allow_pickle=False)
    row = dict(
        expected,
        id=identity,
        cache=str(relative),
        shape=[512, 512, 3],
        cache_sha256=recovery.sha(cache),
        bin_factor=4,
        color_space="linear-sRGB",
        dtype="uint16",
    )
    manifest = source / "manifest.jsonl.tmp"
    manifest.write_text(json.dumps(row) + "\n")
    stage = tmp_path / "originals"
    stage.mkdir()
    recipe = source / "recipe.json"
    recipe.write_text(
        json.dumps(
            {
                "version": 1,
                "factor": 4,
                "source": str(stage),
                "transfer": "linear-sRGB",
                "dtype": "uint16",
                "selection_manifest_sha256": recovery.sha(selection),
            }
        )
    )
    frozen = source.parent / "worker.py"
    frozen.write_text("# original fixture producer\n")
    (source.parent / "plan.json").write_text(
        json.dumps({"frozen_files": {str(frozen): recovery.sha(frozen)}})
    )
    plan = {
        "root": str(output.parent),
        "stage": str(stage),
        "reserve_gib": 608,
        "recovery": {
            "root": str(source.parent),
            "factors": {
                "4": {
                    "root": str(source),
                    "manifest": recovery.ref(manifest),
                    "recipe": recovery.ref(recipe),
                }
            },
        },
    }
    return plan, output, expected, row, cache


def test_recovery_preserves_failed_cache_and_reuses_exact_pixels_without_decoding(
    partial, monkeypatch
):
    plan, output, expected, row, original = partial
    before, inode = recovery.sha(original), original.stat().st_ino
    result = recovery.reuse_partial_caches(plan, output, [expected], 4)
    copied = output / "prepared4" / row["cache"]
    assert result == {"factor": 4, "copied": 1, "bytes": original.stat().st_size}
    assert original.stat().st_ino == inode != copied.stat().st_ino
    assert recovery.sha(copied) == recovery.sha(original) == before

    def reject_decode(*args, **kwargs):
        raise AssertionError("A verified reused array must not decode its original again")

    monkeypatch.setattr(prepare.Image, "open", reject_decode)
    record, error = prepare.prepare_one(
        dict(row), Path(plan["stage"]), output / "prepared4", 4, 512, 120_000_000
    )
    assert error is None and record["cache_sha256"] == before
    assert np.array_equal(np.load(original), np.load(copied))


@pytest.mark.parametrize(
    "corruption", ["pixels", "attribution", "path", "recipe", "shape", "duplicate", "source-code"]
)
def test_recovery_rejects_unbound_bytes_metadata_and_paths(partial, corruption):
    plan, output, expected, row, original = partial
    info = plan["recovery"]["factors"]["4"]
    if corruption == "source-code":
        (Path(plan["recovery"]["root"]) / "worker.py").write_text("# changed producer\n")
    elif corruption == "pixels":
        array = np.load(original, mmap_mode="r+")
        array[0, 0, 0] += 1
        array.flush()
        del array
    elif corruption == "recipe":
        recipe = recovery.read(info["recipe"]["path"])
        recipe["factor"] = 8
        Path(info["recipe"]["path"]).write_text(json.dumps(recipe))
        info["recipe"] = recovery.ref(info["recipe"]["path"])
    else:
        if corruption == "attribution":
            row["attribution"] = "changed"
        elif corruption == "path":
            row["cache"] = "../escape.npy"
        elif corruption == "shape":
            row["shape"] = [512, 513, 3]
        Path(info["manifest"]["path"]).write_text(
            (json.dumps(row) + "\n") * (2 if corruption == "duplicate" else 1)
        )
        info["manifest"] = recovery.ref(info["manifest"]["path"])
    with pytest.raises(ValueError):
        recovery.reuse_partial_caches(plan, output, [expected], 4)
    assert not (output / "prepared4/manifest.jsonl").exists()
    assert original.exists()
    assert not (output / "escape.npy").exists()


def test_recovery_stops_at_memory_guard_before_copying(partial, monkeypatch):
    plan, output, expected, row, original = partial
    monkeypatch.setattr(
        recovery.psutil, "virtual_memory", lambda: SimpleNamespace(available=23 * 2**30)
    )
    with pytest.raises(ValueError, match="24GiB"):
        recovery.reuse_partial_caches(plan, output, [expected], 4)
    assert not (output / "prepared4" / row["cache"]).exists()
    assert original.exists()


@pytest.mark.parametrize("mismatch", ["failed-status", "owner", "plan"])
def test_failed_or_changed_review_closure_cannot_start_preparation(tmp_path, monkeypatch, mismatch):
    monkeypatch.setenv("CUDA_VISIBLE_DEVICES", "")
    monkeypatch.setattr(recovery.os, "nice", lambda _: None)
    monkeypatch.setattr(recovery, "alive", lambda _: False)
    dependency = {
        "status_path": str(tmp_path / "closure.json"),
        "owner": {"pid": 123, "created": 456.0},
        "plan": {"path": "declared-plan", "sha256": "declared-hash"},
        "success_status": "declared-success",
    }
    state = {
        "controller": dependency["owner"],
        "plan": dependency["plan"],
        "status": dependency["success_status"],
    }
    if mismatch == "failed-status":
        state["status"] = "failed-closure"
    elif mismatch == "owner":
        state["controller"] = {"pid": 123, "created": 789.0}
    else:
        state["plan"] = {"path": "declared-plan", "sha256": "changed-hash"}
    Path(dependency["status_path"]).write_text(json.dumps(state))
    plan = {
        "root": str(tmp_path),
        "work": str(SCRIPT.parents[1]),
        "stage": str(tmp_path / "originals"),
        "frozen_files": {},
        "inputs": [],
        "after_completion": dependency,
        "wait_seconds": 30,
    }
    path = tmp_path / "plan.json"
    path.write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="Review closure did not complete"):
        recovery.run(path)
    assert recovery.read(tmp_path / "status.json")["status"] == "failed-local-preparation"
    assert not (tmp_path / "originals").exists()
