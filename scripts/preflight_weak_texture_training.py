"""Actual Commons weak-source CUDA updates from the genuine retained parent."""

import argparse
import gc
import json
import random
from pathlib import Path

import psutil
import torch
import yaml
from preflight_paired_extension import sha, tensors_digest

from demosaic.data import CleanDataset, degrade
from demosaic.inference import load_checkpoint
from demosaic.losses import reconstruction_loss
from demosaic.precision import amp_context, ieee_fp32
from demosaic.safety import writable_path
from demosaic.train import data_random_context, training_domain


def main(config_path, output):
    assert torch.cuda.is_available() and psutil.virtual_memory().available / 1e9 > 24
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("high")
    torch.backends.cudnn.benchmark = True
    cfg = yaml.safe_load(Path(config_path).read_text())
    assert cfg["weak_texture_fraction"] == 0.1 and cfg["synthetic_fraction"] == 0.2
    assert cfg["augmentation_downsample"] == 2 and cfg["batch_size"] == 16
    assert cfg["seed"] == 52 and cfg["data_seed_per_step"]
    parent = Path(cfg["initialize_parent"]["checkpoint"])
    expected = cfg["initialize_parent"]["sha256"]
    assert sha(parent) == expected
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    sources = {p.name: p.read_bytes() for p in Path("src/demosaic").glob("*.py")}
    steps = [step for step in range(1, 100) if training_domain(step, 52, 0.25, 0.25) == "commons"][
        :2
    ]
    batches, cpu_records = {}, []
    for fraction in [0, 0.1]:
        dataset = CleanDataset(
            cfg["manifest"],
            patch_size=256,
            seed=52,
            synthetic_fraction=0.2,
            flat_fraction=0.1,
            augmentation_downsample=2,
            weak_texture_fraction=fraction,
        )
        batches[fraction] = []
        for step in steps:
            indices = list(range((step - 1) * 16, step * 16))
            rgb = torch.stack([dataset[i]["rgb"] for i in indices])
            expected_changes = [i for i in indices if 0.1 <= random.Random(52 + i).random() < 0.2]
            if fraction:
                original = batches[0][len(batches[fraction])]["rgb"]
                changes = [i for i, a, b in zip(indices, original, rgb) if not torch.equal(a, b)]
                assert changes == expected_changes
            batches[fraction].append({"step": step, "indices": indices, "rgb": rgb})
            cpu_records.append(
                {
                    "fraction": fraction,
                    "step": step,
                    "indices": indices,
                    "candidate_replacement_indices": expected_changes,
                    "rgb_sha256": tensors_digest({"rgb": rgb}),
                }
            )

    assert any(r["candidate_replacement_indices"] for r in cpu_records)

    def observation(rgb, step):
        with data_random_context("cuda", 52, step, True):
            return degrade(
                rgb.cuda(),
                reconstruct_highlights=True,
                preserve_negative_read_noise=True,
                physical_fp32=True,
                noise_free_fraction=0.1,
                broad_camera=True,
            )

    common = observation(batches[0][0]["rgb"], steps[0])
    records = []
    for fraction in [0, 0.1]:
        model, state = load_checkpoint(parent, "cuda")
        assert state["loaded_sha256"] == expected
        del state
        model.to(memory_format=torch.channels_last).eval()
        assert model.config.dino_revision == "114c1379950215c8b35dfcd4e90a5c251dde0d32"
        assert all(not p.requires_grad for p in model.context.backbone.parameters())
        initial = tensors_digest(model.restoration_state_dict())
        frozen = tensors_digest(model.context.backbone.state_dict())
        model.set_noise(common["shot"], common["read"])
        with torch.no_grad(), amp_context("cuda", dtype="float16"):
            prediction = model(
                common["packed"],
                common["variance"],
                common["colors"],
                common["wb"],
                common["matrix"],
            )
        initial_prediction = tensors_digest({"prediction": prediction})
        del prediction
        parameters = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(parameters, lr=3e-5, weight_decay=0.01)
        updates = []
        model.train()
        torch.cuda.reset_peak_memory_stats()
        for sample in batches[fraction]:
            batch = observation(sample["rgb"], sample["step"])
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
                norm = torch.nn.utils.clip_grad_norm_(parameters, 1, error_if_nonfinite=True)
            assert norm > 0 and all(p.grad is None for p in model.context.backbone.parameters())
            optimizer.step()
            updates.append(
                {
                    "step_in_original_commons_schedule": sample["step"],
                    "loss": float(loss.detach()),
                    "gradient_norm": float(norm),
                }
            )
        assert frozen == tensors_digest(model.context.backbone.state_dict())
        model.eval()
        with torch.no_grad(), amp_context("cuda", dtype="float16"):
            prediction = model(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
        checkpoint = output / f"discarded-preflight-{len(records)}.pt"
        torch.save(
            {
                "model_config": model.config.to_dict(),
                "model": model.restoration_state_dict(),
                "step": 2,
                "config": {"run": str(output), "preflight_only": True},
            },
            checkpoint,
        )
        restored, restored_state = load_checkpoint(checkpoint, "cuda")
        del restored_state
        restored.to(memory_format=torch.channels_last).eval().set_noise(
            batch["shot"], batch["read"]
        )
        with torch.no_grad(), amp_context("cuda", dtype="float16"):
            reloaded = restored(
                batch["packed"], batch["variance"], batch["colors"], batch["wb"], batch["matrix"]
            )
        torch.testing.assert_close(prediction, reloaded, rtol=0, atol=0)
        records.append(
            {
                "weak_texture_fraction": fraction,
                "initial_weights_sha256": initial,
                "initial_common_prediction_sha256": initial_prediction,
                "foundation_unchanged_sha256": frozen,
                "discarded_updates": updates,
                "portable_fp16_exact": True,
                "checkpoint_sha256": sha(checkpoint),
                "peak_cuda_gb": torch.cuda.max_memory_allocated() / 1e9,
            }
        )
        del (
            model,
            restored,
            optimizer,
            parameters,
            prediction,
            reloaded,
            batch,
            auxiliary,
            loss,
        )
        gc.collect()
        torch.cuda.empty_cache()
    assert len({r["initial_weights_sha256"] for r in records}) == 1
    assert len({r["initial_common_prediction_sha256"] for r in records}) == 1
    assert all(Path("src/demosaic", name).read_bytes() == value for name, value in sources.items())
    result = {
        "scope": "Two discarded BF16 updates per arm from actual first two Commons batches, seed52/B16/native256, weak0/.1 with same photo/flat quotas. Genuine pinned frozen DINO, equal initial tensors/common FP16 output and exact portable reload. No trained quality or throughput claim.",
        "config": str(config_path),
        "config_sha256": sha(config_path),
        "parent": str(parent),
        "parent_sha256": expected,
        "records": records,
        "cpu_source_batches": cpu_records,
        "source_files": {name: sha(Path("src/demosaic", name)) for name in sources},
        "driver_sha256": sha(__file__),
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"arms": len(records), "portable_fp16_exact": True}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, default=Path("configs/dino-paired-weak-texture-b16-v55.yaml")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.config, args.output)
