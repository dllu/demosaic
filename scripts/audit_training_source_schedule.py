"""Count scheduled photograph identities, stopping the real reader before pixels.

This is a source-selection audit, not a training or clean-target replay. A frozen
plan supplies recipe/source/trace hashes. Independent Python selection must agree
with the actual reader, including the complete local RNG state at the stop.
"""

import argparse
import ast
import csv
import hashlib
import inspect
import json
import math
import os
import random
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import numpy as np
import torch
import yaml

import demosaic.data as data_module
from demosaic.data import CleanDataset
from demosaic.train import training_domain


def read(path):
    return json.loads(Path(path).read_text())


def reference(path):
    path = Path(path).resolve()
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def guard(plan):
    for ref in plan["frozen_files"]:
        if reference(ref["path"]) != ref:
            raise ValueError(f"Changed frozen audit input: {ref['path']}")


def definition(path, name):
    node = next(
        n for n in ast.parse(Path(path).read_text()).body if getattr(n, "name", None) == name
    )
    return ast.dump(node, include_attributes=False)


class SelectionStop(Exception):
    def __init__(self, caller, family):
        assert caller.f_code is CleanDataset.__getitem__.__code__
        values = caller.f_locals
        region = values.get("region")
        self.row = {
            "index": values["index"],
            "family": family,
            "source_id": values["record"]["id"] if family == "photographic" else "",
            "reviewed": region is not None,
        }
        self.rng_state = values["rng"].getstate()


def stop_photo(*args, **kwargs):
    raise SelectionStop(inspect.currentframe().f_back, "photographic")


def stop_family(family):
    def stop(*args, **kwargs):
        selected = "fine-weak-texture" if kwargs.get("frequency_profile") == "fine-v1" else family
        raise SelectionStop(inspect.currentframe().f_back, selected)

    return stop


def forbidden(*args, **kwargs):
    raise AssertionError("Neural execution is forbidden in a source-selection audit")


def summarize(counts, visits, ordinary, reviewed, available):
    total_photos = sum(visits.values())
    entropy = -sum((n / total_photos) * math.log(n / total_photos) for n in visits.values())
    histogram = Counter(visits.values())
    histogram[0] = available - len(visits)
    return {
        "families": dict(sorted(counts.items())),
        "photographic_draws": total_photos,
        "reviewed_draws": sum(reviewed.values()),
        "ordinary_draws": sum(ordinary.values()),
        "unique_photographic_sources": len(visits),
        "unique_ordinary_sources": len(ordinary),
        "unique_reviewed_sources": len(reviewed),
        "available_training_sources": available,
        "source_coverage_percent": 100 * len(visits) / available,
        "source_identity_entropy_effective_count": math.exp(entropy),
        "visits_histogram_including_unvisited": dict(sorted(histogram.items())),
        "reviewed_visits_by_source": dict(sorted(reviewed.items())),
        "ordinary_max_visits": max(ordinary.values(), default=0),
        "reviewed_min_max_visits": [min(reviewed.values()), max(reviewed.values())]
        if reviewed
        else [],
    }


