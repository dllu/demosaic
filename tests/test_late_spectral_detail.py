import math

import numpy as np
import pytest
import torch

from demosaic.cfa import color_indices, malvar
from demosaic.late_spectral_detail import LateSpectralDetail


def inputs(size=16):
    generator = torch.Generator().manual_seed(147)
    base = torch.rand(1, 3, 2 * size, 2 * size, generator=generator) * 0.03
    packed = torch.rand(1, 4, size, size, generator=generator) * 0.03
    return base, packed, torch.full_like(packed, 1e-5), color_indices("RGGB")[None]


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_initial_output_is_exact_parent_for_nonconstant_measurements(pattern):
    model = LateSpectralDetail(16)
    base, packed, variance, _ = inputs()
    colors = color_indices(pattern)[None]
    result, aux = model(base, packed, variance, colors, return_aux=True)
    assert torch.equal(result, base)
    assert aux["correction"].count_nonzero() == aux["gain"].count_nonzero() == 0


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
@pytest.mark.parametrize("noise", [0, 1e-5])
def test_learned_component_cannot_change_colored_constants_even_with_nonconstant_parent(
    pattern, noise
):
    model = LateSpectralDetail(16)
    generator = torch.Generator().manual_seed(148)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.1)
    base, _, _, _ = inputs()
    colors = color_indices(pattern)[None]
    raw = torch.tensor([0.005, 0.02, 0.04])[colors][:, :, None, None].expand(1, 4, 16, 16)
    result = model(base, raw, torch.full_like(raw, noise), colors)
    assert torch.equal(result, base)


