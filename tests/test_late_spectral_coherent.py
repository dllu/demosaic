"""Independent CFA transport, native bounds and support-evidence fixtures."""

import math

import numpy as np
import pytest
import torch
from test_late_spectral_matrix import descriptor_numpy, measurements

from demosaic.cfa import color_indices, malvar
from demosaic.late_spectral_coherent import (
    LateSpectralAlignedMatrixDetail,
    LateSpectralCoherentDetail,
    matrix_to_native,
    phase_transport,
    separable_box,
    to_coherent,
)
from demosaic.late_spectral_matrix import LateSpectralMatrixDetail


def numpy_basis(colors, size):
    result = []
    fy, fx = np.meshgrid(np.fft.fftfreq(size), np.fft.fftfreq(size), indexing="ij")
    transport = np.stack(
        [np.exp(-1j * np.pi * (y * fy + x * fx)) for y, x in [(0, 0), (0, 1), (1, 0), (1, 1)]]
    )
    for color in colors:
        order = [
            int(np.flatnonzero(color == 0)[0]),
            *np.flatnonzero(color == 1).tolist(),
            int(np.flatnonzero(color == 2)[0]),
        ]
        R = np.eye(4)[order]
        R[[1, 2]] = np.stack([(R[1] + R[2]) / math.sqrt(2), (R[1] - R[2]) / math.sqrt(2)])
        result.append(R[:, :, None, None] * transport[None])
    return np.stack(result)


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_unitary_phase_transport_and_true_native_green_carrier(pattern):
    size = 32
    colors = color_indices(pattern)[None]
    U = numpy_basis(colors.numpy(), size)
    y, x = np.mgrid[:size, :size]
    raw = np.stack(
        [
            np.cos(2 * np.pi * (3 * (2 * x + dx) + 2 * (2 * y + dy)) / (2 * size))
            for dy, dx in [(0, 0), (0, 1), (1, 0), (1, 1)]
        ]
    )[None]
    spectrum = np.fft.fft2(raw, norm="ortho")
    expected = np.einsum("nbphw,nphw->nbhw", U, spectrum)
    actual = to_coherent(
        torch.tensor(spectrum, dtype=torch.complex64), colors, phase_transport(size)
    )
    np.testing.assert_allclose(actual.numpy(), expected, rtol=3e-6, atol=3e-6)
    assert np.max(abs(expected[:, 2])) < 1e-13
    assert abs(expected[0, 1, 2, 3]) == pytest.approx(size / math.sqrt(2), abs=1e-12)
    product = np.einsum("nbphw,ncphw->nbchw", U, np.conj(U))
    np.testing.assert_allclose(
        product, np.broadcast_to(np.eye(4)[None, :, :, None, None], product.shape), atol=1e-14
    )
    rng = np.random.default_rng(149)
    H = rng.normal(size=(1, 4, 4, size, size)) + 1j * rng.normal(size=(1, 4, 4, size, size))
    native = matrix_to_native(
        torch.tensor(H, dtype=torch.complex64), colors, phase_transport(size)
    ).numpy()
    independent = np.einsum("nbphw,nbchw,ncqhw->npqhw", U.conj(), H, U)
    np.testing.assert_allclose(native, independent, atol=3e-6, rtol=3e-6)


def test_initialization_parameters_and_rng_under_meta_device():
    before = torch.get_rng_state().clone()
    with torch.device("meta"):
        native = LateSpectralMatrixDetail(8)
        aligned = LateSpectralAlignedMatrixDetail(8)
        context = LateSpectralCoherentDetail(8)
    assert torch.equal(before, torch.get_rng_state())
    assert sum(p.numel() for p in aligned.parameters()) == 31409
    assert sum(p.numel() for p in context.parameters()) == 33353
    assert len(native.state_dict()) == len(aligned.state_dict()) == len(context.state_dict()) == 12
    for name, value in native.state_dict().items():
        assert torch.equal(value, aligned.state_dict()[name])
        other = context.state_dict()[name]
        assert torch.equal(value, other[:, :28] if name == "local_in.weight" else other)
    assert context.local_in.weight[:, 28:].count_nonzero() == 0
    assert all(
        v.device.type == "cpu"
        for m in [native, aligned, context]
        for v in [*m.parameters(), *m.buffers()]
    )


