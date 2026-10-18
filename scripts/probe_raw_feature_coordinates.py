"""CPU-only fresh-model optimization diagnosis; never export learned weights."""

import argparse
import hashlib
import json
import os
import random
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import psutil
import torch

from demosaic import packed_isotropic
from demosaic.cfa import bilinear
from demosaic.losses import reconstruction_loss
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.paired_training import paired_reconstruction_loss
from demosaic.precision import ieee_fp32
from demosaic.train import batch_fingerprint, make_optimizer


def coordinate_map(packed, shot, read, mode):
    """Change only input coordinates; original RAW skip/output units stay fixed.

    The compander is the rationalized integral of inverse noise standard
    deviation, normalized at sensor values0 and1, with linear continuation below
    zero. Its coefficients are supplied shot/read parameters, never image stats.
    Gaussian-only/ADC-only observations retain their original coordinates.
    """
    with torch.autocast(packed.device.type, enabled=False), ieee_fp32():
        packed = packed.float()
        if mode == "raw":
            return packed
        if mode == "gain32":
            return packed * 32
        if mode != "noise-compand":
            raise ValueError("Unknown feature coordinate mode")
        shot = torch.as_tensor(shot, dtype=torch.float32, device=packed.device)
        read = torch.as_tensor(read, dtype=torch.float32, device=packed.device)
        offset = (read + 0.375 * shot.square()).clamp_min(1e-12)
        origin = offset.sqrt()
        scale = (shot + offset).sqrt() + origin
        positive = (shot * packed.clamp_min(0) + offset).sqrt() + origin
        denominator = torch.where(packed >= 0, positive, 2 * origin)
        mapped = packed * (scale / denominator)
        return torch.where(shot == 0, packed, mapped)


@contextmanager
def feature_mode(mode, batch):
    """Isolated process-local prototype; leave production modules/config intact."""
    original = packed_isotropic.physical_features

    def features(packed, variance, colors, wb=None, matrix=None):
        legacy = original(packed, variance, colors, wb, matrix)
        mapped = coordinate_map(packed, batch["shot"], batch["read"], mode)
        return torch.cat((mapped, legacy[:, 4:]), 1)

    packed_isotropic.physical_features = features
    try:
        yield
    finally:
        packed_isotropic.physical_features = original


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(path), "sha256": sha(path)}


def digest(items):
    value = hashlib.sha256()
    for name, tensor in items:
        value.update(name.encode())
        value.update(tensor.detach().contiguous().numpy().tobytes())
    return value.hexdigest()


def alive(owner):
    try:
        process = psutil.Process(owner["pid"])
        return (
            process.create_time() == owner["created"] and process.status() != psutil.STATUS_ZOMBIE
        )
    except psutil.NoSuchProcess:
        return False


def guard(plan):
    for path, expected in {**plan["inputs"], **plan["guards"]}.items():
        assert sha(path) == expected, path


def loss_for(model, batch, domain):
    prediction, auxiliary = model(
        *(batch[key] for key in ["packed", "variance", "colors", "wb", "matrix"]), auxiliary=True
    )
    if domain == "paired":
        loss, _ = paired_reconstruction_loss(prediction, batch, auxiliary)
    else:
        loss, _ = reconstruction_loss(prediction, batch, auxiliary, physical_fp32=True)
    return prediction, loss


def mse(prediction, batch, domain):
    if domain == "paired":
        mask = batch["sensor_mask"].bool()
        error = (prediction - batch["sensor_reference"]).square()
        return float(error.masked_fill(~mask, 0).sum() / mask.sum().clamp_min(1))
    return float((prediction - batch["target"]).square().mean())


