"""Prepare and execute a matched full epoch of whole-scene restoration."""

import argparse
import json
import os
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path

import numpy as np
import psutil
from prepare_scene_epoch_corpus import read_catalogue, write_order

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.experiments.runtime import exclusive_run, owner_identity, owner_live


def prepare(repository, root):
    previous = repository / ".cache/experiments/expanded-scene-12000-v2/plan.json"
    corpus_audit = repository / ".cache/experiments/expanded-scene-epoch-corpus-v1/audit.json"
    plan = read_json(previous)
    corpus = read_json(corpus_audit)
    assert plan["train_manifest"] == corpus["train_manifest"]
    rows = read_catalogue(checked(plan["train_manifest"]))
    source_ids = {row["id"] for row in rows}
    assert len(rows) == len(source_ids) == 90_692
    eligible = read_catalogue(checked(corpus["input"]))
    withheld = {row["id"] for row in eligible if row["split"] != "train"}
    development = read_catalogue(checked(plan["development_manifest"]))
    assert len(withheld) == 4_558
    assert not source_ids.intersection(withheld | {row["id"] for row in development})
    assert source_ids <= {row["id"] for row in eligible if row["split"] == "train"}

    root.mkdir(parents=True)
    order_dir = root / "order"
    order_dir.mkdir()
    # The order header still binds the original manifest bytes.
    manifest = order_dir / "manifest-train.jsonl"
    manifest.symlink_to(checked(plan["train_manifest"]))
    seed, steps = 202611180073, 50_000
    order = write_order(manifest, rows, seed=seed, steps=steps, scenes_per_step=2)
    payload = order_dir / "ordinary-photo-order.npy"
    indices = np.load(payload, allow_pickle=False)
    counts = Counter(indices.tolist())
    assert len(set(indices[: len(rows)])) == len(rows)
    assert Counter(counts.values()) == {1: 81_384, 2: 9_308}
    work, files = freeze_sources(repository, root, ["train_scene_context.py"])
    training_script = reference(work / "scripts/train_scene_context.py")
    base_inputs = (
        previous,
        corpus_audit,
        checked(corpus["input"]),
        checked(plan["train_manifest"]),
        checked(plan["development_manifest"]),
        checked(plan["parent"]),
        order,
        payload,
        Path(__file__),
        repository / "scripts/prepare_scene_epoch_corpus.py",
    )
    milestones = sorted({8, 2_000, 12_000, 25_000, 45_346, *range(2_500, steps + 1, 2_500)})
    write_json(
        root / "plan.json",
        plan
        | {
            "root": str(root),
            "work": str(work),
            "frozen_files": files,
            "training_script": training_script,
            "photo_epoch_order": reference(order),
            "inputs": [reference(path) for path in base_inputs],
            "data_seed": seed,
            "steps": steps,
            "phase_stops": milestones,
            "local_contrast_fraction": 0.5,
            "local_flat_core_fraction": 0.25,
            "checkpoint_every": 2_500,
            "log_every": 50,
            "maximum_arm_seconds": 21_600,
            "minimum_start_RAM_GiB": 48,
            "minimum_runtime_RAM_GiB": 32,
            "minimum_disk_GiB": 25,
            "scheduled_counts": {
                "full_epoch_update": 45_346,
                "distinct_photos": len(source_ids),
                "scene_draws_per_arm": len(indices),
                "native_crops_per_arm": len(indices) * 4,
                "first_visit_sources": 81_384,
                "two_visit_sources": 9_308,
                "excluded_canonical_rows": len(withheld),
                "excluded_scene_development": len(development),
            },
            "scientific_primary": "Aligned spatial scene conditioning versus local-only on identical noisy Bayer scenes, with weak and flat local controls embedded in photographed contexts.",
            "scope": "50,000 updates per arm, Corpus 100k EMA, same ordinary Commons source sequence, bin4 targets, frozen DINO, sensor-valid reconstruction. No personal GFX media used for training.",
        },
    )


