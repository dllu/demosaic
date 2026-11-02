"""Replay the actual first mixed batch's output-loss gradients, without neural calls."""

import argparse
import json
import os
import random
from pathlib import Path

import numpy as np
import torch
import yaml
from torch.nn import functional as F
from train_directional_bank_trial import ref, save

from demosaic.color import render
from demosaic.losses import reconstruction_loss

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / ".cache/quality-20261102"


def first_event(path):
    with path.open() as stream:
        return next(
            row
            for row in map(json.loads, stream)
            if row.get("event") == "train" and row["step"] == 1
        )


def manual_gradient_term(prediction, target, wb, matrix, epsilon):
    """Independent NumPy64 divergence, gamma derivative and color-matrix VJP.

    Use the actual CPU-FP32 rendered/linear intermediates, so the check does not
    confuse rounding in those forward arrays with a derivative discrepancy.
    """
    with torch.no_grad():
        display = render(prediction, wb, matrix).numpy()
        truth = render(target, wb, matrix).numpy()
        linear = torch.einsum("bij,bjhw->bihw", matrix, prediction * wb[..., None, None]).numpy()
    gradient = np.zeros(display.shape, dtype=np.float64)
    for axis in (-1, -2):
        # Match the FP32 residual values, then differentiate independently in64bit.
        error = (np.diff(display, axis=axis) - np.diff(truth, axis=axis)).astype(np.float64)
        edge = 0.05 * error / np.sqrt(error**2 + epsilon**2) / error.size
        hi, lo = [slice(None)] * 4, [slice(None)] * 4
        hi[axis], lo[axis] = slice(1, None), slice(None, -1)
        gradient[tuple(hi)] += edge
        gradient[tuple(lo)] -= edge
    x = linear.astype(np.float64).clip(0, 1)
    derivative = np.where(
        x <= 0.0031308, 12.92, (1.055 / 2.4) * np.maximum(x, 1e-10) ** (1 / 2.4 - 1)
    )
    derivative *= (linear >= 0) & (linear <= 1)
    return (
        np.einsum("bij,bihw->bjhw", matrix.numpy().astype(np.float64), gradient * derivative)
        * wb.numpy()[..., None, None]
    )


