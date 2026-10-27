"""A controller handoff must retain checks, source, budgets and worker plan."""

import pytest
import train_raw_spatial_trial as runner
from train_directional_bank_trial import read, ref, save


def fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "REPO", tmp_path)
    monkeypatch.setattr(runner, "live", lambda owner: owner["live"])
    original = tmp_path / ".cache/original"
    original.mkdir(parents=True)
    worker = original / "worker.py"
    worker.write_text("# Immutable neural worker fixture; never executed\n")
    checkpoint = original / "checkpoint.txt"
    checkpoint.write_text("Not a neural checkpoint; protocol fixture only\n")
    plan = {
        "root": str(original),
        "work": str(original / "work"),
        "worker_script": ref(worker),
        "scope": "Protocol fixture. ",
        "arms": {arm: {} for arm in runner.ARMS},
        "inputs": [],
        "frozen_files": {str(worker): ref(worker)["sha256"]},
        "train_updates": 20000,
        "maximum_train_worker_seconds": 172800,
        "maximum_smoke_worker_seconds": 1800,
        "CUDA_allocator_cap_GiB": 16,
    }
    path = original / "plan.json"
    save(path, plan)
    save(original / "launch.json", {"plan": ref(path)})
    completed = {}
    for phase in ("CPU", "CUDA"):
        for arm in runner.ARMS:
            key = f"{phase}-{arm}"
            result = original / f"{key}-result.json"
            save(
                result,
                {
                    "status": "completed-raw-spatial-training-phase",
                    "phase": phase,
                    "arm": arm,
                    "updates": 18,
                    "owner": {"live": False},
                    "model_EMA_Adam_finite": True,
                    "all_AdamW_steps": 18,
                    "checkpoint": ref(checkpoint),
                    "all_observed_inputs_match_saved_control": True,
                },
            )
            completed[key] = ref(result)
    save(
        original / "admission-handoff-v1.json",
        {
            "original_plan": ref(path),
            "original_controller": {"live": False},
            "new_production_updates": 0,
            "completed": completed,
        },
    )
    dependency = tmp_path / ".cache/existing"
    dependency.mkdir()
    dependency_path = dependency / "plan.json"
    save(
        dependency_path,
        {
            "root": str(dependency),
            "arms": {"V124": {}, "V125": {}},
            "inputs": [],
            "frozen_files": {},
        },
    )
    save(
        dependency / "status.json",
        {
            "plan": ref(dependency_path),
            "controller": {"live": True},
            "status": "running-noise-pair-training",
        },
    )
    return path, dependency_path


def test_handoff_reuses_checks_and_preserves_original_worker_budget(tmp_path, monkeypatch):
    path, dependency = fixture(tmp_path, monkeypatch)
    original = path.read_bytes()
    result = runner.adopt_checks_after_admission(tmp_path / ".cache/new", path, dependency)
    plan, old = read(result), read(path)
    assert path.read_bytes() == original
    for key in (
        "work",
        "worker_script",
        "train_updates",
        "maximum_train_worker_seconds",
        "maximum_smoke_worker_seconds",
        "CUDA_allocator_cap_GiB",
    ):
        assert plan[key] == old[key]
    assert len(plan["adopted_phase_results"]) == 4
    assert plan["adopted_worker_plan"] == ref(path)
    assert plan["output_worker_root"] == str(path.parent)
    assert plan["before_train_admission"]["plan"] == ref(dependency)
    assert plan["before_train_admission"]["arm"] == "V125"
    runner.guard(plan)


@pytest.mark.parametrize("change", ["partial", "started", "changed", "live"])
def test_invalid_adoption_creates_no_new_controller(tmp_path, monkeypatch, change):
    path, dependency = fixture(tmp_path, monkeypatch)
    handoff_path = path.parent / "admission-handoff-v1.json"
    handoff = read(handoff_path)
    if change == "partial":
        del handoff["completed"]["CUDA-V132"]
    elif change == "started":
        (path.parent / "train-V131.claim").touch()
    else:
        binding = handoff["completed"]["CUDA-V132"]
        result = read(binding["path"])
        result["owner"]["live"] = True
        save(binding["path"], result)
        if change == "live":
            handoff["completed"]["CUDA-V132"] = ref(binding["path"])
    save(handoff_path, handoff)
    target = tmp_path / ".cache/new"
    with pytest.raises(AssertionError):
        runner.adopt_checks_after_admission(target, path, dependency)
    assert not target.exists()
