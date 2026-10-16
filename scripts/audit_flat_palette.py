"""CPU legacy-data equivalence and genuine-parent palette restart audit.

The forced-smooth batch1/native64 fixture exercises the new path in four updates
and retains the three real training domains. It is not quality training.
"""

import argparse
import gc
import hashlib
import importlib.util
import json
import math
import os
import random
import shutil
from pathlib import Path

import psutil
import torch
import yaml

from demosaic.data import CleanDataset, smooth_scene
from demosaic.safety import writable_path
from demosaic.train import train, training_domain

BASE = Path("/mnt/external/demosaic")
PARENT = BASE / "models/dino-convnext-pyramid-fresh-b16-v58-step10000.pt"
PARENT_SHA = "cc1fb5e6d3e0d042c95495dd7bf1bd07c900cb6f7e3b61541f78c9e08098fea3"
LEGACY_SHA = "b3277bca23d8c17b365ee364e175ea8a850d45a79cf02686628db606341e7be3"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identical(a, b):
    if isinstance(a, torch.Tensor):
        assert torch.equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a:
            identical(a[k], b[k])
    elif isinstance(a, (tuple, list)):
        assert type(a) is type(b) and len(a) == len(b)
        for x, y in zip(a, b):
            identical(x, y)
    else:
        assert a == b


def train_rows(run):
    return [
        r
        for line in (run / "metrics.jsonl").read_text().splitlines()
        if (r := json.loads(line))["event"] == "train"
    ]


