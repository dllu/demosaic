"""Replay a scene-affinity frequency shortlist and independent RAW query selection."""

import argparse
import time
from dataclasses import replace
from pathlib import Path

import numpy as np
from probe_affinity_first_fresh import compose
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_local_phase_bounds import fresh_structure, structure_module
from probe_localized_donor_refinement import unpack
from probe_scene_wire_footprint import STAGES
from probe_screened_scene_donors import crop, offset_box
from probe_surface_aggregation import field

from demosaic.cfa import PATTERNS
from demosaic.donor_frequency_bank import (
    AFFINITY_MARGIN,
    BANK_SIZE,
    QUERY_GAIN,
    active_anchor,
    donor_frequency_bank,
    screened_donor_tiles,
    select_bank_companion,
)
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

NULL_STAGES = ("null-iso400", "null-iso6400")


def prepare(root, screened, windows, disjoint):
    old = reference(screened / "plan.json")
    plan = read_json(checked(old))
    windows_path = reference(windows / "output/collection.json")
    disjoint_path = reference(disjoint / "plan.json")
    disjoint_plan = read_json(checked(disjoint_path))
    originals = {
        panel: reference(screened / f"{panel}.json")
        for panel in ("synthetic", "disjoint", "camera", "replication")
    }
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
                old,
                windows_path,
                disjoint_path,
                disjoint_plan["previous_plan"],
                *originals.values(),
                *plan["inputs"],
                plan["previous"],
                plan["structure"],
            ],
            "screened_source": originals,
            "local_windows": windows_path,
            "macro_layout": disjoint_plan["previous_plan"],
            "macro_decoy_boxes": disjoint_plan["synthetic_appearance_stress"]["decoy_boxes"],
            "bank": {
                "max_candidates": BANK_SIZE,
                "affinity_margin": AFFINITY_MARGIN,
                "minimum_query_gain": QUERY_GAIN,
                "deduplication_native_bins": 1,
            },
            "forced_bank_offsets_degrees": [25, -27, 43, -46, 69, -71, 90],
            "scope": "Preserve the baseline's first admitted carrier. Keep up to eight companion "
            "frequencies from the original scene-affinity windows. Confirm each on separately "
            "withheld donor RAW, and select on the query screening reserve only. Return the "
            "unchanged baseline if there is no measured anchor or if no candidate beats both "
            "the anchor-only null and the baseline companion in both reserve folds. "
            "Keep the original eight-knot delivery and independent per-color validation.",
        },
    )


def options(
    parent,
    raw,
    colors,
    guide,
    query,
    noise,
    cfg,
    threshold,
    old,
    tiles,
    affinities,
    *,
    localized,
    camera=False,
):
    anchor = active_anchor(guide)
    carrier = None if anchor is None else np.asarray(guide["frequencies_xy"][anchor])
    bank = donor_frequency_bank(
        tiles,
        query,
        affinities,
        carrier,
        shot=noise["shot"],
        read=noise["read"],
        localized=localized,
        family_degrees=cfg.family_degrees,
    )
    return apply_bank(
        parent, raw, colors, guide, query, noise, cfg, threshold, old, bank, camera=camera
    )


def eight_refit(parent, raw, colors, guide, query, noise, cfg, threshold, *, camera=False):
    out, _ = restore_local_waves(
        parent,
        raw,
        colors,
        **noise_kwargs(noise),
        config=cfg,
        thresholds=(threshold, threshold + 1),
        evidence_mask=~screening_mask(query),
        guide_frequencies_xy=guide["frequencies_xy"],
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        phase_edge_side="validation" if camera else None,
        active_guide_directions=guide["active"],
    )
    return {o: out["weighted-refit", threshold + o] for o in (0, 1)}


def apply_bank(
    parent, raw, colors, guide, query, noise, cfg, threshold, old, bank, *, camera=False
):
    selected, trace = select_bank_companion(
        raw, colors, query, guide, bank, shot=noise["shot"], read=noise["read"], config=cfg
    )
    fits = old
    if trace["status"] == "selected":
        fits = eight_refit(
            parent, raw, colors, selected, query, noise, cfg, threshold, camera=camera
        )
    return fits, {
        "bank": bank,
        "anchor_index": active_anchor(guide),
        "query_selection": trace,
        "final_guide": selected,
    }


def alternate_admissions(guide, trace):
    """Use the same bank and scores to compare donor-only and positive reserve gates."""
    if "gains" not in trace:
        return {"donor": guide, "positive": guide}
    index = 1 - active_anchor(guide)
    candidates = trace["candidate_frequencies_xy"]

    def replace_partner(frequency):
        frequencies = list(guide["frequencies_xy"])
        frequencies[index] = frequency
        return guide | {"frequencies_xy": frequencies, "active": [True, True]}

    i = trace["best"]
    scores = np.asarray(trace["gains"])
    return {
        "donor": replace_partner(candidates[0]),
        "positive": replace_partner(candidates[i]) if scores[:, i].min() > 0 else guide,
    }


