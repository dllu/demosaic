"""Discarded equal-example CUDA batch4/batch16 optimization comparison."""

import argparse
import json
import math
import os
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from probe_raw_feature_coordinates import alive, batch_fingerprint, guard, loss_for, mse, read, ref
from probe_raw_residual_units import coordinates, digest

from demosaic.cfa import bilinear
from demosaic.losses import reconstruction_loss
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.paired_training import paired_reconstruction_loss
from demosaic.precision import amp_context
from demosaic.train import make_optimizer


def grouped_loss(model, batches, domains):
    """One physical batch; equal original losses for equally sized domain groups."""
    if len(batches) != len(domains) or not batches:
        raise ValueError("Matching nonempty batches/domains required")
    size = len(batches[0]["packed"])
    if any(len(batch["packed"]) != size for batch in batches):
        raise ValueError("Domain groups must have equal sizes")
    inputs = [
        torch.cat([batch[key] for batch in batches])
        for key in ["packed", "variance", "colors", "wb", "matrix"]
    ]
    prediction, auxiliary = model(*inputs, auxiliary=True)
    losses = []
    for index, (batch, domain) in enumerate(zip(batches, domains, strict=True)):
        region = slice(index * size, (index + 1) * size)
        if domain == "paired":
            value, _ = paired_reconstruction_loss(prediction[region], batch, auxiliary[region])
        elif domain in ["commons", "native"]:
            value, _ = reconstruction_loss(
                prediction[region], batch, auxiliary[region], physical_fp32=True
            )
        else:
            raise ValueError("Unknown training domain")
        losses.append(value)
    return torch.stack(losses).mean()