def main(output, legacy_source):
    os.nice(5)
    torch.set_num_threads(2)
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized(), (
        "Use CUDA_VISIBLE_DEVICES=''"
    )
    assert psutil.virtual_memory().available / 1e9 > 24
    assert sha(PARENT) == PARENT_SHA and sha(legacy_source) == LEGACY_SHA
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    assert shutil.disk_usage(output).free / 1e9 > 16
    source_files = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    archive = output / "source"
    archive.mkdir()
    for p in [*Path("src/demosaic").glob("*.py"), Path(__file__)]:
        (archive / p.name).write_bytes(p.read_bytes())
    (archive / "legacy-data.py").write_bytes(Path(legacy_source).read_bytes())
    template = Path("configs/dino-convnext-pyramid-fresh-b16-v58.yaml")
    cfg = yaml.safe_load(template.read_text())
    manifests = {
        key: {"path": cfg[key], "sha256": sha(cfg[key])}
        for key in ["manifest", "validation_manifest", "raw_clean_manifest", "paired_manifest"]
    }
    spec = importlib.util.spec_from_file_location("demosaic._legacy_palette_data", legacy_source)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    coverage = []
    maximum_mean_delta, clipping_changes, neutral = 0, 0, 0
    for i in range(1000):
        seed = 20261016 + i
        a, b, c = [random.Random(seed) for _ in range(3)]
        old = legacy.smooth_scene(4, a)
        default = smooth_scene(4, b)
        wide = smooth_scene(4, c, chroma_stops=8)
        assert torch.equal(old, default) and a.getstate() == b.getstate() == c.getstate()
        gray = torch.equal(old[0], old[1]) and torch.equal(old[1], old[2])
        neutral += gray
        if gray:
            assert torch.equal(old, wide)
        elif wide.max() < 1:
            maximum_mean_delta = max(
                maximum_mean_delta, float((old.mean(0) - wide.mean(0)).abs().max())
            )
        else:
            clipping_changes += 1
        coverage.append(
            {
                "seed": seed,
                "neutral": gray,
                "old_tint_ratio": float(old.mean((1, 2)).max() / old.mean((1, 2)).min()),
                "wide_tint_ratio": float(wide.mean((1, 2)).max() / wide.mean((1, 2)).min()),
            }
        )
    # Real cache rows with production fractions/augmentation, smaller64px CPU fixture.
    options = {
        "patch_size": 64,
        "seed": 48,
        "synthetic_fraction": 0.2,
        "flat_fraction": 0.1,
        "augmentation_downsample": 2,
    }
    old_data, default_data, wide_data = (
        legacy.CleanDataset(cfg["manifest"], **options),
        CleanDataset(cfg["manifest"], **options),
        CleanDataset(cfg["manifest"], **options, flat_chroma_stops=8),
    )
    rows = []
    for index in range(128):
        x, y, z = [data[index]["rgb"] for data in [old_data, default_data, wide_data]]
        assert torch.equal(x, y)
        rng = random.Random(48 + index)
        draw = rng.random()
        if draw < 0.1:
            rng.uniform(-13, -1)
            kind = "neutral" if rng.random() < 0.5 else "colored"
        else:
            kind = "strong" if draw < 0.3 else "photo"
        assert torch.equal(x, z) == (kind != "colored")
        rows.append(
            {
                "index": index,
                "kind": kind,
                "legacy_default_exact": True,
                "wide_equals_default": torch.equal(y, z),
            }
        )
    assert {r["kind"] for r in rows} == {"neutral", "colored", "strong", "photo"}
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
        flat_fraction=1,
        synthetic_fraction=0,
        lr=2e-5,
        steps=10000,
        warmup_steps=100,
    )
    cfg["experiment_notes"] = (
        "Discarded mature-parent CPU engineering fixture. Force all Commons draws smooth to exercise colored branch, native64/batch1/FP32/workers0. All3domains and original10000-plan/100warmup. Not trained quality or production throughput."
    )
    path = output / "cpu-config.yaml"
    checkpoints = {}
    for name, stops, count in [("control4", 0, 4), ("wide4", 8, 4), ("wide-resumed", 8, 2)]:
        cfg.update(run=str(output / name), flat_chroma_stops=stops)
        path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        print(name, flush=True)
        p = train(path, initialize=PARENT, stop_after=count)
        if count == 2:
            prefix = output / "wide-step2.pt"
            shutil.copyfile(p, prefix)
            checkpoints["wide2"] = prefix
            p = train(path, resume=prefix, stop_after=2)
        checkpoints[name] = p
        gc.collect()
    full, resumed = [
        torch.load(checkpoints[k], map_location="cpu", weights_only=True, mmap=True)
        for k in ["wide4", "wide-resumed"]
    ]
    fields = [
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
    for field in fields:
        identical(full[field], resumed[field])
    assert (
        full["config"]["initialized_from"]["sha256"]
        == resumed["config"]["initialized_from"]["sha256"]
        == PARENT_SHA
    )
    assert full["config"]["flat_chroma_stops"] == resumed["config"]["flat_chroma_stops"] == 8
    assert full["step"] == resumed["step"] == 4 and full["config"]["steps"] == 10000
    assert full["cuda_rng"] == []
    assert all(torch.isfinite(t).all() for field in ["model", "ema"] for t in full[field].values())
    assert {float(x["step"]) for x in full["optimizer"]["state"].values()} == {4.0}
    observations = {
        name: train_rows(output / name) for name in ["control4", "wide4", "wide-resumed"]
    }
    for a, b in zip(observations["wide4"], observations["wide-resumed"]):
        identical(
            {k: v for k, v in a.items() if k != "seconds_per_step"},
            {k: v for k, v in b.items() if k != "seconds_per_step"},
        )
    domains = [training_domain(i, 48, 0.25, 0.25) for i in range(1, 5)]
    assert domains == ["commons", "commons", "native", "paired"]
    assert all(
        math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"])
        for run in observations.values()
        for r in run
    )
    batch_match = [
        a["batch_sha256"] == b["batch_sha256"]
        for a, b in zip(observations["control4"], observations["wide4"])
    ]
    assert batch_match == [False, True, True, True], batch_match
    for key, item in manifests.items():
        assert (
            full["config"][key + "_sha256"] == resumed["config"][key + "_sha256"] == item["sha256"]
        )
    assert source_files == {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    assert sha(PARENT) == PARENT_SHA and not torch.cuda.is_initialized()
    receipt = {
        "status": "completed-CPU-legacy-equivalence-and-genuine-mature-parent-restart",
        "parent": {"path": str(PARENT), "sha256": PARENT_SHA},
        "legacy_source": {"path": str(legacy_source), "sha256": LEGACY_SHA},
        "source_files": source_files,
        "driver_sha256": sha(__file__),
        "manifests": manifests,
        "smooth_draws": 1000,
        "legacy_RGB_and_RNG_exact": True,
        "wide_RNG_exact": True,
        "neutral_draws": neutral,
        "neutral_draws_exact": True,
        "max_unclipped_channel_mean_difference": maximum_mean_delta,
        "bright_colored_draws_clipped_after_widening": clipping_changes,
        "palette_coverage": coverage,
        "real_cache_small_patch_checks": rows,
        "genuine_parent_forced_flat_trainer": {
            "updates": 4,
            "resume_after": 2,
            "domain_order": domains,
            "control_wide_batch_hash_equal": batch_match,
            "complete_resumed_fields_exact": fields,
            "model_tensors": len(full["model"]),
            "EMA_tensors": len(full["ema"]),
            "AdamW_states": len(full["optimizer"]["state"]),
            "all_training_values_finite": True,
            "all_optimizer_steps": 4,
            "source_bundle_sha256": full["config"]["source_sha256"],
            "observations": observations,
        },
        "checkpoints": {k: {"path": str(p), "sha256": sha(p)} for k, p in checkpoints.items()},
        "CUDA_initialized": False,
        "limitations": "CPU FP32, batch1/native64, forced Commons smooth fraction1; genuine parent, all3domains and full-state4vs2+2 engineering only. Production256/B16/CUDA behavior and trained quality are unproven. Pre-clamp tint mean preserved, but bright saturation can change final mean. No recipe, weights, corpus or model promoted.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json")}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--legacy-source", required=True, type=Path)
    args = parser.parse_args()
    main(args.output, args.legacy_source)
