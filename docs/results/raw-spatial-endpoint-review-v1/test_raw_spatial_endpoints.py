"""Endpoint identity and review dependency failures must reject before neural work."""

import copy

import pytest
import queue_raw_spatial_endpoints as queue
import torch
from collect_retained_checkpoint_pilot import verify_completed_training_checkpoint
from train_directional_bank_trial import ref


def endpoint(spatial=True):
    values = {f"common.{i}": torch.zeros(1) for i in range(91)}
    if spatial:
        values.update({f"pretrained_rgb.raw_spatial.{i}": torch.ones(1) for i in range(23)})
    lineage = {"path": "parent-fixture", "sha256": "a" * 64, "step": 20000}
    checkpoint = {"path": "endpoint-fixture", "sha256": "b" * 64}
    state = {
        "step": 20000,
        "config": {
            "steps": 20000,
            "seed": 70,
            "source_sha256": "frozen",
            "initialized_from": lineage,
        },
        "model_config": {"raw_spatial_features": spatial},
        "model": values,
        "ema": copy.deepcopy(values),
        "optimizer": {
            "state": {
                i: {"step": torch.tensor(20000), "exp_avg": torch.zeros(1)}
                for i in range(112 if spatial else 89)
            }
        },
    }
    plan = {
        "step": 20000,
        "training_horizon": 20000,
        "raw_spatial_features": spatial,
        "EMA_tensors": len(values),
        "expected_lineage": lineage,
        "checkpoint": checkpoint,
        "training_source_sha256": "frozen",
    }
    result = {
        "status": "completed-raw-spatial-training-phase",
        "phase": "train",
        "arm": "V132" if spatial else "V131",
        "updates": 20000,
        "all_AdamW_steps": 20000,
        "source_sha256": "frozen",
        "checkpoint": checkpoint,
        "counts": {
            "training_forwards": 20000,
            "optimizer_steps": 20000,
            "prepared_training_batches": 20000,
            "validation_forwards": 640,
            "encoder_forwards": 20640,
            "target_contexts": 320000,
        },
        "observed_inputs": [
            {"step": i, "domain": "fixture", "clean_sha256": "clean", "batch_sha256": "noisy"}
            for i in range(1, 20001)
        ],
        "all_observed_inputs_match_saved_control": True,
    }
    return state, plan, result


@pytest.mark.parametrize("spatial", [False, True])
def test_completed_endpoints_validated_without_neural_construction(monkeypatch, spatial):
    def forbidden(*args, **kwargs):
        pytest.fail("State validation must precede neural construction/calls")

    monkeypatch.setattr(torch.nn.Module, "__init__", forbidden)
    monkeypatch.setattr(torch.nn.Module, "_call_impl", forbidden)
    verify_completed_training_checkpoint(*endpoint(spatial))


@pytest.mark.parametrize(
    "change",
    [
        "step",
        "horizon",
        "seed",
        "source",
        "lineage",
        "EMA",
        "architecture",
        "adam",
        "nonfinite",
        "branch",
        "trace",
        "matched",
        "checkpoint",
        "updates",
        "validation",
        "encoder",
        "contexts",
    ],
)
def test_incomplete_or_changed_endpoint_rejected(change):
    state, plan, result = endpoint()
    if change == "step":
        state["step"] = 19999
    elif change == "horizon":
        state["config"]["steps"] = 21000
    elif change == "seed":
        state["config"]["seed"] = 71
    elif change == "source":
        state["config"]["source_sha256"] = "changed"
    elif change == "lineage":
        state["config"]["initialized_from"] = {}
    elif change == "EMA":
        state["ema"].pop("common.0")
    elif change == "architecture":
        state["model_config"]["raw_spatial_features"] = False
    elif change == "adam":
        state["optimizer"]["state"][111]["step"] = torch.tensor(19999)
    elif change == "nonfinite":
        state["model"]["common.0"].fill_(float("nan"))
    elif change == "branch":
        state["model"]["unexpected"] = state["model"].pop("pretrained_rgb.raw_spatial.22")
        state["ema"] = copy.deepcopy(state["model"])
    elif change == "trace":
        result["observed_inputs"][-1]["step"] = 19999
    elif change == "matched":
        result["all_observed_inputs_match_saved_control"] = False
    elif change == "checkpoint":
        result["checkpoint"] = {"path": "different", "sha256": "c" * 64}
    elif change == "updates":
        result["updates"] = 19999
    elif change == "validation":
        result["counts"]["validation_forwards"] = 608
    elif change == "encoder":
        result["counts"]["encoder_forwards"] -= 1
    else:
        result["counts"]["target_contexts"] -= 16
    with pytest.raises(ValueError):
        verify_completed_training_checkpoint(state, plan, result)


