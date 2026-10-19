import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/freeze_reviewed_commons_extension.py"
spec = importlib.util.spec_from_file_location("reviewed_commons", SCRIPT)
extension = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extension)


def fixture():
    rows = [
        {"id": "a", "split": "train", "author": "photographer-a"},
        {"id": "b", "split": "train", "author": "photographer-b"},
        {"id": "c", "split": "reserved", "reserved_split": "val"},
    ]
    review = {
        "manual_source_content_screen_complete": True,
        "all_candidate_thumbnails_actually_viewed": 3,
        "eligible_train_ids": ["a"],
        "withheld_train_ids": ["b"],
        "new_reserved_ids": ["c"],
    }
    return rows, review


def test_review_preserves_reserved_and_source_metadata_without_mutating_input():
    rows, review = fixture()
    result = extension.reviewed_rows(rows, review)
    assert result[0] == rows[0] and result[2] == rows[2]
    assert result[1]["split"] == "excluded" and result[1]["author"] == "photographer-b"
    assert result[1]["original_split"] == "train"
    assert rows[1]["split"] == "train"


@pytest.mark.parametrize(
    "damage",
    [
        "reserved_promotion",
        "unknown",
        "overlap",
        "missing_train",
        "missing_reserved",
        "duplicate_decision",
    ],
)
def test_review_cannot_promote_holdouts_or_admit_omitted_or_ambiguous_sources(damage):
    rows, review = fixture()
    if damage == "reserved_promotion":
        review["eligible_train_ids"].append("c")
        review["new_reserved_ids"] = []
    elif damage == "unknown":
        review["eligible_train_ids"].append("protected-scene")
    elif damage == "overlap":
        review["eligible_train_ids"].append("b")
    elif damage == "missing_train":
        review["withheld_train_ids"] = []
    elif damage == "missing_reserved":
        review["new_reserved_ids"] = []
    else:
        review["eligible_train_ids"].append("a")
    with pytest.raises(ValueError):
        extension.reviewed_rows(rows, review)


@pytest.mark.parametrize(
    "key,value",
    [
        ("manual_source_content_screen_complete", False),
        ("all_candidate_thumbnails_actually_viewed", 2),
    ],
)
def test_incomplete_source_content_review_is_not_admission(key, value):
    rows, review = fixture()
    review[key] = value
    with pytest.raises(ValueError, match="[Cc]ontent"):
        extension.reviewed_rows(rows, review)


def test_duplicate_candidate_identities_cannot_hide_a_source():
    rows, review = fixture()
    rows.append(dict(rows[0]))
    with pytest.raises(ValueError, match="Duplicate candidate"):
        extension.reviewed_rows(rows, review)


def test_raw_holdout_labels_must_be_reserved_before_extension_admission():
    rows, review = fixture()
    rows[2]["split"] = "val"
    with pytest.raises(ValueError, match="Unexpected candidate split"):
        extension.reviewed_rows(rows, review)


def test_changed_review_bytes_fail_before_they_can_change_membership(tmp_path):
    path = tmp_path / "review.json"
    path.write_text('{"status":"before"}')
    receipt = extension.ref(path)
    assert extension.checked(receipt) == {"status": "before"}
    path.write_text('{"status":"after"}')
    with pytest.raises(ValueError, match="Changed review/source"):
        extension.checked(receipt)
