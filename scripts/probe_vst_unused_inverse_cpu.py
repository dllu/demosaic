"""Genuine mature-model CPU parity for removing unused inverse arithmetic."""

import argparse
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import torch
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import read, ref, save

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.safety import writable_path
from demosaic.vst import GeneralizedAnscombe

REPO = Path(__file__).resolve().parents[1]


def main(output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    source = REPO / "src/demosaic/vst.py"
    legacy_path = REPO / "tests/fixtures/vst_inverse_before_elimination.py"
    spec = importlib.util.spec_from_file_location("vst_legacy", legacy_path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    parent = Path(
        "/mnt/external/demosaic/models/dino-convnext-wide-long-control-b16-v63-step20000.pt"
    )
    assert (
        ref(parent)["sha256"] == "ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5"
    )
    fixture_path = Path(
        "/mnt/external/demosaic/benchmarks/packed-isotropic-compilation-inputs-v1/inputs.json"
    )
    fixture = read(fixture_path)
    observation = fixture["serving_probes"][0]["observation"]
    assert ref(observation["path"]) == observation
    with np.load(observation["path"], allow_pickle=False) as data:
        inputs = {
            key: torch.from_numpy(data[key].copy())
            for key in ["packed", "variance", "colors", "wb", "matrix"]
        }
    for key in ["packed", "variance"]:
        inputs[key] = inputs[key][..., 112:144, 108:148].contiguous()
    assert inputs["packed"].shape == (4, 4, 32, 40)
    model, checkpoint = load_checkpoint(parent, "cpu")
    del checkpoint
    model.eval()
    model.set_noise(fixture["conditioning"]["shot"], fixture["conditioning"]["read"])
    before = model_hash(model)
    rng = torch.get_rng_state().clone()
    candidate = GeneralizedAnscombe.inverse
    args = [inputs[key] for key in ["packed", "variance", "colors", "wb", "matrix"]]
    try:
        GeneralizedAnscombe.inverse = legacy.inverse_before_elimination
        with torch.inference_mode(), amp_context("cpu", dtype="float32"):
            baseline = model(*args)
        GeneralizedAnscombe.inverse = candidate
        with torch.inference_mode(), amp_context("cpu", dtype="float32"):
            actual = model(*args)
    finally:
        GeneralizedAnscombe.inverse = candidate
    assert (
        actual.shape == (4, 3, 64, 80)
        and actual.dtype == torch.float32
        and torch.isfinite(actual).all()
    )
    assert torch.equal(actual.flatten().view(torch.uint8), baseline.flatten().view(torch.uint8))
    assert before == model_hash(model) and torch.equal(rng, torch.get_rng_state())
    np.save(root / "baseline-RGB-f32.npy", baseline.numpy(), allow_pickle=False)
    np.save(root / "candidate-RGB-f32.npy", actual.numpy(), allow_pickle=False)
    assert (
        ref(root / "baseline-RGB-f32.npy")["sha256"]
        == ref(root / "candidate-RGB-f32.npy")["sha256"]
    )
    receipt = {
        "status": "completed-genuine-V63-CPU-unused-inverse-work-parity-no-speed-or-quality-result",
        "driver": ref(__file__),
        "candidate_source": ref(source),
        "legacy_inverse": ref(legacy_path),
        "original_source_sha256": legacy.SOURCE_SHA256,
        "checkpoint": ref(parent),
        "fixture": ref(fixture_path),
        "observation": observation,
        "relative_native_xywh": [216, 224, 80, 64],
        "conditioning": fixture["conditioning"],
        "values_compared": actual.numel(),
        "all_output_bytes_exact": True,
        "baseline": ref(root / "baseline-RGB-f32.npy"),
        "candidate": ref(root / "candidate-RGB-f32.npy"),
        "unchanged_model_and_RNG": True,
        "model_sha256": before,
        "CUDA_initialized": False,
        "scope": "CPU engineering on four fixed native64x80 contexts cropped from cached GFX inputs. No reference, scoring, training, source-drive access or manual-view claim. Byte identity is not GPU timing, full512 serving-field parity or a100MP speed result. Active training/review retain their archived original source.",
    }
    save(root / "receipt.json", receipt)
    print(json.dumps(ref(root / "receipt.json")))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    a = p.parse_args()
    main(a.output)
