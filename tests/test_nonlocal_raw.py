"""Independent Bayer orientation and measured-sample consistency checks."""

import numpy as np
import pytest
import torch
from torch import nn

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.nonlocal_raw import NonlocalRawDemosaic, canonical_raw, physical_raw


@pytest.mark.parametrize("pattern", PATTERNS)
@pytest.mark.parametrize("shape", [(1, 4, 7, 9), (2, 4, 8, 12)])
def test_canonical_orientation_matches_dense_native_flip_and_exact_inverse(pattern, shape):
    values = np.arange(np.prod(shape), dtype=np.float32).reshape(shape)
    colors = color_indices(pattern)
    actual, tags = canonical_raw(torch.from_numpy(values), colors)
    dense = np.empty((shape[0], 2 * shape[2], 2 * shape[3]), dtype=np.float32)
    for p in range(4):
        y, x = divmod(p, 2)
        dense[:, y::2, x::2] = values[:, p]
    layout = np.asarray(colors).reshape(2, 2)
    # Choose the native flip by testing the resulting CFA independently.
    candidates = []
    for vertical in [False, True]:
        for horizontal in [False, True]:
            c = layout[::-1] if vertical else layout
            c = c[:, ::-1] if horizontal else c
            if c.tolist() == [[0, 1], [1, 2]]:
                candidates.append((vertical, horizontal))
    assert len(candidates) == 1
    vertical, horizontal = candidates[0]
    if vertical:
        dense = dense[:, ::-1]
    if horizontal:
        dense = dense[:, :, ::-1]
    expected = np.stack(
        [dense[:, 0::2, 0::2], dense[:, 0::2, 1::2], dense[:, 1::2, 1::2], dense[:, 1::2, 0::2]],
        axis=1,
    )
    np.testing.assert_array_equal(actual.numpy(), expected)
    assert torch.equal(physical_raw(actual, tags), torch.from_numpy(values))


class FixedRaw(nn.Module):
    def __init__(self, values):
        super().__init__()
        self.values = values
        self.seen = None

    def forward(self, values):
        self.seen = values.detach().clone()
        return self.values


@pytest.mark.parametrize("pattern", PATTERNS)
def test_hybrid_preserves_denoised_measured_samples_and_noisy_conditioning(pattern):
    pytest.importorskip("einops", reason="Install the optional nonlocal extra for network checks")
    generator = torch.Generator().manual_seed(17002)
    base = torch.rand((1, 3, 16, 24), generator=generator) * 0.02
    packed = torch.rand((1, 4, 8, 12), generator=generator) * 0.03 - 0.001
    variance = packed.clamp_min(0) * 0.00128 + 6.5536e-6
    colors = color_indices(pattern)[None]
    denoised = torch.rand((1, 4, 8, 12), generator=generator) * 0.02
    canonical, _ = canonical_raw(denoised, colors)
    before = torch.get_rng_state().clone()
    module = NonlocalRawDemosaic()
    assert torch.equal(before, torch.get_rng_state())
    module.network = FixedRaw(canonical)
    with torch.inference_mode():
        hybrid, aux = module(
            base, packed, variance, colors, torch.tensor([[1.7, 1.0, 1.3]]), return_aux=True
        )
    assert torch.equal(aux["denoised_packed"], denoised)
    torch.testing.assert_close(mosaic(hybrid, colors), denoised, atol=5e-9, rtol=1e-6)
    torch.testing.assert_close(mosaic(aux["direct_rgb"], colors), denoised, atol=3e-9, rtol=1e-6)
    observed, _ = canonical_raw(packed.clamp(0, 1), colors)
    std, _ = canonical_raw(variance.sqrt(), colors)
    assert torch.equal(module.network.seen, torch.cat((observed, std), 1))
    assert torch.equal(before, torch.get_rng_state())


def test_mixed_CFA_batch_roundtrip_and_invalid_CFA_rejected():
    values = torch.arange(4 * 4 * 5 * 7, dtype=torch.float32).reshape(4, 4, 5, 7)
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    actual, tags = canonical_raw(values, colors)
    assert torch.equal(values, physical_raw(actual, tags))
    with pytest.raises(ValueError):
        canonical_raw(values[:1], torch.tensor([0, 0, 1, 2]))
