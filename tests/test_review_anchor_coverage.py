"""Extra heldout references must never hide a missing or changed admission target."""

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def module(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("review_downloaded_commons")


def sample(module):
    base = []
    for i, split in enumerate(["val", "test", "reserved", "train"]):
        base.append(
            {field: None for field in module.SOURCE_FIELDS}
            | {
                "id": str(i),
                "split": split,
                "cache_sha256": "0" * 64,
                "shape": [256, 320, 3],
                "bin_factor": 8,
                "dtype": "uint16",
                "color_space": "linear-sRGB",
            }
        )
    anchors = [dict(r, pool="Commons-heldout") for r in base[:3]]
    anchors.append(dict(anchors[0], id="extra-protected-holdout"))
    return base, anchors


def test_conservative_extra_holdout_preserves_all_required_source_pixels(module):
    base, anchors = sample(module)
    assert module.validate_anchor_coverage(base, anchors) == 4


@pytest.mark.parametrize(
    "fault", ["missing", "pixels", "shape", "author", "training", "duplicate", "pool"]
)
def test_incomplete_changed_or_mislabeled_anchor_bank_fails(module, fault):
    base, anchors = sample(module)
    if fault == "missing":
        anchors.pop(0)
    elif fault == "pixels":
        anchors[0]["cache_sha256"] = "1" * 64
    elif fault == "shape":
        anchors[0]["shape"] = [320, 256, 3]
    elif fault == "author":
        anchors[0]["author"] = "someone else"
    elif fault == "training":
        anchors[-1]["split"] = "train"
    elif fault == "duplicate":
        anchors.append(dict(anchors[0]))
    else:
        anchors[-1]["pool"] = "unknown"
    with pytest.raises(ValueError):
        module.validate_anchor_coverage(base, anchors)
