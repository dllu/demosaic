"""Unknown cache failures and attribution drift must remain fatal."""

import copy
import importlib
import json
from pathlib import Path

import pytest


@pytest.fixture
def review(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    return importlib.import_module("commons_preparation_review")


def fixture(review):
    sources = [
        {key: None for key in review.SOURCE_FIELDS} | {"sha1_hex": c * 40} for c in ["a", "b"]
    ]
    prepared = {
        str(f): [
            sources[0]
            | {"id": "a" * 40, "bin_factor": f, "dtype": "uint16", "color_space": "linear-sRGB"}
        ]
        for f in [4, 8]
    }
    failures = {str(f): [{"id": "b" * 40, "error": "invalid ICC"}] for f in [4, 8]}
    return sources, prepared, failures, {"b" * 40: "invalid ICC"}


def test_exact_reviewed_failures_preserve_complete_cross_scale_partition(review):
    args = fixture(review)
    before = copy.deepcopy(args)
    assert review.validate_coverage(*args) == {"a" * 40}
    assert args == before
    sources, prepared, failures, approved = args
    assert review.validate_coverage(
        sources, {"4": prepared["4"]}, {"4": failures["4"]}, approved
    ) == {"a" * 40}


@pytest.mark.parametrize(
    "damage",
    [
        "unreviewed",
        "error",
        "missing-error",
        "duplicate-error",
        "missing-cache",
        "duplicate-cache",
        "wrong-source",
        "attribution",
        "pixel-recipe",
        "scale",
    ],
)
def test_mismatched_or_incomplete_failure_accounting_stops(review, damage):
    sources, prepared, failures, approved = fixture(review)
    if damage == "unreviewed":
        approved = {}
    elif damage == "error":
        failures["8"][0]["error"] = "different decoder failure"
    elif damage == "missing-error":
        failures["8"] = []
    elif damage == "duplicate-error":
        failures["8"] *= 2
    elif damage == "missing-cache":
        prepared["4"] = []
    elif damage == "duplicate-cache":
        prepared["4"] *= 2
    elif damage == "wrong-source":
        prepared["4"][0]["id"] = "c" * 40
    elif damage == "attribution":
        prepared["4"][0]["author"] = "someone else"
    elif damage == "pixel-recipe":
        prepared["4"][0]["color_space"] = "unmanaged-RGB"
    else:
        failures.pop("8")
    with pytest.raises(ValueError):
        review.validate_coverage(sources, prepared, failures, approved)


@pytest.fixture
def ledger(review, tmp_path):
    def write(name, value):
        p = tmp_path / name
        p.write_text(json.dumps(value))
        return review.ref(p)

    sources, _, _, _ = fixture(review)
    producer = write("producer.json", {"producer": "fixed"})
    selection = write("selection.json", sources)
    inspection = write("inspection.json", {"sources": ["b" * 40]})
    image = write("image.json", {"source_preview": True})
    actual = write(
        "actual.json",
        {
            "actual_viewed": True,
            "reviewed_ids": ["b" * 40],
            "inspection": inspection,
            "image": image,
        },
    )
    value = {
        "format_version": 1,
        "status": "reviewed-source-preparation-failures-withheld",
        "producer_plan": producer,
        "selection": selection,
        "source_review": actual,
        "sources": [
            {
                "id": "b" * 40,
                "decision": "withhold",
                "reason": "unreadable ICC",
                "expected_error": "invalid ICC",
                "source": sources[1],
            }
        ],
    }
    path = tmp_path / "review.json"
    path.write_text(json.dumps(value))
    return path, producer, selection, value


def test_review_binds_actual_viewing_source_records_and_evidence(review, ledger):
    path, producer, selection, _ = ledger
    result = review.load_failure_review(path, producer, selection)
    assert result["errors"] == {"b" * 40: "invalid ICC"}
    assert len(result["inputs"]) == 6
    assert review.load_failure_review(None, producer, selection) == {"errors": {}, "inputs": []}


@pytest.mark.parametrize(
    "fault", ["producer", "selection", "source", "decision", "duplicate", "viewing", "evidence"]
)
def test_changed_or_unreviewed_failure_ledger_is_rejected(review, ledger, fault):
    path, producer, selection, value = ledger
    if fault == "producer":
        value["producer_plan"]["sha256"] = "0" * 64
    elif fault == "selection":
        value["selection"]["sha256"] = "0" * 64
    elif fault == "source":
        value["sources"][0]["source"]["author"] = "different author"
    elif fault == "decision":
        value["sources"][0]["decision"] = "admit"
    elif fault == "duplicate":
        value["sources"] *= 2
    else:
        actual_path = Path(value["source_review"]["path"])
        actual = review.read(actual_path)
        if fault == "viewing":
            actual["actual_viewed"] = False
        else:
            Path(actual["image"]["path"]).write_text("changed source evidence")
        actual_path.write_text(json.dumps(actual))
        value["source_review"] = review.ref(actual_path)
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError):
        review.load_failure_review(path, producer, selection)
