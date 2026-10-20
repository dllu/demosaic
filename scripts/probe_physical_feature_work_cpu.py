"""CPU model/autograd parity for building anchored physical channels directly."""

import argparse
import hashlib
import importlib.util
import os
from pathlib import Path

import numpy as np
import torch
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import read, ref, save

import demosaic.pretrained_rgb as physical
from demosaic.cfa import PATTERNS, color_indices
from demosaic.inference import load_checkpoint
from demosaic.precision import ieee_fp32
from demosaic.safety import writable_path

REPO = Path(__file__).resolve().parents[1]


def gradient_hashes(model):
    result = {}
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            assert parameter.grad is not None and torch.isfinite(parameter.grad).all(), name
            data = parameter.grad.detach().numpy().tobytes(order="C")
            result[name] = {
                "elements": parameter.numel(),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        else:
            assert parameter.grad is None
    return result


def main(output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == "" and not torch.cuda.is_initialized()
    torch.set_num_threads(2)
    root = writable_path(output).resolve()
    root.mkdir(parents=True, exist_ok=False)
    legacy_path = REPO / "tests/fixtures/physical_features_before_elimination.py"
    spec = importlib.util.spec_from_file_location("physical_legacy", legacy_path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    checkpoint_path = Path(
        "/mnt/external/demosaic/models/dino-convnext-wide-long-control-b16-v63-step20000.pt"
    )
    assert ref(checkpoint_path)["sha256"] == (
        "ed70952dd33c5d7da39199bf1306b58b579862920fb0cccd6b222f19871bc9b5"
    )
    fixture_path = Path(
        "/mnt/external/demosaic/benchmarks/packed-isotropic-compilation-inputs-v1/inputs.json"
    )
    fixture = read(fixture_path)
    observation = fixture["serving_probes"][0]["observation"]
    assert ref(observation["path"]) == observation
    with np.load(observation["path"], allow_pickle=False) as data:
        inputs = {
            k: torch.from_numpy(data[k].copy())
            for k in ["packed", "variance", "colors", "wb", "matrix"]
        }
    for key in ["packed", "variance"]:
        inputs[key] = inputs[key][..., 112:144, 108:148].contiguous()
    model, checkpoint = load_checkpoint(checkpoint_path, "cpu")
    del checkpoint
    model.eval().set_noise(fixture["conditioning"]["shot"], fixture["conditioning"]["read"])
    before = model_hash(model)
    rng = torch.get_rng_state().clone()
    current = physical.physical_rgb_features
    functions = {"original": legacy.original_anchored_features, "candidate": current}
    outputs = {}
    gradients = {}
    try:
        for name, function in functions.items():
            physical.physical_rgb_features = function
            with torch.inference_mode(), ieee_fp32():
                result = model(
                    *(inputs[k] for k in ["packed", "variance", "colors", "wb", "matrix"])
                )
            assert result.shape == (4, 3, 64, 80) and torch.isfinite(result).all()
            np.save(root / f"{name}-GFX-RGB-f32.npy", result.numpy(), allow_pickle=False)
            outputs[name] = ref(root / f"{name}-GFX-RGB-f32.npy")
        assert outputs["original"]["sha256"] == outputs["candidate"]["sha256"]
        # Derivatives use only deterministic nonphotographic fields. GFX and
        # its reference never participate in an objective, backward or update.
        raw = torch.linspace(-0.02, 1.2, 4 * 4 * 32 * 32).reshape(4, 4, 32, 32)
        shot, read_noise = fixture["conditioning"]["shot"], fixture["conditioning"]["read"]
        synthetic = [
            raw,
            raw.clamp_min(0) * shot + read_noise,
            torch.stack([color_indices(p) for p in PATTERNS]),
            inputs["wb"],
            inputs["matrix"],
        ]
        synthetic_outputs = {}
        for name, function in functions.items():
            physical.physical_rgb_features = function
            model.zero_grad(set_to_none=True)
            with ieee_fp32():
                prediction = model(*synthetic)
                prediction.square().mean().backward()
            gradients[name] = gradient_hashes(model)
            np.save(
                root / f"{name}-synthetic-RGB-f32.npy",
                prediction.detach().numpy(),
                allow_pickle=False,
            )
            synthetic_outputs[name] = ref(root / f"{name}-synthetic-RGB-f32.npy")
        assert gradients["original"] == gradients["candidate"] and len(gradients["candidate"]) == 89
        assert synthetic_outputs["original"]["sha256"] == synthetic_outputs["candidate"]["sha256"]
    finally:
        physical.physical_rgb_features = current
        model.zero_grad(set_to_none=True)
    assert before == model_hash(model) and torch.equal(rng, torch.get_rng_state())
    assert not torch.cuda.is_initialized()
    save(root / "gradient-hashes.json", gradients)
    result = {
        "status": "completed-V63-physical-feature-CPU-byte-and-synthetic-autograd-parity",
        "driver": ref(__file__),
        "candidate_source": ref(REPO / "src/demosaic/pretrained_rgb.py"),
        "common_inverse_source": ref(REPO / "src/demosaic/vst.py"),
        "legacy_fixture": ref(legacy_path),
        "checkpoint": ref(checkpoint_path),
        "fixture": ref(fixture_path),
        "observation": observation,
        "relative_native_xywh": [216, 224, 80, 64],
        "conditioning": fixture["conditioning"],
        "GFX_values_compared": 61440,
        "GFX_output_files": outputs,
        "synthetic_native_size": [64, 64],
        "synthetic_CFA_patterns": list(PATTERNS),
        "synthetic_values_compared": prediction.numel(),
        "synthetic_output_files": synthetic_outputs,
        "all89_trainable_parameter_gradient_bytes_exact": True,
        "trainable_gradient_elements": sum(v["elements"] for v in gradients["candidate"].values()),
        "gradient_hashes": ref(root / "gradient-hashes.json"),
        "all_model_output_bytes_exact": True,
        "weights_and_RNG_unchanged": True,
        "model_sha256": before,
        "CUDA_initialized": False,
        "scope": "CPU implementation parity with genuine V63 weights. Real cached GFX contexts are forward-only, without reference or objective. Eval-mode autograd uses deterministic synthetic all-CFA fields, no GT, optimizer or update. Both policies share the previously verified inverse cleanup. No CUDA timing, training-speed, broad quality, manual-view or full100MP claim; active training/review keep original frozen source.",
    }
    save(root / "receipt.json", result)
    print(
        {
            "receipt": ref(root / "receipt.json"),
            "parameter_gradients_exact": len(gradients["candidate"]),
        }
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    main(args.output)