def run(output):
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    os.nice(10)
    torch.set_num_threads(1)
    output.mkdir(parents=True, exist_ok=False)
    training = ROOT / "V143-crossed-gradient5000-v1"
    config = yaml.safe_load((training / "work/artifacts/train/V143/config.yaml").read_text())
    trained = Path(config["source_snapshot"])
    sources = list((REPO / "src/demosaic").glob("*.py"))
    assert len(sources) == 69 and all(
        p.read_bytes() == (trained / p.name).read_bytes() for p in sources
    )
    inputs = training / "retained/train/V143/step-01.npz"
    outputs = training / "retained/train/V143/first-outputs.npz"
    with np.load(inputs, allow_pickle=False) as archive:
        batch = {k: torch.from_numpy(archive[k].copy()) for k in archive.files}
    with np.load(outputs, allow_pickle=False) as archive:
        initial = torch.from_numpy(archive["output_0"].copy())
        auxiliary = torch.from_numpy(archive["output_1"].copy())
    assert initial.shape == (16, 3, 256, 256) and auxiliary.shape == (16, 4, 128, 128)
    trace = training / "work/artifacts/train/V143/source-loss.jsonl"
    with trace.open() as stream:
        records = [json.loads(next(stream)) for _ in range(16)]
    assert all(
        r["step"] == 1 and r["domain"] == "commons" and r["example_in_source_batch"] == i
        for i, r in enumerate(records)
    )
    save(output / "source-loss-first16-v1.json", records)
    python_rng, numpy_rng, torch_rng = (
        random.getstate(),
        np.random.get_state(),
        torch.get_rng_state().clone(),
    )
    original_call = torch.nn.Module._call_impl

    def forbidden(*args, **kwargs):
        raise RuntimeError("Neural module calls are forbidden in the loss-only diagnostic")

    torch.nn.Module._call_impl = forbidden
    measured = {}
    scalars = 0
    try:
        for label, epsilon, control in [
            ("pixel3e-4-gradient3e-4", 0.0003, "V142-crossed-line-v1"),
            ("pixel3e-4-gradient3e-5", 0.00003, "V143-crossed-gradient5000-v1"),
        ]:
            p = initial.clone().requires_grad_()
            aux = auxiliary.clone().requires_grad_()
            options = {
                "physical_fp32": True,
                "camera_supervision": "sensor-valid-v1",
                "reconstruction_charbonnier_epsilon": 0.0003,
                "gradient_charbonnier_epsilon": epsilon,
            }
            loss, terms = reconstruction_loss(p, batch, aux, **options)
            source_metrics = first_event(
                ROOT
                / control
                / ("train-V142.log" if control.startswith("V142") else "train-V143.log")
            )
            for name, value in {"loss": loss, **terms}.items():
                np.testing.assert_allclose(
                    float(value.detach()), source_metrics[name], rtol=2e-5, atol=2e-7
                )
                scalars += 1
            g_term = torch.autograd.grad(0.1 * terms["gradient"], p, retain_graph=True)[0]
            g, ga = torch.autograd.grad(loss, (p, aux))
            independent = manual_gradient_term(
                p.detach(), batch["target"], batch["wb"], batch["matrix"], epsilon
            )
            delta = g_term.numpy().astype(np.float64) - independent
            relative = float(np.linalg.norm(delta) / np.linalg.norm(independent))
            assert relative < 3e-6
            np.testing.assert_allclose(g_term.numpy(), independent, rtol=2e-5, atol=2e-10)
            measured[label] = {
                "gradient": g.numpy().astype(np.float64),
                "gradient_term": g_term.numpy().astype(np.float64),
                "aux_gradient": ga.numpy(),
                "manual_gradient_max_abs": float(np.abs(delta).max()),
                "manual_gradient_relative_L2": relative,
                "loss": float(loss.detach()),
            }
    finally:
        torch.nn.Module._call_impl = original_call
    old, new = measured.values()
    np.testing.assert_array_equal(old["aux_gradient"], new["aux_gradient"])
    difference_error = (new["gradient"] - old["gradient"]) - (
        new["gradient_term"] - old["gradient_term"]
    )
    assert np.max(np.abs(difference_error)) < 2e-10
    target = batch["sensor_target"]
    # Same fixed camera-RGB3x3-minus9x9 band as the earlier loss-smoothing study.
    band = F.avg_pool2d(F.pad(target, (1, 1, 1, 1), mode="reflect"), 3, 1) - F.avg_pool2d(
        F.pad(target, (4, 4, 4, 4), mode="reflect"), 9, 1
    )
    band = band.numpy().astype(np.float64)
    band[..., :8, :] = 0
    band[..., -8:, :] = 0
    band[..., :, :8] = 0
    band[..., :, -8:] = 0
    error = target.numpy().astype(np.float64) - initial.numpy().astype(np.float64)
    rows = []
    for i, source in enumerate(records):
        t = band[i]
        energy = float(np.sum(t * t))
        amount = float(np.sum(error[i] * t) / energy) if energy > 1e-16 else None
        row = {
            "index": i,
            "source": source["source"],
            "noise": source["noise"],
            "target_camera_band_RMS": float(np.sqrt(np.mean(t * t))),
            "missing_target_band_coefficient": amount,
            "options": {},
        }
        for label, value in measured.items():
            g = value["gradient"][i]
            direction = None if amount is None else amount * t
            row["options"][label] = {
                "RGB_output_gradient_L2": float(np.linalg.norm(g)),
                "weighted_gradient_term_L2": float(np.linalg.norm(value["gradient_term"][i])),
                "target_band_corrective_directional_derivative": None
                if direction is None
                else float(np.sum(g * direction)),
            }
        rows.append(row)
    assert random.getstate() == python_rng and np.array_equal(torch.get_rng_state(), torch_rng)
    assert (
        all(np.array_equal(a, b) for a, b in zip(numpy_rng, np.random.get_state(), strict=True))
        and not torch.cuda.is_initialized()
    )
    result = {
        "status": "completed-actual-first-batch-output-loss-gradient-replay",
        "operator": ref(__file__),
        "inputs": ref(inputs),
        "saved_model_outputs": ref(outputs),
        "source_trace_prefix": ref(output / "source-loss-first16-v1.json"),
        "actual_source_modules_exact": 69,
        "GPU_full_batch_loss_term_scalars_replayed": scalars,
        "independent_gradient_RGB_values_checked": 2 * initial.numel(),
        "option_checks": {
            k: {
                a: b for a, b in v.items() if a not in ("gradient", "gradient_term", "aux_gradient")
            }
            for k, v in measured.items()
        },
        "only_gradient_term_changes_max_abs": float(np.abs(difference_error).max()),
        "auxiliary_gradients_exact": True,
        "rows": rows,
        "new_neural_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "scope": "Actual firstB16 training inputs and outputs, two loss-gradient backwards in CPU FP32/one thread. Three crossed-line examples are all present, two ADC-only and one noisy; no absent mesh in this selected batch. Full actualB16 reduction retains valid-mask/batch denominators. Output gradients and fixed target-band directions are not network-parameter gradients, optimizer contributions after clipping, learned-quality evidence or flat-safety proof. Independent NumPy64 VJP uses actual FP32 rendered/linear intermediates. No model execution or data regeneration.",
    }
    save(output / "result-v1.json", result)
    print(
        {
            "scalars_replayed": scalars,
            "gradient_values_checked": 2 * initial.numel(),
            "mesh_rows": [r for r in rows if r["source"]["kind"] == "crossed-lines"],
        },
        flush=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    run(p.parse_args().output.resolve())
