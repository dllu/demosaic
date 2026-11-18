"""Compare reserved-RAW shared perspective against independently chosen phase changes."""

import argparse
import time
from dataclasses import replace
from functools import partial
from pathlib import Path

import numpy as np
from probe_flexible_query_edges import camera, synth
from probe_fresh_phase_refit import write_array
from probe_local_phase_bounds import fresh_structure, structure_module
from probe_surface_aggregation import field
from probe_wire_envelopes import score

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
from demosaic.shared_projective_phase import (
    GRADIENT_STEPS,
    MINIMUM_GEOMETRY_GAIN,
    projective_hessians,
    reserve_projective_phase,
)

SEED = 202611172254
MODES = ("screened", "anchor", "shared", "independent", "transfer")
PANELS = (
    "projective400",
    "projective6400",
    "synthetic",
    "disjoint",
    "null400",
    "null6400",
    "camera",
)


def prepare(root, base, ranking):
    original = reference(base / "plan.json")
    plan = read_json(checked(original))
    receipts = {
        p: reference(base / f"{p}.json") for p in ("synthetic", "disjoint", "replication", "camera")
    }
    root.mkdir()
    snapshot, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "probe_matched_query_evidence.py"]
    )
    write_json(
        root / "plan.json",
        plan
        | {
            "root": str(root),
            "work": str(snapshot),
            "frozen_files": hashes,
            "driver": reference(snapshot / "scripts" / Path(__file__).name),
            "inputs": [
                original,
                *receipts.values(),
                *plan["inputs"],
                plan["previous"],
                plan["structure"],
            ],
            "screened_receipts": receipts,
            "geometry_seed": SEED,
            "geometry_profiles": {"shared": 6, "different": 4, "planar": 2},
            "geometry_screen": {
                "steps_times_native_side": GRADIENT_STEPS,
                "minimum_score": MINIMUM_GEOMETRY_GAIN,
                "ranking": ranking,
            },
            "scope": "On two crossed halves of the screening reserve, compare a second-order perspective "
            "phase with the planar prediction and the carrier-absent null. Estimate two gradient components "
            "per active direction with a screened background and separate CFA color fits. Compare planar, "
            "first-active anchor only, shared perspective, independent direction estimates, and transfer "
            "with an unchanged planar anchor. Keep the "
            "original complementary support, full eight-knot query profiles and all-site weighted delivery.",
        },
    )


def predict(
    parent,
    packed,
    colors,
    guide,
    noise,
    query,
    config,
    threshold,
    *,
    edge_side=False,
    oracle=None,
    ranking="predictive",
):
    stops = (threshold, threshold + 1)
    plans, receipt = reserve_projective_phase(
        packed,
        colors,
        query,
        guide,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        ranking=ranking,
    )
    if plans is None:
        return {(a, t): parent for a in MODES for t in stops}, receipt
    d = receipt["anchor"]
    anchor = np.zeros((2, 2, 2))
    anchor[d] = plans[d, d]
    shared = plans[d] if all(guide["active"]) else anchor
    transfer = shared - anchor
    modes = {
        "screened": np.zeros((2, 2, 2)),
        "anchor": anchor,
        "shared": shared,
        "independent": np.stack((plans[0, 0], plans[1, 1])),
        "transfer": transfer,
    }
    if oracle is not None:
        modes["oracle"] = oracle
        target_companion = oracle.copy()
        target_companion[d] = 0
        modes["oracle-weak"] = target_companion
    cache = {}
    results = {}
    evidence = ~screening_mask(query)
    for name, h in modes.items():
        key = tuple(h.ravel())
        if key not in cache:
            out, _ = restore_local_waves(
                parent,
                packed,
                colors,
                shot=noise["shot"],
                read=noise["read"],
                config=config,
                thresholds=stops,
                evidence_mask=evidence,
                guide_frequencies_xy=guide["frequencies_xy"],
                guide_phase_hessians_xy=h if np.any(h) else None,
                phase_bins=8,
                shrink_phase_fit=True,
                compare_pooled_support=True,
                compare_pooled_refit=True,
                phase_edge_side="validation" if edge_side else None,
                active_guide_directions=guide["active"],
            )
            cache[key] = {t: out["weighted-refit", t] for t in stops}
        results.update({(name, t): x for t, x in cache[key].items()})
    return results, receipt


def adapter(
    parent,
    packed,
    colors,
    guide,
    noise,
    query,
    config,
    threshold,
    *,
    edge_side=False,
    ranking="predictive",
):
    images, receipt = predict(
        parent,
        packed,
        colors,
        guide,
        noise,
        query,
        config,
        threshold,
        edge_side=edge_side,
        ranking=ranking,
    )
    return {(a, int(t - threshold)): img for (a, t), img in images.items()}, receipt


