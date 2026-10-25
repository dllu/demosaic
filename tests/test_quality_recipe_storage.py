from pathlib import Path

import pytest
import train_quality_recipes as recipes


def test_internal_outputs_preserve_external_input_headroom():
    root = recipes.REPO / ".cache/quality-storage-test"
    policy = recipes.storage_policy(root, root / "work/artifacts")
    assert policy["internal_artifacts"]
    assert policy["phase_start_internal_free_GiB"] == 128
    assert policy["runtime_internal_reserve_GiB"] == 96
    assert policy["phase_start_external_free_GiB"] == policy["runtime_external_reserve_GiB"] == 208


def test_external_outputs_keep_existing_resource_reserves():
    root = recipes.REPO / ".cache/quality-storage-test"
    policy = recipes.storage_policy(root, Path("/mnt/external/demosaic/quality-storage-test"))
    assert not policy["internal_artifacts"]
    assert policy["phase_start_internal_free_GiB"] == 32
    assert policy["runtime_internal_reserve_GiB"] == 16
    assert policy["phase_start_external_free_GiB"] == 256
    assert policy["runtime_external_reserve_GiB"] == 128


@pytest.mark.parametrize("path", ["../outside", "work/../../../outside", "work-adjacent"])
def test_internal_output_cannot_escape_frozen_workspace(path):
    root = recipes.REPO / ".cache/quality-storage-test"
    with pytest.raises(ValueError, match="artifacts"):
        recipes.storage_policy(root, root / path)


def test_worktree_outside_cache_is_rejected():
    root = recipes.REPO / "quality-storage-test"
    with pytest.raises(ValueError, match="workspace"):
        recipes.storage_policy(root, root / "work/artifacts")
