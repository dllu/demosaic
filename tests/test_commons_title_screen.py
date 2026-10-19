"""Preserve Unicode title features, reserved anchors and withholding semantics."""

import copy
import importlib
from pathlib import Path

import pytest


@pytest.fixture
def title(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("screen_commons_titles")


def entry(identity, text, **extra):
    return {"id": identity, "title": text, "author": "Photographer", "split": "reserved", **extra}


def test_features_fold_accents_case_and_drop_numbers_and_camera_extensions(title):
    assert title.terms("File:Église_Saint-Pierre_2022_DSCF001.jpg") == title.terms(
        "File:EGLISE Saint Pierre 1999 IMG.tiff"
    )
    assert not title.terms("File:1234_DSCF0001.jpg")


def test_same_site_with_different_dates_uses_new_reserved_anchor_without_admission(title):
    anchors = [entry("a", "File:Cathedral courtyard 2024.jpg", anchor_origin="new-reserved")]
    queries = [entry("b", "File:Cathedral courtyard 2025.jpg", split="train")]
    before = copy.deepcopy((anchors, queries))
    result = title.retrieve(anchors, queries)
    assert result[0]["decision"] == "withhold-title-risk"
    assert result[0]["neighbors"][0]["score"] == pytest.approx(1)
    assert result[0]["neighbors"][0]["origin"] == "new-reserved"
    assert (anchors, queries) == before


@pytest.mark.parametrize("text", ["File:123_DSCF.jpg", "File:qxzpql.jpg"])
def test_missing_feature_neighbor_is_withheld_not_called_a_bad_image(title, text):
    result = title.retrieve([entry("a", "File:Cathedral courtyard.jpg")], [entry("b", text)])
    assert result[0]["decision"] == "withhold-uninformative-title"
    assert result[0]["neighbors"] == []


@pytest.mark.parametrize("damage", ["duplicate_anchor", "duplicate_query", "self_anchor", "empty"])
def test_ambiguous_or_missing_title_pools_are_rejected(title, damage):
    anchors, queries = [entry("a", "File:Stone tower.jpg")], [entry("b", "File:Forest.jpg")]
    if damage == "duplicate_anchor":
        anchors *= 2
    elif damage == "duplicate_query":
        queries *= 2
    elif damage == "self_anchor":
        queries[0]["id"] = "a"
    else:
        anchors = []
    with pytest.raises(ValueError):
        title.retrieve(anchors, queries)
