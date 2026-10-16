"""Prepare/run genuine CUDA checks only after the preceding long review exits.

Two discarded batch16/native256 BF16 updates per arm, portable EMA inference,
complete-state restoration and a third native-RAW update. This is engineering
validation, not a quality trial or proof of deterministic CUDA optimization.
"""

import argparse
import gc
import json
import random
from pathlib import Path

import psutil
import torch
import yaml
from preflight_paired_extension import sha, tensors_digest
from torch.utils.data import default_collate

from demosaic.cfa import PATTERNS, color_indices
from demosaic.data import CleanDataset, degrade
from demosaic.inference import load_checkpoint
from demosaic.losses import reconstruction_loss
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.precision import amp_context, ieee_fp32
from demosaic.pretrained_rgb import initialize_rgb_prior
from demosaic.raw_clean import RawCleanDataset, degrade_raw_clean
from demosaic.safety import writable_path
from demosaic.train import data_random_context, make_optimizer, save_checkpoint, update_ema


def guard_previous(controller_path, status_path, review_path, review_sha):
    """Do not initialize CUDA while the preceding owned workflow is live."""
    controller = json.loads(Path(controller_path).read_text())
    try:
        owner = psutil.Process(controller["pid"])
        if (
            abs(owner.create_time() - controller["created"]) < 0.01
            and owner.status() != psutil.STATUS_ZOMBIE
        ):
            raise RuntimeError(f"Preceding workflow is still live: PID{owner.pid}")
    except psutil.NoSuchProcess:
        pass
    status = json.loads(Path(status_path).read_text())
    if status["status"] != "completed-to10000-and-full-review":
        raise RuntimeError("Preceding original10000 workflow has not completed its evaluation")
    if sha(review_path) != review_sha:
        raise ValueError("Preceding published review hash differs")
    review = json.loads(Path(review_path).read_text())
    if review["workflow"]["status"] != status["status"]:
        raise ValueError("Published review does not cover the completed10000 workflow")
    return {
        "controller": controller,
        "status": status["status"],
        "review": str(review_path),
        "review_sha256": review_sha,
    }


def assert_saved_equal(expected, actual, name):
    if isinstance(expected, torch.Tensor):
        torch.testing.assert_close(expected, actual.detach().cpu(), rtol=0, atol=0, msg=name)
    elif isinstance(expected, dict):
        assert expected.keys() == actual.keys(), name
        for key, value in expected.items():
            assert_saved_equal(value, actual[key], f"{name}/{key}")
    elif isinstance(expected, (list, tuple)):
        assert type(expected) is type(actual) and len(expected) == len(actual), name
        for index, value in enumerate(expected):
            assert_saved_equal(value, actual[index], f"{name}/{index}")
    else:
        assert expected == actual, name


def prediction(model, batch, precision):
    model.set_noise(batch["shot"], batch["read"])
    with amp_context("cuda", dtype=precision):
        return model(
            batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
        )


def update(model, optimizer, ema, batch, step, pyramid):
    model.train().set_noise(batch["shot"], batch["read"])
    optimizer.zero_grad(set_to_none=True)
    with amp_context("cuda", dtype="bfloat16"):
        restored, auxiliary = model(
            batch["packed"],
            batch["variance"],
            batch["colors"],
            batch["wb"],
            batch["matrix"],
            auxiliary=True,
        )
        loss, _ = reconstruction_loss(restored, batch, auxiliary, physical_fp32=True)
    assert torch.isfinite(restored).all() and torch.isfinite(loss)
    with ieee_fp32():
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1, error_if_nonfinite=True)
    gradients = {}
    if pyramid:
        assert not model.context.backbone.training
        assert all(
            not p.requires_grad and p.grad is None for p in model.context.backbone.parameters()
        )
        for name, param in model.context.named_parameters():
            if param.requires_grad:
                assert param.grad is not None and torch.isfinite(param.grad).all()
                gradients[name] = float(param.grad.norm())
        assert all(gradients[f"gates.{i}"] > 0 for i in range(3))
        if step > 1:
            assert all(gradients[f"laterals.{i}.weight"] > 0 for i in range(4))
            assert all(gradients[f"projections.{i}.weight"] > 0 for i in range(3))
    optimizer.step()
    update_ema(model, ema, min(0.999, (1 + step) / (10 + step)))
    return {
        "step": step,
        "loss": float(loss.detach()),
        "gradient_norm": float(norm),
        "context_gradient_norms": gradients,
        "observation_sha256": tensors_digest(batch),
    }


