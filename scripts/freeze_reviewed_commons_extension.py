"""Reuse completed caches in a separately reviewed, coupled Commons extension."""

import argparse
import copy
import hashlib
import json
import os
import shutil
from collections import Counter
from pathlib import Path

import numpy as np
import psutil

from demosaic.prepare import free_license
from demosaic.safety import REPOSITORY, writable_path

REBIN_FIELDS = {"cache", "cache_sha256", "shape", "bin_factor"}
ACTIVE = {"train", "val", "test"}
REVIEW_STATUS = "completed-source-content-and-conservative-metadata-review-for-future-admission"


def ref(path):
    path = Path(path).resolve()
    with path.open("rb") as stream:
        value = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": value}


def read(path):
    return json.loads(Path(path).read_text())


def rows(path):
    values = [json.loads(line) for line in Path(path).read_bytes().splitlines()]
    if len({r["id"] for r in values}) != len(values):
        raise ValueError("Duplicate manifest identity")
    return values


def require(condition, message):
    if not condition:
        raise ValueError(message)


def checked(item):
    require(ref(item["path"]) == item, "Changed review/source binding")
    return read(item["path"])


def reviewed_rows(candidates, review):
    """No flag, reserved source or omitted identity can become training data."""
    by_id = {r["id"]: r for r in candidates}
    require(len(by_id) == len(candidates), "Duplicate candidate identity")
    downloaded = review.get("format_version") == 2
    allowed = {"train", "reserved", "excluded"} if downloaded else {"train", "reserved"}
    require(all(r["split"] in allowed for r in candidates), "Unexpected candidate split")
    require(review["manual_source_content_screen_complete"] is True, "Content review incomplete")
    require(
        review["all_candidate_thumbnails_actually_viewed"] == len(candidates),
        "Content coverage differs",
    )
    sets = {}
    for name in ["eligible_train_ids", "withheld_train_ids", "new_reserved_ids"]:
        values = review[name]
        sets[name] = set(values)
        require(len(values) == len(sets[name]), "Duplicate review decision")
    eligible, withheld, reserved = (sets[k] for k in sets)
    require(
        not eligible & withheld and not (eligible | withheld) & reserved, "Review decisions overlap"
    )
    require(
        eligible | withheld == {r["id"] for r in candidates if r["split"] == "train"},
        "Training decisions incomplete or include a nontraining source",
    )
    require(
        reserved == {r["id"] for r in candidates if r["split"] == "reserved"},
        "Reserved decisions differ",
    )
    if downloaded:
        values = review["preexcluded_ids"]
        require(
            len(values) == len(set(values))
            and set(values) == {r["id"] for r in candidates if r["split"] == "excluded"},
            "Duplicate exclusions differ",
        )
    result = copy.deepcopy(candidates)
    for row in result:
        if row["id"] in withheld:
            row.update(
                original_split="train",
                split="excluded",
                excluded_reason="conservative-new-source-title-content-or-series-risk"
                if downloaded
                else "conservative-new-source-title-or-series-risk",
            )
    return result


def source_fields(row):
    return {k: v for k, v in row.items() if k not in REBIN_FIELDS}


