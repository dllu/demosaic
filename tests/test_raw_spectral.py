"""Independent dense-DFT, phase geometry and parent-preservation checks."""

import math

import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic, pack, unpack
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.raw_spectral import RawSpectralResidual, spectral_innovation, spectral_mask
from demosaic.train import make_optimizer, set_learning_rate


def dense_reference(raw, variance, base):
    """Full complex matrix DFT in float64; no FFT or production helpers."""
    h, w = raw.shape[-2:]
    y, x = np.indices((h, w)).reshape(2, -1)
    matrix = np.exp(-2j * np.pi * (y[:, None] * y / h + x[:, None] * x / w))
    matrix /= math.sqrt(h * w)
    observed = raw.reshape(4, -1) @ matrix.T
    predicted = base.reshape(4, -1) @ matrix.T
    scale = np.maximum(np.maximum(variance, 0).mean((-2, -1)), 1e-12)
    power = (np.abs(observed) ** 2 / scale[:, None]).sum(0)
    t = math.log(h * w / 0.01)
    threshold = 4 + 4 * math.sqrt(t) + 2 * t
    mask = np.maximum(1 - threshold / np.maximum(power, 1e-12), 0)
    mask[0] = 0
    residual = ((observed - predicted) * mask) @ matrix.conj()
    assert np.abs(residual.imag).max() < 1e-12
    return observed.reshape(4, h, w), mask.reshape(h, w), residual.real.reshape(4, h, w)


