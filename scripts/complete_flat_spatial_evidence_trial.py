"""Finish the original local trial once, then stop for actual native inspection."""

import os
import shutil
import subprocess
import time

import psutil
from phase_admission_protocol import owner_live, read, ref
from train_flat_spatial_evidence_trial import REPO, ROOT, guard, own, progress, save


def main():
    owner = own()
    seal = read(ROOT / "completion-source-v1.json")
    assert seal["source"] == ref(__file__)
    plan = read(ROOT / "plan-v1.json")
    assert seal["plan"] == ref(ROOT / "plan-v1.json")
    guard(plan)
    assert ref(ROOT / "evidence-train-launch-v1.json") == seal["adopted_training_launch"]
    for binding in seal["helpers"]:
        assert ref(binding["path"]) == binding
    (ROOT / "completion.claim").open("x").close()
    save(ROOT / "completion-owner-v1.json", owner)
    os.nice(max(0, 10 - psutil.Process().nice()))
    os.sched_setaffinity(0, [6, 7])

    def status(state, **fields):
        progress("completion", dict(status=state, owner=owner, **fields))

    def wait_worker(phase, filename):
        launch = read(ROOT / f"{phase}-launch-v1.json")
        while True:
            try:
                live = owner_live(launch["owner"])
            except (psutil.AccessDenied, OSError) as error:
                status("waiting-for-owner-observation", phase=phase, error=repr(error))
                time.sleep(15)
                continue
            if not live:
                break
            status("waiting-for-" + phase, target=launch["owner"])
            time.sleep(15)
        assert not (ROOT / f"{phase}-failure-v1.json").exists()
        result = read(ROOT / filename)
        assert result["owner"] == launch["owner"] and result["status"].startswith("completed-")
        assert result["plan"] == ref(ROOT / "plan-v1.json")
        return result

    def command(label, source, *arguments, cpu=True):
        assert ref(source["path"]) == source
        log = ROOT / f"completion-{label}-v1.log"
        receipt = ROOT / f"completion-{label}-launch-v1.json"
        assert not receipt.exists()
        env = dict(
            os.environ,
            PYTHONPATH=":".join(
                str(ROOT / name)
                for name in [
                    "audit-work-v1/scripts",
                    "reduction-work-v1/scripts",
                    "render-work-v1/scripts",
                    "work/src",
                    "work/scripts",
                ]
            ),
            OPENBLAS_NUM_THREADS="1",
            OMP_NUM_THREADS="2",
            MKL_NUM_THREADS="1",
            CUBLAS_WORKSPACE_CONFIG=":4096:8",
        )
        if cpu:
            env["CUDA_VISIBLE_DEVICES"] = ""
        argv = [str(REPO / ".venv/bin/python"), source["path"], *arguments]
        with log.open("xb") as stream:
            child = subprocess.Popen(
                argv, cwd=REPO, env=env, stdout=stream, stderr=subprocess.STDOUT
            )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            save(
                receipt,
                {
                    "owner": child_owner,
                    "controller": owner,
                    "command": argv,
                    "source": source,
                    "CPU_only": cpu,
                },
            )
            status("running-" + label, child=child_owner)
            code = child.wait()
        assert code == 0, f"{label} exited {code}; preserved, no retry"

    try:
        wait_worker("evidence-train", "evidence-train-result-v1.json")
        assert not (ROOT / "training-audit-v1.json").exists()
        command("training-audit", seal["auditor"], "training")
        assert read(ROOT / "training-audit-v1.json")["status"].startswith(
            "pass-flat-spatial-terminal-"
        )
        assert (
            not (ROOT / "review-launch-v1.json").exists() and not (ROOT / "review.claim").exists()
        )
        while (
            psutil.virtual_memory().available <= 52 * 2**30
            or shutil.disk_usage(REPO).free <= (48 + 0.5 + 0.8) * 2**30
            or shutil.disk_usage("/mnt/external").free <= (111 + 0.5) * 2**30
        ):
            status("waiting-for-review-resources")
            time.sleep(15)
        command("launch-review", plan["runner"], "launch-review", cpu=False)
        wait_worker("review", "scores-v1.json")
        assert not (ROOT / "quality-audit-v1.json").exists()
        command("quality-audit", seal["auditor"], "quality")
        command("reduce", seal["reducer"])
        command("render", seal["renderer"])
        figures = read(ROOT / "figures-v1.json")
        assert figures["native_figures"] == 60 and figures["native_triplets"] == 12
        assert not figures["fixture_only_no_actual_V181_quality"] and len(figures["sheets"]) == 15
        save(
            ROOT / "completion-result-v1.json",
            {
                "status": "completed-flat-spatial-training-quality-audits-tables-render-awaiting-actual-viewing",
                "owner": owner,
                "plan": ref(ROOT / "plan-v1.json"),
                "figures": ref(ROOT / "figures-v1.json"),
                "source": ref(__file__),
                "actual_native_viewing_claimed": False,
            },
        )
        status("ready-for-actual-native-viewing", figures=ref(ROOT / "figures-v1.json"))
    except BaseException as error:
        save(
            ROOT / "completion-failure-v1.json",
            {
                "status": "failed-preserved-no-automatic-retry",
                "owner": owner,
                "error": repr(error),
                "source": ref(__file__),
            },
        )
        status("failed-preserved-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    main()