def dependency(tmp_path):
    owner = {"pid": 123, "created": 1.0}
    binding = {"path": "training-plan", "sha256": "a" * 64}
    plan = {
        "training_plan": binding,
        "training_owner": owner,
        "training_status": str(tmp_path / "status.json"),
    }
    state = {
        "plan": binding,
        "owner": owner,
        "status": "completed-both-arms-quality-review-pending",
        "results": [
            {"path": str(tmp_path / f"train-{a}-result.json"), "sha256": "b" * 64}
            for a in queue.ARMS
        ],
    }
    return plan, state


def test_dependency_waits_for_exact_live_owner_even_with_terminal_status(tmp_path, monkeypatch):
    plan, state = dependency(tmp_path)
    monkeypatch.setattr(queue, "live", lambda owner: True)
    assert not queue.training_ready(plan, state)
    monkeypatch.setattr(queue, "live", lambda owner: False)
    assert queue.training_ready(plan, state)


@pytest.mark.parametrize("change", ["owner", "plan", "failure", "partial", "other_prefix"])
def test_changed_training_dependency_rejected(tmp_path, monkeypatch, change):
    plan, state = dependency(tmp_path)
    monkeypatch.setattr(queue, "live", lambda owner: False)
    if change == "owner":
        state["owner"] = {"pid": 123, "created": 2.0}
    elif change == "plan":
        state["plan"] = {"path": "other", "sha256": "c" * 64}
    elif change == "failure":
        state["status"] = "failed-preserved-no-automatic-retry"
    elif change == "partial":
        state["status"] = "running-explicit-raw-spatial-continuation"
    else:
        state["results"][0]["path"] = str(tmp_path / "other/train-V131-result.json")
    with pytest.raises((ValueError, RuntimeError)):
        queue.training_ready(plan, state)


def test_all_training_inputs_match_and_single_changed_hash_rejected():
    a, b = endpoint(False)[2], endpoint(True)[2]
    assert queue.matched_results({"V131": a, "V132": b})
    b["observed_inputs"][14549]["batch_sha256"] = "different"
    with pytest.raises(ValueError):
        queue.matched_results({"V131": a, "V132": b})


def controls(tmp_path):
    pred = tmp_path / "saved-prediction"
    pred.write_bytes(b"saved native bytes")
    rows = [
        {
            "id": str(i),
            "arrays": {"path": "input", "sha256": "a" * 64},
            "input_fingerprints": {"packed": "b" * 64},
            "target": {"path": "exact target"},
            "ROI_xywh": [48, 48, 160, 160],
            "display_exposure": 1.0,
            "noise": {"shot": 0.00128, "read": 0.0000065536},
            "reference_role": "exact constructed target",
            "controls": [{"model": {"label": "V120"}}],
        }
        for i in range(2)
    ]
    execution = {
        "observations": copy.deepcopy(rows),
        "step": 20000,
        "training_horizon": 20000,
        "model_label": "V131 endpoint20k",
        "completed_training_checkpoint": True,
    }
    collection = {
        "observations": [{"id": str(i), "prediction": ref(pred)} for i in range(2)],
        "completed_training_checkpoint_verified": True,
    }
    return rows, execution, collection, pred