def local_views(row, case, scene, query, colors, noise):
    views = unpack(scene["donors"] + case["donors"][2:])
    canvas = compose(case, colors, views, noise)
    assert row["query"] == list(query)
    return [(crop(canvas, b), colors, b) for b in scene["scene_window_boxes"]]


def macro_views(plan, case):
    layout = read_json(checked(plan["macro_layout"]))
    boxes = (layout["left_xywh"], layout["right_xywh"], *plan["macro_decoy_boxes"])
    views = []
    for old, b in zip(case["decoys"], boxes, strict=True):
        with np.load(checked(old["raw"])) as f:
            views.append((f["packed"], f["colors"], offset_box(b)))
    return views


def synthetic(plan, cfg, label, profile, output):
    windows = {r["id"]: r for r in read_json(checked(plan["local_windows"]))["synthetic"]}
    local = label == "synthetic"
    component = "original_guides" if local else "disjoint_guides"
    guides = {r["id"]: r for r in read_json(checked(plan["source"][component]))["synthetic"]}
    rows = read_json(checked(plan["screened_source"][label]))["rows"]
    noise, threshold = plan["profiles"][profile], plan["settings"][profile]["threshold"]
    query = offset_box(plan["query_xywh"])
    output_rows = []
    for row in rows:
        key = row["id"]
        if not key.startswith(profile + "-"):
            continue
        earlier = guides[key]
        case = read_json(checked(row["case"]))
        values, colors = sensor_box(case["sensor"], plan["query_xywh"])
        if local:
            geom = windows[key]
            views = local_views(earlier, case, geom, query, colors[0], noise)
            weights = [r["window_scene"] for r in geom["scene_window_affinities"]]
            seen = earlier["roles"]
        else:
            views = macro_views(plan, earlier)
            seen = earlier["rankings"]
            weights = [r["affinities"]["scene"] for r in seen]
        tiles = screened_donor_tiles(views, query, **noise_kwargs(noise), localized=local)
        with np.load(checked(row["prediction"])) as f:
            baseline = dict(f)
        control = {o: baseline[field("scene", "screened", o)] for o in (0, 1)}
        decisions, pictures = [], []
        for i, (raw, layout, witness, affinity) in enumerate(
            zip(values, colors, seen, weights, strict=True)
        ):
            fits, outcome = options(
                baseline["parent"][i],
                raw,
                layout,
                witness["fits"]["scene"],
                query,
                noise,
                cfg,
                threshold,
                {o: x[i] for o, x in control.items()},
                tiles,
                affinity,
                localized=local,
            )
            decisions.append(outcome)
            pictures.append(fits)
        arrays = baseline | {
            field("scene", "bank", o): np.stack([d[o] for d in pictures]) for o in (0, 1)
        }
        output_rows.append(
            row
            | {
                "before": row["prediction"],
                "bank_records": decisions,
                "prediction": write_array(output / f"{key}.npz", **arrays),
            }
        )
        print(label, key, [r["query_selection"]["status"] for r in decisions], flush=True)
    assert len(output_rows) == 8
    return output_rows


def noise_kwargs(noise):
    return {k: noise[k] for k in ("shot", "read")}


