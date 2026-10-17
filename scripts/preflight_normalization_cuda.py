"""Discarded genuine-parent B16/native256 BF16 normalization-augmentation checks."""

import argparse
import gc
import hashlib
import json
import math
import os
import random
import shutil
from pathlib import Path

import psutil
import torch
import yaml
from audit_flat_palette import train_rows
from preflight_dino_pyramid_cuda import assert_saved_equal
from preflight_flat_palette_cuda import portable_predictions
from profile_raw_kernel_inference import model_hash

import demosaic.train as training
from demosaic.cfa import PATTERNS, color_indices
from demosaic.pretrained_rgb import physical_rgb_features
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).resolve()), "sha256": sha(path)}


def physical_probe():
    """Check CUDA coordinates against CPU and preserve the zero-mask path exactly."""
    generator = torch.Generator().manual_seed(42)
    cpu = [
        torch.rand(4, 4, 16, 24, generator=generator),
        torch.ones(4, 4, 16, 24),
        torch.stack([color_indices(pattern) for pattern in PATTERNS]),
        torch.tensor([[1.4, 1, 2.1]]).expand(4, -1),
    ]
    rgb = torch.randn(4, 3, 32, 48, generator=generator) * 3
    mask = torch.tensor([False, True, False, True])
    expected = physical_rgb_features(*cpu, rgb=rgb, stabilized=True, normalization_mask=mask)
    gpu = [x.cuda() for x in cpu]
    canvas = rgb.cuda()
    rng = torch.cuda.get_rng_state().clone()
    plain = physical_rgb_features(*gpu, rgb=canvas, stabilized=True)
    zero = physical_rgb_features(
        *gpu,
        rgb=canvas,
        stabilized=True,
        normalization_mask=torch.zeros(4, dtype=torch.bool, device="cuda"),
    )
    selected = physical_rgb_features(
        *gpu, rgb=canvas, stabilized=True, normalization_mask=mask.cuda()
    )
    maximum = 0.0
    for baseline, noop, actual, oracle in zip(plain, zero, selected, expected, strict=True):
        assert torch.equal(baseline, noop)
        torch.testing.assert_close(actual.cpu(), oracle, atol=3e-6, rtol=3e-6)
        maximum = max(maximum, float((actual.cpu() - oracle).abs().max()))
    assert torch.equal(rng, torch.cuda.get_rng_state())
    assert torch.equal(gpu[0].cpu(), cpu[0]) and torch.equal(canvas.cpu(), rgb)
    return {
        "all4_CFAs_mixed_mask_CPU_oracle_max_abs_difference": maximum,
        "CPU_oracle_atol_rtol": [3e-6, 3e-6],
        "CUDA_noop_bitwise_exact": True,
        "CUDA_RNG_RAW_and_canvas_unchanged": True,
    }


def finite_state(path, parent):
    state = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == 6 and state["config"]["steps"] == 4000
    assert len(state["model"]) == len(state["ema"]) == 91
    assert len(state["optimizer"]["state"]) == 89
    for field in ["model", "ema"]:
        assert all(torch.isfinite(value).all() for value in state[field].values())
    for item in state["optimizer"]["state"].values():
        assert int(item["step"]) == 6
        assert all(torch.isfinite(v).all() for v in item.values() if isinstance(v, torch.Tensor))
    assert all(key in state for key in ["python_rng", "torch_rng", "cuda_rng"])
    assert len(state["cuda_rng"]) == 1
    changed = {}
    for field in ["model", "ema"]:
        changed[field] = sum(not torch.equal(v, parent["ema"][k]) for k, v in state[field].items())
        assert changed[field] == 89
    return state, changed


