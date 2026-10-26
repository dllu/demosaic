import math

import numpy as np
import pytest
import torch

from demosaic.cfa import color_indices
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.raw_frequency_features import (
    RawFrequencyFeatures,
    frequency_descriptor,
    hermitian_projection,
)
from demosaic.train import make_optimizer, set_learning_rate


def test_hermitian_projection_is_real_and_keeps_negative_complex_components():
    generator = torch.Generator().manual_seed(72)
    values = torch.complex(
        torch.randn(2, 3, 8, 8, generator=generator), torch.randn(2, 3, 8, 8, generator=generator)
    )
    actual = hermitian_projection(values)
    reverse = torch.tensor([0, 7, 6, 5, 4, 3, 2, 1])
    assert torch.equal(actual, actual[:, :, reverse][:, :, :, reverse].conj())
    assert torch.fft.ifft2(actual).imag.abs().max() == 0
    assert (actual.real < 0).any() and (actual.imag < 0).any()


def test_descriptor_preserves_signed_cross_and_single_phase_evidence():
    values = torch.zeros(1, 4, 8, 8, dtype=torch.complex64)
    values[:, 0] = 1
    values[:, 1] = -1
    descriptor = frequency_descriptor(values, torch.zeros(1, 4), color_indices("RGGB")[None])
    torch.testing.assert_close(descriptor[:, 4], torch.full((1, 8, 8), -0.5))
    values[:, 1] = 1j
    descriptor = frequency_descriptor(values, torch.zeros(1, 4), color_indices("RGGB")[None])
    torch.testing.assert_close(descriptor[:, 5], torch.full((1, 8, 8), -0.5))
    values[:, 0] = 0
    descriptor = frequency_descriptor(values, torch.zeros(1, 4), color_indices("RGGB")[None])
    assert descriptor[:, 1].min() == 1 and torch.isfinite(descriptor).all()


def test_learned_mixing_preserves_common_phase_rotations_after_nonzero_adaptation():
    generator = torch.Generator().manual_seed(73)
    model = RawFrequencyFeatures(max_window=8)
    with torch.no_grad():
        model.kernel_out.weight.copy_(
            torch.randn(model.kernel_out.weight.shape, generator=generator) * 0.03
        )
        model.kernel_out.bias.copy_(
            torch.randn(model.kernel_out.bias.shape, generator=generator) * 0.03
        )
    spectrum = torch.fft.fft2(torch.randn(2, 4, 8, 8, generator=generator), norm="ortho")
    frequency = torch.fft.fftfreq(8)
    phase = torch.exp(-2j * math.pi * (frequency[:, None] + 2 * frequency[None, :]))
    noise = torch.full((2, 4), 0.01)
    colors = torch.stack((color_indices("BGGR"), color_indices("GRBG")))
    first = model.mix_spectrum(spectrum, noise, colors)
    second = model.mix_spectrum(spectrum * phase, noise, colors)
    torch.testing.assert_close(second, first * phase, atol=2e-6, rtol=2e-6)


def test_nonconstant_phase_features_preserve_channels_last_layout():
    generator = torch.Generator().manual_seed(78)
    model = RawFrequencyFeatures(max_window=8)
    with torch.no_grad():
        model.kernel_out.weight.copy_(
            torch.randn(model.kernel_out.weight.shape, generator=generator) * 0.02
        )
    model.to(memory_format=torch.channels_last)
    raw = torch.rand(2, 4, 9, 13, generator=generator)
    variance = torch.rand(2, 4, 9, 13, generator=generator) * 0.001
    colors = torch.stack((color_indices("GRBG"), color_indices("BGGR")))
    first = model.packed_features(raw, variance, colors)
    second = model.packed_features(
        raw.contiguous(memory_format=torch.channels_last),
        variance.contiguous(memory_format=torch.channels_last),
        colors,
    )
    torch.testing.assert_close(first, second, atol=0, rtol=0)


