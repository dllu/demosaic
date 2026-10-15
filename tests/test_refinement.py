import pytest
import torch

from demosaic.cfa import color_indices
from demosaic.data import degrade
from demosaic.model import JointDemosaic, ModelConfig, RgbNoiseRefiner
from demosaic.precision import amp_context


def test_zero_initialized_refinement_preserves_warm_start_and_adc_only_values():
    options = {"width": 8, "encoder_blocks": (1,), "middle_blocks": 1, "decoder_blocks": (1,)}
    base = JointDemosaic(ModelConfig(**options))
    torch.nn.init.normal_(base.head.weight, std=0.01)
    refined = JointDemosaic(ModelConfig(**options, noise_refinement=True))
    missing, unexpected = refined.load_state_dict(base.restoration_state_dict(), strict=False)
    assert not unexpected and all(k.startswith("refiner.") for k in missing)
    for name, parameter in refined.named_parameters():
        parameter.requires_grad_(name.startswith("refiner."))
    batch = degrade(torch.rand(2, 3, 32, 48))
    args = [batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")]
    result = refined(*args)
    torch.testing.assert_close(result, base(*args), atol=0, rtol=0)
    (result - batch["target"]).square().mean().backward()
    assert refined.refiner.head.weight.grad.abs().sum() > 0
    assert all(
        p.grad is None for n, p in refined.named_parameters() if not n.startswith("refiner.")
    )
    torch.nn.init.normal_(refined.refiner.head.weight, std=0.1)
    args[1] = torch.zeros_like(args[1])
    torch.testing.assert_close(refined(*args), base(*args), atol=0, rtol=0)


def test_refiner_can_remove_flat_noise_while_preserving_photometry():
    # The new path can represent a strong flat-field estimator without needing
    # to infer/reproduce the nonlinear Bayer prior from the original observations.
    torch.manual_seed(6)
    module = RgbNoiseRefiner(8, width=12, blocks=0, window=63)
    with torch.no_grad():
        for parameter in module.parameters():
            parameter.zero_()
        for channel in range(12):
            module.stem.weight[channel, channel, 1, 1] = 1
            module.head.weight[channel, channel, 1, 1] = -1
    rgb = 0.1 + torch.randn(1, 3, 128, 128) * 0.001
    variance = torch.full((1, 4, 64, 64), 1e-4)
    result = rgb + module(rgb, variance, color_indices("RGGB"), torch.zeros(1, 8, 64, 64))
    assert result.std() < rgb.std() / 10
    assert (result.mean() - 0.1).abs() < 1e-4


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA AMP precision")
def test_refinement_keeps_fine_signal_in_fp32_inside_amp():
    module = RgbNoiseRefiner(8, blocks=1).cuda()
    torch.nn.init.normal_(module.head.weight, std=0.01)
    rgb = torch.rand(1, 3, 32, 48, device="cuda")
    variance = torch.full((1, 4, 16, 24), 1e-5, device="cuda")
    features = torch.rand(1, 8, 16, 24, device="cuda")
    args = (rgb, variance, color_indices("GBRG", device="cuda"), features)
    with amp_context("cuda", dtype="float32"):
        expected = module(*args)
    with amp_context("cuda", dtype="bfloat16"):
        actual = module(*args)
    assert actual.dtype == torch.float32
    torch.testing.assert_close(actual, expected, atol=0, rtol=0)