def main(config_path, parent_path, review_path, review_sha256, output):
    os.nice(5)
    torch.set_num_threads(4)
    assert not torch.cuda.is_initialized()
    assert psutil.virtual_memory().available / 2**30 > 32
    assert shutil.disk_usage("/mnt/external").free / 2**30 > 512
    assert sha(review_path) == review_sha256
    review = json.loads(Path(review_path).read_text())
    assert review["review_complete"] is True
    assert review["manual_native_review"]["result"]["actually_viewed_original_images"] == 58
    for label in ["primary_terminal", "supplementary_audit_recovery"]:
        owner = (
            json.loads(Path(review[label]["path"]).read_text())["controller"]
            if label == "primary_terminal"
            else json.loads(
                Path(review[label]["original_failed_workflow_unchanged"]["path"]).read_text()
            )["controller"]
        )
        try:
            assert psutil.Process(owner["pid"]).create_time() != owner["created"]
        except psutil.NoSuchProcess:
            pass
    assert torch.cuda.is_available()
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    cfg = yaml.safe_load(Path(config_path).read_text())
    assert (cfg["batch_size"], cfg["patch_size"], cfg["precision"]) == (16, 256, "bfloat16")
    assert (
        cfg["steps"],
        cfg["seed"],
        cfg["workers"],
        cfg["paired_workers"],
        cfg["raw_clean_workers"],
    ) == (4000, 50, 4, 2, 2)
    assert cfg["normalization_augmentation"] == "none"
    inputs = [config_path, parent_path, review_path, Path(cfg["validation_protocol"])]
    inputs += [
        Path(cfg[key])
        for key in ["manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"]
    ]
    sources = {str(p.resolve()): sha(p) for p in Path("src/demosaic").glob("*.py")}
    helpers = {str(p.resolve()): sha(p) for p in Path("scripts").glob("*.py")}
    (output / "helpers").mkdir()
    for path in helpers:
        shutil.copyfile(path, output / "helpers" / Path(path).name)
    plan = {
        "inputs": [ref(p) for p in inputs],
        "source_files": sources,
        "helper_files": helpers,
        "operator": ref(__file__),
        "template": cfg,
        "scope": "Six discarded updates each in control/augmented/3+3 resumed arms. Genuine V63original20k EMA, fresh AdamW, B16/native256/BF16/workers4+2+2 and actual data. Exact pre-fetch model/optimizer/RNG and pre-update EMA restoration. No quality, throughput or deterministic CUDA optimization claim.",
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    shutil.copyfile(__file__, output / "operator-source.py")
    torch.cuda.reset_peak_memory_stats()
    physical = physical_probe()
    parent = torch.load(parent_path, map_location="cpu", weights_only=True, mmap=True)
    assert parent["step"] == 20000 and len(parent["ema"]) == 91
    constructor, make_optimizer = training.JointDemosaic, training.make_optimizer
    selected_batches, update_ema = training.selected_batches, training.update_ema
    current, expected, starts, gradients = {}, {}, [], []

    def instrument(config):
        model = constructor(config)
        current["model"] = model
        return model

    def optimizer_for(model, config):
        optimizer = make_optimizer(model, config)
        current["optimizer"] = optimizer

        def before_step(optimizer, args, kwargs):
            active = [p for p in model.parameters() if p.requires_grad]
            assert len(active) == 89
            assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in active)
            assert all(
                not p.requires_grad and p.grad is None for p in model.context.backbone.parameters()
            )
            gradients.append({"leg": expected["leg"], "finite_gradient_tensors": len(active)})

        optimizer.register_step_pre_hook(before_step)
        return optimizer

    def before_fetch(*args, **kwargs):
        model, optimizer = current["model"], current["optimizer"]
        assert_saved_equal(expected["state"]["model"], model.restoration_state_dict(), "model")
        assert_saved_equal(expected["optimizer"], optimizer.state_dict(), "optimizer")
        if expected["resume"]:
            for key, actual in [
                ("python_rng", random.getstate()),
                ("torch_rng", torch.get_rng_state()),
                ("cuda_rng", torch.cuda.get_rng_state_all()),
            ]:
                assert_saved_equal(expected["state"][key], actual, key)
        digest = model_hash(model.context.backbone)
        assert all(
            not p.requires_grad and p.grad is None for p in model.context.backbone.parameters()
        )
        current["DINO_hash"] = digest
        current["EMA_checked"] = False
        starts.append(
            {
                "leg": expected["leg"],
                "prefetch_model_optimizer_exact": True,
                "resume_RNG_exact": expected["resume"],
                "DINO_hash": digest,
            }
        )
        yield from selected_batches(*args, **kwargs)

    def before_ema(model, ema, decay):
        if not current["EMA_checked"]:
            assert_saved_equal(expected["state"]["ema"], ema, "EMA-before-first-update")
            current["EMA_checked"] = True
        return update_ema(model, ema, decay)

    rows, checkpoints, changes, portability = {}, {}, {}, {}
    try:
        training.JointDemosaic, training.make_optimizer = instrument, optimizer_for
        training.selected_batches, training.update_ema = before_fetch, before_ema
        for label, policy, split in [
            ("control", "none", False),
            ("augmented", "center-half-mix-v1", False),
            ("augmented-resumed", "center-half-mix-v1", True),
        ]:
            fixture = {
                **cfg,
                "run": str(output / label),
                "checkpoint_every": 6,
                "log_every": 1,
                "validation_images": 1,
                "val_batches": 1,
                "min_available_gb": 24,
                "normalization_augmentation": policy,
            }
            path = output / (label + ".yaml")
            path.write_text(yaml.safe_dump(fixture))
            # AdamW groups carry the config LR even before the first scheduled update.
            probe = constructor(training.ModelConfig(**cfg["model"]))
            fresh_optimizer = make_optimizer(probe, fixture).state_dict()
            del probe
            expected.update(
                leg=label + "-initial",
                state={"model": parent["ema"], "ema": parent["ema"]},
                optimizer=fresh_optimizer,
                resume=False,
            )
            checkpoint = training.train(path, initialize=parent_path, stop_after=3 if split else 6)
            assert model_hash(current["model"].context.backbone) == current["DINO_hash"]
            assert current["EMA_checked"]
            current.clear()
            gc.collect()
            torch.cuda.empty_cache()
            if split:
                middle_path = output / "augmented-step3.pt"
                shutil.copyfile(checkpoint, middle_path)
                middle = torch.load(middle_path, map_location="cpu", weights_only=True, mmap=True)
                expected.update(
                    leg=label + "-resume", state=middle, optimizer=middle["optimizer"], resume=True
                )
                checkpoint = training.train(path, resume=middle_path, stop_after=3)
                assert model_hash(current["model"].context.backbone) == current["DINO_hash"]
                assert current["EMA_checked"]
                current.clear()
                gc.collect()
                torch.cuda.empty_cache()
            state, changes[label] = finite_state(checkpoint, parent)
            rows[label] = train_rows(output / label)
            assert [r["step"] for r in rows[label]] == list(range(1, 7))
            assert {r["domain"] for r in rows[label]} == {
                "synthetic",
                "paired-RAW",
                "native-RAW-synthetic",
            }
            assert all(
                math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"]) for r in rows[label]
            )
            if policy == "none":
                assert all("normalization_mask" not in r for r in rows[label])
            else:
                for row in rows[label]:
                    mask = training.normalization_augmentation_mask(
                        50, row["step"], 16, "cpu"
                    ).tolist()
                    assert row["normalization_mask"] == mask and 0 < sum(mask) < 16
            checkpoints[label] = ref(checkpoint)
            if label != "control":
                portability[label] = portable_predictions(checkpoint, state, fixture)
            del state
            gc.collect()
            torch.cuda.empty_cache()
    finally:
        training.JointDemosaic, training.make_optimizer = constructor, make_optimizer
        training.selected_batches, training.update_ema = selected_batches, update_ema
    assert len(gradients) == 18 and len(starts) == 4
    assert len({r["DINO_hash"] for r in starts}) == 1
    for label, values in rows.items():
        assert [r["batch_sha256"] for r in values] == [r["batch_sha256"] for r in rows["control"]]
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    assert sources == {str(p.resolve()): sha(p) for p in Path("src/demosaic").glob("*.py")}
    assert helpers == {str(p.resolve()): sha(p) for p in Path("scripts").glob("*.py")}
    result = {
        "status": "completed-genuine-V63-parent-B16-native256-BF16-normalization-preflight",
        "plan": ref(output / "plan.json"),
        "physical_GPU_check": physical,
        "prefetch_restoration_checks": starts,
        "per_update_gradient_checks": gradients,
        "finite_state_counts_each_arm": {"model": 91, "EMA": 91, "AdamW": 89},
        "changed_tensors": changes,
        "training_rows": rows,
        "checkpoints": checkpoints,
        "all6_observation_hashes_match_across_control_augmentation_and_resume": True,
        "portable_ordinary_FP16_EMA_predictions": portability,
        "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
        "production_training_started": False,
        "limits": plan["scope"],
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"receipt": str(output / "receipt.json"), "status": result["status"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--initialize", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--review-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.config, args.initialize, args.review, args.review_sha256, args.output)