def audit_recipe(recipe, plan, output):
    config = yaml.safe_load(Path(recipe["config"]).read_text())
    label = recipe["label"]
    assert config["steps"] == 20000 and config["batch_size"] == 16
    assert config.get("optimizer_batch_groups", 1) == 1
    assert config["augmentation_downsample"] == 2
    source_root = Path(recipe["executed_source_root"])
    functions = {
        "data.py": ["CleanDataset"],
        "photo_sampling.py": ["PhotoSamplingReference"],
        "reviewed_rois.py": ["ReviewedPhotoROIs"],
        "train.py": ["training_domain", "domain_indices"],
        "paired_training.py": ["paired_step"],
        "raw_clean.py": ["raw_clean_step"],
    }
    for filename, names in functions.items():
        for name in names:
            assert definition(source_root / filename, name) == definition(
                Path(data_module.__file__).parent / filename, name
            ), (label, filename, name)

    keys = [
        "patch_size",
        "synthetic_fraction",
        "seed",
        "flat_fraction",
        "augmentation_downsample",
        "weak_texture_fraction",
        "flat_chroma_stops",
        "optical_blur_probability",
        "photographic_low_contrast_fraction",
        "reviewed_roi_catalogue",
        "reviewed_roi_fraction",
        "reviewed_roi_catalogue_sha256",
        "fine_weak_texture_fraction",
        "photo_sampling_reference_manifest",
        "photo_sampling_reference_sha256",
    ]
    reader = CleanDataset(config["manifest"], **{k: config[k] for k in keys if k in config})
    active = {row["id"] for row in reader.rows}
    catalogue = read(config["reviewed_roi_catalogue"])
    bank = [row["id"] for row in catalogue["examples"]]
    initial_ids = [
        json.loads(line)["id"]
        for line in Path(config["photo_sampling_reference_manifest"]).read_text().splitlines()
        if json.loads(line)["split"] == "train"
    ]
    fractions = sorted(set(plan["counterfactual_fractions"] + [config["reviewed_roi_fraction"]]))
    counters = {f: [Counter(), Counter(), Counter(), Counter()] for f in fractions}
    traced = {}
    for line in (
        Path(recipe["trace_prefix"]).read_text().splitlines() if recipe.get("trace_prefix") else []
    ):
        record = json.loads(line)
        index = record["source"]["draw_index"]
        assert record["data_step"] == index // 16 + 1
        assert index not in traced
        traced[index] = record
    trace_matches = 0
    domains, cumulative = Counter(), []
    audit_rows = 0
    path = output / f"{label}-metadata-draws.csv"
    with (
        path.open("w", newline="") as stream,
        patch.object(np, "load", stop_photo),
        patch.object(data_module, "smooth_scene", stop_family("smooth-field")),
        patch.object(data_module, "synthetic", stop_family("procedural")),
        patch.object(data_module, "weak_texture", stop_family("weak-texture")),
        patch.object(torch.nn.Module, "_call_impl", forbidden),
    ):
        writer = csv.DictWriter(
            stream,
            fieldnames=["step", "index", "family", "source_id", "reviewed"],
            lineterminator="\n",
        )
        writer.writeheader()
        for step in range(1, config["steps"] + 1):
            seed = config["seed"]
            paired, native = config["paired_fraction"], config["raw_clean_fraction"]
            domain = (
                "paired"
                if random.Random(f"paired:{seed}:{step}").random() < paired
                else (
                    "native"
                    if random.Random(f"raw-clean:{seed}:{step}").random() < native / (1 - paired)
                    else "commons"
                )
            )
            assert domain == training_domain(step, seed, paired, native)
            domains[domain] += 1
            if domain == "commons":
                for index in range((step - 1) * 16, step * 16):
                    rng = random.Random(seed + index)
                    draw = rng.random()
                    family = (
                        "smooth-field"
                        if draw < config["flat_fraction"]
                        else (
                            "fine-weak-texture"
                            if draw
                            < config["flat_fraction"] + config.get("fine_weak_texture_fraction", 0)
                            else (
                                "weak-texture"
                                if draw < config["flat_fraction"] + config["weak_texture_fraction"]
                                else (
                                    "procedural"
                                    if draw < config["flat_fraction"] + config["synthetic_fraction"]
                                    else "photographic"
                                )
                            )
                        )
                    )
                    identity, reviewed = "", False
                    if family == "photographic":
                        initial = initial_ids[rng.randrange(len(initial_ids))]
                        digest = hashlib.sha256(
                            f"reviewed-photo-roi-v1:{seed}:{index}".encode()
                        ).digest()
                        bank_rng = random.Random(int.from_bytes(digest[:8], "little"))
                        gate = bank_rng.random()
                        bank_id = bank[bank_rng.randrange(len(bank))]
                        ordinary_rng = random.Random()
                        ordinary_rng.setstate(rng.getstate())
                        ordinary_id = initial
                        while ordinary_id not in active:
                            ordinary_id = initial_ids[ordinary_rng.randrange(len(initial_ids))]
                        for fraction, (types, visits, ordinary, region) in counters.items():
                            selected = gate < fraction
                            selected_id = bank_id if selected else ordinary_id
                            types[
                                "photographic-reviewed" if selected else "photographic-ordinary"
                            ] += 1
                            visits[selected_id] += 1
                            (region if selected else ordinary)[selected_id] += 1
                        reviewed = gate < config["reviewed_roi_fraction"]
                        identity = bank_id if reviewed else ordinary_id
                        if not reviewed:
                            rng.setstate(ordinary_rng.getstate())
                    else:
                        for types, _, _, _ in counters.values():
                            types[family] += 1
                    expected = {
                        "index": index,
                        "family": family,
                        "source_id": identity,
                        "reviewed": reviewed,
                    }
                    try:
                        reader[index]
                    except SelectionStop as actual:
                        assert actual.row == expected, (label, step, actual.row, expected)
                        assert actual.rng_state == rng.getstate(), (label, index, "local RNG")
                    else:
                        raise AssertionError("Reader continued beyond the metadata stop")
                    writer.writerow({"step": step, **expected})
                    audit_rows += 1
                    if index in traced:
                        source = traced[index]["source"]
                        assert source["kind"] == family
                        if identity:
                            assert source["source_id"] == identity
                            assert (source["reviewed_roi_xywh"] is not None) == reviewed
                        trace_matches += 1
            if step % 1000 == 0:
                cumulative.append(
                    {
                        "step": step,
                        "fractions": {
                            str(f): {
                                "unique_sources": len(values[1]),
                                "photographic_draws": sum(values[1].values()),
                            }
                            for f, values in counters.items()
                        },
                    }
                )
    assert trace_matches == len(traced)
    summaries = {str(f): summarize(*values, len(active)) for f, values in counters.items()}
    return {
        "label": label,
        "config": reference(recipe["config"]),
        "seed": config["seed"],
        "steps": config["steps"],
        "batch_size": 16,
        "actual_reviewed_fraction": config["reviewed_roi_fraction"],
        "bank_regions": len(bank),
        "noise_pair_draws": config.get("noise_pair_draws", 1),
        "domain_batches": dict(domains),
        "source_context_slots": 16 * sum(domains.values()),
        "actual_reader_metadata_stops": audit_rows,
        "actual_trace_rows_matched": trace_matches,
        "draws": reference(path),
        "fraction_summaries": summaries,
        "cumulative": cumulative,
        "constructor_reviewed_cache_checks": len(bank),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    plan = read(args.plan)
    guard(plan)
    output = Path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    state = random.getstate(), np.random.get_state(), torch.get_rng_state()
    results = [audit_recipe(recipe, plan, output) for recipe in plan["recipes"]]
    assert state[0] == random.getstate()
    now = np.random.get_state()
    assert state[1][0] == now[0] and np.array_equal(state[1][1], now[1]) and state[1][2:] == now[2:]
    assert torch.equal(state[2], torch.get_rng_state()) and not torch.cuda.is_initialized()
    guard(plan)
    result = {
        "status": "passed-full-schedule-actual-reader-metadata-and-independent-selection",
        "plan": reference(args.plan),
        "recipes": results,
        "global_Python_NumPy_Torch_RNG_unchanged": True,
        "CUDA_initialized": False,
        "new_training_targets": 0,
        "geometry_augmentations": 0,
        "neural_forwards": 0,
        "noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "scope": "Full prospective source schedules; actual execution validated only at saved trace rows. Source identity repetition is not repeated augmented pixels. Counterfactual fractions are metadata only, not quality outcomes. Constructor checks read the original reviewed caches.",
    }
    (output / "result-v1.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "recipes": [
                    {
                        "label": row["label"],
                        "stops": row["actual_reader_metadata_stops"],
                        "trace_matches": row["actual_trace_rows_matched"],
                        "actual": row["fraction_summaries"][str(row["actual_reviewed_fraction"])],
                    }
                    for row in results
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
