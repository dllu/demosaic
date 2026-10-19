"""Freeze a complete review using the live trial's actual model package bytes."""

import argparse
import copy
import shutil
from pathlib import Path

import psutil
from train_directional_interval_trial import guard, read, ref, save

from demosaic.safety import writable_path


def references(value):
    if isinstance(value, dict):
        if "path" in value and "sha256" in value:
            yield value
        for child in value.values():
            yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def prepare(training_path, historical_path, output):
    training, historical = read(training_path), read(historical_path)
    assert training["parent"] == historical["parent"]
    guard(training)
    state_path = Path(training["root"]) / "status.json"
    status = read(state_path)
    owner = status["controller"]
    process = psutil.Process(owner["pid"])
    assert process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
    assert status["status"] == "running-directional-bank-original4000"
    root = writable_path(output)
    root.mkdir(parents=True, exist_ok=False)
    work, trained = root / "work", Path(training["work"])
    files = [*trained.glob("src/demosaic/*.py")]
    files += [
        trained / p
        for p in (
            "pyproject.toml",
            "uv.lock",
            "configs/evaluation.yaml",
            "third_party/gaussian/Noise2VST-LICENSE",
            "third_party/gaussian/KAIR-LICENSE",
            "third_party/dinov3/LICENSE.md",
            "docs/directional-bank-v80-v81.md",
        )
    ]
    for source in files:
        target = work / source.relative_to(trained)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for source in Path("scripts").glob("*.py"):
        target = work / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    core = {
        str(p.relative_to(trained)): ref(p)["sha256"] for p in trained.glob("src/demosaic/*.py")
    }
    assert all(ref(work / p)["sha256"] == digest for p, digest in core.items())
    plan = copy.deepcopy(historical)
    plan.update(
        root=str(root),
        work=str(work),
        python=training["python"],
        HF_HOME=training["HF_HOME"],
        worker=ref(work / "scripts/review_directional_bank.py"),
        training_status=str(state_path),
        training_plan=ref(training_path),
        training_owner=owner,
        quality_criteria=training["quality_review_plan"],
        static_input_recipe=ref(historical_path),
        actual_training_core=core,
        model_source_reuse_policy="Fresh predictions with exact training package bytes. Historical scores/images require per-panel identity/control witnesses; never reuse new-model predictions.",
        scope="Full fixed V80/V81 original4000 review, after exact successful training owner/child exit. Fresh parent primary, unchanged evaluation targets, fixed weak-carrier/flat criteria and native crops. No protected-final scoring, automatic extension or promotion.",
    )
    plan["outputs"] = {k: str(work / "outputs" / k) for k in historical["outputs"]}
    # Retain static score/input bindings, not the old study's owner or mutable code.
    inputs = [
        r
        for r in historical["inputs"]
        if r["path"] != historical["training_plan"]["path"]
        and not r["path"].endswith(".py")
        and "/docs/results/" not in r["path"]
    ]
    inputs += [
        ref(training_path),
        ref(historical_path),
        training["quality_review_plan"]["predeclared_snapshot"],
    ]
    closure = read(Path(historical["root"]) / "closure-plan.json")
    closure.update(root=str(root), worker=ref(work / "scripts/close_directional_bank_review.py"))
    closure.pop("review_owner")
    closure.pop("review_plan")
    closure["scope"] = (
        "CPU saved-array arithmetic, fixed numerical/weak-carrier criteria and exact native boards after all10 stages and exact review owner/child exit. Actual manual viewing remains mandatory. No promotion or automatic retry."
    )
    supplement = read(Path(historical["root"]) / "reference-plan.json")
    supplement.update(
        output=str(work / "outputs/reference-closure"),
        worker=ref(work / "scripts/prepare_directional_reference_boards.py"),
        closure_root=str(root),
    )
    supplement.pop("closure_owner")
    for panel, spec in supplement["panels"].items():
        spec["fresh_report"] = str(
            work
            / "outputs"
            / (
                "gfx/report.json"
                if panel == "gfx"
                else f"closure/{panel}-native-sources/report.json"
            )
        )
    for template in (closure, supplement):
        inputs += list(references(template))
    unique = {(x["path"], x["sha256"]): x for x in inputs}
    plan["inputs"] = list(unique.values())
    plan["frozen_files"] = {
        str(p): ref(p)["sha256"] for p in sorted(work.rglob("*")) if p.is_file()
    }
    guard(plan)
    save(root / "plan.json", plan)
    closure["review_plan"] = ref(root / "plan.json")
    save(root / "closure-template.json", closure)
    save(root / "reference-template.json", supplement)
    print(
        {
            "plan": ref(root / "plan.json"),
            "frozen_files": len(plan["frozen_files"]),
            "identical_training_modules": len(core),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training-plan", type=Path, required=True)
    parser.add_argument("--historical-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.training_plan, args.historical_review, args.output)
