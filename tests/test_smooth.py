import json
import random

import numpy as np
import pytest
import torch

from demosaic.data import CleanDataset, smooth_scene


def test_dark_smooth_curriculum_is_deterministic_and_excludes_validation(tmp_path):
    image = np.full((32, 32, 3), 32768, dtype=np.uint16)
    np.save(tmp_path / "photo.npy", image)
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps({"id": s, "split": s, "cache": "photo.npy"}) for s in ("train", "val"))
    )
    training = CleanDataset(manifest, patch_size=32, synthetic_fraction=0, flat_fraction=1)
    heldout = CleanDataset(
        manifest, split="val", patch_size=32, synthetic_fraction=0, flat_fraction=1
    )
    assert torch.equal(training[0]["rgb"], training[0]["rgb"])
    assert training[0]["rgb"].mean() < 0.5
    torch.testing.assert_close(heldout[0]["rgb"], torch.full((3, 32, 32), 32768 / 65535))
    fields = torch.stack([smooth_scene(32, random.Random(i)) for i in range(30)])
    assert fields.min() >= 0 and fields.max() <= 1
    assert fields.flatten(1).mean(1).min() < 0.001
    assert (fields * 255 - (fields * 255).round()).abs().max() > 0.1
    with pytest.raises(ValueError, match="fractions"):
        CleanDataset(manifest, flat_fraction=0.9)
