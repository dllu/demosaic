"""Preserve a verified fixed boundary and stop only its exact training owners."""

import argparse
import json
import os
import shutil
import signal
import time
from pathlib import Path

import psutil
from train_context_trial import alive
from train_directional_bank_trial import guard, read, ref, save

from demosaic.safety import writable_path


def handoff(plan_path, output, step):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    plan_path = Path(plan_path).resolve()
    plan = read(plan_path)
    assert plan["planned_updates"] == plan["boundary_updates"] == 4000
    assert not plan["engineering_only"] and step == 1000
    guard(plan)
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    original = Path(plan["root"])
    status = read(original / "status.json")
    assert status["status"] == "running-source-frozen-spectral-arm" and status["arm"] == "control"
    owners = {key: status[key] for key in ["controller", "child"]}
    assert all(alive(o) and os.getpgid(o["pid"]) == o["pid"] for o in owners.values())
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "training_plan": ref(plan_path),
        "training_owners": owners,
        "source": ref(__file__),
        "reason": "Fix final double-save retention wrapper; preserve original4000 trajectory.",
    }

    def record(value, **fields):
        info.update(status=value, updated_unix=time.time(), **fields)
        save(root / "status.json", info)
        print(json.dumps({"status": value}), flush=True)

    try:
        record("waiting-for-verified-control-step1000-before-explicit-handoff")
        run = Path(plan["arms"][0]["run"])
        retained, latest = run / "step-001000.pt", run / "last.pt"
        deadline = owners["child"]["created"] + plan["timeout_seconds"]
        while True:
            assert time.time() < deadline and all(alive(o) for o in owners.values())
            if (
                retained.exists()
                and latest.exists()
                and ref(retained)["sha256"] == ref(latest)["sha256"]
            ):
                break
            time.sleep(5)
        import torch

        torch.set_num_threads(2)
        checkpoint = ref(retained)
        state = torch.load(retained, weights_only=True, map_location="cpu", mmap=True)
        assert state["step"] == step and state["config"]["steps"] == 4000
        assert state["config"]["seed"] == 55 and state["config"]["batch_size"] == 16
        assert (
            len(state["model"]) == len(state["ema"]) == 91
            and len(state["optimizer"]["state"]) == 89
        )
        for field in ["model", "ema"]:
            assert all(torch.isfinite(v).all() for v in state[field].values())
        for item in state["optimizer"]["state"].values():
            assert int(item["step"]) == step and item["exp_avg_sq"].min() >= 0
            assert all(torch.isfinite(v).all() for v in item.values() if torch.is_tensor(v))
        target = root / "control-step001000.pt"
        shutil.copyfile(retained, target)
        assert ref(target)["sha256"] == checkpoint["sha256"]
        assert all(alive(o) and os.getpgid(o["pid"]) == o["pid"] for o in owners.values())
        record(
            "verified-step1000-stopping-only-exact-original-controller-and-worker",
            checkpoint=ref(target),
            original_checkpoint=checkpoint,
            original_status_at_stop=read(original / "status.json"),
        )
        # Each was launched in its own session. Stop the old controller first
        # so it cannot launch the companion arm during the handoff.
        for key in ["controller", "child"]:
            owner = owners[key]
            assert alive(owner) and os.getpgid(owner["pid"]) == owner["pid"]
            process = psutil.Process(owner["pid"])
            os.killpg(owner["pid"], signal.SIGTERM)
            process.wait(timeout=30)
            assert not alive(owner)
        assert ref(retained) == checkpoint and ref(target)["sha256"] == checkpoint["sha256"]
        observations = [
            r for r in read(original / "control-observations.json") if r["step"] <= step
        ]
        assert [r["step"] for r in observations] == [*range(1, 17), *range(25, step + 1, 25)]
        assert all(
            r["source_sha256"] == r["actual_loss_sha256"]
            and r["actual_forward_sha256"] == r["expected_forward_sha256"]
            for r in observations
        )
        save(root / "control-prefix-observations.json", observations)
        lines = (run / "metrics.jsonl").read_text().splitlines()
        prefix = [line for line in lines if json.loads(line).get("step", 0) <= step]
        (root / "control-prefix-metrics.jsonl").write_text("\n".join(prefix) + "\n")
        training = [json.loads(line) for line in prefix if json.loads(line)["event"] == "train"]
        assert [r["step"] for r in training] == [1, *range(25, step + 1, 25)]
        assert training[-1]["step"] == step
        guard(plan)
        record(
            "completed-verified-checkpoint-handoff-original-owners-exited",
            observations=ref(root / "control-prefix-observations.json"),
            metrics=ref(root / "control-prefix-metrics.jsonl"),
            original_config=ref(plan["arms"][0]["config"]),
            source_sha256=state["config"]["source_sha256"],
            original_model_modules_unchanged=46,
            original_active_seconds_consumed=time.time() - owners["child"]["created"],
            no_training_updates_in_handoff=True,
            scope="Controlled wrapper repair at a verified immutable step1000. Original files, logs, frozen plan and code remain unchanged. Some unretained post-checkpoint computation may be discarded; retained trajectory resumes the original4000 horizon without reset or extension. No quality result.",
        )
    except BaseException as error:
        record("failed-spectral-checkpoint-handoff-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--training-plan", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--step", type=int, default=1000)
    a = p.parse_args()
    handoff(a.training_plan, a.output, a.step)
