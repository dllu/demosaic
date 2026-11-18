"""Compare localized spectral, near and whole-scene rankings on the same RAW windows."""

import argparse
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from probe_affinity_first_fresh import compose, place
from probe_donor_phase_geometry import sensor_box
from probe_fresh_phase_refit import write_array
from probe_localized_donor_refinement import unpack
from probe_localized_donor_support import deliver_options
from probe_scene_context_extent import encode
from probe_screened_scene_donors import crop, offset_box

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.io import read_raw
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.prediction_archive import fingerprint
from demosaic.scene_window_donors import corridor_affinities, rank_scene_windows
from demosaic.screened_scene_donors import donor_affinities, retain_near_preview, screening_preview
from demosaic.search_donor_geometry import candidate_boxes

RANKS = ("window_spectral", "window_near", "window_scene", "window_corridor")


def prepare(root, previous, fresh):
    old_plan = reference(previous / "plan.json")
    previous_result = reference(previous / "output/collection.json")
    fresh_plan = reference(fresh / "plan.json")
    old = read_json(checked(old_plan))
    context = read_json(checked(fresh_plan))
    assert read_json(checked(previous_result))["plan"] == old_plan
    encoder = Path(context["encoder"])
    weights = [reference(encoder / name) for name in ("config.json", "model.safetensors")]
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_scene_wave_guides.py"]
    )
    write_json(
        root / "plan.json",
        old
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "previous": previous_result,
            "inputs": [
                old_plan,
                previous_result,
                fresh_plan,
                old["camera_baseline"],
                old["camera_conditions"],
                *old["photos"].values(),
                *weights,
            ],
            "encoder": str(encoder),
            "encoder_revision": encoder.name,
            "preview": context["preview"],
            "arms": ["parent", "parallel", *RANKS],
            "synthetic_windows": [[128, 32], [192, 64]],
            "camera_windows": [[64, 48], [96, 48], [128, 64]],
            "scope": "Select the top bracket before checking reserved RAW. All rankings share "
            "the same multi-scale window catalog, refined A-only screening, two-edge donor "
            "confirmation and unchanged independent query delivery. The near and full DINO "
            "arms also share their encoder, preview geometry, normalization and exposure. "
            "Pre-existing exact-target observations and both protected GFX scenes are reused.",
        },
    )


def load_encoder(path):
    from transformers import AutoModel

    base = AutoModel.from_pretrained(path, local_files_only=True).eval()
    mean = torch.tensor([0.485, 0.456, 0.406]).reshape(1, 3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).reshape(1, 3, 1, 1)
    return SimpleNamespace(
        base=SimpleNamespace(context=SimpleNamespace(backbone=base, mean=mean, std=std))
    )


def catalog(frames, query, options):
    return sorted(
        {
            box
            for frame in frames
            for size, stride in options
            for box in candidate_boxes(frame, query, size, stride)
        }
    )


def affinities(full, near, boxes, query):
    scene = donor_affinities(full.features, full.grid, boxes, query)
    return {
        "window_spectral": np.ones(len(boxes)),
        "window_near": donor_affinities(near.features, near.grid, boxes, query),
        "window_scene": scene,
        "window_corridor": corridor_affinities(full.features, full.grid, boxes, query, scene),
    }


def synthetic(plan, rows, encoder, config, out):
    query = offset_box(plan["query_xywh"])
    cases = []
    for row in rows:
        case = read_json(checked(row["case"]))
        noise = plan["profiles"][case["profile"]]
        threshold = plan["settings"][case["profile"]]["threshold"]
        views = unpack(row["donors"] + case["donors"][2:])
        boxes = catalog([v[2] for v in views], query, plan["synthetic_windows"])
        packed, colors = sensor_box(case["sensor"], plan["query_xywh"])
        with np.load(checked(case["sensor"])) as obs:
            wb, matrix = obs["wb"], obs["matrix"]
        with np.load(checked(row["prediction"])) as archive:
            predicted = dict(archive)
        raw = compose(case, colors[0], views, noise)
        donors = [(crop(raw, box), colors[0], box) for box in boxes]
        ranks, preview_hashes = [], []
        for obs, color, white, mat in zip(packed, colors, wb, matrix, strict=True):
            place(raw, obs, color, query)
            preview, grid = screening_preview(raw, case["CFA"], white, mat, **plan["preview"])
            full = encode(encoder, preview, grid)
            local = encode(encoder, retain_near_preview(preview, grid, (256, 256, 768, 768)), grid)
            ranks.append(affinities(full, local, boxes, query))
            preview_hashes.append(fingerprint(preview))
        # Spectra need only one computation per donor even when three query roles
        # produce different priors. Held-out donor RAW never sets a ranking.
        fits = rank_scene_windows(
            donors,
            query,
            shot=noise["shot"],
            read=noise["read"],
            affinities={(i, k): value for i, role in enumerate(ranks) for k, value in role.items()},
        )
        by_role = [{k: fits[i, k] for k in RANKS} for i in range(len(ranks))]
        corrections = [
            deliver_options(parent, obs, col, fit, query, noise, config, threshold)
            for parent, obs, col, fit in zip(
                predicted["parent"], packed, colors, by_role, strict=True
            )
        ]
        predicted.update({k: np.stack([v[k] for v in corrections]) for k in RANKS})
        cases.append(
            row
            | {
                "role2_fits": row["role2_fits"] | by_role[2],
                "scene_window_fits": by_role,
                "scene_window_boxes": boxes,
                "preview_hashes": preview_hashes,
                "scene_window_affinities": [
                    {k: values.tolist() for k, values in rank.items()} for rank in ranks
                ],
                "prediction": write_array(out / f"{row['id']}.npz", **predicted),
            }
        )
        print(row["id"], len(boxes), [fit["active"] for fit in by_role[2].values()], flush=True)
    return cases


