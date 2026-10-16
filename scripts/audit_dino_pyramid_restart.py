"""Check a genuine-weight four-update CPU prefix against a complete-state restart.

This is a discarded batch-one/native64 engineering audit. The original planned
10,000-update LR schedule is retained. It is not a trained quality comparison.
"""

import argparse
import gc
import hashlib
import json
import math
import shutil
from datetime import UTC, datetime
from pathlib import Path

import psutil
import torch
import yaml

from demosaic.safety import writable_path
from demosaic.train import train, training_domain


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def assert_equal(expected, actual, name):
    """Compare every nested tensor/scalar; file hashes differ with run metadata."""
    if isinstance(expected, torch.Tensor):
        torch.testing.assert_close(expected, actual, rtol=0, atol=0, msg=name)
    elif isinstance(expected, dict):
        assert expected.keys() == actual.keys(), name
        for key, value in expected.items():
            assert_equal(value, actual[key], f"{name}/{key}")
    elif isinstance(expected, (list, tuple)):
        assert type(expected) is type(actual) and len(expected) == len(actual), name
        for index, value in enumerate(expected):
            assert_equal(value, actual[index], f"{name}/{index}")
    else:
        assert expected == actual, name


def metrics(path):
    rows = [json.loads(line) for line in Path(path).read_text().splitlines()]
    return [r for r in rows if r["event"] == "train"]


