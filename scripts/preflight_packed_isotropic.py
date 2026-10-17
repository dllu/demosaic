"""Discarded production-size mixed training and portable inference checks.

Use cached genuine DINOv3 weights and the configured Commons/native/paired
manifests. No quality score, training extension, or promoted model is produced.
"""

import argparse
import gc
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml

import demosaic.train as training
from demosaic.cfa import bilinear, color_indices
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def tensor_hash(value):
    return hashlib.sha256(value.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def module_hash(module):
    digest = hashlib.sha256()
    for name, value in module.state_dict().items():
        digest.update(name.encode())
        digest.update(value.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def prediction(model, batch, precision):
    with amp_context("cuda", dtype=precision):
        return model(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))


def main(config_path, output):
    config_path, output = Path(config_path).resolve(), writable_path(output)
    assert not output.exists(), "Choose a new output directory"
    assert psutil.virtual_memory().available / 2**30 > 40
    assert psutil.disk_usage(output.parent).free / 2**30 > 512
    config = yaml.safe_load(config_path.read_text())
    assert config["model"]["restoration_backbone"] == "packed-isotropic"
    assert config["model"]["dino"] and config["model"]["dino_feature_fusion"] == "packed-convnext"
    assert config["model"]["dino_revision"] == "10d30274b4d445111e2d5bf75ac93bbd94db274b"
    assert config["batch_size"] == 16 and config["patch_size"] == 256
    assert config["precision"] == "bfloat16" and config["steps"] == 40000
    output.mkdir()
    guards = {
        str(path.resolve()): sha(path)
        for path in [config_path, Path(__file__), *Path("src/demosaic").glob("*.py")]
    }
    for key in ("manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"):
        guards[config[key]] = sha(config[key])
    plan = {
        "scope": "12 discarded B16/native256/BF16 updates with actual mixed data and production "
        "workers, finite gradients/model/EMA/Adam, unchanged genuine frozen DINO, portable EMA "
        "FP32/BF16/FP16 equality and synthetic tile forward timing. No quality, convergence or "
        "100MP end-to-end timing claim.",
        "guards": guards,
        "fixture_overrides": {"run": str(output / "run"), "log_every": 1},
        "stop_after": 12,
        "planned_schedule": config["steps"],
        "available_gib_before": psutil.virtual_memory().available / 2**30,
        "shared_machine": True,
    }
    (output / "plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    fixture = {**config, **plan["fixture_overrides"]}
    fixture_path = output / "fixture.yaml"
    fixture_path.write_text(yaml.safe_dump(fixture, sort_keys=False))
    capture = {}
    constructor = training.JointDemosaic

    def tracked(options):
        model = constructor(options)
        capture["model"] = model
        capture["DINO_before"] = module_hash(model.context.backbone)
        capture["initial_parameters"] = {
            name: tensor_hash(value)
            for name, value in model.named_parameters()
            if value.requires_grad
        }

        def first_forward(module, args, kwargs):
            # Initial zero output head must preserve RAW precision under AMP.
            with torch.no_grad():
                result = module.packed_isotropic(*args, context=module.context)
                torch.testing.assert_close(result, bilinear(args[0], args[2]), rtol=0, atol=0)
            handle.remove()
            capture["initial_signal_preserved"] = True

        handle = model.register_forward_pre_hook(first_forward, with_kwargs=True)
        return model

    torch.set_num_threads(4)
    training.JointDemosaic = tracked
    try:
        checkpoint = training.train(fixture_path, stop_after=12)
    finally:
        training.JointDemosaic = constructor
    model = capture["model"]
    assert module_hash(model.context.backbone) == capture["DINO_before"]
    assert not model.context.backbone.training
    assert all(not p.requires_grad and p.grad is None for p in model.context.backbone.parameters())
    gradients = {
        name: float(value.grad.norm())
        for name, value in model.named_parameters()
        if value.requires_grad
    }
    assert all(value > 0 and np.isfinite(value) for value in gradients.values())
    changed = [
        name
        for name, p in model.named_parameters()
        if p.requires_grad and tensor_hash(p) != capture["initial_parameters"][name]
    ]
    assert len(changed) == len(gradients)
    rows = [
        r
        for line in (output / "run/metrics.jsonl").read_text().splitlines()
        if (r := json.loads(line)).get("event") == "train"
    ]
    assert len(rows) == 12 and {r["domain"] for r in rows} == {
        "synthetic",
        "paired-RAW",
        "native-RAW-synthetic",
    }
    state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
    assert state["step"] == 12 and state["config"]["steps"] == 40000
    assert len(state["optimizer"]["state"]) == len(gradients)
    for group in (state["model"], state["ema"]):
        assert all(torch.isfinite(value).all() for value in group.values())
    for item in state["optimizer"]["state"].values():
        assert int(item["step"]) == 12
        assert all(torch.isfinite(value).all() for value in item.values())
    training_peak = torch.cuda.max_memory_allocated()
    model.load_state_dict(state["ema"], strict=False)
    model.eval()
    restored, _ = load_checkpoint(checkpoint, "cuda")
    restored.eval().to(memory_format=torch.channels_last)
    assert module_hash(model) == module_hash(restored)
    portable = []
    with torch.inference_mode():
        for index in range(2):
            path = (
                Path("/mnt/external/demosaic/evaluation/two-fixed-examples-v43-none10k-cpu-v1")
                / f"observation-{index}-cpu.npz"
            )
            with np.load(path, allow_pickle=False) as archive:
                batch = {
                    key: torch.from_numpy(archive[key].copy()).to("cuda") for key in archive.files
                }
            for precision in ("float32", "bfloat16", "float16"):
                a, b = prediction(model, batch, precision), prediction(restored, batch, precision)
                assert a.dtype == torch.float32 and torch.isfinite(a).all()
                torch.testing.assert_close(a, b, rtol=0, atol=0)
                portable.append(
                    {
                        "observation": str(path),
                        "observation_sha256": sha(path),
                        "precision": precision,
                        "bitwise_equal": True,
                    }
                )
    del restored, a, b, batch, state
    gc.collect()
    torch.cuda.empty_cache()
    timings = []
    with torch.inference_mode():
        raw = torch.rand(4, 4, 256, 256, device="cuda").contiguous(
            memory_format=torch.channels_last
        )
        batch = {
            "packed": raw,
            "variance": raw * 0.0014635775921166604 + 1.0715704128646712e-6,
            "colors": color_indices("RGGB", device="cuda")[None].expand(4, -1),
            "wb": torch.tensor([[1.5132450331, 1.0, 2.2152317881]], device="cuda").expand(4, -1),
            "matrix": torch.eye(3, device="cuda")[None].expand(4, -1, -1),
        }
        for precision in ("float16", "bfloat16"):
            for _ in range(5):
                prediction(model, batch, precision)
            torch.cuda.synchronize()
            for repeat in range(3):
                started = time.perf_counter()
                for _ in range(10):
                    prediction(model, batch, precision)
                torch.cuda.synchronize()
                seconds = (time.perf_counter() - started) / 10
                timings.append(
                    {
                        "precision": precision,
                        "repeat": repeat,
                        "batch": 4,
                        "native_tile": 512,
                        "seconds_per_forward": seconds,
                    }
                )
    for path, expected in guards.items():
        assert sha(path) == expected, path
    receipt = {
        "status": "completed-discarded-packed-isotropic-CUDA-preflight",
        "scope": plan["scope"],
        "plan_sha256": sha(output / "plan.json"),
        "checkpoint": {"path": str(checkpoint), "sha256": sha(checkpoint)},
        "source_sha256": yaml.safe_load((output / "run/config.yaml").read_text())["source_sha256"],
        "DINO_sha256_unchanged": capture["DINO_before"],
        "initial_signal_preserved": capture["initial_signal_preserved"],
        "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
        "trainable_tensors": len(gradients),
        "changed_tensors": changed,
        "finite_gradient_norms": gradients,
        "model_EMA_Adam_finite": True,
        "all_model_EMA_backbone_tensors_equal_after_portable_reload": True,
        "training": rows,
        "portable_predictions": portable,
        "peak_training_cuda_allocated_bytes": training_peak,
        "tile_forward_timing": timings,
        "timing_scope": "Synthetic random RAW tiles; forward only, including physical/DINO/neural "
        "work. Excludes decoding, loading, tile extraction/transfer, blending and writing. "
        "Not a full-frame restoration time or quality measurement.",
        "available_gib_after": psutil.virtual_memory().available / 2**30,
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "receipt": str(output / "receipt.json"),
                "trainable_parameters": receipt["trainable_parameters"],
                "peak_training_cuda_allocated_bytes": training_peak,
                "timings": timings,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.config, args.output)