def camera(plan, rows, encoder, config, out):
    baseline = {r["id"]: r["source"] for r in read_json(checked(plan["camera_baseline"]))["camera"]}
    noise_by_id = {
        r["board"]["id"]: r["noise"]
        for r in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    computed = {}
    for family, binding in plan["photos"].items():
        raw, meta = read_raw(checked(binding))
        preview, grid = screening_preview(
            raw, meta.pattern, meta.white_balance, meta.camera_to_srgb, **plan["preview"]
        )
        full = encode(encoder, preview, grid)
        signature = fingerprint(preview)
        local_by_frame = {}
        for row in rows:
            key = row["id"]
            if not key.startswith(family + "-"):
                continue
            frame, query = tuple(row["frame"]), row["query"]
            noise = noise_by_id[key]
            with np.load(checked(baseline[key]["query_arrays"])) as arrays:
                colors = arrays["colors"][0]
                np.testing.assert_array_equal(arrays["packed"][0], crop(raw, frame))
            if frame not in local_by_frame:
                local_by_frame[frame] = encode(
                    encoder, retain_near_preview(preview, grid, frame), grid
                )
            boxes = catalog((frame,), query, plan["camera_windows"])
            priors = affinities(full, local_by_frame[frame], boxes, query)
            fits = rank_scene_windows(
                [(crop(raw, b), colors, b) for b in boxes],
                query,
                shot=noise["shot"],
                read=noise["read"],
                affinities=priors,
            )
            with np.load(checked(row["predictions"])) as f:
                predicted = dict(f)
            predicted.update(
                deliver_options(
                    predicted["parent"],
                    crop(raw, query),
                    colors,
                    fits,
                    query,
                    noise,
                    config,
                    2,
                    edge=True,
                )
            )
            computed[key] = row | {
                "fits": row["fits"] | fits,
                "scene_window_boxes": boxes,
                "scene_window_affinities": {k: values.tolist() for k, values in priors.items()},
                "preview": signature,
                "preview_hw": grid.preview_hw,
                "predictions": write_array(out / f"{key}.npz", **predicted),
            }
            print(key, len(boxes), [fit["active"] for fit in fits.values()], flush=True)
    return [computed[r["id"]] for r in rows]


@torch.inference_mode()
def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    start = time.monotonic()
    encoder = load_encoder(plan["encoder"])
    previous = read_json(checked(plan["previous"]))
    cfg = LocalWaveConfig(**plan["config"])
    out = Path(plan["root"]) / "output"
    out.mkdir()
    cases = synthetic(plan, previous["synthetic"], encoder, cfg, out)
    cameras = camera(plan, previous["camera"], encoder, cfg, out)
    assert len(cases) == 16 and len(cameras) == 8
    write_json(
        out / "collection.json",
        {
            "plan": reference(path),
            "seconds": time.monotonic() - start,
            "restoration_calls": 0,
            "synthetic": cases,
            "camera": cameras,
        },
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cmds = cli.add_subparsers(dest="command", required=True)
    setup = cmds.add_parser("prepare")
    setup.add_argument("root", type=Path)
    setup.add_argument("previous", type=Path)
    setup.add_argument("fresh", type=Path)
    run = cmds.add_parser("collect")
    run.add_argument("plan", type=Path)
    args = cli.parse_args()
    if args.command == "prepare":
        prepare(args.root.resolve(), args.previous.resolve(), args.fresh.resolve())
    else:
        collect(args.plan.resolve())