def target(index, seed):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 0, index]))
    style = "bent-rail" if index % 2 == 0 else "two-rails"
    angle, width, shift, level, contrast = rng.uniform(
        [0.1, 6, -24, 0.036, 0.06], [3.02, 14, 24, 0.085, 0.145]
    )
    parent = fresh_structure(style, angle, width, shift, level, contrast)
    shape = parent.shape[1:]
    offsets = np.array([np.cos(angle), np.sin(angle)]) * (shift + 6)
    yy, xx = np.indices(shape) - 127.5
    phi = angle + np.deg2rad(rng.uniform([48, 5], [68, 15]))
    frequencies = (
        np.column_stack((np.cos(phi), np.sin(phi))) / rng.uniform([10, 12], [14, 18])[:, None]
    )
    direction = rng.uniform(0, 2 * np.pi)
    strong_gradient = (
        np.array([np.cos(direction), np.sin(direction)]) * rng.uniform(0.10, 0.19) / 256
    )
    if index < 6:
        kind, weak_gradient = "shared", strong_gradient
    elif index < 10:
        kind, weak_gradient = "different", -strong_gradient[::-1]
    else:
        kind, strong_gradient, weak_gradient = "planar", np.zeros(2), np.zeros(2)
    h = np.stack(
        (
            projective_hessians(frequencies, strong_gradient)[0],
            projective_hessians(frequencies, weak_gradient)[1],
        )
    )
    x, y = xx - offsets[0], yy - offsets[1]
    along = -np.sin(angle) * x + np.cos(angle) * y - rng.uniform(-23, 23)
    across = np.cos(angle) * x + np.sin(angle) * y
    rad = np.hypot(along / rng.uniform(96, 112), across / rng.uniform(64, 78))
    envelope = np.cos((np.pi / 2) * np.minimum(rad, 1)) ** 2
    envelope[rad >= 1] = 0
    phases = rng.uniform(0, 1, 2)
    strengths = rng.uniform([0.0065, 0.0014], [0.009, 0.0022])
    widths = rng.uniform([0.055, 0.043], [0.085, 0.065])
    rgb = np.array([[0.69, 1, 0.63], [-0.42, 1, 0.58] if index % 2 else [0.63, 1, 0.59]])
    components = []
    for f, Hess, phase, amp, spread, chroma in zip(
        frequencies, h, phases, strengths, widths, rgb, strict=True
    ):
        wire = np.zeros(shape)
        for dx in (-0.25, 0.25):
            for dy in (-0.25, 0.25):
                qx, qy = xx + dx, yy + dy
                p = (
                    f[0] * qx
                    + f[1] * qy
                    + phase
                    + 0.5 * (Hess[0, 0] * qx**2 + 2 * Hess[0, 1] * qx * qy + Hess[1, 1] * qy**2)
                )
                folded = np.remainder(p + 0.5, 1) - 0.5
                wire += 0.25 * np.exp(-0.5 * (folded / spread) ** 2)
        profile = envelope * (wire - np.sum(envelope * wire) / envelope.sum())
        components.append((amp * chroma[:, None, None] * profile).astype(np.float32))
    one = parent + components[0]
    return (
        parent,
        one,
        one + components[1],
        frequencies,
        h,
        envelope == 0,
        {
            "kind": kind,
            "style": style,
            "gradients_per_native_pixel": [strong_gradient.tolist(), weak_gradient.tolist()],
            "true_hessians_xy": h.tolist(),
        },
    )