def test_endpoint_controls_join_without_mutating_sources(tmp_path):
    rows, execution, collection, _ = controls(tmp_path)
    before = copy.deepcopy(rows)
    result = queue.attach_control(rows, execution, collection)
    assert rows == before
    assert all(len(row["controls"]) == 2 for row in result)
    assert all(row["controls"][-1]["model"]["label"] == "V131 endpoint20k" for row in result)


@pytest.mark.parametrize(
    "change",
    [
        "arrays",
        "input_fingerprints",
        "target",
        "ROI_xywh",
        "display_exposure",
        "noise",
        "reference_role",
        "duplicate",
        "partial",
        "progress",
        "label",
        "prediction",
    ],
)
def test_control_identity_and_native_display_provenance_rejected(tmp_path, change):
    rows, execution, collection, pred = controls(tmp_path)
    if change in rows[0]:
        rows[0][change] = "changed"
    elif change == "duplicate":
        collection["observations"].append(collection["observations"][0])
    elif change == "partial":
        collection["observations"].pop()
    elif change == "progress":
        execution["step"] = 1000
    elif change == "label":
        execution["model_label"] = "different endpoint"
    else:
        pred.write_bytes(b"mutated prediction")
    with pytest.raises(ValueError):
        queue.attach_control(rows, execution, collection)


def protocol_fixture(tmp_path, bad_count=False):
    import os
    import sys

    from train_directional_bank_trial import save

    root = tmp_path / "review"
    root.mkdir()
    training_root = tmp_path / "training"
    training_root.mkdir()
    checkpoint = tmp_path / "fixture-only-checkpoint"
    checkpoint.write_text("Protocol fixture; not a neural checkpoint")
    dead = {"pid": os.getpid(), "created": 0.0}
    training_path = training_root / "plan.json"
    save(
        training_path,
        {
            "parent": ref(checkpoint),
            "parent_step": 20000,
            "restoration_tensors_by_arm": {"V131": 91, "V132": 114},
            "backbones": {a: {} for a in queue.ARMS},
        },
    )
    results = []
    inputs = [
        {"step": i, "domain": "protocol-fixture", "clean_sha256": "clean", "batch_sha256": "noisy"}
        for i in range(1, 20001)
    ]
    for arm in queue.ARMS:
        path = training_root / f"train-{arm}-result.json"
        save(
            path,
            {"arm": arm, "owner": dead, "observed_inputs": inputs, "checkpoint": ref(checkpoint)},
        )
        results.append(ref(path))
    training_status = training_root / "status.json"
    save(
        training_status,
        {
            "plan": ref(training_path),
            "owner": dead,
            "status": "completed-both-arms-quality-review-pending",
            "results": results,
        },
    )
    rows = [
        {
            "id": str(i),
            "controls": [{"model": {"label": "V120"}}],
            "arrays": {"path": "fixture-only-input"},
            "input_fingerprints": {},
            "ROI_xywh": [48, 48, 160, 160],
            "display_exposure": 1,
            "noise": {},
            "reference_role": "protocol fixture only",
        }
        for i in range(102)
    ]
    collector = """import hashlib,json,pathlib,sys
p=pathlib.Path(sys.argv[1]);plan=json.loads(p.read_text());root=pathlib.Path(plan['root'])
def ref(q):return {'path':str(q),'sha256':hashlib.sha256(q.read_bytes()).hexdigest()}
q=root/'protocol-only-prediction';q.write_bytes(b'No neural prediction; protocol fixture only')
rows=[{'id':r['id'],'prediction':ref(q)} for r in plan['observations']]
result={'plan':ref(p),'counts':{'root':COUNT,'encoder':COUNT},'completed_training_checkpoint_verified':True,'RNG_unchanged':True,'observations':rows,'protocol_fixture_only':True}
(root/'collection-v1.json').write_text(json.dumps(result))
""".replace("COUNT", "101" if bad_count else "102")
    reporter = """import json,pathlib,sys
p=json.loads(pathlib.Path(sys.argv[1]).read_text());root=pathlib.Path(p['root'])/'report-v1';root.mkdir();(root/'report.json').write_text(json.dumps({'protocol_fixture_only':True}))
"""
    auditor = """import json,pathlib,sys
root=pathlib.Path(sys.argv[1]);(root/'independent-audit-v1.json').write_text(json.dumps({'status':'passed-independent-FFT-metric-and-native-pixel-audit','protocol_fixture_only':True}))
"""
    for arm in queue.ARMS:
        work = root / arm / "work"
        scripts = work / "scripts"
        scripts.mkdir(parents=True)
        for name, text in [
            ("collect_retained_checkpoint_pilot.py", collector),
            ("report_checkpoint_pilot.py", reporter),
            ("audit_checkpoint_pilot.py", auditor),
        ]:
            (scripts / name).write_text(text)
    plan = {
        "root": str(root),
        "training_plan": ref(training_path),
        "training_status": str(training_status),
        "training_owner": dead,
        "training_source_sha256": "protocol-fixture",
        "include_camera_jpegs": True,
        "controller_source": ref(queue.__file__),
        "observations": rows,
        "training_wait_deadline_unix": 10**12,
        "maximum_headroom_wait_seconds": 10,
        "maximum_collector_seconds": 10,
        "maximum_CPU_analysis_seconds": 10,
        "launch_RAM_GiB": 0,
        "runtime_RAM_GiB": 0,
        "launch_internal_reserve_GiB": 0,
        "runtime_internal_reserve_GiB": 0,
        "launch_external_reserve_GiB": 0,
        "runtime_external_reserve_GiB": 0,
        "CUDA_quota_GiB": 0,
        "inputs": [],
        "frozen_files": {},
        "python": sys.executable,
        "scope": "CPU protocol fixture only; no neural/data/quality evidence",
    }
    path = root / "plan.json"
    save(path, plan)
    return path, root


