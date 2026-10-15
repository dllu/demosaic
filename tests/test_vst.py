import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from demosaic.cfa import PATTERNS, color_indices, malvar, mosaic
from demosaic.gaussian import JointGaussianPrior, StabilizedGaussianPrior, load_gaussian_prior
from demosaic.vst import GeneralizedAnscombe


@pytest.mark.parametrize("shot,read", [(1e-3, 4e-6), (2e-5, 0.0), (1e-10, 1e-4)])
def test_centered_gat_algebraic_roundtrip_keeps_sub_16bit_precision(shot, read):
    transform = GeneralizedAnscombe(shot, read, inverse="algebraic")
    raw = torch.linspace(-0.1 * shot, 1.0, 257)
    actual = transform.inverse(transform(raw))
    assert actual.dtype == torch.float32 and torch.isfinite(actual).all()
    torch.testing.assert_close(actual, raw, atol=2e-7, rtol=1e-7)


@pytest.mark.parametrize("read_e", [0.0, 0.4, 2.0])
def test_expectation_inverse_matches_independent_dense_gaussian_integration(read_e):
    # Independent integration in Gaussian coordinates, with no root substitution
    # or access to the implementation's interpolation grid.
    shot = 0.001
    transform = GeneralizedAnscombe(shot, (shot * read_e) ** 2)
    algebraic = GeneralizedAnscombe(shot, (shot * read_e) ** 2, inverse="algebraic")
    n = np.arange(401, dtype=np.float64)
    x = np.linspace(-10, 10, 16385)
    density = np.exp(-x * x / 2) / math.sqrt(2 * math.pi)
    q = 3 / 8 + read_e**2
    values = 2 * np.sqrt(np.maximum(n[:, None] + read_e * x + q, 0)) - 2 * math.sqrt(q)
    expected_per_count = np.trapezoid(values * density, x, axis=1)
    log_factorial = np.array([math.lgamma(v + 1) for v in n])
    for mean in [0.0, 0.25, 1.0, 4.0, 16.0, 64.0, 128.0, 128.001, 200.0]:
        probability = np.exp(n * np.log(max(mean, 1e-300)) - mean - log_factorial)
        expected = torch.tensor([(probability * expected_per_count).sum()], dtype=torch.float64)
        actual = transform.inverse(expected).item() / shot
        assert abs(actual - mean) < 0.001, (read_e, mean, actual)
        if mean == 4.0:
            biased = algebraic.inverse(expected).item() / shot
            assert abs(actual - mean) < abs(biased - mean) / 20


@pytest.mark.parametrize(
    "shot,read", [(0.0, 1e-6), (-1.0, 0.0), (float("nan"), 0.0), (0.001, -1.0)]
)
def test_invalid_gat_profiles_rejected(shot, read):
    with pytest.raises(ValueError, match="finite positive"):
        GeneralizedAnscombe(shot, read)


class IdentityGaussian(nn.Module):
    def __init__(self):
        super().__init__()
        self.weight = nn.Parameter(torch.zeros(()))
        self.calls = []

    def forward(self, x, *, sigma, norm_equiv):
        self.calls.append(sigma)
        return x + self.weight * 0


def test_gaussian_adapter_preserves_all_cfa_geometry_and_zero_noise_identity():
    network = IdentityGaussian()
    model = StabilizedGaussianPrior(network, inverse="algebraic")
    packed = torch.rand(4, 4, 35, 43) * 0.3
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    wb = torch.tensor([1.5, 1.0, 2.0])[None].expand(4, -1)
    expected = malvar(packed, colors, wb)
    with pytest.raises(ValueError, match="conditioning"):
        model(packed, torch.zeros_like(packed), colors, wb)
    model.set_noise(0, 0)
    assert torch.equal(model(packed, torch.zeros_like(packed), colors, wb), expected)
    assert not network.calls
    model.set_noise(0.001, 4e-6)
    torch.testing.assert_close(
        model(packed, torch.zeros_like(packed), colors, wb), expected, atol=4e-7, rtol=1e-6
    )
    assert network.calls == [1.0] * 16
    network.calls.clear()
    model.set_noise(0, 0.01)
    assert torch.equal(model(packed, torch.zeros_like(packed), colors, wb), expected)
    assert network.calls == [0.1] * 16


