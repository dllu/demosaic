"""Prove external checkpoint/prefix recovery against a genuine uninterrupted CPU run."""

import argparse
import copy
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import psutil
import yaml
from train_context_trial import alive
from train_directional_bank_trial import guard, read, ref, save

from demosaic.safety import writable_path


def main(preflight_path, output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    previous = read(preflight_path)
    status_path = Path(previous["root"]) / "status.json"
    status = read(status_path)
    owner = status["controller"]
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "preflight": ref(preflight_path),
        "source": ref(__file__),
    }

    def record(value, **fields):
        info.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", info)

    try:
        record("waiting-for-exact-corrected-CPU-preflight-owner-exit", waited_owner=owner)
        deadline = time.monotonic() + 1800
        while alive(owner):
            assert time.monotonic() < deadline
            time.sleep(5)
        status = read(status_path)
        assert (
            status["controller"] == owner
            and status["status"] == "completed-spectral-engineering-preflight"
        )
        assert status["restart_full_model_EMA_AdamW_RNG_exact"]
        assert (
            previous["device"] == "cpu"
            and previous["engineering_only"]
            and previous["boundary_updates"] == 16
        )
        guard(previous)
        work, oldwork = root / "work", Path(previous["work"])
        for path in previous["frozen_files"]:
            source = Path(path)
            target = work / source.relative_to(oldwork)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        checkpoint = Path(previous["root"]) / "restart-step8.pt"
        original = read(Path(previous["root"]) / "restart-observations.json")
        prefix = [r for r in original if r["step"] <= 8]
        assert [r["step"] for r in prefix] == list(range(1, 9))
        save(root / "prefix-observations.json", prefix)
        arm = copy.deepcopy(next(a for a in previous["arms"] if a["name"] == "spectral"))
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        run = work / "runs/spectral"
        run.mkdir(parents=True)
        cfg["run"] = str(run)
        path = work / "configs/spectral.yaml"
        path.write_text(yaml.safe_dump(cfg, sort_keys=True))
        arm.update(config=str(path), run=str(run))
        oldrun = Path(next(a for a in previous["arms"] if a["name"] == "restart")["run"])
        lines = [
            s
            for s in (oldrun / "metrics.jsonl").read_text().splitlines()
            if read_line(s).get("step", 0) <= 8
        ]
        (run / "metrics.jsonl").write_text("\n".join(lines) + "\n")
        plan = copy.deepcopy(previous)
        plan.update(
            root=str(root),
            work=str(work),
            arms=[arm],
            worker=ref(work / "scripts/train_spectral_trial.py"),
            resume={
                "spectral": {
                    "step": 8,
                    "checkpoint": ref(checkpoint),
                    "observations": ref(root / "prefix-observations.json"),
                }
            },
            frozen_files={
                str(p): ref(p)["sha256"]
                for p in work.rglob("*")
                if p.is_file() and "runs" not in p.relative_to(work).parts
            },
            scope="Discarded CPU external8+8 resume adapter, retaining original4000 schedule; no quality result.",
        )
        plan["inputs"] += [
            ref(preflight_path),
            ref(status_path),
            ref(checkpoint),
            ref(root / "prefix-observations.json"),
        ]
        guard(plan)
        save(root / "plan.json", plan)
        env = dict(os.environ, **plan["cache_environment"])
        env.update(
            PYTHONPATH=str(work / "src") + ":" + str(work / "scripts"),
            CUDA_VISIBLE_DEVICES="",
            HF_HUB_OFFLINE="1",
            OMP_NUM_THREADS="2",
            OPENBLAS_NUM_THREADS="2",
        )
        with (root / "worker.log").open("xb") as log:
            child = subprocess.Popen(
                [
                    plan["python"],
                    "-P",
                    plan["worker"]["path"],
                    "worker",
                    str(root / "plan.json"),
                    "--arm",
                    "spectral",
                ],
                cwd=work,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            child_owner = {"pid": child.pid, "created": psutil.Process(child.pid).create_time()}
            record("running-genuine-external-checkpoint-prefix-resume", child=child_owner)
            try:
                code = child.wait(timeout=900)
            except subprocess.TimeoutExpired:
                assert alive(child_owner) and os.getpgid(child.pid) == child.pid
                os.killpg(child.pid, signal.SIGTERM)
                child.wait(timeout=30)
                raise
            assert code == 0
        import torch
        from audit_flat_palette import identical

        torch.set_num_threads(2)
        assert not torch.cuda.is_initialized()
        actual = read(root / "spectral-result.json")
        reference = read(Path(previous["root"]) / "spectral-result.json")
        a, b = [
            torch.load(c["checkpoint"]["path"], weights_only=True, map_location="cpu", mmap=True)
            for c in [actual, reference]
        ]
        for key in [
            "model",
            "ema",
            "optimizer",
            "python_rng",
            "torch_rng",
            "cuda_rng",
            "best",
            "step",
            "model_config",
        ]:
            identical(a[key], b[key])
        assert read(actual["observations"]["path"]) == read(reference["observations"]["path"])
        assert actual["captures"] == [
            {
                "common_initial_state_exact": True,
                "DINO_sha256": plan["DINO_sha256"],
                "initial_output_exact_parent": False,
                "resuming": True,
            }
        ]
        guard(plan)
        record(
            "completed-genuine-external8plus8-recovery-exact-no-quality-result",
            plan=ref(root / "plan.json"),
            result=ref(root / "spectral-result.json"),
            reference=ref(Path(previous["root"]) / "spectral-result.json"),
            model_EMA_AdamW_RNG_best_exact=True,
            all16_observations_exact=True,
            CUDA_initialized=False,
        )
    except BaseException as error:
        record("failed-spectral-recovery-preflight-no-automatic-retry", error=repr(error))
        raise


def read_line(line):
    import json

    return json.loads(line)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--preflight", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.preflight.resolve(), a.output)
