"""Discarded CUDA execution sweep for the same mixed optimizer batch16."""

import argparse
import gc
import json
import os
import statistics
import time
from pathlib import Path

import numpy as np
import psutil
import torch
from probe_raw_feature_coordinates import alive, batch_fingerprint, guard, read, ref
from probe_raw_residual_units import digest

from demosaic.cfa import bilinear
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.optimizer_batches import backward_groups
from demosaic.precision import amp_context
from demosaic.train import make_optimizer


def run(plan_path):
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.backends.cudnn.benchmark = True
    plan = read(plan_path)
    guard(plan)
    for entry in plan["completed_workflows"]:
        state = read(entry["path"])
        assert state["status"] == entry["terminal_status"] and not alive(state["controller"])
    assert torch.cuda.is_available() and psutil.virtual_memory().available > 40 * 2**30
    root, status = Path(plan["root"]), Path(plan["status"])
    assert not status.exists()
    with (root / "launch.claim").open("x") as stream:
        stream.write(str(os.getpid()) + "\n")
    info = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
    }

    def record(stage, **fields):
        info.update(status=stage, updated_unix=time.time(), **fields)
        temporary = status.with_suffix(".tmp")
        temporary.write_text(json.dumps(info, indent=2, allow_nan=False) + "\n")
        temporary.replace(status)
        print(json.dumps(info), flush=True)

    try:
        record("loading-frozen-training-fixtures-for-mixed-execution-sweep")
        fixtures = read(plan["fixtures"]["path"])
        assert len(fixtures) == 16
        batches = []
        for entry in fixtures:
            assert ref(entry["fixture"]["path"]) == entry["fixture"]
            with np.load(entry["fixture"]["path"], allow_pickle=False) as arrays:
                values = {key: torch.from_numpy(arrays[key].copy()) for key in arrays.files}
            assert batch_fingerprint(values) == entry["batch_fingerprint"]
            assert values["packed"].shape == (4, 4, 128, 128)
            batches.append({key: value.cuda() for key, value in values.items()})
        points = []
        for enabled in (False, True):
            arm = "dino" if enabled else "no-dino"
            for forward in plan["forward_group_order"]:
                assert psutil.virtual_memory().available > 40 * 2**30
                torch.manual_seed(51)
                options = {
                    **plan["model_config"],
                    "dino": enabled,
                    "dino_feature_fusion": "packed-convnext" if enabled else "bottleneck",
                }
                model = JointDemosaic(ModelConfig(**options))
                initial = digest(
                    ("packed_isotropic." + key, value)
                    for key, value in model.packed_isotropic.state_dict().items()
                )
                assert initial == plan["initial_RAW_state_SHA256"]
                model = model.cuda().to(memory_format=torch.channels_last)
                optimizer = make_optimizer(model, {"lr": 2e-4})
                backbone = digest(model.context.backbone.state_dict().items()) if enabled else None
                if enabled:
                    assert backbone == plan["official_frozen_DINO_SHA256"]
                count = 863 if enabled else 852
                assert sum(p.requires_grad for p in model.parameters()) == count
                model.eval()
                with torch.inference_mode(), amp_context("cuda", dtype="float32"):
                    for batch in batches:
                        actual = model(
                            *(batch[k] for k in ["packed", "variance", "colors", "wb", "matrix"])
                        )
                        assert torch.equal(actual, bilinear(batch["packed"], batch["colors"]))
                config = {
                    "optimizer_batch_groups": 4,
                    "optimizer_forward_groups": forward,
                    "data_seed_per_step": True,
                    "amp": True,
                    "precision": "float32",
                    "model": options,
                }
                record("timing-mixed-optimizer-batch16", arm=arm, forward_groups=forward)
                times, losses = [], []
                with amp_context("cuda", dtype="float32"):
                    for update in range(plan["warmup_updates"] + plan["timed_updates"]):
                        indices = [(update * 4 + offset) % 16 for offset in range(4)]
                        selected = [(i + 1, fixtures[i]["domain"], batches[i]) for i in indices]
                        assert psutil.virtual_memory().available > 16 * 2**30
                        torch.cuda.synchronize()
                        if update == plan["warmup_updates"]:
                            torch.cuda.reset_peak_memory_stats()
                        started = time.perf_counter()
                        model.train()
                        optimizer.zero_grad(set_to_none=True)
                        loss, _, norm, _ = backward_groups(
                            model, selected, lambda step, domain, batch: batch, config
                        )
                        optimizer.step()
                        torch.cuda.synchronize()
                        elapsed = time.perf_counter() - started
                        assert torch.isfinite(loss) and torch.isfinite(norm)
                        if update >= plan["warmup_updates"]:
                            times.append(elapsed)
                            losses.append(loss.item())
                peak_allocated = torch.cuda.max_memory_allocated() / 2**30
                peak_reserved = torch.cuda.max_memory_reserved() / 2**30
                assert len(optimizer.state) == count
                expected_step = plan["warmup_updates"] + plan["timed_updates"]
                assert all(
                    int(state["step"]) == expected_step for state in optimizer.state.values()
                )
                assert all(torch.isfinite(value).all() for value in model.state_dict().values())
                assert all(
                    torch.isfinite(value).all()
                    for state in optimizer.state.values()
                    for value in state.values()
                )
                assert all(
                    p.grad is not None and torch.isfinite(p.grad).all()
                    for p in model.parameters()
                    if p.requires_grad
                )
                if enabled:
                    assert backbone == digest(model.context.backbone.state_dict().items())
                    assert all(
                        not p.requires_grad and p.grad is None
                        for p in model.context.backbone.parameters()
                    )
                point = {
                    "arm": arm,
                    "forward_groups": forward,
                    "physical_forward_batch": forward * 4,
                    "effective_batch": 16,
                    "timed_update_seconds": times,
                    "timed_losses": losses,
                    "median_update_seconds": statistics.median(times),
                    "range_seconds": [min(times), max(times)],
                    "examples_per_second": 16 * len(times) / sum(times),
                    "peak_allocated_GiB": peak_allocated,
                    "peak_reserved_GiB": peak_reserved,
                    "initial_RAW_state_SHA256": initial,
                    "DINO_SHA256": backbone,
                    "finite_model_gradient_optimizer_states": count,
                    "Adam_steps": expected_step,
                    "learned_weights_discarded": True,
                }
                points.append(point)
                (root / "points.json").write_text(json.dumps(points, indent=2) + "\n")
                del model, optimizer, actual, loss, norm
                gc.collect()
                torch.cuda.empty_cache()
        combined = {
            forward: sum(
                sum(p["timed_update_seconds"]) for p in points if p["forward_groups"] == forward
            )
            for forward in plan["forward_group_order"]
        }
        winner = min(combined, key=combined.get)
        assert all(
            batch_fingerprint({key: value.cpu() for key, value in batch.items()})
            == entry["batch_fingerprint"]
            for batch, entry in zip(batches, fixtures, strict=True)
        )
        guard(plan)
        result = {
            "status": "completed-discarded-mixed-batch-execution-sweep",
            "plan": ref(plan_path),
            "points": points,
            "combined_timed_seconds": combined,
            "fastest_observed_common_forward_groups": winner,
            "all_fixture_fingerprints_unchanged": True,
            "GPU": torch.cuda.get_device_name(),
            "torch": str(torch.__version__),
            "scope": plan["scope"],
        }
        (root / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
        record(result["status"], result=ref(root / "receipt.json"))
    except BaseException as error:
        record("failed-no-automatic-restart-no-weights-exported", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