def run(plan_path):
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), "Hide CUDA"
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    status = Path(plan["status"])
    assert not status.exists()
    with (root / "launch.claim").open("x") as stream:
        stream.write(str(os.getpid()) + "\n")
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "CUDA_initialized": False,
        "completed_updates_per_arm": 0,
    }

    def record(state, **fields):
        info.update(status=state, updated_unix=time.time(), **fields)
        temp = status.with_suffix(".tmp")
        temp.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n")
        temp.replace(status)
        print(json.dumps({"status": state, **fields}), flush=True)

    def yield_for_reviews():
        # Use at most two CPU threads during training. Give owned inference /
        # timing stages the CPU too once the original training owner exits.
        if alive(plan["training_owner"]):
            return
        waiting = False
        while True:
            active = []
            for entry in plan["review_and_timing_owners"]:
                if alive(entry["owner"]):
                    active.append(entry["owner"])
                else:
                    current = read(entry["workflow"])
                    if (
                        current["controller"] == entry["owner"]
                        and current.get("child")
                        and alive(current["child"])
                    ):
                        active.append(current["child"])
            if not active:
                break
            if not waiting:
                record("waiting-for-owned-review-and-timing-owners-no-CPU-compute", active=active)
                waiting = True
            time.sleep(15)
        if waiting:
            record("resuming-discarded-CPU-diagnosis-after-owned-reviews")

    try:
        record("loading-fixed-training-only-arrays-no-CUDA")
        fixtures = read(plan["fixtures"]["path"])
        assert len(fixtures) == 16
        batches = []
        for entry in fixtures:
            assert ref(entry["fixture"]["path"]) == entry["fixture"]
            with np.load(entry["fixture"]["path"], allow_pickle=False) as arrays:
                batch = {key: torch.from_numpy(arrays[key].copy()) for key in arrays.files}
            assert batch_fingerprint(batch) == entry["batch_fingerprint"]
            assert batch["packed"].shape == (4, 4, 128, 128)
            assert all(s.get("split", "train") == "train" for s in entry["sources"])
            batches.append(batch)
        models, optimizers, initial = {}, {}, {}
        rng_digest = None
        for mode in plan["modes"]:
            torch.manual_seed(plan["seed"])
            random.seed(plan["seed"])
            model = JointDemosaic(ModelConfig(**plan["model_config"])).cpu()
            assert not model.config.dino and len(list(model.parameters())) == 852
            models[mode] = model
            optimizers[mode] = make_optimizer(model, {"lr": plan["lr"]})
            initial[mode] = digest(model.state_dict().items())
            value = hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest()
            rng_digest = value if rng_digest is None else rng_digest
            assert value == rng_digest
        assert len(set(initial.values())) == 1

        @torch.inference_mode()
        def evaluate(update):
            result = {}
            for mode, model in models.items():
                model.eval()
                rows = []
                for entry, batch in zip(fixtures, batches, strict=True):
                    yield_for_reviews()
                    with feature_mode(mode, batch):
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
                means = {
                    domain: {
                        key: float(np.mean([r[key] for r in rows if r["domain"] == domain]))
                        for key in ["loss", "MSE"]
                    }
                    for domain in ["commons", "native", "paired"]
                }
                result[mode] = {"cases": rows, "domain_means": means}
            return {"update": update, "arms": result}

        curves = [evaluate(0)]
        (root / "curves.json").write_text(json.dumps(curves, indent=2, allow_nan=False) + "\n")
        record(
            "running-fresh-CPU-coordinate-diagnosis",
            initial_model_SHA256=initial,
            initial_RNG_sha256=rng_digest,
            all16_initial_outputs_equal_bilinear=True,
        )
        with (root / "training.jsonl").open("x") as log:
            for update in range(1, plan["updates"] + 1):
                index = (update - 1) % 16
                entry, batch = fixtures[index], batches[index]
                for mode in plan["modes"]:
                    yield_for_reviews()
                    assert psutil.virtual_memory().available > 16 * 2**30
                    model, optimizer = models[mode], optimizers[mode]
                    model.train()
                    optimizer.zero_grad(set_to_none=True)
                    with feature_mode(mode, batch):
                        _, loss = loss_for(model, batch, entry["domain"])
                    assert torch.isfinite(loss)
                    with ieee_fp32():
                        loss.backward()
                        assert all(
                            p.grad is not None and torch.isfinite(p.grad).all()
                            for p in model.parameters()
                        )
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
                                "loss": float(loss),
                                "gradient_norm": float(norm),
                            },
                            allow_nan=False,
                        )
                        + "\n"
                    )
                info["completed_updates_per_arm"] = update
                if update % 16 == 0:
                    log.flush()
                    record(
                        "running-fresh-CPU-coordinate-diagnosis", completed_updates_per_arm=update
                    )
                if update in plan["evaluation_updates"]:
                    curves.append(evaluate(update))
                    (root / "curves.json").write_text(
                        json.dumps(curves, indent=2, allow_nan=False) + "\n"
                    )
        states = {}
        for mode, model in models.items():
            optimizer = optimizers[mode]
            assert all(torch.isfinite(v).all() for v in model.state_dict().values())
            assert len(optimizer.state) == 852
            assert all(int(v["step"]) == plan["updates"] for v in optimizer.state.values())
            assert all(
                torch.isfinite(t).all() for v in optimizer.state.values() for t in v.values()
            )
            states[mode] = {
                "final_model_SHA256": digest(model.state_dict().items()),
                "finite_model_and852_Adam_states": True,
                "Adam_steps": plan["updates"],
                "learned_weights_discarded": True,
            }
        assert all(
            batch_fingerprint(b) == f["batch_fingerprint"]
            for b, f in zip(batches, fixtures, strict=True)
        )
        guard(plan)
        result = {
            "status": "completed-discarded-fresh-CPU-feature-coordinate-comparison",
            "plan": ref(plan_path),
            "initial_model_SHA256": initial,
            "initial_RNG_sha256": rng_digest,
            "all16_initial_outputs_equal_bilinear": True,
            "curves": ref(root / "curves.json"),
            "training_log": ref(root / "training.jsonl"),
            "states": states,
            "CUDA_initialized": torch.cuda.is_initialized(),
            "scope": plan["scope"],
        }
        assert not result["CUDA_initialized"]
        (root / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        record(result["status"], result=ref(root / "receipt.json"))
    except BaseException as error:
        record("failed-no-automatic-restart-no-learned-weights-exported", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
