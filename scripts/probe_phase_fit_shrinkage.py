"""Compare discovery-only fit shrinkage with the closed RAW phase-profile study."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
from probe_phase_profiles import THRESHOLDS, names

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves

METHOD = "shrunken-profile"


def prepare(root, source):
    root.mkdir()
    plan_path, closure = source / "plan.json", source / "output/collection.json"
    plan, closed = read_json(plan_path), read_json(closure)
    assert closed["plan"] == reference(plan_path) and closed["query_roles"] == 384
    assert tuple(plan["thresholds"]) == THRESHOLDS and plan["shapes"]["phase-profile"] == 8
    assert len(plan["groups"]) == len(closed["synthetic"]) == 128
    work, files = freeze_sources(
        Path.cwd(),
        root,
        ["probe_phase_fit_shrinkage.py", "report_phase_profiles.py", "report_scene_wave_guides.py"],
    )
    write_json(
        root / "plan.json",
        {
            **plan,
            "root": str(root),
            "work": str(work),
            "frozen_files": files,
            "driver": reference(work / "scripts/probe_phase_fit_shrinkage.py"),
            "adopted_plan": reference(plan_path),
            "adopted_collection": reference(closure),
            "adopted_report": reference(source / "review/result.json"),
            "inputs": [
                *plan["inputs"],
                reference(plan_path),
                reference(closure),
                reference(source / "review/result.json"),
            ],
            "methods": [*names(), *(f"{METHOD}-t{t:g}" for t in THRESHOLDS)],
            "scope": "Reuse all384 queries and8 standing camera cases. Test one change to the eight"
            " phase-bin fit: subtract nominal fitted noise energy using the discovery fold,"
            " attenuating both held-out test prediction and emitted parent correction. Same"
            " geometry, layout, guides and three fixed thresholds. All original sinusoid"
            " and phase-bin controls are read from their exact retained outputs.",
        },
    )


def restore(parent, packed, colors, frequencies, noise, config):
    restored, statistics = restore_local_waves(
        parent,
        packed,
        colors,
        guide_frequencies_xy=frequencies,
        phase_bins=8,
        shrink_phase_fit=True,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=THRESHOLDS,
    )
    outputs = {f"{METHOD}-t{t:g}": restored["local", t] for t in THRESHOLDS}
    assert all(v.shape == parent.shape and np.isfinite(v).all() for v in outputs.values())
    return outputs, statistics


def collect(path, *, restore_view=restore, driver=__file__):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(driver)
    config = LocalWaveConfig(**plan["config"])
    adopted = read_json(checked(plan["adopted_collection"]))
    old_groups = {row["id"]: row for row in adopted["synthetic"]}
    old_camera = {row["id"]: row for row in adopted["camera"]}
    output = Path(plan["root"]) / "output"
    output.mkdir()
    started = time.monotonic()
    groups = []
    for group in plan["groups"]:
        key = group["id"]
        with np.load(checked(group["arrays"])) as arrays:
            packed, colors = arrays["packed"][..., 64:192, 64:192], arrays["colors"]
        parent = np.load(checked(group["parent"]))[..., 128:384, 128:384]
        rows = []
        for old in old_groups[key]["rows"]:
            role = old["role"]
            outputs, stats = restore_view(
                parent[role],
                packed[role],
                colors[role],
                group["frequencies"],
                group["noise"],
                config,
            )
            destination = output / f"{key}-role{role}.npz"
            with destination.open("xb") as stream:
                np.savez(stream, **outputs)
            rows.append(
                {
                    "role": role,
                    "prediction": reference(destination),
                    "fits": stats,
                    "adopted_prediction": old["prediction"],
                }
            )
        assert [row["role"] for row in rows] == [0, 1, 2]
        row = {"id": key, "rows": rows}
        write_json(output / f"{key}.json", row)
        groups.append(row)
        print(len(groups), key, flush=True)
    real = []
    metadata = read_json(checked(plan["camera_guide_source"]))
    old_plan = read_json(checked(metadata["plan"]))
    native = read_json(checked(old_plan["native_plan"]))
    for row in plan["camera_cases"]:
        key = row["id"]
        x, y, width, height = row["query_box"]
        assert width == height == 256
        with np.load(checked(row["query_arrays"])) as data:
            packed, colors = (
                data["packed"][0, :, y // 2 : (y + height) // 2, x // 2 : (x + width) // 2],
                data["colors"][0],
            )
        noise = next(o["noise"] for o in native["observations"] if o["id"] == row["query"])
        parent = np.load(checked(row["parent_prediction"]))[0, :, y : y + height, x : x + width]
        outputs, stats = restore_view(parent, packed, colors, row["guide"], noise, config)
        destination = output / f"{key}.npz"
        with destination.open("xb") as stream:
            np.savez(stream, **outputs)
        real.append(
            {
                "id": key,
                "prediction": reference(destination),
                "fits": stats,
                "adopted_prediction": old_camera[key]["prediction"],
            }
        )
    assert len(groups) == 128 and len(real) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": groups,
            "camera": real,
            "query_roles": sum(len(v["rows"]) for v in groups),
            "references_read": 0,
            "learned_calls": 0,
            "noise_draws": 0,
            "seconds": time.monotonic() - started,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--adopt", type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    if args.adopt:
        prepare(args.path.resolve(), args.adopt.resolve())
    else:
        collect(args.path.resolve())
