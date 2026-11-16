"""Matched H1 versus phase-conditioned measurement averaging, three noise priors."""

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


def prepare(root):
    from demosaic.local_validated_waves import LocalWaveConfig
    from demosaic.phase_aggregation import PhaseAggregateConfig

    original = REPO / ".cache/experiments/local-validated-wave-panel-v1"
    pilot = REPO / ".cache/experiments/local-wave-shapes-pilot-v1/matching"
    full, old = read_json(original / "plan.json"), read_json(pilot / "plan.json")
    model = read_json(original / "analytic-model-v2.json")
    binding = model["parent_bindings_by_domain"]["finite-wire"]
    for prior in binding["priors"].values():
        assert (
            prior["parent"]["sha256"]
            == "96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4"
        )
        checked(prior["source_plan"])
    groups = [
        group
        for group in full["finite_groups"]
        if group["metadata"]["recipe"]["source"] in (0, 1)
        and group["metadata"]["pattern"] == "RGGB"
        and group["metadata"]["repeat"] == 0
    ]
    ids = {case for group in groups for case in group["cases"]}
    rows = [
        dict(row, ROI_xywh=[176, 176, 160, 160], display_exposure=2.0)
        for row in full["rows"]
        if row["id"] in ids
    ] + [row for row in old["rows"] if row["kind"] != "finite-wire"]
    assert len(groups) == 12 and len(rows) == 48 and len({r["id"] for r in rows}) == 48
    root.mkdir(parents=True, exist_ok=False)
    work, files = freeze_sources(
        REPO,
        root,
        entries=(
            "pilot_phase_aggregation.py",
            "report_local_validated_waves.py",
            "audit_local_wave_pilot.py",
            "report_checkpoint_pilot.py",
            "audit_checkpoint_pilot.py",
        ),
    )
    geometry, aggregation = LocalWaveConfig().to_dict(), PhaseAggregateConfig().to_dict()
    analytic = {
        "kind": "Input-only phase-conditioned measurement averaging, no trained weights",
        "geometry": geometry,
        "aggregation": aggregation,
        "thresholds": [0, 2, 4],
        "source": reference(work / "src/demosaic/phase_aggregation.py"),
        "shared_geometry_source": reference(work / "src/demosaic/local_validated_waves.py"),
        "parents": model["parent_bindings_by_domain"],
        "scope": "Two separate normalized nonnegative averages form a signed detail operator. Per-color, per-direction empirical held-out scores, not calibrated confidence or convex delivered RGB. Matched current-cardinality H1 control uses identical discovery fits and observations. Parent used only after scoring; no GT/reference access in prediction.",
    }
    write_json(root / "analytic-model.json", analytic)
    inputs = [
        reference(original / "plan.json"),
        reference(original / "analytic-model-v2.json"),
        reference(pilot / "plan.json"),
        reference(root / "analytic-model.json"),
    ]
    inputs += [r[k] for r in rows for k in ("arrays", "parent")]
    plan = {
        "root": str(root),
        "work": str(work),
        "script": reference(work / "scripts/pilot_phase_aggregation.py"),
        "model": reference(root / "analytic-model.json"),
        "geometry_config": geometry,
        "aggregation_config": aggregation,
        "thresholds": [0, 2, 4],
        "modes": ["H1-global", "H1-local", "global", "local"],
        "rows": rows,
        "finite_groups": groups,
        "frozen_files": files,
        "inputs": list({(x["path"], x["sha256"]): x for x in inputs}.values()),
        "minimum_RAM_GiB": 32,
        "minimum_disk_GiB": 96,
        "maximum_prediction_seconds": 3600,
        "scope": "Fixed two-geometry/RGGB/repeat0 near/far development panel across400/1600/6400,36 finite-role images plus12 original material/GFX contexts. Both protected GFX families, both cab profiles/ROIs/JPEG metadata retained. Identical RAW-only discovery fits for H1 and aggregation, primary localt2, fixed threshold sweep0/2/4 and global/local controls. Close all48 input-only outputs before scoring. No NN/DINO/source/noise/RAW/optimizer work. Reused adaptive development sources, not blind generalization or a broad camera-quality result.",
    }
    write_json(root / "plan.json", plan)
    verify_plan(plan)
    return root / "plan.json"


