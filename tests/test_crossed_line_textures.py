import random

import numpy as np
import pytest
import torch
import yaml
from test_weak_texture_routing import dataset

from demosaic.textures import crossed_line_texture
from demosaic.train import train


@pytest.mark.parametrize("seed", [2, 7, 19, 43])
def test_counterfactual_background_rng_precision_and_empty_regions(seed):
    state, python = torch.get_rng_state().clone(), random.getstate()
    a, b = random.Random(seed), random.Random(seed)
    present, pa = crossed_line_texture(256, a, pixel_scale=2, present=True)
    empty, pb = crossed_line_texture(256, b, pixel_scale=2, present=False)
    assert a.getstate() == b.getstate()
    assert torch.equal(torch.get_rng_state(), state) and random.getstate() == python
    assert present.shape == (3, 256, 256) and present.dtype == empty.dtype == torch.float32
    assert torch.isfinite(present).all() and 0 < present.min() < present.max() < 1
    ignore = {"present", "peak_relative_contrast", "rms_relative_contrast"}
    assert {k: v for k, v in pa.items() if k not in ignore} == {
        k: v for k, v in pb.items() if k not in ignore
    }
    assert pb["peak_relative_contrast"] == pb["rms_relative_contrast"] == 0
    x = (np.arange(256) + 0.5) / 2
    xx, yy = np.meshgrid(x, x)
    radius = ((xx - pa["mask_center_final_pixels"][0]) / pa["mask_radii_final_pixels"][0]) ** 2
    radius += ((yy - pa["mask_center_final_pixels"][1]) / pa["mask_radii_final_pixels"][1]) ** 2
    # Well outside the support, RGB remains exactly the matched background.
    assert np.array_equal(present.numpy()[:, radius > 1.001], empty.numpy()[:, radius > 1.001])
    assert (
        np.max(np.abs((present.double() - empty.double()).mean((-2, -1)).numpy()))
        < 2e-8 * pa["level"]
    )
    # Check continuous target construction independently in NumPy64.
    slope = pa["background_slope"]
    background = (
        pa["level"]
        * np.array(pa["tint"])[:, None, None]
        * (1 + slope[0] * (xx / 128 - 0.5) + slope[1] * (yy / 128 - 0.5))
    )
    wires = []
    for angle, period, width, phase in zip(
        pa["angles_radians"],
        pa["periods_final_pixels"],
        pa["wire_sigma_final_pixels"],
        pa["phases_cycles"],
        strict=True,
    ):
        distance = (
            xx * np.cos(angle) + yy * np.sin(angle) + phase * period + period / 2
        ) % period - period / 2
        wires.append(np.exp(-0.5 * (distance / width) ** 2))
    lattice = 1 - (1 - wires[0]) * (1 - wires[1])
    mask = np.where(radius < 1, 0.5 * (1 + np.cos(np.pi * np.minimum(radius, 1))), 0)
    field = mask * (lattice - np.sum(lattice * mask) / np.sum(mask))
    field /= max(np.max(np.abs(field)), 0.1)
    expected = (
        background
        + pa["level"]
        * pa["requested_peak_relative_contrast"]
        * np.array(pa["contrast_direction"])[:, None, None]
        * field
    )
    assert np.max(np.abs(present.numpy() - expected)) < 4e-5 * pa["level"]
    np.testing.assert_allclose(empty.numpy(), background, rtol=3e-7, atol=pa["level"] * 1e-8)


def test_only_selected_weak_draws_change_and_validation_remains_photographic(tmp_path):
    original = dataset(tmp_path, weak_texture_fraction=0.15, optical_blur_probability=0)
    zero = dataset(
        tmp_path, weak_texture_fraction=0.15, optical_blur_probability=0, mesh_texture_fraction=0
    )
    candidate = dataset(
        tmp_path,
        weak_texture_fraction=0.15,
        optical_blur_probability=0,
        mesh_texture_fraction=0.05,
        trace_sources=True,
    )
    selected = 0
    for index in range(100):
        a, b, c = original[index], zero[index], candidate[index]
        assert torch.equal(a["rgb"], b["rgb"])
        draw = random.Random(52 + index).random()
        changed = 0.1 <= draw < 0.15
        assert torch.equal(a["rgb"], c["rgb"]) == (not changed)
        if changed:
            import json

            provenance = json.loads(c["source"])
            assert provenance["kind"] == "crossed-lines"
            assert type(provenance["texture_recipe"]["present"]) is bool
            selected += 1
    assert selected > 0
    a = dataset(tmp_path, split="val", augmentation_downsample=1)
    b = dataset(
        tmp_path,
        split="val",
        augmentation_downsample=1,
        weak_texture_fraction=0.15,
        mesh_texture_fraction=0.05,
    )
    assert b.mesh_texture_fraction == 0 and torch.equal(a[0]["rgb"], b[0]["rgb"])


@pytest.mark.parametrize("mesh,fine", [(-0.01, 0), (0.16, 0), (0.06, 0.1), (float("nan"), 0)])
def test_invalid_fraction_and_combined_quotas_reject(tmp_path, mesh, fine):
    with pytest.raises(ValueError, match="[Mm]esh"):
        dataset(
            tmp_path,
            weak_texture_fraction=0.15,
            fine_weak_texture_fraction=fine,
            mesh_texture_fraction=mesh,
        )


def test_actual_training_uses_mesh_data_and_changed_fraction_rejects_before_model(
    tmp_path, monkeypatch
):
    data = dataset(tmp_path, weak_texture_fraction=0.15, mesh_texture_fraction=0.05)
    recipe = {
        "manifest": str(data.manifest),
        "run": str(tmp_path / "train"),
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
        "flat_fraction": 0.1,
        "synthetic_fraction": 0.2,
        "weak_texture_fraction": 0.15,
        "mesh_texture_fraction": 0.05,
        "seed": 52,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "middle_blocks": 0,
            "decoder_blocks": [1],
            "attention": False,
        },
    }
    # Choose the training index by the actual reader rule, without changing the target.
    index = next(i for i in range(100) if 0.1 <= random.Random(52 + i).random() < 0.15)
    recipe["seed"] = 52 + index  # First DataLoader item is index0.
    expected = dataset(
        tmp_path,
        weak_texture_fraction=0.15,
        mesh_texture_fraction=0.05,
        optical_blur_probability=0,
        seed=recipe["seed"],
    )[0]["rgb"]
    import demosaic.train as training

    prepare = training.prepare_training_batch
    observed = []

    def check_target(step, domain, clean, **kwargs):
        assert step == 1 and domain == "commons" and torch.equal(clean["rgb"][0], expected)
        observed.append(step)
        return prepare(step, domain, clean, **kwargs)

    monkeypatch.setattr(training, "prepare_training_batch", check_target)
    path = tmp_path / "train.yaml"
    path.write_text(yaml.safe_dump(recipe))
    checkpoint = train(path, stop_after=1)
    state = torch.load(checkpoint, weights_only=True)
    assert state["step"] == 1 and state["config"]["mesh_texture_fraction"] == 0.05
    assert observed == [1]
    recipe["mesh_texture_fraction"] = 0.04
    path.write_text(yaml.safe_dump(recipe))
    monkeypatch.setattr("demosaic.train.JointDemosaic", lambda *_: pytest.fail("constructed model"))
    with pytest.raises(ValueError, match="Resume mesh texture fraction differs"):
        train(path, resume=checkpoint)
