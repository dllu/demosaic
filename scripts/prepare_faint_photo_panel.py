"""Freeze a 427-photo faint-ADC study using the established physical simulator."""

import argparse
import os
import subprocess
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import psutil
from queue_faint_adc_precision import adc_observation, faint_target

from demosaic.experiments.artifacts import checked, freeze_sources, read_json, reference, write_json
from demosaic.prediction_archive import fingerprint


def prepare(root, canonical_path, native_path, training_manifest):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("Preparation requires hidden CUDA")
    root = Path(root).resolve()
    root.mkdir()
    native = read_json(native_path)
    canonical = read_json(canonical_path)
    if not canonical["all_input_witnesses_exact"]:
        raise ValueError("Canonical input witnesses must be exact")
    # Qualify the unchanged one-image functions against every retained faint
    # observation before constructing the expanded cohort or running a model.
    qualifications = []
    for observation in native["observations"]:
        if "contrast0p025-adc" not in observation.get("case_id", ""):
            continue
        with np.load(checked(observation["case"]["original_target"])) as data:
            target = faint_target(data["target"])
        with np.load(checked(observation["target"])) as data:
            np.testing.assert_array_equal(target, data["target"])
        values = adc_observation(target, observation["pattern"])
        with np.load(checked(observation["arrays"])) as data:
            for key, value in zip(("packed", "variance", "colors"), values, strict=True):
                np.testing.assert_array_equal(value, data[key])
        qualifications.append(observation["id"])
    assert len(qualifications) == 16
    with Path(training_manifest).open() as stream:
        import json

        source_rows = [json.loads(line) for line in stream]
    training_ids = {row["id"] for row in source_rows if row["split"] == "train"}
    metadata = {row["id"]: row for row in source_rows}
    assert len(training_ids) == 90778
    records = [
        record for record in canonical["records"]
        if record["stage"] == "photo"
        and record["context"]["condition"]["name"] == "adc-only"
        and record["context"]["pattern"] == "RGGB"
    ]
    assert len(records) == 111
    ids = [identity for record in records for identity in record["context"]["ids"]
           if not identity.startswith("synthetic-")]
    assert len(ids) == len(set(ids)) == 427 and not (set(ids) & training_ids)
    assert all(metadata[identity]["split"] == "val" for identity in ids)
    inputs = root / "inputs"
    inputs.mkdir()
    observations, groups = [], []
    for record in records:
        selected = [i for i, identity in enumerate(record["context"]["ids"])
                    if not identity.startswith("synthetic-")]
        if not selected:
            continue
        assert record["context"]["condition"]["exposure"] == 1
        with np.load(checked(record["arrays"]), allow_pickle=False) as data:
            original = data["target"][selected].copy()
            wb, matrix = data["wb"][selected].copy(), data["matrix"][selected].copy()
        names = [record["context"]["ids"][i] for i in selected]
        faint = np.concatenate([faint_target(one[None]) for one in original])
        target_path = inputs / f"target-{len(groups):03d}.npz"
        with target_path.open("xb") as stream:
            np.savez(stream, target=faint, original_target=original)
        group = {"ids": names, "original_canonical": record, "target": reference(target_path)}
        groups.append(group)
        for pattern in ("RGGB", "BGGR", "GRBG", "GBRG"):
            pieces = [adc_observation(one[None], pattern) for one in faint]
            packed, variance, colors = [np.concatenate([p[k] for p in pieces]) for k in range(3)]
            arrays = {"packed": packed, "variance": variance, "colors": colors,
                      "wb": wb, "matrix": matrix}
            path = inputs / f"input-{len(groups)-1:03d}-{pattern}.npz"
            with path.open("xb") as stream:
                np.savez(stream, **arrays)
            observations.append({
                "id": f"faint-photo-{len(groups)-1:03d}-{pattern}", "kind": "faint-photo",
                "source_ids": names, "pattern": pattern, "arrays": reference(path),
                "target": group["target"], "original_canonical": record,
                "input_fingerprints": {k: fingerprint(v) for k, v in arrays.items()},
                "output_shape": list(faint.shape), "ROI_xywh": [8, 8, 240, 240],
                "noise": {"name": "contrast0p025-adc", "shot": 0., "read": 0.,
                          "ADC_bits": 16, "black_level": .03, "CPU_precision": "float64"},
            })
    assert len(groups) == 107 and len(observations) == 428
    assert sum(o["output_shape"][0] for o in observations) == 1708
    work, frozen = freeze_sources(Path.cwd(), root, [
        "collect_full_corpus_checkpoint_review.py", "prepare_faint_photo_panel.py",
        "queue_faint_adc_precision.py", "diagnose_local_material_detail.py",
        "audit_checkpoint_pilot.py",
    ])
    write_json(root / "cohort.json", {
        "groups": groups, "source_ids": ids, "source_metadata": [metadata[i] for i in ids],
        "training_manifest": reference(training_manifest), "training_overlap": [],
        "legacy16_qualification": qualifications,
        "scope": "All427 fixed photo sources are val under current90778 training cohort;"
                 " no lifetime-novelty claim. Synthetic sources excluded. No original RAW/HDD access.",
    })
    plan = {
        "root": str(root), "work": str(work), "inputs": [reference(canonical_path),
            reference(native_path), reference(training_manifest), reference(root / "cohort.json")]
            + [spec["checkpoint"] for spec in native["models"].values()],
        "frozen_files": frozen,
        "collector": reference(work / "scripts/collect_full_corpus_checkpoint_review.py"),
        "models": native["models"], "DINO_sha256": native["DINO_sha256"],
        "CPU_affinity": [2, 3], "CPU_threads": 2, "maximum_seconds": 21600,
        "observations": observations, "planned_root_calls": 856,
        "planned_DINO_executions": 428, "batch_histogram": dict(Counter(
            o["output_shape"][0] for o in observations)),
        "analysis_protocol": {
            "policies": ["raw", "existing-exact-Malvar", "existing-exact-sites", "ADC-bins-Malvar"],
            "photometry_border": 8, "fine_block": 16, "annulus_cycles_per_pixel": [1/8, 1/3],
            "eligibility": "Original-source linear sRGB unsaturated; original luma mean.02..9,"
                           " original band RMS>=1e-5, unchanged contrast bins0/.02/.05/.1/.2.",
            "truth": "Faint target for coefficients/error; original target for eligibility masks."
                     " Pool4CFAs then equal-source, keep quiet-block errors separate.",
            "native_selection": "First two sorted source IDs and bark/fur if present; RGGB,"
                                " center160/common contrast20 target-ROI anchor; no resizing.",
        },
        "scope": "New427-photo/4-CFA deterministic faint-ADC protocol,1708 images/model."
                 " Legacy16 physical inputs/targets qualified bitexact before NN. Source and"
                 " policy selection frozen before forwards. Fresh matched CPU EMA outputs."
                 " No standard full427 score/history point, new RAW/noise/GPU/training or default change.",
    }
    write_json(root / "plan.json", plan)
    env = os.environ.copy()
    env.update(CUDA_VISIBLE_DEVICES="", PYTHONPATH=str(work / "scripts") + ":" + str(work / "src"))
    command = [sys.executable, str(work / "scripts/collect_full_corpus_checkpoint_review.py"),
               str(root / "plan.json")]
    with (root / "collection.log").open("xb") as log:
        child = subprocess.Popen(command, env=env, stdout=log, stderr=subprocess.STDOUT,
                                 start_new_session=True)
    write_json(root / "launch.json", {
        "producer": reference(__file__), "pid": child.pid,
        "create_time": psutil.Process(child.pid).create_time(), "command": command,
        "plan": reference(root / "plan.json"), "no_automatic_retry": True,
    })
    print("Launched", child.pid, "428 batches/1708 faint images per model")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("--canonical", required=True, type=Path)
    parser.add_argument("--native-plan", required=True, type=Path)
    parser.add_argument("--training-manifest", required=True, type=Path)
    args = parser.parse_args()
    prepare(args.root, args.canonical, args.native_plan, args.training_manifest)
