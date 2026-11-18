"""Compare a nested RAW background screen against the saved parallel and curved fits."""

import argparse
import time
from dataclasses import replace
from itertools import product
from pathlib import Path

import numpy as np
from probe_flexible_query_edges import camera, nulls, predict, synth
from probe_local_phase_bounds import fresh_structure, structure_module
from probe_surface_aggregation import field

from demosaic.cfa import PATTERNS
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig

CONTROL_SEED = 202611172104
STYLES = ("flat", "step", "rail", "wedge", "bent-rail", "two-rails")
ARMS = {"curved4": "curved4_step", "screened": "screened_curved4_step"}


def prepare(root, previous):
    old_path = reference(previous / "plan.json")
    old = read_json(checked(old_path))
    retained = {
        key: reference(previous / f"{key}.json")
        for key in ("synthetic", "disjoint", "camera", "retained", "fresh", "sensitivity")
    }
    root.mkdir()
    source, files = freeze_sources(
        Path.cwd(),
        root,
        [Path(__file__).name, "probe_matched_query_evidence.py", "report_scene_wave_guides.py"],
    )
    write_json(
        root / "plan.json",
        old
        | {
            "root": str(root),
            "work": str(source),
            "frozen_files": files,
            "driver": reference(source / "scripts" / Path(__file__).name),
            "inputs": [old_path, *old["inputs"], *retained.values()],
            "curved_receipts": retained,
            "backgrounds": ARMS,
            "replication": {"seed": CONTROL_SEED, "styles": STYLES, "trials": 4},
            "scope": "Reserve a second set inside each outer discovery fold to compare three nuisance-only RAW "
            "predictions. Require a gain above three standardized units against both hard and smooth parallel "
            "models. Refit the chosen family on the outer discovery fold before the original crossed wave "
            "test. The outer validation data are unchanged. Repeat both archived panels and collect 48 "
            "unseen structure controls with disjoint geometry and noise.",
        },
    )


def replicate(plan, cfg, configs):
    recipe = structure_module(plan["structure"])
    arms = {"parallel": cfg, **configs}
    rows = []
    for i, (profile, style, trial) in enumerate(product(plan["profiles"], STYLES, range(4))):
        gen = np.random.default_rng(np.random.SeedSequence([CONTROL_SEED, 0, i]))
        geometry = [
            float(gen.uniform(a, b))
            for a, b in ((0.07, 3.05), (6, 14), (-29, 29), (0.035, 0.085), (0.05, 0.15))
        ]
        angle, width, *_ = geometry
        period = np.clip(2 * width, 8, 26)
        a, b = np.cos(angle) / period, np.sin(angle) / period
        guides = [[a, b], [-b, a]]
        constructor = recipe.construct if style in STYLES[:3] else fresh_structure
        target = constructor(style, *geometry)
        cfa = tuple(PATTERNS)[trial]
        colors = np.asarray(PATTERNS[cfa])
        noise = plan["profiles"][profile]
        noise_seed = [CONTROL_SEED, 1, i]
        rng = np.random.default_rng(np.random.SeedSequence(noise_seed))
        packed = recipe.corrupt(target, colors, rng, noise)
        inputs = {"active": [True, True], "frequencies_xy": guides}
        threshold = plan["settings"][profile]["threshold"]
        values, diagnostics = predict(
            target, packed, colors, inputs, noise, recipe.QUERY, arms, threshold
        )
        metrics = {}
        for (arm, offset), image in values.items():
            d = (image[recipe.MEASURE].astype(float) - target[recipe.MEASURE]) * 65535
            metrics[field("null", arm, offset)] = {
                "RMS_DN16": float(np.sqrt(np.mean(d**2))),
                "max_abs_DN16": float(np.max(np.abs(d))),
                "changed_pixels": int(np.count_nonzero(np.any(d != 0, axis=0))),
            }
        rows.append(
            {
                "profile": profile,
                "style": style,
                "trial": trial,
                "CFA": cfa,
                "angle_radians": angle,
                "width_shift_level_height": geometry[1:],
                "guide_frequencies_xy": guides,
                "noise_seed": noise_seed,
                "metrics": metrics,
                "boundaries": diagnostics,
            }
        )
        print("replication", profile, style, trial, flush=True)
    assert len(rows) == 48
    return rows


def run(path, label):
    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    cfg = LocalWaveConfig(**plan["config"])
    configs = {arm: replace(cfg, background=kind) for arm, kind in ARMS.items()}
    root = Path(plan["root"])
    start = time.monotonic()
    if label == "replication":
        rows = replicate(plan, cfg, configs)
    elif label in ("fresh", "retained"):
        rows = nulls(plan, configs, label)
    else:
        out = root / f"arrays-{label}"
        out.mkdir()
        current = read_json(checked(plan["source"]["output/collection.json"]))[label]
        if label == "camera":
            rows = camera(plan, current, out, configs)
        else:
            rows = synth(plan, current, configs, label, out)
    write_json(
        root / f"{label}.json",
        {
            "plan": reference(path),
            "rows": rows,
            "producer": reference(__file__),
            "CPU_wall_seconds": time.monotonic() - start,
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="action", required=True)
    setup = actions.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("previous", type=Path)
    execute = actions.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument(
        "label", choices=("retained", "fresh", "replication", "synthetic", "disjoint", "camera")
    )
    args = cli.parse_args()
    if args.action == "prepare":
        prepare(args.root.resolve(), args.previous.resolve())
    else:
        run(args.plan.resolve(), args.label)