def test_exact_constant_phases_are_preserved_with_nonzero_noise_priors():
    network = IdentityGaussian()
    model = StabilizedGaussianPrior(network).set_noise(0.001, 4e-6)
    raw = torch.tensor([0.0, 0.2, 0.5, 1.0])[None, :, None, None].expand(1, 4, 32, 32)
    colors = color_indices("RGGB")
    assert torch.equal(model(raw, torch.ones_like(raw), colors), malvar(raw, colors))
    assert not network.calls


def test_joint_projection_preserves_measurement_geometry_for_every_cfa():
    network = IdentityGaussian()
    model = JointGaussianPrior(network, inverse="algebraic", sigmas=(4.0, 2.0, 1.0))
    model.set_noise(0.001, 4e-6)
    raw = torch.rand(4, 4, 32, 40) * 0.3
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    prediction = model(raw, torch.zeros_like(raw), colors)
    assert prediction.shape == (4, 3, 64, 80)
    torch.testing.assert_close(mosaic(prediction, colors), raw, atol=2e-7, rtol=1e-6)
    assert network.calls == [4.0, 2.0, 1.0] * 4


@pytest.mark.parametrize("sigmas,weight", [((), 0.23), ((0.0,), 0.23), ((1.0,), 0.0)])
def test_invalid_joint_schedules_rejected(sigmas, weight):
    with pytest.raises(ValueError):
        JointGaussianPrior(IdentityGaussian(), sigmas=sigmas, weight=weight)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA physical transform")
def test_gaussian_physical_math_stays_fp32_under_bfloat16_amp():
    model = StabilizedGaussianPrior(IdentityGaussian()).cuda().set_noise(0.001, 4e-6)
    raw = torch.rand(1, 4, 32, 40, device="cuda") * 0.3
    with torch.autocast("cuda", dtype=torch.bfloat16):
        result = model(raw, torch.zeros_like(raw), color_indices("GRBG", device="cuda"))
    assert result.dtype == torch.float32 and result.shape == (1, 3, 64, 80)
    assert torch.isfinite(result).all()


def test_external_gaussian_archive_and_checksums_are_enforced(tmp_path):
    root = tmp_path / "external"
    source = root / "src/noise2vst/models/drunet.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "import torch\nclass DRUNet(torch.nn.Module):\n def __init__(self,color=False):\n  super().__init__()\n  self.weight=torch.nn.Parameter(torch.zeros(()))\n def forward(self,x,**kw):\n  return x+self.weight*0\n"
    )
    weights = root / "weights.pth"
    torch.save({"weight": torch.zeros(())}, weights)
    (root / "LICENSE").write_text("MIT test fixture")
    receipt = tmp_path / "reference.json"
    record = {
        "checkout": str(root),
        "kair_license": str(root / "LICENSE"),
        "models": [
            {
                "model": "DRUNet",
                "weights": str(weights),
                "sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
                "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            }
        ],
    }
    receipt.write_text(json.dumps(record))
    output = tmp_path / "archive"
    model = load_gaussian_prior(receipt, archive=output)
    snapshot = Path(model.receipt["snapshot"])
    assert snapshot.exists() and snapshot.read_bytes() == weights.read_bytes()
    snapshot.write_bytes(b"corrupt")
    with pytest.raises(ValueError, match="Frozen Gaussian weights"):
        load_gaussian_prior(receipt, archive=output)
    source.write_text("# changed after acquisition")
    with pytest.raises(ValueError, match="External Gaussian source"):
        load_gaussian_prior(receipt)
