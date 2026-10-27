import hashlib
import json
import random
from types import SimpleNamespace

import numpy as np
import pytest
import torch
import yaml

from demosaic import train as training
from demosaic.data import degrade
from demosaic.noise_pairs import validate_noise_pair_batch
from demosaic.shadow_exposure import (
    MAX_GREEN,
    MIN_GAIN,
    MIN_GREEN,
    POLICY,
    apply_shadow_exposure,
    require_resume_reviewed_shadows,
    reviewed_shadow_levels,
    reviewed_shadow_options,
)
from demosaic.source_loss import SourceLossTrace


def sources():
    return [
        json.dumps(
            {
                "kind": "photographic",
                "reviewed_roi_xywh": [0, 0, 512, 512],
                "draw_index": 4,
                "source_id": "reviewed",
            }
        ),
        json.dumps(
            {
                "kind": "photographic",
                "reviewed_roi_xywh": None,
                "draw_index": 5,
                "source_id": "ordinary",
            }
        ),
        json.dumps({"kind": "weak-texture", "draw_index": 6}),
    ]


@pytest.mark.parametrize("fraction", [True, -1, 1.1, float("nan"), float("inf"), "0.5"])
def test_invalid_fraction_is_rejected(fraction):
    with pytest.raises(ValueError, match="fraction"):
        reviewed_shadow_options({"reviewed_shadow_fraction": fraction})


def test_resume_is_legacy_compatible_and_rejects_changed_policy():
    require_resume_reviewed_shadows({}, {"reviewed_shadow_fraction": 0})
    assert reviewed_shadow_options({"reviewed_shadow_fraction": 0.5}) == (0.5, POLICY)
    with pytest.raises(ValueError, match="Resume reviewed shadow"):
        require_resume_reviewed_shadows({}, {"reviewed_shadow_fraction": 0.5})
    with pytest.raises(ValueError, match="Unknown"):
        reviewed_shadow_options({"reviewed_shadow_fraction": 1, "reviewed_shadow_policy": "other"})


def test_selection_uses_reviewed_photos_and_local_rng_only():
    clean = {"rgb": torch.ones(3, 3, 32, 32), "source": sources()}
    py, rng = random.getstate(), torch.get_rng_state().clone()
    a = reviewed_shadow_levels(clean, fraction=1, seed=68, step=2, device="cpu")
    b = reviewed_shadow_levels(clean, fraction=1, seed=68, step=2, device="cpu")
    assert MIN_GREEN <= a[0] <= MAX_GREEN and not a[1:].any()
    assert torch.equal(a, b)
    assert random.getstate() == py and torch.equal(rng, torch.get_rng_state())
    assert reviewed_shadow_levels({}, fraction=0, seed=68, step=2, device="cpu") is None


def test_camera_green_targeting_preserves_color_texture_and_bounds_gain():
    rgb = torch.linspace(0.2, 0.7, 3 * 32 * 32).reshape(1, 3, 32, 32).repeat(2, 1, 1, 1)
    inverse = torch.tensor([[[0.8, 0.15, 0.05], [0.1, 0.75, 0.15], [0.1, 0.1, 0.8]]]).repeat(
        2, 1, 1
    )
    wb = torch.tensor([[2.0, 1.0, 1.5]]).repeat(2, 1)
    exposure = torch.tensor([0.5, 2.0])[:, None, None, None]
    levels = torch.tensor([0.012, 0.0])
    chosen = apply_shadow_exposure(rgb, inverse, wb, exposure, levels)
    clean = torch.einsum("bij,bjhw->bihw", inverse, rgb * chosen) / wb[..., None, None]
    torch.testing.assert_close(clean[0, 1].mean(), levels[0], rtol=2e-6, atol=1e-9)
    assert torch.equal(chosen[1], exposure[1])
    dimmed = apply_shadow_exposure(rgb, inverse, wb, exposure, torch.tensor([MIN_GREEN, MIN_GREEN]))
    assert torch.all(dimmed >= MIN_GAIN) and torch.all(dimmed <= 1)
    assert torch.all(dimmed == MIN_GAIN)
    target = rgb * chosen
    torch.testing.assert_close(
        target[0] / rgb[0], chosen[0].expand_as(rgb[0]), rtol=1e-7, atol=1e-8
    )


