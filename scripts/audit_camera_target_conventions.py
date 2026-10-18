"""Exact noiseless RAW-head and camera/reference-white compatibility oracles."""

import argparse
import json
from pathlib import Path

import torch
from probe_saved_cfa_gain_grid import ref

from demosaic.cfa import PATTERNS, mosaic
from demosaic.data import camera_pair
from demosaic.raw_kernel import AdaptiveRawKernel
from demosaic.safety import writable_path


def reference_white_projection(prediction, wb, matrix):
    """Diagnostic only: canonical reference mapping, not a proposed RAW output."""
    linear = torch.einsum("bij,bjhw->bihw", matrix, prediction * wb[..., None, None])
    difference = linear.clamp(0, 1) - linear
    return (
        prediction
        + torch.einsum("bij,bjhw->bihw", torch.linalg.inv(matrix), difference) / wb[..., None, None]
    )


def cases():
    torch.set_num_threads(2)
    generator = torch.Generator().manual_seed(20261018)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(20261018)
        head = AdaptiveRawKernel(67, phase_conditioning=True)
        with torch.no_grad():
            for parameter in head.parameters():
                parameter.normal_(0, 0.2)
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    matrix = torch.tensor(
        [
            [
                [1.117647, -0.0588235, -0.0588235],
                [-0.0588235, 1.117647, -0.0588235],
                [-0.0588235, -0.0588235, 1.117647],
            ]
        ]
    )
    rows = []
    for name, color in [
        ("below-reference-white", [0.3, 0.2, 0.1]),
        ("reference-white-only-clipped", [1.4, 0.4, 0.2]),
        ("reference-white-and-sensor-clipped", [3.6, 1.8, 0.9]),
    ]:
        scene = torch.tensor(color)[None, :, None, None].expand(1, 3, 32, 32)
        clean, reference = camera_pair(
            scene, torch.linalg.inv(matrix), wb, reconstruct_highlights=True
        )
        for pattern, labels in PATTERNS.items():
            colors = torch.tensor(labels)[None]
            packed = mosaic(clean.clamp(0, 1), colors)
            features = torch.randn((1, 67, 32, 32), generator=generator, requires_grad=True)
            head.zero_grad(set_to_none=True)
            prediction = head(packed, colors, features)
            ref_error = (prediction - reference).square().mean()
            ref_error.backward()
            gradient = max(float(p.grad.abs().max()) for p in head.parameters())
            assert gradient == 0.0 and float(features.grad.abs().max()) == 0.0
            projected = reference_white_projection(prediction.detach(), wb, matrix)
            target_cfa = mosaic(clean, colors)
            valid = (target_cfa >= 0) & (target_cfa < 0.98)

            def sensor_mse(value, colors=colors, target_cfa=target_cfa, valid=valid):
                delta = (mosaic(value, colors) - target_cfa).double().square()
                return float(delta[valid].mean()) if valid.any() else None

            rows.append(
                {
                    "case": name,
                    "pattern": pattern,
                    "scene_linear_sRGB": color,
                    "clean_camera_RGB": clean[0, :, 0, 0].tolist(),
                    "reference_white_camera_RGB": reference[0, :, 0, 0].tolist(),
                    "sensor_samples_are_unclipped": bool(((clean >= 0) & (clean < 1)).all()),
                    "raw_head_reference_white_MSE": float(ref_error.detach()),
                    "projected_head_reference_white_MSE": float(
                        (projected - reference).double().square().mean()
                    ),
                    "raw_head_valid_sensor_MSE": sensor_mse(prediction.detach()),
                    "projected_head_valid_sensor_MSE": sensor_mse(projected),
                    "valid_sensor_samples": int(valid.sum()),
                    "maximum_trainable_head_gradient": gradient,
                    "maximum_feature_gradient": float(features.grad.abs().max()),
                }
            )
    return rows


def main(output):
    assert not torch.cuda.is_initialized()
    output = writable_path(output)
    output.mkdir(parents=True, exist_ok=False)
    paths = [
        Path(__file__),
        *map(
            Path,
            [
                "src/demosaic/raw_kernel.py",
                "src/demosaic/cfa.py",
                "src/demosaic/data.py",
                "src/demosaic/precision.py",
            ],
        ),
    ]
    (output / "source").mkdir()
    for path in paths:
        (output / "source" / path.name).write_bytes(path.read_bytes())
    rows = cases()
    for row in rows:
        if row["case"] == "reference-white-only-clipped":
            assert row["sensor_samples_are_unclipped"]
            assert row["raw_head_reference_white_MSE"] > 1e-3
            assert row["raw_head_valid_sensor_MSE"] < 2e-14
            assert row["projected_head_reference_white_MSE"] < 2e-14
            assert row["projected_head_valid_sensor_MSE"] > 1e-3
    result = {
        "status": "completed-exact-noiseless-camera-target-convention-audit",
        "source_files": [ref(p) for p in paths],
        "cases": rows,
        "CUDA_initialized": False,
        "scope": "Actual experimental centered-RAW head with arbitrary deterministic coefficients/features, not a trained checkpoint or denoising benchmark. No source image/RAW/noise or model-weight load. The reference-white-only case is sensor-unclipped: the head exactly represents physical camera RGB but cannot match the alternate canonical target, with zero trainable gradients. Projecting solves that canonical case while creating physical measured-CFA error. This does not quantify how much any historical training failure came from this conflict or establish a new trained model.",
    }
    (output / "result.json").write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"status": result["status"], "cases": len(rows)}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    main(parser.parse_args().output)
