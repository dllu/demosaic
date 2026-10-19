"""Wait for exact review owners, then prepare private native report assets."""

import argparse
import os
import signal
import subprocess
import time
from pathlib import Path

import psutil
from close_directional_bank_review import alive
from train_directional_interval_trial import read, ref, save


def main(plan_path):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    os.nice(10)
    plan = read(plan_path)
    for item in (plan["driver"], plan["package_driver"], plan["queue"], plan["review_plan"]):
        assert ref(item["path"]) == item
    status_path = Path(plan["status"])
    queue = read(plan["queue"]["path"])
    owners = [queue[k] for k in ("review_owner", "closure_owner", "reference_owner")]
    status = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
    }

    def record(value, **details):
        status.update(status=value, updated_unix=time.time(), **details)
        save(status_path, status)
        print({"status": value}, flush=True)

    try:
        record("waiting-for-exact-review-closure-reference-owner-exits")
        review_root = Path(read(plan["review_plan"]["path"])["root"])
        while any(alive(owner) for owner in owners):
            for name in ("status.json", "closure-status.json"):
                if read(review_root / name)["status"].startswith("failed-"):
                    raise RuntimeError(
                        "Preceding review/closure failed; no report package or retry"
                    )
            time.sleep(5)
        for item in (plan["package_driver"], plan["queue"], plan["review_plan"]):
            assert ref(item["path"]) == item
        with Path(plan["log"]).open("xb") as log:
            child = subprocess.Popen(
                [
                    plan["python"],
                    "-P",
                    plan["package_driver"]["path"],
                    "--review-plan",
                    plan["review_plan"]["path"],
                    "--output",
                    plan["output"],
                ],
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            record(
                "preparing-native-report-assets",
                child={"pid": child.pid, "created": psutil.Process(child.pid).create_time()},
            )
            try:
                code = child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
                raise
            assert code == 0, "Report package failed; inspect its log"
        result = Path(plan["output"]) / "index.json"
        data = read(result)
        assert data["manual_review_completed"] is False and data["quality_decision"] is None
        record("prepared-native-report-assets-awaiting-manual-inspection", result=ref(result))
    except BaseException as error:
        record("failed-report-asset-preparation-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
