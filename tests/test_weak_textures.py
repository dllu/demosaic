import random

import pytest
import torch

from demosaic.textures import weak_texture


@pytest.mark.parametrize("kind", ["bandlimited", "fibers"])
@pytest.mark.parametrize("scale", [1, 2])
def test_texture_is_deterministic_bounded_linear_and_preserves_global_rng(kind, scale):
    torch_state = torch.get_rng_state().clone()
    random_state = random.getstate()
    first, recipe = weak_texture(128, random.Random(17), pixel_scale=scale, kind=kind)
    second, repeated = weak_texture(128, random.Random(17), pixel_scale=scale, kind=kind)
    assert torch.equal(first, second) and recipe == repeated
    assert torch.equal(torch.get_rng_state(), torch_state) and random.getstate() == random_state
    assert first.shape == (3, 128, 128) and first.dtype == torch.float32
    assert torch.isfinite(first).all() and 0 < first.min() < first.max() < 1
    base = recipe["level"] * torch.tensor(recipe["tint"])[:, None, None]
    relative = first / base - 1
    assert relative.mean().abs() < 1e-6
    assert abs(float(relative.abs().max()) - recipe["peak_relative_contrast"]) < 2e-7
    assert recipe["rms_relative_contrast"] > 0.0001
    # Continuous targets retain many more levels than an 8-bit source over
    # these weak variations. This does not claim independent sensor bit depth.
    assert torch.unique(first[0]).numel() > 1000


@pytest.mark.parametrize("scale", [1, 2])
def test_bandlimited_field_support_is_in_final_pixel_units(scale):
    rgb, recipe = weak_texture(128, random.Random(9), pixel_scale=scale, kind="bandlimited")
    field = rgb[0].double() / rgb[0].double().mean() - 1
    power = torch.fft.rfft2(field).abs().square()
    fy = torch.fft.fftfreq(128, d=1 / scale)[:, None]
    fx = torch.fft.rfftfreq(128, d=1 / scale)[None]
    radius = (fx.square() + fy.square()).sqrt()
    low, high = recipe["frequency_band_cycles_per_final_pixel"]
    outside = (radius < low) | (radius > high)
    assert float(power[outside].sum() / power.sum()) < 1e-8
    assert high < 0.25


def test_invalid_texture_recipe_fails():
    for kwargs in [
        {"size": 16},
        {"size": 32.5},
        {"size": 32, "pixel_scale": 4},
        {"size": 32, "kind": "unknown"},
    ]:
        with pytest.raises(ValueError):
            weak_texture(rng=random.Random(0), **kwargs)
