"""Test measured quadratic donor geometry on retained sensor observations."""

import argparse
import time
from pathlib import Path

import numpy as np
from probe_fresh_phase_refit import write_array
from report_fold_support_pooling import ROI, evaluated, measure
from report_phase_drift import aggregate
from report_scene_wave_guides import native_board

from demosaic.archive_metrics import noisy_malvar
from demosaic.donor_phase_geometry import transport_donor_geometry
from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves

ARMS = ("guarded", "planar", "transport")
QUERY_BOX = (128, 128, 256, 256)
DONOR_BOX = (384, 128, 256, 256)


def prepare(root, previous):
    source = previous / "plan.json"
    old = read_json(source)
    collection = previous / "output/collection.json"
    assert read_json(collection)["plan"] == reference(source)
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name])
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "frozen_files": hashes,
            "driver": reference(work / "scripts" / Path(__file__).name),
            "inputs": [
                reference(source),
                reference(collection),
                old["camera_baseline"],
                old["camera_conditions"],
            ],
            "previous_plan": reference(source),
            "previous_collection": reference(collection),
            "camera_baseline": old["camera_baseline"],
            "camera_conditions": old["camera_conditions"],
            "parent_checkpoint": old["parent"],
            "config": old["config"],
            "profiles": old["profiles"],
            "settings": old["settings"],
            "arms": ARMS,
            "query_xywh": QUERY_BOX,
            "donor_xywh": DONOR_BOX,
            "donor_noise_repeat": 7952,
            "scope": "Use the same 32 query observations and V143 predictions. Render a stronger adjacent donor "
            "with the same geometry and an independent noise seed. Query-alone amplitude, "
            "color, phase and support. Both fixed arms use the same transported center frequencies. "
            "The guarded arm reuses exact saved planar controls. Eight camera crops use cached disjoint donors.",
        },
    )


def sensor_box(path, box):
    x, y, w, h = box
    with np.load(checked(path)) as data:
        return data["packed"][..., y // 2 : (y + h) // 2, x // 2 : (x + w) // 2], data["colors"]


def restore(parent, packed, colors, geometry, noise, cfg, thresholds, near, curved):
    output, diagnostics = restore_local_waves(
        parent,
        packed,
        colors,
        shot=noise["shot"],
        read=noise["read"],
        config=cfg,
        thresholds=thresholds,
        guide_frequencies_xy=geometry["frequencies_xy"],
        guide_phase_hessians_xy=geometry["hessians_xy"] if curved else None,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        phase_edge_side="validation" if near else None,
    )
    return {t: output["weighted-refit", t] for t in thresholds}, diagnostics


def sample_donor_raw(case, noise, box, repeat):
    from demosaic.experiments.data.edge_response import edge_observation

    recipe = case["metadata"]["recipe"] | {
        "size": 256,
        "level": 0.11,
        "bright_level": 0.25,
        "edge_jitter": 0.0,
        "mask_radii": [116.0, 116.0],
        "amplitude": 0.055,
        "weak_fraction": 1.0,
        "phase_position_offset_xy": box[:2],
        "phase_reference_size": 512,
    }
    data, metadata = edge_observation(recipe, "far", "RGGB", repeat, condition=noise)
    return data["packed"][2], data["colors"][2], metadata


def synthetic_donor(plan, case, seed, noise, output):
    packed, colors, metadata = sample_donor_raw(
        case, noise, plan["donor_xywh"], plan["donor_noise_repeat"]
    )
    fit = transport_donor_geometry(
        packed,
        colors,
        plan["donor_xywh"],
        plan["query_xywh"],
        seed,
        shot=noise["shot"],
        read=noise["read"],
    )
    return {
        "metadata": metadata,
        "sensor": write_array(output, packed=packed, colors=colors),
        "initial_guide": seed,
        "fit": fit,
    }


def collect(path):
    import torch

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    cfg = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    previous = read_json(checked(plan["previous_collection"]))
    started = time.monotonic()
    donors, records, cameras = {}, [], []
    for old in previous["synthetic"]:
        case = read_json(checked(old))
        key = case["id"]
        profile = case["profile"]
        donor_id = case["guide_key"]
        noise = plan["profiles"][profile]
        if donor_id not in donors:
            seed = previous["donors"][donor_id]["frequencies"]
            donors[donor_id] = synthetic_donor(
                plan, case, seed, noise, output / f"{donor_id}-transport-donor.npz"
            )
        donor = donors[donor_id]["fit"]
        packed, colors = sensor_box(case["sensor"], plan["query_xywh"])
        parent = np.load(checked(case["parent"]))[ROI]
        near = case["placement"] == "near"
        thresholds = tuple(
            sorted(
                {
                    s["threshold"]
                    for s in plan["settings"]
                    if (s["profile"], s["placement"]) == (profile, case["placement"])
                }
            )
        )
        arrays = {}
        for arm in ("planar", "transport"):
            for role in range(3):
                values, _ = restore(
                    parent[role],
                    packed[role],
                    colors[role],
                    donor,
                    noise,
                    cfg,
                    thresholds,
                    near,
                    arm == "transport",
                )
                for t, pixels in values.items():
                    arrays.setdefault(f"{arm}--t{t:g}", []).append(pixels)
        with np.load(checked(case["prediction"])) as saved:
            for t in thresholds:
                arrays[f"guarded--t{t:g}"] = saved[f"planar--t{t:g}"]
                if not any(donor["accepted"]):
                    np.testing.assert_array_equal(
                        arrays[f"planar--t{t:g}"], arrays[f"transport--t{t:g}"]
                    )
        records.append(
            {
                "id": key,
                "case": old,
                "guide_key": donor_id,
                "prediction": write_array(
                    output / f"{key}.npz", **{k: np.stack(v) for k, v in arrays.items()}
                ),
            }
        )
        print(
            len(records), key, donor["accepted"], round(time.monotonic() - started, 2), flush=True
        )
    camera_baseline = read_json(checked(plan["camera_baseline"]))
    conditions = read_json(checked(plan["camera_conditions"]))
    for row, condition in zip(camera_baseline["camera"], conditions["camera"], strict=True):
        key, scene = row["id"], row["source"]
        assert key == condition["board"]["id"]
        noise = condition["noise"]
        donor, donor_colors = sensor_box(scene["donor_arrays"], scene["donor_box"])
        fit = transport_donor_geometry(
            donor[0],
            donor_colors[0],
            scene["absolute_donor_xywh"],
            scene["absolute_query_xywh"],
            scene["guide"],
            shot=noise["shot"],
            read=noise["read"],
        )
        if any(fit["accepted"]):
            x, y, w, h = scene["query_box"]
            parent = np.load(checked(scene["parent_prediction"]), mmap_mode="r")[
                0, :, y : y + h, x : x + w
            ]
            query, colors = sensor_box(scene["query_arrays"], scene["query_box"])
            corrected, _ = restore(parent, query[0], colors[0], fit, noise, cfg, (2.0,), True, True)
            prediction = write_array(output / f"{key}.npz", corrected=corrected[2.0])
        else:
            prediction = row["crosscheck_prediction"]
        cameras.append({"id": key, "prediction": prediction, "fit": fit})
    assert len(records) == 32 and len(cameras) == 8 and len(donors) == 16
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": records,
            "camera": cameras,
            "donors": donors,
            "seconds": time.monotonic() - started,
            "new_neural_calls": 0,
        },
    )


