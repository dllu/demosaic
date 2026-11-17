"""Test direction proposals from a separate simulated RAW region."""

import argparse
import os
import sys
import time
from copy import deepcopy
from pathlib import Path

import numpy as np
import psutil

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, fit_local_candidate, restore_local_waves

CONFIG = LocalWaveConfig(window=256, stride=256)
MODES = ("query-only", "matching-guide", "unrelated-guide")


def prepare(root, panel_path):
    from demosaic.experiments.data.edge_response import edge_observation

    root.mkdir()
    panel = read_json(panel_path)
    groups = [
        group
        for group in panel["finite_groups"]
        if group["profile"] in ("iso400", "iso6400")
        and group["metadata"]["pattern"] == "RGGB"
        and group["metadata"]["repeat"] == 0
    ]
    assert len(groups) == 32
    old_rows = {item["id"]: item for item in panel["rows"]}
    donors = {}
    work, sources = freeze_sources(Path.cwd(), root, ["probe_scene_wave_guides.py"])
    for group in groups:
        metadata = group["metadata"]
        geometry = metadata["recipe"]["source"]
        key = f"{group['profile']}-{geometry}"
        if key in donors:
            continue
        recipe = deepcopy(metadata["recipe"])
        # Separate synthetic region of the same nominal lattice. Retain only
        # native directions and periods. Phase, background and support differ.
        recipe.update(
            size=256,
            level=0.11,
            bright_level=0.25,
            edge_jitter=0.0,
            mask_radii=[116.0, 116.0],
            amplitude=0.055,
            weak_fraction=1.0,
            phases=[
                (phase + shift) % 1
                for phase, shift in zip(recipe["phases"], (0.271, 0.389), strict=True)
            ],
        )
        arrays, meta = edge_observation(
            recipe, "far", "RGGB", repeat=2931, condition=metadata["noise"]
        )
        path = root / f"guide-raw-{key}.npz"
        with path.open("xb") as stream:
            np.savez(stream, packed=arrays["packed"][2], colors=arrays["colors"][2])
        donors[key] = {"arrays": reference(path), "simulation": meta}
    assert len(donors) == 16
    cases = []
    for group in groups:
        metadata = group["metadata"]
        source = metadata["recipe"]["source"]
        profile = group["profile"]
        for identity in group["cases"]:
            row = old_rows[identity]
            assert row["arrays"] == group["arrays"]
            cases.append(
                {
                    "id": identity,
                    "arrays": row["arrays"],
                    "parent": row["parent"],
                    "sample": row["sample"],
                    "source": source,
                    "profile": profile,
                    "placement": metadata["placement"],
                    "query_noise": metadata["noise"],
                    "matching": f"{profile}-{source}",
                    "unrelated": f"{profile}-{(source + 4) % 8}",
                }
            )
    assert len(cases) == 96
    model_path = panel_path.with_name("analytic-model-v2.json")
    parents = read_json(model_path)["parent_bindings_by_domain"]["finite-wire"]
    assert parents["label"] == "V143"
    inputs = [reference(panel_path), reference(model_path)]
    for case in cases:
        inputs.extend((case["arrays"], case["parent"]))
    inputs.extend(donor["arrays"] for donor in donors.values())
    path = root / "plan.json"
    write_json(
        path,
        {
            "root": str(root),
            "driver": reference(work / "scripts/probe_scene_wave_guides.py"),
            "inputs": list({item["path"]: item for item in inputs}.values()),
            "frozen_files": sources,
            "config": CONFIG.to_dict(),
            "threshold": 2.0,
            "cases": cases,
            "donors": donors,
            "parents": parents,
            "query_native_xywh": [128, 128, 256, 256],
            "native_display_ROI_xywh": [48, 48, 160, 160],
            "scope": "Eight reused procedural geometries, near and far, ISO400/6400, RGGB draw0,"
            " three independent retained query roles each. Fresh donor-only simulations"
            " have stronger wires, separate phases and independent noise, with the same"
            " two nominal directions/periods. Only their detected frequency vectors enter"
            " query fits. One unrelated donor per query, fixed before collection."
            " No query target, clean donor phase/amplitude or new neural/model calls.",
        },
    )
    print(path, file=sys.stdout)


def collect(plan_path):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert reference(__file__) == plan["driver"]
    config = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    guide_config = LocalWaveConfig(**plan.get("guide_config", plan["config"]))
    guides = {}
    for key, donor in plan["donors"].items():
        with np.load(checked(donor["arrays"]), allow_pickle=False) as data:
            packed, colors = data["packed"], data["colors"]
        raw = packed.reshape(2, 2, 128, 128).transpose(2, 0, 3, 1).reshape(256, 256)
        cfa = np.tile(colors.reshape(2, 2), (128, 128))
        noise = donor["simulation"]["noise"]
        candidate = fit_local_candidate(
            raw,
            cfa,
            np.ones(raw.shape, dtype=bool),
            shot=noise["shot"],
            read=noise["read"],
            config=guide_config,
        )
        guides[key] = candidate.frequencies_xy
    write_json(output / "guides.json", guides)
    rows = []
    started = time.monotonic()
    for case in plan["cases"]:
        if psutil.virtual_memory().available < 24 * 2**30:
            raise RuntimeError("Available memory fell below 24 GiB")
        index = case["sample"]
        with np.load(checked(case["arrays"]), allow_pickle=False) as data:
            packed = data["packed"][index, :, 64:192, 64:192]
            colors = data["colors"][index]
        parent = np.load(checked(case["parent"]), allow_pickle=False)[index, :, 128:384, 128:384]
        predictions, records = {}, {}
        noise = case["query_noise"]
        for label, guide in zip(
            MODES, (None, guides[case["matching"]], guides[case["unrelated"]]), strict=True
        ):
            result, record = restore_local_waves(
                parent,
                packed,
                colors,
                shot=noise["shot"],
                read=noise["read"],
                config=config,
                thresholds=(plan["threshold"],),
                guide_frequencies_xy=guide,
            )
            prediction = result["local", plan["threshold"]]
            assert prediction.shape == parent.shape and np.isfinite(prediction).all()
            predictions[label], records[label] = prediction, record
        path = output / (case["id"] + ".npz")
        with path.open("xb") as stream:
            np.savez(stream, **predictions)
        row = {"id": case["id"], "outputs": reference(path), "query_fits": records}
        write_json(output / (case["id"] + ".json"), row)
        rows.append(row)
        print(len(rows), case["id"], flush=True)
    assert len(rows) == len(plan["cases"]) == 96
    write_json(
        output / "collection.json",
        {
            "plan": reference(plan_path),
            "rows": rows,
            "guides": reference(output / "guides.json"),
            "seconds": time.monotonic() - started,
            "query_target_arrays_read": 0,
            "scope": "All96 query roles close before scoring. Each mode runs the same two query"
            " A/B fits, fixed threshold, interpolation, and delivery. Matching and unrelated"
            " guides share only two vectors. Parent participates in delivery only.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve())
    else:
        collect(args.path)
