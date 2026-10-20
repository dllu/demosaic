"""Freeze unchanged full quality/native panels using the actual spectral model code."""

import argparse
import copy
import shutil
import subprocess
from pathlib import Path

from prepare_directional_bank_review import references
from queue_spectral_review import validate_preflight
from review_directional_bank import alive
from train_directional_bank_trial import guard, read, ref, save

from demosaic.safety import writable_path


def prepare(training_path, historical_path, closure_path, preflight_path, output):
    training, historical = read(training_path), read(historical_path)
    guard(training)
    assert (
        training["parent"] == historical["parent"]
        and not training["engineering_only"]
        and training["boundary_updates"] == 4000
    )
    status_path = Path(training["root"]) / "status.json"
    status = read(status_path)
    assert alive(status["controller"]) and status["status"] == "running-source-frozen-spectral-arm"
    proof = read(preflight_path)
    validate_preflight(proof)
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    work, trained = root / "work", Path(training["work"])
    sources = [*trained.glob("src/demosaic/*.py")]
    sources += [trained / p for p in ["pyproject.toml", "uv.lock", "configs/evaluation.yaml"]]
    sources += [p for p in (trained / "third_party").rglob("*LICENSE*") if p.is_file()]
    for source in sources:
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
    assert len(core) == 46 and all(ref(work / p)["sha256"] == sha for p, sha in core.items())
    for item in proof["scripts"]:
        assert ref(work / "scripts" / Path(item["path"]).name)["sha256"] == item["sha256"]
    criteria = training["protocol"]
    assert ref(criteria["path"]) == criteria
    snapshot = work / "docs/spectral-v88-v89.md"
    snapshot.parent.mkdir(parents=True)
    shutil.copyfile(criteria["path"], snapshot)
    assert ref(snapshot)["sha256"] == criteria["sha256"]
    plan = copy.deepcopy(historical)
    plan.update(
        root=str(root),
        work=str(work),
        python=training["python"],
        HF_HOME=training["cache_environment"]["HF_HOME"],
        worker=ref(work / "scripts/review_spectral_trial.py"),
        training_status=str(status_path),
        training_plan=ref(training_path),
        training_owner=status["controller"],
        actual_training_core=core,
        static_input_recipe=ref(historical_path),
        engineering_preflight=False,
        review_CPU_preflight=ref(preflight_path),
        quality_numerical_scorer=ref(work / "scripts/score_spectral_eligibility.py"),
        quality_criteria={
            "predeclared_snapshot": ref(snapshot),
            "scope": "Original4000 matched spectral experiment, unchanged full primary/sensitivity/weak-carrier/all192 ADC/hue/native criteria; explicit control1000 recovery. No automatic extension/promotion.",
        },
        git_head_at_freeze=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        scope="Fresh V88/V89 original4000 final EMA review after exact successful training exits. Same full427, known4/unseen5, sensitivity/analytic/ADC/hue/GFX/highlight panels, fresh V63 and witnessed retained V43/RawNIND. Native160 triplets include foliage/fence. No protected-final scoring, extension or promotion.",
    )
    plan.pop("recovery_of", None)
    plan["outputs"] = {k: str(work / "outputs" / k) for k in historical["outputs"]}
    closure = copy.deepcopy(read(closure_path))
    closure.update(
        root=str(root),
        output=str(work / "outputs/closure"),
        worker=ref(work / "scripts/close_spectral_review.py"),
        closure_engine=ref(work / "scripts/close_bank_detachment_review.py"),
        historical_replay=False,
        scope="CPU saved-array/arithmetic, original spectral criteria and exact native boards after all10 stages. Actual viewing remains required; no promotion.",
    )
    for k in ["review_owner", "review_plan", "recovery_of", "frozen_files", "inputs"]:
        closure.pop(k, None)
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
        criteria,
        ref(snapshot),
    ]
    for template in [closure, supplement]:
        inputs += list(references(template))
    unique = {}
    for item in inputs:
        if item["path"] in unique:
            assert unique[item["path"]] == item["sha256"]
        unique[item["path"]] = item["sha256"]
    plan["inputs"] = [{"path": p, "sha256": s} for p, s in sorted(unique.items())]
    plan["frozen_files"] = {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()}
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
            "model_modules": len(core),
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ["training-plan", "historical-review", "historical-closure", "preflight", "output"]:
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    prepare(
        a.training_plan.resolve(),
        a.historical_review.resolve(),
        a.historical_closure.resolve(),
        a.preflight.resolve(),
        a.output,
    )