def freeze(base4, base8, prepared4, candidate8, review_path, output, *, reserve_gib=500):
    require(
        type(reserve_gib) is int and reserve_gib >= 256,
        "External disk reserve must be an integer of at least256GiB",
    )
    output = writable_path(output)
    require(not output.exists(), "Output exists; preserve previous freezes")
    require(psutil.virtual_memory().available >= 24 * 2**30, "System memory guard")
    require(shutil.disk_usage("/mnt/external").free >= reserve_gib * 2**30, "External disk reserve")
    inputs = [ref(p) for p in [base4, base8, prepared4, candidate8, review_path, __file__]]
    review = read(review_path)
    require(
        review["format_version"] in {1, 2} and review["status"] == REVIEW_STATUS,
        "Review not complete",
    )
    downloaded = review["format_version"] == 2
    inventory = checked(review["inventory"])
    if not downloaded:
        require(
            inventory["candidate_manifest"] == ref(candidate8)
            and inventory["base_manifest"] == ref(base8),
            "Wrong reviewed candidate/base",
        )
    duplicate = checked(review["duplicate_audit"])
    require(
        duplicate["manifest_sha256"] == ref(candidate8)["sha256"]
        and duplicate["base_sha256"] == ref(base8)["sha256"],
        "Duplicate audit differs",
    )
    terminal = checked(review["producer_terminal"])
    expected_status = (
        "prepared-and-screened-downloaded-quarantine-awaiting-independent-review"
        if downloaded
        else "prepared-and-screened-quarantine-awaiting-independent-review"
    )
    require(terminal["status"] == expected_status, "Cache producer incomplete")
    require(terminal["receipt"] == review["producer_receipt"], "Wrong producer receipt")
    owner = terminal["owner"]
    try:
        process = psutil.Process(owner["pid"])
        require(
            process.create_time() != owner["created"] or process.status() == psutil.STATUS_ZOMBIE,
            "Cache producer still live",
        )
    except psutil.NoSuchProcess:
        pass
    producer = checked(review["producer_receipt"])
    if downloaded:
        producer_plan = checked(producer["plan"])
        require(
            producer_plan["engineering_only"] is review["engineering_only"],
            "Engineering/production producer mixed",
        )
    protected = checked(producer["screening"])
    if downloaded:
        require(
            duplicate["max_hamming"] == 8 and duplicate["min_correlation"] == 0.99,
            "Duplicate thresholds differ from the reviewed operator",
        )
        require(
            Path(duplicate["addition_manifest"]).resolve()
            == Path(protected["cleared_manifest"]).resolve()
            and duplicate["addition_sha256"] == protected["cleared_sha256"],
            "Duplicate audit bypasses protected screening",
        )
    expected_four = Path(protected["manifest"]).parent.parent / "prepared4/manifest.jsonl"
    require(
        Path(prepared4).resolve() == expected_four.resolve(), "Wrong complete4 producer manifest"
    )
    area = checked(producer["cache_audit"])
    require(
        not any(area["errors"].values()) and area["area_max_uint16_codes"] <= 1,
        "Cache/area audit failed",
    )
    for contact in review["viewed_contacts"]:
        require(contact["actual_viewed"] is True, "Unviewed content screen")
        require(ref(contact["PNG"]["path"]) == contact["PNG"], "Changed contact screen")
    require(
        [c["PNG"] for c in review["viewed_contacts"]] == [c["PNG"] for c in inventory["contacts"]],
        "Content screens incomplete",
    )
    require(
        sum(c["count"] for c in inventory["contacts"]) == len(inventory["new_rows"]),
        "Content count differs",
    )
    if not downloaded:
        for item in [*review["viewed_title_pair_contacts"], review["viewed_new_reserved_pairs"]]:
            require(ref(item["path"]) == item, "Changed viewed title-pair screen")
        title = checked(review["title_screen"])
        policy = checked(title["policy"])
        require(
            title["inventory"] == review["inventory"] and title["policy"] == review["title_policy"],
            "Wrong title review",
        )
        require(
            policy["threshold"] == 0.55
            and title["status"] == "completed-metadata-risk-screen-no-training-admission",
            "Incomplete title screen",
        )
        decisions = checked(title["decisions"])
        require(
            sorted(r["id"] for r in decisions if r["decision"] == "eligible-after-data-review")
            == review["eligible_train_ids"],
            "Title flag released without separate review",
        )
        require(
            sorted(r["id"] for r in decisions if r["decision"] != "eligible-after-data-review")
            == review["withheld_train_ids"],
            "Title decisions differ",
        )
    old4, old8, combined, four = [rows(p) for p in [base4, base8, candidate8, prepared4]]
    require(len(four) == area["prepared"]["4"], "Prepared4 membership incomplete")
    before8, before4 = ({r["id"]: r for r in group} for group in [old8, old4])
    after = {r["id"]: r for r in combined}
    require(
        before8.keys() <= after.keys() and all(after[k] == r for k, r in before8.items()),
        "Existing source or split changed",
    )
    new = [r for r in combined if r["id"] not in before8]
    if downloaded:
        from review_downloaded_commons import validate_downloaded_review

        inputs += [
            ref(Path(__file__).with_name(name))
            for name in [
                "review_downloaded_commons.py",
                "screen_commons_titles.py",
                "render_commons_contact_sheets.py",
            ]
        ]
        validate_downloaded_review(
            review, inventory, new, base8, prepared4, Path(protected["manifest"]), candidate8
        )
    else:
        require(new == inventory["new_rows"], "Reviewed additions differ")
    reviewed = reviewed_rows(new, review)
    active8 = {k for k, r in before8.items() if r["split"] in ACTIVE}
    require(before4.keys() == active8, "Base4/base8 active membership differs")
    require(
        all(source_fields(r) == source_fields(before8[k]) for k, r in before4.items()),
        "Base4/base8 source metadata differs",
    )
    four_by_id = {r["id"]: r for r in four}
    eligible = [r for r in reviewed if r["split"] == "train"]
    new4, audited = [], []
    for row in eligible:
        require(
            row["id"] in four_by_id and row["id"] not in before4, "Missing/new4 identity collision"
        )
        companion = copy.deepcopy(four_by_id[row["id"]])
        require(source_fields(companion) == source_fields(row), "New4/new8 source or split differs")
        companion["cache"] = str((Path(prepared4).parent / companion["cache"]).resolve())
        for factor, item in [(4, companion), (8, row)]:
            path = (
                (Path(prepared4).parent / item["cache"]).resolve()
                if factor == 4
                else Path(item["cache"]).resolve()
            )
            require(
                path.is_relative_to(REPOSITORY) or path.is_relative_to("/mnt/external"),
                "Cache outside allowed SSD roots",
            )
            require(
                item["bin_factor"] == factor
                and item["dtype"] == "uint16"
                and item["color_space"] == "linear-sRGB"
                and free_license(item["license"]),
                "Invalid cache recipe/license",
            )
            require(ref(path)["sha256"] == item["cache_sha256"], "Cache bytes changed")
            pixels = np.load(path, mmap_mode="r", allow_pickle=False)
            require(
                pixels.dtype == np.uint16
                and list(pixels.shape) == item["shape"]
                and pixels.ndim == 3
                and pixels.shape[-1] == 3
                and min(pixels.shape[:2]) >= 2048 // factor,
                "Cache shape/dtype differs",
            )
            audited.append(
                {
                    "id": item["id"],
                    "factor": factor,
                    "sha256": item["cache_sha256"],
                    "bytes": path.stat().st_size,
                }
            )
        new4.append(companion)
    for item in inputs:
        require(ref(item["path"]) == item, "Input changed during freeze")
    output.mkdir(parents=True)
    shutil.copyfile(__file__, output / "source.py")
    if downloaded:
        source_output = output / "executed-review-sources"
        source_output.mkdir()
        for name in [
            "review_downloaded_commons.py",
            "screen_commons_titles.py",
            "render_commons_contact_sheets.py",
        ]:
            shutil.copyfile(Path(__file__).with_name(name), source_output / name)
    outputs = {}
    for factor, source, added in [(4, base4, new4), (8, base8, reviewed)]:
        prefix = Path(source).read_bytes()
        require(prefix.endswith(b"\n"), "Base manifest requires a final newline")
        path = output / f"manifest{factor}.jsonl"
        path.write_bytes(
            prefix + b"".join((json.dumps(r, ensure_ascii=False) + "\n").encode() for r in added)
        )
        outputs[str(factor)] = ref(path)
    receipt = {
        "status": "frozen-reviewed-coupled-Commons-extension-no-active-recipe-change",
        "review_format_version": review["format_version"],
        "engineering_only": bool(review.get("engineering_only", False)),
        "external_reserve_gib": reserve_gib,
        "inputs": inputs,
        "manual_review": ref(review_path),
        "manifests": outputs,
        "counts4": dict(Counter(r["split"] for r in old4 + new4)),
        "counts8": dict(Counter(r["split"] for r in old8 + reviewed)),
        "new_train": len(eligible),
        "new_withheld": len(review["withheld_train_ids"]),
        "new_reserved": len(review["new_reserved_ids"]),
        "all_old_rows_and_literal_bytes_preserved": True,
        "new4_new8_training_membership_and_source_metadata_exact": True,
        "new_training_cache_SHA256_header_checks": len(audited),
        "new_training_cache_bytes": sum(a["bytes"] for a in audited),
        "cache_audit": audited,
        "scope": "Separately frozen future corpus only. All old rows/splits and source caches preserved. New4 includes only reviewed active training members; new8 additionally records reserved/excluded arrivals. Finite source/content/title screens do not prove complete scene independence or native noiseless targets. No model-quality result, active recipe update or protected-final performance scoring.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps(
            {
                "receipt": ref(output / "receipt.json"),
                "new_train": len(eligible),
                "counts4": receipt["counts4"],
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ["base4", "base8", "prepared4", "candidate8", "review", "output"]:
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--reserve-gib", type=int, default=500)
    args = parser.parse_args()
    require(os.environ.get("CUDA_VISIBLE_DEVICES") == "", "Use hidden CUDA for data-only freezing")
    freeze(
        args.base4,
        args.base8,
        args.prepared4,
        args.candidate8,
        args.review,
        args.output,
        reserve_gib=args.reserve_gib,
    )
