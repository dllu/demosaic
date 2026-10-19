"""Review the new connected/detached bank pair using the established panel runners."""

import argparse
import json
from pathlib import Path

import review_directional_bank as panels
from train_directional_interval_trial import guard, read, ref, save, sha

TERMINAL = "completed-matched-bank-detachment-original4000-awaiting-full-quality-and-native-review"
CPU_TERMINAL = "completed-matched-bank-detachment-CPU-six-update-preflight"


def require_completed(plan):
    status = read(plan["training_status"])
    engineering = plan.get("engineering_preflight", False)
    terminal = CPU_TERMINAL if engineering else TERMINAL
    if status["status"] != terminal:
        raise RuntimeError("Both fixed training budgets must complete before review")
    assert status["controller"] == plan["training_owner"]
    assert not panels.alive(status["controller"]) and not panels.alive(status["child"])
    assert status["all_sampled_full_legacy_and_input_observations_match"]
    assert status["all_logged_domains_and_LRs_match"]
    assert status["sampled_observation_pairs"] == (6 if engineering else 176)
    assert status["logged_domain_LR_pairs"] == (1 if engineering else 161)
    assert status["plan"] == plan["training_plan"]
    training = read(plan["training_plan"]["path"])
    assert training["engineering_only"] is engineering
    assert training["planned_updates"] == 4000
    assert training["boundary_updates"] == (6 if engineering else 4000)
    assert [a["detach_input"] for a in training["arms"]] == [False, True]
    guard(training)
    return status, training


