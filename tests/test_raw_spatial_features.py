import numpy as np
import pytest
import torch

from demosaic.cfa import color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.raw_spatial_features import RawSpatialFeatures, SpatialWindowBlock


def test_attention_matches_independent_dense_softmax_with_invalid_keys():
    block = SpatialWindowBlock(width=8, heads=2, window=2)
    rng = np.random.default_rng(131)
    arrays = [rng.normal(size=(3, 4, 8)).astype(np.float32) for _ in range(3)]
    valid = np.array([[True, False, True, True], [False, True, False, False], [True] * 4])
    bias = rng.normal(size=(2, 9)).astype(np.float32)
    with torch.no_grad():
        block.relative_bias.copy_(torch.from_numpy(bias))
    actual = block.attention(*(torch.from_numpy(x) for x in arrays), torch.from_numpy(valid))
    expected = np.zeros_like(arrays[0], dtype=np.float64)
    coordinates = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for batch in range(3):
        for head in range(2):
            for row, (qy, qx) in enumerate(coordinates):
                columns = np.flatnonzero(valid[batch])
                logits = []
                for column in columns:
                    ky, kx = coordinates[column]
                    q, k = [x[batch].astype(float).reshape(4, 2, 4) for x in arrays[:2]]
                    logits.append(
                        q[row, head] @ k[column, head] / 2
                        + bias[head, (qy - ky + 1) * 3 + qx - kx + 1]
                    )
                weights = np.exp(np.array(logits) - max(logits))
                weights /= weights.sum()
                values = arrays[2][batch].astype(float).reshape(4, 2, 4)
                expected[batch, row, head * 4 : (head + 1) * 4] = weights @ values[columns, head]
    np.testing.assert_allclose(actual.detach().numpy(), expected, atol=4e-7, rtol=2e-6)


@pytest.mark.parametrize("shift", [0, 2])
@pytest.mark.parametrize("shape", [(1, 1), (3, 9), (9, 5)])
def test_padded_window_average_matches_real_coordinate_groups_without_wrap(shape, shift):
    block = SpatialWindowBlock(width=4, heads=1, window=4, shift=shift)
    with torch.no_grad():
        for parameter in block.parameters():
            parameter.zero_()
        block.v.weight.copy_(torch.eye(4))
        block.out.weight.copy_(torch.eye(4))
    h, w = shape
    values = np.arange(h * w * 4, dtype=np.float32).reshape(h, w, 4) / 10
    expected = values.astype(np.float64).copy()
    for y in range(h):
        for x in range(w):
            pixels = [
                values[yy, xx].astype(float)
                for yy in range(h)
                for xx in range(w)
                if (yy + shift) // 4 == (y + shift) // 4 and (xx + shift) // 4 == (x + shift) // 4
            ]
            expected[y, x] += np.mean(pixels, axis=0)
    actual = block(torch.from_numpy(values[None]), torch.zeros(1, h, w, 16))
    np.testing.assert_allclose(actual[0].detach().numpy(), expected, atol=3e-6, rtol=1e-6)


def test_constructor_preserves_cpu_rng_without_touching_cuda_or_default_device(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Constructor must not seed CUDA")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    before = torch.get_rng_state()
    with torch.device("meta"):
        model = RawSpatialFeatures()
    assert torch.equal(before, torch.get_rng_state())
    assert all(x.device.type == "cpu" for x in [*model.parameters(), *model.buffers()])


@pytest.mark.parametrize("shape", [(1, 1), (3, 11), (9, 13)])
def test_all_CFA_phase_constants_stay_exactly_zero_after_learning(shape):
    model = RawSpatialFeatures()
    generator = torch.Generator().manual_seed(132)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.copy_(torch.randn(parameter.shape, generator=generator) * 0.1)
    h, w = shape
    packed = torch.rand(4, 4, 1, 1, generator=generator).expand(4, 4, h, w) * 1000
    variance = torch.rand(4, 4, h, w, generator=generator)
    colors = torch.stack([color_indices(x) for x in ["RGGB", "BGGR", "GRBG", "GBRG"]])
    span = torch.tensor([0.01, 0.1, 1.0, 10.0])[:, None, None, None]
    with torch.autocast("cpu", dtype=torch.bfloat16):
        output = model(packed, variance, colors, span)
    assert output.shape == (4, 64, h * 2, w * 2) and output.dtype == torch.float32
    assert torch.equal(output, torch.zeros_like(output))


def test_zero_initial_offset_then_gradients_reach_every_learned_tensor_and_reload():
    model = RawSpatialFeatures()
    generator = torch.Generator().manual_seed(133)
    packed = torch.rand(1, 4, 9, 13, generator=generator)
    variance = torch.rand(1, 4, 9, 13, generator=generator) * 0.01
    colors = color_indices("RGGB")
    target = torch.randn(1, 64, 18, 26, generator=generator)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    assert torch.equal(model(packed, variance, colors), torch.zeros_like(target))
    for _ in range(2):
        optimizer.zero_grad(set_to_none=True)
        (model(packed, variance, colors) - target).square().mean().backward()
        optimizer.step()
    for name, parameter in model.named_parameters():
        assert parameter.grad is not None and torch.isfinite(parameter.grad).all(), name
        assert parameter.grad.abs().max() > 0, name
    restored = RawSpatialFeatures()
    restored.load_state_dict(model.state_dict(), strict=True)
    torch.testing.assert_close(
        restored(packed, variance, colors), model(packed, variance, colors), atol=0, rtol=0
    )
    state = model.state_dict()
    state.pop("project.weight")
    with pytest.raises(RuntimeError, match="Missing key"):
        restored.load_state_dict(state, strict=True)


def test_nonconstant_channels_last_and_contiguous_inputs_match():
    model = RawSpatialFeatures()
    generator = torch.Generator().manual_seed(134)
    with torch.no_grad():
        model.project.weight.normal_(generator=generator)
    packed = torch.rand(2, 4, 9, 13, generator=generator)
    variance = packed * 0.001
    colors = torch.stack((color_indices("GRBG"), color_indices("BGGR")))
    first = model(packed, variance, colors)
    second = model(
        packed.contiguous(memory_format=torch.channels_last),
        variance.contiguous(memory_format=torch.channels_last),
        colors,
    )
    torch.testing.assert_close(first, second, atol=0, rtol=0)


@pytest.mark.parametrize(
    "change",
    [
        {"raw_spatial_features": 1},
        {"variance_stabilization": False},
        {"raw_frequency_features": True},
        {"rgb_processing_scale": 2},
        {"adc_cfa_projection": True},
        {"late_rgb_refinement": "spatial"},
    ],
)
def test_invalid_model_combinations_reject_before_encoder_or_trunk_construction(change):
    values = {
        "restoration_backbone": "pretrained-rgb",
        "width": 64,
        "physical_anchors": True,
        "variance_stabilization": True,
        "raw_spatial_features": True,
    }
    values.update(change)
    with pytest.raises(ValueError, match="spatial features"):
        JointDemosaic(ModelConfig(**values))