def report(path):
    from report_phase_drift import make_camera_board

    plan = read_json(path)
    root = Path(plan["root"])
    receipt = root / "output/collection.json"
    done = read_json(receipt)
    assert done["plan"] == reference(path)
    options = plan.get("rendering", {})
    labels = options.get("labels", ("Guarded guide", "Fixed planar", "Donor curvature"))
    picture_sources = options.get("sources", (80, 83))
    caption = options.get("camera_label", "Donor curvature")
    output = root / "review"
    output.mkdir()
    rows, boards = [], []
    for record in done["synthetic"]:
        case = read_json(checked(record["case"]))
        parent = np.load(checked(case["parent"])).astype(np.float64)
        with np.load(checked(case["target"])) as f:
            target, quiet = f["target"].astype(np.float64), f["quiet"][ROI]
        with np.load(checked(record["prediction"])) as stored:
            for setting in plan["settings"]:
                if (setting["profile"], setting["placement"]) != (
                    case["profile"],
                    case["placement"],
                ):
                    continue
                t, scale = setting["threshold"], setting["scale"]
                predicted = {k: stored[f"{k}--t{t:g}"] for k in plan["arms"]}
                for arm, pixels in predicted.items():
                    fit = measure(parent, target, quiet, pixels)
                    rows.append(
                        {
                            "id": case["id"],
                            "kind": case["kind"],
                            "arm": arm,
                            "setting": setting,
                            "moments": {k: v.tolist() for k, v in fit.items()},
                            "fixed": evaluated(fit, scale),
                        }
                    )
                if (case["profile"], case["placement"], setting["budget_DN16"]) == (
                    "iso400",
                    "far",
                    0.02,
                ) and case["source"] in picture_sources:
                    p = parent[2][ROI]
                    with np.load(checked(case["sensor"])) as f:
                        ctx = {k: f[k][2:3] for k in ("colors", "wb", "matrix")}
                        ctx["packed"] = f["packed"][2:3, :, 64:192, 64:192]
                    boards.append(
                        native_board(
                            output,
                            case["id"],
                            [
                                noisy_malvar(ctx)[0],
                                p,
                                *(p + scale * (f[2] - p) for f in predicted.values()),
                                target[2][ROI],
                            ],
                            ctx,
                            {"case_receipt": record["case"], "operating_point": setting},
                            labels=("Noisy Malvar", "V143 EMA", *labels, "Exact GT"),
                            triplet_indices=(0, len(labels) + 1, len(labels) + 2),
                            contrast=options.get("contrast", 1),
                        )
                    )
    old = read_json(checked(plan["camera_baseline"]))
    cameras = [
        make_camera_board(output, a, b, label=caption)
        for a, b in zip(old["camera"], done["camera"], strict=True)
    ]
    assert len(rows) == 64 * len(plan["arms"]) and len(boards) == 2 and len(cameras) == 8
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "plan": reference(path),
            "collection": reference(receipt),
            "metrics": rows,
            "aggregates": aggregate(rows, plan),
            "boards": boards,
            "camera": cameras,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--prepare-from", type=Path)
    group.add_argument("--report", action="store_true")
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve())
    elif args.report:
        report(args.path.resolve())
    else:
        collect(args.path.resolve())
