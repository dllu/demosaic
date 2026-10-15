import pytest
import torch

from demosaic.cfa import malvar, mosaic
from demosaic.data import degrade
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.prior import wiener_packed


def test_variance_prior_removes_flat_noise_and_preserves_zero_noise_exactly():
    rng = torch.Generator().manual_seed(416)
    noisy = 0.1 + 0.01 * torch.randn((2, 4, 128, 128), generator=rng)
    filtered = wiener_packed(noisy, torch.full_like(noisy, 1e-4))
    interior = filtered[..., 8:-8, 8:-8]
    assert abs(interior.mean() - 0.1) < 0.0003
    assert interior.std() < noisy[..., 8:-8, 8:-8].std() * 0.35
    assert torch.equal(wiener_packed(noisy, torch.zeros_like(noisy)), noisy)
    with pytest.raises(ValueError, match="odd window"):
        wiener_packed(noisy, torch.zeros_like(noisy), window=4)


def test_prior_backbone_starts_at_declared_baseline_and_trains():
    model = JointDemosaic(
        ModelConfig(
            width=4,
            encoder_blocks=(1,),
            decoder_blocks=(1,),
            middle_blocks=0,
            attention=False,
            baseline="wiener-malvar",
        )
    )
    batch = degrade(torch.rand(2, 3, 32, 48))
    prediction, auxiliary = model(
        batch["packed"],
        batch["variance"],
        batch["colors"],
        batch["wb"],
        batch["matrix"],
        auxiliary=True,
    )
    filtered = wiener_packed(batch["packed"], batch["variance"])
    torch.testing.assert_close(
        prediction, malvar(filtered, batch["colors"], batch["wb"]), atol=0, rtol=0
    )
    torch.testing.assert_close(auxiliary, filtered, atol=0, rtol=0)
    (prediction - batch["target"]).square().mean().backward()
    assert model.head.weight.grad.abs().sum() > 0


def test_noise_free_training_samples_keep_only_adc_quantization():
    rgb = torch.rand(8, 3, 32, 32)
    batch = degrade(rgb, noise_free_fraction=1, preserve_negative_read_noise=True)
    assert not batch["shot"].any() and not batch["read"].any() and not batch["variance"].any()
    torch.testing.assert_close(
        batch["packed"], mosaic(batch["target"], batch["colors"]), atol=1e-5, rtol=0
    )
    state = torch.get_rng_state()
    a = degrade(rgb)
    torch.set_rng_state(state)
    b = degrade(rgb, noise_free_fraction=0)
    assert all(torch.equal(a[key], b[key]) for key in a)
