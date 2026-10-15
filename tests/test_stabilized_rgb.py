import pytest
import torch
from torch import nn

from demosaic.cfa import PATTERNS, color_indices, malvar
from demosaic.inference import load_checkpoint, restore_tiled
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import physical_rgb_features, stabilized_photometry
from demosaic.vst import GeneralizedAnscombe


def model(*, identity=False, physical_anchors=False):
    result = JointDemosaic(
        ModelConfig(
            restoration_backbone="pretrained-rgb",
            width=64,
            camera_conditioning=True,
            variance_stabilization=True,
            physical_anchors=physical_anchors,
        )
    )
    if identity:

        class Identity(nn.Module):
            def forward(self, rgb, noise, **kwargs):
                return rgb

        result.pretrained_rgb.network = Identity()
    return result


def test_stabilized_batch_matches_independent_physical_pipelines_all_cfas():
    net = model(identity=True)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    raw = torch.rand(4, 4, 7, 9) * 0.3 - 0.01
    wb = torch.tensor([1.5, 1.0, 2.0])[None].expand(4, -1)
    shot = torch.tensor([0.001, 0.0, 0.00002, 0.0], dtype=torch.float64)
    read = torch.tensor([4e-6, 1e-6, 1.6e-9, 0.0], dtype=torch.float64)
    net.set_noise(shot, read)
    actual = net(
        raw,
        raw.clamp_min(0) * shot.float()[:, None, None, None] + read.float()[:, None, None, None],
        colors,
        wb,
    )
    expected = []
    for b in range(4):
        if shot[b]:
            transform = GeneralizedAnscombe(shot[b].item(), read[b].item())
            expected.append(transform.inverse(malvar(transform(raw[b : b + 1]), colors[b : b + 1])))
        else:
            expected.append(malvar(raw[b : b + 1], colors[b : b + 1], wb[b : b + 1]))
    torch.testing.assert_close(actual, torch.cat(expected), atol=3e-7, rtol=2e-6)
    assert actual.dtype == torch.float32


def test_explicit_priors_required_validated_cached_and_not_checkpointed():
    net = model(identity=True)
    raw = torch.rand(2, 4, 8, 8)
    colors = color_indices("RGGB")
    with pytest.raises(ValueError, match="explicit shot/read"):
        net(raw, torch.ones_like(raw), colors)
    for shot, read in [(-1, 0), (1, float("nan")), ([1, 2], [1, 2, 3]), ([], [])]:
        with pytest.raises(ValueError):
            net.set_noise(shot, read)
    net.set_noise(0.001, 1e-6)
    profiles = net.pretrained_rgb._noise_profiles
    net.set_noise(0.001, 1e-6)
    assert net.pretrained_rgb._noise_profiles is profiles
    net(raw, torch.ones_like(raw), colors)
    assert not any("_noise" in name for name in net.state_dict())
    net.set_noise([0.001, 0.002, 0.003], 0.0)
    with pytest.raises(ValueError, match="match the image batch"):
        net(raw, torch.ones_like(raw), colors)


def test_unit_noise_flat_normalization_keeps_pretrained_noise_range():
    raw = torch.ones(1, 4, 8, 8) * 5
    rgb, normalized, noise, _, _, span = physical_rgb_features(
        raw, torch.ones_like(raw), color_indices("RGGB"), stabilized=True
    )
    assert span.item() == 8
    assert noise.max().item() == 0.125
    assert normalized.abs().max() == 0
    assert torch.isfinite(rgb).all()


def test_gat_inverse_backpropagates_and_checkpoint_reloads_without_profiles(tmp_path):
    net = model().set_noise(0.001, 4e-6)
    raw = (torch.rand(1, 4, 7, 9) * 0.1 + 0.01).requires_grad_()
    colors = color_indices("GRBG")
    prediction = net(raw, raw.detach() * 0.001 + 4e-6, colors)
    prediction.square().mean().backward()
    assert torch.isfinite(raw.grad).all() and raw.grad.abs().sum() > 0
    gradient = net.pretrained_rgb.network.m_tail.weight.grad
    assert torch.isfinite(gradient).all() and gradient.abs().sum() > 0
    path = tmp_path / "stabilized.pt"
    torch.save({"model_config": net.config.to_dict(), "model": net.restoration_state_dict()}, path)
    restored, _ = load_checkpoint(path)
    assert restored.pretrained_rgb._noise_profiles is None
    restored.set_noise(0.001, 4e-6)
    with torch.no_grad():
        torch.testing.assert_close(
            restored(raw.detach(), raw.detach() * 0.001 + 4e-6, colors), prediction
        )


