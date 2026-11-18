"""Evaluate donor rankings on unseen wire fields with paired appearance controls."""

import argparse
import time
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import torch
from probe_affinity_first_donors import choose, same_geometry
from probe_fresh_phase_refit import PATTERNS, SENSOR_KEYS, write_array
from probe_scene_context_extent import encode
from probe_screened_scene_donors import alternate_raw, context_ranks, offset_box
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
from demosaic.experiments.data.edge_response import edge_observation, scene_recipe
from demosaic.inference import load_checkpoint
from demosaic.local_validated_waves import LocalWaveConfig
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.screened_scene_donors import retain_near_preview, screening_preview
from demosaic.search_donor_geometry import _native, screening_mask, search_donor_geometry

ARMS = ("parent", "planar", "weighted", "near", "scene")
DRIFTS = (
    ((3, 0), (-6, 0)),
    ((-5, 0), (3, 0)),
    ((0, 4), (0, -3)),
    ((0, -4), (0, 3)),
    ((6, 0), (6, 0)),
    ((0, -6), (0, 5)),
    ((0, 0), (0, 0)),
    ((0, 0), (0, 0)),
)
HORIZONTAL = ((-128, 128, 256, 256), (384, 128, 256, 256))
VERTICAL = ((128, -128, 256, 256), (128, 384, 256, 256))
SIZE = 1280


def prepare(root, prior, parent_device):
    source = read_json(prior)
    root.mkdir()
    work, files = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_scene_wave_guides.py"]
    )
    groups = [
        {
            "source": i + 88,
            "CFA": PATTERNS[i % 4],
            "drifts": drift,
            "profile": profile,
            "appearance": "distinct" if i % 2 else "same-paint",
            "matched_vertical": i % 4 >= 2,
            "id": f"{profile}-source{i + 88}-{PATTERNS[i % 4]}",
        }
        for i, drift in enumerate(DRIFTS)
        for profile in ("iso400", "iso6400")
    ]
    weights = [
        reference(Path(source["encoder"]) / key) for key in ("config.json", "model.safetensors")
    ]
    write_json(
        root / "plan.json",
        {
            **{
                k: source[k]
                for k in (
                    "query_xywh",
                    "parent_checkpoint",
                    "encoder",
                    "config",
                    "profiles",
                    "preview",
                )
            },
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": files,
            "inputs": [reference(prior), source["parent_checkpoint"], *weights],
            "groups": groups,
            "arms": ARMS,
            "parent_device": parent_device,
            "cuda_allocator_limit_bytes": 6 * 2**30 if parent_device == "cuda" else None,
            "settings": {
                s["profile"]: s
                for s in source["settings"]
                if s["placement"] == "far" and s["budget_DN16"] == 0.02
            },
            "query_repeat": 9164,
            "matched_repeats": [9165, 9166],
            "alternate_repeats": [9167, 9168],
            "scope": "Source-disjoint 88–95 and independent sensor draws. Test distinct paint and identical paint/levels "
            "with the same strong rotated distractor; swap the correct bracket axis across sources. "
            "Same spectrum and donor/query split for all policies. No use of clean targets for ranking.",
        },
    )


