"""Account for explicitly reviewed source failures without relaxing cache coverage."""

import hashlib
import json
from pathlib import Path

SOURCE_FIELDS = (
    "title",
    "page_url",
    "original_url",
    "author",
    "license",
    "license_url",
    "attribution",
    "credit",
    "sha1",
    "sha1_hex",
    "download_path",
    "width",
    "height",
)


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked(item):
    require(ref(item["path"]) == item, "Changed failure-review evidence")
    return read(item["path"])


def load_failure_review(path, producer, selection):
    if path is None:
        return {"errors": {}, "inputs": []}
    ledger = read(path)
    require(
        ledger["format_version"] == 1
        and ledger["status"] == "reviewed-source-preparation-failures-withheld",
        "Unrecognized source-failure review",
    )
    require(
        ledger["producer_plan"] == producer and ledger["selection"] == selection,
        "Failure review belongs to another producer/selection",
    )
    checked(producer)
    selected = checked(selection)
    by_id = {row["sha1_hex"]: row for row in selected}
    require(len(by_id) == len(selected), "Duplicate selected source identity")
    review = checked(ledger["source_review"])
    entries = ledger["sources"]
    errors = {}
    for row in entries:
        identity = row["id"]
        require(identity in by_id and identity not in errors, "Unknown/duplicate reviewed failure")
        require(row["decision"] == "withhold" and bool(row["reason"]), "Failure was not withheld")
        require(row["source"] == by_id[identity], "Failure source identity/attribution changed")
        require(
            isinstance(row["expected_error"], str) and bool(row["expected_error"]),
            "Missing reviewed failure reason",
        )
        errors[identity] = row["expected_error"]
    require(bool(errors), "Empty source-failure review")
    require(
        review["actual_viewed"] is True
        and len(review["reviewed_ids"]) == len(errors)
        and set(review["reviewed_ids"]) == set(errors),
        "Failure source review is incomplete",
    )
    inputs = [ref(path), producer, selection, ledger["source_review"]]
    for name in ["inspection", "image"]:
        item = review[name]
        require(ref(item["path"]) == item, "Changed inspected source evidence")
        inputs.append(item)
    return {"errors": errors, "inputs": inputs}


def validate_coverage(selection, prepared, failures, reviewed_errors):
    """Every selected source must be cached or one exact reviewed withheld failure."""
    selected = {row["sha1_hex"]: row for row in selection}
    require(len(selected) == len(selection), "Duplicate selected source identity")
    require(set(reviewed_errors) <= set(selected), "Unknown declared failure")
    factors = set(prepared)
    require(
        bool(factors) and factors <= {"4", "8"} and set(failures) == factors,
        "Unexpected/incomplete cache scales",
    )
    accepted = set(selected) - set(reviewed_errors)
    for factor in factors:
        failed = {row["id"]: row["error"] for row in failures[factor]}
        require(len(failed) == len(failures[factor]), "Duplicate actual source failure")
        require(failed == reviewed_errors, "Undeclared, changed or missing source failure")
        values = prepared[factor]
        by_id = {row["id"]: row for row in values}
        require(
            len(by_id) == len(values) and set(by_id) == accepted,
            "Cache/failure source partition differs",
        )
        for identity, row in by_id.items():
            require(
                all(
                    field in row and row[field] == selected[identity][field]
                    for field in SOURCE_FIELDS
                ),
                "Prepared source attribution changed",
            )
            require(
                row["bin_factor"] == int(factor)
                and row["dtype"] == "uint16"
                and row["color_space"] == "linear-sRGB",
                "Prepared pixel recipe changed",
            )
    return accepted