def test_actual_child_protocol_reports_both_endpoints_and_reuses_control(tmp_path, monkeypatch):
    import json

    original_sleep = queue.time.sleep
    monkeypatch.setattr(queue.time, "sleep", lambda seconds: original_sleep(0.01))
    path, root = protocol_fixture(tmp_path)
    queue.controller(path)
    status = json.loads((root / "status.json").read_text())
    assert status["status"] == "completed-both-endpoint-reviews-awaiting-actual-viewing"
    assert set(status["completed"]) == set(status["reports"]) == {"V131", "V132"}
    execution = json.loads((root / "V132/plan-v1.json").read_text())
    assert all(len(row["controls"]) == 2 for row in execution["observations"])
    assert all(
        row["controls"][-1]["model"]["label"] == "V131 endpoint20k"
        for row in execution["observations"]
    )
    with pytest.raises(FileExistsError):
        queue.controller(path)


def test_actual_child_bad_counts_preserved_without_second_endpoint_or_retry(tmp_path, monkeypatch):
    import json

    original_sleep = queue.time.sleep
    monkeypatch.setattr(queue.time, "sleep", lambda seconds: original_sleep(0.01))
    path, root = protocol_fixture(tmp_path, bad_count=True)
    with pytest.raises(AssertionError):
        queue.controller(path)
    state = json.loads((root / "status.json").read_text())
    assert state["status"] == "failed-endpoint-review-preserved-no-automatic-retry"
    assert (root / "V131/collection-v1.json").exists()
    assert not (root / "V132/collection-v1.json").exists()
    with pytest.raises(FileExistsError):
        queue.controller(path)