def candidates(plan, group, recipe, colors, wb, matrix, noise, output):
    correct, wrong = (VERTICAL, HORIZONTAL) if group["matched_vertical"] else (HORIZONTAL, VERTICAL)
    level, bright = 0.16, 0.30
    spec = {
        "alternate_angles_degrees": 40,
        "alternate_amplitude": 0.077,
        "alternate_level": level,
        "alternate_bright_level": bright,
        "alternate_rgb_scale": [1.45, 1, 0.60] if group["appearance"] == "distinct" else [1, 1, 1],
    }
    visits = []
    for i, (box, repeat) in enumerate(
        zip((*correct, *wrong), plan["matched_repeats"] + plan["alternate_repeats"], strict=True)
    ):
        if i < 2:
            donor_recipe = recipe | {
                "size": 256,
                "level": level,
                "bright_level": bright,
                "edge_jitter": 0.0,
                "amplitude": 0.055,
                "weak_fraction": 1.0,
                "mask_radii": [116.0, 116.0],
                "phase_position_offset_xy": list(box[:2]),
                "phase_reference_size": 512,
            }
            values, declaration = edge_observation(
                donor_recipe, "far", group["CFA"], repeat, condition=noise
            )
            np.testing.assert_array_equal(values["colors"][2], colors)
            packed, identity = values["packed"][2], declaration["identities"][2]
        else:
            packed, identity = alternate_raw(
                group | {"metadata": {"recipe": recipe}}, wb, matrix, noise, spec, repeat
            )
        visits.append(
            {
                "box": offset_box(box),
                "identity": identity,
                "raw": write_array(
                    output / f"{group['id']}-donor{i}.npz", packed=packed, colors=colors
                ),
            }
        )
    return visits


def place(raw, packed, colors, box):
    x, y, w, h = box
    raw[y : y + h, x : x + w] = _native(packed, colors, box)[0]


