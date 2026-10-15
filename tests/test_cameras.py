import torch

from demosaic.data import camera_pair, degrade, sample_broad_cameras


def test_broad_camera_population_covers_primary_mixing_and_warm_light():
    torch.manual_seed(17)
    wb, inverse = sample_broad_cameras(2048, "cpu")
    matrix = torch.linalg.inv(inverse)
    neutral = torch.ones(2048, 3, 1)
    torch.testing.assert_close(inverse @ neutral, neutral)
    torch.testing.assert_close(matrix @ neutral, neutral, atol=2e-6, rtol=2e-6)
    assert torch.isfinite(matrix).all()
    assert torch.linalg.cond(inverse).max() < 12
    assert (wb[:, 0] < 1).any() and (wb[:, 0] > 3).any()
    assert (wb[:, 2] < 1).any() and (wb[:, 2] > 3).any()
    assert matrix[:, 0, 0].max() > 2 and matrix[:, 0, 1].min() < -1
    torch.testing.assert_close(wb[:, 1], torch.ones(2048))
    rgb = torch.rand(2048, 3, 4, 4)
    sensor, target = camera_pair(rgb, inverse, wb, reconstruct_highlights=True)
    recovered = torch.einsum("bij,bjhw->bihw", matrix, sensor * wb[..., None, None])
    torch.testing.assert_close(recovered, rgb, atol=2e-6, rtol=2e-6)
    torch.testing.assert_close(sensor, target)


def test_broad_degradation_preserves_signed_sensor_and_finite_physical_targets():
    torch.manual_seed(19)
    batch = degrade(
        torch.rand(16, 3, 32, 32) * 0.01,
        broad_camera=True,
        reconstruct_highlights=True,
        preserve_negative_read_noise=True,
    )
    for value in batch.values():
        assert torch.isfinite(value).all()
    assert batch["packed"].min() < 0
    assert (batch["variance"] >= 0).all()
