"""Continue after a reporting-only exception; never repeat completed parent work."""

import argparse
import json
import os
import subprocess

import numpy as np
import psutil
import torch
from directional_trial_protocol import REPO, freeze, guard, read, ref, require_launch, save
from phase_admission_protocol import owner_live
from prepare_shared_edge_cache import ROOT, cache, resource_check

from demosaic.prediction_archive import fingerprint


def validated_prefix():
    original = read(ROOT / "plan-v1.json")
    guard(original)
    failure = read(ROOT / "cache-failure-v1.json")
    assert not owner_live(failure["owner"])
    assert failure["error"] == "ValueError(\"Invalid suffix 'tmp'\")"
    assert not (ROOT / "cache-result-v1.json").exists()
    parity = read(ROOT / "parent-policy-parity-v1.json")
    assert parity["status"] == "pass-one-original-parent-bit-exact-policy-parity"
    assert all(v == 1 for v in parity["counts"].values())
    events = [json.loads(line) for line in (ROOT / "cache-trace-v1.jsonl").read_text().splitlines()]
    assert len(events) == 2 and events[0]["event"] == "before-parent"
    assert events[1]["event"] == "completed"
    assert all(v == 1 for v in events[0]["counts"].values())
    assert all(v == 2 for v in events[1]["counts"].values())
    record = events[1]["record"]
    assert record["step"] == original["selected"][0]["step"] == 4
    assert ref(record["arrays"]["path"]) == record["arrays"]
    assert ref(record["parent"]["path"]) == record["parent"]
    with np.load(record["arrays"]["path"], allow_pickle=False) as arrays:
        assert {k: fingerprint(arrays[k]) for k in arrays.files} == record["inputs"]
    assert (
        fingerprint(np.load(record["parent"]["path"], allow_pickle=False))
        == record["parent_values"]
    )
    inspection = read(ROOT / "inspection-v1.json")
    for row in inspection["batches"]:
        assert ref(row["arrays"]["path"]) == row["arrays"]
    return {"records": {4: record}, "counts": events[1]["counts"]}


def prepare():
    integration_tests = REPO / ".cache/v202-cache-integration-test-v2.log"
    assert "1 passed" in integration_tests.read_text()
    prefix = validated_prefix()
    prior_resume_failure = read(ROOT / "resume-cache-failure-v1.json")
    assert not owner_live(prior_resume_failure["owner"])
    assert (ROOT / "resume-cache-trace-v1.jsonl").stat().st_size == 0
    original = read(ROOT / "plan-v1.json")
    work, sources = freeze(ROOT / "resume-v2", ["resume_shared_edge_cache.py"])
    plan = dict(
        original,
        work=str(work),
        runner=ref(work / "scripts/resume_shared_edge_cache.py"),
        frozen_files=sources,
    )
    plan["resumption"] = {
        "original_plan": ref(ROOT / "plan-v1.json"),
        "failure": ref(ROOT / "cache-failure-v1.json"),
        "original_launch": ref(ROOT / "cache-launch-v1.json"),
        "journal": ref(ROOT / "cache-trace-v1.jsonl"),
        "parity": ref(ROOT / "parent-policy-parity-v1.json"),
        "completed_new_steps_adopted": [4],
        "completed_parent_roots": 2,
        "remaining_new_parent_roots": 155,
        "remaining_source_constructions": 150,
        "change": "Fix progress-path suffix only. Adopt original parity and step4 parent; all six inspection inputs reused. Same generator, parent weights/config/policy, noise seeds and output targets. No scientific prefix replay.",
    }
    plan["resumption"]["prior_resume_failure"] = ref(ROOT / "resume-cache-failure-v1.json")
    plan["resumption"]["prior_resume_empty_journal"] = ref(ROOT / "resume-cache-trace-v1.jsonl")
    plan["resumption_journal"] = "resume2-cache-trace-v1.jsonl"
    plan["execution_plan_path"] = str(ROOT / "resume-plan-v2.json")
    plan["inputs"] += [v for v in plan["resumption"].values() if isinstance(v, dict)]
    plan["inputs"] += [
        prefix["records"][4]["arrays"],
        prefix["records"][4]["parent"],
        ref(integration_tests),
        ref(REPO / "tests/test_shared_edge_cache_resume.py"),
    ]
    plan["CPU_reporting_failure_resume_integration"] = ref(integration_tests)
    save(ROOT / "resume-plan-v2.json", plan)
    print("Prepared resume:2parent roots/6input batches adopted;155new parents remain")


def launch(plan):
    resource_check(plan)
    assert psutil.virtual_memory().available > plan["launch_RAM_GiB"] * 2**30
    assert not (ROOT / "resume2-cache-launch-v1.json").exists()
    env = dict(
        os.environ,
        PYTHONPATH=f"{plan['work']}/src:{plan['work']}/scripts",
        CUDA_VISIBLE_DEVICES="0",
        HF_HUB_OFFLINE="1",
        OPENBLAS_NUM_THREADS="1",
        OMP_NUM_THREADS="2",
        MKL_NUM_THREADS="1",
        CUBLAS_WORKSPACE_CONFIG=":4096:8",
    )
    with (ROOT / "resume2-cache-v1.log").open("xb") as log:
        p = subprocess.Popen(
            [str(REPO / ".venv/bin/python"), plan["runner"]["path"], "resume2-cache"],
            cwd=REPO,
            env=env,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    save(
        ROOT / "resume2-cache-launch-v1.json",
        {
            "owner": {"pid": p.pid, "created": psutil.Process(p.pid).create_time()},
            "plan": ref(ROOT / "resume-plan-v2.json"),
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "launch", "resume2-cache"])
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare()
        return
    plan = read(ROOT / "resume-plan-v2.json")
    guard(plan)
    if args.phase == "launch":
        launch(plan)
        return
    assert ref(__file__) == plan["runner"]
    prefix = validated_prefix()
    owner = require_launch(ROOT, "resume2-cache")
    (ROOT / "resume2-cache.claim").open("x").close()
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [4, 5])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    try:
        cache(plan, owner, resume=prefix)
    except BaseException as error:
        save(
            ROOT / "resume2-cache-failure-v1.json",
            {"owner": owner, "error": repr(error), "status": "failed-preserved-no-retry"},
        )
        raise


if __name__ == "__main__":
    main()
