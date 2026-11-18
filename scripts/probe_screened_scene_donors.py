"""Rank RAW donors with full or spatially restricted A-only scene features."""

import argparse
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from probe_donor_phase_geometry import report, sensor_box
from probe_fresh_phase_refit import write_array
from probe_scene_context_extent import encode
from probe_search_donor_geometry import deliver
from report_fold_support_pooling import ROI

from demosaic.cfa import PATTERNS
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.data.edge_response import edge_observation, render_scene
from demosaic.io import read_raw
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.prediction_archive import fingerprint
from demosaic.screened_scene_donors import donor_affinities, retain_near_preview, screening_preview
from demosaic.search_donor_geometry import (
    _native,
    candidate_boxes,
    screening_mask,
    search_donor_geometry,
)
from demosaic.suite import observation

ARMS = ("guarded", "planar", "near", "scene")
RANKS = ARMS[1:]
TILE_SIZE = 128
STRIDE = 64
SCENE_SIZE = 1280
OFFSET = 384


def prepare(root, previous, model_cache):
    source_plan = reference(previous / "plan.json")
    source_results = reference(previous / "output/collection.json")
    old = read_json(checked(source_plan))
    assert read_json(checked(source_results))["plan"] == source_plan
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    architecture = read_json("configs/current-model.json")["architecture"]
    encoder = model_cache / architecture["dino_revision"]
    photos = {
        "main": reference(read_json("configs/gfx-qualitative-20231231.json")["noisy"]),
        "mesh": reference(
            read_json("configs/gfx-green-mesh-20231231.json")["sources"]["noisy"]["path"]
        ),
    }
    weights = [reference(encoder / k) for k in ("config.json", "model.safetensors")]
    write_json(
        root / "plan.json",
        {
            **{
                k: old[k]
                for k in (
                    "camera_baseline",
                    "camera_conditions",
                    "parent_checkpoint",
                    "config",
                    "profiles",
                    "settings",
                    "query_xywh",
                    "previous_plan",
                    "previous_collection",
                )
            },
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [
                source_plan,
                source_results,
                old["camera_baseline"],
                old["camera_conditions"],
                *photos.values(),
                *weights,
            ],
            "base_plan": source_plan,
            "base_collection": source_results,
            "photos": photos,
            "encoder": str(encoder),
            "encoder_revision": architecture["dino_revision"],
            "arms": ARMS,
            "rendering": {
                "labels": ["Guarded guide", "Spectral rank", "Near context", "Scene context"],
                "sources": [81, 85],
                "camera_label": "Scene rank",
                "contrast": 5,
            },
            "preview": {"long_side": 1536, "exposure": 4.0},
            "synthetic_appearance_stress": {
                "frame": [0, 0, SCENE_SIZE, SCENE_SIZE],
                "xy_offset": [OFFSET, OFFSET],
                "alternate_angles_degrees": 40,
                "alternate_amplitude": 0.083,
                "alternate_level": 0.18,
                "alternate_bright_level": 0.32,
                "alternate_rgb_scale": [1.45, 1.0, 0.60],
                "decoy_boxes": [[128, -128, 256, 256], [128, 384, 256, 256]],
                "decoy_repeats": [8410, 8411],
                "matched_repeats": [8406, 8407],
                "background_noise_seed": 8451,
            },
            "scope": "Match the planar-only RAW screen across spectral, spatially restricted DINO and full-scene DINO rankings. "
            "Pick one pair before the reserved donor folds. All three ranks also exclude the same preview sites from query fitting and scores. "
            "Full and near previews share the same coordinates, normalization and retained "
            "footprint. The complete camera preview is built from a single cached original and uses only fixed screening samples. "
            "Synthetic composites reuse exact query RAW and regenerate intended donors in its CFA layout. Two rotated wire patches on another "
            "painted surface form a competing pair. Render each noisy query role independently, with the same candidate donor RAW.",
        },
    )


