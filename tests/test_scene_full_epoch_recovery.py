import json
import subprocess
import sys
from pathlib import Path

import pytest

from demosaic.experiments.artifacts import checked, read_json, reference, write_json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import resume_scene_full_epoch as recovery


def test_scene_resume_retains_verified_prefix(tmp_path, monkeypatch):
    frozen_script = tmp_path / "frozen.py"
    frozen_script.write_text("# frozen\n")
    plan = {"training_script": reference(frozen_script), "steps": 50000}
    path = tmp_path / "plan.json"
    write_json(path, plan)
    binding = reference(path)
    calls = []

    class Dataset:
        def source_row(self, index):
            return {"id": f"photo-{index}"}

    def produce(root, plan, folder, mode, end, resume):
        calls.append(end)
        if end == 4 and calls.count(4) == 1:
            raise InterruptedError("controller interrupted")
        if resume is None:
            begin, checkpoint = 0, None
        else:
            previous = read_json(checked(resume))
            begin, checkpoint = previous["steps"], previous["checkpoints"][-1]
        folder.mkdir()
        trace = folder / "observations.jsonl"
        trace.write_text(
            "".join(
                json.dumps({"index": i, "source_id": f"photo-{i}", "recipe": {"noise_seed": i}})
                + "\n"
                for i in range(2 * begin, 2 * end)
            )
        )
        state = folder / "checkpoint"
        state.write_bytes(f"step {end}".encode())
        receipt = folder / "completed.json"
        write_json(
            receipt,
            {
                "plan": binding,
                "mode": mode,
                "script": plan["training_script"],
                "start_step_exclusive": begin,
                "steps": end,
                "schedule_steps": plan["steps"],
                "resume": checkpoint,
                "seconds": 2.0,
                "data_seconds": 0.5,
                "checkpoint_seconds": 0.25,
                "checkpoints": [reference(state)],
                "observations": reference(trace),
                "DINO_unchanged": True,
            },
        )
        return receipt

    monkeypatch.setattr(recovery, "completed_segment", produce)
    args = tmp_path, binding, plan, Dataset(), "none", 0, 5, None, 2
    with pytest.raises(InterruptedError):
        recovery.resume_phase(*args)
    result = recovery.resume_phase(*args)
    assert calls == [2, 4, 4, 5]
    assert recovery.resume_phase(*args) == result
    assert result["training_seconds"] == 6.0
    assert result["scene_types"] == {"plain": 10}
    receipt = read_json(checked(result["receipt"]))
    assert [read_json(checked(segment))["steps"] for segment in receipt["segments"]] == [2, 4, 5]
    observations = [
        json.loads(line) for line in checked(receipt["observations"]).read_text().splitlines()
    ]
    assert [r["index"] for r in observations] == list(range(10))


@pytest.mark.parametrize(
    "diagnosis, continues",
    [
        ("RuntimeError: Training RAM reserve unavailable", True),
        ("FloatingPointError: Nonfinite supervised scene/crop loss", False),
    ],
)
def test_scene_segment_retries_only_memory(tmp_path, monkeypatch, diagnosis, continues):
    attempts = []

    def worker(root, plan, folder, arguments):
        attempts.append(arguments)
        attempt = folder / f"attempt-{len(attempts):02d}"
        attempt.mkdir()
        if len(attempts) == 1:
            (attempt / "worker.log").write_text(diagnosis)
            write_json(folder / "launch.json", {"attempt": str(attempt)})
            raise subprocess.CalledProcessError(1, arguments)
        output = attempt / "work"
        output.mkdir()
        (output / "completed.json").write_text("{}")
        return output

    monkeypatch.setattr(recovery, "run_worker", worker)
    args = tmp_path, {}, tmp_path / "segment", "spatial", 500, None
    if continues:
        assert recovery.completed_segment(*args).is_file()
        assert attempts[0] == attempts[1]
    else:
        with pytest.raises(subprocess.CalledProcessError):
            recovery.completed_segment(*args)
        assert len(attempts) == 1
