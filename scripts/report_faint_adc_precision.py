"""Derive report metadata from completed new faint-ADC predictions, without models."""

import argparse
import importlib.util
import os
import shutil
from pathlib import Path

from train_directional_bank_trial import guard, read, ref, save


def analyze(path, label):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        raise RuntimeError("Saved-output analysis is CPU-only")
    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    status = read(root / "status.json")
    assert status["plan"] == ref(path)
    binding = status["completed"][label]
    assert ref(binding["path"]) == binding
    collection = read(binding["path"])
    actual_path = root / label / "plan-v1.json"
    execution = read(actual_path)
    assert collection["plan"] == ref(actual_path)
    assert collection["counts"] == {"root": 16, "encoder": 16}
    guard(execution)
    cases = {c["id"]: c for c in plan["cases"]}
    assert len(cases) == 4
    observations = []
    for original in execution["observations"]:
        case = cases[original["case_id"]]
        # The first frozen input schema retained this provenance at case level.
        # Attach it to each reporting observation; do not change inference/input
        # plans, target arrays, saved predictions or any forward count.
        observations.append(
            {**original, "case": case, "original_case_id": case["original_case_id"]}
        )
    destination = root / f"analysis-{label}-v1"
    destination.mkdir(exist_ok=False)
    derived = {
        **execution,
        "root": str(destination),
        "observations": observations,
        "actual_neural_execution": ref(actual_path),
        "inputs": [*execution["inputs"], ref(path), ref(actual_path), binding],
        "scope": execution["scope"]
        + " Report-only per-observation source/GT-label metadata from immutable case catalogue; same saved16 predictions/targets, zero new neural/noise/RAW work.",
    }
    save(destination / "plan-v1.json", derived)
    save(
        destination / "collection-v1.json",
        {
            **collection,
            "plan": ref(destination / "plan-v1.json"),
            "actual_neural_collection": binding,
            "new_forwards_in_this_derivation": 0,
        },
    )
    source = Path(execution["work"]) / "scripts"
    for name in (
        "report_checkpoint_pilot.py",
        "audit_checkpoint_pilot.py",
        "train_directional_bank_trial.py",
        "train_v43_quality_trial.py",
    ):
        shutil.copyfile(source / name, destination / name)
    from demosaic import archive_metrics

    assert (
        ref(archive_metrics.__file__)["sha256"]
        == ref(Path(execution["work"]) / "src/demosaic/archive_metrics.py")["sha256"]
    )
    spec = importlib.util.spec_from_file_location(
        f"faint_report_{label}", destination / "report_checkpoint_pilot.py"
    )
    reporter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reporter)
    reporter.report(destination / "plan-v1.json", destination / "collection-v1.json")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--label", choices=("V120", "V129", "V130"), required=True)
    args = parser.parse_args()
    print(analyze(args.plan.resolve(), args.label))
