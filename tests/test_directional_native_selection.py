"""Fresh parent coverage must not be mixed with stale or duplicate baselines."""

import importlib.util
from pathlib import Path

import pytest


@pytest.fixture
def worker(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").absolute()))
    path = Path("scripts/close_directional_interval_review.py")
    spec = importlib.util.spec_from_file_location("directional_closure", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def crops(label, digest):
    return [
        {
            "model_label": label,
            "checkpoint_sha256": digest * 64,
            "source_id": f"photo-{i}",
            "scene": "same-scene",
            "prepared_crop": {"id": f"tile-{i}"},
        }
        for i in range(2)
    ]


@pytest.mark.parametrize("kind", ["synthetic", "camera"])
@pytest.mark.parametrize("fresh_parent", [False, True])
def test_fresh_parent_replaces_old_parent_and_camera_keeps_only_channel_RawNIND(
    worker, kind, fresh_parent
):
    fresh = crops("V78", "a") + crops("V79", "b")
    parent, channel, global_gain = (
        crops("V63", "c"),
        crops("RawNIND:cfa-channel", "d"),
        crops("RawNIND:cfa-ls", "d"),
    )
    retained = parent + channel + global_gain
    if fresh_parent:
        fresh += parent
    selected = worker.select_retained(fresh, retained, kind, "c" * 64, "d" * 64)
    assert selected == ([] if fresh_parent else parent) + (channel if kind == "camera" else [])


@pytest.mark.parametrize("kind", ["synthetic", "camera"])
@pytest.mark.parametrize("problem", ["partial", "duplicate"])
def test_incomplete_fresh_parent_cannot_be_filled_by_an_old_parent(worker, kind, problem):
    fresh = crops("V78", "a") + crops("V79", "b")
    parent = crops("V63", "c")
    fresh += parent[:1] if problem == "partial" else [parent[0], parent[0]]
    with pytest.raises(AssertionError, match="Fresh parent coverage"):
        worker.select_retained(
            fresh, parent + crops("RawNIND:cfa-channel", "d"), kind, "c" * 64, "d" * 64
        )


def test_duplicate_camera_reference_does_not_pass_a_count_only_check(worker):
    fresh = crops("V78", "a") + crops("V79", "b") + crops("V63", "c")
    channel = crops("RawNIND:cfa-channel", "d")
    with pytest.raises(AssertionError):
        worker.select_retained(fresh, [channel[0], channel[0]], "camera", "c" * 64, "d" * 64)
