"""Replay disjoint RAW validation with up to two or four curved query boundaries."""

import argparse
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_local_phase_bounds import fresh_structure, structure_module
from probe_screened_scene_donors import offset_box
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
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
from demosaic.search_donor_geometry import screening_mask

MODES = {"curved2": "curved_step", "curved4": "curved4_step"}


def prepare(root, local, scene):
    original = read_json(local / "output/collection.json")
    old = read_json(checked(original["plan"]))
    pooling = read_json(checked(old["previous_plan"]))
    sources = {
        p: reference(local / p)
        for p in ("output/collection.json", "null-retained.json", "null-fresh.json")
    }
    sources["disjoint_guides"] = reference(scene / "output/collection.json")
    sources["original_guides"] = pooling["previous"]
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(),
        root,
        [Path(__file__).name, "probe_matched_query_evidence.py", "report_scene_wave_guides.py"],
    )
    write_json(
        root / "plan.json",
        old
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [
                *sources.values(),
                original["plan"],
                old["structure"],
                old["camera_baseline"],
                old["camera_conditions"],
            ],
            "source": sources,
            "background_arms": MODES,
            "scope": "Preserve all guides and the wave scorer and refit. Replace the hard parallel "
            "query nuisance by up to two or four smooth boundaries with offset, independent "
            "obliquity and quadratic curvature. Fit only on the discovery RAW; both the "
            "conditional null and full wave share that background. Preserve the original "
            "parallel outputs and exact sensor observations.",
        },
    )


def predict(parent, packed, colors, guide, noise, query, configs, threshold, *, edge_side=False):
    values, receipts = {}, {}
    for arm, config in configs.items():
        if any(guide["active"]):
            out, aux = restore_local_waves(
                parent,
                packed,
                colors,
                shot=noise["shot"],
                read=noise["read"],
                config=config,
                thresholds=(threshold, threshold + 1),
                evidence_mask=~screening_mask(query),
                guide_frequencies_xy=guide["frequencies_xy"],
                phase_bins=8,
                shrink_phase_fit=True,
                compare_pooled_support=True,
                compare_pooled_refit=True,
                phase_edge_side="validation" if edge_side else None,
                active_guide_directions=guide["active"],
            )
            receipts[arm] = [
                {
                    "parallel_edges": r["parallel_edges"],
                    "flexible_edges": r.get("flexible_edges"),
                    **({"flexible_screen": r["flexible_screen"]} if "flexible_screen" in r else {}),
                }
                for r in aux["records"]
            ]
        else:
            out, receipts[arm] = {}, []
        for offset in (0, 1):
            values[arm, offset] = out.get(("weighted-refit", threshold + offset), parent)
    return values, receipts


def synth(plan, table, configs, split, out):
    if split == "synthetic":
        preceding = read_json(checked(plan["source"]["original_guides"]))["synthetic"]
        by_id = {r["id"]: r for r in preceding}
    else:
        before = read_json(checked(plan["source"]["disjoint_guides"]))
        by_id = {r["id"]: r for r in before["synthetic"]}
    rows = []
    for row in table:
        key = row["id"]
        case = read_json(checked(row["case"]))
        prior = by_id[key]
        profile = case["profile"]
        noise, threshold = plan["profiles"][profile], plan["settings"][profile]["threshold"]
        samples, colors = sensor_box(case["sensor"], plan["query_xywh"])
        with np.load(checked(row["prediction"])) as f:
            previous = dict(f)
        assert prior["case"] == row["case"]
        query = prior["query"] if split == "synthetic" else offset_box(plan["query_xywh"])
        cases = []
        witnesses = []
        for role, (rgb, raw, cfa) in enumerate(
            zip(previous["parent"], samples, colors, strict=True)
        ):
            choices = (
                {name: prior["roles"][role]["fits"][name] for name in ("scene", "exact-center")}
                if split == "synthetic"
                else {"scene": prior["rankings"][role]["fits"]["scene"]}
            )
            corrected, fit_details = {}, {}
            for g, guess in choices.items():
                images, receipts = predict(rgb, raw, cfa, guess, noise, query, configs, threshold)
                corrected.update({field(g, arm, t): x for (arm, t), x in images.items()})
                fit_details[g] = receipts
            cases.append(corrected)
            witnesses.append(fit_details)
        arrays = previous | {k: np.stack([r[k] for r in cases]) for k in cases[0]}
        rows.append(
            row
            | {
                "before": row["prediction"],
                "witnesses_flexible": witnesses,
                "prediction": write_array(out / f"{key}.npz", **arrays),
            }
        )
        print(split, key, flush=True)
    return rows


