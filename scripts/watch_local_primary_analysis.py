"""Audit and analyze weak detail after the bound20k primary evaluation closes."""

import argparse
import os
import time
from pathlib import Path

import psutil
from audit_local_primary import audit
from diagnose_archive_local_detail import analyze
from export_local_primary_archive import export

from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json


def live(identity):
    try:
        p = psutil.Process(identity["pid"])
        return p.create_time() == identity["create_time"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def run(path):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    plan = read_json(path)
    verify_plan(plan)
    assert reference(__file__) == plan["driver"]
    root = Path(plan["root"])
    (root / "analysis.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, [8, 9])
    owner = {"pid": os.getpid(), "create_time": psutil.Process().create_time()}

    def status(state, **details):
        write_json(
            root / "status.json",
            {"owner": owner, "status": state, "observed_unix": time.time(), **details},
            replace=True,
        )

    primary_result = Path(plan["expected_primary_result"])
    missing = 0
    while not primary_result.exists():
        alive = live(plan["upstream_queue_owner"])
        launch_path = Path(plan["expected_primary_launch"])
        if launch_path.exists():
            child = read_json(launch_path)
            child_plan = read_json(checked(child["plan"]))
            assert plan["upstream_queue_plan"] in child_plan["inputs"]
            alive |= live(child)
        missing = 0 if alive else missing + 1
        if missing >= 3:
            status("upstream-terminal-without-full-primary-result")
            return
        status("waiting-for-full-primary", upstream_live=alive)
        time.sleep(10)
    result = read_json(primary_result)
    assert result["all_complete"] and result["kind"] == "full" and result["cases"] == 3162
    assert len(result["models"]) == 2 and all(v["step"] == 20000 for v in result["models"].values())
    candidate = result["models"]["scale-control20k"]["checkpoint"]
    admission = read_json(Path(plan["endpoint_admission"]))
    assert candidate == admission["checkpoint"]
    status("independent-primary-audit", source_result=reference(primary_result))
    audit(primary_result, root / "independent-primary-audit")
    status("binding-native-photo-archive")
    export(primary_result, root / "native-photo-archive")
    manifest = root / "native-photo-archive/records.jsonl"
    status("full427-original-weak-band-analysis")
    parent = result["models"]["V120"]["checkpoint"]
    analyze(
        manifest,
        parent["sha256"],
        manifest,
        candidate["sha256"],
        root / "broad-local-detail",
        maximum_seconds=1800,
    )
    detail = read_json(root / "broad-local-detail/result-v1.json")
    assert (
        detail["photographic_sources"] == 427
        and detail["paired_source_noise_CFA_observations"] == 5124
    )
    assert detail["unique_source_blocks"] == 96075
    write_json(
        root / "result.json",
        {
            "plan": reference(path),
            "primary_result": reference(primary_result),
            "independent_primary_audit": reference(root / "independent-primary-audit/result.json"),
            "archive": reference(root / "native-photo-archive/result.json"),
            "broad_detail": reference(root / "broad-local-detail/result-v1.json"),
            "scope": "Complete3162-case independent photometry/CFA audit and unchanged full427/three-prior/all-CFA local weak-band analysis, original borders/masks/tolerances/source balancing. Zero new neural/GPU/RAW/noise/optimizer calls. Numerical completion is separate from actual native viewing, model recommendation and source-bound history publication.",
        },
    )
    status("numerical-audit-and-broad-detail-complete-publication-pending")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
