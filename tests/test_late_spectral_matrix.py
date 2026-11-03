import numpy as np
import pytest
import torch

from demosaic.cfa import color_indices, malvar
from demosaic.late_spectral_detail import LateSpectralDetail
from demosaic.late_spectral_matrix import LateSpectralMatrixDetail, bounded_real_image_mixing


def measurements(pattern="RGGB", size=8):
    rng = torch.Generator(device="cpu").manual_seed(148)
    base = torch.rand(2, 3, 2 * size, 2 * size, generator=rng) * 0.03
    raw = torch.rand(2, 4, size, size, generator=rng) * 0.03
    return base, raw, torch.full_like(raw, 1e-5), color_indices(pattern)[None].expand(2, -1)


@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_zero_init_and_arbitrary_learned_constant_invariance(pattern):
    module = LateSpectralMatrixDetail(8)
    base, raw, var, colors = measurements(pattern)
    result, aux = module(base, raw, var, colors, return_aux=True)
    assert torch.equal(result, base) and aux["gain"].count_nonzero() == 0
    rng = torch.Generator(device="cpu").manual_seed(149)
    with torch.no_grad():
        for p in module.parameters():
            p.copy_(torch.randn(p.shape, generator=rng) * 0.3)
    constants = torch.tensor([0.002, 0.007, 0.03])[colors][:, :, None, None].expand_as(raw)
    for variance in (torch.zeros_like(var), var):
        assert torch.equal(module(base, constants, variance, colors), base)


def test_constructor_common_weights_rng_and_meta_device(monkeypatch):
    before = torch.get_rng_state()

    def forbidden(*args, **kwargs):
        raise AssertionError("Constructor seeded CUDA")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    with torch.device("meta"):
        scalar, matrix = LateSpectralDetail(8), LateSpectralMatrixDetail(8)
    assert torch.equal(before, torch.get_rng_state())
    assert sum(p.numel() for p in matrix.parameters()) == 31409
    assert len(matrix.state_dict()) == 12
    assert all(p.device.type == "cpu" for p in [*matrix.parameters(), *matrix.buffers()])
    common = [k for k in scalar.state_dict() if not k.startswith("frequency_out.")]
    assert len(common) == 10 and all(
        torch.equal(scalar.state_dict()[k], matrix.state_dict()[k]) for k in common
    )


def test_projection_matches_numpy_and_bounds_singular_values_with_finite_zero_gradient():
    rng = np.random.default_rng(148)
    values = (rng.normal(size=(3, 4, 4, 8, 8)) + 1j * rng.normal(size=(3, 4, 4, 8, 8))).astype(
        np.complex64
    ) * 3
    matrix = torch.from_numpy(values).requires_grad_()
    actual = bounded_real_image_mixing(matrix)
    reverse = (-np.arange(8)) % 8
    paired = (
        values.astype(np.complex128)
        + values.astype(np.complex128)[..., reverse, :][..., :, reverse].conj()
    ) / 2
    row_max = np.max(np.sum(np.abs(paired), axis=2), axis=1)
    col_max = np.max(np.sum(np.abs(paired), axis=1), axis=1)
    expected = paired / np.maximum(1, np.sqrt(row_max * col_max))[:, None, None]
    np.testing.assert_allclose(actual.detach().numpy(), expected, atol=2e-7, rtol=2e-6)
    singular = np.linalg.svd(
        np.moveaxis(actual.detach().numpy(), (1, 2), (-2, -1)), compute_uv=False
    )
    assert singular.max() <= 1 + 2e-6
    np.testing.assert_allclose(
        actual.detach().numpy(),
        actual.detach().numpy()[..., reverse, :][..., :, reverse].conj(),
        atol=1e-7,
    )
    actual.abs().square().sum().backward()
    assert torch.isfinite(matrix.grad).all() and matrix.grad.abs().max() > 0
    zero = torch.zeros(1, 4, 4, 8, 8, dtype=torch.complex64, requires_grad=True)
    result = bounded_real_image_mixing(zero)
    (result.real.sum() + result.imag.sum()).backward()
    assert torch.isfinite(zero.grad).all() and zero.grad.abs().max() > 0


