import random

import pytest
import torch
import yaml
from test_weak_texture_routing import dataset

from demosaic.data import CleanDataset
from demosaic.textures import weak_texture
from demosaic.train import train


@pytest.mark.parametrize("kind", ["bandlimited", "fibers"])
@pytest.mark.parametrize("scale", [1, 2])
def test_fine_profile_preserves_other_draws_precision_and_global_rng(kind, scale):
    torch_rng, python_rng = torch.get_rng_state().clone(), random.getstate()
    a, b = random.Random(17), random.Random(17)
    legacy, old = weak_texture(128, a, pixel_scale=scale, kind=kind)
    fine, recipe = weak_texture(128, b, pixel_scale=scale, kind=kind, frequency_profile="fine-v1")
    repeated, same = weak_texture(128, random.Random(17), pixel_scale=scale, kind=kind, frequency_profile="fine-v1")
    assert torch.equal(fine, repeated) and recipe == same and a.getstate() == b.getstate()
    assert not torch.equal(fine, legacy) and "frequency_profile" not in old
    for key in ("seed", "level", "peak_relative_contrast", "tint"):
        assert recipe[key] == old[key]
    if kind == "fibers":
        assert 3.5 <= recipe["carrier_period_final_pixels"] <= 6
        for key in ("angle_radians", "bend_period_final_pixels", "bend_radians", "phase_offset"):
            assert recipe[key] == old[key]
    assert fine.dtype == torch.float32 and torch.isfinite(fine).all() and 0 < fine.min() < fine.max() < 1
    assert torch.unique(fine[0]).numel() > 1000
    assert torch.equal(torch.get_rng_state(), torch_rng) and random.getstate() == python_rng


def test_fine_random_fields_cover_four_pixel_frequencies_without_nominal_aliasing():
    rgb, recipe = weak_texture(256, random.Random(9), pixel_scale=2, kind="bandlimited", frequency_profile="fine-v1")
    field = rgb[0].double()/rgb[0].double().mean()-1
    power = torch.fft.rfft2(field).abs().square()
    axis = torch.fft.fftfreq(256, d=.5)
    x = torch.fft.rfftfreq(256, d=.5)
    radius = (axis[:, None]**2+x[None]**2).sqrt()
    low, high = recipe["frequency_band_cycles_per_final_pixel"]
    assert low == 1/6 and .34 <= high <= .4
    assert float(power[(radius < low) | (radius > high)].sum()/power.sum()) < 1e-7
    assert float(power[(radius >= .225) & (radius < .35)].sum()/power.sum()) > .3
    reduced = torch.nn.functional.avg_pool2d(rgb, 2)
    original_rms = (rgb[0].double()/rgb[0].double().mean()-1).square().mean().sqrt()
    reduced_rms = (reduced[0].double()/reduced[0].double().mean()-1).square().mean().sqrt()
    assert .75 < float(reduced_rms/original_rms) < 1


def test_profile_routing_changes_only_its_existing_weak_quota(tmp_path):
    legacy = dataset(tmp_path, weak_texture_fraction=.15, optical_blur_probability=0)
    zero = dataset(tmp_path, weak_texture_fraction=.15, fine_weak_texture_fraction=0, optical_blur_probability=0)
    candidate = dataset(tmp_path, weak_texture_fraction=.15, fine_weak_texture_fraction=.075, optical_blur_probability=0)
    changed = 0
    for i in range(80):
        draw = random.Random(52+i).random()
        old, same, new = (d[i]["rgb"] for d in (legacy, zero, candidate))
        assert torch.equal(old, same)
        expected = .1 <= draw < .175
        assert torch.equal(old, new) == (not expected)
        changed += expected
    assert changed > 0


def test_legacy_positional_dataset_arguments_keep_their_meaning(tmp_path):
    source = dataset(tmp_path)
    actual = CleanDataset(source.manifest, "train", 32, .2, 52, None, False, .1, 2, .15, 8, 0, .25, None, 0, None)
    assert actual.fine_weak_texture_fraction == 0 and actual.flat_chroma_stops == 8
    assert actual.optical_blur_probability == 0 and actual.photographic_low_contrast_fraction == .25


