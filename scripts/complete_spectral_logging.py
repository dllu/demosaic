"""Audit the finished control's extra resume log, then run the unchanged fresh arm."""

import argparse
import ast
import copy
import importlib.util
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
from review_spectral_trial import canonical_training_rows
from train_context_trial import alive
from train_directional_bank_trial import guard, read, ref, save

from demosaic.safety import writable_path

REPO = Path(__file__).resolve().parents[1]


def prepare(previous_path, output):
    previous = read(previous_path)
    guard(previous)
    status_path = Path(previous["root"]) / "status.json"
    status = read(status_path)
    assert status["status"] == "running-source-frozen-spectral-arm" and status["arm"] == "control"
    assert alive(status["controller"]) and alive(status["child"]) and not status["completed"]
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    scripts = root / "coordinator-scripts"
    scripts.mkdir()
    for source in (REPO / "scripts").glob("*.py"):
        shutil.copyfile(source, scripts / source.name)
    tree = ast.parse(Path(previous["worker"]["path"]).read_text())
    worker = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "worker")
    expected = next(
        n.lineno
        for n in ast.walk(worker)
        if isinstance(n, ast.Assert)
        and "for r in rows" in ast.unparse(n.test)
        and "4001" in ast.unparse(n.test)
    )
    assert not Path(previous["arms"][1]["run"]).exists(), "Fresh spectral arm already exists"
    plan = copy.deepcopy(previous)
    plan.update(
        root=str(root),
        completion_metadata_of=ref(previous_path),
        original_status=str(status_path),
        original_control_owner=status["child"],
        original_controller=status["controller"],
        expected_log_assertion_line=expected,
        coordinator=ref(scripts / "complete_spectral_logging.py"),
        scope="Original control continues untouched to4000. Accept only its known post-training log-cardinality failure after independently auditing saved4000 state. Preserve extra1001 row; run unchanged fresh spectral worker for original4000. No new control update, schedule reset, model/source/noise/loss change or promotion.",
    )
    plan["inputs"] += [ref(previous_path)]
    plan["frozen_files"].update({str(p): ref(p)["sha256"] for p in scripts.glob("*.py")})
    guard(plan)
    save(root / "plan.json", plan)
    print(
        {
            "plan": ref(root / "plan.json"),
            "expected_postcheck_assertion_line": expected,
            "training_worker_unchanged": plan["worker"],
        }
    )


def collect_control(plan):
    import torch
    from audit_flat_palette import train_rows

    torch.set_num_threads(2)
    failure = read(plan["original_status"])
    assert failure["status"] == "failed-spectral-trial-no-automatic-retry"
    assert (
        failure["controller"] == plan["original_controller"]
        and failure["child"] == plan["original_control_owner"]
    )
    assert not alive(failure["controller"]) and not alive(failure["child"])
    previous = read(plan["completion_metadata_of"]["path"])
    oldroot = Path(previous["root"])
    run = Path(plan["arms"][0]["run"])
    log = oldroot / "control.log"
    text = log.read_text()
    assert f'File "{plan["worker"]["path"]}", line {plan["expected_log_assertion_line"]}' in text
    checkpoint = ref(run / "last.pt")
    assert ref(run / "step-004000.pt")["sha256"] == checkpoint["sha256"]
    state = torch.load(checkpoint["path"], weights_only=True, map_location="cpu", mmap=True)
    assert state["step"] == state["config"]["steps"] == 4000
    assert len(state["model"]) == len(state["ema"]) == 91 and len(state["optimizer"]["state"]) == 89
    for field in ["model", "ema"]:
        assert all(torch.isfinite(v).all() for v in state[field].values())
    for values in state["optimizer"]["state"].values():
        assert int(values["step"]) == 4000 and values["exp_avg_sq"].min() >= 0
        assert all(torch.isfinite(v).all() for v in values.values() if torch.is_tensor(v))
    assert state["optimizer"]["param_groups"][0]["lr"] == state["config"]["lr"] * 0.1
    rows = train_rows(run)
    canonical, extra = canonical_training_rows(rows, resume_step=1000)
    assert len(canonical) == 161 and len(extra) == 1 and extra[0]["step"] == 1001
    samples = read(oldroot / "control-observations.json")
    assert len(samples) == 176
    keyed = {r["step"]: r for r in samples}
    for row in canonical:
        assert row["batch_sha256"] == keyed[row["step"]]["source_sha256"]
        assert row["context_supervision_sha256"] == keyed[row["step"]]["actual_loss_sha256"]
    assert (
        extra[0]["batch_sha256"]
        == extra[0]["context_forward_sha256"]
        == extra[0]["context_supervision_sha256"]
    )
    initial = ref(oldroot / "control-initializations.json")
    captures = read(initial["path"])
    assert captures == [
        {
            "common_initial_state_exact": True,
            "DINO_sha256": plan["DINO_sha256"],
            "initial_output_exact_parent": False,
            "resuming": True,
        }
    ]
    result = {
        "status": "independently-audited-original4000-control-after-log-only-wrapper-failure",
        "arm": "control",
        "checkpoint": checkpoint,
        "captures": captures,
        "initializations": initial,
        "resume": plan["resume"]["control"],
        "observations": ref(oldroot / "control-observations.json"),
        "metrics": ref(run / "metrics.jsonl"),
        "logged_observations": rows,
        "actual_step": 4000,
        "planned_steps": 4000,
        "engineering_only": False,
        "source_sha256": state["config"]["source_sha256"],
        "source_snapshot": state["config"]["source_snapshot"],
        "finite_states": {"model": 91, "EMA": 91, "AdamW": 89},
        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "actual_training_owner": plan["original_control_owner"],
        "completion_failure": ref(plan["original_status"]),
        "failure_log": ref(log),
        "metadata_collector": plan["coordinator"],
        "additional_first_resume_logs": extra,
        "original_training_worker": plan["worker"],
        "post_training_DINO_and_finite_state_assertions_precede_failure": True,
        "scope": "Independent CPU endpoint/log audit after the original GPU worker finished all4000 updates and failed only its known log-cardinality assertion. The bound source and traceback reach that postcheck after original final DINO/finite-state assertions. Preserve all162 logs and176 observations. No new control inference/update or fresh direct final DINO-memory measurement is claimed.",
    }
    save(Path(plan["root"]) / "control-result.json", result)
    return result


