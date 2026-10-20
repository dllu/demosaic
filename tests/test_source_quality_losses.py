"""Per-source curation loss must agree with the actual V43 training objective."""

import torch
from score_commons_quality import per_image_losses

from demosaic.cfa import mosaic
from demosaic.losses import reconstruction_loss


def test_individual_losses_match_canonical_objective_with_different_saturation_masks():
    generator = torch.Generator().manual_seed(20261020)
    target = torch.rand(3, 3, 32, 32, generator=generator) * 0.8
    target[0] *= 0.01
    target[1, :, 8:24, 8:24] = 1.4
    batch = {
        "target": target,
        "colors": torch.tensor([[0, 1, 1, 2]]).expand(3, -1),
        "wb": torch.tensor([[2.0, 1.0, 1.5]]).expand(3, -1),
        "matrix": torch.eye(3)[None].expand(3, -1, -1),
    }
    prediction = target + torch.randn(target.shape, generator=generator) * 0.03
    measured = per_image_losses(prediction, batch)
    for i in range(3):
        source = {k: v[i : i + 1] for k, v in batch.items()}
        loss, terms = reconstruction_loss(
            prediction[i : i + 1], source, mosaic(prediction[i : i + 1], source["colors"])
        )
        torch.testing.assert_close(measured["loss"][i], loss)
        for key, value in terms.items():
            torch.testing.assert_close(measured[key][i], value)