def test_constructor_preserves_rng_and_ignores_ambient_default_device(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Constructor must not seed CUDA")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    before = torch.get_rng_state()
    with torch.device("meta"):
        module = LateSpectralDetail(8)
    assert torch.equal(before, torch.get_rng_state())
    assert all(v.device.type == "cpu" for v in [*module.parameters(), *module.buffers()])


def test_analysis_gain_noise_units_and_synthesis_match_independent_dense_dft():
    height, width, size = 9, 11, 8
    yy, xx = np.meshgrid(np.arange(height), np.arange(width), indexing="ij")
    raw = np.stack([0.02 + 0.001 * np.sin(.8 * xx + .4 * yy + c) for c in range(4)]).astype(np.float32)
    variance = np.stack([np.full((height, width), 1e-5) + xx * 1e-7 * (c + 1) for c in range(4)]).astype(np.float32)
    model = LateSpectralDetail(size)
    spectra, geometry = model.analysis(torch.from_numpy(raw[None]))
    noise = model.noise_power(torch.from_numpy(variance[None]), geometry)
    hop = size // 2
    pad = ((0, 0), (hop, hop + (-height % hop)), (hop, hop + (-width % hop)))
    values = np.pad(raw.astype(float) - raw[:, :1, :1], pad, mode="edge")
    var = np.pad(variance.astype(float), pad, mode="edge")
    py, px = np.meshgrid(np.arange(size), np.arange(size), indexing="ij")
    window = np.sin(np.pi * py / size) * np.sin(np.pi * px / size)
    basis = np.stack([np.ones_like(px), 2 * px / (size - 1) - 1, 2 * py / (size - 1) - 1], -1).reshape(-1, 3)
    dft = np.exp(-2j * np.pi * (py.ravel()[:, None] * py.ravel()[None] + px.ravel()[:, None] * px.ravel()[None]) / size) / size
    expected, expected_noise, origins = [], [], []
    for y in range(0, values.shape[-2] - size + 1, hop):
        for x in range(0, values.shape[-1] - size + 1, hop):
            channels = []
            for phase in values[:, y:y+size, x:x+size]:
                v = (phase - phase[0, 0]).ravel()
                beta = np.linalg.lstsq(window.ravel()[:, None] * basis, window.ravel() * v, rcond=None)[0]
                coefficient = dft @ (window.ravel() * (v - basis @ beta))
                coefficient[0] = 0
                channels.append(coefficient.reshape(size, size))
            expected.append(channels)
            expected_noise.append((var[:, y:y+size, x:x+size] * window**2).mean((-2, -1)))
            origins.append((y, x))
    expected, expected_noise = np.array(expected), np.array(expected_noise)
    np.testing.assert_allclose(spectra.detach().numpy(), expected, atol=2e-8, rtol=2e-4)
    np.testing.assert_allclose(noise.numpy(), expected_noise, atol=2e-12, rtol=2e-6)
    with torch.no_grad():
        model.frequency_out.bias.fill_(math.atanh(.4))
    colors = color_indices("BGGR")[None].expand(len(expected), -1)
    gain = model.frequency_gain(spectra, spectra, noise, colors)
    frequency = np.fft.fftfreq(size)
    radius = np.hypot(frequency[:, None], frequency[None])
    band = np.sin(np.pi/2*np.clip((radius-1/32)/(1/32), 0, 1))**2 * np.sin(np.pi/2*np.clip((.45-radius)/.05, 0, 1))**2
    power = np.sum(np.abs(expected)**2, axis=1, keepdims=True)
    desired_gain = .4 * power / np.maximum(power + expected_noise.sum(1)[:, None, None, None], 1e-12) * band
    np.testing.assert_allclose(gain.detach().numpy(), desired_gain, atol=2e-6, rtol=2e-4)
    desired_delta = desired_gain * expected
    actual = model.synthesis(gain * spectra, geometry).detach().numpy()[0]
    numerator = np.zeros_like(values)
    denominator = np.zeros(values.shape[-2:])
    for frame, (y, x) in zip(desired_delta, origins, strict=True):
        numerator[:, y:y+size, x:x+size] += np.fft.ifft2(frame, norm="ortho").real * window
        denominator[y:y+size, x:x+size] += window**2
    expected_result = numerator[:, hop:hop+height, hop:hop+width] / denominator[hop:hop+height, hop:hop+width]
    np.testing.assert_allclose(actual, expected_result, atol=2e-8, rtol=2e-4)
    assert (actual < 0).any() and (actual > 0).any()


@pytest.mark.parametrize("amp", [False, True])
def test_learning_reaches_frequency_and_local_support_parameters_and_resumes(tmp_path, amp):
    model = LateSpectralDetail(8)
    base, packed, variance, colors = inputs(8)
    target = malvar(packed, colors)
    optimizer = torch.optim.AdamW(model.parameters(), lr=.001)
    maxima = {n: 0. for n, _ in model.named_parameters()}
    for _ in range(4):
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
            result, aux = model(base, packed, variance, colors, return_aux=True)
            loss = (result-target).square().mean() + .01 * model.spectral_supervision(target, colors, aux)
        loss.backward()
        for name, p in model.named_parameters():
            assert p.grad is not None and torch.isfinite(p.grad).all()
            maxima[name] = max(maxima[name], float(p.grad.abs().max()))
        optimizer.step()
    assert result.dtype == torch.float32 and all(v > 0 for v in maxima.values())
    path = tmp_path / "branch.pt"
    torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict()}, path)
    restored = LateSpectralDetail(8)
    state = torch.load(path, weights_only=True)
    restored.load_state_dict(state["model"], strict=True)
    fresh = torch.optim.AdamW(restored.parameters(), lr=.001)
    fresh.load_state_dict(state["optimizer"])
    assert len(fresh.state) == len(list(restored.parameters())) == 12
    assert all(float(v["step"]) == 4 for v in fresh.state.values())
    torch.testing.assert_close(restored(base, packed, variance, colors), model(base, packed, variance, colors), atol=0, rtol=0)


def test_cuda_matches_cpu_and_preserves_cuda_rng():
    if not torch.cuda.is_available():
        pytest.skip("CUDA unavailable")
    model = LateSpectralDetail(8)
    with torch.no_grad():
        model.frequency_out.bias.fill_(.2)
    args = inputs(8)
    expected = model(*args).detach()
    model = model.cuda()
    before = torch.cuda.get_rng_state()
    with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
        actual = model(*(a.cuda() for a in args)).cpu()
    torch.testing.assert_close(actual, expected, atol=2e-7, rtol=2e-5)
    assert torch.equal(before, torch.cuda.get_rng_state())


@pytest.mark.parametrize("change", ["raw", "variance", "parent", "colors"])
def test_mismatched_shapes_rejected(change):
    model = LateSpectralDetail(8)
    base, raw, variance, colors = inputs(8)
    if change == "raw":
        raw = raw[:, :3]
    elif change == "variance":
        variance = variance[..., :-1]
    elif change == "parent":
        base = base[..., :-1]
    else:
        colors = colors[:, :3]
    with pytest.raises(ValueError):
        model(base, raw, variance, colors)