@pytest.mark.parametrize("shape", [(5, 7), (6, 8)])
def test_fft_and_signed_camera_innovation_match_independent_dense_dft(shape):
    generator = torch.Generator().manual_seed(326)
    raw = torch.randn(1, 4, *shape, generator=generator) * 0.2 - 0.05
    variance = torch.rand(raw.shape, generator=generator) * 0.0003
    variance[:, 0] = 0  # Explicit finite ADC-only convention, with other phases noisy.
    base = torch.rand(1, 3, 2 * shape[0], 2 * shape[1], generator=generator) * 0.4
    colors = color_indices("GRBG")
    expected, mask, residual = dense_reference(
        raw[0].numpy(), variance[0].numpy(), mosaic(base, colors)[0].numpy()
    )
    spectrum, weight = spectral_mask(raw, variance)
    np.testing.assert_allclose(spectrum[0], expected[..., : shape[1] // 2 + 1], atol=1e-7)
    np.testing.assert_allclose(weight[0, 0], mask[..., : shape[1] // 2 + 1], atol=2e-6)
    correction = spectral_innovation(base, raw, variance, colors, torch.tensor([[2.0, 1.0, 1.5]]))
    np.testing.assert_allclose(mosaic(correction, colors)[0], residual, atol=2e-7)
    assert mosaic(correction, colors).mean((-2, -1)).abs().max() < 3e-8
    assert correction.min() < 0 and correction.max() > 0


def spatial_transform(value, turns, flip):
    result = torch.rot90(value, turns, (-2, -1))
    return result.flip(-1) if flip else result


@pytest.mark.parametrize("pattern", PATTERNS)
def test_all_native_d4_geometries_and_batches_have_equivalent_innovations(pattern):
    generator = torch.Generator().manual_seed(8)
    raw = torch.rand(2, 4, 9, 13, generator=generator) * 0.2
    variance = torch.rand(raw.shape, generator=generator) * 0.0003
    base = torch.rand(2, 3, 18, 26, generator=generator) * 0.1
    colors = color_indices(pattern)
    labels = colors.reshape(1, 4, 1, 1).expand(1, 4, 9, 13).float()
    first = spectral_innovation(base, raw, variance, colors)
    separate = torch.cat(
        [
            spectral_innovation(base[i : i + 1], raw[i : i + 1], variance[i : i + 1], colors)
            for i in range(2)
        ]
    )
    torch.testing.assert_close(first, separate, atol=1e-7, rtol=1e-5)
    for turns in range(4):
        for flip in [False, True]:
            changed_raw = pack(spatial_transform(unpack(raw), turns, flip))
            changed_var = pack(spatial_transform(unpack(variance), turns, flip))
            changed_colors = pack(spatial_transform(unpack(labels), turns, flip))[0, :, 0, 0].long()
            result = spectral_innovation(
                spatial_transform(base, turns, flip), changed_raw, changed_var, changed_colors
            )
            torch.testing.assert_close(
                result, spatial_transform(first, turns, flip), atol=2e-7, rtol=1e-4
            )


@pytest.mark.parametrize("amp", [False, True])
def test_zero_head_preserves_parent_and_common_gradients_then_learns(amp):
    torch.manual_seed(24)
    before = torch.get_rng_state()
    branch = RawSpectralResidual()
    assert torch.equal(before, torch.get_rng_state())
    base = (torch.rand(2, 3, 18, 22) * 0.4).requires_grad_()
    raw = torch.rand(2, 4, 9, 11) * 0.3
    variance = torch.full_like(raw, 0.0001)
    features = torch.rand(2, 67, 18, 22, requires_grad=True)
    colors = color_indices("BGGR")
    originals = [a.detach().clone() for a in [base, raw, variance, features]]
    with torch.autocast("cpu", enabled=amp, dtype=torch.bfloat16):
        output = branch(base, raw, variance, colors, features)
    assert torch.equal(output, base) and output.dtype == torch.float32
    output.square().mean().backward()
    reference = base.detach().clone().requires_grad_()
    reference.square().mean().backward()
    assert torch.equal(base.grad, reference.grad)
    assert features.grad.count_nonzero() == 0
    assert branch.weight.grad.count_nonzero() and branch.bias.grad.count_nonzero()
    assert all(torch.equal(a, b) for a, b in zip(originals, [base, raw, variance, features]))
    with torch.no_grad():
        branch.weight.add_(-branch.weight.grad * 0.1)
    base.grad = features.grad = None
    branch(base, raw, variance, colors, features).square().mean().backward()
    assert features.grad.count_nonzero() and torch.isfinite(base.grad).all()


def test_complex_backward_matches_independent_finite_difference():
    generator = torch.Generator().manual_seed(3)
    raw = (torch.rand(1, 4, 4, 6, generator=generator) * 0.3).requires_grad_()
    variance = torch.full_like(raw, 0.00001)
    colors = color_indices("RGGB")
    base = torch.rand(1, 3, 8, 12, generator=generator) * 0.1
    # Measured-site projection removes interpolation from the FFT derivative check.
    loss = mosaic(spectral_innovation(base, raw, variance, colors), colors).square().mean()
    loss.backward()
    raw64 = raw.detach()[0].double().numpy()
    base64 = mosaic(base, colors)[0].double().numpy()
    for index in [(0, 1, 3), (1, 2, 4), (2, 0, 5), (3, 3, 1)]:
        plus, minus = raw64.copy(), raw64.copy()
        plus[index] += 1e-5
        minus[index] -= 1e-5
        a = dense_reference(plus, variance[0].numpy(), base64)[2]
        b = dense_reference(minus, variance[0].numpy(), base64)[2]
        expected = ((a * a).mean() - (b * b).mean()) / 2e-5
        assert float(raw.grad[(0, *index)]) == pytest.approx(expected, rel=2e-4, abs=1e-7)


def test_constants_and_explicit_adc_floor_are_finite_and_keep_dc():
    colors = color_indices("GBRG")
    base = torch.tensor([-0.03, 0.18, 1.2])[None, :, None, None].expand(1, 3, 18, 22)
    raw = mosaic(base, colors)
    for variance in [torch.zeros_like(raw), torch.full_like(raw, 0.0003)]:
        correction = spectral_innovation(base * 0.4, raw, variance, colors)
        assert torch.isfinite(correction).all() and correction.abs().max() < 2e-7


@pytest.mark.parametrize("alpha", [0, 1, -0.1, float("nan"), float("inf")])
def test_invalid_alpha_rejected(alpha):
    with pytest.raises(ValueError, match="alpha"):
        spectral_mask(torch.zeros(1, 4, 5, 7), torch.zeros(1, 4, 5, 7), alpha=alpha)


@pytest.mark.parametrize("amp", [False, True])
def test_complete_model_parent_values_gradients_rng_and_portable_state(tmp_path, amp):
    def config(enabled):
        return ModelConfig(
            restoration_backbone="pretrained-rgb",
            width=64,
            camera_conditioning=True,
            variance_stabilization=True,
            physical_anchors=True,
            raw_spectral_residual=enabled,
        )

    torch.manual_seed(17)
    parent = JointDemosaic(config(False))
    after_parent = torch.get_rng_state()
    torch.manual_seed(17)
    candidate = JointDemosaic(config(True))
    assert torch.equal(after_parent, torch.get_rng_state())
    missing = candidate.load_state_dict(parent.restoration_state_dict(), strict=False)
    assert set(missing.missing_keys) == {
        "pretrained_rgb.raw_spectral.weight",
        "pretrained_rgb.raw_spectral.bias",
    }
    assert not missing.unexpected_keys
    generator = torch.Generator().manual_seed(37)
    raw = torch.rand(1, 4, 12, 16, generator=generator) * 0.5
    variance = torch.full_like(raw, 0.0003)
    colors = color_indices("BGGR")
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    for model in [parent, candidate]:
        model.set_noise(torch.tensor([0.001]), torch.tensor([1e-5]))
    with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        a, aa = parent(raw, variance, colors, wb, auxiliary=True)
        b, ba = candidate(raw, variance, colors, wb, auxiliary=True)
    assert torch.equal(a, b) and torch.equal(aa, ba)
    a.square().mean().backward()
    b.square().mean().backward()
    other = dict(candidate.named_parameters())
    for name, parameter in parent.named_parameters():
        assert torch.equal(parameter.grad, other[name].grad), name
    branch = candidate.pretrained_rgb.raw_spectral
    assert branch.weight.grad.count_nonzero() and branch.bias.grad.count_nonzero()
    path = tmp_path / "candidate.pt"
    with torch.no_grad():
        branch.bias.fill_(0.4)
    torch.save(
        {"model_config": candidate.config.to_dict(), "model": candidate.restoration_state_dict()},
        path,
    )
    loaded, _ = load_checkpoint(path)
    loaded.set_noise(torch.tensor([0.001]), torch.tensor([1e-5]))
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        assert torch.equal(loaded(raw, variance, colors, wb), candidate(raw, variance, colors, wb))
    old = config(False).to_dict()
    del old["raw_spectral_residual"]
    assert ModelConfig.from_checkpoint(old).raw_spectral_residual is False


def test_optimizer_only_accelerates_spectral_parameters_and_rejects_invalid_groups():
    model = JointDemosaic(
        ModelConfig(
            restoration_backbone="pretrained-rgb",
            width=64,
            camera_conditioning=True,
            variance_stabilization=True,
            physical_anchors=True,
            raw_spectral_residual=True,
        )
    )
    optimizer = make_optimizer(model, {"lr": 1e-5, "raw_spectral_lr_multiplier": 20})
    first, second = optimizer.param_groups
    assert {id(p) for p in second["params"]} == {
        id(p) for p in model.pretrained_rgb.raw_spectral.parameters()
    }
    assert {id(p) for p in first["params"]}.isdisjoint({id(p) for p in second["params"]})
    assert {id(p) for group in optimizer.param_groups for p in group["params"]} == {
        id(p) for p in model.parameters() if p.requires_grad
    }
    set_learning_rate(optimizer, 3e-6)
    assert [g["lr"] for g in optimizer.param_groups] == [3e-6, 3e-6 * 20]
    for value in [0, -1, float("nan"), float("inf")]:
        with pytest.raises(ValueError, match="Spectral"):
            make_optimizer(model, {"raw_spectral_lr_multiplier": value})
    model.config.raw_spectral_residual = False
    with pytest.raises(ValueError, match="requires the spectral branch"):
        make_optimizer(model, {"raw_spectral_lr_multiplier": 20})
