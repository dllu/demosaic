"""Prevent holdout omissions and incompatible feature-cache reuse."""

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def bank(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("build_commons_content_bank")


def row(identity="a", **changes):
    return {
        "id": identity,
        "cache": f"/mnt/external/demosaic/fixtures/{identity}.npy",
        "cache_sha256": "0" * 64,
        "shape": [256, 384, 3],
        "bin_factor": 8,
        "dtype": "uint16",
        "color_space": "linear-sRGB",
        "split": "train",
    } | changes


def test_all_heldout_assignments_retained_without_training_or_excluded_rows(bank):
    base = [
        row(str(i), split=split)
        for i, split in enumerate(["train", "val", "test", "reserved", "excluded"])
    ]
    additional = [
        row("camera", pool="native150"),
        row("protected", pool="protected45"),
        row("other", pool="candidates34"),
    ]
    result = bank.anchors(base, additional)
    assert [r["id"] for r in result] == ["1", "2", "3", "camera", "protected"]
    assert [r["split"] for r in result[:3]] == ["val", "test", "reserved"]
    assert "pool" not in base[1]


@pytest.mark.parametrize(
    "changes",
    [
        {"cache": "/mnt/dataz/pictures/raw/personal.raf"},
        {"bin_factor": 4},
        {"shape": [191, 300, 3]},
        {"dtype": "float32"},
        {"color_space": "camera-RGB"},
    ],
)
def test_wrong_storage_and_incompatible_recipes_rejected(bank, changes):
    with pytest.raises(ValueError):
        bank.anchors([row(split="val", **changes)], [])


@pytest.mark.parametrize(
    "changes",
    [
        {"cache_sha256": "1" * 64},
        {"shape": [384, 256, 3]},
        {"bin_factor": 4},
        {"dtype": "float32"},
        {"color_space": "sRGB"},
        {"id": "different"},
    ],
)
def test_reuse_requires_pixel_identity_and_all_recipe_fields(bank, changes):
    assert bank.reused_locations([row(**changes)], [[row()]]) == [None]


def test_reuse_allows_verified_identical_pixel_bytes_at_new_path_and_preserves_mapping(bank):
    selected = [row("b"), row("a", cache="/mnt/external/demosaic/alias.npy", split="reserved")]
    assert bank.reused_locations(selected, [[row("a")], [row("b")]]) == [(1, 0), (0, 0)]
    with pytest.raises(ValueError, match="Ambiguous reusable"):
        bank.reused_locations(selected, [[row("a")], [row("a")]])


@pytest.mark.parametrize("ram,disk", [(47, 600), (60, 547)])
def test_shared_resource_guards_stop_before_inference(bank, monkeypatch, ram, disk):
    monkeypatch.setattr(
        bank.psutil, "virtual_memory", lambda: SimpleNamespace(available=ram * 2**30)
    )
    monkeypatch.setattr(bank.shutil, "disk_usage", lambda _: SimpleNamespace(free=disk * 2**30))
    with pytest.raises(RuntimeError):
        bank.resources("/mnt/external")
