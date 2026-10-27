"""Repair a verified zero-forward frequency-checkpoint identity rejection."""

import argparse
import inspect
import shutil
import time
from pathlib import Path

from rebind_unstarted_quality_queue import replace_dependencies
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import live

REPO = Path(__file__).resolve().parents[1]


def zero_forward_failure(original, state):
    root = Path(original["root"])
    assert state["status"] == "failed-quality-evaluation-preserved-no-automatic-retry"
    assert not live(state["owner"]) and state.get("child") and not live(state["child"])
    assert state["stage"] == "photo" and not state["completed"]
    assert {p.name for p in root.glob("*.claim")} == {"controller.claim", "photo.claim"}
    evaluation = read(root / "evaluation-plan-v1.json")
    archive = Path(evaluation["stages"]["photo"]["output"]) / "archive"
    assert (archive / "records.jsonl").stat().st_size == 0
    assert not any((archive / "predictions").iterdir())
    assert not any((archive / "supervision").iterdir())
    assert not any(
        Path(s["output"]).exists() for k, s in evaluation["stages"].items() if k != "photo"
    )
    log = (root / "photo-v1.log").read_text()
    assert "assert len(model.restoration_state_dict()) == 91" in log
    assert log.rstrip().endswith("AssertionError")
    return evaluation


def prepare(original_path, root):
    import torch
    from collect_quality_predictions import verify_restoration_state
    from queue_matched_quality_predictions import verify_frequency_training_state

    original_path, root = original_path.resolve(), root.resolve()
    assert root.is_relative_to(REPO / ".cache")
    original = read(original_path)
    guard(original)
    old_root = Path(original["root"])
    state = read(old_root / "status.json")
    assert state["queue_plan"] == ref(original_path)
    evaluation = zero_forward_failure(original, state)
    training = read(original["training_execution"]["path"])
    guard(training)
    producer = read(original["training_status"])
    assert producer["status"] == original["expected_training_terminal"]
    assert not live(producer["controller"]) and producer.get("child") is None
    states = {}
    parent = torch.load(
        training["parent"]["path"], map_location="cpu", mmap=True, weights_only=True
    )
    for item in evaluation["checkpoints"]:
        assert ref(item["path"]) == {k: item[k] for k in ("path", "sha256")}
        snapshot = torch.load(item["path"], map_location="cpu", mmap=True, weights_only=True)
        result_binding = producer["completed"][f"train-{item['arm']}"]
        assert ref(result_binding["path"]) == result_binding
        result = read(result_binding["path"])
        assert result["checkpoint"]["sha256"] == item["sha256"] and not live(result["owner"])
        verify_frequency_training_state(
            result, snapshot, parent, training["arm_scopes"][item["arm"]]
        )
        assert len(snapshot["model"]) == len(snapshot["ema"]) == 96
        states[item["arm"]] = {
            "checkpoint": {k: item[k] for k in ("path", "sha256")},
            "EMA_tensors": 96,
            "optimizer_states": len(snapshot["optimizer"]["state"]),
            "all_optimizer_steps": 20000,
            "state_finite": True,
        }
    del parent, snapshot
    root.mkdir(parents=True, exist_ok=False)
    files = dict(original["frozen_files"])
    files.update({r["path"]: r["sha256"] for r in original["inputs"]})
    for name, digest in files.items():
        source = Path(name)
        if source.is_relative_to(old_root):
            destination = root / source.relative_to(old_root)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            assert ref(destination)["sha256"] == digest
    plan = replace_dependencies(original, [], str(old_root), str(root))
    collector = Path(plan["collector_source"]["path"])
    text = collector.read_text()
    old = (
        "            assert len(model.restoration_state_dict()) == 91\n"
        '            assert all(torch.equal(v.cpu(), state["ema"][k]) for k, v in model.restoration_state_dict().items())'
    )
    assert text.count(old) == 1
    text = text.replace(old, "            verify_restoration_state(model, state, checkpoint)")
    marker = "@torch.inference_mode()\ndef collect("
    assert text.count(marker) == 1
    collector.write_text(
        text.replace(marker, inspect.getsource(verify_restoration_state) + "\n\n" + marker)
    )
    controller = Path(plan["controller_source"]["path"])
    text = controller.read_text()
    marker = '                "arm": name,\n'
    assert text.count(marker) == 1
    text = text.replace(marker, marker + '                "EMA_tensors": len(snapshot["ema"]),\n')
    marker = "                    assert time.monotonic() - began < 43200\n"
    assert text.count(marker) == 1
    text = text.replace(
        marker,
        '                    if deadline := plan.get("absolute_stage_deadlines", {}).get(stage):\n                        assert time.time() < deadline\n'
        + marker,
    )
    marker = "                assert time.monotonic() - began < 7200\n"
    assert text.count(marker) == 1
    text = text.replace(
        marker,
        '                if deadline := plan.get("absolute_stage_headroom_deadlines", {}).get(stage):\n                    assert time.time() < deadline\n'
        + marker,
    )
    controller.write_text(text)
    plan["collector_source"], plan["controller_source"] = ref(collector), ref(controller)
    plan["frozen_files"][str(collector)] = ref(collector)["sha256"]
    plan["frozen_files"][str(controller)] = ref(controller)["sha256"]
    # The failed first photo worker spent no neural budget, but its original
    # 12h worker deadline still applies. Its headroom bound is conservative.
    plan["absolute_stage_deadlines"] = {"photo": state["child"]["created"] + 43200}
    plan["absolute_stage_headroom_deadlines"] = {"photo": state["child"]["created"] - 300 + 7200}
    original_wait_deadline = state["owner"]["created"] + original["maximum_training_wait_seconds"]
    plan["maximum_training_wait_seconds"] = original_wait_deadline - time.time()
    assert plan["maximum_training_wait_seconds"] > 0
    copied = root / "repair-source.py"
    shutil.copyfile(__file__, copied)
    plan["frozen_files"][str(copied)] = ref(copied)["sha256"]
    declaration = root / "identity-repair-v1.json"
    save(
        declaration,
        {
            "status": "verified-zero-forward-identity-repair-no-inference-repeated",
            "original_plan": ref(original_path),
            "original_failure": ref(old_root / "status.json"),
            "original_evaluation": ref(old_root / "evaluation-plan-v1.json"),
            "original_failure_log": ref(old_root / "photo-v1.log"),
            "source": ref(copied),
            "checkpoints": states,
            "original_root_forwards": 0,
            "original_encoder_forwards": 0,
            "original_archive_records": 0,
            "original_predictions": 0,
            "original_absolute_dependency_deadline_unix": original_wait_deadline,
            "retained_first_photo_deadline_unix": plan["absolute_stage_deadlines"]["photo"],
            "scope": "The frozen collector rejected96-tensor frequency EMA checkpoints using a legacy91-tensor assertion, before recording a model or executing root/encoder forwards. Explicit per-checkpoint state counts and exact EMA checks replace that assertion. All inference source files, observations, checkpoints, source/noise/profile inputs, stage counts and model/worker budgets otherwise retained. Original empty archive/logs/claims/failures preserved; no trained-prefix/check/control inference repeated.",
        },
    )
    plan["inputs"] += [ref(original_path), ref(old_root / "status.json"), ref(declaration)]
    plan["identity_repair"] = ref(declaration)
    plan["scope"] += (
        " Explicit zero-forward restoration-state identity repair;96-tensor frequency checkpoints declared individually, original first photo deadline retained."
    )
    path = root / "queue-plan-v1.json"
    save(path, plan)
    guard(plan)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original_plan", type=Path)
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    print(prepare(args.original_plan, args.root))
