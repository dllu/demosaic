"""Input-only local wave replacement on fixed finite-wire/material/GFX inputs."""

import argparse
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").is_file())


def checked_adoption(binding, parent, packed, colors, methods):
    from demosaic.prediction_archive import fingerprint

    record = read_json(checked(binding))
    for key, value in [
        ("parent_values", parent),
        ("packed_values", packed),
        ("colors_values", colors),
    ]:
        if record[key] != fingerprint(value):
            raise ValueError("Adopted analytic prediction inputs differ")
    predictions = {name: record["predictions"][name] for name in methods}
    for item in predictions.values():
        value = np.load(checked(item), allow_pickle=False, mmap_mode="r")
        if (
            value.shape != parent.shape
            or value.dtype != parent.dtype
            or not np.isfinite(value).all()
        ):
            raise ValueError("Adopted native prediction shape/dtype/values differ")
    return predictions, record["aux"]


def prepare(root):
    from demosaic.local_validated_waves import LocalWaveConfig

    cache_path = REPO / ".cache/experiments/near-edge-response-iso400-v1/cache.json"
    cache = read_json(cache_path)
    queue_path = REPO / ".cache/experiments/raw-spatial-endpoint-review-v3/queue-plan.json"
    queue = read_json(queue_path)
    rows, groups = [], []
    for item in cache["rows"]:
        meta = item["metadata"]
        if (
            meta["recipe"]["source"] not in [0, 1]
            or meta["pattern"] != "RGGB"
            or meta["repeat"] != 0
        ):
            continue
        ids = []
        for role in range(3):
            case = f"source{meta['recipe']['source']}-{meta['placement']}-role{role}"
            ids.append(case)
            rows.append(
                {
                    "id": case,
                    "kind": "finite-wire",
                    "arrays": item["arrays"],
                    "parent": item["parent"],
                    "sample": role,
                    "noise": meta["noise"],
                    "metadata": meta,
                    "reference_role": "Exact constructed finite-wire RGB GT",
                    "ROI_xywh": [176, 176, 160, 160],
                    "display_exposure": 2.0,
                }
            )
        groups.append(
            {"index": item["index"], "cases": ids, "arrays": item["arrays"], "metadata": meta}
        )
    wanted = {
        "bark-RGGB-draw0",
        "raccoon-fur-RGGB-draw0",
        "bark-contrast0p025-adc-RGGB",
        "raccoon-fur-contrast0p025-adc-RGGB",
        "pixls-5002-fine-contrast0p025-adc-RGGB",
        "pixls-1951-field-contrast0p025-adc-RGGB",
    }
    for observation in queue["observations"]:
        if observation["id"] not in wanted and observation["kind"] not in ["gfx", "mesh"]:
            continue
        control = observation["controls"]
        if len(control) != 1:
            raise ValueError("Require the original single V120 saved control")
        rows.append(
            {
                "id": observation["id"],
                "kind": observation["kind"],
                "arrays": observation["arrays"],
                "parent": control[0]["prediction"],
                "sample": 0,
                "noise": observation["noise"],
                "reference_role": observation["reference_role"],
                "ROI_xywh": observation.get("ROI_xywh"),
                "display_exposure": observation["display_exposure"],
                "observation": observation,
            }
        )
    if len(groups) != 4 or len(rows) != 24 or len({r["id"] for r in rows}) != 24:
        raise ValueError(
            f"Fixed pilot coverage differs: {len(groups)} wire groups/{len(rows)} cases"
        )
    root.mkdir(parents=True, exist_ok=False)
    work, files = freeze_sources(REPO, root)
    script = work / "scripts" / Path(__file__).name
    script.parent.mkdir()
    shutil.copyfile(__file__, script)
    files[str(script)] = reference(script)["sha256"]
    config = LocalWaveConfig().to_dict()
    identity_path = root / "analytic-model.json"
    write_json(
        identity_path,
        {
            "kind": "Input-only local validated wave replacement, no trained weights",
            "config": config,
            "thresholds": [0, 2, 4],
            "modes": ["global", "local"],
            "parent_checkpoint_sha256": "a9d9b6b4f974e24a6b11e5e740aab32314233a7f53c056cf37c7d2aac1c589fb",
            "source": reference(work / "src/demosaic/local_validated_waves.py"),
            "score_interpretation": "Empirical plug-in predictive scores; thresholds fixed before pilot and not calibration-risk guarantees.",
        },
    )
    inputs = [reference(cache_path), reference(queue_path), reference(identity_path)]
    inputs += [r[k] for r in rows for k in ["arrays", "parent"]]
    plan = {
        "root": str(root),
        "work": str(work),
        "script": reference(script),
        "python": sys.executable,
        "model": reference(identity_path),
        "config": config,
        "thresholds": [0, 2, 4],
        "modes": ["global", "local"],
        "rows": rows,
        "finite_groups": groups,
        "minimum_RAM_GiB": 32,
        "minimum_disk_GiB": 96,
        "maximum_prediction_seconds": 1800,
        "inputs": list({(b["path"], b["sha256"]): b for b in inputs}.values()),
        "frozen_files": files,
        "scope": "Fixed first-two-source RGGB/repeat0 finite-wire near/far400 pilot, ordinary exact-target bark/fur, all4 faint-ADC RGGB materials, both protected GFX families/all4 main contexts/both cab profiles and ROIs/JPEG metadata. Reuse V120 predictions, no neural model/DINO/noise/source/RAW work. Raw-only discovery/conditional validation and per-color scores, then replace parent wave projection. Full256 discovery/129 local validation, two-fold CFA split, fixed thresholds0/2/4, matched global/local support comparison from identical candidates. All24 input-only outputs close before target/reference loading. This pilot is development evidence, not broad/independent model-quality promotion or calibrated confidence.",
    }
    write_json(root / "plan.json", plan)
    verify_plan(plan)
    return root / "plan.json"


