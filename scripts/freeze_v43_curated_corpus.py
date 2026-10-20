"""Freeze matched Commons cohorts after completed ranking and explicit visual review."""

import argparse
import collections
import json
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def freeze(screen_root, decisions_path, output, *, check=False):
    plan_path = screen_root / "plan.json"
    plan = read(plan_path)
    guard(plan)
    candidates_path = Path(plan["work"]) / "source-scores/review-candidates.json"
    candidates, review = read(candidates_path), read(decisions_path)
    reviewed = {r["id"]: r for r in review["sources"]}
    assert len(reviewed) == len(review["sources"])
    assert all(
        r["decision"] in ("retain", "exclude", "withhold") and r["reason"]
        for r in reviewed.values()
    )
    needed = set()
    for records in candidates["high_loss"].values():
        needed.update(r["id"] for r in records[:32])
    for records in candidates["IQA_proxies_not_automatic_labels"].values():
        needed.update(r["id"] for r in records[:16])
    missing = sorted(needed - reviewed.keys())
    state = {
        "ranking_complete": candidates["complete"],
        "sources_scored": candidates["sources_scored"],
        "required_visual_sources": len(needed),
        "missing_visual_decisions": missing,
        "scope": "Top32 per fixed noise condition plus top16 per IQA proxy. Additional prior and metadata-cue decisions also apply. Targeted review, not a claim that all sources were manually viewed.",
    }
    if check:
        print(json.dumps(state, indent=2))
        return
    assert candidates["complete"] and not missing, state
    receipt_path = Path(plan["work"]) / "source-scores/receipt.json"
    receipt = read(receipt_path)
    assert receipt["status"] == "completed-source-difficulty-ranking-awaiting-visual-curation"
    assert receipt["plan"] == ref(plan_path) and not receipt["engineering_only"]
    assert (
        receipt["sources_scored"]
        == candidates["sources_scored"]
        == plan["counts"]["train"]
        == 88508
    )
    assert receipt["actual_forwards"] == receipt["DINO_calls"] == 22128
    assert receipt["cases"] == 177016 and receipt["state_config_parameters_RNG_inputs_preserved"]
    assert ref(receipt["scores"]["path"]) == receipt["scores"]
    current = rows(plan["manifest"]["path"])
    by_id = {r["id"]: r for r in current}
    assert len(by_id) == len(current)
    train = {r["id"] for r in current if r["split"] == "train"}
    assert set(reviewed) <= train
    for identity, decision in reviewed.items():
        row = by_id[identity]
        assert row["sha1_hex"] == decision["source_original_SHA1"]
        assert row["cache_sha256"] == decision["cache_SHA256"]
        assert ref(decision["view"]["path"]) == decision["view"]
        if "larger_native_view" in decision:
            assert ref(decision["larger_native_view"]["path"]) == decision["larger_native_view"]
    # Read the actual parent lineage; never reconstruct the old cohort by title.
    import torch

    parent = torch.load(
        plan["checkpoint"]["path"], map_location="cpu", weights_only=True, mmap=True
    )
    old_path = Path(parent["config"]["manifest"])
    assert ref(old_path)["sha256"] == parent["config"]["manifest_sha256"]
    old = rows(old_path)
    original = {r["id"] for r in old if r["split"] == "train"}
    assert len(original) == 40170
    for split in ("val", "test"):
        assert {r["id"] for r in old if r["split"] == split} == {
            r["id"] for r in current if r["split"] == split
        }
    assert not original & {r["id"] for r in current if r["split"] != "train"}
    excluded = {identity for identity, value in reviewed.items() if value["decision"] != "retain"}
    eligible = train - excluded
    cohorts = {"small": original & eligible, "large": eligible}
    assert 0 < len(cohorts["small"]) < len(cohorts["large"])
    output = output.resolve()
    assert output.is_relative_to(REPO / ".cache")
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    for name, membership in cohorts.items():
        selected = [r for r in current if r["split"] != "train" or r["id"] in membership]
        path = output / f"manifest4-{name}.jsonl"
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in selected))
        artifacts[name] = {
            "manifest": ref(path),
            "counts": dict(collections.Counter(r["split"] for r in selected)),
        }
    guard(plan)
    save(
        output / "receipt.json",
        {
            "status": "frozen-curated-matched-V43-cohorts",
            "review_scope": state,
            "inputs": [
                ref(p) for p in (plan_path, receipt_path, candidates_path, decisions_path, old_path)
            ]
            + [plan["checkpoint"], plan["source_manifest"]],
            "cohorts": artifacts,
            "newly_withheld_ids": sorted(excluded),
            "old_training_ids_already_ineligible": sorted(original - train),
            "validation_and_test_IDs_unchanged": True,
            "originals_and_historical_manifests_unmodified": True,
            "scope": "Membership-only curation of already audited Commons caches. Manual decisions apply to training only. Existing protected series and standing GFX exclusions remain inherited from current eligible manifest. No fresh full-file hash audit of every corpus image is claimed.",
        },
    )
    print(ref(output / "receipt.json"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("screen_root", type=Path)
    parser.add_argument("decisions", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--check", action="store_true", help="List pending visual decisions without freezing."
    )
    args = parser.parse_args()
    freeze(args.screen_root.resolve(), args.decisions.resolve(), args.output, check=args.check)