def local_slice(packed, native, origin):
    x, y, w, h = native
    dx, dy = x - origin[0], y - origin[1]
    assert (
        min(dx, dy) >= 0 and (dx + w) // 2 <= packed.shape[-1] and (dy + h) // 2 <= packed.shape[-2]
    )
    return packed[:, dy // 2 : (dy + h) // 2, dx // 2 : (dx + w) // 2]


def camera(plan, cfg, output):
    source = read_json(checked(plan["camera_baseline"]))["camera"]
    previous = read_json(checked(plan["screened_source"]["camera"]))["rows"]
    original = read_json(checked(plan["previous"]))["camera"]
    scenes = read_json(checked(plan["local_windows"]))["camera"]
    noise_by_id = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    rows = []
    for original_row, row, base, scene in zip(original, previous, source, scenes, strict=True):
        key, info = base["id"], base["source"]
        assert key == row["id"] == original_row["id"] == scene["id"]
        query, origin = scene["query"], scene["frame"]
        assert info["absolute_query_xywh"] == query
        noise = noise_by_id[key]
        with np.load(checked(info["query_arrays"])) as f:
            packed, colors = f["packed"][0], f["colors"][0]
        raw = local_slice(packed, query, origin)
        views = [(local_slice(packed, b, origin), colors, b) for b in scene["scene_window_boxes"]]
        tiles = screened_donor_tiles(views, query, **noise_kwargs(noise), localized=True)
        with np.load(checked(row["predictions"])) as f:
            variants = dict(f)
        receipts = {}
        for g, label in (("scene", "window_scene"), ("spectral", "window_spectral")):
            pred, trace = options(
                variants["parent"],
                raw,
                colors,
                original_row["fits"][g],
                query,
                noise,
                cfg,
                2,
                {o: variants[field(g, "screened", o)] for o in (0, 1)},
                tiles,
                scene["scene_window_affinities"][label],
                localized=True,
                camera=True,
            )
            receipts[g] = trace
            variants.update({field(g, "bank", o): x for o, x in pred.items()})
        rows.append(
            row
            | {
                "before": row["predictions"],
                "bank_records": receipts,
                "predictions": write_array(output / f"{key}.npz", **variants),
            }
        )
        print(
            "camera", key, [r["query_selection"]["status"] for r in receipts.values()], flush=True
        )
    assert len(rows) == 8
    return rows


def run(path, stage):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    root = Path(plan["root"])
    output = root / f"arrays-{stage}"
    output.mkdir()
    cfg = replace(LocalWaveConfig(**plan["config"]), background="screened_curved4_step")
    start = time.monotonic()
    if stage == "camera":
        rows = camera(plan, cfg, output)
    elif stage in NULL_STAGES:
        rows = rail_controls(plan, cfg, stage.split("-")[1])
    else:
        rows = synthetic(plan, cfg, *stage.split("-"), output)
    write_json(
        root / f"{stage}.json",
        {
            "plan": reference(path),
            "rows": rows,
            "producer": reference(__file__),
            "CPU_wall_seconds": time.monotonic() - start,
        },
    )


def rail_controls(plan, cfg, profile):
    source = read_json(checked(plan["screened_source"]["replication"]))["rows"]
    recipe = structure_module(plan["structure"])
    noise, threshold = plan["profiles"][profile], plan["settings"][profile]["threshold"]
    rows = []
    for old in source:
        if old["profile"] != profile:
            continue
        style = old["style"]
        ctor = recipe.construct if style in ("flat", "step", "rail") else fresh_structure
        parent = ctor(style, old["angle_radians"], *old["width_shift_level_height"])
        colors = np.asarray(PATTERNS[old["CFA"]])
        gen = np.random.default_rng(np.random.SeedSequence(old["noise_seed"]))
        packed = recipe.corrupt(parent, colors, gen, noise)
        frequencies = old["guide_frequencies_xy"]
        angle = np.arctan2(frequencies[0][1], frequencies[0][0])
        phi = angle + np.deg2rad(plan["forced_bank_offsets_degrees"])
        directions = np.column_stack((np.cos(phi), np.sin(phi))) * np.linalg.norm(frequencies[0])
        bank = {
            "shortlist": [{"frequency_xy": f.tolist(), "donor_valid": True} for f in directions]
        }
        guide = {"frequencies_xy": frequencies, "active": [True, True]}
        control = eight_refit(parent, packed, colors, guide, recipe.QUERY, noise, cfg, threshold)
        result, trace = apply_bank(
            parent, packed, colors, guide, recipe.QUERY, noise, cfg, threshold, control, bank
        )
        metrics = {}
        routes = {"screened": control, "bank": result}
        guide_map = alternate_admissions(guide, trace["query_selection"])
        for arm, candidate in guide_map.items():
            if candidate == guide:
                routes[arm] = control
            elif candidate == trace["final_guide"]:
                routes[arm] = result
            else:
                routes[arm] = eight_refit(
                    parent, packed, colors, candidate, recipe.QUERY, noise, cfg, threshold
                )
        for name, preds in routes.items():
            for o, image in preds.items():
                err = (image[recipe.MEASURE].astype(float) - parent[recipe.MEASURE]) * 65535
                metrics[field("null", name, o)] = {
                    "RMS_DN16": float(np.sqrt(np.mean(err**2))),
                    "max_abs_DN16": float(np.max(np.abs(err))),
                    "changed_pixels": int(np.count_nonzero(np.any(err != 0, axis=0))),
                }
                if name == "screened":
                    assert metrics[field("null", name, o)] == old["metrics"][field("null", name, o)]
        rows.append(
            {
                "profile": profile,
                "style": style,
                "trial": old["trial"],
                "metrics": metrics,
                "trace": trace,
                "alternates": guide_map,
            }
        )
        print("null", profile, style, old["trial"], trace["query_selection"]["status"], flush=True)
    assert len(rows) == 24
    return rows


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    actions = p.add_subparsers(dest="action", required=True)
    prep = actions.add_parser("prepare")
    for name in ("root", "screened", "windows", "disjoint"):
        prep.add_argument(name, type=Path)
    execute = actions.add_parser("run")
    execute.add_argument("plan", type=Path)
    execute.add_argument("stage", choices=(*STAGES, *NULL_STAGES))
    args = p.parse_args()
    if args.action == "prepare":
        prepare(*(getattr(args, k).resolve() for k in ("root", "screened", "windows", "disjoint")))
    else:
        run(args.plan.resolve(), args.stage)
