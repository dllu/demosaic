"""Final title retrieval and evidence checks for downloaded Commons admission.

No flag is a training approval. The coupled freezer still needs complete,
actually viewed source and content-neighbor sheets and explicit decisions.
"""

import argparse
import json
import shutil
from pathlib import Path

from commons_preparation_review import SOURCE_FIELDS
from render_commons_contact_sheets import FIELDS
from screen_commons_titles import THRESHOLD, retrieve
from train_directional_interval_trial import read, ref, save

from demosaic.safety import writable_path

FINAL_TITLE_STATUS = "completed-final-candidate-title-retrieval-no-training-admission"
CONTENT_STATUS = "completed-source-content-neighbors-awaiting-actual-review-no-training-admission"


def validate_anchor_coverage(base, anchor_rows):
    """Require every admission holdout's exact pixels/source; allow extra heldouts."""
    pools = {"Commons-heldout", "native150", "protected45"}
    require(all(row.get("pool") in pools for row in anchor_rows), "Unknown anchor pool")
    require(
        len({(r["pool"], r["id"]) for r in anchor_rows}) == len(anchor_rows),
        "Duplicate anchor identity",
    )
    expected = {r["id"]: r for r in base if r["split"] in {"val", "test", "reserved"}}
    commons = {r["id"]: r for r in anchor_rows if r["pool"] == "Commons-heldout"}
    require(
        all(r["split"] in {"val", "test", "reserved"} for r in commons.values()),
        "Training source in heldout anchor pool",
    )
    require(expected.keys() <= commons.keys(), "Content bank omits an admission holdout")
    fields = [*SOURCE_FIELDS, "cache_sha256", "shape", "bin_factor", "dtype", "color_space"]
    for identity, row in expected.items():
        require(
            all(
                field in commons[identity] and commons[identity][field] == row[field]
                for field in fields
            ),
            "Heldout anchor pixels or source attribution differ",
        )
    return len(commons)


def require(value, message):
    if not value:
        raise ValueError(message)


def checked(item):
    require(ref(item["path"]) == item, "Changed downloaded source-review proof")
    return read(item["path"])


def rows(path):
    values = [json.loads(line) for line in Path(path).read_text().splitlines()]
    require(len({r["id"] for r in values}) == len(values), "Duplicate source identity")
    return values


def final_titles(base, candidate, prepared8, duplicate_audit, output):
    bindings = [ref(p) for p in [base, candidate, prepared8, duplicate_audit, __file__]]
    matcher = Path(__file__).with_name("screen_commons_titles.py")
    bindings.append(ref(matcher))
    duplicate = read(duplicate_audit)
    require(
        duplicate["base_sha256"] == bindings[0]["sha256"]
        and duplicate["manifest_sha256"] == bindings[1]["sha256"],
        "Wrong completed duplicate candidate",
    )
    old, combined, prepared = (rows(p) for p in [base, candidate, prepared8])
    before = {r["id"]: r for r in old}
    require(
        all(r == before[r["id"]] for r in combined if r["id"] in before)
        and before.keys() <= {r["id"] for r in combined},
        "Prior source or split changed",
    )
    new = [r for r in combined if r["id"] not in before]
    raw = {r["id"]: r for r in prepared}
    require(all(r["id"] in raw for r in new), "Candidate missing from direct8 preparation")
    require(
        all(r["split"] in {"train", "reserved", "excluded"} for r in new),
        "Raw holdout bucket was not reserved",
    )
    require(
        all(r["split"] in {"train", "val", "test"} for r in prepared),
        "Expected complete direct8 manifest",
    )
    anchors = [
        dict(r, anchor_origin="existing-corpus")
        for r in old
        if r["split"] in {"val", "test", "reserved"}
    ]
    # Keep every raw holdout hash as an anchor, including sources withheld by
    # protected/pixel screens. This conservative superset cannot release a risk.
    anchors += [
        dict(r, split="reserved", anchor_origin="new-reserved")
        for r in prepared
        if r["split"] in {"val", "test"}
    ]
    queries = [r for r in new if r["split"] == "train"]
    decisions = retrieve(anchors, queries)
    output = writable_path(output)
    require(not output.exists(), "Preserve previous title screens")
    for item in bindings:
        require(ref(item["path"]) == item, "Title input changed")
    output.mkdir(parents=True)
    shutil.copyfile(__file__, output / "executed-source.py")
    shutil.copyfile(matcher, output / "executed-title-matcher.py")
    policy = {
        "threshold": THRESHOLD,
        "stage": "final-candidate-population-after-protected-and-pixel-audit",
        "queries": "Only duplicate-candidate new train rows; excluded sources never queried for eligibility.",
        "anchors": "All prior val/test/reserved plus every new prepared val/test hash, including withheld holdout sources.",
        "action": "All title-risk/uninformative decisions stay withheld. No-title-flag permits further manual review only; content/series review can withhold more sources.",
    }
    save(output / "policy.json", policy)
    save(output / "decisions.json", decisions)
    result = {
        "status": FINAL_TITLE_STATUS,
        "base": bindings[0],
        "candidate": bindings[1],
        "prepared8": bindings[2],
        "duplicate_audit": bindings[3],
        "driver": ref(output / "executed-source.py"),
        "matcher": ref(output / "executed-title-matcher.py"),
        "inputs": bindings,
        "policy": ref(output / "policy.json"),
        "decisions": ref(output / "decisions.json"),
        "anchors": len(anchors),
        "prior_heldout_anchors": sum(r["split"] in {"val", "test", "reserved"} for r in old),
        "new_reserved_anchors": sum(r["split"] in {"val", "test"} for r in prepared),
        "queries": len(queries),
        "training_admission": False,
    }
    save(output / "report.json", result)
    return ref(output / "report.json")


