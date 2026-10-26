import json
from pathlib import Path

import pytest
import train_noise_pair_trial as runner


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "REPO", tmp_path)
    monkeypatch.setattr(runner, "live", lambda owner: owner["live"])
    root = tmp_path / ".cache/original"
    root.mkdir(parents=True)
    worker = root / "worker.py"
    worker.write_text("# original immutable worker\n")
    plan = {
        "root": str(root),
        "work": str(root / "work"),
        "worker_script": runner.ref(worker),
        "inputs": [],
        "frozen_files": {str(worker): runner.ref(worker)["sha256"]},
        "launch_available_RAM_GiB": 64,
        "runtime_available_RAM_GB": 32,
        "CUDA_allocator_cap_GiB": 24,
        "maximum_train_worker_seconds": 172800,
    }
    runner.save(root / "plan.json", plan)
    completed = {}
    for phase in ["CPU-V124", "CPU-V125", "CUDA-V124"]:
        path = root / f"{phase}-result.json"
        runner.save(
            path,
            {
                "owner": {"live": False},
                "updates": 18,
                "status": "completed-noise-pair-training-phase",
                "model_EMA_Adam_finite": True,
                "all_AdamW_steps": 18,
            },
        )
        completed[phase] = runner.ref(path)
    status = {
        "controller": {"live": True},
        "plan": runner.ref(root / "plan.json"),
        "status": "waiting-for-noise-pair-training-headroom",
        "phase": "CUDA",
        "arm": "V125",
        "completed": completed,
    }
    runner.save(root / "status.json", status)
    return root, status


def test_adoption_preserves_original_worker_checks_and_production_policy(tmp_path, monkeypatch):
    root, status = fixture(tmp_path, monkeypatch)
    before = (root / "plan.json").read_bytes()
    result = runner.adopt_prepared_checks(tmp_path / ".cache/new", root / "plan.json")
    plan = json.loads(result.read_text())
    assert plan["adopted_phase_results"] == status["completed"]
    assert plan["adopted_worker_plan"] == runner.ref(root / "plan.json")
    assert plan["work"] == str(root / "work")
    assert plan["worker_script"] == runner.ref(root / "worker.py")
    assert plan["phase_launch_available_RAM_GiB"] == {"CUDA": 56}
    assert plan["launch_available_RAM_GiB"] == 64
    assert plan["maximum_train_worker_seconds"] == 172800
    assert plan["runtime_available_RAM_GB"] == 32 and plan["CUDA_allocator_cap_GiB"] == 24
    assert (root / "plan.json").read_bytes() == before
    runner.guard(plan)


@pytest.mark.parametrize("change", ["started", "partial", "changed", "live_worker"])
def test_adoption_rejects_active_or_changed_checks(tmp_path, monkeypatch, change):
    root, status = fixture(tmp_path, monkeypatch)
    if change == "started":
        (root / "CUDA-V125.claim").touch()
    elif change == "partial":
        del status["completed"]["CPU-V125"]
    else:
        binding = status["completed"]["CPU-V124"]
        path = Path(binding["path"])
        receipt = runner.read(path)
        receipt["owner"]["live"] = True
        runner.save(path, receipt)
        if change == "live_worker":
            status["completed"]["CPU-V124"] = runner.ref(path)
    runner.save(root / "status.json", status)
    with pytest.raises(AssertionError):
        runner.adopt_prepared_checks(tmp_path / ".cache/new", root / "plan.json")
    assert not (tmp_path / ".cache/new").exists()
