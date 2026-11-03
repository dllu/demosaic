"""Independent local WLS/covariance and known spatially varying phase checks."""

import numpy as np
import pytest

from demosaic.phase_envelope import correct_complex_patch, local_green_phasor
from demosaic.phase_harmonic import correct_local_patch


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_local_phasor_against_direct_physical_weighted_least_squares(colors):
    yy, xx = np.mgrid[:9, :11]
    residual = np.stack([0.002 * np.sin(0.7 * xx + 0.3 * yy + p) for p in range(4)])
    variance = np.stack([1e-5 * (1 + 0.03 * xx + 0.02 * yy + 0.1 * p) for p in range(4)])
    planes = np.stack([0.00003 * (xx - yy + p) for p in range(4)])
    frequency, sigma = (0.081, 0.057), 4.0
    coefficients, power, info = local_green_phasor(
        residual, variance, colors, planes, frequency, sigma
    )
    radius = int(np.ceil(4 * sigma / 2))
    coordinates = np.arange(-radius, radius + 1)
    for y, x in [(0, 0), (4, 5), (8, 10)]:
        design, observations, weights, raw_variance = [], [], [], []
        for p in np.flatnonzero(np.asarray(colors) == 1):
            oy, ox = divmod(int(p), 2)
            angle = 2 * np.pi * (frequency[0] * (2 * xx + ox) + frequency[1] * (2 * yy + oy))
            kernel_y = np.exp(-0.5 * ((coordinates - (oy - 0.5) / 2) / (sigma / 2)) ** 2)
            kernel_x = np.exp(-0.5 * ((coordinates - (ox - 0.5) / 2) / (sigma / 2)) ** 2)
            kernel = np.exp(
                -0.5
                * (
                    ((2 * yy + oy - (2 * y + 0.5)) / sigma) ** 2
                    + ((2 * xx + ox - (2 * x + 0.5)) / sigma) ** 2
                )
            ) / (kernel_y.sum() * kernel_x.sum())
            kernel *= (abs(yy - y) <= radius) & (abs(xx - x) <= radius)
            design.append(np.stack([np.cos(angle).ravel(), np.sin(angle).ravel()], axis=1))
            observations.append((residual[p] - planes[p]).ravel())
            weights.append((kernel / variance[p]).ravel())
            raw_variance.append(variance[p].ravel())
        design, observations, weights, raw_variance = map(
            np.concatenate, [design, observations, weights, raw_variance]
        )
        # Independently form the complete linear estimator, not an expanded2x2 inverse.
        estimator = np.linalg.solve(design.T @ (weights[:, None] * design), design.T * weights)
        expected = estimator @ observations
        covariance = (estimator * raw_variance) @ estimator.T
        np.testing.assert_allclose(coefficients[:, y, x], expected, rtol=3e-13, atol=1e-16)
        np.testing.assert_allclose(
            info["covariance"][:, y, x], covariance[[0, 0, 1], [0, 1, 1]], rtol=4e-13
        )
        np.testing.assert_allclose(
            power[y, x], expected @ np.linalg.solve(covariance, expected), rtol=5e-13
        )


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_slowly_bending_phase_recovers_more_than_scalar_envelope(colors):
    yy, xx = np.mgrid[:256, :256]
    base = np.full((3, 256, 256), 0.02)
    angle = 2 * np.pi * (0.0625 * xx + 0.09375 * yy) + 1.5 * np.sin(2 * np.pi * xx / 512)
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * np.cos(angle)
    packed = np.stack([target[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    variance = np.full_like(packed, 1e-7)
    old, _ = correct_local_patch(packed, variance, colors, base)
    actual, info = correct_complex_patch(packed, variance, colors, base)
    roi = (..., slice(48, 208), slice(48, 208))
    assert info["peaks"]
    assert np.mean((actual[roi] - target[roi]) ** 2) < 0.4 * np.mean((old[roi] - target[roi]) ** 2)
    unchanged, _ = correct_complex_patch(packed, np.zeros_like(packed), colors, base)
    np.testing.assert_array_equal(unchanged, base)


def test_invalid_local_scale_rejected():
    with pytest.raises(ValueError, match="scale"):
        local_green_phasor(
            np.zeros((4, 3, 3)),
            np.ones((4, 3, 3)),
            [0, 1, 1, 2],
            np.zeros((4, 3, 3)),
            (0.1, 0.1),
            0,
        )


def test_cli_selects_envelope_before_RGB16_export(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace

    import tifffile
    import torch

    from demosaic import inference
    from demosaic.cli import main

    yy, xx = np.mgrid[:256, :256]
    base = np.full((3, 256, 256), 0.02, dtype=np.float32)
    angle = 2 * np.pi * (0.0625 * xx + 0.09375 * yy) + 1.5 * np.sin(2 * np.pi * xx / 512)
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * np.cos(angle)
    colors = [0, 1, 1, 2]
    raw = np.empty((256, 256), dtype=np.float32)
    for p, c in enumerate(colors):
        raw[p // 2 :: 2, p % 2 :: 2] = target[c, p // 2 :: 2, p % 2 :: 2]
    input_path = tmp_path / "wave.npy"
    np.save(input_path, raw)
    # Exercise actual CLI normalization, correction dispatch and serialized RGB16.
    # A declared stub replaces only the independently tested neural loading/pass.
    model = SimpleNamespace(config=SimpleNamespace(to_dict=lambda: {"test_stub": True}))
    monkeypatch.setattr(
        inference,
        "load_checkpoint",
        lambda *a, **k: (model, {"step": 0, "loaded_sha256": "0" * 64}),
    )
    monkeypatch.setattr(
        inference,
        "restore_tiled",
        lambda *a, **k: (torch.from_numpy(base.copy()), {"seconds": 0, "test_stub": True}),
    )
    errors = {}
    for name, mode, refined in [
        ("scalar", "scalar", False),
        ("complex", "complex", False),
        ("edge", "edge", False),
        ("refined", "edge", True),
        ("sparse", "sparse", False),
        ("wide", "wide", False),
        ("cross", "cross", False),
        ("detail", "detail", False),
        ("default", None, False),
    ]:
        output = tmp_path / f"{name}.tiff"
        main(
            [
                "infer",
                str(tmp_path / "stub.pt"),
                str(input_path),
                str(output),
                "--device",
                "cpu",
                "--white",
                "1",
                "--shot",
                "0",
                "--read",
                "1e-7",
                "--phase-harmonic",
            ]
            + (["--phase-harmonic-envelope", mode] if mode else [])
            + (["--phase-harmonic-refine-frequency"] if refined else [])
        )
        image = tifffile.imread(output)
        assert image.dtype == np.uint16
        errors[name] = np.mean(
            (image[48:208, 48:208] / 65535 - target[:, 48:208, 48:208].transpose(1, 2, 0)) ** 2
        )
        metadata = json.loads(output.with_suffix(".json").read_text())
        mode = mode or "detail"
        assert metadata["phase_harmonic"]["envelope"] == mode
        assert metadata["phase_harmonic"]["new_model_calls"] == 0
        assert metadata["phase_harmonic"]["refine_frequency"] == (
            refined or mode in ("sparse", "wide", "cross", "detail")
        )
        if refined or mode in ("sparse", "wide", "cross", "detail"):
            assert metadata["phase_harmonic"]["frequency_search"]["solves"] > 0
        if mode in ("edge", "sparse", "wide", "cross", "detail"):
            assert metadata["phase_harmonic"]["TV"]["device"] == "cpu"
            assert metadata["phase_harmonic"]["TV"]["solves"] > 0
        if mode in ("sparse", "wide", "cross", "detail"):
            assert metadata["phase_harmonic"]["support_TV"]["solves"] > 0
            assert (
                metadata["phase_harmonic"]["sparse_support"]["minimum_connected_packed_area"] == 805
            )
        if mode in ("wide", "cross", "detail"):
            assert metadata["phase_harmonic"]["context_small_image_fallback"]
    assert errors["complex"] < 0.4 * errors["scalar"]
    assert errors["edge"] < np.mean((base[:, 48:208, 48:208] - target[:, 48:208, 48:208]) ** 2)
