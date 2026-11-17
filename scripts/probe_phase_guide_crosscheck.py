"""Cross-check frequency moves inside each discovery fold and replay retained RAW cases."""

import argparse
import os
import time
from pathlib import Path

import numpy as np
from probe_fresh_phase_refit import write_array

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves


def prepare(root, fresh, older):
    recent, historical = [read_json(p / "plan.json") for p in (fresh, older)]
    recent_receipt = fresh / "output/collection.json"
    stress_receipt = older / "output/collection.json"
    recent_cases, stress_cases = [read_json(p) for p in (recent_receipt, stress_receipt)]
    assert recent_cases["plan"] == reference(fresh / "plan.json")
    assert stress_cases["plan"] == reference(older / "plan.json")
    assert recent["config"] == historical["config"]
    camera_report = fresh / "review/result.json"
    samples = []
    for item, mode in [
        *((v, "near") for v in recent_cases["synthetic"]),
        *((v, "far") for v in stress_cases["synthetic"]),
    ]:
        packed = read_json(checked(item))
        case = packed if mode == "near" else read_json(checked(packed["case"]))
        if case["placement"] == mode:
            samples.append({"arm": mode, "source": item, "id": case["id"]})
    assert sum(v["arm"] == "near" for v in samples) == sum(v["arm"] == "far" for v in samples) == 16
    root.mkdir()
    work, hashes = freeze_sources(
        Path.cwd(), root, [Path(__file__).name, "report_phase_guide_crosscheck.py"]
    )
    write_json(
        root / "plan.json",
        {
            "root": str(root),
            "work": str(work),
            "driver": reference(work / "scripts" / Path(__file__).name),
            "frozen_files": hashes,
            "inputs": [
                reference(p)
                for p in (
                    fresh / "plan.json",
                    older / "plan.json",
                    recent_receipt,
                    stress_receipt,
                    camera_report,
                )
            ],
            "config": recent["config"],
            "profiles": recent["profiles"],
            "settings": recent["settings"],
            "synthetic": samples,
            "camera_report": reference(camera_report),
            "camera_conditions": recent["camera_plan"],
            "scope": "No outcome-based adjustment. Nominal donor, same-side validation on all 16 fresh near groups."
            " The earlier 16 far groups receive their recorded one-bin radial guide error and baseline."
            " Compare with nested bidirectional confirmation of proposed recentering, preserving all observations.",
        },
    )


def restore(parent, packed, colors, guide, noise, config, thresholds, side):
    return restore_local_waves(
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
        phase_guide_crosscheck=True,
        phase_edge_side="validation" if side else None,
    )


def collect(path):
    plan = read_json(path)
    verify_plan(plan)
    assert plan["driver"] == reference(__file__)
    output = Path(plan["root"]) / "output"
    output.mkdir()
    cfg = LocalWaveConfig(**plan["config"])
    records, camera = [], []
    start = time.monotonic()
    for item in plan["synthetic"]:
        control = read_json(checked(item["source"]))
        near = item["arm"] == "near"
        case = control if near else read_json(checked(control["case"]))
        assert case["id"] == item["id"] and near == (case["placement"] == "near")
        old_key = "same-side" if near else "radial-guard8"
        noise = plan["profiles"][case["profile"]]
        old_prediction = case["prediction"] if near else control["output"]
        parent = np.load(checked(case["parent"]))[..., 128:384, 128:384]
        with np.load(checked(case["sensor"])) as data:
            packed, colors = data["packed"][..., 64:192, 64:192], data["colors"]
        thresholds = tuple(
            sorted(
                {
                    v["threshold"]
                    for v in plan["settings"]
                    if (v["profile"], v["placement"]) == (case["profile"], case["placement"])
                }
            )
        )
        stored, fits = {}, []
        for role, before in enumerate(control["fits"][old_key]):
            pred, fit = restore(
                parent[role],
                packed[role],
                colors[role],
                before["guide_frequencies_xy"],
                noise,
                cfg,
                thresholds,
                near,
            )
            for name in ("edges", "guide_search_excluded"):
                np.testing.assert_array_equal(before["records"][0][name], fit["records"][0][name])
            fits.append(fit)
            for t in thresholds:
                stored.setdefault(f"t{t:g}", []).append(pred["weighted-refit", t])
        key = case["id"]
        prediction = write_array(
            output / f"{key}.npz", **{k: np.stack(f) for k, f in stored.items()}
        )
        receipt = output / f"{key}.json"
        write_json(
            receipt,
            {
                "id": key,
                "case": item["source"] if near else control["case"],
                "control": item,
                "control_prediction": old_prediction,
                "control_prefix": old_key,
                "prediction": prediction,
                "fits": fits,
            },
        )
        records.append(reference(receipt))
        print(len(records), key, round(time.monotonic() - start, 3), flush=True)
    previous = read_json(checked(plan["camera_report"]))
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
        values, fit = restore(
            parent, packed, colors, scene["guide"], declaration["noise"], cfg, (2,), True
        )
        prediction = write_array(output / f"{key}.npz", corrected=values["weighted-refit", 2])
        camera.append({"id": key, "prediction": prediction, "fit": fit})
    assert len(records) == 32 and len(camera) == 8
    write_json(
        output / "collection.json",
        {
            "plan": reference(path),
            "synthetic": records,
            "camera": camera,
            "synthetic_fits": len(records) * 3,
            "camera_fits": len(camera),
            "seconds": time.monotonic() - start,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--prepare-from", nargs=2, type=Path)
    arguments = parser.parse_args()
    os.sched_setaffinity(0, [6, 7])
    os.nice(11)
    if arguments.prepare_from:
        prepare(arguments.path.resolve(), *(p.resolve() for p in arguments.prepare_from))
    else:
        collect(arguments.path.resolve())