def test_tiler_supplies_noise_priors_and_preserves_native_geometry():
    net = model(identity=True)
    raw = torch.rand(31, 43) * 0.1
    output, metadata = restore_tiled(
        net,
        raw,
        color_indices("BGGR"),
        shot=0.0,
        read=0.0,
        tile=32,
        overlap=8,
        batch_size=2,
        device="cpu",
        amp=False,
    )
    assert output.shape == (3, 31, 43) and torch.isfinite(output).all()
    assert metadata["tiles"] > 1
    assert net.pretrained_rgb._noise_profiles is not None


def test_variance_stabilization_rejects_incompatible_local_architecture():
    with pytest.raises(ValueError, match="requires the pretrained RGB"):
        JointDemosaic(ModelConfig(variance_stabilization=True))


def test_physical_anchors_recover_sensor_black_white_in_every_noise_family():
    transforms = [GeneralizedAnscombe(0.001, 4e-6), None, None]
    profiles = [(transforms[0], 0.002, True), (None, 0.01, True), (None, 1.0, False)]
    offset = torch.tensor([2.0, 4.0, 0.2])[:, None, None, None]
    span = torch.tensor([8.0, 16.0, 0.5])[:, None, None, None]
    anchors = stabilized_photometry(profiles, offset, span)
    for b, (transform, scale, _) in enumerate(profiles):
        endpoints = anchors[b : b + 1, :2].sinh() * span[b : b + 1] + offset[b : b + 1]
        # Calibration anchors describe noiseless sensor measurements. Their
        # algebraic inverse differs from the expectation inverse used for a
        # denoised prediction; the latter intentionally corrects noise bias.
        physical = (
            GeneralizedAnscombe(transform.shot, transform.read, inverse="algebraic").inverse(
                endpoints
            )
            if transform
            else endpoints * scale
        )
        torch.testing.assert_close(
            physical.flatten(), torch.tensor([0.0, 1.0]), atol=3e-7, rtol=1e-6
        )
    assert anchors[1, 2].item() == -1 and anchors[2, 2].item() == -2


def test_clipped_flat_anchors_retain_iso_information_lost_by_range_normalization():
    states = []
    for shot in [2e-5, 0.00256]:
        transform = GeneralizedAnscombe(shot, (2 * shot) ** 2)
        raw = transform(torch.ones(1, 4, 8, 8))
        colors = color_indices("RGGB")
        _, normalized, noise, _, offset, span = physical_rgb_features(
            raw, torch.ones_like(raw), colors, stabilized=True
        )
        anchors = stabilized_photometry([(transform, 2 * shot, True)], offset, span)
        states.append((normalized, noise, anchors))
    torch.testing.assert_close(states[0][0], states[1][0], atol=1e-5, rtol=0)
    torch.testing.assert_close(states[0][1], states[1][1], atol=0, rtol=0)
    assert (states[0][2] - states[1][2]).abs().max() > 1


def test_zero_adapter_preserves_initial_prediction_when_adding_physical_anchors():
    original = model()
    anchored = model(physical_anchors=True)
    anchored.load_state_dict(original.state_dict(), strict=True)
    raw = torch.rand(1, 4, 8, 8) * 0.1 + 0.01
    colors = color_indices("BGGR")
    original.set_noise(0.001, 4e-6)
    anchored.set_noise(0.001, 4e-6)
    with torch.no_grad():
        torch.testing.assert_close(
            original(raw, raw * 0.001 + 4e-6, colors),
            anchored(raw, raw * 0.001 + 4e-6, colors),
            atol=0,
            rtol=0,
        )
    with pytest.raises(ValueError, match="anchors require variance"):
        JointDemosaic(ModelConfig(physical_anchors=True))
