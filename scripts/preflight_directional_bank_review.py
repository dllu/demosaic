"""CPU-only complete historical statistics/crop replay and real small-model load."""

import argparse
import os
import shutil
from pathlib import Path

import numpy as np
import torch
from audit_commons_source_sensitivity import audit as audit_sensitivity
from build_native_crop_board import build
from close_directional_bank_review import native_report
from compare_long_commons_scores import rows
from profile_raw_kernel_inference import model_hash
from report_commons_source_sensitivity import run as sensitivity
from review_directional_bank import statistics
from score_directional_bank_eligibility import evaluate_analytic, evaluate_primary
from score_directional_eligibility import evaluate as old_criteria
from train_directional_interval_trial import read, ref, save

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path
from demosaic.train import batch_fingerprint


def main(historical_path, output, model_receipt_path, input_receipt_path):
    os.nice(10)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    receipt = read(model_receipt_path)
    input_receipt = read(input_receipt_path)
    payload_path = Path(input_receipt["payload"]["path"])
    assert ref(payload_path) == input_receipt["payload"]
    assert (
        input_receipt["batch_sha256"]
        == "b0ac985abbfa82a415e731e5094cb4f5ff31452e7ed7fbb4a7c39e870babcc7f"
    )
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(__file__, output / "executed-source.py")
    historical = read(historical_path)
    boundary = read(Path(historical["root"]) / "training-boundary.json")
    checkpoints = boundary["checkpoints"]
    plan = {**historical, "root": str(output)}
    statistics(plan, checkpoints)
    result = read(output / "primary-statistics.json")
    previous = read(Path(historical["root"]) / "primary-statistics.json")
    assert result["comparisons"] == previous["comparisons"]
    result.update(
        preflight_only=True,
        scope="Historical V78/V79/V63 scores only; no new inference or V80/V81 evidence.",
    )
    save(output / "primary-statistics.json", result)
    parent = {**historical["parent"], "label": "V63-parent"}
    actual = evaluate_primary(result, *checkpoints, parent)
    expected = old_criteria(previous, *checkpoints, parent)
    assert actual["arms"] == expected["arms"]
    assert actual["matched_bank_effect"] == expected["matched_interval_effect"]
    sensitivity(
        output / "primary-statistics.json",
        ref(output / "primary-statistics.json")["sha256"],
        Path(historical["cohorts"]["path"]),
        historical["cohorts"]["sha256"],
        output / "sensitivity",
    )
    independent = audit_sensitivity(output / "sensitivity")
    save(output / "sensitivity-independent-audit.json", independent)
    analytic = Path(historical["outputs"]["analytic"])
    weak = evaluate_analytic(
        read(analytic / "summary.json"), rows(analytic / "per-case.jsonl"), *checkpoints
    )
    assert not weak["all_criteria_pass"]
    save(
        output / "historical-criteria.json",
        {"preflight_only": True, "primary": actual, "weak_carriers": weak},
    )
    closure = read(Path(historical["root"]) / "closure-plan.json")
    native = []
    for panel, kind in (("full427", "synthetic"), ("known", "camera"), ("unseen", "camera")):
        report = native_report(
            Path(historical["outputs"][panel]) / "summary.json",
            Path(closure["retained_native_reports"][panel]["path"]),
            output / (panel + "-sources"),
            kind,
            historical["parent"]["sha256"],
            historical["rawnind_sha256"],
        )
        board = build([report], output / (panel + "-native.png"), kind)
        native.append(
            {
                "panel": panel,
                "board": board["board"],
                "receipt": ref(output / (panel + "-native.json")),
                "native_cells": board["native_cells_exact"],
                "triplets": len(board["source_triplets"]),
            }
        )
    # Actual six-update GPU checkpoints, loaded as CPU inference models. This
    # checks new architecture portability without scoring held-out photographs.
    payload = torch.load(payload_path, map_location="cpu", weights_only=True, mmap=True)["batch"]
    assert batch_fingerprint(payload) == input_receipt["batch_sha256"]
    batch = {
        k: payload[k][:1].clone()
        for k in ("packed", "variance", "colors", "wb", "matrix", "shot", "read")
    }
    for k in ("packed", "variance"):
        batch[k] = batch[k][..., 48:80, 48:80].contiguous()
    portability = []
    for case, flag in (("control", False), ("bank", True)):
        item = receipt["cases"][case]["checkpoint"]
        assert ref(item["path"]) == item
        net, state = load_checkpoint(item["path"], "cpu")
        assert state["step"] == 6 and state["loaded_sha256"] == item["sha256"]
        assert net.config.raw_directional_bank_context is flag
        net.eval().set_noise(batch["shot"], batch["read"])
        before = model_hash(net)
        with torch.inference_mode(), amp_context("cpu", dtype="float32"):
            value = net(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
        assert (
            value.shape == (1, 3, 64, 64)
            and value.dtype == torch.float32
            and torch.isfinite(value).all()
        )
        assert model_hash(net) == before
        assert all(p.grad is None for p in net.parameters())
        path = output / (case + "-CPU64-f32.npy")
        np.save(path, value.numpy(), allow_pickle=False)
        portability.append(
            {"checkpoint": item, "prediction": ref(path), "state_unchanged": True, "finite": True}
        )
        del net, state
    assert not torch.cuda.is_initialized()
    save(
        output / "receipt.json",
        {
            "status": "completed-historical-bank-review-preflight-no-new-quality-evidence",
            "historical_plan": ref(historical_path),
            "driver": ref(output / "executed-source.py"),
            "primary_statistics": ref(output / "primary-statistics.json"),
            "comparison_rows_exact": len(result["comparisons"]),
            "primary_audits": result["audits"],
            "source_sensitivity": ref(output / "sensitivity/result.json"),
            "independent_sensitivity_audit": ref(output / "sensitivity-independent-audit.json"),
            "criteria_replay": ref(output / "historical-criteria.json"),
            "native_boards": native,
            "CPU_portability": portability,
            "cached_training_input": ref(payload_path),
            "input_receipt": ref(input_receipt_path),
            "model_receipt": ref(model_receipt_path),
            "input_sha256": batch_fingerprint(batch),
            "native_input_ROI_xywh": [96, 96, 64, 64],
            "CUDA_initialized": False,
            "scope": "Historical V78/V79/V63 scalar statistics, fixed418/416 sensitivities and unchanged native crop composition only. Two actual discarded six-update models loaded on CPU/FP32 with one cached training crop; outputs are functional checks, not quality metrics. No new V80/V81 trained quality result, promotion or manual-view claim.",
        },
    )
    print(
        {
            "receipt": ref(output / "receipt.json"),
            "historical_comparisons": len(result["comparisons"]),
            "CPU_model_checks": len(portability),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--historical-review", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-receipt", type=Path, required=True)
    parser.add_argument("--input-receipt", type=Path, required=True)
    args = parser.parse_args()
    main(args.historical_review, args.output, args.model_receipt, args.input_receipt)
