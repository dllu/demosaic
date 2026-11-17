"""Test donor subharmonic decisions on retained, disjoint query RAW."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
from probe_fold_support_pooling import THRESHOLDS

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves


def prepare(root, source, assessment):
    prior_plan, prior_close, prior_report = (
        source / name for name in ("plan.json", "output/collection.json", "review/result.json")
    )
    plan, prior, scores = (read_json(path) for path in (prior_plan, prior_close, assessment))
    assert prior["plan"] == reference(prior_plan) and prior["query_roles"] == 384
    assert len(scores["synthetic"]) == 16 and len(scores["camera"]) == 8
    assert scores["direction_score_threshold_each_fold"] == 3.0
    assert scores["real_collection"] == plan["camera_guide_source"]
    for name in (
        "driver",
        "spectrum_operator",
        "synthetic_plan",
        "original_guides",
        "real_collection",
    ):
        checked(scores[name])
    for kind in ("synthetic", "camera"):
        for value in scores[kind].values():
            checked(value["donor"])
            decision = np.min(value["fold_by_direction_scores"], axis=0) >= 3.0
            assert decision.tolist() == value["accepted"]
            assert (
                np.asarray(value["existing"]) * np.where(decision[:, None], 0.5, 1)
            ).tolist() == value["revised"]
    root.mkdir()
    work, frozen = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_donor_subharmonics.py"]
    )
    write_json(
        root / "plan.json",
        {
            **plan,
            "root": str(root),
            "work": str(work),
            "frozen_files": frozen,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "adopted_plan": reference(prior_plan),
            "adopted_collection": reference(prior_close),
            "adopted_report": reference(prior_report),
            "donor_assessment": reference(assessment),
            "inputs": [
                *plan["inputs"],
                reference(prior_plan),
                reference(prior_close),
                reference(prior_report),
                reference(assessment),
            ],
            "scope": "Exact retained pooled query inputs and eight fixed thresholds. Apply only donor RAW"
            " subharmonic decisions with both fold scores at least 3. Collect only changed"
            " query geometry. Adopting unchanged cases preserves exact existing predictions."
            " No target or reference enters delivery. Standing GFX reporting uses threshold 2.",
        },
    )


def restore(parent, packed, colors, guide, noise, config, thresholds):
    restored, stats = restore_local_waves(
        parent,
        packed,
        colors,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=thresholds,
        guide_frequencies_xy=guide,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
    )
    values = {f"subharmonic-t{t:g}": restored["pooled-local", t] for t in thresholds}
    assert all(v.shape == parent.shape and np.isfinite(v).all() for v in values.values())
    return values, stats


def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__) and tuple(plan["thresholds"]) == THRESHOLDS
    donor = read_json(checked(plan["donor_assessment"]))
    prior = read_json(checked(plan["adopted_collection"]))
    config = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    n = 0
    groups = []
    start = time.monotonic()
    for group, saved in zip(plan["groups"], prior["synthetic"], strict=True):
        assert group["id"] == saved["id"]
        guide = donor["synthetic"][group["guide_key"]]
        assert group["frequencies"] == guide["existing"]
        if not any(guide["accepted"]):
            groups.append({"id": group["id"], "changed": False, "rows": saved["rows"]})
            continue
        with np.load(checked(group["arrays"])) as data:
            packed, colors = data["packed"][..., 64:192, 64:192], data["colors"]
        parent = np.load(checked(group["parent"]))[..., 128:384, 128:384]
        rows = []
        for role in range(3):
            values, stats = restore(
                parent[role],
                packed[role],
                colors[role],
                guide["revised"],
                group["noise"],
                config,
                THRESHOLDS,
            )
            path_out = output / f"{group['id']}-role{role}.npz"
            with path_out.open("xb") as stream:
                np.savez(stream, **values)
            rows.append({"role": role, "prediction": reference(path_out), "fits": stats})
            n += 1
        row = {"id": group["id"], "changed": True, "rows": rows, "guide": guide}
        write_json(output / f"{group['id']}.json", row)
        groups.append(row)
        print(group["id"], n, flush=True)

    real = []
    metadata = read_json(checked(plan["camera_guide_source"]))
    native = read_json(checked(read_json(checked(metadata["plan"]))["native_plan"]))
    noise = {v["id"]: v["noise"] for v in native["observations"]}
    for row, saved in zip(plan["camera_cases"], prior["camera"], strict=True):
        key = row["id"]
        guide = donor["camera"][key]
        assert saved["id"] == key and row["guide"] == guide["existing"]
        if not any(guide["accepted"]):
            real.append({"id": key, "changed": False, "prediction": saved["prediction"]})
            continue
        x, y, w, h = row["query_box"]
        with np.load(checked(row["query_arrays"])) as data:
            packed, colors = (
                data["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2],
                data["colors"][0],
            )
        parent = np.load(checked(row["parent_prediction"]))[0, :, y : y + h, x : x + w]
        values, stats = restore(
            parent, packed, colors, guide["revised"], noise[row["query"]], config, (2.0,)
        )
        path_out = output / f"{key}.npz"
        with path_out.open("xb") as stream:
            np.savez(stream, **values)
        real.append({"id": key, "changed": True, "prediction": reference(path_out), "fits": stats})
    assert len(groups) == 128 and len(real) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": groups,
            "camera": real,
            "synthetic_roles_refit": n,
            "synthetic_roles_adopted": 384 - n,
            "camera_refit": sum(v["changed"] for v in real),
            "seconds": time.monotonic() - start,
            "references_read": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--adopt", type=Path)
    parser.add_argument("--donor-assessment", type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    if args.adopt:
        if args.donor_assessment is None:
            parser.error("--donor-assessment is required to prepare the study")
        prepare(args.path.resolve(), args.adopt.resolve(), args.donor_assessment.resolve())
    else:
        collect(args.path.resolve())
