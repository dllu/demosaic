"""Stress the phase refit with fixed guide offsets and bounded fold-local recovery."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
import psutil
from probe_fresh_phase_refit import METHODS, write_array

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves

OFFSETS = {"nominal": 0.0, "tangential": 0.5, "radial": 1.0}
ARMS = tuple(f"{error}-{fit}" for error in OFFSETS for fit in ("fixed", "recentered"))


def displaced(frequencies, arm, source):
    original = np.asarray(frequencies, dtype=np.float64)
    if arm == "nominal":
        return original
    unit = original / np.linalg.norm(original, axis=1, keepdims=True)
    if arm == "tangential":
        unit = np.stack((-unit[:, 1], unit[:, 0]), axis=1)
    sign = (-1.0) ** (source + np.arange(2))[:, None]
    return original + sign * unit * (OFFSETS[arm] / 256)


def prepare(root, fresh):
    orig_path, collected, report_path = (
        fresh / name for name in ("plan.json", "output/collection.json", "review/result.json")
    )
    orig, closed, report = map(read_json, (orig_path, collected, report_path))
    assert closed["plan"] == report["plan"] == reference(orig_path)
    assert report["collection"] == reference(collected) and closed["query_roles"] == 96
    development = read_json(checked(orig["development_report"]))
    previous = read_json(checked(development["plan"]))
    group = read_json(checked(previous["camera_guide_source"]))
    native = read_json(checked(read_json(checked(group["plan"]))["native_plan"]))
    camera_noise = {item["id"]: item["noise"] for item in native["observations"]}
    root.mkdir()
    work, files = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_phase_guide_recenter.py"]
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": files,
            "inputs": [
                reference(orig_path),
                reference(collected),
                reference(report_path),
                orig["development_report"],
                *closed["cases"],
            ],
            "fresh_plan": reference(orig_path),
            "fresh_collection": reference(collected),
            "fresh_report": reference(report_path),
            "config": orig["config"],
            "settings": orig["settings"],
            "offsets_native_bins": OFFSETS,
            "arms": ARMS,
            "camera": [
                {"board": item, "noise": camera_noise[item["source"]["query"]]}
                for item in orig["retained_camera_review"]
            ],
            "scope": "Reuse identical fresh RAW inputs and parent images. Counterbalance the sign by"
            " parity of source and guide order. Add ±0.5 bin tangential or ±1 bin radial"
            " to each guide. Compare fixed and independently recentered guides for all"
            " six arms, including a no-perturbation recenter control. Settings frozen."
            " Recenter the measured non-perturbed guides on both standing camera families.",
        },
    )


def restore(parent, packed, colors, guides, noise, cfg, thresholds, recenter, *, edge_guard_px=0):
    values, audit = restore_local_waves(
        parent,
        packed,
        colors,
        guide_frequencies_xy=guides,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        recenter_phase_guides=recenter,
        phase_guide_edge_guard_px=edge_guard_px,
        shot=noise["shot"],
        read=noise["read"],
        config=cfg,
        thresholds=thresholds,
    )
    output = {
        f"{'fold-average' if mode == 'pooled-local' else mode}-t{t:g}": item
        for (mode, t), item in values.items()
        if mode in ("pooled-local", "weighted-refit")
    }
    return output, audit


def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__) and plan["arms"] == list(ARMS)
    closed = read_json(checked(plan["fresh_collection"]))
    original = read_json(checked(plan["fresh_plan"]))
    cfg = LocalWaveConfig(**plan["config"])
    root = Path(plan["root"])
    output = root / "output"
    output.mkdir()
    observed, camera = [], []
    started = time.monotonic()
    for ref in closed["cases"]:
        if psutil.virtual_memory().available < 24 * 2**30:
            raise RuntimeError("Available memory fell below 24 GiB")
        case = read_json(checked(ref))
        key = case["id"]
        with np.load(checked(case["sensor"]), allow_pickle=False) as source:
            sensor = source["packed"][..., 64:192, 64:192]
            colors = source["colors"]
        parent = np.load(checked(case["parent"]))[..., 128:384, 128:384]
        guide = closed["donors"][case["guide_key"]]["frequencies"]
        noise = original["profiles"][case["profile"]]
        targets = tuple(
            sorted(
                {
                    2,
                    *(
                        r["threshold"]
                        for r in plan["settings"]
                        if (r["profile"], r["placement"]) == (case["profile"], case["placement"])
                    ),
                }
            )
        )
        fits, variants = {}, {}
        for key_kind in OFFSETS:
            seed = displaced(guide, key_kind, case["source"])
            for recenter in (False, True):
                if key_kind == "nominal" and not recenter:
                    continue
                arm = f"{key_kind}-{'recentered' if recenter else 'fixed'}"
                rows = []
                for i in range(3):
                    values, audit = restore(
                        parent[i], sensor[i], colors[i], seed, noise, cfg, targets, recenter
                    )
                    rows.append(audit)
                    for name, image in values.items():
                        variants.setdefault(f"{arm}--{name}", []).append(image)
                fits[arm] = rows
        dest = write_array(
            output / f"{key}-predictions.npz", **{k: np.stack(v) for k, v in variants.items()}
        )
        receipt = output / f"{key}.json"
        write_json(receipt, {"id": key, "case": ref, "output": dest, "fits": fits})
        observed.append(reference(receipt))
        print(len(observed), key, f"{time.monotonic() - started:.2f}s", flush=True)
    assert len(observed) == 32 and len(METHODS) == 2
    for item in plan["camera"]:
        board = item["board"]
        case = board["source"]
        x, y, w, h = case["query_box"]
        with np.load(checked(case["query_arrays"]), allow_pickle=False) as source:
            packed = source["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = source["colors"][0]
        parent = np.load(checked(case["parent_prediction"]))[0, :, y : y + h, x : x + w]
        result, stats = restore(
            parent, packed, colors, case["guide"], item["noise"], cfg, (2,), True
        )
        camera.append(
            {
                "id": board["id"],
                "fit": stats,
                "output": write_array(output / f"{board['id']}.npz", **result),
            },
        )
    assert len(camera) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": observed,
            "camera": camera,
            "new_synthetic_calls": 480,
            "new_camera_calls": 8,
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
