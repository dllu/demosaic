import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.cfa import adc_cfa_projection as project
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig


def fixture():
    generator = torch.Generator().manual_seed(23)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    rgb = torch.rand(4, 3, 16, 20, generator=generator) * 0.5 + 0.1
    packed = torch.rand(4, 4, 8, 10, generator=generator) * 0.8 + 0.05
    wb = torch.tensor([[2, 1, 1.5], [1.3, 1, 2.1], [1.7, 1, 1.1], [2.2, 1, 1.4]])
    return rgb, packed, colors, wb


def test_all_cfas_reproduce_nonclipped_observations():
    rgb, packed, colors, wb = fixture()
    corrected = project(rgb, packed, colors, wb)
    assert corrected.dtype == torch.float32 and torch.isfinite(corrected).all()
    torch.testing.assert_close(mosaic(corrected, colors), packed, rtol=0, atol=1e-7)


def test_clipped_and_near_black_measured_sites_keep_the_prediction():
    rgb, packed, colors, wb = fixture()
    packed[..., 0, :3] = packed.new_tensor([0, 1, 0.5 / 65535])
    sampled = mosaic(rgb, colors)
    valid = (packed > 1 / 65535) & (packed < 1 - 1 / 65535)
    actual = mosaic(project(rgb, packed, colors, wb), colors)
    torch.testing.assert_close(actual[valid], packed[valid], rtol=0, atol=1e-7)
    torch.testing.assert_close(actual[~valid], sampled[~valid], rtol=0, atol=0)


def test_zero_residual_is_exact_identity_and_does_not_clamp_hdr():
    rgb, _, colors, wb = fixture()
    rgb = rgb * 4 - 0.7
    assert rgb.min() < 0 and rgb.max() > 1
    actual = project(rgb, mosaic(rgb, colors), colors, wb)
    torch.testing.assert_close(actual, rgb, rtol=0, atol=0)


def test_autocast_keeps_native_code_variation_in_float32():
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    plane = 0.2 + torch.arange(32 * 40).reshape(32, 40) / 65535
    target = plane[None, None].expand(4, 3, -1, -1)
    packed = mosaic(target, colors)
    prediction = target + torch.tensor([0.01, -0.02, 0.03])[None, :, None, None]
    with torch.autocast("cpu", dtype=torch.bfloat16):
        actual = project(prediction, packed, colors, torch.ones(4, 3))
    assert actual.dtype == torch.float32
    torch.testing.assert_close(mosaic(actual, colors), packed, rtol=0, atol=1e-7)
    assert (actual * 65535).round().unique().numel() > 256


@pytest.mark.parametrize("bad_cfa", [True, False])
def test_invalid_dimensions_rejected(bad_cfa):
    rgb, packed, colors, wb = fixture()
    with pytest.raises(ValueError):
        project(rgb, packed[:, :3] if bad_cfa else packed[..., :-1], colors, wb)


def model_config(**kwargs):
    return ModelConfig(
        restoration_backbone="pretrained-rgb", width=64, camera_conditioning=True,
        variance_stabilization=True, physical_anchors=True, **kwargs,
    )


@pytest.mark.parametrize("mode", ["malvar", "sites"])
@pytest.mark.parametrize("precision", [torch.float32, torch.bfloat16])
@torch.no_grad()
def test_explicit_profiles_select_only_adc_images_and_preserve_auxiliary(precision, mode):
    torch.manual_seed(17)
    model = JointDemosaic(model_config(
        adc_cfa_projection=True, adc_cfa_projection_mode=mode,
    )).eval()
    _, packed, colors, wb = fixture()
    model.set_noise([0, 0.001, 0, 0], [0, 0, 0, 0.00001])
    # The variance map must not override supplied shot/read: deliberately use
    # a positive map for ADC images and zero for the noisy ones.
    variance = torch.zeros_like(packed)
    variance[[0, 2]] = 0.01
    with torch.autocast("cpu", dtype=precision, enabled=precision != torch.float32):
        model.pretrained_rgb.adc_projection = False
        parent = model(packed, variance, colors, wb)
        model.pretrained_rgb.adc_projection = True
        actual, sampled = model(packed, variance, colors, wb, auxiliary=True)
    torch.testing.assert_close(actual[[1, 3]], parent[[1, 3]], rtol=0, atol=0)
    expected = project(parent[[0, 2]], packed[[0, 2]], colors[[0, 2]], wb[[0, 2]], mode=mode)
    torch.testing.assert_close(actual[[0, 2]], expected, rtol=0, atol=0)
    torch.testing.assert_close(sampled, mosaic(actual, colors), rtol=0, atol=0)
    torch.testing.assert_close(sampled[[0, 2]], packed[[0, 2]], rtol=0, atol=2e-7)


@pytest.mark.parametrize("shot,read", [(0.001, 0), (0, 0.00001), (0.001, 0.00001)])
@torch.no_grad()
def test_scalar_noisy_prior_is_an_exact_noop(shot, read):
    model = JointDemosaic(model_config(adc_cfa_projection=True)).eval().set_noise(shot, read)
    _, packed, colors, wb = fixture()
    variance = torch.zeros_like(packed)
    parent = model(packed, variance, colors, wb)
    model.pretrained_rgb.adc_projection = False
    torch.testing.assert_close(model(packed, variance, colors, wb), parent, rtol=0, atol=0)


