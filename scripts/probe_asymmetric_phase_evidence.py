"""Compare bright-side cross-edge evidence on fresh wire observations."""

import argparse
import os
import time
from itertools import product
from pathlib import Path

import numpy as np
import psutil
from probe_fresh_phase_refit import PATTERNS, PROFILES, SENSOR_KEYS, measure_donor, write_array

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves

ARMS = {"independent": None, "same-side": 0.0, "bright-half": 0.5, "bright-full": 1.0}
SOURCES = tuple(range(60, 68))
QUERY_REPEAT, DONOR_REPEAT = 7521, 7522


def prepare(root, prior):
    previous = prior / "plan.json"
    previous_report = prior / "review/result.json"
    old = read_json(previous)
    report = read_json(previous_report)
    assert report["plan"] == reference(previous)
    guard = read_json(checked(old["guard_plan"]))
    fresh = read_json(checked(guard["fresh_plan"]))
    assert not (set(SOURCES) & (set(fresh["sources"]) | set(range(8))))
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_asymmetric_phase_evidence.py"]
    )
    groups = [
        {
            "id": f"{profile}-source{source}-{place}-{PATTERNS[i % 4]}",
            "profile": profile,
            "source": source,
            "placement": place,
            "CFA": PATTERNS[i % 4],
            "repeat": QUERY_REPEAT,
        }
        for profile, (i, source), place in product(PROFILES, enumerate(SOURCES), ("near", "far"))
        if place == "near" or i < 2
    ]
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": hashes,
            "inputs": [
                reference(previous),
                reference(previous_report),
                old["guard_plan"],
                old["guard_report"],
                guard["fresh_plan"],
                fresh["parent"],
            ],
            "parent": fresh["parent"],
            "parent_weights": "EMA",
            "profiles": fresh["profiles"],
            "guide_config": fresh["guide_config"],
            "config": guard["config"],
            "guide_half_threshold_each_fold": fresh["guide_half_threshold_each_fold"],
            "sources": SOURCES,
            "donor_repeat": DONOR_REPEAT,
            "groups": groups,
            "settings": [s for s in old["settings"] if s["method"] == "weighted-refit"],
            "arms": ARMS,
            "camera_controls": reference(previous_report),
            "camera_plan": old["guard_plan"],
            "scope": "Fresh near-edge sources 60 through 67, crossed with two noise levels and all four Bayer"
            " orders. Sources 60 and 61 are also retained far controls. Same V143 parent, donor"
            " protocol, guard, both folds and frozen weighted-refit settings. Reuse the earlier"
            " audited V120 camera controls and replay the two asymmetric arms.",
        },
    )


def restore(parent, packed, colors, guide, noise, config, thresholds, weight):
    values, fit = restore_local_waves(
        parent,
        packed,
        colors,
        shot=noise["shot"],
        read=noise["read"],
        config=config,
        thresholds=thresholds,
        guide_frequencies_xy=guide,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        recenter_phase_guides=True,
        phase_guide_edge_guard_px=8,
        phase_edge_side=None if weight is None else "validation",
        bright_cross_edge_weight=0.0 if weight is None else weight,
    )
    return values, fit


def compare_geometry(left, right):
    for key in ("frequencies", "edges", "guide_search_excluded", "discovery_reliability"):
        np.testing.assert_array_equal(left["records"][0][key], right["records"][0][key])


