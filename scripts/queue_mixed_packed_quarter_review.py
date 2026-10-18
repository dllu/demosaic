"""Queue the complete 160k-example review behind the exact mixed16 training owner."""

import argparse
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import psutil

REPO = Path("/home/dllu/proj/demosaic")
BASE = Path("/mnt/external/demosaic")
ROOT = BASE / "benchmarks/packed-isotropic-mixed16-quarter-review-workflow-v1"
STATUS = BASE / "runs/packed-isotropic-mixed16-quarter-review-workflow-v1.json"
TRAINING = BASE / "runs/packed-isotropic-mixed16-quarter-workflow-v1.json"
OLD = BASE / "benchmarks/packed-isotropic-mixed16-first32000-review-workflow-v1"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def guard(plan):
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path


def prepare():
    assert not ROOT.exists() and not STATUS.exists()
    assert psutil.virtual_memory().available > 32 * 2**30
    # Actual completed-review storage leaves room for another~12GiB panel set.
    assert shutil.disk_usage(BASE).free > 516 * 2**30
    training = read(TRAINING)
    assert alive(training["controller"]) or training["status"] == (
        "completed-matched-mixed16-quarter160000-examples-awaiting-full-quality-review"
    )
    assert training["plan"] == ref(training["plan"]["path"])
    train_plan = read(training["plan"]["path"])
    assert (train_plan["quality_gate_updates"], train_plan["quality_gate_examples"]) == (
        10000,
        160000,
    )
    guard(train_plan)
    prior_status = read(BASE / "runs/packed-isotropic-mixed16-first32000-review-workflow-v1.json")
    assert prior_status["status"].startswith("completed-")
    assert all(not alive(prior_status[k]) for k in ["controller", "child"])
    old = read(OLD / "plan.json")
    guard(old)
    ROOT.mkdir()
    work, tools = ROOT / "work", ROOT / "tools"
    shutil.copytree(OLD / "work", work, symlinks=True)
    tools.mkdir()
    for source in (REPO / "scripts").glob("*.py"):
        shutil.copyfile(source, tools / source.name)
    shutil.copyfile(
        OLD / "tools/review_mixed_packed_trial.py", tools / "review_mixed_packed_initial.py"
    )
    shutil.copyfile(
        REPO / "scripts/review_mixed_packed_quarter.py", tools / "review_mixed_packed_trial.py"
    )
    shutil.copyfile(OLD / "controller.py", ROOT / "legacy_review_controller.py")
    shutil.copyfile(__file__, ROOT / "controller.py")
    budget = [
        {
            "label": "V71-original-RAW40k-same160000examples",
            "path": str(BASE / "models/no-dino-packed-isotropic-b4-v71-step40000.pt"),
            "sha256": "5708fdc19542ca1ef1aaafec25038dc049e4f5027782809846cf6d888ebed2cc",
        },
        {
            "label": "V70-original-DINO-RAW40k-same160000examples",
            "path": str(BASE / "models/dino-packed-isotropic-b4-v70-step40000.pt"),
            "sha256": "4c2926e77dc5dea8580879eff9ebb69550fa891a295fa329a5800189c7fa8337",
        },
    ]
    assert all(sha(c["path"]) == c["sha256"] for c in budget)
    new = copy.deepcopy(old)
    panels = ["known", "unseen", "full427", "analytic", "gfx", "three-camera", "colored-CPU"]
    outputs = {k: str(BASE / f"evaluation/packed-isotropic-mixed16-quarter-{k}-v1") for k in panels}
    extras = {
        k: str(BASE / f"evaluation/packed-isotropic-mixed16-quarter-{name}-v1")
        for k, name in [
            ("grid", "hue"),
            ("extra", "GFX-highlights"),
            ("sensitivity", "source-sensitivity"),
        ]
    }
    assert all(not Path(p).exists() for p in [*outputs.values(), *extras.values()])
    checkpoints = [a["target"] for a in train_plan["arms"]] + [c["path"] for c in old["references"]]
    primary = checkpoints + [c["path"] for c in budget]
    manifests = old["manifests"]
    for key in ["known", "unseen"]:
        (ROOT / f"stage-{key}.py").write_text(
            "from pathlib import Path\nfrom demosaic.real_suite import evaluate_pairs\n"
            + f'evaluate_pairs({primary!r},Path({manifests[key]!r}),Path({outputs[key]!r}),rawnind=Path({old["rawnind"]!r}),batch_size=4,precision="float32")\n'
        )
    (ROOT / "stage-full427.py").write_text(
        "from pathlib import Path\nfrom demosaic.suite import run_suite\n"
        + f'run_suite({primary!r},Path({manifests["full427"]!r}),Path({outputs["full427"]!r}),"configs/evaluation.yaml",batch_size=2,synthetic_count=16,rawnind=Path({old["rawnind"]!r}),precision="float32")\n'
    )
    inputs = {
        **old["inputs"],
        str(OLD / "plan.json"): sha(OLD / "plan.json"),
        str(training["plan"]["path"]): training["plan"]["sha256"],
    }
    for c in budget:
        inputs[c["path"]] = c["sha256"]
    original = BASE / "runs/no-dino-packed-isotropic-b4-v71-quarter/metrics.jsonl"
    inputs[str(original)] = sha(original)
    for panel, filename in [
        ("known", "per-crop.jsonl"),
        ("unseen", "per-crop.jsonl"),
        ("full427", "per-image.jsonl"),
    ]:
        for name in ["summary.json", filename]:
            p = Path(old["outputs"][panel]) / name
            inputs[str(p)] = sha(p)
    initial_registry = REPO / "docs/results/packed-isotropic-mixed16-first32000-review-v1.json"
    inputs[str(initial_registry)] = sha(initial_registry)
    new.update(
        work=str(work),
        tools=str(tools),
        training_workflow=str(TRAINING),
        training_plan=ref(training["plan"]["path"]),
        previous_owner=training["controller"],
        initial_review_plan=ref(OLD / "plan.json"),
        initial_quality_registry=ref(initial_registry),
        matched_budget_references=budget,
        original_RAW_metrics=ref(original),
        outputs=outputs,
        checkpoints_to_evaluate=checkpoints,
        primary_checkpoints=primary,
        statistics=str(ROOT / "primary-scores.json"),
        progress=str(ROOT / "own-parent-progress.json"),
        analytic_audit=str(ROOT / "analytic-statistics-audit.json"),
        legacy_controller=ref(ROOT / "legacy_review_controller.py"),
        **extras,
        inputs=inputs,
        guards={str(p): sha(p) for p in ROOT.rglob("*") if p.is_file() and ".cache" not in p.parts},
        scope="Wait for exact2k->10k mixed16 controller and final child exit; require both finite full-state160k-example endpoints, actual CUDA model/Adam/RNG/EMA and next16 input restoration, unchanged source/schedule and403 logged pair/original observation matches. Eleven freshly FP32 primary methods on known792/unseen990/full136444 cases, mature and old equal160k-example controls, fullGFX12RGB16, foliage/fence/sky/building, three cached cameras, selected colors, fresh FP32 hue, supplementary highlights, independent audits and fixed-cohort sensitivities. Reuse existing2k parent scores only for separate24-metric progress comparisons after exact protocol/coverage/classical witnesses. Full native visual review/quality decision remain manual; no training, promotion, protected-final scores or automatic extension. Single shared-machine times are descriptive.",
    )
    (ROOT / "plan.json").write_text(json.dumps(new, indent=2) + "\n")
    guard(new)
    print(
        json.dumps(
            {
                "prepared": ref(ROOT / "plan.json"),
                "inputs": len(inputs),
                "guards": len(new["guards"]),
            }
        )
    )


