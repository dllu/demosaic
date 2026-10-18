"""CPU counterexamples for censored sensor values and clipped display gradients.

This is a mathematical fixture, not a trained restoration model or inference
calibration. The oracle line uses GT only to establish feasible representations.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import torch

from demosaic.cfa import bilinear, color_indices, mosaic
from demosaic.color import render
from demosaic.data import camera_pair
from demosaic.losses import charbonnier, reconstruction_loss
from demosaic.noise import add_noise
from demosaic.raw_kernel import AdaptiveRawKernel
from demosaic.safety import writable_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).absolute()), "sha256": sha(path)}


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def linear_rgb(prediction, wb, matrix):
    return torch.einsum("bij,bjhw->bihw", matrix, prediction * wb[..., None, None])


def interval_errors(prediction, reference, epsilon=1e-6):
    """Exact interior values, a lower bound at white and upper bound at black."""
    return torch.where(
        reference >= 1 - epsilon,
        (prediction - 1).clamp_max(0),
        torch.where(reference <= epsilon, prediction.clamp_min(0), prediction - reference),
    )


def interval_loss(prediction, batch):
    return charbonnier(
        interval_errors(
            linear_rgb(prediction, batch["wb"], batch["matrix"]),
            linear_rgb(batch["target"], batch["wb"], batch["matrix"]),
        )
    )


def censor_gate(packed, colors):
    """Only observed maximum ADC codes activate this diagnostic RGB correction."""
    return bilinear((packed >= 1 - 0.5 / 65535).float(), colors)


def fixture(scene, matrix, pattern="RGGB", observation="ideal-clipped", size=32):
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    matrix = torch.tensor(matrix)[None]
    scene = torch.tensor(scene)[None, :, None, None].expand(1, 3, size, size)
    clean, target = camera_pair(scene, torch.linalg.inv(matrix), wb, reconstruct_highlights=True)
    colors = color_indices(pattern)[None]
    raw = mosaic(clean, colors)
    if observation == "ideal-clipped":
        packed = raw.clamp(0, 1)
    elif observation == "ADC16-black.03":
        packed = add_noise(
            raw, 0.0, 0.0, black_level=0.03, generator=torch.Generator().manual_seed(42)
        )
    else:
        raise ValueError("Unknown diagnostic observation")
    return {
        "target": target,
        "sensor_target": clean,
        "colors": colors,
        "wb": wb,
        "matrix": matrix,
    }, packed


def numpy_replay(prediction, batch, gate):
    """Independent FP64 arrays, CFA gathering, sRGB and scalar loss arithmetic."""
    p = prediction.detach().numpy()[0].astype(np.float64)
    target = batch["target"].numpy()[0].astype(np.float64)
    sensor = batch["sensor_target"].numpy()[0].astype(np.float64)
    wb = batch["wb"].numpy()[0].astype(np.float64)
    matrix = batch["matrix"].numpy()[0].astype(np.float64)
    valid = (sensor >= 0) & (sensor < 0.98)

    def mean_penalty(error, mask=None):
        values = np.sqrt(error**2 + 1e-6)
        return (
            float(values.mean() if mask is None else values[mask].mean())
            if mask is None or mask.any()
            else 0.0
        )

    def transport(value):
        return np.einsum("ij,jhw->ihw", matrix, value * wb[:, None, None])

    def srgb(value):
        value = np.clip(value, 0, 1)
        return np.where(value <= 0.0031308, 12.92 * value, 1.055 * value ** (1 / 2.4) - 0.055)

    display, truth = srgb(transport(p)), srgb(transport(target))
    gradient = (
        sum(mean_penalty(np.diff(display, axis=d) - np.diff(truth, axis=d)) for d in [-1, -2]) / 2
    )
    saturated = truth.max(axis=0) > 0.98
    assert bool(saturated.all()) or not bool(saturated.any()), "Fixture saturation must be uniform"
    chroma = (display - display.mean(axis=0)) - (truth - truth.mean(axis=0))
    highlight = float(np.abs(chroma).mean()) if saturated.any() else 0.0
    colors = batch["colors"][0].tolist()
    observed_p, observed_s = [], []
    for phase, color in enumerate(colors):
        y, x = divmod(phase, 2)
        observed_p.append(p[color, y::2, x::2])
        observed_s.append(sensor[color, y::2, x::2])
    observed_p, observed_s = np.array(observed_p), np.array(observed_s)
    terms = {
        "linear": mean_penalty(p - sensor, valid),
        "rendered": mean_penalty(display - truth),
        "gradient": gradient,
        "highlight": highlight,
        "sensor": mean_penalty(observed_p - observed_s, (observed_s >= 0) & (observed_s < 0.98)),
    }
    total = (
        terms["linear"]
        + 0.5 * terms["rendered"]
        + 0.1 * terms["gradient"]
        + 0.1 * terms["highlight"]
        + 0.1 * terms["sensor"]
    )
    value, reference = transport(p), transport(target)
    white, black = reference >= 1 - 1e-6, reference <= 1e-6
    error = np.where(
        white, np.minimum(value - 1, 0), np.where(black, np.maximum(value, 0), value - reference)
    )
    active = np.where(white, value < 1, np.where(black, value > 0, True))
    derivative = error / np.sqrt(error**2 + 1e-6) * active / error.size
    rgb_derivative = np.einsum("ij,ihw->jhw", matrix, derivative) * wb[:, None, None]
    beta_gradient = (rgb_derivative * gate.numpy()[0]).sum(axis=(1, 2))
    return total, terms, mean_penalty(error), beta_gradient.tolist()


def inspect_beta(base, gate, batch, beta_values):
    beta = torch.tensor(beta_values, requires_grad=True)
    prediction = base + gate * beta[None, :, None, None]
    loss, terms = reconstruction_loss(
        prediction, batch, mosaic(prediction, batch["colors"]), camera_supervision="sensor-valid-v1"
    )
    gradient = torch.autograd.grad(loss, beta, retain_graph=True)[0]
    interval = interval_loss(prediction, batch)
    extra_gradient = torch.autograd.grad(interval, beta)[0]
    replay, replay_parts, replay_interval, replay_gradient = numpy_replay(prediction, batch, gate)
    differences = [
        abs(float(loss.detach()) - replay),
        abs(float(interval.detach()) - replay_interval),
    ]
    differences.extend(abs(float(v.detach()) - replay_parts[k]) for k, v in terms.items())
    grad_difference = max(
        abs(float(a) - b) for a, b in zip(extra_gradient, replay_gradient, strict=True)
    )
    assert max(differences) < 5e-6 and grad_difference < 5e-6
    valid = (batch["sensor_target"] >= 0) & (batch["sensor_target"] < 0.98)
    return {
        "beta": beta_values,
        "prediction_camera_RGB": prediction.detach()[0, :, 0, 0].tolist(),
        "prediction_linear_sRGB": linear_rgb(prediction.detach(), batch["wb"], batch["matrix"])[
            0, :, 0, 0
        ].tolist(),
        "rendered_MSE": float(
            (
                render(prediction.detach(), batch["wb"], batch["matrix"])
                - render(batch["target"], batch["wb"], batch["matrix"])
            )
            .square()
            .mean()
        ),
        "valid_camera_MSE": float(
            (prediction.detach() - batch["sensor_target"])[valid].square().mean()
        ),
        "current_loss": float(loss.detach()),
        "current_loss_beta_gradient": gradient.tolist(),
        "interval_loss": float(interval.detach()),
        "interval_beta_gradient": extra_gradient.tolist(),
        "maximum_independent_loss_difference": max(differences),
        "maximum_independent_gradient_difference": grad_difference,
    }


def oracle_direction(base, gate, batch, initial):
    """GT-only feasibility witness; this must never be used for inference."""
    prediction = base + gate * torch.tensor(initial)[None, :, None, None]
    value = linear_rgb(prediction, batch["wb"], batch["matrix"])[0, 2].double().mean()
    reference = linear_rgb(batch["target"], batch["wb"], batch["matrix"])[0, 2].double().mean()
    enabled = gate[0, :, 0, 0].double()
    direction = batch["matrix"][0, 2].double() * batch["wb"][0].double() * enabled
    return ((reference - value) * direction / direction.square().sum()).float()


def state_hash(head):
    h = hashlib.sha256()
    for key, value in sorted(head.state_dict().items()):
        h.update(key.encode() + value.detach().numpy().tobytes())
    return h.hexdigest()


def main(plan_path):
    os.nice(5)
    torch.set_num_threads(2)
    assert not torch.cuda.is_available() and not torch.cuda.is_initialized()
    plan = json.loads(plan_path.read_text())
    for path, digest in plan["frozen_files"].items():
        assert sha(path) == digest
    output = writable_path(plan["output"])
    output.mkdir(parents=True, exist_ok=False)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(20261018)
        head = AdaptiveRawKernel(67, phase_conditioning=True)
        with torch.no_grad():
            for parameter in head.parameters():
                parameter.normal_(0, 0.2)
    before = state_hash(head)
    generator = torch.Generator().manual_seed(20261018)
    cases, plateaus, curve_fixture = [], [], None
    for case in plan["cases"]:
        batch, packed = fixture(case["scene"], case["matrix"], case["pattern"], case["observation"])
        features = torch.randn((1, 67, 32, 32), generator=generator, requires_grad=True)
        head.zero_grad(set_to_none=True)
        prediction = head(packed, batch["colors"], features)
        loss, _ = reconstruction_loss(
            prediction,
            batch,
            mosaic(prediction, batch["colors"]),
            camera_supervision="sensor-valid-v1",
        )
        loss.backward()
        head_gradient = max(float(p.grad.abs().max()) for p in head.parameters())
        assert head_gradient == float(features.grad.abs().max()) == 0.0
        base = prediction.detach()
        gate = censor_gate(packed, batch["colors"])
        assert torch.equal(mosaic(gate, batch["colors"]), (packed >= 1 - 0.5 / 65535).float())
        row = {
            **case,
            "clean_camera_RGB": batch["sensor_target"][0, :, 0, 0].tolist(),
            "reference_camera_RGB": batch["target"][0, :, 0, 0].tolist(),
            "gate": gate[0, :, 0, 0].tolist(),
            "raw_head_maximum_gradient": head_gradient,
            "feature_maximum_gradient": float(features.grad.abs().max()),
            "zero_correction": inspect_beta(base, gate, batch, [0.0, 0.0, 0.0]),
        }
        cases.append(row)
        if (
            case["scene_name"] == "reference-white-and-sensor-clipped"
            and case["matrix_name"] == "coupled"
        ):
            start = plan["plateau_beta"]
            plateau = inspect_beta(base, gate, batch, start)
            assert plateau["rendered_MSE"] > 0.0005
            assert plateau["current_loss_beta_gradient"] == [0.0, 0.0, 0.0]
            assert (
                plateau["interval_beta_gradient"][0] < -0.01
                and plateau["interval_beta_gradient"][1] < -0.01
            )
            delta = oracle_direction(base, gate, batch, start)
            oracle = inspect_beta(base, gate, batch, (torch.tensor(start) + delta).tolist())
            assert oracle["rendered_MSE"] < 1e-12
            assert oracle["valid_camera_MSE"] == plateau["valid_camera_MSE"]
            plateaus.append(
                {
                    "pattern": case["pattern"],
                    "observation": case["observation"],
                    "plateau": plateau,
                    "GT_only_oracle_delta": delta.tolist(),
                    "GT_only_feasible_oracle": oracle,
                }
            )
            if curve_fixture is None:
                curve_fixture = (base, gate, batch, torch.tensor(start), delta)
    assert len(cases) == 48 and len(plateaus) == 8 and state_hash(head) == before
    base, gate, batch, start, delta = curve_fixture
    curve = []
    with torch.no_grad():
        for t in np.linspace(0, 1.25, 161):
            prediction = base + gate * (start + float(t) * delta)[None, :, None, None]
            loss, _ = reconstruction_loss(
                prediction,
                batch,
                mosaic(prediction, batch["colors"]),
                camera_supervision="sensor-valid-v1",
            )
            interval = interval_loss(prediction, batch)
            curve.append(
                {
                    "t": float(t),
                    "current_loss": float(loss),
                    "current_plus_interval": float(
                        loss + plan["illustrative_interval_weight"] * interval
                    ),
                    "linear_blue": float(
                        linear_rgb(prediction, batch["wb"], batch["matrix"])[0, 2].mean()
                    ),
                }
            )
    save(output / "cases.json", {"cases": cases, "censored_plateaus": plateaus})
    save(
        output / "oracle-line.json",
        {
            "curve": curve,
            "scope": "GT-only feasible line to expose a gradient barrier; never an inference correction or training quality claim.",
        },
    )
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(10, 3.7), constrained_layout=True)
    t = [v["t"] for v in curve]
    for key, label in [
        ("current_loss", "Current sensor-valid loss"),
        ("current_plus_interval", "Current + 0.1 interval constraint"),
    ]:
        axes[0].plot(t, [v[key] for v in curve], label=label)
    axes[0].set(xlabel="Position on GT-only feasibility line", ylabel="Fixture training loss")
    axes[0].legend(fontsize=8)
    axes[1].plot(t, [v["linear_blue"] for v in curve], label="Predicted linear blue")
    axes[1].axhline(1, color="gray", linestyle="--", label="Display clamp")
    axes[1].axhline(0.9, color="black", linestyle=":", label="Reference blue")
    axes[1].set(xlabel="Position on GT-only feasibility line", ylabel="Before display clipping")
    axes[1].legend(fontsize=8)
    for ax in axes:
        ax.axvline(1, color="gray", linestyle=":", linewidth=0.8)
        ax.grid(alpha=0.2)
    fig.suptitle(
        "Artificial constant highlight: feasibility and gradients, no trained-model result",
        fontsize=10,
    )
    fig.savefig(output / "loss-barrier.png", dpi=150)
    plt.close(fig)
    for path, digest in plan["frozen_files"].items():
        assert sha(path) == digest
    assert not torch.cuda.is_initialized()
    receipt = {
        "status": "completed-CPU-censored-highlight-representation-and-gradient-audit",
        "plan": ref(plan_path),
        "cases": ref(output / "cases.json"),
        "oracle_line": ref(output / "oracle-line.json"),
        "plot": ref(output / "loss-barrier.png"),
        "actual_head_forwards": len(cases),
        "full_restoration_model_forwards": 0,
        "DINO_loads": 0,
        "source_images_read": 0,
        "CUDA_initialized": False,
        "head_parameter_state_unchanged": state_hash(head) == before,
        "limits": "48 artificial constant fixtures only; no model training, inference calibration or causal explanation of V77. The ADC-gated affine correction and interval constraint are experimental mathematical probes outside production. Oracle line uses GT solely for a feasibility witness, never for inference. No quality/speed/model promotion claim; V76/V77 gates and frozen review unchanged.",
    }
    save(output / "receipt.json", receipt)
    print(json.dumps(receipt))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
