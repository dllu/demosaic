"""Freeze the full three-prior local/global support comparison, reusing the pilot."""

import argparse
import sys
from pathlib import Path

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)
from demosaic.local_validated_waves import LocalWaveConfig

REPO = Path(__file__).resolve().parents[1]


def prepare(root):
    pilot = REPO / ".cache/experiments/local-validated-wave-pilot-v1"
    previous, collection = read_json(pilot / "plan.json"), read_json(pilot / "collection.json")
    if (
        collection["plan"] != reference(pilot / "plan.json")
        or len(collection["rows"]) != 24
        or collection["target_or_reference_arrays_loaded"] != 0
    ):
        raise ValueError("Require the completed input-only pilot collection")
    config = LocalWaveConfig().to_dict()
    corrected = pilot / "analytic-model-v2.json"
    pilot_model = reference(corrected) if corrected.exists() else previous["model"]
    old_model = read_json(checked(pilot_model))
    if "parent_bindings_by_domain" not in old_model:
        raise ValueError("Require verified domain-specific parent lineage")
    stage = REPO / "src/demosaic/local_validated_waves.py"
    if previous["config"] != config or old_model["source"]["sha256"] != reference(stage)["sha256"]:
        raise ValueError("Panel configuration/numerical stage differs from completed pilot")
    source_rows = {
        (r["arrays"]["sha256"], r["parent"]["sha256"], r["sample"]): r for r in previous["rows"]
    }
    old_records = {r["id"]: r for r in collection["rows"]}
    inputs, rows, groups, adoptions = (
        [reference(pilot / "plan.json"), reference(pilot / "collection.json"), pilot_model],
        [],
        [],
        {},
    )
    for profile, directory in [
        ("iso6400", "near-edge-response-v1"),
        ("iso1600", "near-edge-response-iso1600-v1"),
        ("iso400", "near-edge-response-iso400-v1"),
    ]:
        path = REPO / ".cache/experiments" / directory / "cache.json"
        cache = read_json(path)
        source_plan = read_json(path.with_name("plan.json"))
        if (
            source_plan["parent"]["sha256"]
            != "96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4"
        ):
            raise ValueError("Full wire panel parent differs from V143")
        if len(cache["rows"]) != 128:
            raise ValueError("Require all128 closed observations per prior")
        inputs.append(reference(path))
        inputs.append(reference(path.with_name("plan.json")))
        for item in cache["rows"]:
            cases = []
            for role in range(3):
                name = f"{profile}-index{item['index']:04d}-role{role}"
                cases.append(name)
                row = {
                    "id": name,
                    "profile": profile,
                    "kind": "finite-wire",
                    "arrays": item["arrays"],
                    "parent": item["parent"],
                    "sample": role,
                    "noise": item["metadata"]["noise"],
                    "metadata": item["metadata"],
                    "reference_role": "Exact constructed finite-wire RGB GT",
                }
                old = source_rows.get((row["arrays"]["sha256"], row["parent"]["sha256"], role))
                if old is not None:
                    if any(row["noise"][k] != old["noise"][k] for k in ["shot", "read"]):
                        raise ValueError("Adopted noise conditioning differs")
                    binding = reference(pilot / "predictions" / (old["id"] + "-receipt.json"))
                    record = old_records[old["id"]]
                    if read_json(checked(binding)) != record:
                        raise ValueError("Adopted pilot record differs from completed collection")
                    adoptions[name] = binding
                    inputs += [
                        binding,
                        *[record["predictions"][m] for m in ["global-t2", "local-t2"]],
                    ]
                rows.append(row)
                inputs += [row["arrays"], row["parent"]]
            groups.append(
                {
                    "profile": profile,
                    "index": item["index"],
                    "cases": cases,
                    "arrays": item["arrays"],
                    "metadata": item["metadata"],
                }
            )
    if len(rows) != 1152 or len(groups) != 384 or len(adoptions) != 12:
        raise ValueError("Complete-panel/adoption coverage differs")
    root.mkdir(parents=True, exist_ok=False)
    work, files = freeze_sources(REPO, root, entries=("pilot_local_validated_waves.py",))
    source = work / "scripts/pilot_local_validated_waves.py"
    identity = root / "analytic-model.json"
    write_json(
        identity,
        {
            **old_model,
            "source": reference(work / "src/demosaic/local_validated_waves.py"),
            "thresholds": [2],
            "scope": "Same completed pilot numerical stage/configuration, both global/local variants; primary threshold2 fixed before full cohort.",
        },
    )
    inputs.append(reference(identity))
    plan = {
        "root": str(root),
        "work": str(work),
        "script": reference(source),
        "python": sys.executable,
        "model": reference(identity),
        "config": config,
        "thresholds": [2],
        "modes": ["global", "local"],
        "rows": rows,
        "finite_groups": groups,
        "adoptions": adoptions,
        "pilot_source": pilot_model,
        "new_cases": 1140,
        "minimum_RAM_GiB": 32,
        "minimum_disk_GiB": 96,
        "maximum_prediction_seconds": 14400,
        "inputs": list({(b["path"], b["sha256"]): b for b in inputs}.values()),
        "frozen_files": files,
        "scope": "Full fixed three-prior finite-wire comparison:8 geometries x2 placements x4 CFAs x2 independent repeats x3 roles x3 priors =1152 images. Same raw-only stage/config as completed pilot, global/local threshold2 only; no parameter/threshold change after full results. Adopt12 exact completed pilot outputs with identical input/noise/source checks; no replay. All new input-only predictions close before target/mask loading. Zero source/noise/RAW/model/DINO work; original V132 training untouched. This extends descriptive development evidence, not population-calibrated confidence or a broad camera/photograph ranking.",
    }
    write_json(root / "plan.json", plan)
    verify_plan(plan)
    return root / "plan.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    print(prepare(parser.parse_args().root.resolve()))
