"""Measurement geometry, parent preservation and learning for the residual branch."""

import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.raw_directional import DIRECTIONS, RawDirectionalResidual, line_mean
from demosaic.train import make_optimizer, set_learning_rate


def config(**kwargs):
    return ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        variance_stabilization=True,
        physical_anchors=True,
        **kwargs,
    )


@pytest.mark.parametrize("direction", DIRECTIONS)
def test_directional_average_matches_independent_double_precision_samples(direction):
    value = torch.randn(2, 4, 13, 15, generator=torch.Generator().manual_seed(9))
    dy, dx = direction
    array = value.numpy().astype(np.float64)
    expected = np.zeros_like(array)
    for y in range(13):
        for x in range(15):
            samples = [
                array[..., np.clip(y + k * dy, 0, 12), np.clip(x + k * dx, 0, 14)]
                for k in range(-16, 17)
            ]
            expected[..., y, x] = np.mean(samples, axis=0)
    torch.testing.assert_close(
        # FP32 sum of 32 differences; this bound is below one 16-bit code.
        line_mean(value, direction),
        torch.from_numpy(expected).float(),
        rtol=1e-5,
        atol=1.2e-6,
    )
    constants = torch.tensor([-0.1, 0.00001, 0.2, 1.8])[None, :, None, None].expand_as(value)
    assert torch.equal(line_mean(constants, direction), constants)


def test_line_filter_preserves_a_coherent_carrier_and_reduces_independent_noise():
    x = torch.arange(160).float()
    carrier = (0.02 * torch.cos(2 * torch.pi * x / 8))[None, None, None].expand(1, 4, 160, -1)
    assert torch.equal(line_mean(carrier, (1, 0)), carrier)
    noise = torch.randn(carrier.shape, generator=torch.Generator().manual_seed(41)) * 0.02
    error = line_mean(carrier + noise, (1, 0)) - carrier
    ratio = error[..., 16:-16, 16:-16].square().mean() / noise[..., 16:-16, 16:-16].square().mean()
    assert 0.02 < ratio < 0.05  # A 33-sample line, allowing this finite realization.


def test_zero_branch_preserves_values_and_rng_but_has_trainable_heads():
    torch.manual_seed(17)
    rng = torch.get_rng_state()
    head = RawDirectionalResidual()
    assert torch.equal(rng, torch.get_rng_state())
    assert len(head.state_dict()) == 8 and sum(p.numel() for p in head.parameters()) == 25800
    colors = color_indices("RGGB")
    raw = torch.rand(1, 4, 12, 12)
    raw[..., :3, :3] = 1
    base = torch.rand(1, 3, 24, 24)
    features = torch.randn(1, 67, 24, 24)
    variance = torch.full_like(raw, 0.001)
    before = [x.clone() for x in (base, raw, features, variance)]
    optimizer = torch.optim.AdamW(head.parameters(), lr=0.001)
    losses = []
    for step in range(3):
        optimizer.zero_grad(set_to_none=True)
        with torch.autocast("cpu", dtype=torch.bfloat16):
            result = head(base, raw, variance, colors, features)
        if step == 0:
            assert torch.equal(result, base) and result.dtype == torch.float32
        loss = (result - 0.1).square().mean()
        losses.append(loss.item())
        loss.backward()
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in head.parameters())
        assert head.mix_weight.grad.count_nonzero() and head.censored_weight.grad.count_nonzero()
        if step:
            assert head.local[0].weight.grad.count_nonzero()
        optimizer.step()
    assert losses[-1] < losses[0]
    assert all(
        torch.equal(a, b) for a, b in zip(before, (base, raw, features, variance), strict=True)
    )


