"""Test the weighted RAW refit on new wire geometries and sensor observations."""

import argparse
import os
import time
from itertools import product
from pathlib import Path

import numpy as np
import psutil
from probe_fold_support_pooling import THRESHOLDS
from report_fold_support_pooling import evaluated, scale_at_budget

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import (
    LocalWaveConfig,
    donor_subharmonic_scores,
    fit_local_candidate,
    restore_local_waves,
)

METHODS = {"fold-average": "square", "weighted-refit": "weighted-refit"}
BUDGETS = (0.02, 0.1)
PROFILES = ("iso400", "iso6400")
PLACEMENTS = ("far", "near")
PATTERNS = ("RGGB", "BGGR", "GRBG", "GBRG")
SOURCES = tuple(range(40, 48))
QUERY_REPEAT = 7311
DONOR_REPEAT = 7312
SENSOR_KEYS = ("packed", "variance", "colors", "wb", "matrix")


def calibrate(rows, thresholds, budgets):
    """Freeze one threshold and scale per stratum on the previous geometries."""
    settings = []
    for profile, placement, (method, prior), budget in product(
        PROFILES, PLACEMENTS, METHODS.items(), budgets
    ):
        candidates = []
        for threshold in thresholds:
            source = [
                r
                for r in rows
                if r["profile"] == profile
                and r["placement"] == placement
                and r["method"] == f"{prior}-t{threshold:g}"
            ]
            assert {(r["source"], r["CFA"]) for r in source} == set(
                product(range(8), PATTERNS)
            ) and len(source) == 32
            moment = {
                k: np.mean([r["moments"][k] for r in source], 0) for k in source[0]["moments"]
            }
            alpha = (
                scale_at_budget(moment["quiet_mse"], budget) if moment["weak_gain"][1] > 0 else 0
            )
            observed, parent = evaluated(moment, alpha), evaluated(moment, 0)
            delta = observed["quiet_RMS_DN16"] - parent["quiet_RMS_DN16"]
            assert 0 <= alpha <= 1 and delta <= budget + 1e-10
            candidates.append((observed["weak_gain"], -threshold, alpha, delta))
        recovery, negative_t, scale, delta = max(candidates)
        settings.append(
            {
                "profile": profile,
                "placement": placement,
                "method": method,
                "budget_DN16": budget,
                "threshold": -negative_t,
                "scale": scale,
                "calibration_weak_gain": recovery,
                "calibration_quiet_delta_DN16": delta,
            }
        )
    return settings


def prepare(root, development):
    plan_path, report_path = (development / p for p in ("plan.json", "review/result.json"))
    old, closed = read_json(plan_path), read_json(report_path)
    assert closed["plan"] == reference(plan_path)
    assessment = read_json(checked(old["donor_assessment"]))
    guide = read_json(checked(assessment["synthetic_plan"]))
    parent = guide["parents"]["priors"]["iso400"]["parent"]
    assert all(guide["parents"]["priors"][p]["parent"] == parent for p in PROFILES)
    profiles = {row["profile"]: row["noise"] for row in old["groups"]}
    retained = {row["source"] for row in old["groups"]}
    assert retained == set(range(8)) and not retained.intersection(SOURCES)
    refs = [
        reference(plan_path),
        reference(report_path),
        old["donor_assessment"],
        assessment["synthetic_plan"],
        parent,
    ]
    root.mkdir()
    work, files = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_fresh_phase_refit.py"]
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": files,
            "inputs": refs,
            "development_report": reference(report_path),
            "config": old["config"],
            "guide_config": guide["guide_config"],
            "parent": parent,
            "parent_weights": "EMA",
            "parent_batch_size": 3,
            "CPU_threads": 2,
            "profiles": profiles,
            "sources": list(SOURCES),
            "thresholds": list(THRESHOLDS),
            "settings": calibrate(closed["fixed_threshold_metrics"], THRESHOLDS, BUDGETS),
            "guide_half_threshold_each_fold": 3,
            "groups": [
                {
                    "id": f"{p}-source{s}-{w}-{PATTERNS[i % 4]}",
                    "profile": p,
                    "source": s,
                    "placement": w,
                    "CFA": PATTERNS[i % 4],
                    "repeat": QUERY_REPEAT,
                }
                for p, (i, s), w in product(PROFILES, enumerate(SOURCES), PLACEMENTS)
            ],
            "donor_repeat": DONOR_REPEAT,
            "retained_camera_review": closed["camera_boards"],
            "scope": "New procedural scenes and sensor noise, same finite-wire generator family and native 512"
            " parent context. Balanced single CFA per source. Settings use development groups 0–7 only."
            " Donors are separate noisy regions with changed phase and stronger contrast."
            " No failed guides dropped. Camera outputs adopt the reviewed same-operator predictions.",
        },
    )


def write_array(path, **arrays):
    with path.open("xb") as stream:
        np.savez(stream, **arrays)
    return reference(path)


