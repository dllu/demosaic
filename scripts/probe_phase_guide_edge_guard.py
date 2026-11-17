"""Replay guide recentering with strong-edge exclusions of 8 and 24 pixels."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import psutil
from probe_fresh_phase_refit import write_array
from probe_phase_guide_recenter import OFFSETS, displaced, restore

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig

WIDTHS = (8, 24)


def prepare(root, previous):
    old_path, collected, report_path = (
        previous / name for name in ("plan.json", "output/collection.json", "review/result.json")
    )
    old, closed, report = (read_json(p) for p in (old_path, collected, report_path))
    assert closed["plan"] == report["plan"] == reference(old_path)
    assert reference(collected) == report["collection"] and len(report["metrics"]) == 768
    noise = {v["board"]["id"]: v["noise"] for v in old["camera"]}
    root.mkdir()
    work, files = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_phase_guide_edge_guard.py"]
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": files,
            "inputs": [
                reference(old_path),
                reference(collected),
                reference(report_path),
                old["fresh_plan"],
                old["fresh_report"],
                old["fresh_collection"],
                *closed["synthetic"],
            ],
            "previous_plan": reference(old_path),
            "previous_collection": reference(collected),
            "previous_report": reference(report_path),
            "fresh_plan": old["fresh_plan"],
            "fresh_collection": old["fresh_collection"],
            "config": old["config"],
            "settings": old["settings"],
            "widths_px": WIDTHS,
            "camera": [{"board": b, "noise": noise[b["id"]]} for b in report["camera"]],
            "scope": "Strong fitted edges exclude an 8- or 24-native-pixel half-width from"
            " frequency selection only. The bounded search, predictions, validation"
            " and delivery use the frozen comparison's remaining settings. Both widths"
            " replay all nominal, radial and tangential guides. Adopt the original controls.",
        },
    )


def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__) and plan["widths_px"] == list(WIDTHS)
    previous = read_json(checked(plan["previous_collection"]))
    fresh = read_json(checked(plan["fresh_collection"]))
    profiles = read_json(checked(plan["fresh_plan"]))["profiles"]
    cfg = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    observed, camera = [], []
    started = time.monotonic()
    for link in previous["synthetic"]:
        if psutil.virtual_memory().available < 24 * 2**30:
            raise RuntimeError("Available memory fell below 24 GiB")
        old = read_json(checked(link))
        case = read_json(checked(old["case"]))
        key = case["id"]
        assert key == old["id"]
        with np.load(checked(case["sensor"])) as f:
            packed, colors = f["packed"][..., 64:192, 64:192], f["colors"]
        parent = np.load(checked(case["parent"]))[..., 128:384, 128:384]
        noise = profiles[case["profile"]]
        guide = fresh["donors"][case["guide_key"]]["frequencies"]
        thresholds = tuple(
            sorted(
                {
                    2,
                    *(
                        s["threshold"]
                        for s in plan["settings"]
                        if (s["profile"], s["placement"]) == (case["profile"], case["placement"])
                    ),
                }
            )
        )
        fits, images = {}, {}
        for offset in OFFSETS:
            seed = displaced(guide, offset, case["source"])
            for width in WIDTHS:
                arm = f"{offset}-guard{width}"
                stats = []
                for role in range(3):
                    values, run = restore(
                        parent[role],
                        packed[role],
                        colors[role],
                        seed,
                        noise,
                        cfg,
                        thresholds,
                        True,
                        edge_guard_px=width,
                    )
                    stats.append(run)
                    for mode, image in values.items():
                        images.setdefault(f"{arm}--{mode}", []).append(image)
                fits[arm] = stats
        dest = write_array(
            output / f"{key}-predictions.npz", **{k: np.stack(v) for k, v in images.items()}
        )
        record = output / f"{key}.json"
        write_json(
            record, {"id": key, "previous": link, "case": old["case"], "output": dest, "fits": fits}
        )
        observed.append(reference(record))
        print(len(observed), key, f"{time.monotonic() - started:.2f}s", flush=True)
    assert len(observed) == 32
    for item in plan["camera"]:
        board = item["board"]
        case = board["source"]
        x, y, w, h = case["query_box"]
        with np.load(checked(case["query_arrays"])) as raw:
            packed = raw["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = raw["colors"][0]
        parent = np.load(checked(case["parent_prediction"]))[0, :, y : y + h, x : x + w]
        values, fits = {}, {}
        for width in WIDTHS:
            out, stats = restore(
                parent,
                packed,
                colors,
                case["guide"],
                item["noise"],
                cfg,
                (2,),
                True,
                edge_guard_px=width,
            )
            values[f"guard{width}"] = out["weighted-refit-t2"]
            fits[f"guard{width}"] = stats
        camera.append(
            {
                "id": board["id"],
                "output": write_array(output / f"{board['id']}.npz", **values),
                "fits": fits,
            }
        )
    assert len(camera) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": observed,
            "camera": camera,
            "new_synthetic_calls": 576,
            "new_camera_calls": 16,
            "seconds": time.monotonic() - started,
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
        collect(args.path.resolve())
