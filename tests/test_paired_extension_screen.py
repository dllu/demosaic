import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

spec = importlib.util.spec_from_file_location(
    "screen_paired_extension",
    Path(__file__).resolve().parents[1] / "scripts/screen_paired_extension.py",
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def picture(seed):
    return np.random.default_rng(seed).integers(0, 65536, (128, 160, 3), dtype=np.uint16)


def fixture(tmp_path, monkeypatch):
    protected = tmp_path / "protected.json"
    np.save(tmp_path / "protected.npy", picture(1))
    protected.write_text(
        json.dumps(
            {
                "protected": [
                    {
                        "scene": "heldout",
                        "screen_cache": "protected.npy",
                        "screen_sha256": module.sha(tmp_path / "protected.npy"),
                    }
                ]
            }
        )
    )
    commons = tmp_path / "commons.jsonl"
    rows = []
    for i, split in enumerate(["val", "test", "train"]):
        # A matching train image must never act as a protected holdout.
        np.save(tmp_path / f"commons{i}.npy", picture(2 if i == 2 else 10 + i))
        rows.append(
            {
                "id": f"common{i}",
                "title": f"Photo{i}",
                "split": split,
                "cache": f"commons{i}.npy",
                "cache_sha256": module.sha(tmp_path / f"commons{i}.npy"),
            }
        )
    commons.write_text("".join(json.dumps(r) + "\n" for r in rows))
    records, arrays = [], {}
    for i, array in enumerate([picture(3), np.rot90(picture(1)), picture(2)]):
        raw = tmp_path / f"source{i}.arw"
        raw.write_bytes(f"verified source{i}".encode())
        screen = tmp_path / f"screen{i}.npy"
        np.save(screen, array)
        record = {
            "filename": raw.name,
            "path": str(raw),
            "bytes": raw.stat().st_size,
            "sha1": hashlib.sha1(raw.read_bytes()).hexdigest(),
            "sha256": module.sha(raw),
            "publisher_checksum": {
                "type": "MD5",
                "value": hashlib.md5(raw.read_bytes()).hexdigest(),
            },
        }
        records.append(record)
        arrays[record["sha256"]] = screen
    manifest = tmp_path / "quarantine.json"
    manifest.write_text(
        json.dumps(
            {
                "split": "quarantine",
                "selection": [
                    {"scene": "alias", "split": "quarantine", "clean": records[:2], "noisy": []},
                    {"scene": "new", "split": "quarantine", "clean": records[2:], "noisy": []},
                ],
            }
        )
    )

    def decode(record, output):
        module.verify_file(record["path"], record)
        path = arrays[record["sha256"]]
        return {
            "source_sha256": record["sha256"],
            "screen_cache": str(path),
            "screen_sha256": module.sha(path),
            "identity": {"Model": "Fixture Camera"},
        }

    monkeypatch.setattr(module, "decode_reference", decode)
    return manifest, protected, commons


def test_second_reference_alias_holds_whole_scene_and_preserves_quarantine(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    result = module.screen(*paths, tmp_path / "review")
    assert result["held_scenes"] == ["alias"]
    assert result["screen_clear_scenes"] == ["new"]
    assert result["references"][1]["protected_matches"]
    assert len(result["protected_commons_sources"]) == 2
    cleared = json.loads(Path(result["screen_clear_manifest"]).read_text())
    assert cleared["split"] == cleared["selection"][0]["split"] == "quarantine"
    assert cleared["files"] == 1 and "Pending" in cleared["manual_review"]
    with pytest.raises(ValueError, match="frozen"):
        module.screen(*paths, tmp_path / "review")


def test_commons_overlap_holds_scene_and_changed_cache_is_rejected(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    np.save(tmp_path / "commons0.npy", picture(2))
    rows = [json.loads(line) for line in paths[2].read_text().splitlines()]
    with pytest.raises(ValueError, match="Commons cache changed"):
        module.screen(*paths, tmp_path / "bad-cache")
    rows[0]["cache_sha256"] = module.sha(tmp_path / "commons0.npy")
    paths[2].write_text("".join(json.dumps(row) + "\n" for row in rows))
    result = module.screen(*paths, tmp_path / "overlap")
    assert result["held_scenes"] == ["alias", "new"]
    assert result["references"][-1]["commons_matches"]


def test_interruption_reuses_only_unchanged_reference_outcomes(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    original = module.overlap.matches
    calls = []

    def interrupted(array, pool):
        calls.append(1)
        if len(calls) == 3:
            raise RuntimeError("fixture interruption")
        return original(array, pool)

    monkeypatch.setattr(module.overlap, "matches", interrupted)
    with pytest.raises(RuntimeError, match="fixture interruption"):
        module.screen(*paths, tmp_path / "resume")
    monkeypatch.setattr(module.overlap, "matches", original)
    result = module.screen(*paths, tmp_path / "resume")
    assert len(result["references"]) == 3


def test_screen_rejects_training_and_empty_reference_selection(tmp_path, monkeypatch):
    paths = fixture(tmp_path, monkeypatch)
    data = json.loads(paths[0].read_text())
    data["split"] = "train"
    paths[0].write_text(json.dumps(data))
    with pytest.raises(ValueError, match="quarantined"):
        module.screen(*paths, tmp_path / "train")
    data["split"] = "quarantine"
    data["selection"][0]["clean"] = []
    paths[0].write_text(json.dumps(data))
    with pytest.raises(ValueError, match="clean references"):
        module.screen(*paths, tmp_path / "empty")


@pytest.mark.parametrize("kind", ["duplicate", "unsafe"])
def test_reference_identities_cannot_collide_or_escape_the_ledger(tmp_path, monkeypatch, kind):
    paths = fixture(tmp_path, monkeypatch)
    data = json.loads(paths[0].read_text())
    data["selection"][0]["clean"][1]["sha256"] = (
        data["selection"][0]["clean"][0]["sha256"] if kind == "duplicate" else "../escape"
    )
    paths[0].write_text(json.dumps(data))
    with pytest.raises(ValueError, match="SHA256 reference identities"):
        module.screen(*paths, tmp_path / "unsafe")
    assert not (tmp_path / "unsafe").exists()
