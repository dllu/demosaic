"""Compare planar and locally varying RAW phase on fresh weak-wire observations."""

import argparse
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

DRIFTS = {
    80: ((4, 0), (-8, 0)),
    81: ((-8, 0), (4, 0)),
    82: ((8, 0), (8, 0)),
    83: ((0, -8), (0, 4)),
    84: ((0, 8), (0, -8)),
    85: ((0, 4), (0, 8)),
    86: ((0, 0), (0, 0)),
    87: ((0, 0), (0, 0)),
}
ARMS = {"planar": False, "drift": True}
ROI = np.s_[..., 128:384, 128:384]


def prepare(root, previous):
    old_path = previous / "plan.json"
    old = read_json(old_path)
    camera_path = previous / "review/result.json"
    assert read_json(camera_path)["plan"] == reference(old_path)
    asymmetric_path = previous.parent / "asymmetric-phase-evidence-v1/plan.json"
    assert reference(asymmetric_path) in old["inputs"]
    asymmetric = read_json(asymmetric_path)
    assert not set(DRIFTS).intersection(asymmetric["sources"])
    root.mkdir()
    work, hashes = freeze_sources(Path.cwd(), root, [Path(__file__).name, "report_phase_drift.py"])
    groups = [
        {
            "id": f"{profile}-source{source}-{place}-{PATTERNS[i % 4]}",
            "profile": profile,
            "source": source,
            "placement": place,
            "CFA": PATTERNS[i % 4],
            "repeat": 7821,
            "drifts": DRIFTS[source],
            "kind": "straight" if i >= 6 else "spacing" if i < 3 else "curved",
        }
        for profile, (i, source), place in product(PROFILES, enumerate(DRIFTS), ("near", "far"))
    ]
    inherited = {
        k: asymmetric[k]
        for k in ("parent", "profiles", "guide_config", "guide_half_threshold_each_fold")
    }
    write_json(
        root / "plan.json",
        {
            **inherited,
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": hashes,
            "inputs": [
                reference(old_path),
                reference(camera_path),
                reference(asymmetric_path),
                old["camera_conditions"],
                asymmetric["parent"],
            ],
            "config": old["config"],
            "donor_repeat": 7822,
            "groups": groups,
            "settings": old["settings"],
            "camera_baseline": reference(camera_path),
            "camera_conditions": old["camera_conditions"],
            "arms": ARMS,
            "scope": "Fresh sources 80–87, 32 groups and independent noise in all three roles; straight "
            "disjoint donors. Same V143 EMA, donor, guarded cross-checked recenter, local support, "
            "phase basis and weighted refit in both arms. Eight retained GFX queries compose V120 "
            "with the same guarded fit at threshold 2.",
        },
    )


def restore(parent, packed, colors, guide, noise, cfg, thresholds, near, drift):
    outputs, diagnostics = restore_local_waves(
        parent,
        packed,
        colors,
        shot=noise["shot"],
        read=noise["read"],
        config=cfg,
        thresholds=thresholds,
        guide_frequencies_xy=guide,
        phase_bins=8,
        shrink_phase_fit=True,
        compare_pooled_support=True,
        compare_pooled_refit=True,
        recenter_phase_guides=True,
        phase_guide_edge_guard_px=8,
        phase_guide_crosscheck=True,
        phase_drift_search=drift,
        phase_edge_side="validation" if near else None,
    )
    return {t: outputs["weighted-refit", t] for t in thresholds}, diagnostics