def run_worker(root, plan, phase, arguments):
    if phase.exists():
        previous_owner = phase / "launch.json"
        if previous_owner.exists() and owner_live(read_json(previous_owner)["child"]):
            raise RuntimeError(f"Earlier worker still owns {phase}")
    phase.mkdir(exist_ok=True)
    attempt = phase / f"attempt-{len(list(phase.glob('attempt-*'))) + 1:02d}"
    attempt.mkdir()
    while (
        psutil.virtual_memory().available < plan["minimum_start_RAM_GiB"] * 2**30
        or shutil.disk_usage(root).free < plan["minimum_disk_GiB"] * 2**30
    ):
        write_json(root / "status.json", {"waiting_for_resources": str(attempt)}, replace=True)
        time.sleep(30)
    work = Path(plan["work"])
    command = [
        plan["python"],
        str(checked(plan["training_script"])),
        arguments[0],
        str(root / "plan.json"),
        str(attempt / "work"),
        *arguments[1:],
    ]
    env = os.environ | {
        "PYTHONPATH": f"{work}/src:{work}/scripts",
        "PYTHONUNBUFFERED": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "2",
        "MKL_NUM_THREADS": "2",
    }
    with (attempt / "worker.log").open("xb") as output:
        process = subprocess.Popen(command, env=env, stdout=output, stderr=subprocess.STDOUT)
        child = {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}
        launch = {
            "child": child,
            "controller": owner_identity(),
            "command": command,
            "attempt": str(attempt),
        }
        write_json(phase / "launch.json", launch, replace=True)
        write_json(attempt / "launch.json", launch)
        write_json(root / "status.json", launch, replace=True)
        status = process.wait()
    write_json(attempt / "exit.json", {"returncode": status})
    if status:
        raise subprocess.CalledProcessError(status, command)
    return attempt / "work"


def phase_audit(receipt, binding, mode, first, stop, dataset):
    data = read_json(receipt)
    assert data["mode"] == mode and data["plan"] == binding and data["DINO_unchanged"]
    assert (data["start_step_exclusive"], data["steps"], data["schedule_steps"]) == (
        first,
        stop,
        50_000,
    )
    kinds = Counter()
    noise_seeds = set()
    with checked(data["observations"]).open() as observations:
        for index, line in zip(range(first * 2, stop * 2), observations, strict=True):
            row = json.loads(line)
            assert row["index"] == index and row["source_id"] == dataset.source_row(index)["id"]
            noise_seeds.add(row["recipe"]["noise_seed"])
            contrast = row.get("local_contrast")
            kinds[
                "plain"
                if contrast is None
                else "flat"
                if contrast.get("exact_flat_core")
                else "weak"
            ] += 1
    assert len(noise_seeds) == (stop - first) * 2
    return {
        "receipt": reference(receipt),
        "observations": data["observations"],
        "scene_types": dict(kinds),
        "checkpoint": reference(checked(data["checkpoints"][-1])),
        "training_seconds": data["seconds"],
        "reader_and_cpu_fingerprints_seconds": data["data_seconds"],
        "checkpoint_seconds": data["checkpoint_seconds"],
    }


def run(root):
    from train_scene_context import training_dataset

    with exclusive_run(root):
        binding = reference(root / "plan.json")
        plan = read_json(checked(binding))
        verify_plan(plan)
        dataset = training_dataset(plan)
        qualified = root / "qualified.json"
        if not qualified.exists():
            result = run_worker(root, plan, root / "preflight", ["preflight"]) / "result.json"
            preflight = read_json(result)
            left, right = preflight["results"]
            assert preflight["all_modes_passed"] and preflight["plan"] == binding
            assert left["training_observations"] == right["training_observations"]
            rows = left["training_observations"]
            assert [row["index"] for row in rows] == [0, 1, 2, 3]
            assert rows[0]["local_contrast"]["exact_flat_core"]
            assert 0 < rows[1]["local_contrast"]["scale"] < 1 and "local_contrast" not in rows[2]
            write_json(qualified, {"preflight": reference(result), "plan": binding})
        previous = {mode: None for mode in plan["modes"]}
        first = 0
        for stop in plan["phase_stops"]:
            summaries = {}
            for mode in plan["modes"]:
                phase = root / f"{mode}-{stop:06d}"
                verified = phase / "verified.json"
                if verified.exists():
                    summary = read_json(verified)
                else:
                    arguments = ["train", "--mode", mode, "--stop-step", str(stop)]
                    if previous[mode] is not None:
                        arguments += ["--resume-receipt", str(checked(previous[mode]))]
                    work = run_worker(root, plan, phase, arguments)
                    summary = phase_audit(
                        work / "completed.json", binding, mode, first, stop, dataset
                    )
                    write_json(verified, summary)
                previous[mode] = summary["receipt"]
                summaries[mode] = summary
            local, spatial = (summaries[mode] for mode in plan["modes"])
            assert local["observations"]["sha256"] == spatial["observations"]["sha256"]
            matched = root / f"matched-{stop:06d}.json"
            if not matched.exists():
                write_json(
                    matched,
                    {
                        "plan": binding,
                        "matched_input_traces": True,
                        "first_step_exclusive": first,
                        "through_update": stop,
                        "arms": summaries,
                        "training_complete": stop == plan["steps"],
                        "numerical_review_complete": False,
                        "native_review_complete": False,
                    },
                )
            first = stop
        write_json(
            root / "status.json", {"training_complete": True, "through_update": first}, replace=True
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "run"))
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    if args.operation == "prepare":
        prepare(Path.cwd(), args.root.resolve())
    else:
        run(args.root.resolve())
