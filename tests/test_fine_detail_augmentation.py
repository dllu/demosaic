"""Fine-detail recipes remove optical PSFs without changing legacy defaults."""

import json
import random

import numpy as np
import pytest
import torch
import yaml
from torch.nn import functional as F

from demosaic import data


def legacy_augmentation(rgb, size, rng):
    rgb = torch.rot90(rgb, rng.randrange(4), (-2, -1))
    if rng.random() < 0.5:
        rgb = rgb.flip(-1)
    if rng.random() < 0.2:
        rgb = data.homography(rgb, rng, output_size=2 * size)
    elif rgb.shape[-2:] != (2 * size, 2 * size):
        rgb = F.interpolate(rgb[None], size=(2 * size, 2 * size), mode="area")[0]
    if rng.random() < 0.25:
        rgb = data.optical_blur(rgb, rng, pixel_scale=2)
    return F.avg_pool2d(rgb, 2)


def test_default_pixels_and_rng_remain_exact_against_previous_algorithm():
    rgb = torch.linspace(0, 1, 3 * 72 * 80).reshape(3, 72, 80)
    for seed in range(40):
        a, b = random.Random(seed), random.Random(seed)
        expected = legacy_augmentation(rgb, 32, a)
        actual = data.augment_before_downsample(rgb, 32, b)
        assert expected.numpy().tobytes() == actual.numpy().tobytes()
        assert a.getstate() == b.getstate()


def test_zero_blur_never_calls_any_optical_kernel(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Optical augmentation was disabled")

    monkeypatch.setattr(data, "optical_blur", forbidden)
    # Include seeds that normally select every optical kernel and geometry.
    rgb = torch.full((3, 64, 64), 0.18)
    for seed in range(40):
        output = data.augment_before_downsample(
            rgb, 32, random.Random(seed), optical_blur_probability=0
        )
        assert output.shape == (3, 32, 32) and torch.isfinite(output).all()


def test_low_contrast_retains_mean_geometry_and_continuous_precision():
    wave = torch.sin(torch.arange(64).float() * 2 * torch.pi / 8)[None, None].expand(3, 64, 64)
    rgb = 0.18 * (1 + 0.02 * wave)
    output = data.attenuate_photographic_contrast(rgb, random.Random(7))
    torch.testing.assert_close(output.mean((-2, -1)), rgb.mean((-2, -1)))
    ratio = (output - output.mean((-2, -1), keepdim=True)) / (
        rgb - rgb.mean((-2, -1), keepdim=True)
    ).clamp_min(1e-12)
    valid = wave > 0.5
    scale = ratio[valid].mean()
    assert 0.125 <= scale <= 0.5
    torch.testing.assert_close(
        output,
        output.mean((-2, -1), keepdim=True) + scale * (rgb - rgb.mean((-2, -1), keepdim=True)),
        rtol=1e-5,
        atol=1e-7,
    )
    assert output.dtype == torch.float32 and output.min() >= rgb.min() and output.max() <= rgb.max()


@pytest.mark.parametrize("value", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_probability_rejected(value):
    with pytest.raises(ValueError, match="finite"):
        data.validate_probability(value, "Blur")


def test_quality_recipe_resume_guards_use_effective_native_probability(tmp_path):
    from demosaic.train import train

    source = tmp_path / "source.npy"
    np.save(source, np.full((80, 80, 3), 12000, np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": split, "cache": source.name, "split": split, "bin_factor": 4})
            for split in ("train", "val")
        )
    )
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "run"),
        "device": "cpu",
        "steps": 2,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "checkpoint_every": 2,
        "min_available_gb": 0,
        "augmentation_downsample": 2,
        "optical_blur_probability": 0,
        "photographic_low_contrast_fraction": 0.25,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "middle_blocks": 0,
            "decoder_blocks": [1],
            "attention": False,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    checkpoint = train(path, stop_after=1)
    for key, value, error in [
        ("optical_blur_probability", 0.25, "Resume optical blur probability differs"),
        (
            "photographic_low_contrast_fraction",
            0.5,
            "Resume photographic low contrast fraction differs",
        ),
        (
            "raw_clean_optical_blur_probability",
            0.25,
            "Resume native optical blur probability differs",
        ),
    ]:
        changed = {**config, key: value}
        path.write_text(yaml.safe_dump(changed))
        with pytest.raises(ValueError, match=error):
            train(path, resume=checkpoint)
