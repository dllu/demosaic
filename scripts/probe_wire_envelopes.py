"""Test the value of a spatial wire envelope with exact frequencies held fixed."""

import argparse
import importlib.util
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from probe_fresh_phase_refit import write_array
from probe_local_phase_bounds import structure_module

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

ARMS = (
    "uniform",
    "taper-only",
    "exact",
    "broad",
    "shifted",
    "uniform-fundamental",
    "exact-fundamental",
)


def prepare(root, previous):
    original = reference(previous / "plan.json")
    plan = read_json(checked(original))
    archive = reference(previous / "sensitivity.json")
    prior = read_json(checked(archive))
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(),
        root,
        [Path(__file__).name, "probe_flexible_query_edges.py", "probe_matched_query_evidence.py"],
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "archive": archive,
            "target_recipe": prior["target_recipe"],
            "case_catalog": plan["source"]["null-fresh.json"],
            "structure": plan["structure"],
            "inputs": [
                original,
                archive,
                prior["target_recipe"],
                plan["source"]["null-fresh.json"],
                plan["structure"],
            ],
            "config": replace(
                LocalWaveConfig(**plan["config"]), background="screened_curved4_step"
            ).to_dict(),
            "settings": plan["settings"],
            "profiles": plan["profiles"],
            "arms": ARMS,
            "ellipse_radii_pixels": [93, 57],
            "envelope_variants": {"exact": [1, 0], "broad": [1.5, 0], "shifted": [1, 40]},
            "scope": "Paired strong-only and strong-plus-weak RAW with the archived seeds, reference frequencies, "
            "analytic rail parent, predictive gate and weighted refit. Taper the finished correction or fit "
            "with a fixed nonnegative envelope. Include 50% larger radii and a 40-pixel displacement chosen "
            "by trial parity. Isolate the fit shape with a first-harmonic control on uniform and exact support.",
        },
    )


def footprint(row, shape, seed, radii, growth, shift):
    phi = row["angle_radians"]
    rng = np.random.default_rng(
        np.random.SeedSequence([seed, 0, row["trial"], row["style"] == "two-rails"])
    )
    yy, xx = np.indices(shape) - (np.asarray(shape)[:, None, None] - 1) / 2
    along = -np.sin(phi) * xx + np.cos(phi) * yy - rng.uniform(-24, 24)
    across = np.cos(phi) * xx + np.sin(phi) * yy - (row["width_shift_level_height"][1] + 8)
    across -= shift if row["trial"] % 2 else -shift
    radius = np.hypot(along / (radii[0] * growth), across / (radii[1] * growth))
    return np.where(radius < 1, np.cos(np.pi * np.minimum(radius, 1) / 2) ** 2, 0)


def predict(
    parent, raw, colors, frequencies, fields, noise, config, query, threshold, *, arms=ARMS
):
    stops = (threshold, threshold + 1, 0.0)
    result = {}
    for arm in arms:
        fundamental = arm.endswith("-fundamental")
        envelope = fields.get(arm.removesuffix("-fundamental"))
        if arm == "taper-only":
            for stop in stops:
                original = result["uniform", stop]
                pixels = parent + fields["exact"] * (original.astype(float) - parent)
                result[arm, stop] = pixels.astype(parent.dtype)
            continue
        out, _ = restore_local_waves(
            parent,
            raw,
            colors,
            shot=noise["shot"],
            read=noise["read"],
            config=config,
            thresholds=stops,
            evidence_mask=~screening_mask(query),
            guide_frequencies_xy=frequencies,
            phase_bins=8,
            phase_harmonics=((1,), (1,)) if fundamental else None,
            guide_envelopes=np.stack((envelope, envelope)) if envelope is not None else None,
            shrink_phase_fit=True,
            compare_pooled_support=True,
            compare_pooled_refit=True,
            active_guide_directions=[True, True],
        )
        for stop in stops:
            result[arm, stop] = out["weighted-refit", stop]
            if envelope is not None:
                np.testing.assert_array_equal(
                    result[arm, stop][:, envelope == 0], parent[:, envelope == 0]
                )
    return result