def predict(root):
    import psutil

    from demosaic.experiments.runtime import owner_identity
    from demosaic.local_validated_waves import LocalWaveConfig
    from demosaic.phase_aggregation import PhaseAggregateConfig, restore_phase_aggregation
    from demosaic.prediction_archive import fingerprint

    plan = read_json(root / "plan.json")
    verify_plan(plan)
    assert reference(__file__) == plan["script"] and "torch" not in sys.modules
    (root / "predict.claim").open("x").close()
    write_json(root / "owner.json", owner_identity())
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    output = root / "predictions"
    output.mkdir()
    began, records = time.monotonic(), []
    for row in plan["rows"]:
        if (
            psutil.virtual_memory().available < plan["minimum_RAM_GiB"] * 2**30
            or shutil.disk_usage(root).free < plan["minimum_disk_GiB"] * 2**30
        ):
            raise RuntimeError("CPU pilot resource reserve unavailable")
        if time.monotonic() - began > plan["maximum_prediction_seconds"]:
            raise TimeoutError("Declared analytic prediction deadline reached")
        with np.load(checked(row["arrays"]), allow_pickle=False) as z:
            packed, colors = z["packed"][row["sample"]], z["colors"][row["sample"]]
        parent = np.load(checked(row["parent"]), allow_pickle=False)[row["sample"]]
        values, aux = restore_phase_aggregation(
            parent,
            packed,
            colors,
            shot=row["noise"]["shot"],
            read=row["noise"]["read"],
            thresholds=tuple(plan["thresholds"]),
            geometry_config=LocalWaveConfig(**plan["geometry_config"]),
            aggregation_config=PhaseAggregateConfig(**plan["aggregation_config"]),
        )
        predictions = {}
        for (mode, threshold), value in values.items():
            name = f"{mode}-t{threshold:g}"
            path = output / f"{row['id']}-{name}.npy"
            with path.open("xb") as handle:
                np.save(handle, value, allow_pickle=False)
            predictions[name] = reference(path)
            if aux["identity_zero_noise"]:
                assert np.array_equal(value, parent)
        record = {
            "id": row["id"],
            "predictions": predictions,
            "parent_values": fingerprint(parent),
            "packed_values": fingerprint(packed),
            "colors_values": fingerprint(colors),
            "aux": aux,
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
            len(records), "of", len(plan["rows"]), row["id"], aux["patches"], "patches", flush=True
        )
    verify_plan(plan)
    assert "torch" not in sys.modules
    write_json(
        root / "collection.json",
        {
            "plan": reference(root / "plan.json"),
            "model": plan["model"],
            "rows": records,
            "elapsed_seconds": time.monotonic() - began,
            "target_or_reference_arrays_loaded": 0,
            "new_neural_forwards": 0,
            "RAW_decodes": 0,
            "optimizer_steps": 0,
            "Torch_imported": False,
            "status": "all48-input-only-aggregation-and-H1-outputs-closed-before-GT",
        },
    )


def score(root):
    from demosaic.experiments.evaluation.edge_response import measure

    plan, collection = read_json(root / "plan.json"), read_json(root / "collection.json")
    assert collection["plan"] == reference(root / "plan.json")
    assert len(collection["rows"]) == len(plan["rows"])
    records = {r["id"]: r for r in collection["rows"]}
    methods = ["V143", *records[plan["rows"][0]["id"]]["predictions"]]
    metrics = []
    for group in plan["finite_groups"]:
        with np.load(checked(group["arrays"]), allow_pickle=False) as z:
            arrays = {k: z[k] for k in ("target", "quiet", "edge_band")}
        parent = next(r["parent"] for r in plan["rows"] if r["id"] == group["cases"][0])
        for method in methods:
            value = (
                np.load(checked(parent), allow_pickle=False)
                if method == "V143"
                else np.stack(
                    [
                        np.load(checked(records[case]["predictions"][method]), allow_pickle=False)
                        for case in group["cases"]
                    ]
                )
            )
            metrics.append(
                {
                    "profile": group["profile"],
                    "source": group["metadata"]["recipe"]["source"],
                    "placement": group["metadata"]["placement"],
                    "method": method,
                    **measure(arrays, value),
                }
            )
    write_json(
        root / "finite-scores.json",
        {
            "collection": reference(root / "collection.json"),
            "rows": metrics,
            "scope": plan["scope"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "predict", "score"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    {"prepare": lambda p: print(prepare(p)), "predict": predict, "score": score}[args.mode](
        args.root.resolve()
    )