@torch.no_grad()
def test_scalar_adc_prior_broadcasts_without_white_balance():
    model = JointDemosaic(model_config(adc_cfa_projection=True)).eval().set_noise(0, 0)
    _, packed, colors, _ = fixture()
    actual = model(packed, torch.zeros_like(packed), colors)
    torch.testing.assert_close(mosaic(actual, colors), packed, rtol=0, atol=2e-7)


def test_projection_has_finite_gradients_and_preserves_unselected_batch_gradients():
    rgb, packed, colors, wb = fixture()
    rgb.requires_grad_(True)
    indices = torch.tensor([0, 2])
    corrected = project(rgb[indices], packed[indices], colors[indices], wb[indices])
    output = rgb.index_copy(0, indices, corrected)
    gradient, = torch.autograd.grad(output.sum(), rgb)
    assert torch.isfinite(gradient).all()
    torch.testing.assert_close(gradient[[1, 3]], torch.ones_like(gradient[[1, 3]]), rtol=0, atol=0)


@pytest.mark.parametrize("enabled,mode", [(False, "malvar"), (True, "malvar"), (True, "sites")])
@torch.no_grad()
def test_portable_checkpoint_policy_and_missing_legacy_default(tmp_path, enabled, mode):
    model = JointDemosaic(model_config(
        adc_cfa_projection=enabled, adc_cfa_projection_mode=mode,
    )).eval()
    config = model.config.to_dict()
    if mode == "malvar":
        config.pop("adc_cfa_projection_mode")
    if not enabled:
        config.pop("adc_cfa_projection")
    path = tmp_path / "portable.pt"
    torch.save({"model_config": config, "model": model.restoration_state_dict(), "step": 0}, path)
    restored, _ = load_checkpoint(path)
    assert restored.config.adc_cfa_projection is enabled
    assert restored.pretrained_rgb.adc_projection is enabled
    assert restored.config.adc_cfa_projection_mode == mode
    assert restored.pretrained_rgb.adc_projection_mode == mode
    assert restored.restoration_state_dict().keys() == model.restoration_state_dict().keys()
    model.set_noise(0, 0)
    restored.set_noise(0, 0)
    _, packed, colors, wb = fixture()
    variance = torch.zeros_like(packed)
    torch.testing.assert_close(model(packed, variance, colors, wb), restored(packed, variance, colors, wb), rtol=0, atol=0)


def test_projection_requires_explicit_noise_conditioning():
    model = JointDemosaic(model_config(adc_cfa_projection=True))
    _, packed, colors, wb = fixture()
    with pytest.raises(ValueError, match="explicit shot/read"):
        model(packed, torch.zeros_like(packed), colors, wb)
    with pytest.raises(ValueError, match="ADC CFA projection"):
        JointDemosaic(ModelConfig(adc_cfa_projection=True))
    with pytest.raises(ValueError, match="ADC CFA projection"):
        JointDemosaic(ModelConfig(restoration_backbone="pretrained-rgb", variance_stabilization=False, adc_cfa_projection=True))


@pytest.mark.parametrize("broadcast_colors", [False, True])
def test_sites_preserve_every_unmeasured_and_censored_channel_with_exact_gradients(broadcast_colors):
    rgb, packed, colors, wb = fixture()
    if broadcast_colors:
        colors = colors[0]
    packed[..., 0, :6] = packed.new_tensor([
        0, 1, 0.5 / 65535, 1 - 0.5 / 65535, 1 / 65535, 1 - 1 / 65535,
    ])
    rgb.requires_grad_(True)
    with torch.autocast("cpu", dtype=torch.bfloat16):
        actual = project(rgb, packed, colors, wb, mode="sites")
    expected = rgb.detach().clone()
    expected_gradient = torch.ones_like(rgb)
    # Independent phase/channel oracle, including censored observations.
    for batch in range(len(rgb)):
        for phase in range(4):
            channel = int(colors[phase] if broadcast_colors else colors[batch, phase])
            y, x = divmod(phase, 2)
            values = packed[batch, phase]
            valid = (values > 1 / 65535) & (values < 1 - 1 / 65535)
            expected[batch, channel, y::2, x::2][valid] = values[valid]
            expected_gradient[batch, channel, y::2, x::2][valid] = 0
    assert actual.dtype == torch.float32
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    gradient, = torch.autograd.grad(actual.sum(), rgb)
    torch.testing.assert_close(gradient, expected_gradient, rtol=0, atol=0)
    # The site-only operator is independent of white balance.
    torch.testing.assert_close(
        project(rgb, packed, colors, mode="sites"), actual, rtol=0, atol=0,
    )


def test_invalid_projection_modes_are_rejected():
    rgb, packed, colors, wb = fixture()
    with pytest.raises(ValueError, match="mode"):
        project(rgb, packed, colors, wb, mode="unknown")
    with pytest.raises(ValueError, match="mode"):
        JointDemosaic(model_config(adc_cfa_projection_mode="unknown"))
