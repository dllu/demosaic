"""Discarded CPU engineering checks for the optional RAW reconstruction head.

Archive the candidate package before imports. Compare actual legacy/default-off
photo inference, genuine-parent initialization, then four vs two-plus-two actual
training updates. No GPU, protected RAW, output fitting or trained-quality claim.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import psutil

REPO = Path("/home/dllu/proj/demosaic")
BASE = Path("/mnt/external/demosaic")
PARENT = BASE / "models/dino-convnext-palette-wide-b16-v60-step4000.pt"
PARENT_SHA = "1e9812afcfaa5322593c9d2c2314fa0d8ae5458c4e116be0f516c992c880b47e"
OBSERVATIONS = BASE / "evaluation/two-fixed-examples-v43-none10k-cpu-v1"


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def identical(a, b):
    import torch

    if isinstance(a, torch.Tensor):
        assert torch.equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            identical(a[key], b[key])
    elif isinstance(a, (tuple, list)):
        assert type(a) is type(b) and len(a) == len(b)
        for x, y in zip(a, b, strict=True):
            identical(x, y)
    else:
        assert a == b


def worker(mode, package, output):
    import gc
    import math

    import numpy as np
    import torch
    import yaml

    from demosaic.cfa import bilinear
    from demosaic.inference import load_checkpoint
    from demosaic.model import JointDemosaic, ModelConfig
    from demosaic.train import train

    assert Path(sys.modules["demosaic.model"].__file__).resolve() == package / "demosaic/model.py"
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    if mode in ["legacy", "default-off"]:
        model, _ = load_checkpoint(PARENT, "cpu")
        model.eval()
        records = []
        for case in range(3):
            source = OBSERVATIONS / f"observation-{min(case, 1)}-cpu.npz"
            with np.load(source, allow_pickle=False) as values:
                batch = {
                    k: torch.from_numpy(values[k].copy())
                    for k in ["packed", "variance", "colors", "wb", "matrix"]
                }
            if case == 2:
                for key in ["packed", "variance"]:
                    batch[key] = batch[key][..., :63, :79]
            model.set_noise(0.00256, 0.0000262144)
            with torch.inference_mode():
                result = model(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                ).numpy()
            path = output / f"{mode}-photo-{case}-f32.npy"
            np.save(path, result, allow_pickle=False)
            records.append(
                {
                    "path": str(path),
                    "sha256": sha(path),
                    "source": str(source),
                    "source_sha256": sha(source),
                    "shape": list(result.shape),
                    "ROI_variant": "packed63x79" if case == 2 else "original256",
                }
            )
        result = {
            "source": str(package),
            "cases": records,
            "CUDA_initialized": torch.cuda.is_initialized(),
        }
    else:
        template = yaml.safe_load(
            (REPO / "configs/dino-convnext-wide-long-control-b16-v63.yaml").read_text()
        )
        options = {
            **template["model"],
            "raw_kernel_reconstruction": True,
            "raw_kernel_windows": [1, 5, 17],
        }
        parent = torch.load(PARENT, map_location="cpu", weights_only=True, mmap=True)
        model = JointDemosaic(ModelConfig(**options))
        missing = model.load_state_dict(parent["ema"], strict=False)
        assert not missing.unexpected_keys
        extra = sorted(k for k in missing.missing_keys if not k.startswith("context.backbone."))
        assert extra == [
            "pretrained_rgb.raw_kernel.coefficients.bias",
            "pretrained_rgb.raw_kernel.coefficients.weight",
        ]
        for key, value in parent["ema"].items():
            identical(model.restoration_state_dict()[key], value)
        assert all(not p.requires_grad for p in model.context.backbone.parameters())
        with np.load(OBSERVATIONS / "observation-0-cpu.npz", allow_pickle=False) as values:
            sample = {
                k: torch.from_numpy(values[k].copy())
                for k in ["packed", "variance", "colors", "wb", "matrix"]
            }
        model.eval().set_noise(0.00256, 0.0000262144)
        with torch.inference_mode():
            initial = model(
                sample["packed"],
                sample["variance"],
                sample["colors"],
                sample["wb"],
                sample["matrix"],
            )
        identical(initial, bilinear(sample["packed"], sample["colors"]))
        del model, parent
        gc.collect()
        template.update(
            model=options,
            device="cpu",
            batch_size=1,
            patch_size=64,
            workers=0,
            raw_clean_workers=0,
            paired_workers=0,
            amp=False,
            precision="float32",
            cpu_threads=2,
            seed=48,
            flat_fraction=1,
            synthetic_fraction=0,
            log_every=1,
            checkpoint_every=4,
            val_batches=1,
            validation_images=2,
            validation_protocol=str(REPO / "configs/evaluation.yaml"),
        )
        checkpoints, logs = {}, {}
        for label, split in [("full", False), ("resumed", True)]:
            cfg = {**template, "run": str(output / label)}
            config_path = output / f"{label}-fixture.yaml"
            config_path.write_text(yaml.safe_dump(cfg, sort_keys=False))
            checkpoint = train(config_path, initialize=PARENT, stop_after=2 if split else 4)
            if split:
                frozen = output / "resumed-step2.pt"
                shutil.copyfile(checkpoint, frozen)
                checkpoint = train(config_path, resume=frozen, stop_after=2)
            checkpoints[label] = {"path": str(checkpoint), "sha256": sha(checkpoint)}
            logs[label] = [
                r
                for line in (output / label / "metrics.jsonl").read_text().splitlines()
                if (r := json.loads(line))["event"] == "train"
            ]
            assert [r["domain"] for r in logs[label]] == [
                "synthetic",
                "synthetic",
                "native-RAW-synthetic",
                "paired-RAW",
            ]
            assert all(math.isfinite(r[k]) for r in logs[label] for k in ["loss", "grad_norm"])
        full, resumed = [
            torch.load(checkpoints[k]["path"], map_location="cpu", weights_only=True, mmap=True)
            for k in ["full", "resumed"]
        ]
        fields = [
            "model_config",
            "model",
            "ema",
            "optimizer",
            "python_rng",
            "torch_rng",
            "cuda_rng",
            "step",
        ]
        for field in fields:
            identical(full[field], resumed[field])
        if full["best"] == resumed["best"]:
            fields.append("best")
        for a, b in zip(logs["full"], logs["resumed"], strict=True):
            identical(
                {k: v for k, v in a.items() if k != "seconds_per_step"},
                {k: v for k, v in b.items() if k != "seconds_per_step"},
            )
        assert full["step"] == 4 and full["config"]["steps"] == 20000
        assert full["config"]["initialized_from"]["sha256"] == PARENT_SHA
        assert all(torch.isfinite(v).all() for key in ["model", "ema"] for v in full[key].values())
        assert all(
            torch.isfinite(v).all()
            for state in full["optimizer"]["state"].values()
            for v in state.values()
            if isinstance(v, torch.Tensor)
        )
        assert {int(v["step"]) for v in full["optimizer"]["state"].values()} == {4}
        result = {
            "genuine_parent_all_existing_EMA_tensors_exact_at_initialization": True,
            "only_new_parameter_names": extra,
            "initial_output_exact_bilinear_not_parent_quality": True,
            "DINO_backbone_frozen": True,
            "exact_CPU_restart_fields": fields,
            "best_values": [full["best"], resumed["best"]],
            "all_numeric_logs_and_input_hashes_exact": True,
            "all_model_EMA_AdamW_finite": True,
            "state_counts": {
                "model": len(full["model"]),
                "EMA": len(full["ema"]),
                "AdamW": len(full["optimizer"]["state"]),
            },
            "checkpoints": checkpoints,
            "training": logs,
            "new_source_sha256": full["config"]["source_sha256"],
            "CUDA_initialized": torch.cuda.is_initialized(),
            "scope": "Four discarded native64/B1/FP32 updates per path, forced smooth Commons/workers0/val2images. Not production throughput, convergence, quality or deterministic CUDA training. Extra midpoint validation can affect best-selection metadata.",
        }
    (output / f"{mode}-result.json").write_text(json.dumps(result, indent=2) + "\n")


def main(output):
    import numpy as np

    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    assert not output.exists() and psutil.virtual_memory().available / 1e9 > 24
    assert sha(PARENT) == PARENT_SHA
    output.mkdir(parents=True)
    snapshot = output / "source"
    package = snapshot / "src/demosaic"
    package.mkdir(parents=True)
    source = {str(p): sha(p) for p in (REPO / "src/demosaic").glob("*.py")}
    for path in (REPO / "src/demosaic").glob("*.py"):
        (package / path.name).write_bytes(path.read_bytes())
    for name in [
        "pyproject.toml",
        "uv.lock",
        "third_party/gaussian/Noise2VST-LICENSE",
        "third_party/gaussian/KAIR-LICENSE",
        "third_party/dinov3/LICENSE.md",
    ]:
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes((REPO / name).read_bytes())
    operator = output / Path(__file__).name
    operator.write_bytes(Path(__file__).read_bytes())
    for mode, source_root in [
        ("legacy", REPO / ".cache/wide-flat-palette-worktree/src"),
        ("default-off", snapshot / "src"),
        ("train", snapshot / "src"),
    ]:
        with (output / f"{mode}.log").open("w") as log:
            subprocess.run(
                [
                    sys.executable,
                    str(operator),
                    "--worker",
                    mode,
                    "--package",
                    str(source_root),
                    "--output",
                    str(output),
                ],
                cwd=REPO,
                env={
                    **os.environ,
                    "PYTHONPATH": str(source_root),
                    "HF_HUB_OFFLINE": "1",
                    "OMP_NUM_THREADS": "2",
                },
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
    legacy, current = [read(output / (m + "-result.json")) for m in ["legacy", "default-off"]]
    for old, new in zip(legacy["cases"], current["cases"], strict=True):
        assert np.array_equal(
            np.load(old["path"], allow_pickle=False), np.load(new["path"], allow_pickle=False)
        )
    assert all(sha(p) == h for p, h in source.items())
    result = {
        "status": "completed-CPU-engineering-only-RAW-kernel-prototype",
        "parent": {"path": str(PARENT), "sha256": PARENT_SHA},
        "source_files": source,
        "default_off_actual_legacy_three_photo_cases_exact": True,
        "legacy": legacy,
        "default_off": current,
        "enabled_training": read(output / "train-result.json"),
        "driver_sha256": sha(__file__),
        "scope": "Actual frozen legacy vs archived candidate CPU inference, including odd dimensions, then genuine parent initialization and actual CPU restart. No GPU, trained-quality result, output calibration or live-recipe change.",
    }
    (output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"receipt": str(output / "receipt.json")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--worker", choices=["legacy", "default-off", "train"])
    parser.add_argument("--package", type=Path)
    args = parser.parse_args()
    if args.worker:
        worker(args.worker, args.package, args.output)
    else:
        main(args.output)
