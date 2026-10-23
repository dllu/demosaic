"""A derived initializer must not replace the actual quality reference model."""

import copy

import pytest
from queue_quality_fullframe import export_checkpoints
from queue_quality_recipe_evaluation import (
    checkpoints,
    phase_keys,
    validate_reference_checkpoints,
)
from train_directional_bank_trial import ref, save

TINY = {"model": "official/tiny", "revision": "1" * 40, "sha256": "a" * 64}
SMALL = {"model": "official/small", "revision": "2" * 40, "sha256": "b" * 64}
OWNER = {"pid": 1, "created": 0}
PLAN = {"path": "/immutable/plan.json", "sha256": "c" * 64}


@pytest.fixture
def boundary(tmp_path, monkeypatch):
    monkeypatch.setattr("queue_quality_recipe_evaluation.live", lambda _: False)
    original, zero = tmp_path / "V102.pt", tmp_path / "Tiny-zero.pt"
    original.write_bytes(b"original-restoration-EMA")
    zero.write_bytes(b"derived-gate-zero-restoration-EMA")
    references = [
        {
            "arm": "V102",
            **ref(original),
            "expected_lineage": {"step": 20000},
            "expected_backbone": TINY,
        }
    ]
    training = {
        "parent": ref(zero),
        "parent_step": 20000,
        "parent_backbone": TINY,
        "arms": {"V107": {}, "V108": {}},
        "backbones": {"V107": TINY, "V108": SMALL},
        "smoke_updates": 8,
        "train_updates": 20000,
    }
    state = {
        "status": "completed-training-awaiting-model-comparisons",
        "plan": PLAN,
        "controller": OWNER,
        "child": OWNER,
        "completed": {},
    }
    for phase in ("CPU", "CUDA", "train"):
        for arm, identity in training["backbones"].items():
            checkpoint = tmp_path / f"{phase}-{arm}.pt"
            checkpoint.write_bytes(f"{phase}-{arm}".encode())
            result = tmp_path / f"{phase}-{arm}.json"
            save(
                result,
                {
                    "status": "completed-quality-training-phase",
                    "phase": phase,
                    "arm": arm,
                    "updates": 20000 if phase == "train" else 8,
                    "initialization": {
                        "initial_EMA_exact": True,
                        "DINO_sha256": identity["sha256"],
                    },
                    "owner": OWNER,
                    "checkpoint": ref(checkpoint),
                    "source_sha256": "d" * 64,
                },
            )
            state["completed"][f"{phase}-{arm}"] = ref(result)
    queue = {
        "training_plan": PLAN,
        "training_controller": OWNER,
        "training_arms": ["V107", "V108"],
        "parent_label": "V102-zero",
        "reference_checkpoints": references,
    }
    return training, state, queue


@pytest.mark.parametrize("cpu_smoke", [True, False])
def test_original_baseline_and_zero_initializer_keep_distinct_identities(boundary, cpu_smoke):
    training, state, queue = boundary
    records, inputs = checkpoints(
        state,
        training,
        cpu_smoke=cpu_smoke,
        parent_label=queue["parent_label"],
        reference_checkpoints=queue["reference_checkpoints"],
    )
    assert [r["arm"] for r in records] == ["V102", "V102-zero", "V107", "V108"]
    assert [r["expected_backbone"] for r in records] == [TINY, TINY, TINY, SMALL]
    assert records[0]["sha256"] != records[1]["sha256"]
    assert records[0]["expected_lineage"] == {"step": 20000}
    assert all(
        r["expected_lineage"]["initialized_from"] == {**training["parent"], "step": 20000}
        for r in records[2:]
    )
    assert {k: records[0][k] for k in ("path", "sha256")} in inputs


@pytest.mark.parametrize("cpu_smoke", [True, False])
def test_fullframe_receives_the_same_fixed_reference(boundary, cpu_smoke):
    training, state, queue = boundary
    records = export_checkpoints(state, training, queue, cpu_smoke=cpu_smoke)
    assert [r["arm"] for r in records] == (
        ["V102", "V102-zero"] if cpu_smoke else ["V102", "V102-zero", "V107", "V108"]
    )
    assert records[0] == queue["reference_checkpoints"][0]
    assert records[1]["sha256"] == training["parent"]["sha256"]