def boundaries(plan):
    import math

    import torch
    import yaml

    from demosaic.model import ModelConfig

    status, training_plan = require_completed(plan)
    engineering = plan.get("engineering_preflight", False)
    step = 6 if engineering else 4000
    parent = torch.load(
        training_plan["parent"]["path"], map_location="cpu", weights_only=True, mmap=True
    )
    checkpoints, logs, evidence, rngs = [], [], [], []
    for arm in training_plan["arms"]:
        case_ref = status["completed"][arm["name"]]
        assert case_ref == ref(case_ref["path"])
        case = read(case_ref["path"])
        assert not panels.alive(case["owner"])
        checkpoint = case["checkpoint"]
        assert checkpoint == ref(checkpoint["path"])
        state = torch.load(checkpoint["path"], map_location="cpu", weights_only=True, mmap=True)
        cfg = yaml.safe_load(Path(arm["config"]).read_text())
        assert state["step"] == step and state["config"]["steps"] == 4000
        for key, value in cfg.items():
            if key != "validation_protocol":
                assert state["config"][key] == value, key
        assert state["config"]["initialized_from"] == {**training_plan["parent"], "step": 20000}
        expected_config = ModelConfig.from_checkpoint(parent["model_config"]).to_dict()
        expected_config["raw_directional_residual"] = True
        expected_config["raw_directional_bank_context"] = True
        expected_config["raw_directional_bank_detach_input"] = arm["detach_input"]
        assert state["config"]["training_execution"] == "deterministic-v1"
        assert state["config"]["training_execution_runtime"]["deterministic_algorithms"] is True
        assert ModelConfig.from_checkpoint(state["model_config"]).to_dict() == expected_config
        assert len(state["model"]) == len(state["ema"]) == 105
        assert len(state["optimizer"]["state"]) == 103
        for field in ["model", "ema"]:
            assert all(torch.isfinite(v).all() for v in state[field].values())
            unchanged = [
                k
                for k, v in state[field].items()
                if k in parent["ema"] and torch.equal(v, parent["ema"][k])
            ]
            if not engineering:
                assert sorted(unchanged) == ["context.mean", "context.std"]
            else:
                assert {"context.mean", "context.std"}.issubset(unchanged)
        for values in state["optimizer"]["state"].values():
            assert int(values["step"]) == step
            assert all(torch.isfinite(v).all() for v in values.values() if torch.is_tensor(v))
        for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]:
            assert state["config"][key + "_sha256"] == sha(cfg[key])
        assert all(k in state for k in ["python_rng", "torch_rng", "cuda_rng"])
        rngs.append({k: state[k] for k in ("python_rng", "torch_rng", "cuda_rng")})
        rows = [
            json.loads(x)
            for x in Path(case["metrics"]["path"]).read_text().splitlines()
            if json.loads(x).get("event") == "train"
        ]
        assert [r["step"] for r in rows] == [1, *range(25, step + 1, 25)]
        for row in rows:
            logged_step = row["step"]
            progress = max(0, logged_step - 100) / 3900
            expected_lr = (
                1e-5
                * min(1, logged_step / 100)
                * (0.1 + 0.9 * (1 + math.cos(math.pi * progress)) / 2)
            )
            assert row["lr"] == expected_lr
            assert math.isfinite(row["loss"]) and math.isfinite(row["grad_norm"])
        logs.append(rows)
        assert case["capture"]["initial_EMA_exact"]
        assert case["metrics"] == ref(case["metrics"]["path"])
        assert case["sampled_observations"] == ref(case["sampled_observations"]["path"])
        samples = read(case["sampled_observations"]["path"])
        assert [r["step"] for r in samples] == [
            *range(1, min(16, step) + 1),
            *range(25, step + 1, 25),
        ]
        assert all(r["sensor_target_present"] == (r["domain"] != "paired") for r in samples)
        if not checkpoints:
            control_samples = samples
        else:
            for x, y in zip(samples, control_samples, strict=True):
                assert all(
                    x[k] == y[k]
                    for k in [
                        "step",
                        "domain",
                        "legacy_batch_sha256",
                        "input_sha256",
                        "full_batch_sha256",
                    ]
                )

        checkpoints.append(
            {
                **checkpoint,
                "arm": arm["name"],
                "step": step,
                "kind": "joint-checkpoint",
                "label": f"V{arm['version']}-CPU-check{step}"
                if engineering
                else f"V{arm['version']}-original4000",
            }
        )
        evidence.append(
            {
                "arm": arm["name"],
                "source_sha256": state["config"]["source_sha256"],
                "finite_states": [
                    105,
                    105,
                    103,
                ],
                "full4000_common_tensor_change_requirement_applied": not engineering,
                "result": case_ref,
                "initialization": case["capture"],
            }
        )
    captures = [e["initialization"] for e in evidence]
    for key in [
        "initial_EMA_exact",
        "initial_local_sha256",
        "initial_bank_sha256",
        "initial_model_sha256",
        "first_raw_gradient_sha256",
        "first_output_sha256",
        "DINO_sha256",
        "gradient_hash_zero_signs_normalized",
    ]:
        assert captures[0][key] == captures[1][key]
    assert captures[0]["gradient_hash_zero_signs_normalized"] is True
    for a, b in zip(*logs, strict=True):
        assert all(a[k] == b[k] for k in ["step", "domain", "lr"])
    assert evidence[0]["source_sha256"] == evidence[1]["source_sha256"]
    assert rngs[0]["python_rng"] == rngs[1]["python_rng"]
    assert torch.equal(rngs[0]["torch_rng"], rngs[1]["torch_rng"])
    assert len(rngs[0]["cuda_rng"]) == len(rngs[1]["cuda_rng"])
    assert all(
        torch.equal(a, b) for a, b in zip(rngs[0]["cuda_rng"], rngs[1]["cuda_rng"], strict=True)
    )
    save(
        Path(plan["root"]) / "training-boundary.json",
        {
            "status": "independently-verified-bank-detachment-CPU-six-update-boundaries"
            if engineering
            else "independently-verified-both-directional-bank-original4000-boundaries",
            "engineering_preflight": engineering,
            "training_status": ref(plan["training_status"]),
            "checkpoints": checkpoints,
            "evidence": evidence,
            "all_sampled_full_legacy_and_input_observations_match": True,
            "sampled_observation_pairs": len(samples),
            "all_logged_domains_and_LRs_match": True,
            "logged_domain_LR_pairs": len(logs[0]),
            "final_Python_CPU_CUDA_RNG_exact": True,
            "scope": "Full-state engineering boundary only; no quality claim or continuation.",
        },
    )


def install():
    # Panel inference/statistics/crop logic is shared unchanged. Only training
    # completion and checkpoint-policy validation differ for this experiment.
    panels.require_completed = require_completed
    panels.boundaries = boundaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["controller", "worker"])
    parser.add_argument("plan", type=Path)
    parser.add_argument(
        "--stage",
        choices=[
            "boundary",
            "known",
            "unseen",
            "full427",
            "statistics",
            "sensitivity",
            "gfx",
            "analytic",
            "hue",
            "highlights",
        ],
    )
    args = parser.parse_args()
    install()
    if args.mode == "controller":
        panels.controller(args.plan)
    else:
        plan = read(args.plan)
        assert not plan.get("engineering_preflight", False) or args.stage == "boundary"
        panels.worker(args.plan, args.stage)
