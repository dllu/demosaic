"""Compare whole donor patches with reserved-sample confirmation on local islands."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_affinity_first_donors import same_geometry
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_screened_scene_donors import offset_box
from probe_search_donor_geometry import deliver
from report_fold_support_pooling import ROI

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.data.edge_response import edge_observation
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.localized_donor_geometry import localize_donor_geometry
from demosaic.search_donor_geometry import screening_mask, search_donor_geometry

ARMS = ("parent", "whole", "local", "unequal")


def prepare(root, fresh, real):
    refs = [
        reference(rev / p) for rev in (fresh, real) for p in ("plan.json", "output/collection.json")
    ]
    fresh_plan, real_plan = read_json(checked(refs[0])), read_json(checked(refs[2]))
    assert read_json(checked(refs[1]))["plan"] == refs[0]
    assert read_json(checked(refs[3]))["plan"] == refs[2]
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(),
        root,
        [Path(__file__).name, "report_scene_wave_guides.py", "report_phase_drift.py"],
    )
    write_json(
        root / "plan.json",
        {
            **{
                k: fresh_plan[k]
                for k in ("settings", "profiles", "query_xywh", "parent_checkpoint", "config")
            },
            **{k: real_plan[k] for k in ("camera_baseline", "camera_conditions", "photos")},
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": hashes,
            "inputs": [*refs, real_plan["camera_baseline"], real_plan["camera_conditions"]],
            "fresh": refs[1],
            "camera": refs[3],
            "arms": ARMS,
            "occlusion": {
                "native_square": 128,
                "offsets": [[32, 64], [64, 32], [96, 64], [64, 96]],
                "second_donor_offset": "reflected inside the 256-pixel donor",
                "outside": "existing independently corrupted rotated-wire alternate",
            },
            "edge_controls": {"sources": [88, 92], "donor_repeats": [10167, 10168]},
            "scope": "Camera donor boxes are fixed from the appearance-first run. For exact-target "
            "simulations, fix the intended pair and replace the outer three quarters of each donor with "
            "the archived incompatible material. Both policies see exactly the same occlusion. Test "
            "partial support with or without a weaker opposite screening peak, maintaining independent "
            "donor and query confirmation. All three policies use the same neural parent fallback.",
        },
    )


def fit_options(views, query, noise):
    if not views:
        return {arm: {"status": "no bracket", "active": [False, False]} for arm in ARMS[1:]}
    args = {"shot": noise["shot"], "read": noise["read"]}
    return {
        "whole": search_donor_geometry(views, query, **args),
        "local": localize_donor_geometry(views, query, **args),
        "unequal": localize_donor_geometry(views, query, unequal=True, **args),
    }


def deliver_options(parent, packed, colors, fit, query, noise, config, threshold, edge=False):
    eligible = ~screening_mask(query)
    results = {"parent": parent}
    for arm, proposed in fit.items():
        equivalent = next(
            (other for other in results if other in fit and same_geometry(fit[other], proposed)),
            None,
        )
        if not any(proposed["active"]):
            results[arm] = parent
        elif equivalent is not None:
            results[arm] = results[equivalent]
        else:
            results[arm] = deliver(
                parent,
                packed,
                colors,
                proposed,
                noise,
                config,
                (threshold,),
                edge,
                False,
                evidence_mask=eligible,
            )[threshold]
    return results


def read_donors(case, spec, out):
    donors = case["donors"]
    width = spec["native_square"]
    x, y = spec["offsets"][(case["source"] - 88) % len(spec["offsets"])]
    rows, views = [], []
    for i, (a, b) in enumerate(zip(donors[:2], donors[2:], strict=True)):
        with np.load(checked(a["raw"])) as f, np.load(checked(b["raw"])) as g:
            clean, background = f["packed"], g["packed"].copy()
            colors = f["colors"]
            np.testing.assert_array_equal(colors, g["colors"])
        np.testing.assert_equal(background.shape, (4, 128, 128))
        px, py = (x, y) if i == 0 else (256 - width - x, 256 - width - y)
        sl = np.s_[..., py // 2 : (py + width) // 2, px // 2 : (px + width) // 2]
        background[sl] = clean[sl]
        pixels = write_array(
            out / f"{case['id']}-occlusion{i}.npz", packed=background, colors=colors
        )
        rows.append(
            {
                "source": a["raw"],
                "occluder": b["raw"],
                "raw": pixels,
                "box": a["box"],
                "remaining_surface_xywh": [px, py, width, width],
            }
        )
        views.append((background, colors, a["box"]))
    return rows, views


def edge_control(case, plan, query, noise, out):
    donors = []
    references = []
    for i, (row, repeat) in enumerate(
        zip(case["donors"][:2], plan["edge_controls"]["donor_repeats"], strict=True)
    ):
        recipe = case["metadata"]["recipe"] | {
            "size": 256,
            "level": 0.16,
            "bright_level": 0.30,
            "amplitude": 0.0,
            "mask_radii": [116.0, 116.0],
            "edge_jitter": 3.5 if i == 0 else -4.0,
        }
        sampled, meta = edge_observation(recipe, "near", case["CFA"], repeat, condition=noise)
        raw, colors = sampled["packed"][0], sampled["colors"][0]
        donors.append((raw, colors, row["box"]))
        references.append(
            {
                "box": row["box"],
                "identity": meta["identities"][0],
                "raw": write_array(out / f"{case['id']}-null{i}.npz", packed=raw, colors=colors),
            }
        )
    return {"inputs": references, "fits": fit_options(donors, query, noise)}


def synthetic(plan, source, cfg, output):
    query = offset_box(plan["query_xywh"])
    rows = []
    for b in source["cases"]:
        case = read_json(checked(b))
        noise = plan["profiles"][case["profile"]]
        t = plan["settings"][case["profile"]]["threshold"]
        donors, views = read_donors(case, plan["occlusion"], output)
        fits = fit_options(views, query, noise)
        with np.load(checked(case["parent"])) as p:
            parent = p["parent"][ROI]
        packed, colors = sensor_box(case["sensor"], plan["query_xywh"])
        values = [
            deliver_options(x, y, cs, fits, query, noise, cfg, t)
            for x, y, cs in zip(parent, packed, colors, strict=True)
        ]
        pred = write_array(
            output / f"{case['id']}.npz",
            **{key: np.stack([entry[key] for entry in values]) for key in ARMS},
        )
        controls = (
            edge_control(case, plan, query, noise, output)
            if case["source"] in plan["edge_controls"]["sources"]
            else None
        )
        rows.append(
            {
                "id": case["id"],
                "case": b,
                "donors": donors,
                "prediction": pred,
                "fits": fits,
                "edge_control": controls,
            }
        )
        print(case["id"], [f["active"] for f in fits.values()], flush=True)
    return rows


def camera(plan, source, cfg, output):
    baseline = read_json(checked(plan["camera_baseline"]))["camera"]
    noise_by_key = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    cases = []
    for old, row in zip(source["camera"], baseline, strict=True):
        key, original = row["id"], row["source"]
        assert key == old["id"]
        ox, oy, *_ = old["frame"]
        x, y, w, h = original["query_box"]
        query = original["absolute_query_xywh"]
        noise = noise_by_key[key]
        with np.load(checked(original["query_arrays"])) as f:
            packed, colors = f["packed"][0], f["colors"][0]
        views = [
            (
                packed[:, (b - oy) // 2 : (b - oy + d) // 2, (a - ox) // 2 : (a - ox + c) // 2],
                colors,
                (a, b, c, d),
            )
            for a, b, c, d in old["fits"]["scene"].get("donor_boxes", [])
        ]
        fits = fit_options(views, query, noise)
        parent = np.load(checked(original["parent_prediction"]), mmap_mode="r")[
            0, :, y : y + h, x : x + w
        ]
        values = deliver_options(
            parent,
            packed[:, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2],
            colors,
            fits,
            query,
            noise,
            cfg,
            2.0,
            edge=True,
        )
        receipt = write_array(output / f"{key}.npz", **values)
        cases.append(
            {
                "id": key,
                "query": query,
                "fits": fits,
                "predictions": receipt,
                "appearance_first": old["predictions"]["scene"],
                "frame": old["frame"],
            }
        )
        print(key, [f["active"] for f in fits.values()], flush=True)
    return cases


def collect(path):
    import torch

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    cfg = LocalWaveConfig(**plan["config"])
    start = time.monotonic()
    out = Path(plan["root"]) / "output"
    out.mkdir()
    real = camera(plan, read_json(checked(plan["camera"])), cfg, out)
    simulated = synthetic(plan, read_json(checked(plan["fresh"])), cfg, out)
    assert len(real) == 8 and len(simulated) == 16
    write_json(
        out / "collection.json",
        {
            "plan": reference(path),
            "camera": real,
            "synthetic": simulated,
            "seconds": time.monotonic() - start,
            "neural_calls": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path, nargs=2)
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), *(p.resolve() for p in args.prepare_from))
    else:
        collect(args.path.resolve())