def main(config_path, output, controller, status, review, review_sha):
    preceding = guard_previous(controller, status, review, review_sha)
    assert torch.cuda.is_available() and psutil.virtual_memory().available / 1e9 > 24
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("high")
    torch.backends.cudnn.benchmark = True
    cfg = yaml.safe_load(Path(config_path).read_text())
    assert cfg["seed"] == 48 and cfg["batch_size"] == 16 and cfg["patch_size"] == 256
    assert cfg["model"]["dino_feature_fusion"] == "convnext-pyramid"
    availability_path = Path("docs/results/dino-convnext-tiny-availability-v1.json")
    availability = json.loads(availability_path.read_text())
    assert cfg["model"]["dino_model"] == availability["repo"]
    assert cfg["model"]["dino_revision"] == availability["revision"]
    for item in availability["files"]:
        assert sha(item["path"]) == item["sha256"]
    restart_path = Path("docs/results/dino-convnext-pyramid-cpu-restart.json")
    restart = json.loads(restart_path.read_text())
    assert restart["status"] == "completed-genuine-cpu-complete-state-restart-audit"
    assert restart["matched_logged_observations_and_numerical_metrics"] == 4
    for name, expected in restart["source_files"].items():
        assert sha(name) == expected
    for key, item in restart["manifests"].items():
        assert cfg[key] == item["path"] and sha(cfg[key]) == item["sha256"]
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "source"
    archive.mkdir()
    sources = {}
    for source in [
        *Path("src/demosaic").glob("*.py"),
        Path(__file__),
        Path("scripts/preflight_paired_extension.py"),
        Path(config_path),
        availability_path,
        restart_path,
    ]:
        (archive / source.name).write_bytes(source.read_bytes())
        sources[str(source)] = sha(source)
    dataset = CleanDataset(
        cfg["manifest"],
        patch_size=256,
        seed=48,
        synthetic_fraction=0.2,
        flat_fraction=0.1,
        augmentation_downsample=2,
    )
    clean = [
        torch.stack([dataset[i]["rgb"] for i in range(start, start + 16)]) for start in [0, 16]
    ]
    native_data = RawCleanDataset(
        cfg["raw_clean_manifest"], patch_size=256, seed=48, augmentation_downsample=2
    )
    native = default_collate([native_data[i] for i in range(32, 48)])
    native = {k: v.cuda() for k, v in native.items()}
    batches = []
    for index in range(2):
        with data_random_context("cuda", 48, index + 1, True):
            batches.append(
                degrade(
                    clean[index].cuda(),
                    reconstruct_highlights=True,
                    preserve_negative_read_noise=True,
                    physical_fp32=True,
                    noise_free_fraction=0.1,
                    broad_camera=True,
                )
            )
    with data_random_context("cuda", 48, 3, True):
        native_batch = degrade_raw_clean(
            native,
            reconstruct_highlights=True,
            preserve_negative_read_noise=True,
            noise_free_fraction=0.1,
        )
    fixture_raw = torch.rand(4, 4, 32, 40, generator=torch.Generator().manual_seed(84)).cuda() * 0.3
    fixture_shot = torch.tensor([0, 2e-5, 0.00256, 0.00256], device="cuda")
    fixture_read = torch.tensor([0, 1e-8, 0.0000262144, 0.0000262144], device="cuda")
    fixture = {
        "packed": fixture_raw,
        "variance": fixture_raw * fixture_shot[:, None, None, None]
        + fixture_read[:, None, None, None],
        "shot": fixture_shot,
        "read": fixture_read,
        "colors": torch.stack([color_indices(p) for p in PATTERNS]).cuda(),
        "wb": torch.tensor([[2.0, 1.0, 1.5]], device="cuda").expand(4, -1),
        "matrix": torch.eye(3, device="cuda")[None].expand(4, -1, -1),
    }
    reference, records = {}, []
    for pyramid in [False, True]:
        assert psutil.virtual_memory().available / 1e9 > 24
        torch.manual_seed(48)
        options = dict(
            cfg["model"],
            dino=pyramid,
            dino_feature_fusion="convnext-pyramid" if pyramid else "bottleneck",
        )
        model = JointDemosaic(ModelConfig(**options)).cuda().to(memory_format=torch.channels_last)
        lineage = initialize_rgb_prior(model, cfg["gaussian_initialization"], archive=output)
        model.eval()
        common = tensors_digest(
            {
                k: v
                for k, v in model.restoration_state_dict().items()
                if not k.startswith("context.")
            }
        )
        frozen = tensors_digest(model.context.backbone.state_dict()) if pyramid else None
        initial = {}
        with torch.no_grad():
            for precision in ["float32", "bfloat16", "float16"]:
                result = prediction(model, fixture, precision)
                assert result.shape == (4, 3, 64, 80) and torch.isfinite(result).all()
                if pyramid:
                    torch.testing.assert_close(result, reference[precision], rtol=0, atol=0)
                else:
                    reference[precision] = result.clone()
                initial[precision] = tensors_digest({"prediction": result})
            result = prediction(model, batches[0], "float16")
            assert result.shape == (16, 3, 256, 256) and torch.isfinite(result).all()
            if pyramid:
                torch.testing.assert_close(result, reference["native256"], rtol=0, atol=0)
            else:
                reference["native256"] = result.clone()
            initial["native256_float16"] = tensors_digest({"prediction": result})
        optimizer = make_optimizer(model, cfg)
        ema = {k: v.detach().clone() for k, v in model.restoration_state_dict().items()}
        torch.cuda.reset_peak_memory_stats()
        updates = [
            update(model, optimizer, ema, batch, step, pyramid)
            for step, batch in enumerate(batches, 1)
        ]
        checkpoint = output / f"discarded-complete-state-{int(pyramid)}.pt"
        discarded_cfg = dict(
            cfg,
            run=str(output / f"discarded-{int(pyramid)}"),
            model=model.config.to_dict(),
            preflight_only=True,
            experiment_notes="Engineering-only constant-LR GPU preflight; no actual V58 quality training.",
        )
        save_checkpoint(checkpoint, model, optimizer, ema, 2, discarded_cfg, -float("inf"))
        saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
        assert psutil.virtual_memory().available / 1e9 > 24
        portable, state = load_checkpoint(checkpoint, "cuda")
        del state
        portable.eval().to(memory_format=torch.channels_last)
        assert_saved_equal(saved["ema"], portable.restoration_state_dict(), "portable EMA")
        model.load_state_dict(ema, strict=False)
        with torch.no_grad():
            expected = prediction(model.eval(), batches[1], "float16")
            actual = prediction(portable, batches[1], "float16")
        torch.testing.assert_close(expected, actual, rtol=0, atol=0)
        loaded = portable.load_state_dict(saved["model"], strict=False)
        assert not loaded.unexpected_keys and all(
            k.startswith("context.backbone.") for k in loaded.missing_keys
        )
        restored_optimizer = make_optimizer(portable, cfg)
        restored_optimizer.load_state_dict(saved["optimizer"])
        restored_ema = {k: v.cuda() for k, v in saved["ema"].items()}
        assert_saved_equal(saved["model"], portable.restoration_state_dict(), "restored model")
        assert_saved_equal(saved["ema"], restored_ema, "restored EMA")
        assert_saved_equal(
            saved["optimizer"], restored_optimizer.state_dict(), "restored optimizer"
        )
        torch.set_rng_state(saved["torch_rng"])
        random.setstate(saved["python_rng"])
        torch.cuda.set_rng_state_all(saved["cuda_rng"])
        assert_saved_equal(saved["torch_rng"], torch.get_rng_state(), "restored Torch RNG")
        assert_saved_equal(saved["python_rng"], random.getstate(), "restored Python RNG")
        assert_saved_equal(saved["cuda_rng"], torch.cuda.get_rng_state_all(), "restored CUDA RNG")
        if pyramid:
            assert (
                frozen
                == tensors_digest(model.context.backbone.state_dict())
                == tensors_digest(portable.context.backbone.state_dict())
            )
        continued = update(portable, restored_optimizer, restored_ema, native_batch, 3, pyramid)
        if pyramid:
            assert frozen == tensors_digest(portable.context.backbone.state_dict())
        records.append(
            {
                "pyramid": pyramid,
                "common_initial_sha256": common,
                "initial_predictions": initial,
                "gaussian_initialization": lineage,
                "updates": updates,
                "complete_state_checkpoint": {"path": str(checkpoint), "sha256": sha(checkpoint)},
                "portable_ema_fp16_exact": True,
                "complete_state_restored_exactly_before_next_update": True,
                "restored_native_update": continued,
                "frozen_encoder_initial_and_final_sha256": frozen,
                "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated(),
                "limitations": "State restoration is exact before continuation; CUDA optimization after continuation is not asserted bitwise equal to uninterrupted training. Constant preflight LR1e-4, not actual scheduled V58 training.",
            }
        )
        del (
            model,
            optimizer,
            ema,
            portable,
            restored_optimizer,
            restored_ema,
            saved,
            result,
            actual,
            expected,
        )
        gc.collect()
        torch.cuda.empty_cache()
    assert records[0]["common_initial_sha256"] == records[1]["common_initial_sha256"]
    assert [x["observation_sha256"] for x in records[0]["updates"]] == [
        x["observation_sha256"] for x in records[1]["updates"]
    ]
    assert (
        records[0]["restored_native_update"]["observation_sha256"]
        == records[1]["restored_native_update"]["observation_sha256"]
    )
    for path, expected in sources.items():
        assert sha(path) == expected
    receipt = {
        "status": "completed-genuine-cuda-pyramid-preflight",
        "torch": str(torch.__version__),
        "cuda": torch.version.cuda,
        "preceding_review": preceding,
        "source_files": sources,
        "arms": records,
        "limitations": "Engineering only; no trained quality or isolated speed evidence. Complete actual-trainer CPU restart is separate. Full production CUDA-prefix equivalence is not asserted.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json")}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="configs/dino-convnext-pyramid-fresh-b16-v58.yaml")
    parser.add_argument("--output", required=True)
    parser.add_argument("--preceding-controller", required=True)
    parser.add_argument("--preceding-status", required=True)
    parser.add_argument("--preceding-review", required=True)
    parser.add_argument("--preceding-review-sha256", required=True)
    args = parser.parse_args()
    main(
        args.config,
        args.output,
        args.preceding_controller,
        args.preceding_status,
        args.preceding_review,
        args.preceding_review_sha256,
    )
