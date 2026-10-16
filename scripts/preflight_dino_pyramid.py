"""CPU-only engineering checks with genuine frozen ConvNeXt/Gaussian weights.

Updates/checkpoints are discarded preflight artifacts, never quality candidates.
Run a separate full CUDA validation before launching any actual experiment.
"""

import argparse
import gc
import json
from datetime import UTC, datetime
from pathlib import Path

import torch
import yaml
from preflight_paired_extension import sha, tensors_digest

from demosaic.cfa import PATTERNS, color_indices
from demosaic.data import CleanDataset, degrade
from demosaic.inference import load_checkpoint
from demosaic.losses import reconstruction_loss
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.precision import ieee_fp32
from demosaic.pretrained_rgb import initialize_rgb_prior
from demosaic.safety import writable_path
from demosaic.train import data_random_context


def main(output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    availability_path = Path("docs/results/dino-convnext-tiny-availability-v1.json")
    availability = json.loads(availability_path.read_text())
    for item in availability["files"]:
        assert sha(item["path"]) == item["sha256"]
    cfg_path = Path("configs/control-anchored-native-fresh-b16-v45.yaml")
    cfg = yaml.safe_load(cfg_path.read_text())
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    archive = output / "source"
    archive.mkdir()
    source_files = {}
    for source in [
        *Path("src/demosaic").glob("*.py"),
        Path(__file__),
        Path("scripts/preflight_paired_extension.py"),
        cfg_path,
        availability_path,
    ]:
        (archive / source.name).write_bytes(source.read_bytes())
        source_files[str(source)] = sha(source)
    dataset = CleanDataset(
        cfg["manifest"],
        patch_size=256,
        seed=48,
        synthetic_fraction=0.2,
        flat_fraction=0.1,
        augmentation_downsample=2,
    )
    batches = []
    for index in range(2):
        with data_random_context("cpu", 48, index + 1, True):
            batches.append(
                degrade(
                    dataset[index]["rgb"][None],
                    reconstruct_highlights=True,
                    preserve_negative_read_noise=True,
                    physical_fp32=True,
                    noise_free_fraction=0.1,
                    broad_camera=True,
                )
            )
    raw = torch.rand(4, 4, 17, 25, generator=torch.Generator().manual_seed(84)) * 0.3
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    shot, read = (
        torch.tensor([0, 2e-5, 0.00256, 0.00256]),
        torch.tensor([0, 1e-8, 2.62144e-5, 2.62144e-5]),
    )
    variance = raw * shot[:, None, None, None] + read[:, None, None, None]
    wb = torch.tensor([[2.0, 1.0, 1.5]]).expand(4, -1)
    matrix = torch.eye(3)[None].expand(4, -1, -1)
    reference, records = {}, []
    for enabled in [False, True]:
        print(f"CPU engineering arm: pyramid={enabled}", flush=True)
        options = dict(cfg["model"], dino=enabled)
        if enabled:
            options.update(
                dino_model=availability["repo"],
                dino_revision=availability["revision"],
                dino_feature_fusion="convnext-pyramid",
            )
        torch.manual_seed(48)
        model = JointDemosaic(ModelConfig(**options))
        lineage = initialize_rgb_prior(model, cfg["gaussian_initialization"], archive=output)
        common = tensors_digest(
            {
                k: v
                for k, v in model.restoration_state_dict().items()
                if not k.startswith("context.")
            }
        )
        initial_predictions = {}
        frozen = tensors_digest(model.context.backbone.state_dict()) if enabled else None
        seen_dtypes = []
        handle = model.pretrained_rgb.network.m_down1.register_forward_hook(
            lambda _module, _inputs, result, seen=seen_dtypes: seen.append(result.dtype)
        )
        model.eval()
        for precision in ["float32", "bfloat16"]:
            if precision == "float32":
                model.set_noise(shot, read)
                arguments = raw, variance, colors, wb, matrix
                expected_shape = (4, 3, 34, 50)
            else:
                # CPU BF16 is emulated/slow on some hosts. Keep this genuine
                # precision fixture small; native256 updates below use FP32.
                model.set_noise(shot[2:3], read[2:3])
                arguments = (
                    raw[2:3, :, :16, :16],
                    variance[2:3, :, :16, :16],
                    colors[2:3],
                    wb[2:3],
                    matrix[2:3],
                )
                expected_shape = (1, 3, 32, 32)
            with (
                torch.no_grad(),
                ieee_fp32(),
                torch.autocast("cpu", dtype=torch.bfloat16, enabled=precision == "bfloat16"),
            ):
                prediction = model(*arguments)
            assert seen_dtypes[-1] == getattr(torch, precision)
            assert prediction.shape == expected_shape and torch.isfinite(prediction).all()
            if enabled:
                torch.testing.assert_close(prediction, reference[precision], rtol=0, atol=0)
            else:
                reference[precision] = prediction.clone()
            initial_predictions[precision] = tensors_digest({"prediction": prediction})
            print(f"Initial {precision} fixture passed: {expected_shape}", flush=True)
        first = batches[0]
        model.set_noise(first["shot"], first["read"])
        with torch.no_grad(), torch.autocast("cpu", enabled=False):
            prediction = model(
                first["packed"], first["variance"], first["colors"], first["wb"], first["matrix"]
            )
        assert prediction.shape == (1, 3, 256, 256) and torch.isfinite(prediction).all()
        if enabled:
            torch.testing.assert_close(prediction, reference["native256"], rtol=0, atol=0)
        else:
            reference["native256"] = prediction.clone()
        initial_predictions["native256_float32"] = tensors_digest({"prediction": prediction})
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=1e-4)
        model.train()
        updates = []
        for index, batch in enumerate(batches):
            model.set_noise(batch["shot"], batch["read"])
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cpu", enabled=False):
                prediction, auxiliary = model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                    auxiliary=True,
                )
                loss, _ = reconstruction_loss(prediction, batch, auxiliary, physical_fp32=True)
            assert torch.isfinite(loss) and torch.isfinite(prediction).all()
            with ieee_fp32():
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(
                    model.parameters(), 1, error_if_nonfinite=True
                )
            gradients = {}
            if enabled:
                assert not model.context.backbone.training
                assert all(
                    not p.requires_grad and p.grad is None
                    for p in model.context.backbone.parameters()
                )
                for name, param in model.context.named_parameters():
                    if param.requires_grad:
                        assert param.grad is not None and torch.isfinite(param.grad).all()
                        gradients[name] = float(param.grad.norm())
                assert all(gradients[f"gates.{i}"] > 0 for i in range(3))
                if index:
                    assert all(gradients[f"laterals.{i}.weight"] > 0 for i in range(4))
                    assert all(gradients[f"projections.{i}.weight"] > 0 for i in range(3))
            optimizer.step()
            updates.append(
                {
                    "step": index + 1,
                    "loss": float(loss.detach()),
                    "gradient_norm": float(norm),
                    "context_gradient_norms": gradients,
                    "observation_sha256": tensors_digest(batch),
                }
            )
            print(f"discarded update {index + 1}: loss={float(loss.detach()):.8f}", flush=True)
        if enabled:
            assert frozen == tensors_digest(model.context.backbone.state_dict())
        model.eval()
        with torch.no_grad(), torch.autocast("cpu", enabled=False):
            prediction = model(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
        checkpoint = output / f"discarded-{int(enabled)}.pt"
        torch.save(
            {
                "model_config": model.config.to_dict(),
                "model": model.restoration_state_dict(),
                "step": 2,
                "preflight_only": True,
            },
            checkpoint,
        )
        restored, state = load_checkpoint(checkpoint, "cpu")
        del state
        restored.eval().set_noise(batch["shot"], batch["read"])
        with torch.no_grad(), torch.autocast("cpu", enabled=False):
            actual = restored(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
        torch.testing.assert_close(prediction, actual, rtol=0, atol=0)
        assert seen_dtypes[:2] == [torch.float32, torch.bfloat16]
        assert all(x == torch.float32 for x in seen_dtypes[2:])
        handle.remove()
        records.append(
            {
                "pyramid": enabled,
                "model_config": model.config.to_dict(),
                "trainable_parameters": sum(
                    p.numel() for p in model.parameters() if p.requires_grad
                ),
                "frozen_encoder_parameters": sum(
                    p.numel() for p in model.context.backbone.parameters()
                )
                if enabled
                else 0,
                "context_trainable_parameters": sum(
                    p.numel() for p in model.context.parameters() if p.requires_grad
                )
                if enabled
                else 0,
                "common_initial_sha256": common,
                "initial_predictions": initial_predictions,
                "gaussian_initialization": lineage,
                "updates": updates,
                "frozen_backbone_initial_and_final_sha256": frozen,
                "portable_float32_reload_exact": True,
                "trunk_output_dtypes_verified": [str(x) for x in seen_dtypes],
                "discarded_checkpoint": {"path": str(checkpoint), "sha256": sha(checkpoint)},
            }
        )
        del model, restored, optimizer, prediction, actual, loss
        gc.collect()
    assert records[0]["common_initial_sha256"] == records[1]["common_initial_sha256"]
    assert not torch.cuda.is_initialized()
    receipt = {
        "created_utc": datetime.now(UTC).isoformat(),
        "status": "completed-cpu-engineering-preflight",
        "device": "cpu",
        "torch": torch.__version__,
        "cuda_initialized": False,
        "source_files": source_files,
        "arms": records,
        "precision_protocol": {
            "all_cfa_rectangular_fixture": "FP32, 4 native34x50 images; mixed shot/read including zero",
            "explicit_cpu_bfloat16_fixture": "1 native32x32 GBRG image; shot0.00256/read2.62144e-5; initial forward only",
            "native256_initial_and_updates_and_reload": "FP32, batch1; two discarded updates per arm",
            "observed_trunk_output_dtypes_asserted": True,
        },
        "limitations": "Two discarded batch1 CPU FP32 updates per arm and a small genuine BF16 initial-forward fixture; engineering only. No quality, throughput, CUDA/FP16, BF16-training or convergence evidence; full GPU validation and matched training remain.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json")}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    main(parser.parse_args().output)