@pytest.mark.parametrize("kind", [LateSpectralAlignedMatrixDetail, LateSpectralCoherentDetail])
@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_zero_initialization_and_arbitrary_learned_constants(kind, pattern):
    m = kind(8)
    base, raw, var, colors = measurements(pattern)
    assert torch.equal(m(base, raw, var, colors), base)
    rng = torch.Generator(device="cpu").manual_seed(14902)
    with torch.no_grad():
        for p in m.parameters():
            p.copy_(torch.randn(p.shape, generator=rng) * 0.1)
    raw = torch.tensor([0.003, 0.007, 0.02])[colors][:, :, None, None].expand_as(raw)
    for variance in [var, torch.zeros_like(var)]:
        assert torch.equal(m(base, raw, variance, colors), base)


def test_native_bounded_gain_matches_independent_numpy_complete_estimator():
    m = LateSpectralAlignedMatrixDetail(8)
    rng = np.random.default_rng(14903)
    observed = np.fft.fft2(rng.normal(size=(2, 4, 8, 8)), norm="ortho")
    innovation = observed - np.fft.fft2(rng.normal(size=(2, 4, 8, 8)) * 0.3, norm="ortho")
    noise = rng.uniform(0.1, 0.4, size=(2, 4))
    colors = np.array([[0, 1, 1, 2], [1, 2, 0, 1]])
    U = numpy_basis(colors, 8)
    z = np.einsum("nbphw,nphw->nbhw", U, observed)
    residual = np.einsum("nbphw,nphw->nbhw", U, innovation)
    R = abs(U[:, :, :, 0, 0])
    bn = np.einsum("nbp,np->nb", R**2, noise)
    canonical = np.array([[0, 1, 1, 2]] * 2)
    features = np.concatenate(
        [descriptor_numpy(z, bn, canonical), descriptor_numpy(residual, bn, canonical)[:, :17]], 1
    )
    with torch.no_grad():
        m.frequency_out.weight.copy_(
            torch.tensor(rng.normal(size=m.frequency_out.weight.shape).astype("float32") * 0.2)
        )
        m.frequency_real_bias.copy_(torch.tensor(rng.normal(size=(4, 4)).astype("float32") * 0.1))
    hidden = (
        np.broadcast_to(m.frequency_in.bias.detach().numpy()[None, :, None, None], (2, 32, 8, 8))
        .copy()
        .astype(float)
    )
    for j in range(3):
        for i in range(3):
            hidden += np.einsum(
                "oc,nchw->nohw",
                m.frequency_in.weight.detach().numpy()[:, :, j, i],
                np.roll(features, (1 - j, 1 - i), axis=(-2, -1)),
            )
    hidden = hidden / (1 + np.exp(-hidden))
    logits = np.einsum(
        "oc,nchw->nohw", m.frequency_out.weight.detach().numpy()[:, :, 0, 0], hidden
    ).reshape(2, 4, 4, 2, 8, 8)
    logits[:, :, :, 0] += m.frequency_real_bias.detach().numpy()[None, :, :, None, None]
    H = np.tanh(logits[:, :, :, 0]) + 1j * np.tanh(logits[:, :, :, 1])
    native = np.einsum("nbphw,nbchw,ncqhw->npqhw", U.conj(), H, U)
    reverse = (-np.arange(8)) % 8
    native = (native + native[..., reverse, :][..., :, reverse].conj()) * 0.5
    norm = np.sqrt(
        np.max(np.sum(abs(native), axis=1), axis=1) * np.max(np.sum(abs(native), axis=2), axis=1)
    )
    native /= np.maximum(1, norm)[:, None, None]
    power = descriptor_numpy(observed, noise, colors)[:, :4].sum(1)
    expected = native * power[:, None, None] * m.band_8.numpy()
    actual = m.frequency_gain(
        torch.tensor(observed, dtype=torch.complex64),
        torch.tensor(innovation, dtype=torch.complex64),
        torch.tensor(noise, dtype=torch.float32),
        torch.tensor(colors),
    )
    np.testing.assert_allclose(actual.detach().numpy(), expected, rtol=3e-5, atol=7e-7)
    cap = power * m.band_8.numpy()
    bound = np.sqrt(
        np.max(np.sum(abs(actual.detach().numpy()), axis=1), axis=1)
        * np.max(np.sum(abs(actual.detach().numpy()), axis=2), axis=1)
    )
    assert np.max(bound - cap) < 2e-6
    delta = m.apply_frequency_gain(actual, torch.tensor(innovation, dtype=torch.complex64))
    assert torch.fft.ifft2(delta).imag.abs().max() < 1e-6


def np_box(values, size):
    pad = size // 2
    v = np.pad(values, [(0, 0), (0, 0), (pad, pad), (pad, pad)], mode="edge")
    return np.lib.stride_tricks.sliding_window_view(v, (size, size), axis=(-2, -1)).mean((-2, -1))


