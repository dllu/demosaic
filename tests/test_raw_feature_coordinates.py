import importlib.util
from pathlib import Path

import pytest
import torch


def prototype():
    spec = importlib.util.spec_from_file_location(
        "raw_coordinates", Path("scripts/probe_raw_feature_coordinates.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_noise_companding_preserves_endpoints_signed_samples_and_16bit_steps():
    transform = prototype().coordinate_map
    x = torch.linspace(-0.05, 1.2, 10001)
    y = transform(x, 0.00256, 2.62144e-5, "noise-compand")
    assert y.dtype == torch.float32 and torch.isfinite(y).all()
    assert (torch.diff(y) > 0).all() and (y[x < 0] < 0).all()
    endpoints = transform(torch.tensor([0.0, 1.0]), 0.00256, 2.62144e-5, "noise-compand")
    torch.testing.assert_close(endpoints, torch.tensor([0.0, 1.0]), rtol=0, atol=0)
    for value in [-0.03, 0.0, 0.001, 0.5, 1.0]:
        pair = torch.tensor([value, value + 1 / 65535])
        mapped = transform(pair, 0.00256, 2.62144e-5, "noise-compand")
        assert mapped[1] > mapped[0]


@pytest.mark.parametrize("read", [0.0, 1e-5])
def test_zero_shot_is_exact_identity_including_negative_read_noise(read):
    x = torch.linspace(-0.07, 1.2, 127)
    assert torch.equal(prototype().coordinate_map(x, 0.0, read, "noise-compand"), x)


def test_compander_is_pointwise_per_example_and_does_not_use_crop_statistics():
    fn = prototype().coordinate_map
    torch.manual_seed(4)
    x = torch.rand(4, 4, 7, 9) * 0.7 - 0.02
    shot = torch.tensor([0.0, 1e-5, 0.001, 0.01]).reshape(4, 1, 1, 1)
    read = torch.tensor([0.0, 1e-7, 1e-6, 1e-5]).reshape(4, 1, 1, 1)
    whole = fn(x, shot, read, "noise-compand")
    torch.testing.assert_close(
        fn(x[..., 2:5, 3:8], shot, read, "noise-compand"), whole[..., 2:5, 3:8], rtol=0, atol=0
    )
    for index in range(4):
        torch.testing.assert_close(
            fn(
                x[index : index + 1],
                shot[index : index + 1],
                read[index : index + 1],
                "noise-compand",
            ),
            whole[index : index + 1],
            rtol=0,
            atol=0,
        )


def test_compander_gradient_is_positive_and_join_is_smooth():
    fn = prototype().coordinate_map
    x = torch.tensor([-0.001, -1e-8, 0.0, 1e-8, 0.001, 0.5], requires_grad=True)
    fn(x, 0.002, 1e-5, "noise-compand").sum().backward()
    assert torch.isfinite(x.grad).all() and (x.grad > 0).all()
    torch.testing.assert_close(x.grad[1:4], x.grad[2].expand(3), rtol=1e-5, atol=0)


def test_coordinates_stay_fp32_in_outer_autocast_and_unknown_mode_rejects():
    fn = prototype().coordinate_map
    x = torch.linspace(-0.02, 1.0, 123)
    expected = fn(x, 0.002, 1e-6, "noise-compand")
    with torch.autocast("cpu", dtype=torch.bfloat16):
        actual = fn(x, 0.002, 1e-6, "noise-compand")
    assert torch.equal(actual, expected) and actual.dtype == torch.float32
    assert torch.equal(fn(x, 0.0, 0.0, "gain32"), x * 32)
    with pytest.raises(ValueError, match="mode"):
        fn(x, 0.002, 1e-6, "unknown")


def test_isolated_feature_hook_preserves_initial_signal_all_cfas_and_restores_on_error():
    from demosaic import packed_isotropic
    from demosaic.cfa import PATTERNS, bilinear, color_indices
    from demosaic.model import JointDemosaic, ModelConfig

    module = prototype()
    torch.manual_seed(51)
    model = JointDemosaic(
        ModelConfig(
            restoration_backbone="packed-isotropic",
            camera_conditioning=True,
            width=8,
            isotropic_groups=1,
            isotropic_blocks=1,
            isotropic_local_width=8,
        )
    ).eval()
    packed = torch.rand(4, 4, 17, 25) * 0.6 - 0.02
    variance = packed.clamp_min(0) * 0.002 + 1e-6
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    batch = {
        "shot": torch.tensor([0.0, 0.002, 0.001, 0.003]).reshape(4, 1, 1, 1),
        "read": torch.full((4, 1, 1, 1), 1e-6),
    }
    original = packed_isotropic.physical_features
    before = {name: value.clone() for name, value in model.state_dict().items()}
    with torch.inference_mode():
        for mode in ["raw", "gain32", "noise-compand"]:
            with module.feature_mode(mode, batch):
                output = model(packed, variance, colors)
            assert torch.equal(output, bilinear(packed, colors))
            assert packed_isotropic.physical_features is original
        with pytest.raises(ValueError, match="mode"), module.feature_mode("unknown", batch):
            model(packed, variance, colors)
    assert packed_isotropic.physical_features is original
    assert all(torch.equal(value, before[name]) for name, value in model.state_dict().items())
