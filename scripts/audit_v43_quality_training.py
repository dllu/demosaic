"""Independently verify a completed matched V43 arm without inference or CUDA."""

import argparse
import collections
import datetime
import gc
import json
import math
import os
import shutil
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import psutil
import torch
import yaml
from train_directional_bank_trial import guard, read, ref, save
from train_v43_quality_trial import expected_training_model_config

REPO = Path(__file__).resolve().parents[1]


def audit(root, arm, output):
    output = output.resolve()
    assert output.is_relative_to(REPO / ".cache") and not output.exists()
    output.parent.mkdir(parents=True, exist_ok=True)
    operator_snapshot = output.with_name(output.stem + "-executed-source.py")
    assert not operator_snapshot.exists()
    shutil.copyfile(__file__, operator_snapshot)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(1)
    plan_path = root / "plan.json"
    plan = read(plan_path)
    guard(plan)
    assert not plan["engineering_only"]
    updates = plan["planned_updates"]
    assert updates > 0 and arm in plan["arms"]
    result_path = root / f"train-{arm}-result.json"
    result = read(result_path)
    assert result["status"] == "completed-V43-quality-stage-awaiting-independent-evaluation"
    assert result["plan"] == ref(plan_path) and result["phase"] == "train" and result["arm"] == arm
    assert not result["engineering_only"] and result["CUDA_initialized"]
    assert result["fresh_optimizer_empty"]
    assert result["initial_model_sha256"] == plan.get(
        "initial_model_sha256",
        "4a45d92210acaeca3d4189c78eb22aa1cbc33f28b971dbeb56d1f6f29d62ed9a",
    )
    assert (
        result["DINO_sha256"] == "35035ba142eb119cd5980cf0d9809bfa28f622538c259ffb0fcf348ca6e68898"
    )
    owner = result["owner"]
    try:
        process = psutil.Process(owner["pid"])
        live = (
            process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        live = False
    assert not live
    assert ref(result["checkpoint"]["path"]) == result["checkpoint"]
    assert ref(result["metrics"]["path"]) == result["metrics"]
    cfg = yaml.safe_load(Path(plan["configs"][arm]["train"]["path"]).read_text())
    protocol = yaml.safe_load((Path(plan["work"]) / "configs/evaluation.yaml").read_text())
    assert len(protocol["conditions"]) == 7 and len(protocol["patterns"]) == 4
    assert cfg["validation_images"] == 8 and cfg["val_batches"] == 4
    steps = [*plan["retain_steps"], updates]
    assert steps == plan.get("validation_steps", steps)
    expected_validation_forwards = len(steps) * (4 + 28 * math.ceil(8 / cfg["batch_size"]))
    assert result["counts"] == {
        "training_forwards": updates,
        "validation_forwards": expected_validation_forwards,
        "DINO_calls": updates + expected_validation_forwards,
        "optimizer_steps": updates,
    }
    events = [json.loads(line) for line in Path(result["metrics"]["path"]).read_text().splitlines()]
    training = [r for r in events if r.get("event") == "train"]
    validation = [r for r in events if r.get("event") == "validation"]
    assert [r["step"] for r in training] == [1, *range(25, updates + 1, 25)]
    assert training == result["logged_training_observations"]
    assert all(math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"]) for r in training)
    assert {r["domain"] for r in training} == {"native-RAW-synthetic", "paired-RAW", "synthetic"}
    assert [r["step"] for r in validation] == steps
    cells = {(c["name"], p) for c in protocol["conditions"] for p in protocol["patterns"]}
    for event in validation:
        cases = event["panel_cases"]
        assert event["panel_images"] == 8 and len(cases) == 28
        assert {(c["condition"], c["pattern"]) for c in cases} == cells
        assert all(c["images"] == 8 for c in cases)
        assert all(math.isfinite(x) for c in cases for x in c["metrics"].values() if x is not None)
        assert all(math.isfinite(x) for x in event.values() if isinstance(x, (int, float)))
    probe = read(root / f"CUDA-{arm}-result.json")
    assert result["early_observations"] == probe["early_observations"]
    assert result["source_sha256"] == probe["source_sha256"]
    assert [r["step"] for r in result["early_observations"]] == list(range(1, 25))

    sys.path.insert(0, str(Path(plan["work"]) / "src"))
    from demosaic.model import ModelConfig

    parent = torch.load(plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True)
    parent_cfg = ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
    expected_cfg = expected_training_model_config(parent_cfg, plan, arm)
    cohort = read(plan["curation"]["path"])["cohorts"]["small" if arm == "V93" else "large"]
    run = Path(result["checkpoint"]["path"]).parent
    checkpoints = [(run / f"step-{n:06d}.pt", n) for n in plan["retain_steps"]]
    checkpoints += [(run / "last.pt", updates), (run / "best.pt", None)]
    retained = []
    for path, expected_step in checkpoints:
        identity = ref(path)
        state = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        step, actual = state["step"], state["config"]
        assert step in steps and (expected_step is None or step == expected_step)
        assert json.dumps(
            ModelConfig.from_checkpoint(state["model_config"]).to_dict(), sort_keys=True
        ) == json.dumps(expected_cfg, sort_keys=True)
        assert state["model"].keys() == state["ema"].keys() == parent["ema"].keys()
        assert len(state["model"]) == len(state["ema"]) == 71
        for group in ("model", "ema"):
            assert all(torch.isfinite(v).all().item() for v in state[group].values())
            assert any(not torch.equal(v, parent["ema"][k]) for k, v in state[group].items())
        optimizer = state["optimizer"]["state"]
        assert len(optimizer) == 69
        for item in optimizer.values():
            assert float(item["step"]) == step
            assert all(
                torch.isfinite(v).all().item() for v in item.values() if isinstance(v, torch.Tensor)
            )
        assert actual["initialized_from"] == {
            **plan["parent"],
            "step": plan.get("parent_step", 2000),
        }
        for key in cfg:
            if key != "validation_protocol":
                assert actual[key] == cfg[key], key
        assert actual["manifest_sha256"] == cohort["manifest"]["sha256"]
        for key in ("manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"):
            assert ref(actual[key])["sha256"] == actual[key + "_sha256"]
        for key in ("validation_manifest", "raw_clean_manifest", "paired_manifest"):
            assert actual[key + "_sha256"] == parent["config"][key + "_sha256"]
        assert (
            ref(actual["validation_protocol"])["sha256"]
            == actual["validation_protocol_sha256"]
            == ref(Path(plan["work"]) / "configs/evaluation.yaml")["sha256"]
        )
        assert actual["source_sha256"] == result["source_sha256"]
        prefix = [v["panel_srgb_psnr"] for v in validation if v["step"] <= step]
        assert state["best"] == max(prefix)
        if path.name == "best.pt":
            assert state["best"] == max(v["panel_srgb_psnr"] for v in validation)
            assert (
                next(v["panel_srgb_psnr"] for v in validation if v["step"] == step) == state["best"]
            )
        assert ref(path) == identity
        retained.append(
            {
                "checkpoint": identity,
                "step": step,
                "model_tensors_finite": 71,
                "EMA_tensors_finite": 71,
                "Adam_states_finite_with_correct_step": 69,
                "canonical_model_config_and_tensor_keys_exact_parent": expected_cfg == parent_cfg,
                "canonical_model_config_exact_declared_policy_and_tensor_keys_exact_parent": True,
            }
        )
        del state, optimizer, item
        gc.collect()
    assert retained[-2]["checkpoint"] == result["checkpoint"]
    guard(plan)
    assert not torch.cuda.is_initialized()
    save(
        output,
        {
            "status": "completed-matched-V43-arm-independent-saved-state-and-trace-audit-passed",
            "recorded_local": datetime.datetime.now(ZoneInfo("America/Los_Angeles")).isoformat(),
            "operator": ref(operator_snapshot),
            "operator_root_source_at_execution": ref(__file__),
            "plan": ref(plan_path),
            "arm": arm,
            "worker_result": ref(result_path),
            "actual_worker_owner_exited": owner,
            "counts": result["counts"],
            "primary_final_EMA_checkpoint": result["checkpoint"],
            "metrics": result["metrics"],
            "retained_checkpoints": retained,
            "initial_model_sha256_from_executed_worker": result["initial_model_sha256"],
            "DINO_sha256_from_executed_worker": result["DINO_sha256"],
            "source_sha256": result["source_sha256"],
            "curated_training_membership": cohort,
            "training_metric_rows_with_finite_loss_and_gradients": len(training),
            "training_domain_log_counts": dict(collections.Counter(r["domain"] for r in training)),
            "all_first24_production_inputs_exact_discarded_CUDA_probe": True,
            "validation": {
                "steps": steps,
                "sources": 8,
                "cells_per_validation": 28,
                "observations_per_validation": 224,
                "all_present_metrics_finite": True,
                "training_subset_only": True,
            },
            "worker_final_frozen_DINO_assertions_completed": True,
            "auditor_CUDA_initialized": False,
            "scope": f"Independent CPU-only hashes, exact stage lineage/effective architecture, every retained model/EMA/Adam state and step, exact final/probe input traces, fixed manifests/protocol and scheduled training-validation coverage. Frozen executed worker additionally checks final DINO weights/no gradients. No new inference or training; this is not a held-out quality comparison, native-crop review, inference-speed result or promotion. Fixed{updates} final EMA remains primary; validation-best and intermediates remain separate.",
        },
    )
    print(ref(output))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "--arm", choices=("V93", "V94", "V95", "V96", "V97", "V98", "V99"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.root.resolve(), args.arm, args.output)