def descriptor_numpy(spectrum, noise, colors):
    power = np.abs(spectrum) ** 2
    total = power.sum(1, keepdims=True)
    noise_sum = noise.sum(1)[:, None, None, None]
    scale = np.maximum(total + noise_sum, 1e-12)
    gram = spectrum[:, :, None] * spectrum[:, None, :].conj()
    channels = [power / scale]
    for i in range(4):
        for j in range(i + 1, 4):
            channels += [gram[:, i : i + 1, j].real / scale, gram[:, i : i + 1, j].imag / scale]
    channels.append(np.log1p(total / np.maximum(noise_sum, 1e-12)) / 8)
    n, _, h, w = spectrum.shape
    placement = np.eye(3)[colors].reshape(n, 12)
    channels.append(np.broadcast_to(placement[:, :, None, None], (n, 12, h, w)))
    fy, fx = np.meshgrid(np.fft.fftfreq(h), np.fft.fftfreq(w), indexing="ij")
    channels += [
        np.broadcast_to(fx[None, None], (n, 1, h, w)),
        np.broadcast_to(fy[None, None], (n, 1, h, w)),
    ]
    return np.concatenate(channels, 1)


def test_frequency_convolution_matrix_and_application_match_independent_numpy():
    module = LateSpectralMatrixDetail(8)
    rng = np.random.default_rng(151)
    observed = np.fft.fft2(rng.normal(size=(2, 4, 8, 8)), norm="ortho")
    innovation = observed - np.fft.fft2(rng.normal(size=(2, 4, 8, 8)) * 0.4, norm="ortho")
    noise = rng.uniform(0.1, 0.4, size=(2, 4))
    colors = np.array([[0, 1, 1, 2], [1, 2, 0, 1]])
    with torch.no_grad():
        module.frequency_out.weight.copy_(
            torch.from_numpy(
                rng.normal(size=module.frequency_out.weight.shape).astype(np.float32) * 0.2
            )
        )
        module.frequency_real_bias.copy_(
            torch.from_numpy(rng.normal(size=(4, 4)).astype(np.float32) * 0.1)
        )
    descriptor = descriptor_numpy(observed, noise, colors)
    features = np.concatenate([descriptor, descriptor_numpy(innovation, noise, colors)[:, :17]], 1)
    kernel = module.frequency_in.weight.detach().numpy().astype(float)
    hidden = (
        np.broadcast_to(
            module.frequency_in.bias.detach().numpy()[None, :, None, None], (2, 32, 8, 8)
        )
        .copy()
        .astype(float)
    )
    for y in range(3):
        for x in range(3):
            shifted = np.roll(features, (1 - y, 1 - x), axis=(-2, -1))
            hidden += np.einsum("oc,nchw->nohw", kernel[:, :, y, x], shifted)
    hidden /= 1 + np.exp(-hidden)
    values = np.einsum(
        "oc,nchw->nohw", module.frequency_out.weight.detach().numpy()[:, :, 0, 0], hidden
    ).reshape(2, 4, 4, 2, 8, 8)
    values[:, :, :, 0] += module.frequency_real_bias.detach().numpy()[None, :, :, None, None]
    values = np.tanh(values)
    raw_matrix = values[:, :, :, 0] + 1j * values[:, :, :, 1]
    reverse = (-np.arange(8)) % 8
    paired = (raw_matrix + raw_matrix[..., reverse, :][..., :, reverse].conj()) / 2
    norm_one = np.max(np.sum(np.abs(paired), axis=1), axis=1)
    norm_inf = np.max(np.sum(np.abs(paired), axis=2), axis=1)
    matrix = paired / np.maximum(1, np.sqrt(norm_one * norm_inf))[:, None, None]
    fy, fx = np.meshgrid(np.fft.fftfreq(8), np.fft.fftfreq(8), indexing="ij")
    radius = np.hypot(fx, fy)
    band = (
        np.sin(np.pi / 2 * np.clip((radius - 1 / 32) / (1 / 32), 0, 1)) ** 2
        * np.sin(np.pi / 2 * np.clip((0.45 - radius) / 0.05, 0, 1)) ** 2
    )
    expected = matrix * descriptor[:, :4].sum(1)[:, None, None] * band
    actual = module.frequency_gain(
        torch.from_numpy(observed.astype(np.complex64)),
        torch.from_numpy(innovation.astype(np.complex64)),
        torch.from_numpy(noise.astype(np.float32)),
        torch.from_numpy(colors),
    )
    np.testing.assert_allclose(actual.detach().numpy(), expected, atol=5e-7, rtol=2e-5)
    delta = module.apply_frequency_gain(actual, torch.from_numpy(innovation.astype(np.complex64)))
    oracle = sum(expected[:, :, i] * innovation[:, i : i + 1] for i in range(4))
    np.testing.assert_allclose(delta.detach().numpy(), oracle, atol=2e-6, rtol=3e-5)
    assert np.abs(expected.imag).max() > 0.001