@pytest.mark.parametrize("pattern", PATTERNS)
def test_arbitrary_mixture_cannot_shift_a_clean_uncensored_constant_scene(pattern):
    head = RawDirectionalResidual()
    with torch.no_grad():
        head.mix_weight.normal_(std=2)
        head.mix_bias.normal_(std=2)
        head.censored_weight.normal_(std=2)
        head.censored_bias.normal_(std=2)
    colors = color_indices(pattern)
    base = torch.tensor([-0.03, 0.00001, 0.7])[None, :, None, None].expand(1, 3, 18, 22)
    raw = mosaic(base, colors)
    output = head(base, raw, torch.full_like(raw, 0.001), colors, torch.randn(1, 67, 18, 22))
    torch.testing.assert_close(output, base, rtol=0, atol=3e-7)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_censored_head_cannot_change_unsaturated_measured_samples(pattern):
    head = RawDirectionalResidual()
    with torch.no_grad():
        head.censored_bias.copy_(torch.tensor([0.8, -0.4, 1.3]))
    colors = color_indices(pattern)
    raw = torch.full((1, 4, 9, 11), 1 - 1 / 65535)
    raw[..., ::3, ::2] = 1
    base = torch.rand(1, 3, 18, 22)
    output = head(base, raw, torch.full_like(raw, 0.001), colors, torch.randn(1, 67, 18, 22))
    correction = mosaic(output - base, colors)
    assert correction[raw != 1].count_nonzero() == 0
    assert correction[raw == 1].count_nonzero() == (raw == 1).sum()


@pytest.mark.parametrize("amp", [False, True])
def test_enabled_model_keeps_common_initialization_outputs_gradients_and_checkpoint(tmp_path, amp):
    torch.manual_seed(39)
    parent = JointDemosaic(config())
    parent_rng = torch.get_rng_state()
    torch.manual_seed(39)
    candidate = JointDemosaic(config(raw_directional_residual=True))
    assert torch.equal(parent_rng, torch.get_rng_state())
    parent_state, state = parent.restoration_state_dict(), candidate.restoration_state_dict()
    extra = state.keys() - parent_state.keys()
    assert len(extra) == 8 and all(k.startswith("pretrained_rgb.raw_directional.") for k in extra)
    assert all(torch.equal(v, state[k]) for k, v in parent_state.items())
    raw = torch.rand(1, 4, 12, 16) * 0.6
    colors = color_indices("GRBG")
    variance = torch.full_like(raw, 0.001)
    for net in (parent, candidate):
        net.set_noise(torch.tensor([0.001]), torch.tensor([0.00001]))
    with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        a, aa = parent(raw, variance, colors, auxiliary=True)
        b, ba = candidate(raw, variance, colors, auxiliary=True)
    assert torch.equal(a, b) and torch.equal(aa, ba)
    ap = parent.pretrained_rgb.network.m_tail.weight
    bp = candidate.pretrained_rgb.network.m_tail.weight
    ga = torch.autograd.grad(a.square().mean(), ap)[0]
    gb = torch.autograd.grad(b.square().mean(), bp)[0]
    assert torch.equal(ga, gb)
    path = tmp_path / "directional.pt"
    torch.save({"model_config": candidate.config.to_dict(), "model": state}, path)
    restored, _ = load_checkpoint(path)
    assert restored.config.raw_directional_residual
    restored.set_noise(torch.tensor([0.001]), torch.tensor([0.00001]))
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        assert torch.equal(restored(raw, variance, colors), b)


def test_optimizer_keeps_common_lr_and_scales_every_directional_parameter_once():
    model = JointDemosaic(config(raw_directional_residual=True))
    optimizer = make_optimizer(model, {"lr": 1e-5, "raw_directional_lr_multiplier": 20})
    groups = optimizer.param_groups
    assert len(groups) == 2
    actual = [id(p) for g in groups for p in g["params"]]
    assert len(actual) == len(set(actual)) == sum(p.requires_grad for p in model.parameters())
    expected = {id(p) for p in model.pretrained_rgb.raw_directional.parameters()}
    assert {id(p) for p in groups[1]["params"]} == expected
    set_learning_rate(optimizer, 2e-6)
    assert [g["lr"] for g in groups] == [2e-6, 2e-6 * 20]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"rgb_processing_scale": 2},
        {"raw_kernel_reconstruction": True},
        {"adc_cfa_projection": True},
        {"raw_directional_residual": 1},
    ],
)
def test_incompatible_model_paths_are_rejected(kwargs):
    with pytest.raises(ValueError, match="directional"):
        JointDemosaic(config(**{"raw_directional_residual": True, **kwargs}))
