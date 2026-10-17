"""Actual-trainer CPU/CUDA checks for the matched full-restoration sensor loss."""

import argparse
import gc
import json
import math
import shutil
from pathlib import Path

import psutil
import torch
import yaml
from audit_flat_palette import PARENT, PARENT_SHA, identical, sha, train_rows
from preflight_flat_palette_cuda import portable_predictions

from demosaic.safety import writable_path
from demosaic.train import train

BASE = Path("/mnt/external/demosaic")
PRECEDING = {
    "wide-flat-palette-full4k-workflow-v1": "completed-original4000-and-evaluation-awaiting-manual-review",
    "palette-final-review-workflow-v1": "completed-final4k-review-artifacts-awaiting-native-review",
    "rawforge-original-GPU-workflow-v1": "completed-original-exports-awaiting-numerical-and-native-review",
    "rawforge-original-GPU-render-workflow-v1": "completed-original-GPU-native-rendering-awaiting-visual-review",
}


def preceding_review(review_path, expected_sha256):
    """Check actual producer exits before output creation or CUDA initialization."""
    if sha(review_path) != expected_sha256:
        raise ValueError("Completed palette review SHA differs")
    review = json.loads(Path(review_path).read_text())
    if not review["review_complete"]:
        raise ValueError("Palette review is incomplete")
    records = []
    for name, terminal in PRECEDING.items():
        path = BASE / "runs" / (name + ".json")
        status = json.loads(path.read_text())
        owner = status["controller"]
        try:
            proc = psutil.Process(owner["pid"])
            if (
                abs(proc.create_time() - owner["created"]) < 0.01
                and proc.status() != psutil.STATUS_ZOMBIE
            ):
                raise RuntimeError(f"Preceding owned workflow remains live: {proc.pid}")
        except psutil.NoSuchProcess:
            pass
        if status["status"] != terminal:
            raise RuntimeError(f"Preceding owned workflow incomplete: {name}")
        records.append(
            {"path": str(path), "sha256": sha(path), "controller": owner, "status": terminal}
        )
    return {"path": str(review_path), "sha256": expected_sha256, "actual_exits": records}