@pytest.mark.parametrize("include_jpegs", [False, True])
def test_actual_CPU_report_and_independent_audit_preserve_native_camera_pixels(
    tmp_path, include_jpegs
):
    import json
    import os
    import subprocess
    import sys
    from pathlib import Path

    import numpy as np
    from PIL import Image
    from train_directional_bank_trial import save

    root = tmp_path / "report"
    root.mkdir()
    rgb = np.full((1, 3, 256, 256), 0.01, dtype=np.float32)
    arrays = root / "inputs.npz"
    np.savez(
        arrays,
        wb=np.ones((1, 3), dtype=np.float32),
        matrix=np.eye(3, dtype=np.float32)[None],
        noisy_rgb=rgb,
        reference_rgb=rgb,
    )
    prediction = root / "prediction.npy"
    np.save(prediction, rgb)
    jpeg = {}
    expected = []
    for index, key in enumerate(["noisy_camera_jpeg", "reference_camera_jpeg"]):
        pixels = (
            np.arange(160 * 160 * 3, dtype=np.uint32).reshape(160, 160, 3) + index * 37
        ).astype(np.uint8)
        path = root / f"{key}.npy"
        np.save(path, pixels)
        jpeg[key] = {
            "pixels": ref(path),
            "xywh": [index, index, 160, 160],
            "scope": "Native original-pixel protocol fixture, no resizing",
        }
        expected.append(pixels)
    checkpoint = root / "checkpoint-fixture"
    checkpoint.write_text("Protocol fixture only; no neural checkpoint")
    obs = {
        "id": "mesh-protocol",
        "kind": "mesh",
        "arrays": ref(arrays),
        "noise": {"shot": 0.00128, "read": 0.0000065536},
        "display_exposure": 16,
        "reference_role": "Independent qualitative reference fixture; not GT",
        "controls": [{"model": {"label": "V120 fixture"}, "prediction": ref(prediction)}],
        "cases": [{"name": "fixture-left", "ROI_xywh": [48, 48, 160, 160], "camera_JPEGs": jpeg}],
    }
    plan = {
        "root": str(root),
        "observations": [obs],
        "checkpoint": ref(checkpoint),
        "step": 20000,
        "include_camera_jpegs": include_jpegs,
        "model_label": "endpoint fixture",
        "scope": "CPU protocol fixture, no model quality evidence",
        "inputs": [ref(arrays), ref(prediction), *[r["pixels"] for r in jpeg.values()]],
        "frozen_files": {},
    }
    path = root / "plan-v1.json"
    save(path, plan)
    save(
        root / "collection-v1.json",
        {
            "plan": ref(path),
            "counts": {"root": 1, "encoder": 1},
            "observations": [{"id": obs["id"], "prediction": ref(prediction)}],
            "protocol_fixture_only": True,
        },
    )
    repo = Path(__file__).resolve().parents[1]
    env = dict(os.environ, CUDA_VISIBLE_DEVICES="", PYTHONPATH=f"{repo}/src:{repo}/scripts")
    for script, args in [
        ("report_checkpoint_pilot.py", [str(path), str(root / "collection-v1.json")]),
        ("audit_checkpoint_pilot.py", [str(root)]),
    ]:
        subprocess.run(
            [sys.executable, "-P", str(repo / "scripts" / script), *args],
            env=env,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    report = json.loads((root / "report-v1/report.json").read_text())
    audit = json.loads((root / "independent-audit-v1.json").read_text())
    assert (
        audit["Torch_imported"] is False
        and audit["root_forwards"] == audit["encoder_forwards"] == 0
    )
    board = next(x for x in report["images"] if x["name"].endswith("-comparison"))
    assert len(board["panels"]) == (6 if include_jpegs else 4)
    if include_jpegs:
        pixels = np.asarray(Image.open(board["image"]["path"]))
        for panel, cell in zip(board["panels"][-2:], expected, strict=True):
            x, y, w, h = panel["png_xywh"]
            assert (w, h) == (160, 160)
            np.testing.assert_array_equal(pixels[y : y + h, x : x + w], cell)
    assert audit["PNG_channels_exact"] == report["PNG_channels_verified"]