def test_fine_draw_generates_once_without_reading_photo_or_strong_source(tmp_path, monkeypatch):
    d = dataset(tmp_path, weak_texture_fraction=.15, fine_weak_texture_fraction=.075)
    i = next(i for i in range(100) if .1 <= random.Random(52+i).random() < .175)
    def forbidden(*_a, **_kw):
        raise AssertionError("Unselected source work")
    calls = []
    def selected(*a, **kw):
        calls.append(kw["frequency_profile"])
        return weak_texture(*a, **kw)
    monkeypatch.setattr("demosaic.data.np.load", forbidden)
    monkeypatch.setattr("demosaic.data.synthetic", forbidden)
    monkeypatch.setattr("demosaic.data.weak_texture", selected)
    assert d[i]["rgb"].shape == (3, 32, 32) and calls == ["fine-v1"]


def test_validation_ignores_fine_profile_and_invalid_probabilities_fail(tmp_path):
    old = dataset(tmp_path, split="val", augmentation_downsample=1)
    new = dataset(tmp_path, split="val", augmentation_downsample=1, weak_texture_fraction=.15, fine_weak_texture_fraction=.075)
    assert new.fine_weak_texture_fraction == 0 and torch.equal(old[0]["rgb"], new[0]["rgb"])
    for value in (-.1, .16, float("nan"), float("inf")):
        with pytest.raises(ValueError, match="Fine weak texture"):
            dataset(tmp_path, weak_texture_fraction=.15, fine_weak_texture_fraction=value)
    with pytest.raises(ValueError, match="frequency profile"):
        weak_texture(32, random.Random(0), frequency_profile="unknown")


def test_actual_fine_training_resume_is_exact_and_rejects_quota_change(tmp_path):
    source = dataset(tmp_path, synthetic_fraction=1, flat_fraction=0, weak_texture_fraction=1,
                     fine_weak_texture_fraction=1)
    config = {"manifest": str(source.manifest), "run": str(tmp_path/"full"), "device": "cpu", "steps": 2,
              "seed": 52, "batch_size": 1, "patch_size": 32, "workers": 0, "cpu_threads": 2, "amp": False,
              "precision": "float32", "warmup_steps": 1, "checkpoint_every": 2, "log_every": 1, "val_batches": 1,
              "min_available_gb": 0, "augmentation_downsample": 2, "flat_fraction": 0, "synthetic_fraction": 1,
              "weak_texture_fraction": 1, "fine_weak_texture_fraction": 1, "optical_blur_probability": 0,
              "model": {"restoration_backbone": "packed-isotropic", "camera_conditioning": True, "width": 4, "isotropic_groups": 1,
                        "isotropic_blocks": 1, "isotropic_local_width": 4, "isotropic_raw_gain": 32,
                        "isotropic_residual_scale": 1/32}}
    path = tmp_path/"recipe.yaml"
    path.write_text(yaml.safe_dump(config));full = train(path)
    config["run"] = str(tmp_path/"resumed")
    path.write_text(yaml.safe_dump(config));partial = train(path, stop_after=1)
    resumed = train(path, resume=partial)
    a, b = [torch.load(p, weights_only=True) for p in (full, resumed)]
    for field in ("model", "ema"):
        assert all(torch.equal(v, b[field][k]) for k, v in a[field].items())
    for key, state in a["optimizer"]["state"].items():
        assert all(torch.equal(v, b["optimizer"]["state"][key][name]) for name, v in state.items())
    assert torch.equal(a["torch_rng"], b["torch_rng"]) and a["python_rng"] == b["python_rng"]
    config["fine_weak_texture_fraction"] = .5
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="Resume fine weak texture fraction differs"):
        train(path, resume=resumed)