def main(config_path, control_path, output, device, review_path, review_sha256, weight=0.01):
    assert not torch.cuda.is_initialized()
    preceding = preceding_review(review_path, review_sha256)
    if device == "cpu":
        assert not torch.cuda.is_available(), "Set CUDA_VISIBLE_DEVICES='' for CPU checks"
    else:
        assert torch.cuda.is_available()
    assert psutil.virtual_memory().available / 1e9 > 24 and sha(PARENT) == PARENT_SHA
    cfg = yaml.safe_load(Path(config_path).read_text())
    control = yaml.safe_load(Path(control_path).read_text())
    excluded = {"run", "experiment_notes", "multiscale_sensor_weight"}
    assert {k: v for k, v in cfg.items() if k not in excluded} == {
        k: v for k, v in control.items() if k not in excluded
    }
    assert 0 < weight <= 0.01
    assert (
        cfg["multiscale_sensor_weight"] == weight
        and control.get("multiscale_sensor_weight", 0) == 0
    )
    assert cfg["flat_chroma_stops"] == 8 and cfg["steps"] == 4000
    assert cfg["batch_size"] == 16 and cfg["patch_size"] == 256 and cfg["seed"] == 48
    assert all(
        not cfg.get(key, False)
        for key in ["refiner_only", "coarse_refiner_only", "pyramid_refiner_only"]
    )
    source = {str(path): sha(path) for path in Path("src/demosaic").glob("*.py")}
    frozen = json.loads(
        (BASE / "benchmarks/wide-flat-palette-full4k-workflow-v1/plan.json").read_text()
    )
    assert {Path(k).name: v for k, v in source.items()} == {
        Path(k).name: v for k, v in frozen["source_files"].items()
    }
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    assert shutil.disk_usage(output).free > 512 * 1024**3
    archive = output / "source"
    archive.mkdir()
    scripts = [
        Path(__file__),
        *[
            Path(__file__).with_name(name)
            for name in [
                "audit_flat_palette.py",
                "preflight_flat_palette_cuda.py",
                "preflight_dino_pyramid_cuda.py",
                "preflight_paired_extension.py",
            ]
        ],
    ]
    for path in [
        *Path("src/demosaic").glob("*.py"),
        *scripts,
        Path(config_path),
        Path(control_path),
    ]:
        (archive / path.name).write_bytes(path.read_bytes())
    manifests = {
        key: {"path": cfg[key], "sha256": sha(cfg[key])}
        for key in ["manifest", "validation_manifest", "paired_manifest", "raw_clean_manifest"]
    }
    template = {
        **cfg,
        "device": device,
        "workers": 0,
        "paired_workers": 0,
        "raw_clean_workers": 0,
        "log_every": 1,
        "checkpoint_every": 4,
        "flat_fraction": 1,
        "synthetic_fraction": 0,
        "cpu_threads": 2 if device == "cpu" else 4,
    }
    if device == "cpu":
        template.update(batch_size=1, patch_size=64, amp=False, precision="float32")
    configs = [("control", 0, False), ("loss-resumed", weight, True)]
    if device == "cpu":
        configs.insert(1, ("loss-full", weight, False))
    runs, checkpoints, portable = {}, {}, None
    path = output / "fixture-config.yaml"
    for label, arm_weight, resume in configs:
        run_config = {**template, "run": str(output / label), "multiscale_sensor_weight": arm_weight}
        path.write_text(yaml.safe_dump(run_config, sort_keys=False))
        checkpoint = train(path, initialize=PARENT, stop_after=2 if resume else 4)
        if resume:
            step2 = output / (label + "-step2.pt")
            shutil.copyfile(checkpoint, step2)
            state = torch.load(step2, map_location="cpu", weights_only=True, mmap=True)
            assert state["step"] == 2 and len(state["model"]) == len(state["ema"]) == 91
            assert len(state["optimizer"]["state"]) == 89
            if device == "cuda":
                portable = portable_predictions(step2, state, run_config)
            del state
            checkpoint = train(path, resume=step2, stop_after=2)
        state = torch.load(checkpoint, map_location="cpu", weights_only=True, mmap=True)
        assert state["step"] == 4 and state["config"]["steps"] == 4000
        assert state["config"]["initialized_from"]["sha256"] == PARENT_SHA
        assert state["config"]["multiscale_sensor_weight"] == arm_weight
        assert (
            len(state["model"]) == len(state["ema"]) == 91
            and len(state["optimizer"]["state"]) == 89
        )
        assert {float(v["step"]) for v in state["optimizer"]["state"].values()} == {4.0}
        assert all(
            torch.isfinite(v).all() for field in ["model", "ema"] for v in state[field].values()
        )
        assert all(
            torch.isfinite(v).all()
            for item in state["optimizer"]["state"].values()
            for v in item.values()
            if isinstance(v, torch.Tensor)
        )
        for key, item in manifests.items():
            assert state["config"][key + "_sha256"] == item["sha256"]
        runs[label] = train_rows(output / label)
        checkpoints[label] = {"path": str(checkpoint), "sha256": sha(checkpoint)}
        assert len(runs[label]) == 4
        assert [r["domain"] for r in runs[label]] == [
            "synthetic",
            "synthetic",
            "native-RAW-synthetic",
            "paired-RAW",
        ]
        assert all(math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"]) for r in runs[label])
        if arm_weight:
            assert any(r["multiscale_sensor"] > 0 for r in runs[label])
            assert all(
                math.isfinite(r["multiscale_sensor"]) and r["multiscale_sensor"] >= 0
                for r in runs[label]
            )
        del state
        gc.collect()
        if device == "cuda":
            torch.cuda.empty_cache()
    for label, rows in runs.items():
        assert all(
            a["batch_sha256"] == b["batch_sha256"]
            for a, b in zip(rows, runs["control"], strict=True)
        ), label
    exact_fields = []
    if device == "cpu":
        full, resumed = [
            torch.load(checkpoints[name]["path"], map_location="cpu", weights_only=True, mmap=True)
            for name in ["loss-full", "loss-resumed"]
        ]
        exact_fields = [
            "model_config",
            "model",
            "ema",
            "optimizer",
            "python_rng",
            "torch_rng",
            "cuda_rng",
            "best",
            "step",
        ]
        for field in exact_fields:
            identical(full[field], resumed[field])
        for a, b in zip(runs["loss-full"], runs["loss-resumed"], strict=True):
            identical(
                {k: v for k, v in a.items() if k != "seconds_per_step"},
                {k: v for k, v in b.items() if k != "seconds_per_step"},
            )
        assert not torch.cuda.is_initialized()
    assert source == {str(path): sha(path) for path in Path("src/demosaic").glob("*.py")}
    assert sha(PARENT) == PARENT_SHA
    result = {
        "status": "completed-actual-trainer-sensor-mean-engineering-only",
        "device": device,
        "loss_weight": weight,
        "preceding": preceding,
        "parent": {"path": str(PARENT), "sha256": PARENT_SHA},
        "source_files": source,
        "driver_sha256": sha(__file__),
        "helper_source_files": {str(p): sha(p) for p in scripts[1:]},
        "manifests": manifests,
        "configs": [{"path": str(p), "sha256": sha(p)} for p in [config_path, control_path]],
        "batch_size": template["batch_size"],
        "native_patch": template["patch_size"],
        "planned_steps": 4000,
        "three_domains": True,
        "all_observation_hashes_match_control": True,
        "CPU_uninterrupted_vs_resumed_exact_fields": exact_fields,
        "CUDA_step2_state_restoration_and_portable_EMA": portable,
        "observations": runs,
        "checkpoints": checkpoints,
        "peak_cuda_allocated_bytes": torch.cuda.max_memory_allocated()
        if device == "cuda"
        else None,
        "limitations": "Four discarded updates per arm, forced smooth Commons/workers0. CPU exact restart is separate from CUDA saved-state/portable checks; no deterministic CUDA optimization claim. Full restoration network trains with frozen DINO backbone. No quality, throughput, general color repair or model promotion claim.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                "receipt": str(output / "receipt.json"),
                "device": device,
                "all_domain_input_hashes_match": True,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--control", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--review-sha256", required=True)
    parser.add_argument("--weight", type=float, default=0.01)
    args = parser.parse_args()
    main(
        args.config,
        args.control,
        args.output,
        args.device,
        args.review,
        args.review_sha256,
        args.weight,
    )
