import math
from pathlib import Path

import pytest
import torch


@pytest.fixture
def fit(monkeypatch):
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "scripts"))
    from diagnose_texture_observability import carrier_fit

    return carrier_fit


def fixture():
    coordinate = 2 * torch.arange(32, dtype=torch.float64)[None, None, :]
    coordinate = coordinate + torch.tensor([0, 1, 0, 1], dtype=torch.float64)[:, None, None]
    cosine = (coordinate * (2 * math.pi / 8)).cos().expand(4, 32, 32)
    sine = (coordinate * (2 * math.pi / 8)).sin().expand_as(cosine)
    base = torch.tensor([0.1, 0.2, 0.3, 0.4], dtype=torch.float64)[:, None, None].expand_as(cosine)
    phase_gains = torch.tensor([0.9, 1, 1.1, 0.8], dtype=torch.float64)[:, None, None]
    measured = (base * (phase_gains + 0.02 * cosine - 0.01 * sine))[None]
    variance = torch.full_like(base, 0.0001)
    return measured, base, cosine, sine, variance


def test_known_carrier_is_separated_from_four_phase_offsets(fit):
    beta, std = fit(*fixture())
    torch.testing.assert_close(
        beta[0], torch.tensor([0.9, 1, 1.1, 0.8, 0.02, -0.01], dtype=torch.float64)
    )
    assert math.isfinite(std) and std > 0


def test_fourfold_noise_variance_doubles_contrast_uncertainty(fit):
    measured, base, cosine, sine, variance = fixture()
    beta, std = fit(measured, base, cosine, sine, variance)
    other, bigger = fit(measured, base, cosine, sine, 4 * variance)
    torch.testing.assert_close(beta, other)
    assert math.isclose(bigger, 2 * std, rel_tol=1e-12)