def score(parent, strong, both, images, quiet, scale, nominal):
    truth = (both.astype(float) - strong).ravel()
    strong_truth = (strong.astype(float) - parent).ravel()
    magnitude = truth @ truth
    metrics = {}
    for (arm, stop), candidate in images[1].items():
        change = scale * (candidate.astype(float) - parent)
        null = scale * (images[0][arm, stop].astype(float) - parent)
        correction = (change - null).ravel()
        key = arm if stop == nominal else f"{arm}-{'strict' if stop > nominal else 'positive'}"
        metrics[key] = {
            "weak_projection": float(correction @ truth / magnitude),
            "absent_weak_projection": float(null.ravel() @ truth / magnitude),
            "strong_projection": float(null.ravel() @ strong_truth / (strong_truth @ strong_truth)),
            "increment_RMS_DN16": float(np.sqrt(np.mean((correction - truth) ** 2)) * 65535),
            "quiet_RMS_DN16": float(np.sqrt(np.mean(change[:, quiet] ** 2)) * 65535),
            "quiet_null_RMS_DN16": float(np.sqrt(np.mean(null[:, quiet] ** 2)) * 65535),
        }
    return metrics


def run(path, profile):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    seed_source = checked(plan["target_recipe"])
    spec = importlib.util.spec_from_file_location("archived_wire_recipe", seed_source)
    targets = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(targets)
    recipe = structure_module(plan["structure"])
    cases = [
        r
        for r in read_json(checked(plan["case_catalog"]))["rows"]
        if r["style"] in ("bent-rail", "two-rails")
    ]
    archive = read_json(checked(plan["archive"]))["rows"]
    config = LocalWaveConfig(**plan["config"])
    op, noise = plan["settings"][profile], plan["profiles"][profile]
    start = time.monotonic()
    rows = []
    for i, (case, prior) in enumerate(zip(cases, archive, strict=True)):
        if case["profile"] != profile:
            continue
        assert i == prior["case"] and case["style"] == prior["style"]
        parent, strong, both, frequencies, quiet = targets.targets(case)
        np.testing.assert_array_equal(frequencies, prior["wire_frequency"])
        fields = {
            k: footprint(case, parent.shape[1:], targets.SEED, plan["ellipse_radii_pixels"], *v)
            for k, v in plan["envelope_variants"].items()
        }
        np.testing.assert_array_equal(fields["exact"] == 0, quiet)
        colors = np.asarray(PATTERNS[case["CFA"]])
        images = []
        for role, signal in enumerate((strong, both)):
            rng = np.random.default_rng(np.random.SeedSequence([targets.SEED, 1, i, role]))
            raw = recipe.corrupt(signal, colors, rng, noise)
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
                    op["threshold"],
                )
            )
        metrics = score(parent, strong, both, images, quiet, op["scale"], op["threshold"])
        for stop in ("", "-strict"):
            for key, value in prior["metrics"][f"screened{stop}"].items():
                np.testing.assert_allclose(metrics[f"uniform{stop}"][key], value, atol=2e-12)
        quick = write_array(
            Path(plan["root"]) / f"{profile}-{i}.npz",
            packed=raw,
            cfa=colors,
            parent=parent,
            target=both,
            strong=strong,
            **fields,
            **{arm: images[1][arm, op["threshold"]] for arm in ARMS if arm not in fields},
            **{f"restored_{arm}": images[1][arm, op["threshold"]] for arm in fields},
        )
        rows.append(
            case
            | {
                "case": i,
                "frequencies_xy": frequencies.tolist(),
                "metrics": metrics,
                "predictions": quick,
            }
        )
        print(
            profile,
            i,
            case["style"],
            {k: round(metrics[k]["weak_projection"] * 100, 3) for k in ARMS},
            flush=True,
        )
    assert len(rows) == 8
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
    setup = actions.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("previous", type=Path)
    execute = actions.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("profile", choices=("iso400", "iso6400"))
    args = cli.parse_args()
    if args.action == "prepare":
        prepare(args.root.resolve(), args.previous.resolve())
    else:
        run(args.plan.resolve(), args.profile)