def collect(path):
    import torch
    from profile_raw_kernel_inference import model_hash

    from demosaic.experiments.data.edge_response import edge_observation, scene_recipe
    from demosaic.inference import load_checkpoint
    from demosaic.precision import ieee_fp32
    from demosaic.prediction_archive import fingerprint

    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__) and plan["arms"] == ARMS
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    model, state = load_checkpoint(checked(plan["parent"]), "cpu")
    assert state["step"] == plan["parent"]["step"]
    assert state["loaded_sha256"] == plan["parent"]["sha256"]
    assert all(torch.equal(v, state["ema"][k]) for k, v in model.restoration_state_dict().items())
    del state
    model.eval().requires_grad_(False).to(memory_format=torch.contiguous_format)
    before = model_hash(model)
    cfg = LocalWaveConfig(**plan["config"])
    output = Path(plan["root"]) / "output"
    output.mkdir()
    started, model_seconds = time.monotonic(), 0.0
    donors, observations, cameras = {}, [], []
    with torch.inference_mode(), ieee_fp32():
        for group in plan["groups"]:
            if psutil.virtual_memory().available < 24 * 2**30:
                raise RuntimeError("Available memory fell below 24 GiB")
            key, profile = group["id"], group["profile"]
            noise = plan["profiles"][profile]
            recipe = scene_recipe(group["source"])
            donor_id = f"{profile}-{group['source']}"
            if donor_id not in donors:
                donors[donor_id] = measure_donor(recipe, profile, noise, plan, output)
            guide = donors[donor_id]["frequencies"]
            data, meta = edge_observation(
                recipe | {"phase_drifts": group["drifts"]},
                group["placement"],
                group["CFA"],
                group["repeat"],
                condition=noise,
            )
            observed = {k: data.pop(k) for k in SENSOR_KEYS}
            sensor = write_array(output / f"{key}-sensor.npz", **observed)
            target = write_array(output / f"{key}-target.npz", **data)
            model.set_noise(noise["shot"], noise["read"])
            begin_model = time.monotonic()
            parent = model(*(torch.from_numpy(observed[k]) for k in SENSOR_KEYS)).numpy()
            model_seconds += time.monotonic() - begin_model
            assert parent.shape == (3, 3, 512, 512) and np.isfinite(parent).all()
            parent_path = output / f"{key}-parent.npy"
            with parent_path.open("xb") as file:
                np.save(file, parent, allow_pickle=False)
            thresholds = tuple(
                sorted(
                    {
                        s["threshold"]
                        for s in plan["settings"]
                        if (s["profile"], s["placement"]) == (profile, group["placement"])
                    }
                )
            )
            predictions, fits = {}, {}
            for label, drift in ARMS.items():
                fits[label] = []
                for role in range(3):
                    values, diagnostics = restore(
                        parent[role][ROI],
                        observed["packed"][role, :, 64:192, 64:192],
                        observed["colors"][role],
                        guide,
                        noise,
                        cfg,
                        thresholds,
                        group["placement"] == "near",
                        drift,
                    )
                    fits[label].append(diagnostics)
                    for t, value in values.items():
                        predictions.setdefault(f"{label}--t{t:g}", []).append(value)
            case = output / f"{key}.json"
            write_json(
                case,
                {
                    **group,
                    "metadata": meta,
                    "sensor": sensor,
                    "target": target,
                    "parent": reference(parent_path),
                    "guide_key": donor_id,
                    "prediction": write_array(
                        output / f"{key}-predictions.npz",
                        **{k: np.stack(v) for k, v in predictions.items()},
                    ),
                    "fits": fits,
                    "sensor_fingerprints": {k: fingerprint(v) for k, v in observed.items()},
                },
            )
            observations.append(reference(case))
            print(len(observations), key, round(time.monotonic() - started, 2), flush=True)
    assert model_hash(model) == before
    previous = read_json(checked(plan["camera_baseline"]))
    conditions = read_json(checked(plan["camera_conditions"]))
    for board, declaration in zip(previous["camera"], conditions["camera"], strict=True):
        key = board["id"]
        assert key == declaration["board"]["id"]
        scene = board["source"]
        x, y, w, h = scene["query_box"]
        parent = np.load(checked(scene["parent_prediction"]), mmap_mode="r")[
            0, :, y : y + h, x : x + w
        ]
        with np.load(checked(scene["query_arrays"])) as data:
            packed = data["packed"][0, :, y // 2 : (y + h) // 2, x // 2 : (x + w) // 2]
            colors = data["colors"][0]
        common = (parent, packed, colors, scene["guide"], declaration["noise"], cfg, (2,), True)
        planar, _ = restore(*common, False)
        with np.load(checked(board["crosscheck_prediction"])) as old:
            np.testing.assert_array_equal(planar[2], old["corrected"])
        changed, fit = restore(*common, True)
        cameras.append(
            {
                "id": key,
                "prediction": write_array(output / f"{key}.npz", corrected=changed[2]),
                "fit": fit,
            }
        )
    assert len(observations) == 32 and len(cameras) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": observations,
            "camera": cameras,
            "donors": donors,
            "model_sha256": before,
            "synthetic_parent_forwards": len(observations),
            "seconds": time.monotonic() - started,
            "model_seconds": model_seconds,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", type=Path)
    args = parser.parse_args()
    if args.prepare_from:
        prepare(args.path.resolve(), args.prepare_from.resolve())
    else:
        collect(args.path.resolve())
