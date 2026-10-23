import copy

import pytest
from queue_quality_recipe_evaluation import KEYS, TERMINAL, checkpoints, phase_keys, training_ready
from train_directional_bank_trial import ref, save

PLAN = {"path": "/frozen/plan.json", "sha256": "a" * 64}
OWNER = {"pid": 100, "created": 1.0}
CHILD = {"pid": 200, "created": 2.0}


def completed():
    return {
        "plan": copy.deepcopy(PLAN),
        "controller": copy.deepcopy(OWNER),
        "child": copy.deepcopy(CHILD),
        "status": TERMINAL,
        "completed": dict.fromkeys(KEYS),
    }


@pytest.mark.parametrize("owners_alive", [[], [OWNER], [CHILD], [OWNER, CHILD]])
def test_evaluation_waits_for_both_training_processes_to_exit(owners_alive):
    assert training_ready(completed(), PLAN, OWNER, is_live=lambda x: x in owners_alive) is (
        not owners_alive
    )


@pytest.mark.parametrize("damage", ["plan", "owner", "missing-arm", "unexpected-arm", "failure"])
def test_bad_training_boundary_cannot_release_evaluation(damage):
    state = completed()
    if damage == "plan":
        state["plan"]["sha256"] = "b" * 64
    elif damage == "owner":
        state["controller"]["created"] += 1
    elif damage == "missing-arm":
        state["completed"].pop("train-V101")
    elif damage == "unexpected-arm":
        state["completed"]["train-V102"] = None
    else:
        state["status"] = "failed-training-preserved-no-automatic-retry"
    with pytest.raises(AssertionError):
        training_ready(state, PLAN, OWNER, is_live=lambda _: False)


def test_incomplete_training_requires_its_original_controller_alive():
    state = completed()
    state.update(status="running-quality-training", completed={})
    assert not training_ready(state, PLAN, OWNER, is_live=lambda x: x == OWNER)
    with pytest.raises(AssertionError, match="exited before completion"):
        training_ready(state, PLAN, OWNER, is_live=lambda _: False)


@pytest.mark.parametrize("owners_alive", [[], [OWNER], [CHILD], [OWNER, CHILD]])
def test_explicit_new_versions_wait_for_both_original_training_owners(owners_alive):
    state = completed()
    state["completed"] = dict.fromkeys(phase_keys(("V102", "V103")))
    assert training_ready(
        state, PLAN, OWNER, arms=("V102", "V103"), is_live=lambda x: x in owners_alive
    ) is (not owners_alive)
    # A legacy phase set cannot release a new experiment with different versions.
    with pytest.raises(AssertionError, match="Unexpected training phase"):
        training_ready(state, PLAN, OWNER, is_live=lambda _: False)


@pytest.mark.parametrize("arms", [[], ["V102", "V102"], ["V102", "other"], ["V0"]])
def test_invalid_expected_versions_do_not_define_a_completion_boundary(arms):
    with pytest.raises(AssertionError):
        phase_keys(arms)


@pytest.mark.parametrize("cpu_smoke", [False, True])
def test_checkpoint_boundary_uses_explicit_parent_step_and_original_horizon(
    tmp_path, monkeypatch, cpu_smoke
):
    from queue_quality_recipe_evaluation import DINO_SHA

    monkeypatch.setattr("queue_quality_recipe_evaluation.live", lambda _: False)
    phase, updates = ("CPU", 8) if cpu_smoke else ("train", 20000)
    parent = {"path": "/immutable/V101.pt", "sha256": "e" * 64}
    training = {
        "parent": parent,
        "parent_step": 10000,
        "smoke_updates": 8,
        "train_updates": 20000,
        "arms": {"V102": {}, "V103": {}},
    }
    state = {"completed": {}}
    for arm in training["arms"]:
        checkpoint = tmp_path / f"{arm}.pt"
        checkpoint.write_bytes(arm.encode())
        result = tmp_path / f"{arm}.json"
        save(
            result,
            {
                "status": "completed-quality-training-phase",
                "phase": phase,
                "arm": arm,
                "updates": updates,
                "initialization": {"initial_EMA_exact": True, "DINO_sha256": DINO_SHA},
                "owner": CHILD,
                "checkpoint": ref(checkpoint),
                "source_sha256": "f" * 64,
            },
        )
        state["completed"][f"{phase}-{arm}"] = ref(result)
    records, _ = checkpoints(state, training, cpu_smoke=cpu_smoke, parent_label="V101")
    assert [r["arm"] for r in records] == ["V101", "V102", "V103"]
    assert records[0]["expected_lineage"] == {"step": 10000}
    assert all(
        r["expected_lineage"] == {"step": updates, "initialized_from": {**parent, "step": 10000}}
        for r in records[1:]
    )
    # A valid checkpoint hash still cannot stand in for an unfinished horizon.
    from train_directional_bank_trial import read

    result = tmp_path / "V103.json"
    damaged = read(result)
    damaged["updates"] -= 1
    save(result, damaged)
    state["completed"][f"{phase}-V103"] = ref(result)
    with pytest.raises(AssertionError):
        checkpoints(state, training, cpu_smoke=cpu_smoke, parent_label="V101")


@pytest.mark.parametrize("damage", [None, "one-code-file", "both-code-files", "other-data", "ROI"])
def test_only_declared_catalogue_difference_is_allowed_between_actual_archives(tmp_path, damage):
    import hashlib

    import yaml
    from queue_quality_recipe_evaluation import reviewed_catalogue_source_boundary

    work = tmp_path / "work"
    (work / "src/demosaic").mkdir(parents=True)
    (work / "src/demosaic/model.py").write_bytes(b"same numerical source")
    manifest = tmp_path / "commons.jsonl"
    manifest.write_bytes(b"same frozen Commons sources")
    training, results = {"work": str(work), "arms": {}}, {}
    for arm in ("V102", "V103"):
        run = tmp_path / arm
        run.mkdir()
        catalogue = tmp_path / f"{arm}-ROI.json"
        catalogue.write_bytes(arm.encode())
        config = tmp_path / f"{arm}.yaml"
        config.write_text(
            yaml.safe_dump({"manifest": str(manifest), "reviewed_roi_catalogue": str(catalogue)})
        )
        training["arms"][arm] = {"CPU": str(config)}
        payloads = {
            "model.py": b"same numerical source",
            "reviewed-photo-rois.json": catalogue.read_bytes(),
            "validation-manifest.jsonl": b"same held-out source records",
            "manifest.jsonl": manifest.read_bytes(),
        }
        if damage == "both-code-files" or (arm == "V103" and damage == "one-code-file"):
            payloads["model.py"] = b"different numerical source"
        if arm == "V103" and damage == "other-data":
            payloads["validation-manifest.jsonl"] = b"different validation data"
        if arm == "V103" and damage == "ROI":
            payloads["reviewed-photo-rois.json"] = b"not the catalogue in the frozen recipe"
        digest = hashlib.sha256()
        for name in sorted(payloads):
            if name != "manifest.jsonl":
                digest.update(name.encode() + payloads[name])
        source_sha = digest.hexdigest()
        archive = run / "source" / source_sha
        archive.mkdir(parents=True)
        for name, content in payloads.items():
            (archive / name).write_bytes(content)
        results[arm] = {"checkpoint": {"path": str(run / "last.pt")}, "source_sha256": source_sha}
    if damage:
        with pytest.raises(AssertionError):
            reviewed_catalogue_source_boundary(results, training, "CPU")
    else:
        inputs = reviewed_catalogue_source_boundary(results, training, "CPU")
        assert len(inputs) == 8
