import torch

from demosaic.metrics import quality_metrics, ssim


def test_ssim_identity_constant_and_known_luminance_difference():
    torch.set_num_threads(2)
    x = torch.rand(2, 3, 32, 48)
    torch.testing.assert_close(ssim(x, x), torch.ones(2), atol=1e-6, rtol=0)
    zero, one = torch.zeros_like(x), torch.ones_like(x)
    torch.testing.assert_close(
        ssim(zero, one), torch.full((2,), 0.0001 / 1.0001), atol=1e-6, rtol=0
    )


def test_quality_metrics_distinguish_missing_regions_from_zero_error():
    target = torch.full((1, 3, 32, 48), 0.2)
    scores = quality_metrics(target, target, torch.ones(1, 3), torch.eye(3)[None])
    assert scores["srgb_psnr"].item() == 120
    assert scores["chroma_mae"].item() == 0
    assert torch.isnan(scores["highlight_boundary_chroma_mae"]).all()
    assert torch.isnan(scores["shadow_linear_psnr"]).all()
    target[..., 12:20, 12:20] = 1
    scores = quality_metrics(target, target, torch.ones(1, 3), torch.eye(3)[None])
    assert scores["highlight_boundary_chroma_mae"].item() == 0