def fresh(plan, config, recipe, profile):
    settings, noise = plan["settings"][profile], plan["profiles"][profile]
    rows = []
    root = Path(plan["root"])
    for i in range(sum(plan["geometry_profiles"].values())):
        parent, strong, both, frequencies, hessians, quiet, metadata = target(
            i, plan["geometry_seed"]
        )
        cfa = tuple(PATTERNS)[i % 4]
        colors = np.asarray(PATTERNS[cfa])
        guide = {"active": [True, True], "frequencies_xy": frequencies.tolist()}
        outputs, choices = [], []
        for role, truth in enumerate((strong, both)):
            seed = np.random.SeedSequence(
                [plan["geometry_seed"], 1, i, int(profile == "iso6400"), role]
            )
            packed = recipe.corrupt(truth, colors, np.random.default_rng(seed), noise)
            images, witness = predict(
                parent,
                packed,
                colors,
                guide,
                noise,
                recipe.QUERY,
                config,
                settings["threshold"],
                oracle=hessians,
                ranking=plan["geometry_screen"]["ranking"],
            )
            outputs.append(images)
            choices.append(witness)
        metrics = score(
            parent, strong, both, outputs, quiet, settings["scale"], settings["threshold"]
        )
        arrays = write_array(
            root / f"{profile}-{i}.npz",
            parent=parent,
            strong=strong,
            target=both,
            packed=packed,
            cfa=colors,
            quiet=quiet,
            **{a: img for (a, t), img in outputs[1].items() if t == settings["threshold"]},
        )
        rows.append(
            metadata
            | {
                "case": i,
                "profile": profile,
                "CFA": cfa,
                "guide": guide,
                "selection": choices,
                "metrics": metrics,
                "prediction": arrays,
            }
        )
        print(
            profile,
            i,
            metadata["kind"],
            [(r["accepted"], r["proposed"]) for r in choices[1]["directions"]],
            flush=True,
        )
    return rows


def controls(plan, config, recipe, profile):
    original = read_json(checked(plan["screened_receipts"]["replication"]))["rows"]
    noise, settings = plan["profiles"][profile], plan["settings"][profile]
    t = settings["threshold"]
    rows = []
    for row in original:
        if row["profile"] != profile:
            continue
        style = row["style"]
        ctor = recipe.construct if style in ("flat", "step", "rail") else fresh_structure
        parent = ctor(style, row["angle_radians"], *row["width_shift_level_height"])
        colors = np.asarray(PATTERNS[row["CFA"]])
        rng = np.random.default_rng(np.random.SeedSequence(row["noise_seed"]))
        raw = recipe.corrupt(parent, colors, rng, noise)
        guide = {"active": [True, True], "frequencies_xy": row["guide_frequencies_xy"]}
        outputs, witness = predict(
            parent,
            raw,
            colors,
            guide,
            noise,
            recipe.QUERY,
            config,
            t,
            ranking=plan["geometry_screen"]["ranking"],
        )
        metrics = {}
        for (mode, stop), image in outputs.items():
            d = (image[recipe.MEASURE].astype(float) - parent[recipe.MEASURE]) * 65535
            label = field("null", mode, int(stop - t))
            metrics[label] = {
                "RMS_DN16": float(np.sqrt(np.mean(d**2))),
                "max_abs_DN16": float(np.max(np.abs(d))),
                "changed_pixels": int(np.count_nonzero(np.any(d != 0, axis=0))),
            }
            if mode == "screened":
                assert metrics[label] == row["metrics"][label]
        rows.append(
            {
                "style": style,
                "trial": row["trial"],
                "profile": profile,
                "selection": witness,
                "metrics": metrics,
            }
        )
        print("null", profile, style, row["trial"], flush=True)
    return rows


def run(path, panel):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    root = path.parent
    cfg = replace(LocalWaveConfig(**plan["config"]), background="screened_curved4_step")
    profile = "iso6400" if panel.endswith("6400") else "iso400"
    start = time.monotonic()
    if panel.startswith(("null", "projective")):
        recipe = structure_module(plan["structure"])
        rows = (fresh if panel.startswith("projective") else controls)(plan, cfg, recipe, profile)
    else:
        out = root / f"arrays-{panel}"
        out.mkdir()
        original = read_json(checked(plan["screened_receipts"][panel]))["rows"]
        predictor = partial(adapter, ranking=plan["geometry_screen"]["ranking"])
        rows = (
            camera(plan, original, out, cfg, predictor=predictor)
            if panel == "camera"
            else synth(plan, original, cfg, panel, out, predictor=predictor)
        )
        key = "predictions" if panel == "camera" else "prediction"
        for row, before in zip(rows, original, strict=True):
            assert row["id"] == before["id"]
            with np.load(checked(row[key])) as new, np.load(checked(before[key])) as old:
                for name in old.files:
                    np.testing.assert_array_equal(new[name], old[name])
    write_json(
        root / f"{panel}.json",
        {
            "plan": reference(path),
            "producer": reference(__file__),
            "rows": rows,
            "CPU_wall_seconds": time.monotonic() - start,
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="mode", required=True)
    setup = commands.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("base", type=Path)
    setup.add_argument("--ranking", choices=("predictive", "standardized"), default="predictive")
    execute = commands.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("panel", choices=PANELS)
    args = cli.parse_args()
    if args.mode == "prepare":
        prepare(args.root.resolve(), args.base.resolve(), args.ranking)
    else:
        run(args.plan.resolve(), args.panel)