def predict(root):
    import psutil

    from demosaic.experiments.runtime import owner_identity
    from demosaic.local_validated_waves import LocalWaveConfig, restore_local_waves
    from demosaic.prediction_archive import fingerprint

    plan = read_json(root / "plan.json")
    verify_plan(plan)
    if reference(__file__) != plan["script"] or "torch" in sys.modules:
        raise RuntimeError("Require the frozen NumPy-only source")
    (root / "predict.claim").open("x").close()
    write_json(root / "owner.json", owner_identity())
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    output = root / "predictions"
    output.mkdir()
    records, began = [], time.monotonic()
    try:
        for row in plan["rows"]:
            if (
                psutil.virtual_memory().available < plan["minimum_RAM_GiB"] * 2**30
                or shutil.disk_usage(root).free < plan["minimum_disk_GiB"] * 2**30
            ):
                raise RuntimeError("CPU pilot resource reserve unavailable")
            if time.monotonic() - began > plan["maximum_prediction_seconds"]:
                raise TimeoutError("CPU pilot inference budget reached")
            with np.load(checked(row["arrays"]), allow_pickle=False) as z:
                packed, colors = z["packed"][row["sample"]], z["colors"][row["sample"]]
            parent = np.load(checked(row["parent"]), allow_pickle=False)[row["sample"]]
            if parent.ndim != 3 or parent.shape[0] != 3:
                raise ValueError("Expected saved native V120 camera RGB")
            adoption = plan.get("adoptions", {}).get(row["id"])
            if adoption is not None:
                methods = [
                    f"{mode}-t{float(t):g}" for mode in plan["modes"] for t in plan["thresholds"]
                ]
                predictions, aux = checked_adoption(adoption, parent, packed, colors, methods)
            else:
                results, aux = restore_local_waves(
                    parent,
                    packed,
                    colors,
                    shot=row["noise"]["shot"],
                    read=row["noise"]["read"],
                    thresholds=tuple(plan["thresholds"]),
                    config=LocalWaveConfig(**plan["config"]),
                )
                predictions = {}
                for (mode, threshold), value in results.items():
                    name = f"{mode}-t{threshold:g}"
                    path = output / f"{row['id']}-{name}.npy"
                    with path.open("xb") as stream:
                        np.save(stream, value, allow_pickle=False)
                    predictions[name] = reference(path)
                    if aux["identity_zero_noise"] and not np.array_equal(value, parent):
                        raise ValueError("ADC-only control changed")
            record = {
                "id": row["id"],
                "predictions": predictions,
                "parent_values": fingerprint(parent),
                "packed_values": fingerprint(packed),
                "colors_values": fingerprint(colors),
                "aux": aux,
                "adopted_from": adoption,
            }
            write_json(output / (row["id"] + "-receipt.json"), record)
            records.append(record)
            write_json(
                root / "progress.json",
                {
                    "owner": owner_identity(),
                    "completed_cases": len(records),
                    "expected_cases": len(plan["rows"]),
                    "last_case": row["id"],
                    "elapsed_seconds": time.monotonic() - began,
                },
                replace=True,
            )
            print(
                len(records),
                "of",
                len(plan["rows"]),
                row["id"],
                aux["patches"],
                "patches",
                flush=True,
            )
        verify_plan(plan)
        if "torch" in sys.modules:
            raise RuntimeError("Pilot prediction imported Torch")
        write_json(
            root / "collection.json",
            {
                "status": "all-declared-input-only-local-wave-outputs-closed-before-GT",
                "plan": reference(root / "plan.json"),
                "model": plan["model"],
                "rows": records,
                "target_or_reference_arrays_loaded": 0,
                "new_neural_forwards": 0,
                "new_source_noise_draws": 0,
                "RAW_decodes": 0,
                "optimizer_steps": 0,
                "Torch_imported": False,
                "elapsed_seconds": time.monotonic() - began,
            },
        )
    except BaseException as error:
        write_json(
            root / "failure.json",
            {
                "error": repr(error),
                "completed_cases": len(records),
                "scope": "Failed CPU pilot preserved; no automatic retry or training signals.",
            },
        )
        raise


