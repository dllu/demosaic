import sys
from pathlib import Path

import pytest
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from probe_real_noise_conditioning import predict_context


class ObservationRecorder:
    def set_noise(self, shot, read):
        self.profile = shot, read

    def __call__(self, packed, variance, colors, wb, matrix):
        self.observed = packed.clone(), variance.clone()
        return packed[:, :3].clone()


@pytest.mark.parametrize("factor", [0.25, 1, 4])
def test_variance_factor_preserves_signed_measurements_and_scales_noise_std(factor):
    model = ObservationRecorder()
    packed = torch.tensor([-0.1, 0, 0.2, 0.9], dtype=torch.float32).reshape(1, 4, 1, 1)
    original = packed.clone()
    colors = torch.tensor([[0, 1, 1, 2]])
    result = predict_context(
        model, packed, colors, None, None, shot=0.1, read_noise=0.0004, variance_factor=factor
    )
    assert model.profile == (0.1 * factor, 0.0004 * factor)
    torch.testing.assert_close(model.observed[0], original, rtol=0, atol=0)
    # Analytically known variances, including negative read-noise observations.
    expected = torch.tensor([0.0004, 0.0004, 0.0204, 0.0904]).reshape(1, 4, 1, 1)
    torch.testing.assert_close(model.observed[1].sqrt(), expected.sqrt() * factor**0.5)
    torch.testing.assert_close(packed, original, rtol=0, atol=0)
    assert result.dtype == torch.float32 and result[0, 0, 0, 0] < 0


@pytest.mark.parametrize(
    "shot,read,factor",
    [(-1, 0, 1), (0, -1, 1), (0, 0, 0), (0, 0, -1), (float("nan"), 0, 1), (0, 0, float("inf"))],
)
def test_invalid_profile_rejected_before_model_call(shot, read, factor):
    model = ObservationRecorder()
    with pytest.raises(ValueError):
        predict_context(
            model,
            torch.zeros(1, 4, 1, 1),
            None,
            None,
            None,
            shot=shot,
            read_noise=read,
            variance_factor=factor,
        )
    assert not hasattr(model, "profile")