def crop(raw, box):
    x, y, w, h = box
    region = raw[y : y + h, x : x + w]
    return region.reshape(h // 2, 2, w // 2, 2).transpose(1, 3, 0, 2).reshape(4, h // 2, w // 2)


def offset_box(box):
    return (box[0] + OFFSET, box[1] + OFFSET, *box[2:])


def context_ranks(near, full, boxes, query):
    return {
        "near": donor_affinities(near.features, near.grid, boxes, query),
        "scene": donor_affinities(full.features, full.grid, boxes, query),
    }


def fit_ranks(views, query, noise, affinities):
    return {
        arm: search_donor_geometry(
            views, query, shot=noise["shot"], read=noise["read"], donor_affinity=affinities.get(arm)
        )
        for arm in RANKS
    }


def camera_replays(plan, baseline, model, cfg, output):
    rows = read_json(checked(plan["camera_baseline"]))["camera"]
    conditions = {
        entry["board"]["id"]: entry["noise"]
        for entry in read_json(checked(plan["camera_conditions"]))["camera"]
    }
    records = {}
    for family, binding in plan["photos"].items():
        full, meta = read_raw(checked(binding))
        preview, grid = screening_preview(
            full, meta.pattern, meta.white_balance, meta.camera_to_srgb, **plan["preview"]
        )
        signature = fingerprint(preview)
        full_features = encode(model, preview, grid)
        near_features = {}
        for row in rows:
            key, scene = row["id"], row["source"]
            if not key.startswith(family + "-"):
                continue
            noise = conditions[key]
            x, y, w, h = scene["query_box"]
            query = scene["absolute_query_xywh"]
            frame = tuple(next(item["frame"] for item in baseline["camera"] if item["id"] == key))
            with np.load(checked(scene["query_arrays"])) as data:
                np.testing.assert_array_equal(data["packed"][0], crop(full, frame))
                colors = data["colors"][0]
                assert tuple(colors) == PATTERNS[meta.pattern]
            boxes = candidate_boxes(frame, query, TILE_SIZE, STRIDE)
            views = [(crop(full, box), colors, box) for box in boxes]
            if frame not in near_features:
                near_features[frame] = encode(
                    model, retain_near_preview(preview, grid, frame), grid
                )
            affinities = context_ranks(near_features[frame], full_features, boxes, query)
            fits = fit_ranks(views, query, noise, affinities)
            px = np.load(checked(scene["parent_prediction"]), mmap_mode="r")[
                0, :, y : y + h, x : x + w
            ]
            packed = crop(full, query)
            predictions = {}
            for arm, fit in fits.items():
                prediction = row["crosscheck_prediction"]
                if any(fit["active"]):
                    values = deliver(
                        px,
                        packed,
                        colors,
                        fit,
                        noise,
                        cfg,
                        (2.0,),
                        True,
                        False,
                        evidence_mask=~screening_mask(query),
                    )
                    prediction = write_array(output / f"{key}-{arm}.npz", corrected=values[2.0])
                predictions[arm] = prediction
            records[key] = {
                "id": key,
                "fit": fits["scene"],
                "prediction": predictions["scene"],
                "fits": fits,
                "predictions": predictions,
                "frame": frame,
                "preview_fingerprint": signature,
                "native_hw": grid.native_hw,
                "preview_hw": grid.preview_hw,
                "candidate_boxes": boxes,
                "affinities": {arm: values.tolist() for arm, values in affinities.items()},
            }
            print(key, [f["active"] for f in fits.values()], flush=True)
    return [records[row["id"]] for row in rows]


def alternate_raw(case, wb, matrix, noise, spec, repeat):
    recipe = case["metadata"]["recipe"]
    turn = np.deg2rad(spec["alternate_angles_degrees"])
    recipe = recipe | {
        "size": 256,
        "level": spec["alternate_level"],
        "bright_level": spec["alternate_bright_level"],
        "edge_jitter": 0.0,
        "amplitude": spec["alternate_amplitude"],
        "weak_fraction": 1.0,
        "mask_radii": [116.0, 116.0],
        "phase_drifts": [[0, 0], [0, 0]],
        "phase_position_offset_xy": [-128, 0],
        "phase_reference_size": 512,
        "wire_angles": [float(a + turn) for a in recipe["wire_angles"]],
    }
    rgb, _, _ = render_scene(recipe, "far")
    rgb *= torch.tensor(spec["alternate_rgb_scale"])[None, :, None, None]
    name = f"scene-donor-decoy:{case['source']}:{repeat}"
    sampled = observation(
        rgb[-1:], [name], noise, case["CFA"], wb.tolist(), matrix.tolist(), 20261117
    )
    return sampled["packed"][0].numpy(), name


def composite_inputs(plan, record, case, noise, previous, old, output):
    spec = plan["synthetic_appearance_stress"]
    with np.load(checked(case["sensor"])) as f:
        colors, wb, matrix = f["colors"][2], f["wb"][2], f["matrix"][2]
    views, declarations = [], []
    guide = previous["donors"][record["guide_key"]]
    for side, repeat in zip(("left", "right"), spec["matched_repeats"], strict=True):
        recipe = guide[f"{side}_declaration"]["recipe"]
        data, meta = edge_observation(recipe, "far", case["CFA"], repeat, condition=noise)
        np.testing.assert_array_equal(data["colors"][2], colors)
        pixels = data["packed"][2]
        views.append((pixels, colors, offset_box(old[f"{side}_xywh"])))
        declarations.append(
            {
                "identity": meta["identities"][2],
                "raw": write_array(
                    output / f"{case['id']}-{repeat}.npz", packed=pixels, colors=colors
                ),
            }
        )
    for native_box, repeat in zip(spec["decoy_boxes"], spec["decoy_repeats"], strict=True):
        alt, name = alternate_raw(case, wb, matrix, noise, spec, repeat)
        declarations.append(
            {
                "identity": name,
                "raw": write_array(
                    output / f"{case['id']}-{repeat}.npz", packed=alt, colors=colors
                ),
            }
        )
        views.append((alt, colors, offset_box(native_box)))
    yy, xx = np.ogrid[:SCENE_SIZE, :SCENE_SIZE]
    layout = colors.reshape(2, 2)[yy % 2, xx % 2]
    strip = np.abs(yy - (SCENE_SIZE // 2 + 0.05 * (xx - SCENE_SIZE // 2))) < 156
    base = np.where(
        strip, np.asarray([0.07, 0.11, 0.075])[layout], np.asarray([0.17, 0.15, 0.065])[layout]
    )
    rng = np.random.default_rng(spec["background_noise_seed"] + case["source"])
    canvas = (
        base + rng.normal(size=base.shape) * np.sqrt(noise["read"] + noise["shot"] * base)
    ).astype(np.float32)
    for packed, cs, box in views:
        x, y, w, h = box
        canvas[y : y + h, x : x + w] = _native(packed, cs, box)[0]
    return views, canvas, wb, matrix, declarations


def synthetic_replays(plan, earlier, model, cfg, output):
    prior = read_json(checked(plan["previous_collection"]))
    old = read_json(checked(plan["previous_plan"]))
    result = []
    query = offset_box(plan["query_xywh"])
    x, y, w, h = query
    near_frame = (256, 256, 768, 768)
    for row in earlier["synthetic"]:
        case = read_json(checked(row["case"]))
        noise = plan["profiles"][case["profile"]]
        packed, colors = sensor_box(case["sensor"], plan["query_xywh"])
        parent = np.load(checked(case["parent"]), mmap_mode="r")[ROI]
        views, canvas, wb, matrix, decoys = composite_inputs(
            plan, row, case, noise, prior, old, output
        )
        thresholds = sorted(
            {
                s["threshold"]
                for s in plan["settings"]
                if (s["profile"], s["placement"]) == (case["profile"], case["placement"])
            }
        )
        with np.load(checked(row["prediction"])) as f:
            pred = {f"guarded--t{t:g}": f[f"guarded--t{t:g}"] for t in thresholds}
        rows = []
        for role, (image, values, cs) in enumerate(zip(parent, packed, colors, strict=True)):
            canvas[y : y + h, x : x + w] = _native(values, cs, query)[0]
            preview, grid = screening_preview(canvas, case["CFA"], wb, matrix, **plan["preview"])
            full = encode(model, preview, grid)
            near = encode(model, retain_near_preview(preview, grid, near_frame), grid)
            affinities = context_ranks(near, full, [view[2] for view in views], query)
            fits = fit_ranks(views, query, noise, affinities)
            for arm, fit in fits.items():
                if any(fit["active"]):
                    pixels = deliver(
                        image,
                        values,
                        cs,
                        fit,
                        noise,
                        cfg,
                        thresholds,
                        case["placement"] == "near",
                        False,
                        evidence_mask=~screening_mask(query),
                    )
                else:
                    pixels = {t: pred[f"guarded--t{t:g}"][role] for t in thresholds}
                for t in thresholds:
                    pred.setdefault(f"{arm}--t{t:g}", []).append(pixels[t])
            rows.append(
                {
                    "preview": fingerprint(preview),
                    "fits": fits,
                    "affinities": {arm: a.tolist() for arm, a in affinities.items()},
                }
            )
        result.append(
            {
                "id": case["id"],
                "case": row["case"],
                "decoys": decoys,
                "rankings": rows,
                "prediction": write_array(
                    output / f"{case['id']}.npz", **{k: np.asarray(v) for k, v in pred.items()}
                ),
            }
        )
        print(
            len(result),
            case["id"],
            [bool(any(f["active"])) for f in rows[2]["fits"].values()],
            flush=True,
        )
    return result


@torch.inference_mode()
def collect(path):
    from transformers import AutoModel

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    backbone = AutoModel.from_pretrained(plan["encoder"], local_files_only=True).eval()
    assert backbone.config.model_type == "dinov3_convnext"
    mean, std = (
        torch.tensor(v).reshape(1, 3, 1, 1) for v in ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    )
    model = SimpleNamespace(
        base=SimpleNamespace(context=SimpleNamespace(backbone=backbone, mean=mean, std=std))
    )
    cfg = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    started = time.monotonic()
    earlier = read_json(checked(plan["base_collection"]))
    camera = camera_replays(plan, earlier, model, cfg, output)
    write_json(output / "camera-collection.json", {"plan": reference(path), "camera": camera})
    synthetic = synthetic_replays(plan, earlier, model, cfg, output)
    assert len(camera) == 8 and len(synthetic) == 32
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "camera": camera,
            "synthetic": synthetic,
            "seconds": time.monotonic() - started,
            "restoration_checkpoint_forwards": 0,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path)
    parser.add_argument("--dino-snapshots", type=Path)
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve(), args.dino_snapshots.resolve())
    elif args.report:
        report(args.path.resolve())
    else:
        collect(args.path.resolve())