def measure_donor(recipe, profile, noise, plan, output):
    from demosaic.experiments.data.edge_response import edge_observation

    donor = {
        **recipe,
        "size": 256,
        "level": 0.11,
        "bright_level": 0.25,
        "edge_jitter": 0.0,
        "mask_radii": [116.0, 116.0],
        "amplitude": 0.055,
        "weak_fraction": 1.0,
        "phases": [
            (phase + shift) % 1
            for phase, shift in zip(recipe["phases"], (0.271, 0.389), strict=True)
        ],
    }
    arrays, meta = edge_observation(donor, "far", "RGGB", plan["donor_repeat"], condition=noise)
    packed, colors = arrays["packed"][2], arrays["colors"][2]
    raw = packed.reshape(2, 2, 128, 128).transpose(2, 0, 3, 1).reshape(256, 256)
    cfa = np.tile(colors.reshape(2, 2), (128, 128))
    config = LocalWaveConfig(**plan["guide_config"])
    options = {"shot": noise["shot"], "read": noise["read"], "config": config}
    fitted = fit_local_candidate(raw, cfa, np.ones(raw.shape, dtype=bool), **options)
    original = np.asarray(fitted.frequencies_xy)
    scores = donor_subharmonic_scores(raw, cfa, original, **options)
    accepted = (scores >= plan["guide_half_threshold_each_fold"]).all(0)
    return {
        "arrays": write_array(
            output / f"donor-{profile}-{recipe['source']}.npz", packed=packed, colors=colors
        ),
        "metadata": meta,
        "original": original.tolist(),
        "scores": scores.tolist(),
        "accepted": accepted.tolist(),
        "frequencies": (original * np.where(accepted[:, None], 0.5, 1)).tolist(),
    }


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
    torch.set_num_threads(plan["CPU_threads"])
    torch.set_num_interop_threads(1)
    config = LocalWaveConfig(**plan["config"])
    parent, state = load_checkpoint(checked(plan["parent"]), "cpu")
    assert (
        state["step"] == plan["parent"]["step"]
        and state["loaded_sha256"] == plan["parent"]["sha256"]
    )
    assert all(
        torch.equal(value, state["ema"][name])
        for name, value in parent.restoration_state_dict().items()
    )
    del state
    parent.eval().requires_grad_(False).to(memory_format=torch.contiguous_format)
    counts = {"root": 0, "DINO": 0}
    for key, module in (("root", parent), ("DINO", parent.context.backbone)):
        module.register_forward_hook(
            lambda *args, name=key: counts.__setitem__(name, counts[name] + 1)
        )
    state_before = model_hash(parent)
    root = Path(plan["root"])
    output = root / "output"
    output.mkdir()
    started, model_seconds = time.monotonic(), 0.0
    donors, cases = {}, []
    recipes = {i: scene_recipe(i) for i in plan["sources"]}
    with torch.inference_mode(), ieee_fp32():
        for group in plan["groups"]:
            if psutil.virtual_memory().available < 24 * 2**30:
                raise RuntimeError("Available memory fell below 24 GiB")
            key = group["id"]
            recipe = recipes[group["source"]]
            profile = group["profile"]
            noise = plan["profiles"][profile]
            lookup = f"{profile}-{recipe['source']}"
            if lookup not in donors:
                donors[lookup] = measure_donor(recipe, profile, noise, plan, output)
            donor = donors[lookup]
            arrays, metadata = edge_observation(
                recipe, group["placement"], group["CFA"], group["repeat"], condition=noise
            )
            observed = {k: arrays.pop(k) for k in SENSOR_KEYS}
            sensor = write_array(output / f"{key}-sensor.npz", **observed)
            target = write_array(output / f"{key}-target.npz", **arrays)
            parent.set_noise(noise["shot"], noise["read"])
            begin = time.monotonic()
            image = parent(*(torch.from_numpy(observed[k]) for k in SENSOR_KEYS)).numpy()
            model_seconds += time.monotonic() - begin
            assert (
                image.shape == (3, 3, 512, 512)
                and image.dtype == np.float32
                and np.isfinite(image).all()
            )
            path_out = output / f"{key}-parent.npy"
            with path_out.open("xb") as stream:
                np.save(stream, image, allow_pickle=False)
            proposals, fits = {}, []
            for role in range(plan["parent_batch_size"]):
                values, stats = restore_local_waves(
                    image[role, :, 128:384, 128:384],
                    observed["packed"][role, :, 64:192, 64:192],
                    observed["colors"][role],
                    guide_frequencies_xy=donor["frequencies"],
                    shot=noise["shot"],
                    read=noise["read"],
                    config=config,
                    thresholds=plan["thresholds"],
                    phase_bins=8,
                    shrink_phase_fit=True,
                    compare_pooled_support=True,
                    compare_pooled_refit=True,
                )
                fits.append(stats)
                for (mode, t), value in values.items():
                    if mode in ("pooled-local", "weighted-refit"):
                        name = "fold-average" if mode == "pooled-local" else mode
                        proposals.setdefault(f"{name}-t{t:g}", []).append(value)
            predictions = write_array(
                output / f"{key}-predictions.npz", **{k: np.stack(v) for k, v in proposals.items()}
            )
            row = {
                **group,
                "metadata": metadata,
                "sensor": sensor,
                "target": target,
                "parent": reference(path_out),
                "predictions": predictions,
                "guide_key": lookup,
                "fits": fits,
                "sensor_fingerprints": {k: fingerprint(v) for k, v in observed.items()},
            }
            path_row = output / f"{key}.json"
            write_json(path_row, row)
            cases.append(reference(path_row))
            print(len(cases), key, f"{time.monotonic() - started:.2f}s", flush=True)
    assert state_before == model_hash(parent)
    assert counts == {"root": 32, "DINO": 32} and len(cases) == 32 and len(donors) == 16
    assert not torch.cuda.is_initialized()
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "cases": cases,
            "donors": donors,
            "query_roles": 96,
            "counts": counts,
            "parent_state_unchanged": True,
            "model_seconds": model_seconds,
            "seconds": time.monotonic() - started,
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