def camera(plan, current, out, configs):
    previous = read_json(checked(plan["previous"]))["camera"]
    baseline = read_json(checked(plan["camera_baseline"]))["camera"]
    conditioning = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    rows = []
    for recent, prior, scene in zip(current, previous, baseline, strict=True):
        key, source = recent["id"], scene["source"]
        assert key == prior["id"] == scene["id"]
        x, y, w, h = source["query_box"]
        with np.load(checked(source["query_arrays"])) as f:
            packed, colors = (
                f["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2],
                f["colors"][0],
            )
        with np.load(checked(recent["predictions"])) as f:
            pixels = dict(f)
        receipts = {}
        for guide, fit in prior["fits"].items():
            values, receipts[guide] = predict(
                pixels["parent"],
                packed,
                colors,
                fit,
                conditioning[key],
                prior["query"],
                configs,
                2,
                edge_side=True,
            )
            pixels.update({field(guide, arm, t): value for (arm, t), value in values.items()})
        rows.append(
            recent
            | {
                "before": recent["predictions"],
                "flexible_edges": receipts,
                "predictions": write_array(out / f"{key}.npz", **pixels),
            }
        )
        print("camera", key, flush=True)
    return rows


def nulls(plan, configs, label):
    source = read_json(checked(plan["source"][f"null-{label}.json"]))
    recipe = structure_module(plan["structure"])
    constructor = recipe.construct if label == "retained" else fresh_structure
    cases = []
    for r in source["rows"]:
        profile = r["profile"]
        noise, threshold = plan["profiles"][profile], plan["settings"][profile]["threshold"]
        target = constructor(r["style"], r["angle_radians"], *r["width_shift_level_height"])
        colors = np.array(PATTERNS[r["CFA"]])
        rng = np.random.default_rng(np.random.SeedSequence(r["noise_seed"]))
        packed = recipe.corrupt(target, colors, rng, noise)
        guide = {"active": [True, True], "frequencies_xy": r["guide_frequencies_xy"]}
        values, diagnostics = predict(
            target, packed, colors, guide, noise, recipe.QUERY, configs, threshold
        )
        metrics = dict(r["metrics"])
        for (arm, t), pixels in values.items():
            correction = (pixels[recipe.MEASURE].astype(float) - target[recipe.MEASURE]) * 65535
            metrics[field("null", arm, t)] = {
                "RMS_DN16": float(np.sqrt(np.mean(correction**2))),
                "max_abs_DN16": float(np.max(np.abs(correction))),
                "changed_pixels": int(np.any(correction != 0, axis=0).sum()),
            }
        cases.append(r | {"metrics": metrics, "boundaries": diagnostics})
        print(label, profile, r["style"], r["trial"], flush=True)
    return cases


def run(path, task):
    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    cfg = LocalWaveConfig(**plan["config"])
    configs = {arm: replace(cfg, background=name) for arm, name in MODES.items()}
    root = Path(plan["root"])
    start = time.monotonic()
    if task in ("fresh", "retained"):
        result = {"rows": nulls(plan, configs, task)}
    else:
        out = root / f"arrays-{task}"
        out.mkdir()
        current = read_json(checked(plan["source"]["output/collection.json"]))
        if task == "camera":
            result = {"rows": camera(plan, current[task], out, configs)}
        else:
            result = {"rows": synth(plan, current[task], configs, task, out)}
    write_json(
        root / f"{task}.json",
        result
        | {
            "plan": reference(path),
            "CPU_wall_seconds": time.monotonic() - start,
            "producer": reference(__file__),
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="action", required=True)
    init = actions.add_parser("prepare")
    init.add_argument("root", type=Path)
    init.add_argument("local", type=Path)
    init.add_argument("scene", type=Path)
    execute = actions.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("task", choices=("synthetic", "disjoint", "camera", "fresh", "retained"))
    a = cli.parse_args()
    if a.action == "prepare":
        prepare(a.root.resolve(), a.local.resolve(), a.scene.resolve())
    else:
        run(a.plan.resolve(), a.task)
