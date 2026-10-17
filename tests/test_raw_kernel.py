import pytest
import torch
from torch.nn import functional as F

from demosaic.cfa import PATTERNS, bilinear, color_indices, mosaic
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.raw_kernel import AdaptiveRawKernel, constant_preserving_box_mean
from demosaic.train import make_optimizer, update_ema


@pytest.mark.parametrize("window", [1, 3, 5, 17])
def test_stable_box_is_the_same_local_average_with_replicated_borders(window):
    values = torch.rand(2, 4, 7, 9, generator=torch.Generator().manual_seed(17)) - 0.1
    radius = window // 2
    # A direct FP32 pool sums up to 289 repeated border values and can have
    # larger error than the separable implementation under test. Use FP64 as
    # the independent mathematical reference, retaining the original bounds.
    expected = F.avg_pool2d(
        F.pad(values.double(), (radius,) * 4, mode="replicate"), window, stride=1
    ).float()
    torch.testing.assert_close(
        constant_preserving_box_mean(values, window), expected, atol=2e-7, rtol=2e-6
    )
    constants = torch.tensor([-0.03, 0.00001, 0.18, 1.4]).reshape(1, 4, 1, 1).expand(2, -1, 7, 9)
    torch.testing.assert_close(
        constant_preserving_box_mean(constants, window), constants, atol=0, rtol=0
    )


@pytest.mark.parametrize("pattern", PATTERNS)
def test_arbitrary_kernel_features_cannot_shift_clean_constant_rgb(pattern):
    head = AdaptiveRawKernel(8)
    with torch.no_grad():
        head.coefficients.weight.normal_(std=3)
        head.coefficients.bias.normal_(std=3)
    colors = color_indices(pattern)
    rgb = torch.tensor([[0.02, 0.18, 0.9], [1.4, -0.02, 0.00001], [0.0, 0.0, 0.0]])
    target = rgb[..., None, None].expand(-1, -1, 14, 18)
    raw = mosaic(target, colors)
    features = torch.randn(3, 8, 14, 18) * 100
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        result = head(raw, colors, features)
    assert result.dtype == torch.float32
    torch.testing.assert_close(result, target, atol=3e-7, rtol=0)


def test_zero_head_is_exact_bilinear_and_keeps_sub_16bit_variations():
    head = AdaptiveRawKernel(8)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    raw = 0.2 + torch.arange(4 * 4 * 9 * 11).reshape(4, 4, 9, 11) / 131070
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        actual = head(raw, colors, torch.randn(4, 8, 18, 22))
    torch.testing.assert_close(actual, bilinear(raw, colors), atol=0, rtol=0)
    assert torch.unique(actual).numel() > 256


def test_fixed_kernels_respect_independent_per_color_offsets_and_have_gradients():
    torch.manual_seed(3)
    head = AdaptiveRawKernel(8, (1, 3, 7))
    with torch.no_grad():
        head.coefficients.weight.normal_(std=0.01)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    raw = (torch.rand(4, 4, 7, 9) * 0.2).requires_grad_()
    features = torch.randn(4, 8, 14, 18, requires_grad=True)
    shifts = torch.tensor([0.12, -0.03, 0.7]).reshape(1, 3, 1, 1).expand(4, -1, 14, 18)
    a = head(raw, colors, features)
    b = head(raw + mosaic(shifts, colors), colors, features)
    torch.testing.assert_close(b - a, shifts, atol=4e-7, rtol=2e-6)
    a.square().mean().backward()
    for value in [raw, features, head.coefficients.weight, head.coefficients.bias]:
        assert (
            value.grad is not None
            and torch.isfinite(value.grad).all()
            and value.grad.abs().sum() > 0
        )


def test_native_trunk_tail_and_kernel_head_train_and_roundtrip(tmp_path):
    cfg = ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        raw_kernel_reconstruction=True,
        raw_kernel_windows=(1, 3, 7),
    )
    model = JointDemosaic(cfg)
    with torch.no_grad():
        model.pretrained_rgb.raw_kernel.coefficients.weight.normal_(std=0.001)
    raw = torch.rand(1, 4, 7, 9) * 0.2
    colors = color_indices("GBRG")
    prediction, auxiliary = model(raw, torch.ones_like(raw) * 1e-5, colors, auxiliary=True)
    assert prediction.shape == (1, 3, 14, 18)
    torch.testing.assert_close(auxiliary, mosaic(prediction, colors), atol=0, rtol=0)
    prediction.square().mean().backward()
    for parameter in [
        model.pretrained_rgb.network.m_head.weight,
        model.pretrained_rgb.network.m_tail.weight,
        model.pretrained_rgb.raw_kernel.coefficients.weight,
    ]:
        assert parameter.grad is not None and torch.isfinite(parameter.grad).all()
        assert parameter.grad.abs().sum() > 0
    path = tmp_path / "kernel.pt"
    torch.save({"model_config": cfg.to_dict(), "model": model.restoration_state_dict()}, path)
    restored, _ = load_checkpoint(path)
    assert restored.config.raw_kernel_reconstruction
    with torch.no_grad():
        torch.testing.assert_close(
            restored(raw, torch.ones_like(raw) * 1e-5, colors), prediction, atol=0, rtol=0
        )