def controller(plan_path):
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    with (root / "controller.claim").open("x") as f:
        f.write(str(os.getpid()))
    state = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": {},
        "child": plan["original_control_owner"],
    }

    def record(value, **fields):
        state.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", state)
        print({"status": value}, flush=True)

    try:
        record("waiting-for-exact-control-original4000-completion", arm="control")
        deadline = (
            plan["original_control_owner"]["created"] + plan["arm_timeout_seconds"]["control"] + 60
        )
        while alive(plan["original_controller"]) or alive(plan["original_control_owner"]):
            assert time.time() < deadline, "Original control runtime bound exhausted"
            time.sleep(5)
        control = collect_control(plan)
        state["completed"]["control"] = ref(root / "control-result.json")
        spec = importlib.util.spec_from_file_location(
            "actual_spectral_driver", plan["worker"]["path"]
        )
        driver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(driver)
        record("waiting-for-stable-original-spectral-resources", arm="spectral")
        since = None
        deadline = time.monotonic() + 14400
        while True:
            assert time.monotonic() < deadline
            values = (
                psutil.virtual_memory().available / 2**30,
                shutil.disk_usage(plan["repository"]).free / 2**30,
                shutil.disk_usage("/mnt/external").free / 2**30,
            )
            if driver.resources_allow(plan, *values, launch=True):
                since = time.monotonic() if since is None else since
                if time.monotonic() - since >= 60:
                    break
            else:
                since = None
            time.sleep(5)
        guard(plan)
        env = dict(os.environ, **plan["cache_environment"])
        env.update(
            PYTHONPATH=str(Path(plan["work"]) / "src") + ":" + str(Path(plan["work"]) / "scripts"),
            CUDA_VISIBLE_DEVICES="0",
            HF_HUB_OFFLINE="1",
            CUBLAS_WORKSPACE_CONFIG=":4096:8",
            OMP_NUM_THREADS="2",
            OPENBLAS_NUM_THREADS="2",
        )
        with (root / "spectral.log").open("xb") as log:
            child = subprocess.Popen(
                [
                    plan["python"],
                    "-P",
                    plan["worker"]["path"],
                    "worker",
                    str(plan_path),
                    "--arm",
                    "spectral",
                ],
                cwd=plan["work"],
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-source-frozen-spectral-arm", arm="spectral", child=owner)
            deadline = time.monotonic() + plan["arm_timeout_seconds"]["spectral"]
            while child.poll() is None:
                values = (
                    psutil.virtual_memory().available / 2**30,
                    shutil.disk_usage(plan["repository"]).free / 2**30,
                    shutil.disk_usage("/mnt/external").free / 2**30,
                )
                if time.monotonic() > deadline or not driver.resources_allow(plan, *values):
                    assert alive(owner) and os.getpgid(child.pid) == child.pid
                    record(
                        "stopping-exact-owned-spectral-worker-at-bound", resources_at_stop=values
                    )
                    os.killpg(child.pid, signal.SIGTERM)
                    child.wait(timeout=30)
                    raise RuntimeError("Owned spectral worker hit resource/runtime bound; no retry")
                time.sleep(5)
            assert child.wait() == 0
        state["completed"]["spectral"] = ref(root / "spectral-result.json")
        spectral = read(root / "spectral-result.json")
        first, second = (read(c["observations"]["path"]) for c in [control, spectral])
        assert first == second and len(first) == 176
        a, _ = canonical_training_rows(control["logged_observations"], resume_step=1000)
        b, _ = canonical_training_rows(spectral["logged_observations"])
        for x, y in zip(a, b, strict=True):
            assert all(
                x[k] == y[k]
                for k in ["step", "domain", "lr", "batch_sha256", "context_supervision_sha256"]
            )
        assert control["source_sha256"] == spectral["source_sha256"]
        archives = [
            {p.name: ref(p)["sha256"] for p in Path(c["source_snapshot"]).iterdir() if p.is_file()}
            for c in [control, spectral]
        ]
        assert archives[0] == archives[1]
        import torch
        from audit_flat_palette import identical

        saved = [
            torch.load(c["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
            for c in [control, spectral]
        ]
        for key in ["python_rng", "torch_rng", "cuda_rng"]:
            identical(saved[0][key], saved[1][key])
        guard(plan)
        record(
            "completed-spectral-original4000-awaiting-full-quality-and-native-review",
            matched_observations_and_final_RNG=True,
            recorded_pairs=176,
            source_archives_exact=True,
        )
    except BaseException as error:
        record("failed-spectral-log-completion-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="mode", required=True)
    a = sub.add_parser("prepare")
    a.add_argument("previous", type=Path)
    a.add_argument("output", type=Path)
    a = sub.add_parser("controller")
    a.add_argument("plan", type=Path)
    a = p.parse_args()
    if a.mode == "prepare":
        prepare(a.previous.resolve(), a.output)
    else:
        controller(a.plan.resolve())