def test_zero_levels_are_bit_exact_to_legacy_degradation_and_rng():
    torch.set_num_threads(2)
    rgb = torch.linspace(0.01, 0.8, 2 * 3 * 32 * 32).reshape(2, 3, 32, 32)
    state = torch.get_rng_state().clone()
    before = degrade(
        rgb,
        broad_camera=True,
        retain_sensor_target=True,
        retain_noise_settings=True,
        preserve_negative_read_noise=True,
    )
    after = torch.get_rng_state().clone()
    torch.set_rng_state(state)
    actual = degrade(
        rgb,
        broad_camera=True,
        retain_sensor_target=True,
        retain_noise_settings=True,
        preserve_negative_read_noise=True,
        shadow_green_levels=torch.zeros(2),
    )
    assert all(torch.equal(value, actual[key]) for key, value in before.items())
    assert torch.equal(after, torch.get_rng_state())
    assert not actual["shadow_exposure_selected"].any()


def test_selected_degradation_preserves_unselected_targets_and_all_camera_noise_settings():
    rgb = torch.linspace(0.05, 0.6, 2 * 3 * 32 * 32).reshape(2, 3, 32, 32)
    state = torch.get_rng_state().clone()
    control = degrade(
        rgb,
        broad_camera=True,
        retain_sensor_target=True,
        retain_noise_settings=True,
        preserve_negative_read_noise=True,
    )
    torch.set_rng_state(state)
    candidate = degrade(
        rgb,
        broad_camera=True,
        retain_sensor_target=True,
        retain_noise_settings=True,
        preserve_negative_read_noise=True,
        shadow_green_levels=torch.tensor([0.006, 0.0]),
    )
    for key in ["wb", "matrix", "colors", "shot", "read", "adc_bit_depth", "adc_black_level"]:
        assert torch.equal(candidate[key], control[key])
    for key in ["target", "sensor_target"]:
        assert torch.equal(candidate[key][1], control[key][1])
    assert candidate["shadow_exposure_selected"].tolist() == [True, False]
    assert candidate["sensor_target"][0, 1].mean() < 0.032
    assert not torch.equal(candidate["sensor_target"][0], control["sensor_target"][0])


def test_prepare_shares_shadow_geometry_across_two_noise_views(tmp_path):
    clean = {"rgb": torch.full((3, 3, 32, 32), 0.4), "source": sources()}
    config = {
        "reviewed_shadow_fraction": 1,
        "noise_pair_draws": 2,
        "camera_supervision": "sensor-valid-v1",
        "data_seed_per_step": True,
        "reconstruct_highlights": True,
        "broad_camera": True,
    }
    batch = training.prepare_training_batch(
        2,
        "commons",
        clean,
        model=SimpleNamespace(config=SimpleNamespace(physical_fp32=True)),
        device="cpu",
        config=config,
        seed=68,
    )
    assert validate_noise_pair_batch(batch) == 3
    assert batch["shadow_exposure_selected"].tolist() == [True, False, False] * 2
    for key in ["shadow_requested_green", "shadow_exposure_scale", "sensor_target"]:
        assert torch.equal(batch[key][:3], batch[key][3:])
    assert not torch.equal(batch["packed"][:3], batch["packed"][3:])
    trace_path = tmp_path / "source-loss.jsonl"
    SourceLossTrace(trace_path, config)(
        2,
        "commons",
        clean,
        batch["target"][:3],
        None,
        {key: value[:3] for key, value in batch.items()},
        step=2,
    )
    trace = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert [row["reviewed_shadow_exposure"]["selected"] for row in trace] == [True, False, False]
    assert trace[0]["reviewed_shadow_exposure"]["actual_exposure_gain"] > 0


@pytest.mark.parametrize("domain", ["native", "paired"])
def test_other_domains_never_select_or_parse_reviewed_sources(domain, monkeypatch):
    monkeypatch.setattr(
        training, "reviewed_shadow_levels", lambda *a, **k: pytest.fail("Unused Commons policy ran")
    )
    clean = (
        {
            "camera_rgb": torch.full((1, 3, 32, 32), 0.2),
            "wb": torch.ones(1, 3),
            "matrix": torch.eye(3)[None],
        }
        if domain == "native"
        else {"packed": torch.zeros(1, 4, 16, 16)}
    )
    training.prepare_training_batch(
        1, domain, clean, model=None, device="cpu", config={"reviewed_shadow_fraction": 1}, seed=68
    )


