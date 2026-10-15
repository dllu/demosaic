import torch

from demosaic.real_suite import measured_sensor_psnr


def test_sensor_score_uses_only_measured_unsaturated_reference_samples():
    prediction = torch.full((2, 3, 48, 48), 0.9)
    reference = torch.zeros_like(prediction)
    mask = torch.zeros_like(prediction, dtype=torch.bool)
    mask[0, 1, :32, :32] = True
    prediction[0, 1, :32, :32] = 0.2
    reference[0, 1, :32, :32] = 0.1
    # A reference crop without enough measured samples must not create a win.
    mask[1, 2, :16, :16] = True
    scores, count = measured_sensor_psnr(prediction, reference, mask)
    torch.testing.assert_close(scores[0], torch.tensor(20.0))
    assert torch.isnan(scores[1])
    assert count.tolist() == [1024, 256]


def test_sensor_score_applies_declared_sensor_range_clamp():
    prediction = torch.full((1, 3, 32, 32), -0.2)
    reference = torch.zeros_like(prediction)
    mask = torch.ones_like(prediction, dtype=torch.bool)
    scores, _ = measured_sensor_psnr(prediction, reference, mask)
    torch.testing.assert_close(scores, torch.tensor([120.0]))
