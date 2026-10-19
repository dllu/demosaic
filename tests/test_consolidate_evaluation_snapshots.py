import importlib.util
import json
import os
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/consolidate_evaluation_snapshots.py"
spec = importlib.util.spec_from_file_location("consolidate_evaluation_snapshots", SCRIPT)
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)


def copies(tmp_path):
    canonical, target = tmp_path / "canonical.pt", tmp_path / "target.pt"
    canonical.write_bytes(b"checkpoint contents")
    target.write_bytes(canonical.read_bytes())
    canonical.chmod(0o444)
    return canonical, target, storage.sha(canonical), storage.props(target)


def test_verified_copies_share_immutable_storage_without_aliasing_original(tmp_path):
    canonical, target, digest, expected = copies(tmp_path)
    original = tmp_path / "original.pt"
    original.write_bytes(canonical.read_bytes())
    storage.replace_verified_copy(target, canonical, digest, expected)
    assert target.samefile(canonical) and not target.samefile(original)
    assert target.stat().st_mode & 0o222 == 0
    original.write_bytes(b"next training update")
    assert target.read_bytes() == b"checkpoint contents"


@pytest.mark.parametrize("damage", ["bytes", "writable_canonical", "extra_target_alias"])
def test_invalid_copies_refuse_before_replacement(tmp_path, damage):
    canonical, target, digest, expected = copies(tmp_path)
    if damage == "bytes":
        target.write_bytes(b"corrupt checkpoint!")
        expected = storage.props(target)
    elif damage == "writable_canonical":
        canonical.chmod(0o644)
    else:
        os.link(target, tmp_path / "unexpected.pt")
    old = target.read_bytes()
    with pytest.raises(ValueError):
        storage.replace_verified_copy(target, canonical, digest, expected)
    assert target.read_bytes() == old and not target.samefile(canonical)


def test_failed_post_replace_verification_restores_original_inode_and_bytes(tmp_path, monkeypatch):
    canonical, target, digest, expected = copies(tmp_path)
    original_sha = storage.sha
    observations = 0

    def fail_second_target_read(path):
        nonlocal observations
        if Path(path) == target:
            observations += 1
            if observations == 2:
                raise OSError("Injected post-replacement read failure")
        return original_sha(path)

    monkeypatch.setattr(storage, "sha", fail_second_target_read)
    with pytest.raises(OSError, match="post-replacement"):
        storage.replace_verified_copy(target, canonical, digest, expected)
    assert storage.inode(storage.props(target)) == storage.inode(expected)
    assert target.read_bytes() == b"checkpoint contents" and not target.samefile(canonical)
    assert not list(tmp_path.glob("*.new-link-*")) and not list(tmp_path.glob("*.old-link-*"))


def test_original_archive_alias_is_excluded_before_any_metadata_change(tmp_path):
    base = tmp_path / "owned"
    evaluation = base / "evaluation"
    original = base / "models" / "original.pt"
    original.parent.mkdir(parents=True)
    original.write_bytes(b"original archived weights")
    digest = storage.sha(original)
    entries = []
    for index in range(2):
        panel = evaluation / f"panel-{index}"
        path = panel / "weights" / f"weights-{digest}.pt"
        path.parent.mkdir(parents=True)
        if index == 0:
            os.link(original, path)
        else:
            path.write_bytes(original.read_bytes())
        (panel / "summary.json").write_text(
            json.dumps({"native_crops": [], "models": [{"sha256": digest, "snapshot": str(path)}]})
        )
        entries.append({"path": str(path)})
    inventory = tmp_path / "inventory.json"
    inventory.write_text(json.dumps({"candidate_groups": [{"files": entries}]}))
    expected = storage.props(original)
    with pytest.raises(ValueError, match="No eligible"):
        storage.prepare(tmp_path / "operation", evaluation, inventory, [])
    assert storage.props(original) == expected and original.stat().st_mode & 0o200


def test_apply_rejects_a_plan_pointing_outside_its_evaluation_tree(tmp_path):
    operation = tmp_path / "operation"
    operation.mkdir()
    evaluation = tmp_path / "evaluation"
    evaluation.mkdir()
    source = tmp_path / "unrelated-original.pt"
    source.write_bytes(b"original weights")
    expected = storage.props(source)
    plan = {
        "driver": storage.ref(SCRIPT),
        "evaluation": str(evaluation),
        "protected": [],
        "unchanged_report_metric_native_artifacts": [],
        "original_archive_properties": {},
        "groups": [{"canonical": str(source), "targets": [], "sha256": storage.sha(source)}],
    }
    (operation / "plan.json").write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="escapes eligible"):
        storage.apply(operation)
    assert storage.props(source) == expected and not (operation / "claim").exists()
