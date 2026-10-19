"""Start the validated serial review, CPU closure and retained-reference queue."""

import argparse
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from train_directional_interval_trial import guard, read, ref, save


def identity(process):
    return {"pid": process.pid, "created": psutil.Process(process.pid).create_time()}


def wait_status(path, owner):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        process = psutil.Process(owner["pid"])
        if process.create_time() != owner["created"] or process.status() == psutil.STATUS_ZOMBIE:
            raise RuntimeError("Queued owner exited before publishing its wait status")
        if path.exists():
            status = read(path)
            assert status["controller"] == owner
            if status["status"].startswith("failed-"):
                raise RuntimeError("Queued owner failed; inspect its log")
            return
        time.sleep(0.1)
    raise RuntimeError("Queued owner did not publish its wait status")


def main(plan_path, preflight_path):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") != "", "Review must inherit a visible CUDA device"
    plan = read(plan_path)
    guard(plan)
    preflight = read(preflight_path)
    assert (
        preflight["status"] == "completed-historical-bank-review-preflight-no-new-quality-evidence"
    )
    assert preflight["comparison_rows_exact"] == 108 and len(preflight["CPU_portability"]) == 2
    assert preflight["CUDA_initialized"] is False
    status = read(plan["training_status"])
    assert status["controller"] == plan["training_owner"]
    process = psutil.Process(status["controller"]["pid"])
    assert (
        process.create_time() == status["controller"]["created"]
        and process.status() != psutil.STATUS_ZOMBIE
    )
    root, work = Path(plan["root"]), Path(plan["work"])
    with (root / "queue.claim").open("x") as stream:
        stream.write(str(os.getpid()))
    source = root / "queue-source.py"
    shutil.copyfile(__file__, source)
    env = dict(
        os.environ,
        PYTHONPATH=os.pathsep.join(str(work / p) for p in ("src", "scripts")),
        HF_HOME=plan["HF_HOME"],
        HF_HUB_OFFLINE="1",
    )
    cpu_env = {**env, "CUDA_VISIBLE_DEVICES": ""}
    started = []

    def launch(name, command, environment):
        with (root / (name + "-controller.log")).open("xb") as log:
            p = subprocess.Popen(
                [plan["python"], "-P", *command],
                cwd=work,
                env=environment,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        owner = identity(p)
        started.append(owner)
        save(
            root / (name + "-launch.json"),
            {"owner": owner, "launched_unix": time.time(), "command": command},
        )
        return owner

    try:
        review = launch("review", [plan["worker"]["path"], "controller", str(plan_path)], env)
        wait_status(root / "status.json", review)
        closure = read(root / "closure-template.json")
        closure["review_owner"] = review
        save(root / "closure-plan.json", closure)
        close_owner = launch(
            "closure", [closure["worker"]["path"], str(root / "closure-plan.json")], cpu_env
        )
        wait_status(root / "closure-status.json", close_owner)
        supplement = read(root / "reference-template.json")
        supplement["closure_owner"] = close_owner
        save(root / "reference-plan.json", supplement)
        references = launch(
            "reference", [supplement["worker"]["path"], str(root / "reference-plan.json")], cpu_env
        )
        time.sleep(0.2)
        for item in started:
            p = psutil.Process(item["pid"])
            assert p.create_time() == item["created"] and p.status() != psutil.STATUS_ZOMBIE
        guard(plan)
        save(
            root / "queue-launch.json",
            {
                "status": "queued-exact-training-exit-review-and-CPU-closure-manual-review-pending",
                "plan": ref(plan_path),
                "preflight": ref(preflight_path),
                "source": ref(source),
                "review_owner": review,
                "closure_owner": close_owner,
                "reference_owner": references,
                "closure_plan": ref(root / "closure-plan.json"),
                "reference_plan": ref(root / "reference-plan.json"),
                "scope": "No new inference while training is live. Serial full10-stage review after exact successful training exit; then CPU saved-array/criteria/native boards and retained V43/RawNIND supplement. Actual visual inspection and final quality decision remain required; no automatic promotion or retry.",
            },
        )
        print({"queue": ref(root / "queue-launch.json"), "owners": started})
    except BaseException as error:
        # These groups belong only to this queue; never terminate the trainer.
        for item in reversed(started):
            try:
                p = psutil.Process(item["pid"])
                if p.create_time() == item["created"]:
                    os.killpg(item["pid"], signal.SIGTERM)
            except (psutil.NoSuchProcess, ProcessLookupError):
                pass
        save(root / "queue-failure.json", {"error": repr(error), "owners": started})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--preflight", type=Path, required=True)
    args = parser.parse_args()
    main(args.plan.absolute(), args.preflight.absolute())