@pytest.mark.parametrize(
    "damage",
    [
        "missing-hash",
        "short-hash",
        "wrong-file-hash",
        "relative-path",
        "mutable-backbone",
        "unknown-field",
        "duplicate-label",
        "parent-label",
        "arm-label",
        "duplicate-file",
        "parent-file",
        "missing-step",
        "bool-step",
        "negative-step",
        "lineage-extra",
    ],
)
def test_ambiguous_or_changed_reference_is_rejected(boundary, damage):
    training, _, queue = boundary
    references = copy.deepcopy(queue["reference_checkpoints"])
    record = references[0]
    if damage == "missing-hash":
        record.pop("sha256")
    elif damage == "short-hash":
        record["sha256"] = record["sha256"][:16]
    elif damage == "wrong-file-hash":
        record["sha256"] = "e" * 64
    elif damage == "relative-path":
        record["path"] = "relative/V102.pt"
    elif damage == "mutable-backbone":
        record["expected_backbone"]["revision"] = "main"
    elif damage == "unknown-field":
        record["allow_any_model"] = True
    elif damage == "duplicate-label":
        references.append(copy.deepcopy(record))
    elif damage == "parent-label":
        record["arm"] = "V102-zero"
    elif damage == "arm-label":
        record["arm"] = "V108"
    elif damage == "duplicate-file":
        references.append({**record, "arm": "V102-alias"})
    elif damage == "parent-file":
        record.update(training["parent"])
    elif damage == "missing-step":
        record["expected_lineage"] = {}
    elif damage == "bool-step":
        record["expected_lineage"]["step"] = True
    elif damage == "negative-step":
        record["expected_lineage"]["step"] = -1
    else:
        record["expected_lineage"]["initialized_from"] = training["parent"]
    with pytest.raises((ValueError, FileNotFoundError)):
        validate_reference_checkpoints(references, training, parent_label="V102-zero")


def test_reference_file_change_is_detected_at_the_execution_boundary(boundary):
    training, state, queue = boundary
    from pathlib import Path

    Path(queue["reference_checkpoints"][0]["path"]).write_bytes(b"changed baseline")
    with pytest.raises(ValueError, match="file differs"):
        checkpoints(
            state,
            training,
            cpu_smoke=True,
            parent_label="V102-zero",
            reference_checkpoints=queue["reference_checkpoints"],
        )


@pytest.mark.parametrize("references", [None, {}, "V102.pt"])
def test_reference_manifest_requires_an_explicit_record_list(boundary, references):
    training, _, _ = boundary
    with pytest.raises(TypeError):
        validate_reference_checkpoints(references, training, parent_label="V102-zero")


def test_reference_cannot_alias_a_trained_endpoint(boundary):
    training, state, queue = boundary
    from train_directional_bank_trial import read

    endpoint = read(state["completed"]["train-V108"]["path"])["checkpoint"]
    queue["reference_checkpoints"][0].update(endpoint)
    with pytest.raises(AssertionError, match="duplicates a trained endpoint"):
        export_checkpoints(state, training, queue, cpu_smoke=False)


def test_extra_reference_does_not_relax_original_training_completion(boundary):
    training, state, queue = boundary
    state["completed"].pop("train-V108")
    with pytest.raises(AssertionError, match="Incomplete training coverage"):
        export_checkpoints(state, training, queue, cpu_smoke=False)
    assert phase_keys(training["arms"]) - set(state["completed"]) == {"train-V108"}


def test_export_operators_import_before_an_older_queue_snapshot(tmp_path):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    from queue_quality_fullframe import freeze_export_operators, worker_pythonpath

    older = tmp_path / "older-work"
    scripts = older / "scripts"
    scripts.mkdir(parents=True)
    incompatible = scripts / "queue_quality_recipe_evaluation.py"
    payload = b"raise RuntimeError('older operator has no reference validator')\n"
    incompatible.write_bytes(payload)
    operators = freeze_export_operators(tmp_path)
    script_root = Path(__file__).resolve().parents[1] / "scripts"
    env = dict(
        os.environ,
        CUDA_VISIBLE_DEVICES="",
        PYTHONPATH=worker_pythonpath({"work": str(older), "operators": str(operators)})
        + ":"
        + str(script_root),
    )
    result = subprocess.run(
        [
            sys.executable,
            "-P",
            "-c",
            (
                "import json,queue_quality_recipe_evaluation as q,frozen_backbone_identity as b;"
                "assert callable(q.validate_reference_checkpoints);"
                "print(json.dumps([q.__file__,b.__file__]))"
            ),
        ],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert all(Path(p).parent == operators for p in json.loads(result.stdout))
    assert incompatible.read_bytes() == payload


def test_existing_export_plans_keep_their_original_module_search_path():
    from queue_quality_fullframe import worker_pythonpath

    assert worker_pythonpath({"work": "/immutable/work"}) == (
        "/immutable/work/src:/immutable/work/scripts"
    )