def validate_downloaded_review(review, inventory, new, base8, prepared4, prepared8, candidate8):
    """Validate full source coverage, final title flags and actual DINO review."""
    require(review["format_version"] == 2, "Expected downloaded review format2")
    require(
        inventory["status"] == "prepared-all-source-thumbnails-awaiting-actual-content-review",
        "Incomplete source inventory",
    )
    require(inventory["inputs"][0] == ref(prepared4), "Wrong complete4 source contact inventory")
    source_rows = inventory["new_rows"]
    source = {r["id"]: r for r in source_rows}
    require(len(source) == len(source_rows), "Duplicate source-view identity")
    require(
        review["all_source_thumbnails_actually_viewed"] == len(source),
        "Full source viewing incomplete",
    )
    require(
        sum(r["count"] for r in inventory["contacts"]) == len(source),
        "Source sheet coverage differs",
    )
    expected = rows(prepared4)
    require({r["id"] for r in expected} == set(source), "Source inventory omits prepared source")
    normalized = [
        dict(r, cache=str((Path(prepared4).parent / r["cache"]).resolve())) for r in expected
    ]
    require(source_rows == normalized, "Source contact rows differ from complete4 manifest")
    prepared_rows = rows(prepared8)
    require(
        {r["id"] for r in prepared_rows} == set(source), "Complete4/8 source membership differs"
    )
    require(
        [r["indices"] for r in inventory["contacts"]]
        == [[first, min(first + 99, len(source) - 1)] for first in range(0, len(source), 100)],
        "Source sheet indices overlap or omit images",
    )
    for row in new:
        require(
            row["id"] in source and all(row[k] == source[row["id"]][k] for k in FIELDS),
            "Reviewed candidate/source attribution differs",
        )
    require(
        {r["id"] for r in new if r["split"] == "excluded"} == set(review["preexcluded_ids"]),
        "Duplicate exclusions differ",
    )
    title = checked(review["title_screen"])
    policy = checked(title["policy"])
    require(
        title["status"] == FINAL_TITLE_STATUS
        and title["base"] == ref(base8)
        and title["candidate"] == ref(candidate8)
        and title["prepared8"] == ref(prepared8),
        "Final title population differs",
    )
    require(
        ref(title["matcher"]["path"]) == title["matcher"]
        and title["matcher"]["sha256"]
        == ref(Path(__file__).with_name("screen_commons_titles.py"))["sha256"],
        "Final title matcher differs",
    )
    require(
        policy["threshold"] == 0.55
        and policy["stage"] == "final-candidate-population-after-protected-and-pixel-audit",
        "Wrong final title policy",
    )
    require(title["duplicate_audit"] == review["duplicate_audit"], "Title duplicate audit differs")
    decisions = checked(title["decisions"])
    train = {r["id"] for r in new if r["split"] == "train"}
    by_id = {r["id"]: r for r in decisions}
    require(
        len(by_id) == len(decisions) and set(by_id) == train,
        "Final title decision coverage differs",
    )
    require(
        all(
            r["decision"]
            in {"no-title-flag", "withhold-title-risk", "withhold-uninformative-title"}
            for r in decisions
        ),
        "Unknown final title decision",
    )
    withheld = set(review["withheld_train_ids"])
    require(
        {r["id"] for r in decisions if r["decision"] != "no-title-flag"} <= withheld,
        "Title flag released",
    )
    content = checked(review["content_neighbors"])
    require(
        content["status"] == CONTENT_STATUS and content["manifest"] == ref(prepared8),
        "Wrong complete content-neighbor population",
    )
    require(
        content["engineering"] is review["engineering_only"],
        "Engineering/production source evidence mixed",
    )
    require(
        content["first_batch_repeat_bitwise"]
        and content["Torch_RNG_unchanged"]
        and content["CUDA_initialized"] is False,
        "Content encoder/state proof failed",
    )
    require(
        content["backbone_unchanged"]
        == "370a84c2d9e1d216757422c0a25ceb82a0a106083ba8ca545d9b267e704540fd",
        "Different source-content encoder",
    )
    content_plan = checked(content["plan"])
    bank = checked(content_plan["bank"])
    bank_plan = checked(bank["plan"])
    require(
        bank["status"] == "completed-source-content-anchor-bank-no-training-admission"
        and bank["all_selected_pixel_hashes_checked"]
        and bank["Torch_RNG_unchanged"]
        and bank["CUDA_initialized"] is False,
        "Incomplete content anchor bank",
    )
    require(bank["engineering"] is review["engineering_only"], "Engineering/production bank mixed")
    expected_commons = sum(r["split"] in {"val", "test", "reserved"} for r in rows(base8))
    if "base" in bank_plan:
        same_base = bank_plan["base"] == ref(base8)
        if not same_base and review["engineering_only"]:
            original = {r["id"]: r for r in rows(bank_plan["base"]["path"])}
            same_base = all(r == original.get(r["id"]) for r in rows(base8))
        require(same_base, "Content heldout anchors differ from admission base")
        require(ref(bank_plan["base"]["path"]) == bank_plan["base"], "Changed anchor source base")
    else:
        require(
            bank.get("all_selected_vectors_exact_to_completed_sources") is True
            and bank.get("fresh") == 0,
            "Unknown incremental anchor provenance",
        )
        checked(bank_plan["previous"])
        checked(bank_plan["arrivals"])
        require(ref(bank["input_rows"]["path"]) == bank["input_rows"], "Changed anchor population")
        expected_commons = validate_anchor_coverage(rows(base8), rows(bank["input_rows"]["path"]))
    if not review["engineering_only"]:
        require(
            bank["pools"]
            == {
                "Commons-heldout": expected_commons,
                "native150": 150,
                "protected45": 45,
            },
            "Production anchor pool coverage differs",
        )
    require(content["producer_receipt"] == review["producer_receipt"], "Content producer differs")
    require(
        content_plan.get("preparation_failure_review") == review.get("preparation_failure_review"),
        "Content and admission failure reviews differ",
    )
    require(content["new_sources"] == len(source), "Content retrieval omits new sources")
    require(
        content["train_hash_queries"] == sum(r["split"] == "train" for r in prepared_rows)
        and content["new_reserved_anchors"]
        == sum(r["split"] in {"val", "test"} for r in prepared_rows),
        "Content query/holdout coverage differs",
    )
    contacts = review["viewed_content_contacts"]
    require(
        [r["PNG"] for r in contacts] == [r["PNG"] for r in content["contacts"]]
        and all(r["actual_viewed"] is True for r in contacts),
        "Content-neighbor sheets not fully viewed",
    )
    for item in contacts:
        require(ref(item["PNG"]["path"]) == item["PNG"], "Changed viewed content-neighbor sheet")
    pairs = checked(content["contact_pairs"])
    labels = review["content_pair_decisions"]
    require(
        len(labels) == len(pairs) == content["contact_pairs_count"],
        "Content-pair review coverage differs",
    )
    allowed = {
        "different-scene",
        "same-source-or-scene-risk",
        "uncertain-source",
        "query-already-withheld",
    }
    for index, (pair, label) in enumerate(zip(pairs, labels, strict=True)):
        require(
            label["index"] == index
            and label["query_id"] == pair["query_id"]
            and label["reference_id"] == pair["reference_id"]
            and label["decision"] in allowed
            and bool(label["observation"].strip()),
            "Content-pair review identity or decision differs",
        )
        if label["decision"] != "different-scene" and pair["query_id"] in train:
            require(pair["query_id"] in withheld, "Uncertain/shared-scene query released")
    # A source may be withheld after pixel screening; preserve that exclusion
    # even when it appears in the overinclusive source-only DINO contacts.
    require(
        not set(review["eligible_train_ids"]) & set(review["preexcluded_ids"]),
        "Duplicate exclusion promoted",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ["base", "candidate", "prepared8", "duplicate-audit", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            final_titles(
                args.base, args.candidate, args.prepared8, args.duplicate_audit, args.output
            )
        )
    )
