"""Independent physical operators and convex optima for the unadopted study tool."""

import json
import sys

import numpy as np
import pytest
import torch

from demosaic.phase_tv import correct_edge_phase_patch
from scripts.experimental_raw_phase_refit import Solver, candidates, interpolate, main


def _matrix(n, coordinates):
    return np.stack([np.interp(coordinates, np.arange(n), row) for row in np.eye(n)], 1)


@pytest.mark.parametrize("phase", range(4))
def test_physical_interpolation_matches_independent_matrices_and_adjoint(phase):
    rng = np.random.default_rng(2026111003 + phase)
    value, dual = rng.normal(size=(2, 2, 7, 11)), rng.normal(size=(2, 2, 7, 11))
    oy, ox = divmod(phase, 2)
    by = _matrix(7, np.arange(7) + (oy - 0.5) / 2)
    bx = _matrix(11, np.arange(11) + (ox - 0.5) / 2)
    actual = interpolate(torch.tensor(value), phase).numpy()
    np.testing.assert_allclose(actual, by @ value @ bx.T, atol=1e-15)
    adjoint = interpolate(torch.tensor(dual), phase, True).numpy()
    np.testing.assert_allclose(adjoint, by.T @ dual @ bx, atol=1e-15)
    np.testing.assert_allclose(np.sum(actual * dual), np.sum(value * adjoint), atol=2e-14)


@pytest.mark.parametrize("device", ["cpu", "cuda"])
def test_positive_TV_and_group_fit_have_known_constant_optimum_and_feasible_gap(device):
    if device == "cuda" and not torch.cuda.is_available():
        pytest.skip("CUDA required")
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state().clone() if torch.cuda.is_available() else None
    w = _matrix(32, (np.arange(128) + 0.5) / 4 - 0.5)
    phases = (1, 2)
    t = np.zeros((2, 1, 2, 128, 128))
    t[0, 0, 0], t[1, 0, 1] = 1, 1
    known = np.empty((1, 2, 32, 32))
    known[0, 0], known[0, 1] = 0.37, -0.22
    y = []
    for i, phase in enumerate(phases):
        oy, ox = divmod(phase, 2)
        ay = _matrix(128, np.arange(128) + (oy - 0.5) / 2) @ w
        ax = _matrix(128, np.arange(128) + (ox - 0.5) / 2) @ w
        force = 0.05 * known[0, i] + 0.25 * known[0, i] / np.hypot(0.37, 0.22)
        correction = np.linalg.solve(ay.T @ ay, force)
        correction = np.linalg.solve(ax.T @ ax, correction.T).T
        y.append(ay @ (known[0, i] + correction) @ ax.T)
    solve = Solver(1, phases, device)
    value, info = solve(
        t,
        np.asarray(y),
        np.ones((1, 128, 128), bool),
        np.zeros((1, 2, 128, 128)),
        2.0,
        0.25,
    )
    latent_error = np.sum((solve.u.cpu().numpy() - known) ** 2)
    assert 0.05 * latent_error / 2 <= info["relative_gap"] * info["scale"] + 1e-10
    np.testing.assert_allclose(value, w @ known @ w.T, atol=1e-5)
    # Reusing graph buffers for empty support must remove every output value.
    empty, cap = solve(
        t, np.asarray(y), np.zeros((1, 128, 128), bool), value, 2.0, 0.25, iterations=1
    )
    np.testing.assert_array_equal(empty, 0)
    assert cap["iterations"] == 1
    assert torch.equal(cpu_rng, torch.get_rng_state())
    if cuda_rng is not None:
        assert torch.equal(cuda_rng, torch.cuda.get_rng_state())


@pytest.mark.parametrize("colors", [(0, 1, 1, 2), (2, 1, 1, 0), (1, 0, 2, 1), (1, 2, 0, 1)])
def test_research_pipeline_uses_physical_CFA_and_retains_ADC_only_bypass(colors):
    yy, xx = np.mgrid[:256, :256]
    base = np.full((3, 256, 256), 0.02)
    wave = np.cos(2 * np.pi * (-0.0713 * xx + 0.0532 * yy) + 0.7)
    target = base + np.array([0.0015, 0.002, 0.001])[:, None, None] * wave
    packed = np.stack([target[c, p // 2 :: 2, p % 2 :: 2] for p, c in enumerate(colors)])
    values, info = candidates(packed, np.full_like(packed, 1e-7), colors, base)
    actual = values["raw-RGB-group.125"]
    roi = (..., slice(48, 208), slice(48, 208))
    assert np.mean((actual[roi] - target[roi]) ** 2) < 0.1 * np.mean((base[roi] - target[roi]) ** 2)
    assert info["solvers"]["raw-RGB-group.125"]["group_L1"] == 0.125
    unchanged, _ = candidates(packed, np.zeros_like(packed), colors, base)
    np.testing.assert_array_equal(unchanged["raw-RGB-group.125"], base)
    packed[0, 40, 50] = 1.0
    guarded, diagnostic = candidates(packed, np.full_like(packed, 1e-7), colors, base)
    fixed, _ = correct_edge_phase_patch(packed, np.full_like(packed, 1e-7), colors, base)
    np.testing.assert_array_equal(guarded["raw-RGB-group.125"], fixed)
    assert diagnostic["clipping_fallback"]


def test_archive_CLI_reads_measurements_and_parent_without_targets(tmp_path, monkeypatch):
    observation, parent, output = [tmp_path / name for name in ["raw.npz", "parent.npy", "out.npy"]]
    base = np.full((1, 3, 256, 256), 0.02, np.float32)
    np.save(parent, base)
    np.savez(
        observation,
        packed=np.full((1, 4, 128, 128), 0.02, np.float32),
        variance=np.zeros((1, 4, 128, 128)),
        colors=np.array([[0, 1, 1, 2]]),
        target=np.full_like(base, np.nan),
    )
    monkeypatch.setattr(
        sys, "argv", ["experimental_raw_phase_refit", str(observation), str(parent), str(output)]
    )
    main()
    np.testing.assert_array_equal(np.load(output), base)
    metadata = json.loads(output.with_suffix(".json").read_text())
    assert metadata["neural_calls"] == metadata["RAW_opens"] == 0
