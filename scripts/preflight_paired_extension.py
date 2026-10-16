"""Genuine-parent CUDA check of control/expanded paired batches before training."""

import argparse
import gc
import hashlib
import json
from pathlib import Path

import torch
from torch.utils.data import default_collate

from demosaic.inference import load_checkpoint
from demosaic.paired_training import PairedDataset, paired_reconstruction_loss
from demosaic.precision import amp_context
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def tensors_digest(values):
    result = hashlib.sha256()
    for key, value in sorted(values.items()):
        result.update(json.dumps([key, str(value.dtype), list(value.shape)]).encode())
        result.update(
            value.detach().cpu().contiguous().reshape(-1).view(torch.uint8).numpy().tobytes()
        )
    return result.hexdigest()


def gpu_batch(dataset, first):
    batch = default_collate([dataset[i] for i in range(first, first + 16)])
    batch = {key: value.cuda() for key, value in batch.items()}
    for name in ["packed", "variance"]:
        batch[name] = batch[name].contiguous(memory_format=torch.channels_last)
    return batch


def main(parent, expected, manifests, output):
    assert torch.cuda.is_available() and sha(parent) == expected
    torch.set_num_threads(4)
    torch.set_float32_matmul_precision("high")
    torch.backends.cudnn.benchmark = True
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    common_dataset = PairedDataset(manifests[0], patch_size=256, seed=52)
    common = gpu_batch(common_dataset, 0)
    records = []
    for manifest in manifests:
        dataset = PairedDataset(manifest, patch_size=256, seed=52)
        model, state = load_checkpoint(parent, "cuda")
        assert state["loaded_sha256"] == expected
        del state
        model.to(memory_format=torch.channels_last).eval()
        assert model.context is not None and model.config.dino_revision != "main"
        assert all(not p.requires_grad for p in model.context.backbone.parameters())
        initial_weights = tensors_digest(model.restoration_state_dict())
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
        model.train()
        parameters = [p for p in model.parameters() if p.requires_grad]
        optimizer = torch.optim.AdamW(parameters, lr=3e-5)
        steps = []
        torch.cuda.reset_peak_memory_stats()
        for first in [0, 16]:
            batch = gpu_batch(dataset, first)
            optimizer.zero_grad(set_to_none=True)
            model.set_noise(batch["shot"], batch["read"])
            with amp_context("cuda", dtype="bfloat16"):
                prediction, auxiliary = model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                    auxiliary=True,
                )
                loss, _ = paired_reconstruction_loss(prediction, batch, auxiliary)
            assert torch.isfinite(loss) and torch.isfinite(prediction).all()
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(parameters, 1.0)
            assert torch.isfinite(norm) and norm > 0
            assert all(p.grad is None for p in model.context.backbone.parameters())
            optimizer.step()
            steps.append(
                {
                    "sample_first": first,
                    "batch_size": 16,
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
        restored, _ = load_checkpoint(checkpoint, "cuda")
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
                "manifest": str(manifest),
                "manifest_sha256": sha(manifest),
                "sampling_groups": len(dataset),
                "initial_weights_sha256": initial_weights,
                "initial_common_prediction_sha256": initial_prediction,
                "foundation_revision": model.config.dino_revision,
                "foundation_unchanged_sha256": frozen,
                "discarded_updates": steps,
                "peak_cuda_gb": torch.cuda.max_memory_allocated() / 1e9,
                "portable_fp16_exact": True,
                "preflight_checkpoint_sha256": sha(checkpoint),
            }
        )
        del restored, model, optimizer, parameters, prediction, reloaded, auxiliary, batch, loss
        gc.collect()
        torch.cuda.empty_cache()
    assert len({r["initial_weights_sha256"] for r in records}) == 1
    assert len({r["initial_common_prediction_sha256"] for r in records}) == 1
    result = {
        "parent": str(parent),
        "parent_sha256": expected,
        "records": records,
        "source_files": {p.name: sha(p) for p in Path("src/demosaic").glob("*.py")},
        "driver_sha256": sha(__file__),
        "scope": "Two discarded BF16 paired updates per arm with actual B16/native256, genuine unchanged pinned DINO, exact common initialization and portable FP16 reload. Execution evidence only; no restoration quality or throughput claim.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "arms": len(records),
                "groups": [r["sampling_groups"] for r in records],
                "portable_fp16_exact": True,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("parent", type=Path)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--manifests", type=Path, nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.parent, args.expected_sha256, args.manifests, args.output)
