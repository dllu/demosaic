import importlib.util
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stage_commons_local.py"
spec = importlib.util.spec_from_file_location("stage_commons_local", SCRIPT)
staging = importlib.util.module_from_spec(spec)
spec.loader.exec_module(staging)


@pytest.mark.parametrize("budget,maximum,reserve", [(0, 1, 224), (1, 0, 224), (1, 1, 223)])
def test_invalid_limits_refuse_before_creating_a_stage(tmp_path, budget, maximum, reserve):
    root = SCRIPT.parents[1] / ".cache" / f"never-created-{tmp_path.name}-{id(tmp_path)}"
    assert not root.exists()
    with pytest.raises(ValueError, match="positive bounded selection"):
        staging.select(
            root,
            tmp_path,
            tmp_path / "unused.py",
            byte_budget=budget,
            max_images=maximum,
            reserve_gib=reserve,
        )
    assert not root.exists()


def test_insufficient_space_refuses_before_creating_a_stage(tmp_path, monkeypatch):
    root = SCRIPT.parents[1] / ".cache" / f"never-created-space-{id(tmp_path)}"
    monkeypatch.setattr(staging.shutil, "disk_usage", lambda _: SimpleNamespace(free=0))
    with pytest.raises(ValueError, match="reserve exceeds current free space"):
        staging.select(
            root,
            tmp_path,
            tmp_path / "unused.py",
            byte_budget=16 * 2**30,
            max_images=5000,
            reserve_gib=224,
        )
    assert not root.exists()


def test_changed_root_refuses_before_reading_database(tmp_path, monkeypatch):
    monkeypatch.setattr(staging, "writable_path", lambda path: Path(path).resolve())
    (tmp_path / "plan.json").write_text(json.dumps({"root": str(tmp_path / "elsewhere")}))
    with pytest.raises(ValueError, match="root differs"):
        staging.run(tmp_path)
    assert not (tmp_path / "quality_images.sqlite3").exists()


@pytest.mark.parametrize("field", ["license", "sha1_hex", "attribution"])
def test_changed_source_fields_refuse_before_lock_or_network(tmp_path, monkeypatch, field):
    monkeypatch.setattr(staging, "writable_path", lambda path: Path(path).resolve())

    def forbidden():
        raise AssertionError("Tampered source metadata reached download setup")

    monkeypatch.setattr(staging, "lock_downloads", forbidden)
    row = {
        "page_id": 3,
        "sha1_hex": "f" * 40,
        "license": "CC BY 4.0",
        "attribution": "Original public attribution",
        "byte_size": 50,
        "status": "pending",
    }
    selection = tmp_path / "selected.json"
    selection.write_text(json.dumps([row]))
    plan = {
        "root": str(tmp_path),
        "driver": staging.ref(SCRIPT),
        "selection": staging.ref(selection),
        "downloader_sources": [],
        "byte_budget": 100,
    }
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    changed = dict(row, **{field: "changed"})
    with sqlite3.connect(tmp_path / "quality_images.sqlite3") as db:
        db.execute(
            "CREATE TABLE images(page_id INTEGER PRIMARY KEY,sha1_hex TEXT,license TEXT,"
            "attribution TEXT,byte_size INTEGER,status TEXT)"
        )
        db.execute("INSERT INTO images VALUES(?,?,?,?,?,?)", tuple(changed.values()))
    with pytest.raises(ValueError, match="Immutable attribution/source fields changed"):
        staging.run(tmp_path)