@pytest.mark.parametrize("windows", [(), (3,), (1, 2), (1, 3, 3), (1, 7, 3), (True,)])
def test_invalid_supports_are_rejected(windows):
    with pytest.raises(ValueError, match="windows"):
        AdaptiveRawKernel(8, windows)


@pytest.mark.parametrize(
    "options",
    [
        {"restoration_backbone": "local"},
        {
            "restoration_backbone": "pretrained-rgb",
            "rgb_processing_scale": 2,
            "variance_stabilization": True,
        },
        {
            "restoration_backbone": "pretrained-rgb",
            "adc_cfa_projection": True,
            "variance_stabilization": True,
        },
    ],
)
def test_incompatible_model_paths_are_rejected(options):
    with pytest.raises(ValueError, match="RAW kernel"):
        JointDemosaic(
            ModelConfig(
                width=64, camera_conditioning=True, raw_kernel_reconstruction=True, **options
            )
        )


def test_raw_kernel_warmup_updates_only_coefficients_and_keeps_frozen_EMA_exact():
    model = JointDemosaic(
        ModelConfig(
            restoration_backbone="pretrained-rgb",
            width=64,
            camera_conditioning=True,
            raw_kernel_reconstruction=True,
        )
    )
    before = {k: v.clone() for k, v in model.restoration_state_dict().items()}
    ema = {k: v.clone() for k, v in before.items()}
    optimizer = make_optimizer(model, {"raw_kernel_only": True, "lr": 1e-4})
    expected = {
        "pretrained_rgb.raw_kernel.coefficients.weight",
        "pretrained_rgb.raw_kernel.coefficients.bias",
    }
    assert {n for n, p in model.named_parameters() if p.requires_grad} == expected
    assert sum(p.numel() for p in model.parameters() if p.requires_grad) == 22032
    raw = torch.rand(1, 4, 7, 9) * 0.2
    prediction = model(raw, torch.ones_like(raw) * 1e-5, color_indices("RGGB"))
    prediction.square().mean().backward()
    assert all(p.grad is None for n, p in model.named_parameters() if n not in expected)
    assert all(
        p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().sum() > 0
        for n, p in model.named_parameters()
        if n in expected
    )
    optimizer.step()
    update_ema(model, ema, 0.9)
    assert len(optimizer.state) == 2
    after = model.restoration_state_dict()
    for name, value in before.items():
        if name in expected:
            assert not torch.equal(value, after[name]) and not torch.equal(value, ema[name])
        else:
            torch.testing.assert_close(value, after[name], atol=0, rtol=0)
            torch.testing.assert_close(value, ema[name], atol=0, rtol=0)
    # Reconstructing the optimizer from a portable model applies the same scope.
    restored = JointDemosaic(model.config)
    restored_optimizer = make_optimizer(restored, {"raw_kernel_only": True, "lr": 1e-4})
    restored_optimizer.load_state_dict(optimizer.state_dict())
    assert len(restored_optimizer.state) == 2


@pytest.mark.parametrize(
    "options",
    [
        {"raw_kernel_only": "yes"},
        {"raw_kernel_only": True, "refiner_only": True},
        {"raw_kernel_only": True, "coarse_refiner_only": True},
        {"raw_kernel_only": True, "pyramid_refiner_only": True},
    ],
)
def test_invalid_raw_kernel_warmup_scopes_fail(options):
    model = JointDemosaic(ModelConfig())
    with pytest.raises(ValueError, match="RAW kernel-only"):
        make_optimizer(model, options)


def test_raw_kernel_warmup_requires_the_optional_head():
    model = JointDemosaic(ModelConfig())
    with pytest.raises(ValueError, match="requires RAW kernel reconstruction"):
        make_optimizer(model, {"raw_kernel_only": True})