def test_constructor_never_seeds_cuda_or_uses_the_ambient_default_device(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Adapter construction must not touch CUDA RNG")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    before = torch.get_rng_state()
    with torch.device("meta"):
        model = RawFrequencyFeatures(max_window=8)
    assert torch.equal(before, torch.get_rng_state())
    assert all(t.device.type == "cpu" for t in [*model.parameters(), *model.buffers()])


def test_initial_latent_frames_match_independent_dense_DFT_and_explicit_overlap_add():
    height, width, size = 9, 11, 8
    y, x = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
    values = np.stack(
        [0.18 + 0.03 * np.sin(1.3 * x + 0.6 * y + c * 0.4) + 0.002 * x * x for c in range(4)]
    ).astype(np.float32)
    model = RawFrequencyFeatures(max_window=size)
    actual = (
        model.packed_features(
            torch.from_numpy(values[None]),
            torch.full((1, 4, height, width), 0.0001),
            color_indices("GBRG"),
        )[0]
        .detach()
        .numpy()
    )
    hop = size // 2
    padded = np.pad(
        values.astype(float) - values[:, :1, :1],
        ((0, 0), (hop, hop + (-height % hop)), (hop, hop + (-width % hop))),
        mode="edge",
    )
    py, px = np.meshgrid(np.arange(size), np.arange(size), indexing="ij")
    window = np.sin(np.pi * py / size) * np.sin(np.pi * px / size)
    q = np.stack([np.ones_like(px), 2 * px / (size - 1) - 1, 2 * py / (size - 1) - 1], -1).reshape(
        -1, 3
    )
    fourier = (
        np.exp(
            -2j
            * np.pi
            * (
                py.ravel()[:, None] * py.ravel()[None] / size
                + px.ravel()[:, None] * px.ravel()[None] / size
            )
        )
        / size
    )
    # Explicit fixed real mixing, independent of the module's stored buffer.
    mixing = np.concatenate(
        (np.eye(4), np.array([[1, 1, 1, 1], [1, -1, 1, -1], [1, 1, -1, -1], [1, -1, -1, 1]]) / 2)
    )
    numerator = np.zeros((8, *padded.shape[-2:]))
    denominator = np.zeros(padded.shape[-2:])
    for iy in range(0, padded.shape[1] - size + 1, hop):
        for ix in range(0, padded.shape[2] - size + 1, hop):
            coefficients = []
            for plane in padded[:, iy : iy + size, ix : ix + size]:
                centered = (plane - plane[0, 0]).ravel()
                beta = np.linalg.lstsq(
                    window.ravel()[:, None] * q, window.ravel() * centered, rcond=None
                )[0]
                spectrum = fourier @ (window.ravel() * (centered - q @ beta))
                spectrum[0] = 0
                coefficients.append(spectrum)
            for c, spectrum in enumerate(mixing @ np.stack(coefficients)):
                inverse = (fourier.conj().T @ spectrum).real.reshape(size, size)
                numerator[c, iy : iy + size, ix : ix + size] += inverse * window
            denominator[iy : iy + size, ix : ix + size] += window**2
    expected = (
        numerator[:, hop : hop + height, hop : hop + width]
        / denominator[hop : hop + height, hop : hop + width]
    )
    np.testing.assert_allclose(actual, expected, atol=3e-7, rtol=5e-5)


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("variance", [0, 0.0003])
def test_learned_branch_is_exactly_zero_for_constant_per_phase_colors(pattern, variance):
    generator = torch.Generator().manual_seed(74)
    model = RawFrequencyFeatures(max_window=8)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.1)
    colors = color_indices(pattern)
    rgb = torch.tensor([-0.03, 0.18, 1.2])
    raw = rgb[colors][None, :, None, None].expand(1, 4, 9, 13)
    result = model(raw, torch.full_like(raw, variance), colors)
    assert result.shape == (1, 64, 18, 26) and result.count_nonzero() == 0


@pytest.mark.parametrize("amp", [False, True])
def test_zero_start_rng_and_all_layers_learn_with_finite_gradients(amp):
    before = torch.get_rng_state()
    model = RawFrequencyFeatures(max_window=8)
    assert torch.equal(before, torch.get_rng_state())
    generator = torch.Generator().manual_seed(75)
    raw = torch.rand(2, 4, 9, 13, generator=generator)
    variance = torch.full_like(raw, 0.0003)
    colors = torch.stack((color_indices("RGGB"), color_indices("GBRG")))
    target = torch.rand(2, 64, 18, 26, generator=generator) - 0.5
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01, weight_decay=0)
    for step in range(3):
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
            output = model(raw, variance, colors)
        assert output.dtype == torch.float32 and torch.isfinite(output).all()
        if step == 0:
            assert output.count_nonzero() == 0
        (output - target).square().mean().backward()
        for parameter in model.parameters():
            assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
            if step == 2:
                assert parameter.grad.count_nonzero()
        optimizer.step()


