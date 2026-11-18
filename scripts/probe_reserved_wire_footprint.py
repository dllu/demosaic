"""Check whether a separate RAW reserve can locate usable wire support."""

import argparse
import time
from functools import partial
from pathlib import Path

import numpy as np
from probe_flexible_query_edges import camera
from probe_fresh_phase_refit import write_array
from probe_fresh_wire_envelopes import targets
from probe_local_phase_bounds import fresh_structure, structure_module
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
from demosaic.reserved_wire_footprint import (
    CENTERS,
    MINIMUM_LOCALIZATION,
    RADIUS_FRACTION,
    select_wire_footprint,
    wire_footprint,
)
from demosaic.search_donor_geometry import screening_mask

MODES = ("uniform", "centered", "screened", "confirmed")
PROSPECTIVE_SEED = 202611172151
PANELS = ("fresh400", "fresh6400", "offset400", "offset6400", "null400", "null6400", "camera")


def prepare(root, envelopes, screened, partner_only=False, full_profile=False):
    source = reference(envelopes / "plan.json")
    plan = read_json(checked(source))
    archive = {p: reference(envelopes / f"{p}.json") for p in ("iso400", "iso6400")}
    camera_plan = reference(screened / "plan.json")
    cameras = read_json(checked(camera_plan))
    camera_source = reference(screened / "camera.json")
    null_source = reference(screened / "replication.json")
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
                source,
                *archive.values(),
                camera_plan,
                camera_source,
                null_source,
                cameras["previous"],
                cameras["camera_baseline"],
                cameras["camera_conditions"],
                plan["structure"],
            ],
            "fresh_receipts": archive,
            "camera_plan": camera_plan,
            "camera_source": camera_source,
            "null_source": null_source,
            "modes": ("uniform", "partner") if partner_only else MODES,
            "partner_only": partner_only,
            "full_profile": full_profile,
            "prospective_geometry": {
                "seed": PROSPECTIVE_SEED,
                "along_limit": 67,
                "cases_per_noise": 8,
            },
            "selection": {
                "center_fractions": CENTERS,
                "radius_fraction": RADIUS_FRACTION,
                "screened_threshold": 0,
                "confirmed_threshold": MINIMUM_LOCALIZATION,
            },
            "scope": "Use the existing query screening sites only to locate an ellipse-sized circle. "
            "Compare a localized fundamental with the absent carrier and the uniform fundamental on crossed "
            "halves of the reserve. The other direction and nuisance remain competitors. Rank by the "
            "minimum gain across the two references and folds. If admitted, refit both directions with "
            "that support on the remaining Bayer sites and give each direction its own delivery gate. "
            "Compare uniform, fixed query center, and two reserve thresholds with the original weights.",
            **(
                {
                    "scope": "Replay the same reserve search. With its confirmed threshold, apply the "
                    "taper only to the direction that did not determine its location. Keep the confirming "
                    "direction uniform. Both directions use the unchanged crossed final admission."
                }
                if partner_only
                else {}
            ),
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
    oracle_envelope=None,
    partner_only=False,
    full_profile=False,
):
    stops = (threshold, threshold + 1)
    arms = ("uniform", "partner") if partner_only else MODES
    if not any(guide["active"]):
        return {(mode, t): parent for mode in arms for t in stops}, {
            "winner": None,
            "reason": "no guide",
        }
    circles, trace = select_wire_footprint(
        packed,
        colors,
        query,
        guide["frequencies_xy"],
        guide["active"],
        shot=noise["shot"],
        read=noise["read"],
        config=config,
    )
    if partner_only:
        envelope = circles["confirmed"]
        partner = None
        if envelope is not None and all(guide["active"]):
            partner = np.stack((envelope, envelope))
            partner[trace["winner"]["direction"]] = 1
        shapes = {"uniform": None, "partner": partner}
    else:
        height, width = parent.shape[1:]
        center = ((width - 1) / 2, (height - 1) / 2)
        shapes = {"uniform": None, "centered": wire_footprint((height, width), center), **circles}
        if oracle_envelope is not None:
            shapes["oracle"] = oracle_envelope
    evidence = ~screening_mask(query)
    restored = {}
    values = {}
    for arm, envelope in shapes.items():
        key = id(envelope)
        if key not in restored:
            outputs, _ = restore_local_waves(
                parent,
                packed,
                colors,
                shot=noise["shot"],
                read=noise["read"],
                config=config,
                thresholds=stops,
                evidence_mask=evidence,
                guide_frequencies_xy=guide["frequencies_xy"],
                phase_bins=8,
                phase_harmonics=None if full_profile else ((1,), (1,)),
                guide_envelopes=(
                    np.broadcast_to(envelope, (2, *parent.shape[1:]))
                    if envelope is not None
                    else None
                ),
                shrink_phase_fit=True,
                compare_pooled_support=True,
                compare_pooled_refit=True,
                phase_edge_side="validation" if edge_side else None,
                active_guide_directions=guide["active"],
            )
            restored[key] = {t: outputs["weighted-refit", t] for t in stops}
        values.update({(arm, t): pixels for t, pixels in restored[key].items()})
    return values, trace


