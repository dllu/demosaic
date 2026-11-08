"""Shared, source-bound V195 preparation and resource helpers; no Torch import."""

import ast
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import psutil
from phase_admission_protocol import owner_live, read, ref

REPO = Path("/home/dllu/proj/demosaic")
BASE = REPO / ".cache/quality-20261108"
CPU = BASE / "V195-directional-response-CPU-v1"
ADMISSION = BASE / "V195-directional-response-admission-v1"
TRIAL = BASE / "V195-directional-response-trial-v1"
MODES = ("whole", "directional")


def save(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def factory(config):
    from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail

    return LatePooledPhaseWaveDetail(**config)


def dependency():
    index = REPO / "docs/results/v187-pooled-wave-final-v1.json"
    proof = REPO / "docs/results/v187-pooled-wave-publication-verification-v1.json"
    final, verified = read(index), read(proof)
    assert final["status"].startswith("completed-")
    assert verified["status"].startswith("pass-") and verified["publication"] == ref(index)
    donor = final["checkpoints"]["V187-pooled-wave-EMA"]
    old = Path(final["plan"]["path"]).parent
    for name, result in [("wave-train", "wave-train-result-v1.json"), ("review", "scores-v1.json")]:
        assert not owner_live(read(old / f"{name}-launch-v1.json")["owner"])
        assert read(old / result)["status"].startswith("completed-")
    for binding in [donor["export"], donor["frozen_V183_initializer"]["export"]]:
        assert ref(binding["path"]) == binding
    cpu_result = read(CPU / "result-v2.json")
    assert cpu_result["status"].startswith("pass-V195-CPU-native-directional-loss")
    assert cpu_result["output_gradient_coordinates"] == 53477376
    assert "26 passed" in (CPU / "CPU-tests-v2.log").read_text()
    neural = read(REPO / "docs/results/v193-completed-execution-v1.json")[
        "previous103_neural_hashes_unchanged"
    ]
    assert len(neural) == 103
    for name, digest in neural.items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    return {
        "publication": ref(index),
        "verification": ref(proof),
        "donor": donor,
        "initializer": donor["frozen_V183_initializer"],
        "CPU_result": ref(CPU / "result-v2.json"),
        "CPU_tests": ref(CPU / "CPU-tests-v2.log"),
        "neural103": neural,
        "V187_plan": final["plan"],
    }


def freeze(root, entries):
    """Snapshot only code and its local import closure, never data or artifacts."""
    work = root / "work"
    shutil.copytree(
        REPO / "src", work / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
    )
    pending = list(entries)
    copied = set()
    while pending:
        name = pending.pop()
        if name in copied:
            continue
        source = REPO / "scripts" / name
        target = work / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        copied.add(name)
        for node in ast.walk(ast.parse(source.read_text())):
            names = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and not node.level and node.module:
                names = [node.module]
            for imported in names:
                candidate = imported.split(".")[0] + ".py"
                if (REPO / "scripts" / candidate).is_file():
                    pending.append(candidate)
    return work, {str(p): ref(p)["sha256"] for p in work.rglob("*.py")}


def guard(plan, entry=None):
    if entry is not None:
        assert ref(entry) == plan["runner"], "Execute the sealed runner"
    for binding in plan["inputs"]:
        assert ref(binding["path"]) == binding
    for name, digest in plan["frozen_files"].items():
        assert ref(name)["sha256"] == digest


def resources(plan):
    available = {"local": shutil.disk_usage(REPO).free, "RAM": psutil.virtual_memory().available}
    for key, floor in plan["minimum_GiB"].items():
        assert available[key] > floor * 2**30, (key, available[key], floor)


def launch(root, phase, *, mode=None):
    plan = read(root / "plan-v1.json")
    guard(plan)
    assert psutil.virtual_memory().available > plan["launch_RAM_GiB"] * 2**30
    resources(plan)
    name = mode or phase
    assert not (root / f"{name}-launch-v1.json").exists()
    env = dict(
        os.environ,
        PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
        CUDA_VISIBLE_DEVICES="0",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    command = [str(REPO / ".venv/bin/python"), plan["runner"]["path"], phase]
    if mode:
        command += ["--mode", mode]
    with (root / f"{name}-v1.log").open("xb") as log:
        process = subprocess.Popen(
            command, cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True
        )
    owner = {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}
    save(root / f"{name}-launch-v1.json", {"owner": owner, "plan": ref(root / "plan-v1.json")})
    return owner


def require_launch(root, name):
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    for _ in range(60):
        try:
            assert read(root / f"{name}-launch-v1.json")["owner"] == owner
            return owner
        except (FileNotFoundError, json.JSONDecodeError):
            time.sleep(0.2)
    raise RuntimeError("Missing matching launch owner; CUDA not initialized")


def runtime(plan):
    from train_coherent_pair_evidence_engine import runtime as existing_runtime

    existing_runtime(plan)


def objective_total(terms, weight):
    import numpy as np
    from audit_coherent_pair_evidence_trial import loss_from_terms

    base = loss_from_terms({k: v for k, v in terms.items() if k != "response_addition"}, weight)
    return float(
        np.float32(
            np.float32(base) + np.float32(0.25 * weight) * np.float32(terms["response_addition"])
        )
    )
