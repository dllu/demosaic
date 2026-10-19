"""Freeze unchanged full panels and native audits for the context study."""

import argparse
import copy
import shutil
import subprocess
from pathlib import Path

from prepare_directional_bank_review import references
from queue_context_review import validate_preflight
from review_directional_bank import alive
from train_directional_interval_trial import guard, read, ref, save

from demosaic.safety import writable_path


def prepare(training_path, historical_path, closure_path, preflight_path, output):
    training, historical = read(training_path), read(historical_path)
    guard(training)
    assert training["parent"] == historical["parent"]
    assert not training["engineering_only"] and training["boundary_updates"] == 4000
    status_path = Path(training["root"]) / "status.json"
    status = read(status_path)
    assert alive(status["controller"])
    assert status["status"] == "running-source-frozen-context-training-arm"
    proof = read(preflight_path)
    validate_preflight(proof)
    root = writable_path(output)
    root.mkdir(parents=True, exist_ok=False)
    work, trained = root / "work", Path(training["work"])
    # Model/runtime source comes from the actual running study. Only review
    # orchestration is taken from the current committed scripts.
    sources = [*trained.glob("src/demosaic/*.py")]
    sources += [trained / name for name in ["pyproject.toml", "uv.lock", "configs/evaluation.yaml"]]
    sources += [p for p in (trained / "third_party").rglob("*LICENSE*") if p.is_file()]
    for source in sources:
        destination = work / source.relative_to(trained)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    for source in Path("scripts").glob("*.py"):
        destination = work / source
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    core = {
        str(p.relative_to(trained)): ref(p)["sha256"] for p in trained.glob("src/demosaic/*.py")
    }
    assert len(core) == 45
    assert all(ref(work / path)["sha256"] == digest for path, digest in core.items())
    for item in proof["scripts"]:
        assert ref(work / "scripts" / Path(item["path"]).name)["sha256"] == item["sha256"]
    criteria = Path("docs/training-context-v86-v87.md").resolve()
    assert ref(criteria) in training["inputs"]
    snapshot = work / "docs/training-context-v86-v87.md"
    snapshot.parent.mkdir(parents=True)
    shutil.copyfile(criteria, snapshot)
    plan = copy.deepcopy(historical)
    plan.update(
        root=str(root),
        work=str(work),
        python=training["python"],
        HF_HOME=training["cache_environment"]["HF_HOME"],
        worker=ref(work / "scripts/review_context_trial.py"),
        training_status=str(status_path),
        training_plan=ref(training_path),
        training_owner=status["controller"],
        actual_training_core=core,
        static_input_recipe=ref(historical_path),
        engineering_preflight=False,
        review_CPU_preflight=ref(preflight_path),
        quality_numerical_scorer=ref(work / "scripts/score_context_eligibility.py"),
        quality_criteria={
            "predeclared_snapshot": ref(snapshot),
            "scope": "Original4k forward256/320 with identical source320/loss256 study; full primary, sensitivity, weak carrier, all ADC cases, hue and native review. No automatic extension/promotion.",
        },
        git_head_at_freeze=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        scope="Fresh V86/V87 original4000 final EMA review after exact successful controller/child exits. Same full427, known4/unseen5, sensitivity, hue, analytic and GFX/highlight panels, fresh V63, retained V43/RawNIND with witnesses. Native160 crops include foliage/fence. No protected-final scoring, extension or promotion.",
    )
    plan.pop("recovery_of", None)
    plan["outputs"] = {key: str(work / "outputs" / key) for key in historical["outputs"]}
    closure = copy.deepcopy(read(closure_path))
    closure.update(
        root=str(root),
        output=str(work / "outputs/closure"),
        worker=ref(work / "scripts/close_context_review.py"),
        closure_engine=ref(work / "scripts/close_bank_detachment_review.py"),
        historical_replay=False,
        scope="CPU saved-array/arithmetic, original4k context criteria and native boards after all10 stages; actual viewing remains required. No promotion.",
    )
    for key in ["review_owner", "review_plan", "recovery_of", "frozen_files", "inputs"]:
        closure.pop(key, None)
    supplement = copy.deepcopy(read(Path(closure_path).parent / "reference-plan.json"))
    supplement.update(
        output=str(work / "outputs/reference-closure"),
        worker=ref(work / "scripts/prepare_directional_reference_boards.py"),
        closure_root=str(root),
    )
    supplement.pop("closure_owner", None)
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
    inputs = [
        *historical["inputs"],
        ref(training_path),
        ref(historical_path),
        ref(closure_path),
        ref(preflight_path),
        ref(criteria),
        ref(snapshot),
    ]
    for template in [closure, supplement]:
        inputs += list(references(template))
    # Current frozen scripts are covered by frozen_files; references to those
    # same bytes are harmless and retain the wrapper/engine distinction.
    plan["inputs"] = list({(r["path"], r["sha256"]): r for r in inputs}.values())
    plan["frozen_files"] = {
        str(p): ref(p)["sha256"] for p in sorted(work.rglob("*")) if p.is_file()
    }
    guard(plan)
    save(root / "plan.json", plan)
    closure.update(
        review_plan=ref(root / "plan.json"),
        inputs=plan["inputs"],
        frozen_files=plan["frozen_files"],
    )
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
    for name in ["training-plan", "historical-review", "historical-closure", "preflight", "output"]:
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    prepare(
        args.training_plan.resolve(),
        args.historical_review.resolve(),
        args.historical_closure.resolve(),
        args.preflight.resolve(),
        args.output.resolve(),
    )