def score(root):
    from demosaic.experiments.evaluation.edge_response import measure

    plan = read_json(root / "plan.json")
    collection = read_json(root / "collection.json")
    if collection["plan"] != reference(root / "plan.json") or len(collection["rows"]) != len(
        plan["rows"]
    ):
        raise ValueError("Require all declared input-only predictions before target access")
    by_id = {r["id"]: r for r in collection["rows"]}
    methods = ["V120", *by_id[plan["rows"][0]["id"]]["predictions"]]
    metrics = []
    for group in plan["finite_groups"]:
        with np.load(checked(group["arrays"]), allow_pickle=False) as z:
            arrays = {k: z[k] for k in ["target", "quiet", "edge_band"]}
        parent = next(r["parent"] for r in plan["rows"] if r["id"] == group["cases"][0])
        for method in methods:
            if method == "V120":
                value = np.load(checked(parent), allow_pickle=False)
            else:
                value = np.stack(
                    [
                        np.load(checked(by_id[case]["predictions"][method]), allow_pickle=False)
                        for case in group["cases"]
                    ]
                )
            metrics.append(
                {
                    "profile": group.get("profile", "iso400"),
                    "source": group["metadata"]["recipe"]["source"],
                    "placement": group["metadata"]["placement"],
                    "method": method,
                    **measure(arrays, value),
                }
            )
    write_json(
        root / "finite-scores.json",
        {
            "status": "completed-fixed-input-only-finite-wire-pilot",
            "collection": reference(root / "collection.json"),
            "rows": metrics,
            "scope": "Only2 source geometries, RGGB/repeat0, near/far400; fixed descriptive threshold sweep, no risk calibration. Real references never scored. Full cohort review remains separate.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "predict", "score"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"prepare": lambda p: print(prepare(p)), "predict": predict, "score": score}[args.mode](
        args.root.resolve()
    )
