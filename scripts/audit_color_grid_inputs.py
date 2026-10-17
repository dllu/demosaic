"""Independently check every frozen hue-grid observation without inference."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from prepare_color_grid import sha, validate

from demosaic.safety import writable_path
from demosaic.suite import observation

PHASES = {"RGGB": [0, 1, 1, 2], "BGGR": [2, 1, 1, 0], "GRBG": [1, 0, 2, 1], "GBRG": [1, 2, 0, 1]}
SHAPES = {
    "packed": (1, 4, 128, 128),
    "variance": (1, 4, 128, 128),
    "colors": (1, 4),
    "wb": (1, 3),
    "matrix": (1, 3, 3),
    "target": (1, 3, 256, 256),
}


@torch.inference_mode()
def main(inputs, output):
    torch.set_num_threads(2)
    assert not torch.cuda.is_initialized()
    plan = json.loads(Path(inputs).read_text())
    validate(plan)
    root = Path(inputs).parent
    assert sha(root / "source/prepare_color_grid.py") == plan["driver_sha256"]
    assert sha(root / "source/evaluation.yaml") == plan["protocol_sha256"]
    for name, digest in plan["source_files"].items():
        assert sha(root / "source" / Path(name).name) == digest
    output = writable_path(output)
    if output.exists():
        raise ValueError("Audit exists; choose another output")
    maximum_color_difference = 0.0
    maximum_variance_difference = 0.0
    adc_exact = 0
    replays = 0
    saturated = 0
    negative = 0
    bytes_checked = 0
    files = []
    preview_ids = {plan["cases"][i]["id"] for i in plan["native_preview_cases"]}
    for i, c in enumerate(plan["cases"]):
        p = Path(c["arrays"])
        assert sha(p) == c["sha256"]
        bytes_checked += p.stat().st_size
        with np.load(p, allow_pickle=False) as values:
            batch = {k: v.copy() for k, v in values.items()}
        assert batch.keys() == SHAPES.keys()
        for k, v in batch.items():
            assert (
                v.shape == SHAPES[k]
                and v.dtype == (np.int64 if k == "colors" else np.float32)
                and np.isfinite(v).all()
            )
        np.testing.assert_array_equal(batch["colors"][0], PHASES[c["pattern"]])
        np.testing.assert_array_equal(batch["wb"][0], np.asarray(plan["white_balance"], np.float32))
        np.testing.assert_array_equal(
            batch["matrix"][0], np.asarray(plan["camera_to_srgb"], np.float32)
        )
        rgb = np.asarray(c["source"]["linear_srgb"], np.float32).astype(np.float64)
        expected = (
            np.linalg.inv(batch["matrix"][0].astype(np.float64))
            @ rgb
            / batch["wb"][0].astype(np.float64)
        )
        target = batch["target"]
        np.testing.assert_array_equal(target, np.broadcast_to(target[..., :1, :1], target.shape))
        assert target.min() > 0 and target.max() < 1
        delta = float(np.max(np.abs(expected - target[0, :, 0, 0].astype(np.float64))))
        maximum_color_difference = max(maximum_color_difference, delta)
        assert delta < 2e-7
        np.testing.assert_array_equal(
            target[0, :, 0, 0], np.asarray(c["target_camera_RGB"], np.float32)
        )
        condition = c["condition"]
        expected_variance = (
            np.maximum(batch["packed"].astype(np.float64), 0) * condition["shot"]
            + condition["read"]
        )
        dv = float(np.max(np.abs(batch["variance"].astype(np.float64) - expected_variance)))
        maximum_variance_difference = max(maximum_variance_difference, dv)
        np.testing.assert_allclose(
            batch["variance"], expected_variance, rtol=3 * np.finfo(np.float32).eps, atol=1e-14
        )
        black = np.float32(0.03)
        scale = np.float32(1) - black
        levels = np.float32(65535)
        if condition["name"] == "adc-only":
            camera = np.stack(
                [
                    target[:, channel, dy::2, dx::2]
                    for channel, (dy, dx) in zip(
                        PHASES[c["pattern"]], [(0, 0), (0, 1), (1, 0), (1, 1)]
                    )
                ],
                axis=1,
            )
            expected_ADC = (
                np.rint(np.clip(camera * scale + black, 0, 1) * levels) / levels - black
            ) / scale
            np.testing.assert_array_equal(batch["packed"], expected_ADC)
            adc_exact += 1
        if c["id"] in preview_ids and condition["name"] == "iso12800-prior":
            clean = (
                torch.tensor(c["source"]["linear_srgb"], dtype=torch.float32)[None, :, None, None]
                .expand(1, 3, 256, 256)
                .clone()
            )
            regenerated = observation(
                clean,
                [c["id"]],
                condition,
                c["pattern"],
                plan["white_balance"],
                plan["camera_to_srgb"],
                plan["seed"],
            )
            for k, v in regenerated.items():
                np.testing.assert_array_equal(v.numpy(), batch[k])
            replays += 1
        saturated += int(np.count_nonzero(batch["packed"] >= 1))
        negative += int(np.count_nonzero(batch["packed"] < 0))
        files.append(
            {
                "path": str(p),
                "sha256": c["sha256"],
                "shape_dtype_finite_phase_WB_matrix_target_variance_checked": True,
            }
        )
    assert len(files) == 1176 and adc_exact == 588 and replays == 12
    result = {
        "status": "completed-independent-color-grid-input-audit",
        "plan": str(inputs),
        "plan_sha256": sha(inputs),
        "observations": 1176,
        "sources": 147,
        "all_observation_bytes_checked": bytes_checked,
        "all_shapes_dtypes_values_phases_WB_matrix_and_constant_targets_verified": True,
        "maximum_numpy64_inverse_camera_target_difference": maximum_color_difference,
        "maximum_numpy64_variance_formula_difference": maximum_variance_difference,
        "ADC_only_quantization_bit_exact_cases": adc_exact,
        "high_noise_preview_cases_reproduced_bit_exact": replays,
        "clipping_scope": "Clean RGB/camera targets are strictly inside white. Noisy ADC samples can still clip; the plan scope no-clipping phrase refers to clean targets, not observations.",
        "saturated_noisy_ADC_samples": saturated,
        "negative_black_subtracted_noisy_samples": negative,
        "files": files,
        "driver_sha256": sha(__file__),
        "CUDA_initialized": False,
        "limitations": "One fixed WB/matrix and one observation per grid case. NumPy64 independently checks target/variance/ADC math; seeded noisy replay uses the archived-compatible observation implementation. No model inference, quality result or real-photo generalization.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {k: v for k, v in result.items() if k not in ["files", "limitations", "clipping_scope"]}
        ),
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--inputs", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    main(a.inputs, a.output)