def run():
    assert not STATUS.exists()
    plan = read(ROOT / "plan.json")
    guard(plan)
    spec = importlib.util.spec_from_file_location(
        "frozen_initial_review_controller", plan["legacy_controller"]["path"]
    )
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    legacy.ROOT, legacy.STATUS, legacy.TRAINING = ROOT, STATUS, TRAINING
    original_record = legacy.record

    def record(status, **values):
        if (
            status
            == "completed-mixed16-panels-statistics-artifacts-hue-and-sensitivities-awaiting-native-quality-review"
        ):
            status = "completed-quarter-main-panels-before-independent-parent-progress-and-analytic-audit"
        return original_record(status, **values)

    legacy.record = record
    try:
        legacy.run()
        # The serial runner has already checked completion/exact owner exit.
        sys.path[:0] = [plan["tools"], str(Path(plan["work"]) / "src")]
        import torch
        from review_mixed_packed_trial import completed, progress

        torch.set_num_threads(2)
        _training, checkpoints, _ = completed(plan)
        result = progress(plan, checkpoints)
        assert not Path(plan["progress"]).exists()
        Path(plan["progress"]).write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        env = {
            **os.environ,
            "CUDA_VISIBLE_DEVICES": "",
            "PYTHONPATH": str(Path(plan["work"]) / "src") + ":" + plan["tools"],
            "OMP_NUM_THREADS": "2",
            "OPENBLAS_NUM_THREADS": "2",
        }
        with (ROOT / "independent-analytic-summary.log").open("xb") as log:
            child = subprocess.Popen(
                [
                    plan["python"],
                    "-P",
                    str(Path(plan["tools"]) / "audit_analytic_summary.py"),
                    "--root",
                    plan["outputs"]["analytic"],
                    "--candidates",
                    "4",
                    "--output",
                    plan["analytic_audit"],
                ],
                cwd=plan["work"],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            legacy.record("independent-analytic-summary", child=owner)
            assert child.wait() == 0 and not alive(owner)
        guard(plan)
        legacy.record(
            "completed-mixed16-quarter-panels-statistics-artifacts-hue-sensitivities-and-parent-progress-awaiting-native-quality-review",
            progress=ref(plan["progress"]),
            analytic=ref(plan["analytic_audit"]),
            no_quality_decision_or_promotion=True,
        )
    except BaseException as error:
        if legacy.INFO:
            legacy.record("failed-no-automatic-restart-or-promotion", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
    else:
        with (REPO / ".cache/packed-isotropic-mixed16-quarter-review-v1.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            run()
