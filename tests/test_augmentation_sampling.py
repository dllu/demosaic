import hashlib
import json
import math
import random

import numpy as np
import pytest
import torch
from PIL import Image
from torch.nn import functional as F

from demosaic.data import CleanDataset, augment_before_downsample, homography, optical_blur
from demosaic.prepare import bin_linear


class NoAugmentation(random.Random):
    def randrange(self, *args):
        return 0

    def random(self):
        return 0.99


def test_four_then_two_linear_binning_matches_eight_with_only_uint16_roundoff():
    image = Image.fromarray(np.random.default_rng(7).integers(0, 256, (256, 256, 3), np.uint8))
    intermediate = bin_linear(image, 4)
    actual = augment_before_downsample(
        torch.from_numpy(intermediate.astype(np.float32)).permute(2, 0, 1) / 65535,
        32,
        NoAugmentation(),
    )
    expected = torch.from_numpy(bin_linear(image, 8).astype(np.float32)).permute(2, 0, 1) / 65535
    torch.testing.assert_close(actual, expected, atol=1 / 65535 + 1e-7, rtol=0)
    assert actual.dtype == torch.float32
    assert len(torch.unique(actual)) > 256


def test_geometry_is_sampled_before_final_reduction_and_preserves_constant_colour():
    # A projective crop may be rectangular; output geometry must still be native.
    rgb = torch.tensor([0.03, 0.24, 0.51])[:, None, None].expand(3, 80, 92)
    for seed in range(30):
        actual = augment_before_downsample(rgb, 32, random.Random(seed))
        assert actual.shape == (3, 32, 32)
        torch.testing.assert_close(actual.mean((-2, -1)), rgb[:, 0, 0], atol=3e-7, rtol=0)
        assert torch.isfinite(actual).all()
    for seed in range(8):
        blurred = optical_blur(rgb, random.Random(seed), pixel_scale=2)
        assert blurred.shape == rgb.shape
        torch.testing.assert_close(blurred.mean((-2, -1)), rgb[:, 0, 0], atol=3e-7, rtol=0)


def test_projective_resampling_before_reduction_retains_more_continuous_detail():
    # Independent continuous cosine field: integrate the warped scene at 8x to
    # approximate the desired target pixel footprint. Compare two sampling orders.
    def scene(n):
        y, x = torch.meshgrid(
            (torch.arange(n) + 0.5) / n * 2 - 1, (torch.arange(n) + 0.5) / n * 2 - 1, indexing="ij"
        )
        return 0.4 + 0.2 * torch.cos(2 * math.pi * (7.3 * x + 3.7 * y))

    fine = scene(256)
    high = F.avg_pool2d(fine[None, None], 4)[0].expand(3, -1, -1)
    low = F.avg_pool2d(fine[None, None], 8)[0].expand(3, -1, -1)
    # Both methods use the same independent projective parameter draw.
    old = homography(low, random.Random(19))
    new = F.avg_pool2d(homography(high, random.Random(19), output_size=64), 2)
    # Fine-grid warp is an independent higher-density reference; no learned data.
    reference = F.avg_pool2d(homography(fine[None].expand(3, -1, -1), random.Random(19)), 8)
    assert (new - reference).square().mean() < (old - reference).square().mean()


def test_dataset_requires_four_binned_sources_and_produces_deterministic_native_patches(tmp_path):
    values = np.random.default_rng(8).integers(0, 65536, (80, 96, 3), np.uint16)
    cache = tmp_path / "source.npy"
    np.save(cache, values)
    manifest = tmp_path / "manifest.jsonl"
    rows = [{"id": s, "cache": cache.name, "split": s, "bin_factor": 4} for s in ["train", "val"]]
    manifest.write_text("\n".join(json.dumps(r) for r in rows))
    before = hashlib.sha256(cache.read_bytes()).hexdigest()
    data = CleanDataset(manifest, patch_size=32, synthetic_fraction=0, augmentation_downsample=2)
    for index in range(10):
        first, second = data[index]["rgb"], data[index]["rgb"]
        assert first.shape == (3, 32, 32)
        torch.testing.assert_close(first, second, atol=0, rtol=0)
    assert hashlib.sha256(cache.read_bytes()).hexdigest() == before
    with pytest.raises(ValueError, match="training"):
        CleanDataset(manifest, split="val", patch_size=32, augmentation_downsample=2)
    rows[0]["bin_factor"] = 8
    with pytest.raises(ValueError, match="4x-binned"):
        CleanDataset(manifest, patch_size=32, records=rows, augmentation_downsample=2)