def camera_predict(
    parent,
    packed,
    colors,
    guide,
    noise,
    query,
    config,
    threshold,
    *,
    edge_side,
    partner_only,
    full_profile=False,
):
    images, trace = predict(
        parent,
        packed,
        colors,
        guide,
        noise,
        query,
        config,
        threshold,
        edge_side=edge_side,
        partner_only=partner_only,
        full_profile=full_profile,
    )
    return {(a, int(t - threshold)): x for (a, t), x in images.items()}, trace


def positives(root, recipe, plan, config, profile, panel, noise, setting):
    archived = panel.startswith("fresh")
    if archived:
        seed = plan["fresh_seed"]
        along_limit = 35
        rows = read_json(checked(plan["fresh_receipts"][profile]))["rows"]
        count = len(rows)
    else:
        design = plan["prospective_geometry"]
        seed, along_limit, count = (design[k] for k in ("seed", "along_limit", "cases_per_noise"))
    result = []
    for i in range(count):
        parent, strong, both, frequencies, fields, meta = targets(i, seed, along_limit=along_limit)
        cfa = tuple(PATTERNS)[i % 4]
        colors = np.asarray(PATTERNS[cfa])
        xy = np.unravel_index(fields["exact"].argmax(), fields["exact"].shape)[::-1]
        guide = {"frequencies_xy": frequencies.tolist(), "active": [True, True]}
        values, traces = [], []
        for role, truth in enumerate((strong, both)):
            seed_words = [seed, 1, int(profile == "iso6400"), i, role]
            rng = np.random.default_rng(np.random.SeedSequence(seed_words))
            raw = recipe.corrupt(truth, colors, rng, noise)
            images, trace = predict(
                parent,
                raw,
                colors,
                guide,
                noise,
                recipe.QUERY,
                config,
                setting["threshold"],
                oracle_envelope=None if archived or plan.get("partner_only") else fields["exact"],
                partner_only=plan.get("partner_only", False),
                full_profile=plan.get("full_profile", False),
            )
            if trace["winner"] is not None:
                trace["center_error_px"] = float(
                    np.linalg.norm(np.asarray(trace["winner"]["center_xy"]) - xy)
                )
            traces.append(trace)
            values.append(images)
        metrics = score(
            parent,
            strong,
            both,
            values,
            fields["exact"] == 0,
            setting["scale"],
            setting["threshold"],
        )
        references = {}
        if archived:
            old = rows[i]
            assert old["case"] == i and old["CFA"] == cfa
            with np.load(checked(old["predictions"])) as saved:
                np.testing.assert_array_equal(raw, saved["packed"])
            control = "uniform" if plan.get("full_profile", False) else "uniform-fundamental"
            for suffix in ("", "-strict"):
                assert metrics[f"uniform{suffix}"] == old["metrics"][control + suffix]
            references = {a: old["metrics"][a] for a in ("uniform", "exact-fundamental", "broad")}
        prediction = write_array(
            root / f"{panel}-{i}.npz",
            parent=parent,
            target=both,
            packed=raw,
            cfa=colors,
            nominal_support=fields["exact"],
            **{arm: x for (arm, t), x in values[-1].items() if t == setting["threshold"]},
        )
        result.append(
            meta
            | {
                "case": i,
                "profile": profile,
                "CFA": cfa,
                "truth_peak_xy": list(map(int, xy)),
                "selection": traces,
                "previous_metrics": references,
                "metrics": metrics,
                "prediction": prediction,
            }
        )
        print(panel, i, traces[-1], flush=True)
    return result


