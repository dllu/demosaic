import importlib.util
import os
import sys
import time
from argparse import Namespace
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("archive_compactor", SCRIPTS / "compact_project_archives.py")
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


def fixture_plan(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "REPO", tmp_path)
    root = tmp_path / ".cache/archives"
    root.mkdir(parents=True)
    for name in ["one.jpg", "two.jpg", "different.jpg", "outside-alias.jpg"]:
        path = root / name
        data = bytearray(b"a" * 131072)
        if name == "different.jpg":
            data[40000] = 98  # Difference lies outside the sampled regions.
        path.write_bytes(data)
        old = time.time() - 3 * 86400
        os.utime(path, (old, old))
    os.link(root / "outside-alias.jpg", tmp_path / "unknown-alias.jpg")
    monkeypatch.setattr(storage.engine, "checked_root", storage.checked_root)
    monkeypatch.setattr(storage.engine, "SUFFIXES", storage.SUFFIXES)
    plan = tmp_path / "plan.json.gz"
    storage.plan(Namespace(root=[str(root)], age_days=2, output=plan))
    return root, plan


def test_full_hash_distinguishes_sample_collision_and_preserves_unknown_alias(tmp_path, monkeypatch):
    root, plan = fixture_plan(tmp_path, monkeypatch)
    data = storage.engine.read(plan)
    assert len(data["groups"]) == 1
    assert {Path(p).name for i in data["groups"][0]["inodes"] for p in i["paths"]} == {
        "one.jpg", "two.jpg"
    }
    outside = storage.engine.identity(root / "outside-alias.jpg")
    storage.apply(Namespace(plan=plan, journal=tmp_path / "journal", output=tmp_path / "result.json"))
    assert (root / "one.jpg").samefile(root / "two.jpg")
    assert not (root / "one.jpg").samefile(root / "different.jpg")
    assert not (root / "one.jpg").stat().st_mode & 0o222
    assert storage.engine.identity(root / "outside-alias.jpg") == outside


def test_changed_input_is_rejected_before_link_or_mode_changes(tmp_path, monkeypatch):
    root, plan = fixture_plan(tmp_path, monkeypatch)
    (root / "two.jpg").write_bytes(b"changed after plan")
    before = {p: storage.engine.identity(p) for p in root.iterdir()}
    with pytest.raises(AssertionError):
        storage.apply(Namespace(plan=plan, journal=tmp_path / "journal", output=tmp_path / "result.json"))
    assert {p: storage.engine.identity(p) for p in root.iterdir()} == before


def test_policy_binds_plan_bytes(tmp_path, monkeypatch):
    root, plan = fixture_plan(tmp_path, monkeypatch)
    with plan.open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(AssertionError):
        storage.apply(Namespace(plan=plan, journal=tmp_path / "journal", output=tmp_path / "result.json"))
    assert not (root / "one.jpg").samefile(root / "two.jpg")


@pytest.mark.parametrize("root", ["/mnt/external/qi", "/home/dllu/pictures", str(storage.REPO / ".cache"),
                                  str(storage.REPO / ".cache/gfx-qualitative-20231231")])
def test_reject_original_media_and_protected_photo_roots(root):
    with pytest.raises(ValueError):
        storage.checked_root(root)


def test_reject_symlink_root(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "REPO", tmp_path)
    real = tmp_path / ".cache/real"
    real.mkdir(parents=True)
    link = tmp_path / ".cache/link"
    link.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        storage.checked_root(link)
