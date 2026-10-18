"""Discarded fresh-model CUDA comparison of RAW/residual optimization units."""

import argparse
import hashlib
import json
import math
import os
import random
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import psutil
import torch
from probe_raw_feature_coordinates import (
    alive,
    batch_fingerprint,
    feature_mode,
    guard,
    loss_for,
    mse,
    read,
    ref,
)

from demosaic.cfa import bilinear
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.precision import amp_context
from demosaic.train import make_optimizer


@contextmanager
def residual_units(model, scale):
    """Scale only the learned FP32 residual; keep the physical signal skip fixed."""
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("Residual scale must be finite and positive")
    if model.config.restoration_backbone != "packed-isotropic":
        raise ValueError("This diagnostic requires the packed isotropic backbone")

    def scaled_head(module, args, output):
        if output.dtype != torch.float32:
            raise ValueError("Physical residual must remain FP32")
        return output * scale

    handle = model.packed_isotropic.head.register_forward_hook(scaled_head)
    try:
        yield
    finally:
        handle.remove()


@contextmanager
def coordinates(model, mode, batch):
    feature = "gain32" if mode == "gain32-residual32" else mode
    scale = 1 / 32 if mode == "gain32-residual32" else 1
    with feature_mode(feature, batch), residual_units(model, scale):
        yield


def digest(items):
    value = hashlib.sha256()
    for name, tensor in items:
        value.update(name.encode())
        value.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return value.hexdigest()


