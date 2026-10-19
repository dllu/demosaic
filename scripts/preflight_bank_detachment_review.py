"""CPU-only review integration on completed engineering and historical records."""

import argparse
import gc
import os
from pathlib import Path

import numpy as np
import torch
from compare_long_commons_scores import rows
from profile_raw_kernel_inference import model_hash
from review_bank_detachment import boundaries, require_completed
from review_directional_bank import statistics
from score_bank_detachment_eligibility import evaluate_analytic, evaluate_primary
from score_bank_detachment_eligibility import main as apply_production_criteria
from score_directional_bank_eligibility import evaluate_analytic as previous_analytic
from score_directional_bank_eligibility import evaluate_primary as previous_primary
from train_directional_interval_trial import guard, read, ref, save

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.train import batch_fingerprint


def main(plan_path):
    plan = read(plan_path)
    guard(plan)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    os.nice(10)
    torch.set_num_threads(2)
    output = Path(plan["root"])
    output.mkdir(parents=True, exist_ok=False)
    engineering_plan = read(plan["engineering_training_plan"]["path"])
    engineering_status = read(Path(engineering_plan["root"]) / "status.json")
    boundary_plan = {
        "root": str(output),
        "training_status": str(Path(engineering_plan["root"]) / "status.json"),
        "training_plan": plan["engineering_training_plan"],
        "training_owner": engineering_status["controller"],
        "engineering_preflight": True,
    }
    boundaries(boundary_plan)
    boundary = read(output / "training-boundary.json")
    assert boundary["engineering_preflight"] and boundary["sampled_observation_pairs"] == 6
    save(output / "engineering-plan.json", boundary_plan)
    try:
        apply_production_criteria(output / "engineering-plan.json", output / "forbidden.json")
    except ValueError as error:
        assert "Production training boundary" in str(error)
    else:
        raise AssertionError("Engineering checkpoints must not pass the quality boundary")
    assert not (output / "forbidden.json").exists()
    try:
        require_completed({**plan["production_review_boundary"], "engineering_preflight": False})
    except RuntimeError as error:
        assert "Both fixed training budgets" in str(error)
    else:
        raise AssertionError("Live/incomplete production training must refuse review")

    historical = read(plan["historical_review"]["path"])
    checkpoints = read(Path(historical["root"]) / "training-boundary.json")["checkpoints"]
    replay = {**historical, "root": str(output / "historical")}
    Path(replay["root"]).mkdir()
    statistics(replay, checkpoints)
    result = read(Path(replay["root"]) / "primary-statistics.json")
    previous = read(Path(historical["root"]) / "primary-statistics.json")
    assert result["comparisons"] == previous["comparisons"]
    parent = dict(historical["parent"], label="V63-parent")
    new_primary = evaluate_primary(result, *checkpoints, parent)
    old_primary = previous_primary(result, *checkpoints, parent)
    assert new_primary["arms"] == old_primary["arms"]
    assert new_primary["matched_detachment_effect"] == old_primary["matched_bank_effect"]
    analytic_root = Path(historical["outputs"]["analytic"])
    analytic_summary = read(analytic_root / "summary.json")
    analytic_rows = rows(analytic_root / "per-case.jsonl")
    new_analytic = evaluate_analytic(analytic_summary, analytic_rows, *checkpoints)
    old_analytic = previous_analytic(analytic_summary, analytic_rows, *checkpoints)
    assert (
        new_analytic["high_noise_weak_carriers"]["all_criteria_pass"]
        == old_analytic["all_criteria_pass"]
    )
    assert abs(new_analytic["ADC_detail"]["detached_minus_connected_gain"] + 0.329384677) < 1e-8
    assert not new_analytic["ADC_detail"]["signed_gain_improves_at_least_.05"]
    try:
        evaluate_analytic(analytic_summary, analytic_rows[1:], *checkpoints)
    except (AssertionError, ValueError):
        pass
    else:
        raise AssertionError("Incomplete analytic coverage must refuse threshold application")
    save(
        output / "historical-criteria-replay.json",
        {
            "preflight_only": True,
            "primary": new_primary,
            "analytic": new_analytic,
            "scope": "Historical V80/V81/V63 statistics only. Position labels connected/detached are generic scorer roles; these are not V82/V83 measurements.",
        },
    )

    # Use the actual paired six-update CUDA optimizer checkpoints, never a
    # modified state/step or fabricated final-boundary receipt.
    receipt = read(plan["CUDA_optimizer_receipt"]["path"])
    inputs = read(plan["training_input_receipt"]["path"])
    assert ref(inputs["payload"]["path"]) == inputs["payload"]
    payload = torch.load(
        inputs["payload"]["path"], map_location="cpu", weights_only=True, mmap=True
    )
    assert batch_fingerprint(payload["batch"]) == inputs["batch_sha256"]
    batch = {
        k: payload["batch"][k][:1].clone()
        for k in ("packed", "variance", "colors", "wb", "matrix", "shot", "read")
    }
    del payload
    for k in ("packed", "variance"):
        batch[k] = batch[k][..., 48:80, 48:80].contiguous()
    portability = []
    for name, flag in [("connected", False), ("detached", True)]:
        checkpoint = receipt["results"][name]["checkpoint"]
        assert ref(checkpoint["path"]) == checkpoint
        net, state = load_checkpoint(checkpoint["path"], "cpu")
        assert state["step"] == 6 and state["loaded_sha256"] == checkpoint["sha256"]
        assert (
            net.config.raw_directional_bank_context
            and net.config.raw_directional_bank_detach_input is flag
        )
        del state
        net.eval().set_noise(batch["shot"], batch["read"])
        before = model_hash(net)
        with torch.inference_mode(), amp_context("cpu", dtype="float32"):
            value = net(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
        assert value.shape == (1, 3, 64, 64) and value.dtype == torch.float32
        assert torch.isfinite(value).all() and model_hash(net) == before
        assert all(p.grad is None for p in net.parameters())
        image = output / (name + "-CPU64-f32.npy")
        np.save(image, value.numpy(), allow_pickle=False)
        portability.append(
            {
                "checkpoint": checkpoint,
                "prediction": ref(image),
                "state_unchanged": True,
                "detach_input": flag,
            }
        )
        del net, value
        gc.collect()
    assert not torch.cuda.is_initialized()
    guard(plan)
    save(
        output / "receipt.json",
        {
            "status": "completed-bank-detachment-review-CPU-preflight-no-quality-result",
            "plan": ref(plan_path),
            "driver": ref(__file__),
            "actual_six_update_boundary": ref(output / "training-boundary.json"),
            "live_incomplete_production_review_rejected": True,
            "engineering_criteria_application_rejected": True,
            "historical_comparisons_exact": len(result["comparisons"]),
            "historical_criteria_replay": ref(output / "historical-criteria-replay.json"),
            "incomplete_analytic_rows_rejected": True,
            "CPU_portability": portability,
            "CUDA_initialized": False,
            "scope": "Actual engineering checkpoint metadata/owner/RNG validation, historical statistics/scorer parity, ADC gate/missing-row refusal and real CPU64 inference of both six-update gradient-policy checkpoints. No production-quality score, held-out inference, new training, image resize or promotion.",
        },
    )
    print(
        {
            "receipt": ref(output / "receipt.json"),
            "comparisons": len(result["comparisons"]),
            "models": len(portability),
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    main(args.plan)
