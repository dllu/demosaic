import pytest
import torch

from demosaic.reference import load_rawnind


def test_linear_rgb_checkpoint_is_rejected_before_loading_bayer_source(tmp_path):
    # The publisher also releases a 3→3 linear-Rec.2020 model. Its RGB head
    # alone must not identify it as the Bayer pre-upsampled variant.
    torch.save(
        {
            "convs1.0.weight": torch.zeros(32, 3, 3, 3),
            "output_module.0.weight": torch.zeros(3, 32, 1, 1),
        },
        tmp_path / "utnet2-bayer.pt",
    )
    with pytest.raises(ValueError, match="Unsupported RawNIND Bayer"):
        load_rawnind(tmp_path)


def test_inconsistent_encoder_and_output_widths_are_rejected(tmp_path):
    torch.save(
        {
            "convs1.0.weight": torch.zeros(48, 4, 3, 3),
            "output_module.0.weight": torch.zeros(12, 32, 1, 1),
        },
        tmp_path / "utnet2-bayer.pt",
    )
    with pytest.raises(ValueError, match="Unsupported RawNIND Bayer"):
        load_rawnind(tmp_path)