def test_support_features_match_independent_overlap_and_spatial_averages():
    m = LateSpectralCoherentDetail(8)
    _base, raw, var, colors = [v[:1] for v in measurements()]
    observed, g = m.analysis(raw)
    parent = torch.zeros_like(raw)
    features = m.local_features(raw, parent, var, torch.zeros_like(raw), colors, observed, None, g)
    U = numpy_basis(colors.numpy().repeat(g[5], axis=0), 8)
    spectrum = np.einsum("nbphw,nphw->nbhw", U, observed.numpy())[:, 1:3] * m.band_8.numpy()
    frames = np.fft.ifft2(spectrum, norm="ortho").real * m.window_8.numpy()
    total = np.zeros((1, 2, *g[6]))
    weights = np.zeros(g[6])
    ny = (g[6][0] - 8) // 4 + 1
    nx = (g[6][1] - 8) // 4 + 1
    for j in range(ny):
        for i in range(nx):
            total[..., j * 4 : j * 4 + 8, i * 4 : i * 4 + 8] += frames[j * nx + i]
            weights[j * 4 : j * 4 + 8, i * 4 : i * 4 + 8] += m.window_8.numpy() ** 2
    green = total[..., 4:12, 4:12] / weights[4:12, 4:12]
    expected = []
    for size in [9, 33, 129]:
        energy = np_box(green**2, size)
        reference = np.maximum(np_box(var.numpy().mean(1, keepdims=True), size), (1 / 65535) ** 2)
        a, b = energy[:, :1], energy[:, 1:]
        expected.extend(
            [np.log1p(a / reference), np.log1p(b / reference), (a - b) / (a + b + reference)]
        )
        np.testing.assert_allclose(
            separable_box(torch.from_numpy(green.astype("float32")), size).numpy(),
            np_box(green, size),
            rtol=3e-5,
            atol=1e-8,
        )
    np.testing.assert_allclose(
        features[:, 28:].detach().numpy(), np.concatenate(expected, 1), rtol=3e-5, atol=3e-6
    )


@pytest.mark.parametrize("kind", [LateSpectralAlignedMatrixDetail, LateSpectralCoherentDetail])
@pytest.mark.parametrize("amp", [False, True])
def test_all_tensors_train_and_resume(kind, amp, tmp_path):
    m = kind(8)
    base, raw, var, colors = measurements()
    target = malvar(raw, colors)
    opt = torch.optim.AdamW(m.parameters(), lr=0.001)
    maximum = {k: 0.0 for k, _ in m.named_parameters()}
    extra_max = 0.0
    for step in range(4):
        opt.zero_grad(set_to_none=True)
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
            out, aux = m(base, raw, var, colors, return_aux=True)
            loss = (out - target).square().mean() + m.spectral_supervision(target, colors, aux)
        loss.backward()
        for k, p in m.named_parameters():
            assert p.grad is not None and torch.isfinite(p.grad).all()
            maximum[k] = max(maximum[k], float(p.grad.abs().max()))
        if kind is LateSpectralCoherentDetail:
            extra_max = max(extra_max, float(m.local_in.weight.grad[:, 28:].abs().max()))
        opt.step()
        if step == 1:
            path = tmp_path / "resume.pt"
            torch.save({"model": m.state_dict(), "optimizer": opt.state_dict()}, path)
            state = torch.load(path, weights_only=True)
            m = kind(8)
            m.load_state_dict(state["model"], strict=True)
            opt = torch.optim.AdamW(m.parameters(), lr=0.001)
            opt.load_state_dict(state["optimizer"])
    assert len(maximum) == 12 and min(maximum.values()) > 0
    assert len(opt.state) == 12 and all(float(v["step"]) == 4 for v in opt.state.values())
    if kind is LateSpectralCoherentDetail:
        assert extra_max > 0


@pytest.mark.parametrize("kind", [LateSpectralAlignedMatrixDetail, LateSpectralCoherentDetail])
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_cuda_parity_gradients_and_rng(kind):
    torch.cuda.init()
    m = kind(8)
    before, cbefore = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    other = kind(8).cuda()
    with torch.no_grad():
        m.frequency_out.weight.fill_(0.01)
        m.frequency_real_bias.fill_(0.02)
    other.load_state_dict(m.state_dict(), strict=True)
    args = measurements()
    expected = m(*args)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        actual = other(*[a.cuda() for a in args])
    torch.testing.assert_close(actual.cpu(), expected, rtol=3e-5, atol=2e-7)
    actual.square().mean().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in other.parameters())
    assert torch.equal(before, torch.get_rng_state()) and torch.equal(
        cbefore, torch.cuda.get_rng_state()
    )