def nulls(recipe, plan, config, profile, noise, setting):
    result = []
    for row in read_json(checked(plan["null_source"]))["rows"]:
        if row["profile"] != profile:
            continue
        style = row["style"]
        constructor = recipe.construct if style in ("flat", "step", "rail") else fresh_structure
        parent = constructor(style, row["angle_radians"], *row["width_shift_level_height"])
        cfa = np.asarray(PATTERNS[row["CFA"]])
        rng = np.random.default_rng(np.random.SeedSequence(row["noise_seed"]))
        raw = recipe.corrupt(parent, cfa, rng, noise)
        guide = {"active": [True, True], "frequencies_xy": row["guide_frequencies_xy"]}
        images, trace = predict(
            parent,
            raw,
            cfa,
            guide,
            noise,
            recipe.QUERY,
            config,
            setting["threshold"],
            partner_only=plan.get("partner_only", False),
            full_profile=plan.get("full_profile", False),
        )
        metrics = {}
        for (a, t), image in images.items():
            delta = (image[recipe.MEASURE].astype(float) - parent[recipe.MEASURE]) * 65535
            key = a if t == setting["threshold"] else a + "-strict"
            metrics[key] = {
                "RMS_DN16": float(np.sqrt(np.mean(delta**2))),
                "peak_DN16": float(np.max(np.abs(delta))),
                "changed_pixels": int(np.count_nonzero(np.any(delta != 0, axis=0))),
            }
        result.append(
            {k: row[k] for k in ("CFA", "profile", "style", "trial")}
            | {"selection": trace, "metrics": metrics}
        )
        print("null", profile, style, row["trial"], trace["reason"], flush=True)
    return result


def run(path, panel):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    root = Path(plan["root"])
    config = LocalWaveConfig(**plan["config"])
    start = time.monotonic()
    if panel == "camera":
        previous = read_json(checked(plan["camera_plan"]))
        rows = read_json(checked(plan["camera_source"]))["rows"]
        out = root / "camera-arrays"
        out.mkdir()
        value = camera(
            previous,
            rows,
            out,
            config,
            predictor=partial(
                camera_predict,
                partner_only=plan.get("partner_only", False),
                full_profile=plan.get("full_profile", False),
            ),
        )
    else:
        profile = "iso6400" if panel.endswith("6400") else "iso400"
        recipe = structure_module(plan["structure"])
        noise, setting = plan["profiles"][profile], plan["settings"][profile]
        if panel.startswith("null"):
            value = nulls(recipe, plan, config, profile, noise, setting)
        else:
            value = positives(root, recipe, plan, config, profile, panel, noise, setting)
    write_json(
        root / f"{panel}.json",
        {
            "plan": reference(path),
            "producer": reference(__file__),
            "rows": value,
            "CPU_wall_seconds": time.monotonic() - start,
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    actions = cli.add_subparsers(dest="mode", required=True)
    setup = actions.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("envelopes", type=Path)
    setup.add_argument("screened", type=Path)
    setup.add_argument("--partner-only", action="store_true")
    setup.add_argument("--full-profile", action="store_true")
    execute = actions.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("panel", choices=PANELS)
    args = cli.parse_args()
    if args.mode == "prepare":
        prepare(
            args.root.resolve(),
            args.envelopes.resolve(),
            args.screened.resolve(),
            args.partner_only,
            args.full_profile,
        )
    else:
        run(args.plan.resolve(), args.panel)
