"""Preserve complete heldout membership when reusing content vectors."""

import copy
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def extension(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("extend_commons_content_bank")


def row(identity, split="train", **changes):
    return {
        "id": identity,
        "split": split,
        "cache": f"/mnt/external/demosaic/fixture/{identity}.npy",
        "cache_sha256": "0" * 64,
        "shape": [256, 384, 3],
        "bin_factor": 8,
        "dtype": "uint16",
        "color_space": "linear-sRGB",
    } | changes


def test_complete_population_keeps_prior_pools_and_flagged_holdouts_exactly(extension):
    previous = [
        row("old", "reserved", pool="Commons-heldout"),
        row("native", pool="native150"),
        row("protected", pool="protected45"),
    ]
    incoming = [row("train"), row("val", "val", protected_flag=True), row("test", "test")]
    before = copy.deepcopy((previous, incoming))
    selected, locations = extension.population(previous, incoming)
    assert [r["id"] for r in selected] == ["old", "native", "protected", "val", "test"]
    assert locations == [(0, 0), (0, 1), (0, 2), (1, 1), (1, 2)]
    assert selected[3]["protected_flag"] and selected[3]["pool"] == "Commons-heldout"
    assert (previous, incoming) == before
    assert selected[0] is not previous[0]


@pytest.mark.parametrize(
    "fault",
    [
        "old_pool",
        "old_duplicate",
        "new_duplicate",
        "overlap",
        "new_bucket",
        "old_training",
        "pixel_recipe",
    ],
)
def test_incomplete_ambiguous_or_incompatible_populations_fail(extension, fault):
    previous = [row("old", "val", pool="Commons-heldout")]
    incoming = [row("new", "test")]
    if fault == "old_pool":
        previous[0]["pool"] = "unknown"
    elif fault == "old_duplicate":
        previous.append(dict(previous[0]))
    elif fault == "new_duplicate":
        incoming.append(dict(incoming[0]))
    elif fault == "overlap":
        incoming[0]["id"] = "old"
    elif fault == "new_bucket":
        incoming[0]["split"] = "excluded"
    elif fault == "old_training":
        previous[0]["split"] = "train"
    else:
        incoming[0]["bin_factor"] = 4
    with pytest.raises(ValueError):
        extension.population(previous, incoming)


def test_frozen_worker_uses_the_bound_workspace_cache_for_protected_inputs(extension, tmp_path):
    cache = tmp_path / ".cache"
    protected = row("protected", pool="protected45", cache=str(cache / "protected.npy"))
    selected, locations = extension.population([protected], [], workspace_cache=cache)
    assert selected == [protected] and locations == [(0, 0)]
    protected["cache"] = "/mnt/dataz/pictures/raw/personal.npy"
    with pytest.raises(ValueError, match="SSD caches"):
        extension.population([protected], [], workspace_cache=cache)
