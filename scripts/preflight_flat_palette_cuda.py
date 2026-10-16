"""Prepared actual-trainer CUDA palette check after the reference review exits.

Force smooth Commons draws to exercise the changed branch at native256/batch16.
Check all3domains, complete saved-state restoration and portable EMA predictions.
No trained quality or deterministic CUDA optimization claim follows.
"""

import argparse
import gc
import json
import math
import random
import shutil
from pathlib import Path

import numpy as np
import psutil
import torch
import yaml
from audit_flat_palette import PARENT, PARENT_SHA, sha, train_rows
from preflight_dino_pyramid_cuda import assert_saved_equal

from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.precision import amp_context
from demosaic.safety import writable_path
from demosaic.train import make_optimizer, train

STATUS = Path("/mnt/external/demosaic/runs/nonlocal-reference-full-workflow.json")


def guard(reference_review, review_sha256):
    status = json.loads(STATUS.read_text())
    owner = status["controller"]
    try:
        process = psutil.Process(owner["pid"])
        if (
            abs(process.create_time() - owner["created"]) < 0.01
            and process.status() != psutil.STATUS_ZOMBIE
        ):
            raise RuntimeError(f"Preceding reference workflow still live: PID{process.pid}")
    except psutil.NoSuchProcess:
        pass
    if status["status"] != "completed-reference-evaluation-awaiting-manual-review":
        raise RuntimeError("Preceding reference evaluation is not successfully complete")
    if sha(reference_review) != review_sha256:
        raise ValueError("Completed reference review SHA differs")
    review = json.loads(Path(reference_review).read_text())
    if review["workflow_sha256"] != sha(STATUS) or not review["review_complete"]:
        raise ValueError("Reference publication does not cover the completed workflow/review")
    return {
        "status": status,
        "status_sha256": sha(STATUS),
        "review": str(reference_review),
        "review_sha256": review_sha256,
    }


@torch.inference_mode()
def portable_predictions(prefix, state, cfg):
    """Verify raw training state first, then compare reconstructed/portable EMA."""
    torch.set_num_threads(4)
    model = JointDemosaic(ModelConfig.from_checkpoint(state["model_config"])).to("cuda")
    if cfg["channels_last"]:
        model.to(memory_format=torch.channels_last)
    result = model.load_state_dict(state["model"], strict=False)
    assert not result.unexpected_keys and all(
        k.startswith("context.backbone.") for k in result.missing_keys
    )
    optimizer = make_optimizer(model, state["config"])
    optimizer.load_state_dict(state["optimizer"])
    assert_saved_equal(state["model"], model.restoration_state_dict(), "model")
    assert_saved_equal(state["optimizer"], optimizer.state_dict(), "optimizer")
    ema = {k: v.to("cuda") for k, v in state["ema"].items()}
    assert_saved_equal(state["ema"], ema, "EMA")
    random.setstate(state["python_rng"])
    torch.set_rng_state(state["torch_rng"])
    torch.cuda.set_rng_state_all(state["cuda_rng"])
    assert_saved_equal(state["python_rng"], random.getstate(), "Python RNG")
    assert_saved_equal(state["torch_rng"], torch.get_rng_state(), "Torch RNG")
    assert_saved_equal(state["cuda_rng"], torch.cuda.get_rng_state_all(), "CUDA RNG")
    del optimizer, ema
    model.load_state_dict(state["ema"], strict=False)
    model.eval()
    portable, _ = load_checkpoint(prefix, "cuda")
    portable.eval()
    if cfg["channels_last"]:
        portable.to(memory_format=torch.channels_last)
    plan = Path("/mnt/external/demosaic/evaluation/two-fixed-examples-v43-none10k-cpu-v1")
    rows = []
    for i in range(2):
        source = plan / f"observation-{i}-cpu.npz"
        with np.load(source, allow_pickle=False) as arrays:
            batch = {
                k: torch.from_numpy(arrays[k]).to("cuda")
                for k in ["packed", "variance", "colors", "wb", "matrix"]
            }
        predictions = []
        for candidate in [model, portable]:
            candidate.set_noise(0.00256, 0.0000262144)
            with amp_context("cuda", dtype="float16"):
                x = candidate(
                    batch["packed"],
                    batch["variance"],
                    batch["colors"],
                    batch["wb"],
                    batch["matrix"],
                )
            assert x.shape == (1, 3, 256, 256) and torch.isfinite(x).all()
            predictions.append(x.detach().cpu())
        torch.testing.assert_close(*predictions, rtol=0, atol=0)
        rows.append(
            {
                "input": str(source),
                "input_sha256": sha(source),
                "shape": [1, 3, 256, 256],
                "FP16_portable_EMA_exact": True,
            }
        )
    del model, portable
    gc.collect()
    torch.cuda.empty_cache()
    return rows


