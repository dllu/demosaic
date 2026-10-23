"""Keep source review complete and within its explicit capacity budget."""

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


@pytest.fixture
def contact(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("render_commons_contact_sheets")


@pytest.mark.parametrize("reserve", [255, -1, True, 288.5, float("nan")])
def test_invalid_capacity_is_rejected_before_resource_access(contact, monkeypatch, reserve):
    def unexpected(*args):
        pytest.fail("Invalid reserve must fail before system resource access")

    monkeypatch.setattr(contact.psutil, "virtual_memory", unexpected)
    monkeypatch.setattr(contact.shutil, "disk_usage", unexpected)
    with pytest.raises(ValueError, match="at least256GiB"):
        contact.resources(None, reserve)


def test_exact_declared_capacity_and_memory_boundaries(contact, monkeypatch):
    available = 48 * 2**30
    free = 288 * 2**30
    monkeypatch.setattr(
        contact.psutil, "virtual_memory", lambda: SimpleNamespace(available=available)
    )
    monkeypatch.setattr(contact.shutil, "disk_usage", lambda _: SimpleNamespace(free=free))
    contact.resources("/mnt/external", 288)
    free -= 1
    with pytest.raises(RuntimeError, match="RAM/disk"):
        contact.resources("/mnt/external", 288)
    free += 1
    available -= 1
    with pytest.raises(RuntimeError, match="RAM/disk"):
        contact.resources("/mnt/external", 288)


def test_original_default_reserve_still_applies(contact, monkeypatch):
    monkeypatch.setattr(
        contact.psutil, "virtual_memory", lambda: SimpleNamespace(available=64 * 2**30)
    )
    monkeypatch.setattr(contact.shutil, "disk_usage", lambda _: SimpleNamespace(free=547 * 2**30))
    with pytest.raises(RuntimeError, match="RAM/disk"):
        contact.resources("/mnt/external")


def test_partial_and_incomplete_manifests_cannot_be_reviewed(contact, tmp_path):
    with pytest.raises(ValueError, match="partial"):
        contact.inventory(tmp_path / "manifest.jsonl.tmp", None)
    manifest = tmp_path / "manifest.jsonl"
    selection = tmp_path / "selection.json"
    manifest.write_text("")
    selection.write_text(json.dumps([{"sha1_hex": "a" * 40}]))
    with pytest.raises(ValueError, match="Complete selected-source coverage"):
        contact.inventory(manifest, selection)
