"""Root headroom is operational; RAM and external training reserves still apply."""

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def driver(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("train_spectral_trial")


@pytest.mark.parametrize("launch", [False, True])
def test_127GiB_root_is_usable_only_with_explicit_revised_reserve(driver, launch):
    assert not driver.resources_allow({}, 64, 127, 540, launch=launch)
    assert driver.resources_allow({"root_disk_reserve_gib": 64}, 64, 127, 540, launch=launch)


@pytest.mark.parametrize("ram,disk,external", [(23, 127, 540), (64, 63, 540), (64, 127, 499)])
def test_revised_root_reserve_does_not_remove_runtime_limits(driver, ram, disk, external):
    assert not driver.resources_allow({"root_disk_reserve_gib": 64}, ram, disk, external)


def test_launch_still_requires_48GiB_RAM_and_disk_headroom(driver):
    plan = {"root_disk_reserve_gib": 64}
    assert not driver.resources_allow(plan, 47, 127, 540, launch=True)
    assert not driver.resources_allow(plan, 64, 64, 540, launch=True)
    assert not driver.resources_allow(plan, 64, 127, 500, launch=True)
    assert driver.resources_allow(plan, 48, 65, 501, launch=True)


@pytest.mark.parametrize("value", [0, 63, 129, float("nan"), float("inf")])
def test_invalid_or_excessively_small_root_reserves_are_refused(driver, value):
    with pytest.raises(ValueError, match="Root disk reserve"):
        driver.root_disk_reserve({"root_disk_reserve_gib": value})