@pytest.mark.parametrize(
    "levels",
    [
        torch.tensor([-1.0]),
        torch.tensor([float("nan")]),
        torch.tensor([1.0]),
        torch.tensor([0.01, 0.01]),
    ],
)
def test_invalid_levels_fail_before_consuming_noise_rng(levels):
    rgb = torch.ones(1, 3, 32, 32)
    before = torch.get_rng_state().clone()
    with pytest.raises(ValueError, match="Shadow green levels"):
        degrade(rgb, shadow_green_levels=levels)
    assert torch.equal(before, torch.get_rng_state())


def test_actual_training_with_reviewed_shadows_resumes_exactly(tmp_path, monkeypatch):
    image = np.random.default_rng(8).integers(15000, 45000, (512, 512, 3), dtype=np.uint16)
    cache = tmp_path / "image.npy"
    np.save(cache, image)
    record = {
        "id": "reviewed",
        "split": "train",
        "cache": str(cache),
        "cache_sha256": hashlib.sha256(cache.read_bytes()).hexdigest(),
        "shape": [512, 512, 3],
        "bin_factor": 4,
        "dtype": "uint16",
        "color_space": "linear-sRGB",
    }
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps(record) + "\n" + json.dumps({**record, "id": "val", "split": "val"}) + "\n"
    )
    target = image.astype(np.float32).reshape(256, 2, 256, 2, 3).mean((1, 3)) / 65535
    catalogue = tmp_path / "regions.json"
    catalogue.write_text(
        json.dumps(
            {
                "source_manifest": {
                    "path": str(manifest),
                    "sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                },
                "source_split": "train",
                "source_bin_factor": 4,
                "final_area_reduction": 2,
                "effective_bin_factor": 8,
                "target_native_shape": [256, 256, 3],
                "examples": [
                    {
                        "id": "reviewed",
                        "source": record,
                        "ROI_in_bin4_xywh": [0, 0, 512, 512],
                        "actual_bin4_crop_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
                        "native8_target_float32_sha256": hashlib.sha256(
                            target.tobytes()
                        ).hexdigest(),
                    }
                ],
            }
        )
    )
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "steps": 4,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "precision": "float32",
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 1,
        "min_available_gb": 0,
        "training_execution": "deterministic-v1",
        "data_seed_per_step": True,
        "augmentation_downsample": 2,
        "synthetic_fraction": 0,
        "optical_blur_probability": 0,
        "reviewed_roi_fraction": 1,
        "reviewed_roi_catalogue": str(catalogue),
        "reviewed_shadow_fraction": 1,
        "source_loss_every": 0,
        "noise_pair_draws": 2,
        "conditional_mean_weight": 0.25,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "middle_blocks": 0,
            "decoder_blocks": [1],
            "attention": False,
        },
    }
    path = tmp_path / "recipe.yaml"
    path.write_text(yaml.safe_dump(config))
    full = training.train(path)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    checkpoint = training.train(path, stop_after=2)
    resumed = training.train(path, resume=checkpoint, stop_after=2)
    a, b = [torch.load(p, map_location="cpu", weights_only=True) for p in [full, resumed]]
    for key in ["model", "ema"]:
        assert all(torch.equal(value, b[key][name]) for name, value in a[key].items())
    assert torch.equal(a["torch_rng"], b["torch_rng"]) and a["python_rng"] == b["python_rng"]
    for index, state in a["optimizer"]["state"].items():
        assert all(
            torch.equal(value, b["optimizer"]["state"][index][name])
            for name, value in state.items()
        )
    config["reviewed_shadow_fraction"] = 0.5
    path.write_text(yaml.safe_dump(config))
    monkeypatch.setattr(
        training,
        "JointDemosaic",
        lambda *args: pytest.fail("Changed-policy resume constructed a model"),
    )
    with pytest.raises(ValueError, match="Resume reviewed shadow"):
        training.train(path, resume=resumed, stop_after=1)
