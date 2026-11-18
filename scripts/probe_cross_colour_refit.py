"""Change only the validation gate of the screened, per-color weighted RAW refit."""

import argparse
import importlib.util
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
import torch
from probe_flexible_query_edges import camera, synth
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
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
from demosaic.search_donor_geometry import screening_mask

MODES = {"screened": "weighted-refit", "joint": "joint-refit", "partners": "partner-refit"}
PANELS = ("synthetic", "disjoint", "camera", "replication", "sensitivity")


def prepare(root, previous):
    original = reference(previous / "plan.json")
    plan = read_json(checked(original))
    receipts = {label: reference(previous / f"{label}.json") for label in PANELS}
    sensitivity = read_json(checked(receipts["sensitivity"]))
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "probe_matched_query_evidence.py"]
    )
    write_json(
        root / "plan.json",
        plan
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [
                original,
                *plan["inputs"],
                *receipts.values(),
                sensitivity["target_recipe"],
                sensitivity["source"],
            ],
            "screened_receipts": receipts,
            "modes": MODES,
            "scope": "Keep the screened nuisance, two independent RAW folds, and the per-color "
            "weighted fit fixed. Compare the established per-color gate with pooled CFA evidence "
            "and bounded leave-one-color-out support. The cap is twice each color's own crossed-fold "
            "score and requires positive own-color evidence in both folds. Use the established "
            "same-side camera validation and all original guides, RAW observations and settings.",
        },
    )


def predict(parent, packed, colors, guide, noise, query, config, threshold, *, edge_side=False):
    out = {}
    if any(guide["active"]):
        out, _ = restore_local_waves(
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
            compare_cross_colour_refit=True,
            phase_edge_side="validation" if edge_side else None,
            active_guide_directions=guide["active"],
        )
    return {
        (arm, offset): out.get((mode, threshold + offset), parent)
        for arm, mode in MODES.items()
        for offset in (0, 1)
    }, {}


def replicate(plan, config, source):
    recipe = structure_module(plan["structure"])
    rows = []
    for row in source["rows"]:
        style, profile = row["style"], row["profile"]
        constructor = recipe.construct if style in ("flat", "step", "rail") else fresh_structure
        target = constructor(style, row["angle_radians"], *row["width_shift_level_height"])
        colors = np.asarray(PATTERNS[row["CFA"]])
        rng = np.random.default_rng(np.random.SeedSequence(row["noise_seed"]))
        noise, threshold = plan["profiles"][profile], plan["settings"][profile]["threshold"]
        packed = recipe.corrupt(target, colors, rng, noise)
        guide = {"active": [True, True], "frequencies_xy": row["guide_frequencies_xy"]}
        values, _ = predict(target, packed, colors, guide, noise, recipe.QUERY, config, threshold)
        metrics = {}
        for (arm, offset), image in values.items():
            d = (image[recipe.MEASURE].astype(float) - target[recipe.MEASURE]) * 65535
            key = field("null", arm, offset)
            metrics[key] = {
                "RMS_DN16": float(np.sqrt(np.mean(d**2))),
                "max_abs_DN16": float(np.max(np.abs(d))),
                "changed_pixels": int(np.count_nonzero(np.any(d != 0, axis=0))),
            }
            if arm == "screened":
                assert metrics[key] == row["metrics"][key]
        rows.append(row | {"metrics": metrics})
        print("replication", profile, style, row["trial"], flush=True)
    return rows


def sensitivity(plan, config, source):
    path = checked(source["target_recipe"])
    spec = importlib.util.spec_from_file_location("rail_wire_targets", path)
    target_recipe = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(target_recipe)
    original = read_json(checked(plan["source"]["null-fresh.json"]))["rows"]
    cases = [r for r in original if r["style"] in ("bent-rail", "two-rails")]
    recipe = structure_module(plan["structure"])
    rows = []
    for i, (case, prior) in enumerate(zip(cases, source["rows"], strict=True)):
        profile = case["profile"]
        noise, settings = plan["profiles"][profile], plan["settings"][profile]
        parent, strong, both, frequencies, quiet = target_recipe.targets(case)
        assert i == prior["case"] and case["style"] == prior["style"]
        np.testing.assert_array_equal(frequencies, prior["wire_frequency"])
        colors = np.asarray(PATTERNS[case["CFA"]])
        guide = {"active": [True, True], "frequencies_xy": frequencies.tolist()}
        images = []
        for role, signal in enumerate((strong, both)):
            seed = np.random.SeedSequence([target_recipe.SEED, 1, i, role])
            packed = recipe.corrupt(signal, colors, np.random.default_rng(seed), noise)
            result, _ = predict(
                parent, packed, colors, guide, noise, recipe.QUERY, config, settings["threshold"]
            )
            images.append(result)
        truth = (both.astype(float) - strong).ravel()
        norm, scale = truth @ truth, settings["scale"]
        metrics = {}
        for (arm, offset), image in images[1].items():
            image = image.astype(float)
            correction = scale * (image - images[0][arm, offset]).ravel()
            quiet_error = scale * (image[:, quiet] - parent[:, quiet])
            key = f"{arm}{'-strict' if offset else ''}"
            metrics[key] = {
                "weak_projection": float(correction @ truth / norm),
                "increment_RMS_DN16": float(np.sqrt(np.mean((correction - truth) ** 2)) * 65535),
                "quiet_RMS_DN16": float(np.sqrt(np.mean(quiet_error**2)) * 65535),
            }
            if arm == "screened":
                np.testing.assert_allclose(
                    list(metrics[key].values()), list(prior["metrics"][key].values()), atol=2e-12
                )
        rows.append({k: v for k, v in prior.items() if k != "screens"} | {"metrics": metrics})
        print("sensitivity", profile, case["style"], case["trial"], flush=True)
    return rows


def run(path, panel):
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    config = replace(LocalWaveConfig(**plan["config"]), background="screened_curved4_step")
    root = Path(plan["root"])
    start = time.monotonic()
    before = read_json(checked(plan["screened_receipts"][panel]))
    if panel == "replication":
        rows = replicate(plan, config, before)
    elif panel == "sensitivity":
        rows = sensitivity(plan, config, before)
    else:
        output = root / f"arrays-{panel}"
        output.mkdir()
        if panel == "camera":
            rows = camera(plan, before["rows"], output, config, predictor=predict)
            key = "predictions"
        else:
            rows = synth(plan, before["rows"], config, panel, output, predictor=predict)
            key = "prediction"
        for row, prior in zip(rows, before["rows"], strict=True):
            assert row["id"] == prior["id"]
            with np.load(checked(row[key])) as actual, np.load(checked(prior[key])) as archived:
                for name in archived.files:
                    if "screened" in name:
                        np.testing.assert_array_equal(actual[name], archived[name])
    write_json(
        root / f"{panel}.json",
        {
            "plan": reference(path),
            "source": plan["screened_receipts"][panel],
            "producer": reference(__file__),
            "rows": rows,
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
    execute.add_argument("panel", choices=PANELS)
    args = cli.parse_args()
    if args.action == "prepare":
        prepare(args.root.resolve(), args.previous.resolve())
    else:
        run(args.plan.resolve(), args.panel)
