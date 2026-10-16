"""Discarded genuine-parent CUDA updates for the optional DINO input adapter."""

import argparse
import gc
import json
from pathlib import Path

import psutil
import torch
import yaml
from preflight_paired_extension import sha, tensors_digest

from demosaic.cfa import PATTERNS, color_indices
from demosaic.data import CleanDataset, degrade
from demosaic.inference import load_checkpoint
from demosaic.losses import reconstruction_loss
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.precision import amp_context, ieee_fp32
from demosaic.safety import writable_path
from demosaic.train import data_random_context


def main(config_path, output):
    assert torch.cuda.is_available() and psutil.virtual_memory().available / 1e9 > 24
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("high")
    torch.backends.cudnn.benchmark = True
    cfg = yaml.safe_load(Path(config_path).read_text())
    control = yaml.safe_load(Path("configs/dino-paired-expanded-b16-v54.yaml").read_text())
    common = {k: v for k, v in cfg.items() if k not in ["run", "experiment_notes"]}
    common["model"] = dict(common["model"])
    assert common["model"].pop("dino_input_adapter") is True
    assert common == {k: v for k, v in control.items() if k not in ["run", "experiment_notes"]}
    assert cfg["batch_size"] == 16 and cfg["seed"] == 52
    parent = Path(cfg["initialize_parent"]["checkpoint"])
    assert sha(parent) == cfg["initialize_parent"]["sha256"]
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    source_files = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    archive = output / "source"
    archive.mkdir()
    for name, value in source_files.items():
        (archive / name).write_bytes(value)
    (archive / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    (archive / "config.yaml").write_bytes(Path(config_path).read_bytes())
    initial = torch.load(parent, map_location="cpu", weights_only=True)
    weights = initial.get("ema", initial["model"])
    dataset = CleanDataset(
        cfg["manifest"],
        patch_size=256,
        seed=52,
        synthetic_fraction=0.2,
        flat_fraction=0.1,
        augmentation_downsample=2,
    )
    clean = [
        torch.stack([dataset[i]["rgb"] for i in range(start, start + 16)]) for start in [0, 16]
    ]

    def observation(index):
        with data_random_context("cuda", 52, index + 1, True):
            return degrade(
                clean[index].cuda(),
                reconstruct_highlights=True,
                preserve_negative_read_noise=True,
                physical_fp32=True,
                noise_free_fraction=0.1,
                broad_camera=True,
            )

    first = observation(0)
    fixture_raw = torch.rand(4, 4, 32, 40, generator=torch.Generator().manual_seed(84)).cuda() * 0.3
    fixture_colors = torch.stack([color_indices(p) for p in PATTERNS]).cuda()
    fixture_shot = torch.tensor([0, 2e-5, 0.00256, 0.00256], device="cuda")
    fixture_read = torch.tensor([0, 1e-8, 0.0000262144, 0.0000262144], device="cuda")
    fixture_variance = (
        fixture_raw * fixture_shot[:, None, None, None] + fixture_read[:, None, None, None]
    )
    wb = torch.tensor([[2.0, 1.0, 1.5]], device="cuda").expand(4, -1)
    matrix = torch.tensor(
        [[[1.1, -0.05, -0.05], [-0.05, 1.1, -0.05], [-0.05, -0.05, 1.1]]], device="cuda"
    ).expand(4, -1, -1)
    records, reference_predictions = [], {}
    for enabled in [False, True]:
        options = dict(cfg["model"], dino_input_adapter=enabled)
        torch.manual_seed(52)
        model = JointDemosaic(ModelConfig(**options)).cuda().to(memory_format=torch.channels_last)
        incompatible = model.load_state_dict(weights, strict=False)
        assert not incompatible.unexpected_keys
        assert all(
            k.startswith("context.backbone.") or enabled and k.startswith("context.input_adapter.")
            for k in incompatible.missing_keys
        )
        assert all(not p.requires_grad for p in model.context.backbone.parameters())
        original = tensors_digest(model.context.backbone.state_dict())
        common_initial = tensors_digest(
            {
                k: v
                for k, v in model.restoration_state_dict().items()
                if not k.startswith("context.input_adapter.")
            }
        )
        model.eval().set_noise(fixture_shot, fixture_read)
        initial_outputs = {}
        for precision in ["float32", "bfloat16", "float16"]:
            with torch.no_grad(), amp_context("cuda", dtype=precision):
                prediction = model(fixture_raw, fixture_variance, fixture_colors, wb, matrix)
            assert torch.isfinite(prediction).all() and prediction.shape == (4, 3, 64, 80)
            if enabled:
                torch.testing.assert_close(
                    prediction, reference_predictions[precision], rtol=0, atol=0
                )
            else:
                reference_predictions[precision] = prediction.detach().clone()
            initial_outputs[precision] = tensors_digest({"prediction": prediction})
        model.set_noise(first["shot"], first["read"])
        with torch.no_grad(), amp_context("cuda", dtype="float16"):
            prediction = model(
                first["packed"], first["variance"], first["colors"], first["wb"], first["matrix"]
            )
        if enabled:
            torch.testing.assert_close(
                prediction, reference_predictions["native256"], rtol=0, atol=0
            )
        else:
            reference_predictions["native256"] = prediction.detach().clone()
        initial_outputs["native256_fp16"] = tensors_digest({"prediction": prediction})
        optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=3e-5)
        model.train()
        updates = []
        torch.cuda.reset_peak_memory_stats()
        for index in range(2):
            batch = observation(index)
            model.set_noise(batch["shot"], batch["read"])
            optimizer.zero_grad(set_to_none=True)
            with amp_context("cuda", dtype="bfloat16"):
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
            assert all(p.grad is None for p in model.context.backbone.parameters())
            gradients = {}
            if enabled:
                for name, parameter in model.context.input_adapter.named_parameters():
                    assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
                    gradients[name] = float(parameter.grad.norm())
                assert gradients["layers.4.weight"] > 0
                if index:
                    assert gradients["layers.0.weight"] > 0
            optimizer.step()
            updates.append(
                {
                    "step": index + 1,
                    "loss": float(loss.detach()),
                    "gradient_norm": float(norm),
                    "input_adapter_gradient_norms": gradients,
                    "observation_sha256": tensors_digest(batch),
                }
            )
        assert original == tensors_digest(model.context.backbone.state_dict())
        model.eval()
        with torch.no_grad(), amp_context("cuda", dtype="float16"):
            prediction = model(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
        saved = output / f"discarded-{int(enabled)}.pt"
        torch.save(
            {
                "model_config": model.config.to_dict(),
                "model": model.restoration_state_dict(),
                "step": 2,
            },
            saved,
        )
        restored, state = load_checkpoint(saved, "cuda")
        del state
        restored.eval().to(memory_format=torch.channels_last).set_noise(
            batch["shot"], batch["read"]
        )
        with torch.no_grad(), amp_context("cuda", dtype="float16"):
            actual = restored(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
        torch.testing.assert_close(prediction, actual, rtol=0, atol=0)
        records.append(
            {
                "input_adapter": enabled,
                "initial_common_sha256": common_initial,
                "initial_predictions": initial_outputs,
                "frozen_foundation_sha256": original,
                "input_parameters": sum(p.numel() for p in model.context.input_adapter.parameters())
                if enabled
                else 0,
                "discarded_updates": updates,
                "portable_fp16_exact": True,
                "checkpoint": str(saved),
                "checkpoint_sha256": sha(saved),
                "peak_cuda_gb": torch.cuda.max_memory_allocated() / 1e9,
            }
        )
        del model, restored, optimizer, prediction, actual
        gc.collect()
        torch.cuda.empty_cache()
    assert records[0]["initial_common_sha256"] == records[1]["initial_common_sha256"]
    assert records[0]["initial_predictions"] == records[1]["initial_predictions"]
    assert records[0]["frozen_foundation_sha256"] == records[1]["frozen_foundation_sha256"]
    assert [r["observation_sha256"] for r in records[0]["discarded_updates"]] == [
        r["observation_sha256"] for r in records[1]["discarded_updates"]
    ]
    assert all(Path("src/demosaic", n).read_bytes() == p for n, p in source_files.items())
    receipt = {
        "scope": "Execution, gradient, identity and portability evidence only; discarded updates do not establish quality or speed.",
        "parent": str(parent),
        "parent_sha256": sha(parent),
        "config": cfg,
        "config_sha256": sha(config_path),
        "source_files": {n: sha(archive / n) for n in source_files},
        "script_sha256": sha(__file__),
        "records": records,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "receipt": str(output / "receipt.json"),
                "input_parameters": records[1]["input_parameters"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/dino-input-adapter-b16-v56.yaml")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.config, args.output)