def test_scalar_subfamily_and_coherent_green_averaging():
    module = LateSpectralMatrixDetail(8)
    rng = torch.Generator(device="cpu").manual_seed(152)
    innovation = torch.fft.fft2(torch.randn(1, 4, 8, 8, generator=rng), norm="ortho")
    scalar = torch.full((1, 1, 8, 8), 0.4)
    matrix = torch.zeros(1, 4, 4, 8, 8, dtype=torch.complex64)
    for i in range(4):
        matrix[:, i, i] = scalar[:, 0]
    torch.testing.assert_close(
        module.apply_frequency_gain(bounded_real_image_mixing(matrix), innovation),
        scalar * innovation,
        rtol=0,
        atol=0,
    )
    phase = complex(np.exp(1j * np.pi / 4))
    mixing = torch.zeros_like(matrix)
    mixing[0, 1, 1, 1, 1] = mixing[0, 2, 2, 1, 1] = 0.5
    mixing[0, 1, 2, 1, 1] = 0.5 / phase
    mixing[0, 2, 1, 1, 1] = 0.5 * phase
    mixing[..., 7, 7] = mixing[..., 1, 1].conj()
    signal = torch.zeros_like(innovation)
    signal[0, 1, 1, 1], signal[0, 2, 1, 1] = 1, phase
    signal[..., 7, 7] = signal[..., 1, 1].conj()
    noise = torch.zeros_like(signal)
    noise[0, 1, 1, 1], noise[0, 2, 1, 1] = 0.2, -0.2 * phase
    noise[..., 7, 7] = noise[..., 1, 1].conj()
    result = module.apply_frequency_gain(bounded_real_image_mixing(mixing), signal + noise)
    torch.testing.assert_close(result, signal, rtol=0, atol=2e-7)
    assert (signal + noise - signal).abs().sum() > 0.7


@pytest.mark.parametrize("amp", [False, True])
def test_train_all_tensors_and_continue_optimizer_from_checkpoint(tmp_path, amp):
    module = LateSpectralMatrixDetail(8)
    base, raw, var, colors = measurements()
    target = malvar(raw, colors)
    optimizer = torch.optim.AdamW(module.parameters(), lr=0.001)
    maxima = {k: 0.0 for k, _ in module.named_parameters()}
    for step in range(4):
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
            prediction, aux = module(base, raw, var, colors, return_aux=True)
            loss = (prediction - target).square().mean() + module.spectral_supervision(
                target, colors, aux
            )
        loss.backward()
        for k, p in module.named_parameters():
            assert p.grad is not None and torch.isfinite(p.grad).all()
            maxima[k] = max(maxima[k], float(p.grad.abs().max()))
        optimizer.step()
        if step == 1:
            dest = tmp_path / "resume.pt"
            torch.save({"model": module.state_dict(), "optimizer": optimizer.state_dict()}, dest)
            state = torch.load(dest, weights_only=True)
            module = LateSpectralMatrixDetail(8)
            module.load_state_dict(state["model"], strict=True)
            optimizer = torch.optim.AdamW(module.parameters(), lr=0.001)
            optimizer.load_state_dict(state["optimizer"])
    assert len(maxima) == 12 and min(maxima.values()) > 0
    assert len(optimizer.state) == 12 and all(
        float(v["step"]) == 4 for v in optimizer.state.values()
    )


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_cuda_training_parity_and_rng_preservation():
    torch.cuda.init()
    module = LateSpectralMatrixDetail(8)
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    cuda = LateSpectralMatrixDetail(8).cuda()
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    base, raw, var, colors = measurements()
    with torch.no_grad():
        module.frequency_out.weight.fill_(0.01)
        module.frequency_real_bias.fill_(0.02)
    cuda.load_state_dict(module.state_dict(), strict=True)
    expected = module(base, raw, var, colors)
    with torch.autocast("cuda", dtype=torch.bfloat16):
        actual = cuda(base.cuda(), raw.cuda(), var.cuda(), colors.cuda())
    torch.testing.assert_close(actual.cpu(), expected, atol=2e-7, rtol=2e-5)
    loss = actual.square().mean()
    loss.backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in cuda.parameters())
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
