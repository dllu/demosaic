"""Compare held-out direction support for sinusoidal and sampled phase profiles."""

import argparse
import os
import time
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves

THRESHOLDS = (0.0, 2.0, 4.0)
SHAPES = {"sinusoid": 0, "phase-profile": 8}


def names():
    return [f"{shape}-t{t:g}" for shape in SHAPES for t in THRESHOLDS]


def prepare(root, panel, synthetic_guides, camera_collection):
    root.mkdir()
    panel, synthetic_guides, camera_collection = map(
        reference, (panel, synthetic_guides, camera_collection)
    )
    overview = read_json(checked(panel))
    known = read_json(checked(synthetic_guides))
    camera = read_json(checked(camera_collection))
    assert len(known) == 16 and len(camera["rows"]) == 8
    groups = []
    all_rows = {row["id"]: row for row in overview["rows"]}
    for group in overview["finite_groups"]:
        profile, meta = group["profile"], group["metadata"]
        if profile not in ("iso400", "iso6400") or meta["repeat"] != 1:
            continue
        source = meta["recipe"]["source"]
        guide_key = f"{profile}-{source}"
        roles = [all_rows[key] for key in group["cases"]]
        parent = roles[0]["parent"]
        assert [row["sample"] for row in roles] == [0, 1, 2]
        assert all(row["parent"] == parent and row["arrays"] == group["arrays"] for row in roles)
        groups.append(
            {
                "id": f"{profile}-index{group['index']:04d}",
                "profile": profile,
                "source": source,
                "placement": meta["placement"],
                "CFA": meta["pattern"],
                "repeat": meta["repeat"],
                "noise": meta["noise"],
                "arrays": group["arrays"],
                "parent": parent,
                "guide_key": guide_key,
                "frequencies": known[guide_key],
            }
        )
    keys = {(g["profile"], g["source"], g["placement"], g["CFA"]) for g in groups}
    assert len(keys) == len(groups) == 128
    files = [panel, synthetic_guides, camera_collection]
    for g in groups:
        files.extend((g["arrays"], g["parent"]))
    for row in camera["rows"]:
        files.extend(row[k] for k in ("query_arrays", "parent_prediction", "prediction"))
    work, source = freeze_sources(
        Path.cwd(), root, ["probe_phase_profiles.py", "report_phase_profiles.py"]
    )
    path = root / "plan.json"
    write_json(
        path,
        {
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts/probe_phase_profiles.py"),
            "inputs": list({item["path"]: item for item in files}.values()),
            "frozen_files": source,
            "config": LocalWaveConfig(window=256, stride=256).to_dict(),
            "groups": groups,
            "camera_cases": camera["rows"],
            "shapes": SHAPES,
            "thresholds": THRESHOLDS,
            "synthetic_guide_source": synthetic_guides,
            "camera_guide_source": camera_collection,
            "expected_query_roles": 384,
            "scope": "Predeclared draw1 with all four CFAs,8 retained geometries,2 placements,2 priors."
            " Same guides from independent donor RAW as before. Query noise is a different"
            " retained draw from the earlier RGGB0 study. Same parent, nuisance, A/B gates,"
            " thresholds and correction, comparing sine/cosine against eight circular knots."
            " Three fixed thresholds show quiet/error tradeoffs. Eight standing real cases"
            " use the original disjoint donor frequencies. References enter only the report.",
        },
    )
    print(path)


def restore_all(parent, packed, colors, frequencies, noise, config):
    predictions, records = {}, {}
    for method, phase_bins in SHAPES.items():
        restored, record = restore_local_waves(
            parent,
            packed,
            colors,
            guide_frequencies_xy=frequencies,
            phase_bins=phase_bins,
            shot=noise["shot"],
            read=noise["read"],
            config=config,
            thresholds=THRESHOLDS,
        )
        for t in THRESHOLDS:
            value = restored["local", t]
            assert value.shape == parent.shape and np.isfinite(value).all()
            predictions[f"{method}-t{t:g}"] = value
        records[method] = record
    return predictions, records


def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert reference(__file__) == plan["driver"]
    assert plan["shapes"] == SHAPES and tuple(plan["thresholds"]) == THRESHOLDS
    config = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    collected = []
    started = time.monotonic()
    for index, group in enumerate(plan["groups"]):
        source = np.load(checked(group["parent"]), allow_pickle=False)
        with np.load(checked(group["arrays"]), allow_pickle=False) as data:
            packed, colors = data["packed"][..., 64:192, 64:192], data["colors"]
        rows = []
        for role in range(3):
            parent = source[role, :, 128:384, 128:384]
            variants, stats = restore_all(
                parent, packed[role], colors[role], group["frequencies"], group["noise"], config
            )
            filename = output / f"{group['id']}-role{role}.npz"
            with filename.open("xb") as stream:
                np.savez(stream, **variants)
            rows.append({"role": role, "prediction": reference(filename), "fits": stats})
        row = {"id": group["id"], "rows": rows}
        write_json(output / f"{group['id']}.json", row)
        collected.append(row)
        print(index + 1, group["id"], flush=True)
    real = []
    for row in plan["camera_cases"]:
        x, y, width, height = row["query_box"]
        assert width == height == 256
        with np.load(checked(row["query_arrays"])) as data:
            packed = data["packed"][0, :, y // 2 : (y + height) // 2, x // 2 : (x + width) // 2]
            colors = data["colors"][0]
        metadata = read_json(checked(plan["camera_guide_source"]))
        old_plan = read_json(checked(metadata["plan"]))
        native = read_json(checked(old_plan["native_plan"]))
        noise = next(o["noise"] for o in native["observations"] if o["id"] == row["query"])
        parent = np.load(checked(row["parent_prediction"]))[0, :, y : y + height, x : x + width]
        values, stats = restore_all(parent, packed, colors, row["guide"], noise, config)
        with np.load(checked(row["prediction"])) as previous:
            np.testing.assert_array_equal(values["sinusoid-t2"], previous["donor-guide"])
        filename = output / (row["id"] + ".npz")
        with filename.open("xb") as stream:
            np.savez(stream, **values)
        real.append(
            {
                "id": row["id"],
                "prediction": reference(filename),
                "fits": stats,
                "original_sinusoid_bitexact": True,
            }
        )
    assert len(collected) == 128 and len(real) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": collected,
            "camera": real,
            "query_roles": sum(len(row["rows"]) for row in collected),
            "seconds": time.monotonic() - started,
            "references_read": 0,
            "learned_calls": 0,
            "native_sensor_decodes": 0,
            "noise_draws": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument(
        "--prepare-from",
        type=Path,
        nargs=3,
        metavar=("PANEL", "SYNTHETIC_GUIDES", "CAMERA_COLLECTION"),
    )
    args = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    if args.prepare_from:
        prepare(args.path.resolve(), *args.prepare_from)
    else:
        collect(args.path.resolve())
