"""Replay reserved-RAW footprint transfer with saved whole-image frequency guides."""

import argparse
import json
import time
from dataclasses import replace
from functools import partial
from pathlib import Path

import numpy as np
from probe_flexible_query_edges import camera, synth
from probe_reserved_wire_footprint import camera_predict

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig

PANELS = ("synthetic-iso400", "synthetic-iso6400", "disjoint-iso400", "disjoint-iso6400")
STAGES = (*PANELS, "camera")


def prepare(root, screened, reserve, partner, full_profile=False):
    old = reference(screened / "plan.json")
    plan = read_json(checked(old))
    panels = {
        key: reference(screened / f"{key}.json") for key in ("synthetic", "disjoint", "camera")
    }
    controls = {
        "camera_reserved": reference(reserve / "camera.json"),
        "camera_partner": reference(partner / "camera.json"),
    }
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        plan
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [old, *panels.values(), *controls.values(), *plan["inputs"]],
            "screened_sources": panels,
            "controls": controls,
            "full_profile": full_profile,
            "scope": "Run the two earlier ordinary-wire geometry sets with their scene-nominated "
            "frequencies. Retain exact-center controls on the main set. Compare the screened eight-knot "
            "refit with the uniform fundamental and the reserve-confirmed partner footprint. "
            "Validate the camera and two-path footprint results against the previous retained predictions.",
        },
    )


def run(path, stage):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    root = Path(plan["root"])
    output = root / f"arrays-{stage}"
    output.mkdir()
    config = replace(LocalWaveConfig(**plan["config"]), background="screened_curved4_step")
    full_profile = plan.get("full_profile", False)
    predictor = partial(
        camera_predict, edge_side=False, partner_only=True, full_profile=full_profile
    )
    start = time.monotonic()
    verified = 0
    if stage == "camera":
        source = read_json(checked(plan["screened_sources"]["camera"]))["rows"]
        rows = camera(plan, source, output, config, predictor=predictor)
        earlier = read_json(checked(plan["controls"]["camera_partner"]))["rows"]
        for row, old in zip(rows, earlier, strict=True):
            assert row["id"] == old["id"]
            assert json.loads(json.dumps(row["flexible_edges"])) == old["flexible_edges"]
            if full_profile:
                verified += verify_eight(row["predictions"], row["before"])
            else:
                with (
                    np.load(checked(row["predictions"])) as out,
                    np.load(checked(old["predictions"])) as control,
                ):
                    for name in out.files:
                        np.testing.assert_array_equal(out[name], control[name])
                        verified += 1
    else:
        label, profile = stage.split("-")
        source = read_json(checked(plan["screened_sources"][label]))["rows"]
        selected = [r for r in source if r["id"].startswith(profile + "-")]
        assert len(selected) == 8
        rows = synth(plan, selected, config, label, output, predictor=predictor)
        for row, previous in zip(rows, selected, strict=True):
            assert row["id"] == previous["id"]
            with (
                np.load(checked(row["prediction"])) as out,
                np.load(checked(previous["prediction"])) as before,
            ):
                for name in before.files:
                    np.testing.assert_array_equal(out[name], before[name])
                    verified += 1
            if full_profile:
                verified += verify_eight(row["prediction"], row["before"])
    write_json(
        root / f"{stage}.json",
        {
            "plan": reference(path),
            "producer": reference(__file__),
            "rows": rows,
            "unchanged_arrays": verified,
            "CPU_wall_seconds": time.monotonic() - start,
        },
    )


def verify_eight(now, prior):
    with np.load(checked(now)) as out, np.load(checked(prior)) as old:
        names = [name for name in out.files if name.endswith(("-uniform", "-uniform-strict"))]
        assert names
        for name in names:
            np.testing.assert_array_equal(out[name], old[name.replace("-uniform", "-screened")])
        return len(names)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    command = parser.add_subparsers(dest="command", required=True)
    setup = command.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("screened", type=Path)
    setup.add_argument("reserve", type=Path)
    setup.add_argument("partner", type=Path)
    setup.add_argument("--full-profile", action="store_true")
    replay = command.add_parser("run")
    replay.add_argument("plan", type=Path)
    replay.add_argument("stage", choices=STAGES)
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(
            *(p.resolve() for p in (args.root, args.screened, args.reserve, args.partner)),
            args.full_profile,
        )
    else:
        run(args.plan.resolve(), args.stage)
