import pytest
import torch

from demosaic.data import degrade
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.prior import standardized_noise
from demosaic.train import expand_stem


def test_standardized_features_expose_weak_noise_in_physical_units():
    torch.manual_seed(5)
    noise = torch.randn(2, 4, 96, 96) * 0.001
    variance = torch.full_like(noise, 1e-6)
    a = standardized_noise(0.01 + noise, variance)
    b = standardized_noise(0.10 + noise * 10, variance * 100)
    torch.testing.assert_close(a, b, atol=2e-4, rtol=2e-4)
    assert 0.97 < a.std() < 1.03
    torch.testing.assert_close(standardized_noise(noise, variance * 0), noise * 0)
    assert standardized_noise(noise * 100, variance).abs().max() <= 8
    assert torch.isfinite(standardized_noise(noise[..., :8, :12], variance[..., :8, :12])).all()


@pytest.mark.parametrize(
    "source_camera,source_noise,target_camera,target_noise",
    [(False, False, True, False), (True, False, True, True), (False, True, True, True)],
)
def test_warm_start_preserves_channel_roles_and_prediction(
    source_camera, source_noise, target_camera, target_noise
):
    options = {"width": 8, "encoder_blocks": (1,), "middle_blocks": 1, "decoder_blocks": (1,)}
    source = JointDemosaic(
        ModelConfig(**options, camera_conditioning=source_camera, standardized_noise=source_noise)
    )
    torch.nn.init.normal_(source.head.weight, std=0.01)
    target = JointDemosaic(
        ModelConfig(**options, camera_conditioning=target_camera, standardized_noise=target_noise)
    )
    weights = source.restoration_state_dict()
    expand_stem(weights, source.config.to_dict(), target)
    target.load_state_dict(weights)
    batch = degrade(torch.rand(2, 3, 32, 48))
    args = [batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")]
    actual = target(*args)
    torch.testing.assert_close(actual, source(*args), atol=2e-6, rtol=2e-6)
    actual.square().mean().backward()
    offset = 32 if target_camera else 20
    if target_noise and not source_noise:
        assert target.stem.weight.grad[:, offset:].abs().sum() > 0