def run(plan_path):
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read(plan_path)
    guard(plan)
    for entry in plan["completed_GPU_workflows"]:
        state = read(entry["path"])
        assert state["status"] == entry["terminal_status"]
        assert not alive(state["controller"])
        assert not state.get("child") or not alive(state["child"])
    assert torch.cuda.is_available()
    root, status = Path(plan["root"]), Path(plan["status"])
    assert not status.exists()
    with (root / "launch.claim").open("x") as stream:
        stream.write(str(os.getpid()) + "\n")
    info = {"controller": {"pid": os.getpid(), "created": psutil.Process().create_time()}}

    def record(state, **fields):
        info.update(status=state, updated_unix=time.time(), **fields)
        temporary = status.with_suffix(".tmp")
        temporary.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n")
        temporary.replace(status)
        print(json.dumps(info), flush=True)

    try:
        record("loading-training-only-fixtures-for-discarded-batch-learning", plan=ref(plan_path))
        fixtures = read(plan["fixtures"]["path"])
        assert len(fixtures) == 16
        batches = []
        for entry in fixtures:
            assert ref(entry["fixture"]["path"]) == entry["fixture"]
            assert all(row.get("split", "train") == "train" for row in entry["sources"])
            with np.load(entry["fixture"]["path"], allow_pickle=False) as arrays:
                values = {key: torch.from_numpy(arrays[key].copy()) for key in arrays.files}
            assert values["packed"].shape == (4, 4, 128, 128)
            assert batch_fingerprint(values) == entry["batch_fingerprint"]
            batches.append({key: value.cuda() for key, value in values.items()})
        models, optimizers = {}, {}
        for name in plan["arms"]:
            torch.manual_seed(plan["seed"])
            model = JointDemosaic(ModelConfig(**plan["model_config"])).cpu()
            assert not model.config.dino and len(list(model.parameters())) == 852
            assert digest(model.state_dict().items()) == plan["common_initial_model_SHA256"]
            models[name] = model.cuda()
            optimizers[name] = make_optimizer(model, {"lr": plan["lr"]})

        @torch.inference_mode()
        def evaluate(round_index):
            arms = {}
            for name, model in models.items():
                model.eval()
                cases = []
                for entry, batch in zip(fixtures, batches, strict=True):
                    with coordinates(model, plan["arms"][name]["coordinates"], batch):
                        prediction, loss = loss_for(model, batch, entry["domain"])
                    assert torch.isfinite(prediction).all() and torch.isfinite(loss)
                    if round_index == 0:
                        assert torch.equal(prediction, bilinear(batch["packed"], batch["colors"]))
                    cases.append(
                        {
                            "production_step": entry["production_step"],
                            "domain": entry["domain"],
                            "loss": loss.item(),
                            "MSE": mse(prediction, batch, entry["domain"]),
                        }
                    )
                arms[name] = {
                    "optimizer_updates": round_index
                    * (4 if plan["arms"][name]["batch"] == 4 else 1),
                    "cases": cases,
                    "domain_means": {
                        domain: {
                            metric: math.fsum(
                                row[metric] for row in cases if row["domain"] == domain
                            )
                            / sum(row["domain"] == domain for row in cases)
                            for metric in ["loss", "MSE"]
                        }
                        for domain in ["commons", "native", "paired"]
                    },
                }
            return {"round": round_index, "example_draws_per_arm": round_index * 16, "arms": arms}

        with amp_context("cuda", dtype="float32"):
            curves = [evaluate(0)]
            common = next(iter(curves[0]["arms"].values()))["cases"]
            assert all(row["cases"] == common for row in curves[0]["arms"].values())
            (root / "curves.json").write_text(json.dumps(curves, indent=2) + "\n")
            record(
                "running-equal-example-CUDA-batch-learning",
                completed_rounds=0,
                all16_initial_outputs_equal_bilinear=True,
                common_initial_model_SHA256=plan["common_initial_model_SHA256"],
                GPU=torch.cuda.get_device_name(),
                torch=str(torch.__version__),
            )
            with (root / "training.jsonl").open("x") as log:
                for round_index in range(1, plan["rounds"] + 1):
                    indices = [((round_index - 1) * 4 + offset) % 16 for offset in range(4)]
                    assert psutil.virtual_memory().available > 16 * 2**30
                    for name, model in models.items():
                        model.train()
                        optimizer = optimizers[name]
                        arm = plan["arms"][name]
                        groups = [[index] for index in indices] if arm["batch"] == 4 else [indices]
                        assert arm["batch"] in [4, 16]
                        for offset, group in enumerate(groups):
                            optimizer.zero_grad(set_to_none=True)
                            # Only raw/gain32 are permitted here: these transforms
                            # do not read per-example noise coefficients from batch.
                            assert arm["coordinates"] in ["raw", "gain32-residual32"]
                            with coordinates(model, arm["coordinates"], batches[group[0]]):
                                loss = grouped_loss(
                                    model,
                                    [batches[i] for i in group],
                                    [fixtures[i]["domain"] for i in group],
                                )
                            assert torch.isfinite(loss)
                            loss.backward()
                            assert all(
                                parameter.grad is not None for parameter in model.parameters()
                            )
                            norm = torch.nn.utils.clip_grad_norm_(
                                model.parameters(), 1, error_if_nonfinite=True
                            )
                            optimizer.step()
                            log.write(
                                json.dumps(
                                    {
                                        "round": round_index,
                                        "arm": name,
                                        "optimizer_update": (round_index - 1) * len(groups)
                                        + offset
                                        + 1,
                                        "example_draws_after_update": (
                                            (round_index - 1) * 4
                                            + sum(len(g) for g in groups[: offset + 1])
                                        )
                                        * 4,
                                        "production_steps": [
                                            fixtures[i]["production_step"] for i in group
                                        ],
                                        "domains": [fixtures[i]["domain"] for i in group],
                                        "loss": loss.item(),
                                        "gradient_norm": norm.item(),
                                    },
                                    allow_nan=False,
                                )
                                + "\n"
                            )
                    if round_index % 16 == 0:
                        log.flush()
                        record(
                            "running-equal-example-CUDA-batch-learning",
                            completed_rounds=round_index,
                            example_draws_per_arm=round_index * 16,
                        )
                    if round_index in plan["evaluation_rounds"]:
                        curves.append(evaluate(round_index))
                        (root / "curves.json").write_text(json.dumps(curves, indent=2) + "\n")
        states = {}
        for name, model in models.items():
            updates = plan["rounds"] * (4 if plan["arms"][name]["batch"] == 4 else 1)
            optimizer = optimizers[name]
            assert len(optimizer.state) == 852
            assert all(int(state["step"]) == updates for state in optimizer.state.values())
            assert all(torch.isfinite(value).all() for value in model.state_dict().values())
            assert all(
                torch.isfinite(value).all()
                for state in optimizer.state.values()
                for value in state.values()
            )
            states[name] = {
                "final_model_SHA256": digest(model.state_dict().items()),
                "all852_Adam_states_finite_at_update": updates,
                "learned_weights_discarded": True,
            }
        assert all(
            batch_fingerprint({key: value.cpu() for key, value in batch.items()})
            == entry["batch_fingerprint"]
            for batch, entry in zip(batches, fixtures, strict=True)
        )
        guard(plan)
        result = {
            "status": "completed-discarded-equal-example-CUDA-batch-learning",
            "plan": ref(plan_path),
            "curves": ref(root / "curves.json"),
            "training_log": ref(root / "training.jsonl"),
            "states": states,
            "example_draws_per_arm": plan["rounds"] * 16,
            "common_initial_model_SHA256": plan["common_initial_model_SHA256"],
            "all16_initial_outputs_equal_bilinear": True,
            "scope": plan["scope"],
        }
        (root / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        record(result["status"], result=ref(root / "receipt.json"))
    except BaseException as error:
        record("failed-no-automatic-restart-no-learned-weights-exported", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
