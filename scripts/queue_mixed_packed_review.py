"""Freeze and queue the mixed16 quality review behind its exact training owner."""

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import psutil

REPO = Path("/home/dllu/proj/demosaic")
BASE = Path("/mnt/external/demosaic")
ROOT = BASE / "benchmarks/packed-isotropic-mixed16-first32000-review-workflow-v1"
STATUS = BASE / "runs/packed-isotropic-mixed16-first32000-review-workflow-v1.json"
TRAINING = BASE / "runs/packed-isotropic-mixed16-first32000-workflow-v1.json"
INFO = {}


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return (
            abs(process.create_time() - owner["created"]) < 0.01
            and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def resources():
    assert psutil.virtual_memory().available > 32 * 2**30
    # Downloader retains512GiB. Leave500GiB free throughout this read-only
    # review; twelve full102MP RGB16 exports occupy about6.84GiB in total.
    assert shutil.disk_usage(BASE).free > 500 * 2**30


def guard(plan):
    for path, digest in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == digest, path


def record(status, **values):
    INFO.update(values)
    temporary = STATUS.with_suffix(".tmp")
    temporary.write_text(
        json.dumps({**INFO, "status": status, "updated_unix": time.time()}, indent=2) + "\n"
    )
    temporary.replace(STATUS)


def prepare():
    assert not ROOT.exists() and not STATUS.exists()
    resources()
    training = read(TRAINING)
    assert (
        alive(training["controller"])
        or training["status"]
        == "completed-matched-mixed16-first32000-examples-awaiting-full-quality-review"
    )
    assert training["plan"] == ref(training["plan"]["path"])
    train_plan = read(training["plan"]["path"])
    assert (
        train_plan["quality_gate_updates"] == 2000 and train_plan["quality_gate_examples"] == 32000
    )
    old_plan = BASE / "benchmarks/packed-isotropic-quarter-review-workflow-v1/plan.json"
    old = read(old_plan)
    ROOT.mkdir()
    work, tools = ROOT / "work", ROOT / "tools"
    package = work / "src/demosaic"
    package.mkdir(parents=True)
    for source in (Path(train_plan["work"]) / "src/demosaic").glob("*.py"):
        shutil.copyfile(source, package / source.name)
    for name in [
        "pyproject.toml",
        "uv.lock",
        "third_party/dinov3/LICENSE.md",
        "third_party/gaussian/Noise2VST-LICENSE",
        "third_party/gaussian/KAIR-LICENSE",
        "configs/evaluation.yaml",
        "configs/gfx-qualitative-20231231.json",
        "configs/gfx-qualitative-20231231-highlights.json",
        "configs/real-camera-qualitative.json",
    ]:
        target = work / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / name, target)
    (work / ".cache").mkdir()
    for name in ["gfx-qualitative-20231231", "real-camera-qualitative"]:
        (work / ".cache" / name).symlink_to(REPO / ".cache" / name, target_is_directory=True)
    tools.mkdir()
    for source in (REPO / "scripts").glob("*.py"):
        shutil.copyfile(source, tools / source.name)
    shutil.copyfile(__file__, ROOT / "controller.py")
    references = old["references"]
    budget = [
        {
            "label": "V71-original-RAW8k-same32000examples",
            "path": str(BASE / "models/no-dino-packed-isotropic-b4-v71-step8000.pt"),
            "sha256": "abd7345c080cb227d77385647c74614c0416d9316ad2f28c81c31cdd1f1697a2",
        },
        {
            "label": "V70-original-DINO-RAW8k-same32000examples",
            "path": str(BASE / "models/dino-packed-isotropic-b4-v70-step8000.pt"),
            "sha256": "5fc021488d34df6ddf85cac8b0fc5cb0b0117713c87865c010e7e246979a2c14",
        },
    ]
    for item in [*references, *budget]:
        assert ref(item["path"])["sha256"] == item["sha256"]
    panels = ["known", "unseen", "full427", "analytic", "gfx", "three-camera", "colored-CPU"]
    outputs = {
        key: str(BASE / f"evaluation/packed-isotropic-mixed16-first32000-{key}-v1")
        for key in panels
    }
    extra, grid, sensitivity = [
        str(BASE / f"evaluation/packed-isotropic-mixed16-first32000-{key}-v1")
        for key in ["GFX-highlights", "hue", "source-sensitivity"]
    ]
    assert all(not Path(path).exists() for path in [*outputs.values(), extra, grid, sensitivity])
    checkpoints = [a["target"] for a in train_plan["arms"]] + [c["path"] for c in references]
    primary = checkpoints + [c["path"] for c in budget]
    manifests = {
        key: read(Path(old["outputs"][key]) / "summary.json")["prepared_manifest"]
        for key in ["known", "unseen"]
    }
    manifests["full427"] = read(Path(old["outputs"]["full427"]) / "summary.json")["manifest"]
    for key in ["known", "unseen"]:
        (ROOT / f"stage-{key}.py").write_text(
            "from pathlib import Path\nfrom demosaic.real_suite import evaluate_pairs\n"
            + f'evaluate_pairs({primary!r},Path({manifests[key]!r}),Path({outputs[key]!r}),rawnind=Path({old["rawnind"]!r}),batch_size=4,precision="float32")\n'
        )
    (ROOT / "stage-full427.py").write_text(
        "from pathlib import Path\nfrom demosaic.suite import run_suite\n"
        + f'run_suite({primary!r},Path({manifests["full427"]!r}),Path({outputs["full427"]!r}),"configs/evaluation.yaml",batch_size=2,synthetic_count=16,rawnind=Path({old["rawnind"]!r}),precision="float32")\n'
    )
    inputs = [
        Path(training["plan"]["path"]),
        *(Path(p) for p in manifests.values()),
        *(Path(c["path"]) for c in [*references, *budget]),
    ]
    inputs += [
        Path(old[key]) for key in ["grid_inputs", "extra_inputs", "extra_input_audit", "cohorts"]
    ]
    inputs += [
        Path(old["artifact_parent_registry"]["path"]),
        BASE / "evaluation/fresh-none-colored-flats-cpu-v1/plan.json",
        Path(old["rawnind_weights"]["path"]),
        Path(old["rawnind"]) / "raw_denoiser.py",
    ]
    caches = []
    selection = read(REPO / "configs/gfx-qualitative-20231231.json")
    local_paths = [REPO / selection[key] for key in ["noisy", "reference"]]
    camera_selection = read(REPO / "configs/real-camera-qualitative.json")
    local_paths += [REPO / item["source"] for item in camera_selection]
    for path in local_paths:
        path = path.resolve()
        assert path.is_relative_to(REPO) or path.is_relative_to(BASE)
        caches.append(ref(path))
        inputs.append(path)
    for item in camera_selection:
        assert sha(REPO / item["source"]) == item["source_sha256"]
    inputs.append(old_plan)
    original_metrics = BASE / "runs/no-dino-packed-isotropic-b4-v71/metrics.jsonl"
    inputs.append(original_metrics)
    for key in ["known", "unseen"]:
        for case in read(manifests[key])["cases"]:
            if case["metadata"].get("adc_white_level") is None:
                path = Path(case["noisy"]["path"]).resolve()
                assert path.is_relative_to(BASE) and sha(path) == case["noisy"]["sha256"]
                inputs.append(path)
    nl = Path(old["nonlocal_reference"]["path"])
    inputs += [
        nl / name
        for name in [
            "receipt.json",
            "inspection-cpu-v1/receipt.json",
            "native-cuda-build-v1/receipt.json",
            "patchmatch-dependency-v1/receipt.json",
            "patchmatch-native-build-v1/receipt.json",
            "deform-dependency-v1/receipt.json",
            "rawnoise_25_15_9nbr.ckpt",
        ]
    ]
    plan = {
        "python": train_plan["python"],
        "work": str(work),
        "tools": str(tools),
        "training_workflow": str(TRAINING),
        "training_plan": ref(training["plan"]["path"]),
        "previous_owner": training["controller"],
        "references": references,
        "matched_budget_references": budget,
        "original_RAW_metrics": ref(original_metrics),
        "checkpoints_to_evaluate": checkpoints,
        "primary_checkpoints": primary,
        "primary_precision": "float32",
        "rawnind": old["rawnind"],
        "rawnind_weights": old["rawnind_weights"],
        "nonlocal_reference": old["nonlocal_reference"],
        "outputs": outputs,
        "statistics": str(ROOT / "primary-scores.json"),
        "grid": grid,
        "extra": extra,
        "sensitivity": sensitivity,
        **{
            key: old[key]
            for key in [
                "grid_inputs",
                "extra_inputs",
                "extra_input_audit",
                "cohorts",
                "artifact_parent_registry",
            ]
        },
        "raw_caches": caches,
        "manifests": manifests,
        "inputs": {str(p.resolve()): sha(p) for p in inputs},
        "guards": {
            str(p): sha(p) for p in ROOT.rglob("*") if p.is_file() and ".cache" not in p.parts
        },
        "scope": "Both actual2k-optimizer/8k-data/32000-example boundaries must succeed and exact controller/final child exit. Independently verify immutable12-update prefix and full-state resume, final finite model/EMA/Adam/RNG, source bundles, pinned DINO and all82 logged data/noise/LR/example groups. Six NN+two RawNIND+three classical methods on primary panels: known792/unseen990/full136444 records, all freshly FP32. Auxiliary new pair+V43/V63:2240 analytic,6 fullGFX/12RGB16,three cached cameras,128 selected CPU colors,4704 new FP32 hue predictions; no old FP16 array reuse. Thirteen model pairs across3panels=156 metrics/39 classical witnesses,117 fixed-cohort sensitivities. Native100% triplets with exact synthetic GT and correctly labeled real references, foliage/fence/sky/building. No new source admission, protected-final scoring, training, output fitting, automatic continuation or promotion. Actual native visual review and quality decision remain manual. Full-frame times are single shared-machine observations, not a throughput experiment.",
    }
    (ROOT / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    guard(plan)
    print(
        json.dumps(
            {
                "plan": ref(ROOT / "plan.json"),
                "guards": len(plan["guards"]),
                "inputs": len(plan["inputs"]),
                "prepared_only": True,
            }
        ),
        flush=True,
    )


def run():
    assert not STATUS.exists()
    plan = read(ROOT / "plan.json")
    guard(plan)
    INFO.update(
        controller={
            "pid": os.getpid(),
            "created": psutil.Process().create_time(),
            "driver_sha256": sha(__file__),
        },
        plan=ref(ROOT / "plan.json"),
        previous_owner=plan["previous_owner"],
        outputs=plan["outputs"],
        primary_complete=False,
    )
    record("waiting-for-exact-mixed16-training-owner-exit-no-inference")
    while alive(plan["previous_owner"]):
        time.sleep(15)
    sys.path[:0] = [plan["tools"], str(Path(plan["work"]) / "src")]
    import torch
    from review_mixed_packed_trial import completed

    torch.set_num_threads(2)
    _training, checkpoints, _ = completed(plan)
    assert not torch.cuda.is_initialized()
    INFO["checkpoints"] = checkpoints
    env = {
        **os.environ,
        "PYTHONPATH": str(Path(plan["work"]) / "src") + ":" + plan["tools"],
        "HF_HUB_OFFLINE": "1",
        "OMP_NUM_THREADS": "4",
        "OPENBLAS_NUM_THREADS": "2",
    }
    tools, out = Path(plan["tools"]), {k: Path(v) for k, v in plan["outputs"].items()}
    cp = plan["checkpoints_to_evaluate"]

    def stage(name, arguments, cpu=False):
        resources()
        guard(plan)
        with (ROOT / (name + ".log")).open("xb") as log:
            child = subprocess.Popen(
                [plan["python"], "-P", *map(str, arguments)],
                cwd=plan["work"],
                env={**env, **({"CUDA_VISIBLE_DEVICES": ""} if cpu else {})},
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record(name, child=owner)
            assert child.wait() == 0, name
            assert not alive(owner)
        guard(plan)

    common = ["--plan", ROOT / "plan.json", "--workflow", STATUS]
    operator = tools / "review_mixed_packed_trial.py"
    stage(
        "independent-completed-training-boundary",
        [operator, "training", *common, "--output", ROOT / "training-audit.json"],
        True,
    )
    for key, filename, count in [
        ("known", "per-crop.jsonl", 792),
        ("unseen", "per-crop.jsonl", 990),
        ("full427", "per-image.jsonl", 136444),
    ]:
        stage("evaluating-" + key, [ROOT / f"stage-{key}.py"])
        assert sum(1 for _ in (out[key] / filename).open()) == count
    stage(
        "evaluating-analytic",
        [
            tools / "evaluate_texture_candidates.py",
            *cp,
            "--precision",
            "float32",
            "--output",
            out["analytic"],
        ],
    )
    assert sum(1 for _ in (out["analytic"] / "per-case.jsonl").open()) == 2240
    stage(
        "evaluating-full-GFX-and-RawNIND",
        [
            tools / "report_raw_pair.py",
            "configs/gfx-qualitative-20231231.json",
            *cp,
            "--full-frame",
            "--rawnind",
            plan["rawnind"],
            "--rawnind-gain-modes",
            "cfa-ls",
            "cfa-channel",
            "--precision",
            "float32",
            "--output",
            out["gfx"],
        ],
    )
    stage(
        "evaluating-three-cached-cameras",
        [
            tools / "compare_raw_crops.py",
            "configs/real-camera-qualitative.json",
            *cp,
            "--rawnind",
            plan["rawnind"],
            "--rawnind-gain-modes",
            "cfa-channel",
            "--precision",
            "float32",
            "--output",
            out["three-camera"],
        ],
    )
    stage(
        "evaluating-selected-CPU-colors",
        [
            tools / "evaluate_saved_color_flats.py",
            *cp,
            "--inputs",
            BASE / "evaluation/fresh-none-colored-flats-cpu-v1/plan.json",
            "--output",
            out["colored-CPU"],
        ],
        True,
    )
    assert len(read(out["colored-CPU"] / "report.json")["float_predictions"]) == 128
    stage(
        "independent-selected-CPU-colors",
        [
            tools / "audit_saved_color_flats.py",
            "--report",
            out["colored-CPU"] / "report.json",
            "--output",
            out["colored-CPU"] / "independent-audit",
            "--additional-palette",
            "fabric-cyclic-gbr",
            "--additional-palette",
            "fabric-cyclic-brg",
        ],
        True,
    )
    record("completed-primary-before-statistics", primary_complete=True)
    stage(
        "independent-primary-statistics",
        [operator, "scores", *common, "--output", plan["statistics"]],
        True,
    )
    assert len(read(plan["statistics"])["comparisons"]) == 156
    stage(
        "evaluating-fresh-FP32-hue-grid-and-released-RAW-reference",
        [operator, "hue", *common, "--output", plan["grid"]],
    )
    grid = Path(plan["grid"])
    assert read(grid / "report.json")["prediction_work"] == {
        "new_inference": 4704,
        "reused_verified_arrays": 0,
    }
    stage(
        "independent-hue-cases",
        [
            tools / "audit_saved_color_flats.py",
            "--report",
            grid / "report.json",
            "--output",
            grid / "independent-audit",
        ],
        True,
    )
    stage(
        "independent-hue-groups",
        [
            tools / "audit_color_grid_summary.py",
            "--report",
            grid / "report.json",
            "--case-audit",
            grid / "independent-audit/audit.json",
            "--output",
            grid / "group-summary-audit.json",
        ],
        True,
    )
    stage(
        "independent-native-artifacts",
        [operator, "artifacts", *common, "--output", ROOT / "artifact-audit.json"],
        True,
    )
    stage(
        "supplementary-neon-platform",
        [
            tools / "evaluate_gfx_highlight_inputs.py",
            *cp,
            "--inputs",
            plan["extra_inputs"],
            "--input-audit",
            plan["extra_input_audit"],
            "--rawnind",
            plan["rawnind"],
            "--output",
            plan["extra"],
        ],
        True,
    )
    extra = Path(plan["extra"])
    stage(
        "independent-supplementary-GFX",
        [
            tools / "audit_gfx_highlight_comparison.py",
            "--report",
            extra / "report.json",
            "--output",
            extra / "independent-audit.json",
        ],
        True,
    )
    stage(
        "fixed-source-sensitivities",
        [
            tools / "report_commons_source_sensitivity.py",
            "--statistics",
            plan["statistics"],
            "--statistics-sha256",
            sha(plan["statistics"]),
            "--cohorts",
            plan["cohorts"],
            "--cohort-sha256",
            sha(plan["cohorts"]),
            "--output",
            plan["sensitivity"],
        ],
        True,
    )
    stage(
        "independent-source-sensitivities",
        [tools / "audit_commons_source_sensitivity.py", plan["sensitivity"]],
        True,
    )
    assert len(read(Path(plan["sensitivity"]) / "result.json")["comparisons"]) == 117
    record(
        "completed-mixed16-panels-statistics-artifacts-hue-and-sensitivities-awaiting-native-quality-review",
        training=ref(plan["training_workflow"]),
        statistics=ref(plan["statistics"]),
        hue=ref(grid / "report.json"),
        artifacts=ref(ROOT / "artifact-audit.json"),
        supplementary=ref(extra / "report.json"),
        source_sensitivity=ref(Path(plan["sensitivity"]) / "result.json"),
        no_quality_decision_or_promotion=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        prepare()
    else:
        with (REPO / ".cache/packed-isotropic-mixed16-review-v1.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                run()
            except BaseException as error:
                if INFO:
                    record("failed-no-automatic-restart-or-promotion", error=repr(error))
                raise