def main(output):
    assert not torch.cuda.is_initialized()
    assert not torch.cuda.is_available(), (
        "Run with CUDA_VISIBLE_DEVICES='' to isolate this CPU audit"
    )
    assert psutil.virtual_memory().available / 1e9 > 24
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    assert shutil.disk_usage(output).free / 1e9 > 20
    template = Path("configs/dino-convnext-pyramid-fresh-b16-v58.yaml")
    cfg = yaml.safe_load(template.read_text())
    assert cfg["seed"] == 48 and cfg["steps"] == 10000 and cfg["warmup_steps"] == 100
    assert cfg["model"]["dino_feature_fusion"] == "convnext-pyramid"
    assert cfg["model"]["dino_revision"] == "10d30274b4d445111e2d5bf75ac93bbd94db274b"
    availability = Path("docs/results/dino-convnext-tiny-availability-v1.json")
    for item in json.loads(availability.read_text())["files"]:
        assert sha(item["path"]) == item["sha256"]
    manifests = {
        key: {"path": cfg[key], "sha256": sha(cfg[key])}
        for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]
    }
    source_files = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    archive = output / "source"
    archive.mkdir()
    for path in [*Path("src/demosaic").glob("*.py"), Path(__file__), template, availability]:
        (archive / path.name).write_bytes(path.read_bytes())
    cfg.update(
        device="cpu",
        batch_size=1,
        patch_size=64,
        workers=0,
        paired_workers=0,
        raw_clean_workers=0,
        cpu_threads=2,
        amp=False,
        precision="float32",
        channels_last=False,
        checkpoint_every=4,
        log_every=1,
        val_batches=1,
        validation_images=1,
        min_available_gb=24,
    )
    cfg["experiment_notes"] = (
        "Discarded genuine ConvNeXt/Gaussian CPU restart audit only. Original seed48, "
        "planned10000/warmup100/LR and frozen manifests; batch1/native64/FP32/workers0. "
        "Compare four uninterrupted updates with2+2 whole-state resume. Not V58 quality training."
    )
    config_path = output / "cpu-config.yaml"
    full_run, resumed_run = output / "discarded-full", output / "discarded-resumed"
    cfg["run"] = str(full_run)
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    print("Uninterrupted genuine CPU prefix: four updates", flush=True)
    full_path = train(config_path, stop_after=4)
    gc.collect()
    cfg["run"] = str(resumed_run)
    config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
    print("Interrupted genuine CPU prefix: two updates", flush=True)
    interrupted_path = train(config_path, stop_after=2)
    interrupted_copy = output / "discarded-step2.pt"
    shutil.copyfile(interrupted_path, interrupted_copy)
    gc.collect()
    print("Resuming complete model/EMA/AdamW/RNG for two further updates", flush=True)
    actual_path = train(config_path, resume=interrupted_copy, stop_after=2)
    gc.collect()
    print("Comparing complete states and every observation", flush=True)
    full = torch.load(full_path, map_location="cpu", weights_only=True)
    actual = torch.load(actual_path, map_location="cpu", weights_only=True)
    assert full["step"] == actual["step"] == 4
    assert full["config"]["steps"] == actual["config"]["steps"] == 10000
    fields = [
        "model_config",
        "model",
        "ema",
        "optimizer",
        "torch_rng",
        "python_rng",
        "cuda_rng",
        "best",
    ]
    for field in fields:
        assert_equal(full[field], actual[field], field)
    assert full["cuda_rng"] == actual["cuda_rng"] == []
    assert full["config"]["source_sha256"] == actual["config"]["source_sha256"]
    for key, item in manifests.items():
        assert (
            full["config"][key + "_sha256"] == actual["config"][key + "_sha256"] == item["sha256"]
        )
    expected_prior = "479abe3c5327dfd10ff54a80ec7d4098ca80752a5c9492cdff31cee430bec4b4"
    for state in [full, actual]:
        assert state["config"]["initialized_from"]["prior"]["weights_sha256"] == expected_prior
        assert not any(key.startswith("context.backbone.") for key in state["model"])
        assert {float(x["step"]) for x in state["optimizer"]["state"].values() if "step" in x} == {
            4.0
        }
        assert all(torch.isfinite(x).all() for x in state["model"].values())
        assert all(float(state["model"][f"context.gates.{i}"].norm()) > 0 for i in range(3))
    uninterrupted = metrics(full_run / "metrics.jsonl")
    resumed = metrics(resumed_run / "metrics.jsonl")
    assert len(uninterrupted) == len(resumed) == 4
    numerical_fields = [key for key in uninterrupted[0] if key not in ["seconds_per_step"]]
    for first, second in zip(uninterrupted, resumed):
        # Paired/native loss components differ by domain; compare every key.
        assert {k: v for k, v in first.items() if k != "seconds_per_step"} == {
            k: v for k, v in second.items() if k != "seconds_per_step"
        }
        assert math.isfinite(first["loss"])
    assert {r["domain"] for r in uninterrupted} == {
        "synthetic",
        "native-RAW-synthetic",
        "paired-RAW",
    }
    assert [training_domain(s, 48, 0.25, 0.25) for s in range(1, 5)] == [
        "commons",
        "commons",
        "native",
        "paired",
    ]
    for path, expected in source_files.items():
        assert sha(path) == expected
    assert not torch.cuda.is_initialized()
    receipt = {
        "status": "completed-genuine-cpu-complete-state-restart-audit",
        "created_utc": datetime.now(UTC).isoformat(),
        "torch": str(torch.__version__),
        "device": "cpu",
        "cuda_initialized": False,
        "source_files": source_files,
        "driver": {"path": str(Path(__file__).resolve()), "sha256": sha(__file__)},
        "template": {"path": str(template), "sha256": sha(template)},
        "changes_for_cpu_fixture": {
            key: cfg[key]
            for key in [
                "device",
                "batch_size",
                "patch_size",
                "workers",
                "paired_workers",
                "raw_clean_workers",
                "cpu_threads",
                "amp",
                "precision",
                "channels_last",
                "checkpoint_every",
                "log_every",
                "val_batches",
                "validation_images",
                "min_available_gb",
            ]
        },
        "original_schedule": {
            "planned_updates": 10000,
            "warmup_updates": 100,
            "base_lr": cfg["lr"],
        },
        "actual_global_updates": 4,
        "resume_boundary": 2,
        "exact_fields": fields,
        "source_bundle_sha256": full["config"]["source_sha256"],
        "matched_logged_observations_and_numerical_metrics": 4,
        "only_excluded_training_metric": "seconds_per_step",
        "checked_first_step_fields": numerical_fields,
        "observations": [
            {k: v for k, v in row.items() if k != "seconds_per_step"} for row in uninterrupted
        ],
        "model_tensor_count": len(full["model"]),
        "ema_tensor_count": len(full["ema"]),
        "optimizer_parameter_states": len(full["optimizer"]["state"]),
        "learned_gate_norms": [float(full["model"][f"context.gates.{i}"].norm()) for i in range(3)],
        "genuine_gaussian_weights_sha256": expected_prior,
        "genuine_convnext_weights_sha256": "bd30a9459d6149564ef53af6e8a1999980953b009b94cde836ac1bac4d339cb2",
        "manifests": manifests,
        "checkpoints": {
            key: {"path": str(path), "sha256": sha(path)}
            for key, path in [
                ("uninterrupted4", full_path),
                ("interrupted2", interrupted_copy),
                ("resumed4", actual_path),
            ]
        },
        "limitations": (
            "Four discarded CPU FP32 batch1/native64 updates with genuine weights, including all three training domains. "
            "Not CUDA/BF16/FP16 equivalence, production batch16/native256 validation, convergence, speed or trained quality. "
            "Checkpoint file hashes differ with run metadata; every listed model/EMA/optimizer/RNG field is compared exactly."
        ),
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