def collect(path):
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.experiments.data.edge_response import edge_observation, scene_recipe
    from demosaic.inference import load_checkpoint
    from demosaic.precision import ieee_fp32
    from demosaic.prediction_archive import fingerprint

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__) and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    image_model, state = load_checkpoint(checked(plan["parent"]), "cpu")
    assert (
        state["step"] == plan["parent"]["step"]
        and state["loaded_sha256"] == plan["parent"]["sha256"]
    )
    assert all(
        torch.equal(v, state["ema"][k]) for k, v in image_model.restoration_state_dict().items()
    )
    del state
    image_model.eval().requires_grad_(False).to(memory_format=torch.contiguous_format)
    counts = {"root": 0, "DINO": 0}
    for name, module in (("root", image_model), ("DINO", image_model.context.backbone)):
        module.register_forward_hook(lambda *_, key=name: counts.__setitem__(key, counts[key] + 1))
    before = model_hash(image_model)
    config = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    start, model_seconds = time.monotonic(), 0.0
    donors, observations, cameras = {}, [], []
    with torch.inference_mode(), ieee_fp32():
        for group in plan["groups"]:
            if psutil.virtual_memory().available < 24 * 2**30:
                raise RuntimeError("Available memory fell below 24 GiB")
            key = group["id"]
            noise = plan["profiles"][group["profile"]]
            recipe = scene_recipe(group["source"])
            donor_id = f"{group['profile']}-{group['source']}"
            if donor_id not in donors:
                donors[donor_id] = measure_donor(recipe, group["profile"], noise, plan, output)
            guide = donors[donor_id]["frequencies"]
            data, meta = edge_observation(
                recipe, group["placement"], group["CFA"], group["repeat"], condition=noise
            )
            observed = {k: data.pop(k) for k in SENSOR_KEYS}
            sensor = write_array(output / f"{key}-sensor.npz", **observed)
            target = write_array(output / f"{key}-target.npz", **data)
            image_model.set_noise(noise["shot"], noise["read"])
            started = time.monotonic()
            parent = image_model(*(torch.from_numpy(observed[k]) for k in SENSOR_KEYS)).numpy()
            model_seconds += time.monotonic() - started
            assert (
                parent.shape == (3, 3, 512, 512)
                and parent.dtype == np.float32
                and np.isfinite(parent).all()
            )
            path_parent = output / f"{key}-parent.npy"
            with path_parent.open("xb") as file:
                np.save(file, parent, allow_pickle=False)
            thresholds = tuple(
                sorted(
                    {
                        s["threshold"]
                        for s in plan["settings"]
                        if (s["profile"], s["placement"]) == (group["profile"], group["placement"])
                    }
                )
            )
            images, diagnostics = {}, {}
            for label, weight in plan["arms"].items():
                role_fits = []
                for role in range(3):
                    values, fit = restore(
                        parent[role, :, 128:384, 128:384],
                        observed["packed"][role, :, 64:192, 64:192],
                        observed["colors"][role],
                        guide,
                        noise,
                        config,
                        thresholds,
                        weight,
                    )
                    role_fits.append(fit)
                    for threshold in thresholds:
                        images.setdefault(f"{label}--t{threshold:g}", []).append(
                            values["weighted-refit", threshold]
                        )
                    if label != "independent":
                        compare_geometry(diagnostics["independent"][role], fit)
                        if not fit["records"][0]["phase_edge_side_applied"]:
                            for threshold in thresholds:
                                np.testing.assert_array_equal(
                                    images[f"{label}--t{threshold:g}"][role],
                                    images[f"independent--t{threshold:g}"][role],
                                )
                diagnostics[label] = role_fits
            prediction = write_array(
                output / f"{key}-predictions.npz", **{k: np.stack(v) for k, v in images.items()}
            )
            receipt = output / f"{key}.json"
            write_json(
                receipt,
                {
                    **group,
                    "metadata": meta,
                    "sensor": sensor,
                    "target": target,
                    "parent": reference(path_parent),
                    "guide_key": donor_id,
                    "prediction": prediction,
                    "fits": diagnostics,
                    "sensor_fingerprints": {k: fingerprint(v) for k, v in observed.items()},
                },
            )
            observations.append(reference(receipt))
            print(len(observations), key, round(time.monotonic() - start, 3), flush=True)

    control = read_json(checked(plan["camera_controls"]))
    old_collection = read_json(checked(control["collection"]))
    camera_plan = read_json(checked(plan["camera_plan"]))
    for item, old, declaration in zip(
        control["camera"], old_collection["camera"], camera_plan["camera"], strict=True
    ):
        key = item["id"]
        assert key == old["id"] == declaration["board"]["id"]
        scene = item["source"]
        x, y, w, h = scene["query_box"]
        with np.load(checked(scene["query_arrays"])) as sensor:
            packed = sensor["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = sensor["colors"][0]
        parent = np.load(checked(scene["parent_prediction"]), mmap_mode="r")[
            0, :, y : y + h, x : x + w
        ]
        images, fits = {}, {}
        for label in ("bright-half", "bright-full"):
            values, fit = restore(
                parent,
                packed,
                colors,
                scene["guide"],
                declaration["noise"],
                config,
                (2,),
                plan["arms"][label],
            )
            result = values["weighted-refit", 2]
            compare_geometry(old["fits"]["validation"], fit)
            if not fit["records"][0]["phase_edge_side_applied"]:
                with np.load(checked(item["edge_side_predictions"])) as predictions:
                    np.testing.assert_array_equal(result, predictions["validation"])
            images[label], fits[label] = result, fit
        pred = write_array(output / f"{key}-predictions.npz", **images)
        cameras.append({"id": key, "prediction": pred, "fits": fits})
    assert before == model_hash(image_model) and not torch.cuda.is_initialized()
    assert counts == {"root": 20, "DINO": 20} and len(donors) == 16 and len(cameras) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": observations,
            "camera": cameras,
            "donors": donors,
            "synthetic_observations": len(observations) * 3,
            "synthetic_fits": len(observations) * 3 * len(ARMS),
            "camera_fits": len(cameras) * 2,
            "parent_calls": counts,
            "parent_state_unchanged": True,
            "parent_forward_seconds": model_seconds,
            "seconds": time.monotonic() - start,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path)
    args = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(10)
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve())
    else:
        collect(args.path.resolve())