def main(output, reference_review, review_sha256):
    preceding = guard(reference_review, review_sha256)
    assert torch.cuda.is_available() and psutil.virtual_memory().available / 1e9 > 24
    assert sha(PARENT) == PARENT_SHA
    cp = Path("configs/dino-convnext-palette-control-b16-v59.yaml")
    wp = Path("configs/dino-convnext-palette-wide-b16-v60.yaml")
    configs = [yaml.safe_load(p.read_text()) for p in [cp, wp]]
    assert {
        k: v
        for k, v in configs[0].items()
        if k not in ["run", "experiment_notes", "flat_chroma_stops"]
    } == {
        k: v
        for k, v in configs[1].items()
        if k not in ["run", "experiment_notes", "flat_chroma_stops"]
    }
    assert [c["flat_chroma_stops"] for c in configs] == [0, 8]
    assert all(
        c["batch_size"] == 16
        and c["patch_size"] == 256
        and c["steps"] == 4000
        and c["warmup_steps"] == 100
        and c["lr"] == 2e-5
        for c in configs
    )
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    assert shutil.disk_usage(output).free / 1e9 > 16
    archive = output / "source"
    archive.mkdir()
    source = {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    helpers = [
        Path(__file__).with_name(name)
        for name in [
            "audit_flat_palette.py",
            "preflight_dino_pyramid_cuda.py",
            "preflight_paired_extension.py",
        ]
    ]
    for p in [*Path("src/demosaic").glob("*.py"), Path(__file__), *helpers, cp, wp]:
        (archive / p.name).write_bytes(p.read_bytes())
    path = output / "gpu-config.yaml"
    checkpoints = {}
    runs = {}
    portable = None
    for name, cfg in zip(["control", "wide"], configs):
        cfg = {
            **cfg,
            "flat_fraction": 1,
            "synthetic_fraction": 0,
            "run": str(output / name),
            "workers": 0,
            "paired_workers": 0,
            "raw_clean_workers": 0,
            "log_every": 1,
            "checkpoint_every": 4,
        }
        path.write_text(yaml.safe_dump(cfg, sort_keys=False))
        if name == "control":
            checkpoints[name] = train(path, initialize=PARENT, stop_after=4)
        else:
            prefix = train(path, initialize=PARENT, stop_after=2)
            copy = output / "wide-step2.pt"
            shutil.copyfile(prefix, copy)
            state = torch.load(copy, map_location="cpu", weights_only=True, mmap=True)
            assert (
                state["step"] == 2
                and len(state["model"]) == len(state["ema"]) == 91
                and len(state["optimizer"]["state"]) == 89
            )
            portable = portable_predictions(copy, state, cfg)
            del state
            checkpoints[name] = train(path, resume=copy, stop_after=2)
        state = torch.load(checkpoints[name], map_location="cpu", weights_only=True, mmap=True)
        assert state["step"] == 4 and state["config"]["initialized_from"]["sha256"] == PARENT_SHA
        assert state["config"]["flat_chroma_stops"] == cfg["flat_chroma_stops"]
        assert all(
            torch.isfinite(v).all() for field in ["model", "ema"] for v in state[field].values()
        )
        assert {float(x["step"]) for x in state["optimizer"]["state"].values()} == {4.0}
        assert all(
            torch.isfinite(v).all()
            for x in state["optimizer"]["state"].values()
            for v in x.values()
            if isinstance(v, torch.Tensor)
        )
        runs[name] = train_rows(output / name)
        assert len(runs[name]) == 4 and all(
            math.isfinite(r["loss"]) and math.isfinite(r["grad_norm"]) for r in runs[name]
        )
        assert [r["domain"] for r in runs[name]] == [
            "synthetic",
            "synthetic",
            "native-RAW-synthetic",
            "paired-RAW",
        ]
        del state
        gc.collect()
        torch.cuda.empty_cache()
    matches = [
        a["batch_sha256"] == b["batch_sha256"] for a, b in zip(runs["control"], runs["wide"])
    ]
    assert matches[2:] == [True, True] and not matches[0]
    assert source == {str(p): sha(p) for p in Path("src/demosaic").glob("*.py")}
    assert sha(PARENT) == PARENT_SHA
    receipt = {
        "status": "completed-genuine-parent-palette-actual-trainer-CUDA-engineering-only",
        "preceding": preceding,
        "parent": {"path": str(PARENT), "sha256": PARENT_SHA},
        "source_files": source,
        "driver_sha256": sha(__file__),
        "helper_source_files": {str(p): sha(p) for p in helpers},
        "configs": [{"path": str(p), "sha256": sha(p)} for p in [cp, wp]],
        "native_patch": 256,
        "batch_size": 16,
        "forced_smooth_Commons_fraction": 1,
        "three_domains": True,
        "observations": runs,
        "control_wide_perstep_hash_equal": matches,
        "complete_step2_model_EMA_AdamW_RNG_restore_exact": True,
        "portable_EMA_predictions": portable,
        "checkpoints": {k: {"path": str(p), "sha256": sha(p)} for k, p in checkpoints.items()},
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "torch": str(torch.__version__),
        "limitations": "Discarded engineering fixture forces smooth Commons samples, disables data workers and uses4updates. No trained quality/throughput claim or bitwise-equal CUDA optimization after restart. CPU four-vs2+2 complete equivalence is separate. Full production fractions/workers and representative quality must still be trained/evaluated.",
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(
        json.dumps({"status": receipt["status"], "receipt": str(output / "receipt.json")}),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--reference-review", type=Path, required=True)
    parser.add_argument("--reference-review-sha256", required=True)
    args = parser.parse_args()
    main(args.output, args.reference_review, args.reference_review_sha256)