def model_config(enabled):
    return ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        variance_stabilization=True,
        physical_anchors=True,
        raw_frequency_features=enabled,
    )


@pytest.mark.parametrize("amp", [False, True])
def test_complete_model_preserves_parent_function_gradients_rng_and_checkpoint(tmp_path, amp):
    torch.manual_seed(76)
    parent = JointDemosaic(model_config(False))
    after = torch.get_rng_state()
    torch.manual_seed(76)
    candidate = JointDemosaic(model_config(True))
    assert torch.equal(after, torch.get_rng_state())
    missing = candidate.load_state_dict(parent.restoration_state_dict(), strict=False)
    assert not missing.unexpected_keys and len(missing.missing_keys) == 5
    assert all(k.startswith("pretrained_rgb.raw_frequency.") for k in missing.missing_keys)
    generator = torch.Generator().manual_seed(77)
    raw = torch.rand(1, 4, 12, 16, generator=generator) * 0.5
    variance = torch.full_like(raw, 0.0003)
    colors = color_indices("BGGR")
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    for model in (parent, candidate):
        model.set_noise(0.001, 1e-5)
    with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        first, first_aux = parent(raw, variance, colors, wb, auxiliary=True)
        second, second_aux = candidate(raw, variance, colors, wb, auxiliary=True)
    assert torch.equal(first, second) and torch.equal(first_aux, second_aux)
    first.square().mean().backward()
    second.square().mean().backward()
    other = dict(candidate.named_parameters())
    for name, parameter in parent.named_parameters():
        assert torch.equal(parameter.grad, other[name].grad), name
    assert candidate.pretrained_rgb.raw_frequency.project.weight.grad.count_nonzero()
    with torch.no_grad():
        candidate.pretrained_rgb.raw_frequency.project.weight.fill_(0.02)
    path = tmp_path / "frequency-adapter.pt"
    torch.save(
        {"model_config": candidate.config.to_dict(), "model": candidate.restoration_state_dict()},
        path,
    )
    loaded, _ = load_checkpoint(path)
    loaded.set_noise(0.001, 1e-5)
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        assert torch.equal(candidate(raw, variance, colors, wb), loaded(raw, variance, colors, wb))
    old = model_config(False).to_dict()
    del old["raw_frequency_features"]
    assert ModelConfig.from_checkpoint(old).raw_frequency_features is False


def test_optimizer_assigns_only_adapter_parameters_to_new_lr_group():
    model = JointDemosaic(model_config(True))
    optimizer = make_optimizer(model, {"lr": 1e-5, "raw_frequency_lr_multiplier": 20})
    first, second = optimizer.param_groups
    expected = {id(p) for p in model.pretrained_rgb.raw_frequency.parameters()}
    assert {id(p) for p in second["params"]} == expected
    assert expected.isdisjoint({id(p) for p in first["params"]})
    assert {id(p) for group in optimizer.param_groups for p in group["params"]} == {
        id(p) for p in model.parameters() if p.requires_grad
    }
    set_learning_rate(optimizer, 3e-6)
    assert [g["lr"] for g in optimizer.param_groups] == [3e-6, 6e-5]
    for invalid in (0, -1, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="Frequency"):
            make_optimizer(model, {"raw_frequency_lr_multiplier": invalid})
    model.config.raw_frequency_features = False
    with pytest.raises(ValueError, match="requires RAW frequency"):
        make_optimizer(model, {"raw_frequency_lr_multiplier": 20})


@pytest.mark.parametrize(
    "override",
    [
        {"raw_frequency_features": 1},
        {"restoration_backbone": "local"},
        {"variance_stabilization": False},
        {"physical_anchors": False},
        {"rgb_processing_scale": 2},
        {"raw_spectral_residual": True},
        {"raw_directional_residual": True},
        {"raw_kernel_reconstruction": True},
        {"adc_cfa_projection": True},
        {"late_rgb_refinement": "global"},
    ],
)
def test_unsupported_frequency_architecture_combinations_rejected(override):
    values = model_config(True).to_dict()
    values.update(override)
    with pytest.raises(ValueError, match="frequency"):
        JointDemosaic(ModelConfig(**values))
