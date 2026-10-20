"""Freeze unchanged fresh FP32 panels for V92 and its historical V90 reference."""

import argparse
import copy
import shutil
from pathlib import Path

from prepare_directional_bank_review import references
from queue_late_rgb_only_review import validate_preflight
from review_directional_bank import alive
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]
TRAINING = Path("/mnt/external/demosaic/experiments/late-rgb-head-only-v92-original4k-v1")
OLD = Path("/mnt/external/demosaic/experiments/late-rgb-v90-v91-original4k-review-v1")


def prepare(root, preflight):
    training_path = TRAINING / "plan.json"
    training, historical = read(training_path), read(OLD / "plan.json")
    guard(training)
    assert training["parent"] == historical["parent"] and not training["engineering_only"]
    assert training["boundary_updates"] == training["planned_updates"] == 4000
    status_path = TRAINING / "status.json"
    status = read(status_path)
    assert alive(status["controller"]) and status["status"] in (
        "running-source-frozen-head-only-worker",
        "waiting-for-head-only-resources",
    )
    proof = read(preflight)
    validate_preflight(proof)
    root = Path(root).resolve()
    assert root.is_relative_to(REPO / ".cache")
    assert shutil.disk_usage(REPO).free > 72 * 2**30
    root.mkdir(parents=True, exist_ok=False)
    work, trained = root / "work", Path(training["work"])
    sources = [
        *trained.glob("src/demosaic/*.py"),
        *[trained / p for p in ["pyproject.toml", "uv.lock", "configs/evaluation.yaml"]],
    ]
    sources += [p for p in (trained / "third_party").rglob("*LICENSE*") if p.is_file()]
    for source in sources:
        target = work / source.relative_to(trained)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for source in (REPO / "scripts").glob("*.py"):
        target = work / "scripts" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    core = {
        str(p.relative_to(trained)): ref(p)["sha256"] for p in trained.glob("src/demosaic/*.py")
    }
    assert len(core) == 47 and all(ref(work / p)["sha256"] == digest for p, digest in core.items())
    for item in proof["scripts"]:
        assert ref(work / "scripts" / Path(item["path"]).name)["sha256"] == item["sha256"]
    source_proof = read(proof["source_plan"]["path"])
    for source in (Path(source_proof["work"]) / "src/demosaic").glob("*.py"):
        assert ref(source)["sha256"] == ref(work / "src/demosaic" / source.name)["sha256"]
    protocol = trained / "docs/late-rgb-head-only-v92.md"
    snapshot = work / "docs/late-rgb-head-only-v92.md"
    snapshot.parent.mkdir()
    shutil.copyfile(protocol, snapshot)
    plan = copy.deepcopy(historical)
    plan.update(
        root=str(root),
        work=str(work),
        python=training["python"],
        HF_HOME=training["cache_environment"]["HF_HOME"],
        worker=ref(work / "scripts/review_late_rgb_only.py"),
        training_status=str(status_path),
        training_plan=ref(training_path),
        training_owner=status["controller"],
        actual_training_core=core,
        engineering_preflight=False,
        review_CPU_preflight=ref(preflight),
        historical_boundary=ref(OLD / "training-boundary.json"),
        quality_numerical_scorer=ref(work / "scripts/score_late_rgb_only_eligibility.py"),
        quality_criteria={
            "predeclared_snapshot": ref(snapshot),
            "scope": "V92 candidate-only photo/camera criteria and weak-detail/192-slot ADC requirements. V90 is a fixed historical reference, not a newly randomized arm.",
        },
        output_disk_reserve_gib=64,
        storage_scope="Local SSD review artifacts preserve external500GiB and root64GiB reserves; at least72GiB root free verified before freezing. Old equivalent artifacts estimate under8GiB, without deleting prior evidence.",
        model_source_reuse_policy="All V90/V92/V63 neural predictions fresh FP32 from exact V92 training module bytes. Historical V43/RawNIND rows and original source/reference PNGs require the unchanged coverage/input/classical witnesses.",
        scope="Exploratory V92 head-only against historical V90 original4000. Fresh known4/unseen5/full427+16/all7conditions/all4CFAs, analytic192 ADC slots/12means, hue, GFX sky/building/foliage/fence and highlights. Actual native viewing remains required. No retry, training extension or automatic promotion.",
    )
    for key in ["recovery_of", "static_input_recipe", "git_head_at_freeze"]:
        plan.pop(key, None)
    plan["outputs"] = {k: str(work / "outputs" / k) for k in historical["outputs"]}
    closure = copy.deepcopy(read(OLD / "closure-plan.json"))
    closure.update(
        root=str(root),
        output=str(work / "outputs/closure"),
        worker=ref(work / "scripts/close_late_rgb_only_review.py"),
        closure_engine=ref(work / "scripts/close_bank_detachment_review.py"),
        historical_replay=False,
        scope="CPU saved-array/arithmetic, V92 candidate-only criteria and all native boards. No actual-view assertion or automatic promotion.",
    )
    for key in ["review_owner", "review_plan", "recovery_of", "frozen_files", "inputs"]:
        closure.pop(key, None)
    supplement = copy.deepcopy(read(OLD / "reference-plan.json"))
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
        ref(preflight),
        ref(OLD / "plan.json"),
        ref(OLD / "training-boundary.json"),
        ref(TRAINING / "prelaunch-evidence.json"),
        ref(protocol),
        ref(snapshot),
    ]
    for template in [closure, supplement]:
        inputs += list(references(template))
    unique = {}
    for item in inputs:
        if item["path"] in unique:
            assert unique[item["path"]] == item["sha256"]
        unique[item["path"]] = item["sha256"]
    plan["inputs"] = [{"path": path, "sha256": digest} for path, digest in sorted(unique.items())]
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
    print({"plan": ref(root / "plan.json"), "model_modules": len(core), "storage": "local SSD"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("preflight", type=Path)
    args = parser.parse_args()
    prepare(args.root, args.preflight)