def run(plan_path):
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read(plan_path)
    guard(plan)
    for workflow in plan["completed_GPU_workflows"]:
        state = read(workflow["path"])
        assert state["status"] == workflow["terminal_status"]
        assert not alive(state["controller"])
        assert not state.get("child") or not alive(state["child"])
    assert torch.cuda.is_available()
    root, status = Path(plan["root"]), Path(plan["status"])
    assert not status.exists()
    with (root / "launch.claim").open("x") as stream:
        stream.write(str(os.getpid()) + "\n")
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed_updates_per_arm": 0,
    }

    def record(state, **fields):
        info.update(status=state, updated_unix=time.time(), **fields)
        temporary = status.with_suffix(".tmp")
        temporary.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n")
        temporary.replace(status)
        print(json.dumps({"status": state, **fields}), flush=True)

    try:
        record("loading-training-only-fixtures-for-discarded-CUDA-unit-comparison")
        fixtures = read(plan["fixtures"]["path"])
        assert len(fixtures) == 16
        batches = []
        for entry in fixtures:
            assert ref(entry["fixture"]["path"]) == entry["fixture"]
            with np.load(entry["fixture"]["path"], allow_pickle=False) as arrays:
                values = {key: torch.from_numpy(arrays[key].copy()) for key in arrays.files}
            assert batch_fingerprint(values) == entry["batch_fingerprint"]
            assert all(source.get("split", "train") == "train" for source in entry["sources"])
            assert values["packed"].shape == (4, 4, 128, 128)
            batches.append({key: value.cuda() for key, value in values.items()})
        models, optimizers, initial = {}, {}, {}
        for mode in plan["modes"]:
            torch.manual_seed(plan["seed"])
            random.seed(plan["seed"])
            model = JointDemosaic(ModelConfig(**plan["model_config"])).cpu()
            assert not model.config.dino and len(list(model.parameters())) == 852
            initial[mode] = digest(model.state_dict().items())
            assert initial[mode] == plan["common_initial_model_SHA256"]
            models[mode] = model.cuda()
            optimizers[mode] = make_optimizer(model, {"lr": plan["lr"]})
        assert len(set(initial.values())) == 1

        @torch.inference_mode()
        def evaluate(update):
            result = {}
            for mode, model in models.items():
                model.eval()
                rows = []
                for entry, batch in zip(fixtures, batches, strict=True):
                    with coordinates(model, mode, batch):
                        prediction, loss = loss_for(model, batch, entry["domain"])
                    assert torch.isfinite(prediction).all() and torch.isfinite(loss)
                    if update == 0:
                        assert torch.equal(prediction, bilinear(batch["packed"], batch["colors"]))
                    rows.append(
                        {
                            "production_step": entry["production_step"],
                            "domain": entry["domain"],
                            "loss": loss.item(),
                            "MSE": mse(prediction, batch, entry["domain"]),
                        }
                    )
                result[mode] = {
                    "cases": rows,
                    "domain_means": {
                        domain: {
                            metric: math.fsum(r[metric] for r in rows if r["domain"] == domain)
                            / sum(r["domain"] == domain for r in rows)
                            for metric in ["loss", "MSE"]
                        }
                        for domain in ["commons", "native", "paired"]
                    },
                }
            return {"update": update, "arms": result}

        with amp_context("cuda", dtype="float32"):
            curves = [evaluate(0)]
            assert all(
                arm["cases"] == curves[0]["arms"]["raw"]["cases"]
                for arm in curves[0]["arms"].values()
            )
            (root / "curves.json").write_text(json.dumps(curves, indent=2) + "\n")
            record(
                "running-four-fresh-CUDA-IEEE-FP32-coordinate-arms",
                common_initial_model_SHA256=initial,
                all16_initial_outputs_equal_bilinear=True,
                CUDA_initialized=torch.cuda.is_initialized(),
                GPU=torch.cuda.get_device_name(),
                torch=str(torch.__version__),
            )
            with (root / "training.jsonl").open("x") as log:
                for update in range(1, plan["updates"] + 1):
                    entry, batch = fixtures[(update - 1) % 16], batches[(update - 1) % 16]
                    assert psutil.virtual_memory().available > 16 * 2**30
                    for mode, model in models.items():
                        model.train()
                        optimizer = optimizers[mode]
                        optimizer.zero_grad(set_to_none=True)
                        with coordinates(model, mode, batch):
                            _, loss = loss_for(model, batch, entry["domain"])
                        assert torch.isfinite(loss)
                        loss.backward()
                        assert all(parameter.grad is not None for parameter in model.parameters())
                        norm = torch.nn.utils.clip_grad_norm_(
                            model.parameters(), 1, error_if_nonfinite=True
                        )
                        optimizer.step()
                        log.write(
                            json.dumps(
                                {
                                    "update": update,
                                    "mode": mode,
                                    "production_step": entry["production_step"],
                                    "domain": entry["domain"],
                                    "loss": loss.item(),
                                    "gradient_norm": norm.item(),
                                },
                                allow_nan=False,
                            )
                            + "\n"
                        )
                    info["completed_updates_per_arm"] = update
                    if update % 16 == 0:
                        log.flush()
                        record("running-four-fresh-CUDA-IEEE-FP32-coordinate-arms")
                    if update in plan["evaluation_updates"]:
                        curves.append(evaluate(update))
                        (root / "curves.json").write_text(json.dumps(curves, indent=2) + "\n")
        states = {}
        for mode, model in models.items():
            assert all(torch.isfinite(value).all() for value in model.state_dict().values())
            optimizer = optimizers[mode]
            assert len(optimizer.state) == 852
            assert all(int(state["step"]) == plan["updates"] for state in optimizer.state.values())
            assert all(
                torch.isfinite(value).all()
                for state in optimizer.state.values()
                for value in state.values()
            )
            states[mode] = {
                "final_model_SHA256": digest(model.state_dict().items()),
                "all852_Adam_states_finite_and_at256": True,
                "learned_weights_discarded": True,
            }
        assert all(
            batch_fingerprint({k: v.cpu() for k, v in batch.items()}) == entry["batch_fingerprint"]
            for batch, entry in zip(batches, fixtures, strict=True)
        )
        guard(plan)
        result = {
            "status": "completed-discarded-four-arm-CUDA-raw-residual-unit-comparison",
            "plan": ref(plan_path),
            "curves": ref(root / "curves.json"),
            "training_log": ref(root / "training.jsonl"),
            "initial_model_SHA256": initial,
            "all16_initial_outputs_equal_bilinear": True,
            "states": states,
            "scope": plan["scope"],
        }
        (root / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        record(result["status"], result=ref(root / "receipt.json"))
    except BaseException as error:
        record("failed-no-automatic-restart-no-diagnostic-weights-exported", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