def compose(group, colors, views, noise):
    yy, xx = np.ogrid[:SIZE, :SIZE]
    surface = xx if group["matched_vertical"] else yy
    layout = colors.reshape(2, 2)[yy % 2, xx % 2]
    a = np.array([0.10, 0.14, 0.10])
    b = a * (np.array([1.45, 1, 0.60]) if group["appearance"] == "distinct" else 1.0)
    base = np.where(np.abs(surface - SIZE // 2) < 160, a[layout], b[layout])
    rng = np.random.default_rng(group["source"] + 9169)
    raw = (
        base + rng.normal(size=base.shape) * np.sqrt(noise["read"] + noise["shot"] * base)
    ).astype(np.float32)
    for packed, cs, box in views:
        place(raw, packed, cs, box)
    return raw


def role_predictions(plan, group, encoder, prepared, parent, views, noise, cfg):
    query = offset_box(plan["query_xywh"])
    evidence = ~screening_mask(query)
    raw = compose(group, prepared["colors"][0], views, noise)
    t = plan["settings"][group["profile"]]["threshold"]
    x, y, w, h = plan["query_xywh"]
    cropped = prepared["packed"][:, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
    boxes = [b for _, _, b in views]
    rankings, out = [], {arm: [] for arm in ARMS}
    spectral = search_donor_geometry(views, query, shot=noise["shot"], read=noise["read"])
    for role, (tile, packed, colors, wb, matrix) in enumerate(
        zip(
            parent[ROI],
            cropped,
            prepared["colors"],
            prepared["wb"],
            prepared["matrix"],
            strict=True,
        )
    ):
        place(raw, packed, colors, query)
        preview, grid = screening_preview(raw, group["CFA"], wb, matrix, **plan["preview"])
        full = encode(encoder, preview, grid)
        near = encode(encoder, retain_near_preview(preview, grid, (256, 256, 768, 768)), grid)
        affinities = context_ranks(near, full, boxes, query)
        record = {"affinities": affinities}
        fits = {
            "planar": spectral,
            "weighted": search_donor_geometry(
                views,
                query,
                shot=noise["shot"],
                read=noise["read"],
                donor_affinity=affinities["scene"],
            ),
            "near": choose(views, query, noise, record, "near"),
            "scene": choose(views, query, noise, record, "scene"),
        }
        out["parent"].append(tile)
        earlier = {}
        for arm, fit in fits.items():
            match = next((name for name, f in earlier.items() if same_geometry(fit, f)), None)
            if match is not None:
                pixel = out[match][role]
            elif any(fit["active"]):
                pixel = deliver(
                    tile,
                    packed,
                    colors,
                    fit,
                    noise,
                    cfg,
                    (t,),
                    False,
                    False,
                    evidence_mask=evidence,
                )[t]
            else:
                pixel = tile
            out[arm].append(pixel)
            earlier[arm] = fit
        rankings.append(
            {
                "preview": fingerprint(preview),
                "fits": fits,
                "affinities": {arm: view.tolist() for arm, view in affinities.items()},
            }
        )
    return {arm: np.stack(pixels) for arm, pixels in out.items()}, rankings


def collect(path):
    from transformers import AutoModel

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    start = time.monotonic()
    device = torch.device("cuda", 0) if plan["parent_device"] == "cuda" else torch.device("cpu")
    if device.type == "cuda":
        total = torch.cuda.get_device_properties(device).total_memory
        torch.cuda.set_per_process_memory_fraction(
            plan["cuda_allocator_limit_bytes"] / total, device
        )
    model, payload = load_checkpoint(checked(plan["parent_checkpoint"]), "cpu")
    assert payload["step"] == plan["parent_checkpoint"]["step"]
    assert payload["loaded_sha256"] == plan["parent_checkpoint"]["sha256"]
    assert all(torch.equal(v, payload["ema"][k]) for k, v in model.restoration_state_dict().items())
    del payload
    model.eval().requires_grad_(False).to(device=device, memory_format=torch.contiguous_format)
    base = AutoModel.from_pretrained(plan["encoder"], local_files_only=True).eval()
    mean, std = (
        torch.tensor(x).reshape(1, 3, 1, 1) for x in ([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    )
    encoder = SimpleNamespace(
        base=SimpleNamespace(context=SimpleNamespace(backbone=base, mean=mean, std=std))
    )
    cfg = LocalWaveConfig(**plan["config"])
    out = Path(plan["root"]) / "output"
    out.mkdir()
    rows, parent_seconds = [], 0.0
    with torch.inference_mode(), ieee_fp32():
        for group in plan["groups"]:
            key = group["id"]
            noise = plan["profiles"][group["profile"]]
            recipe = scene_recipe(group["source"]) | {"phase_drifts": group["drifts"]}
            data, declaration = edge_observation(
                recipe, "far", group["CFA"], plan["query_repeat"], condition=noise
            )
            prepared = {k: data.pop(k) for k in SENSOR_KEYS}
            model.set_noise(noise["shot"], noise["read"])
            clock = time.monotonic()
            parent = model(*(torch.from_numpy(prepared[k]).to(device) for k in SENSOR_KEYS))
            parent = parent.cpu().numpy()
            parent_seconds += time.monotonic() - clock
            assert parent.shape == (3, 3, 512, 512) and np.isfinite(parent).all()
            visits = candidates(
                plan,
                group,
                recipe,
                prepared["colors"][2],
                prepared["wb"][2],
                prepared["matrix"][2],
                noise,
                out,
            )
            views = []
            for item in visits:
                with np.load(checked(item["raw"])) as f:
                    views.append((f["packed"], f["colors"], item["box"]))
            predicted, rankings = role_predictions(
                plan, group, encoder, prepared, parent, views, noise, cfg
            )
            sensor = write_array(out / f"{key}-sensor.npz", **prepared)
            target = write_array(out / f"{key}-target.npz", **data)
            parent_path = write_array(out / f"{key}-parent.npz", parent=parent)
            prediction = write_array(out / f"{key}-prediction.npz", **predicted)
            row = group | {
                "metadata": declaration,
                "sensor": sensor,
                "target": target,
                "parent": parent_path,
                "prediction": prediction,
                "rankings": rankings,
                "donors": visits,
            }
            file = out / f"{key}.json"
            write_json(file, row)
            rows.append(reference(file))
            print(len(rows), key, round(time.monotonic() - start, 1), flush=True)
    write_json(
        out / "collection.json",
        {
            "plan": reference(path),
            "cases": rows,
            "seconds": time.monotonic() - start,
            "parent_device": device.type,
            "parent_forward_and_transfer_seconds": parent_seconds,
            "peak_cuda_bytes": torch.cuda.max_memory_allocated(device)
            if device.type == "cuda"
            else None,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path)
    parser.add_argument("--parent-device", default="cpu", choices=("cpu", "cuda"))
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve(), args.parent_device)
    else:
        collect(args.path.resolve())
