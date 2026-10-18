"""Replay historical scores through the fresh-three-model review schema, CPU only."""

import argparse
import copy
import json
import os
from pathlib import Path

import torch
from compare_long_commons_scores import rows
from review_directional_interval import statistics
from train_directional_interval_trial import read, ref, save

from demosaic.safety import writable_path
from demosaic.suite import summarize


def main(historical_review, output):
    os.nice(10)
    torch.set_num_threads(2)
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    historical = read(historical_review)
    checkpoints = read(Path(historical["root"]) / "training-boundary.json")["checkpoints"]
    parent_sha = historical["parent"]["sha256"]
    plan = {**historical, "root": str(output), "outputs": {}}
    inputs, counts = [], {}
    for panel, filename in [
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
        ("full427", "per-image.jsonl"),
    ]:
        fresh = Path(historical["outputs"][panel])
        old = Path(historical["historical_panels"][panel])
        summary = copy.deepcopy(read(fresh / "summary.json"))
        parent_summary = read(old / "summary.json")
        parent_records = [
            m
            for m in parent_summary["models"]
            if m.get("sha256", m.get("weight_sha256")) == parent_sha
        ]
        assert len(parent_records) == 1
        parent_record = parent_records[0]
        records = rows(fresh / filename) + [
            r for r in rows(old / filename) if r["model"] == parent_record["label"]
        ]
        summary["models"].append(parent_record)
        if panel == "full427":
            aggregate = summarize(records)
        else:
            summary["per_pair"] += [
                r for r in parent_summary["per_pair"] if r["model"] == parent_record["label"]
            ]
            aggregate = summarize(
                summary["per_pair"],
                comparison_metrics=("sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim"),
            )
        summary.update(aggregate)
        summary.update(
            native_crops=[],
            preflight_scope="Historical V76/V77/V63 scores only, combined to exercise three-model audit schema. No new inference or V78/V79 result.",
        )
        target = output / panel
        target.mkdir()
        save(target / "summary.json", summary)
        with (target / filename).open("w") as stream:
            for record in records:
                stream.write(json.dumps(record, allow_nan=False) + "\n")
        plan["outputs"][panel] = str(target)
        counts[panel] = len(records)
        inputs.extend(
            ref(p)
            for p in [
                fresh / "summary.json",
                fresh / filename,
                old / "summary.json",
                old / filename,
            ]
        )
    save(
        output / "plan.json",
        {
            "historical_review": ref(historical_review),
            "inputs": inputs,
            "driver": ref(__file__),
            "review_driver": ref(Path(statistics.__code__.co_filename)),
            "scope": "Historical saved scores only; no image decoding, noise draws, model inference, recipe selection or V78/V79 results.",
        },
    )
    statistics(plan, checkpoints)
    result_path = output / "primary-statistics.json"
    result = read(result_path)
    old_result = read(Path(historical["root"]) / "primary-statistics.json")
    # Same exact historical model metrics and paired bootstrap effects; only
    # the parent's source report and fresh method count have changed.
    assert result["comparisons"] == old_result["comparisons"]
    result.update(
        preflight_only=True,
        scope="Historical V76/V77/V63 scores only; exercises six-method primary audit and fresh-parent descriptor route. No new inference or model-quality result.",
    )
    save(result_path, result)
    assert not torch.cuda.is_initialized()
    save(
        output / "receipt.json",
        {
            "status": "completed-historical-three-model-primary-statistics-preflight",
            "plan": ref(output / "plan.json"),
            "result": ref(result_path),
            "case_counts": counts,
            "audits": result["audits"],
            "comparison_rows_exactly_match_historical": len(result["comparisons"]),
            "parent_sources_all_use_three_model_fixture": all(
                source["second"]["report"] == str(output / source["panel"] / "summary.json")
                for source in result["sources"]
                if source["second"]["checkpoint_sha256"] == parent_sha
            ),
            "CUDA_initialized": False,
            "scope": result["scope"],
        },
    )
    print(json.dumps({"receipt": ref(output / "receipt.json"), "case_counts": counts}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.historical_review, args.output)
