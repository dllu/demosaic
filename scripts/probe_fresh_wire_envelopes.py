"""Replicate envelope effects on independently drawn finite wires beside rails."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_fresh_phase_refit import write_array
from probe_local_phase_bounds import fresh_structure, structure_module
from probe_wire_envelopes import footprint, predict, score

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

SEED = 202611172131
FUNDAMENTAL_FOOTPRINTS = ("exact-fundamental", "broad-fundamental", "shifted-fundamental")


def setup(root, base, controls=None, fundamental_footprints=False):
    original = reference(base / "plan.json")
    prior = read_json(checked(original))
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "probe_matched_query_evidence.py"]
    )
    inputs = [original, prior["structure"]]
    if controls is not None:
        controls = reference(controls)
        inputs.append(controls)
    write_json(
        root / "plan.json",
        prior
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": inputs,
            "controls": controls,
            **({"arms": FUNDAMENTAL_FOOTPRINTS} if fundamental_footprints else {}),
            "fresh_seed": SEED,
            "trials_per_profile": 8,
            "scope": "Independent finite, tapered wires beside complex rails. All four CFA layouts, both "
            "noise profiles, planar gray and chirped signed-color families. The matched envelope reproduces "
            "the nominal ellipse, whose local break on the chirped fixtures is withheld. Frequencies "
            "describe center phase gradient. Use the same two disjoint sensor observations and gates.",
            **(
                {
                    "scope": "Replay forced-frequency flat and rail-only controls with tapered footprints "
                    "placed beside the nominal edge, with the original RAW samples and gates."
                }
                if controls is not None
                else {}
            ),
        },
    )


def targets(index, seed, *, along_limit=35):
    rng = np.random.default_rng(np.random.SeedSequence([seed, 0, index]))
    style = "bent-rail" if index % 2 == 0 else "two-rails"
    angle, width, shift, level, height = rng.uniform(
        [0.1, 5, -27, 0.032, 0.058], [3.02, 15, 27, 0.085, 0.145]
    )
    rail = fresh_structure(style, angle, width, shift, level, height)
    yy, xx = np.indices(rail.shape[1:]) - 127.5
    along = -np.sin(angle) * xx + np.cos(angle) * yy - rng.uniform(-along_limit, along_limit)
    across = np.cos(angle) * xx + np.sin(angle) * yy - (shift + rng.uniform(3, 11))
    radii = rng.uniform([71, 41], [103, 70])

    def envelope(growth, offset):
        radius = np.hypot(along / (radii[0] * growth), (across - offset) / (radii[1] * growth))
        return np.where(radius < 1, np.cos(np.pi * np.minimum(radius, 1) / 2) ** 2, 0)

    fields = {
        "exact": envelope(1, 0),
        "broad": envelope(1.5, 0),
        "shifted": envelope(1, (-1) ** index * 40),
    }
    actual = fields["exact"]
    chirped = index >= 4
    chord = rng.uniform(-17, 17)
    if chirped:
        actual = actual * (1 - 0.8 * np.exp(-(((along - chord) / 10) ** 2)))
    angle_pair = angle + np.deg2rad(rng.uniform([48, 7], [66, 16]))
    periods = rng.uniform([10, 12], [14, 19])
    freq = np.column_stack((np.cos(angle_pair), np.sin(angle_pair))) / periods[:, None]
    phases = rng.uniform(0, 1, 2)
    chirp = rng.uniform([1.3e-5, -5.1e-5], [5.1e-5, -1.3e-5]) if chirped else np.zeros(2)
    strengths = rng.uniform([0.0026, 0.00065], [0.0039, 0.00105])
    colours = np.array(((0.63, 1, 0.78), (-0.65, 1, 0.46) if chirped else (0.87, 1, 0.79)))
    increments = [
        (
            colors[:, None, None]
            * amplitude
            * actual
            * np.sinc(u)
            * np.sinc(v)
            * np.cos(2 * np.pi * (u * xx + v * yy + phase + bend * along**2))
        ).astype(np.float32)
        for (u, v), phase, amplitude, bend, colors in zip(
            freq, phases, strengths, chirp, colours, strict=True
        )
    ]
    strong = rail + increments[0]
    meta = {
        "style": style,
        "chirped_signed_color": chirped,
        "geometry": [angle, width, shift, level, height],
        "radii": radii.tolist(),
        "poisson_seed_prefix": [seed, 1],
    }
    return rail, strong, strong + increments[1], freq, fields, meta


def run(path, profile):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    recipe = structure_module(plan["structure"])
    config = LocalWaveConfig(**plan["config"])
    op, noise = plan["settings"][profile], plan["profiles"][profile]
    threshold = op["threshold"]
    parent_dir = Path(plan["root"])
    if plan.get("controls") is not None:
        run_controls(plan, path, profile, recipe, config, noise, threshold)
        return
    count = plan["trials_per_profile"]
    start = time.monotonic()
    rows = []
    for i in range(count):
        parent, strong, both, frequencies, fields, meta = targets(i, plan["fresh_seed"])
        quiet = fields["exact"] == 0
        cfa = tuple(PATTERNS)[i % 4]
        colors = np.asarray(PATTERNS[cfa])
        images = []
        for role, truth in enumerate((strong, both)):
            words = [plan["fresh_seed"], 1, int(profile == "iso6400"), i, role]
            rng = np.random.default_rng(np.random.SeedSequence(words))
            raw = recipe.corrupt(truth, colors, rng, noise)
            images.append(
                predict(
                    parent,
                    raw,
                    colors,
                    frequencies,
                    fields,
                    noise,
                    config,
                    recipe.QUERY,
                    threshold,
                    arms=plan["arms"],
                )
            )
        metrics = score(parent, strong, both, images, quiet, op["scale"], threshold)
        prediction = write_array(
            parent_dir / f"{profile}-{i}.npz",
            packed=raw,
            cfa=colors,
            parent=parent,
            target=both,
            strong=strong,
            **fields,
            **{
                f"restored_{arm}": image
                for (arm, stop), image in images[1].items()
                if stop == threshold
            },
        )
        rows.append(
            meta
            | {
                "case": i,
                "profile": profile,
                "CFA": cfa,
                "frequencies_xy": frequencies.tolist(),
                "metrics": metrics,
                "predictions": prediction,
            }
        )
        print(
            profile,
            i,
            meta["style"],
            {k: round(metrics[k]["weak_projection"] * 100, 3) for k in plan["arms"]},
            flush=True,
        )
    write_json(
        parent_dir / f"{profile}.json",
        {
            "plan": reference(path),
            "producer": reference(__file__),
            "rows": rows,
            "CPU_wall_seconds": time.monotonic() - start,
        },
    )


def run_controls(plan, path, profile, recipe, config, noise, threshold):
    start = time.monotonic()
    rows = []
    old = read_json(checked(plan["controls"]))["rows"]
    for row in old:
        if row["profile"] != profile:
            continue
        style = row["style"]
        constructor = recipe.construct if style in ("flat", "step", "rail") else fresh_structure
        target = constructor(style, row["angle_radians"], *row["width_shift_level_height"])
        colors = np.asarray(PATTERNS[row["CFA"]])
        rng = np.random.default_rng(np.random.SeedSequence(row["noise_seed"]))
        raw = recipe.corrupt(target, colors, rng, noise)
        fields = {
            key: footprint(
                row, target.shape[1:], plan["fresh_seed"], plan["ellipse_radii_pixels"], *value
            )
            for key, value in plan["envelope_variants"].items()
        }
        outputs = predict(
            target,
            raw,
            colors,
            row["guide_frequencies_xy"],
            fields,
            noise,
            config,
            recipe.QUERY,
            threshold,
            arms=plan["arms"],
        )
        metrics = {}
        for (arm, stop), image in outputs.items():
            key = (
                arm
                if stop == threshold
                else f"{arm}-{'strict' if stop > threshold else 'positive'}"
            )
            delta = (image[recipe.MEASURE].astype(float) - target[recipe.MEASURE]) * 65535
            metrics[key] = {
                "RMS_DN16": float(np.sqrt(np.mean(delta**2))),
                "peak_DN16": float(np.max(np.abs(delta))),
                "changed_pixels": int(np.count_nonzero(np.any(delta != 0, axis=0))),
            }
            if arm == "uniform" and stop >= threshold:
                baseline = row["metrics"]["null-screened" + ("-strict" if stop > threshold else "")]
                assert list(metrics[key].values()) == list(baseline.values())
        rows.append(
            {k: row[k] for k in ("CFA", "profile", "style", "trial")} | {"metrics": metrics}
        )
        print("null", profile, style, row["trial"], flush=True)
    assert len(rows) == 24
    write_json(
        Path(plan["root"]) / f"{profile}.json",
        {
            "plan": reference(path),
            "producer": reference(__file__),
            "rows": rows,
            "CPU_wall_seconds": time.monotonic() - start,
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="action", required=True)
    prepare = actions.add_parser("prepare")
    prepare.add_argument("root", type=Path)
    prepare.add_argument("previous", type=Path)
    prepare.add_argument("--controls", type=Path)
    prepare.add_argument("--fundamental-footprints", action="store_true")
    execute = actions.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("profile", choices=("iso400", "iso6400"))
    args = cli.parse_args()
    if args.action == "prepare":
        setup(
            args.root.resolve(), args.previous.resolve(), args.controls, args.fundamental_footprints
        )
    else:
        run(args.plan.resolve(), args.profile)
