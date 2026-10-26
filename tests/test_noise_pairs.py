import json
from types import SimpleNamespace

import pytest
import torch
import yaml

from demosaic import train as training
from demosaic.data import degrade
from demosaic.losses import reconstruction_loss
from demosaic.noise_pairs import (
    conditional_mean_reconstruction_loss,
    independent_noise_view,
    noise_pair_options,
    require_resume_noise_pairs,
    validate_noise_pair_batch,
)
from demosaic.raw_clean import degrade_raw_clean


@pytest.mark.parametrize("native", [False, True])
def test_metadata_retention_preserves_original_noise_and_global_rng(native):
    torch.set_num_threads(2)
    rgb = torch.linspace(0.02, 0.6, 3 * 32 * 32).reshape(1, 3, 32, 32)
    source = {"camera_rgb": rgb, "wb": torch.ones(1, 3), "matrix": torch.eye(3)[None]}
    function = degrade_raw_clean if native else degrade
    original = torch.random.get_rng_state().clone()
    legacy = function(
        source if native else rgb, retain_sensor_target=True, preserve_negative_read_noise=True
    )
    after = torch.random.get_rng_state().clone()
    torch.random.set_rng_state(original)
    retained = function(
        source if native else rgb,
        retain_sensor_target=True,
        retain_noise_settings=True,
        preserve_negative_read_noise=True,
    )
    assert torch.equal(after, torch.random.get_rng_state())
    assert set(retained) - legacy.keys() == {"adc_black_level", "adc_bit_depth"}
    assert all(torch.equal(v, retained[k]) for k, v in legacy.items())
    assert torch.all((retained["adc_black_level"] >= 0.002) & (retained["adc_black_level"] <= 0.06))
    assert torch.all(retained["adc_bit_depth"] == 16)


@pytest.fixture
def pair():
    torch.set_num_threads(2)
    rgb = torch.linspace(0.01, 0.8, 2 * 3 * 32 * 32).reshape(2, 3, 32, 32)
    batch = degrade(rgb, training=False, retain_sensor_target=True, retain_noise_settings=True)
    return independent_noise_view(batch, seed=67, step=1, domain="commons")


def test_new_view_reuses_geometry_profile_and_preserves_rng_and_originals(pair):
    half = validate_noise_pair_batch(pair)
    assert half == 2
    assert not torch.equal(pair["packed"][:half], pair["packed"][half:])
    torch.testing.assert_close(
        pair["variance"], pair["packed"].clamp_min(0) * pair["shot"] + pair["read"], rtol=0, atol=0
    )
    original = {
        k: v[:half].clone() for k, v in pair.items() if k not in {"noise_pair_id", "noise_view"}
    }
    before = {k: v.clone() for k, v in original.items()}
    rng = torch.random.get_rng_state().clone()
    a = independent_noise_view(original, seed=67, step=11, domain="commons")
    b = independent_noise_view(original, seed=67, step=11, domain="commons")
    c = independent_noise_view(original, seed=67, step=12, domain="commons")
    assert torch.equal(rng, torch.random.get_rng_state())
    assert all(torch.equal(a[k], b[k]) for k in a)
    assert all(torch.equal(v, original[k]) for k, v in before.items())
    assert torch.equal(a["packed"][:half], c["packed"][:half])
    assert not torch.equal(a["packed"][half:], c["packed"][half:])


@pytest.mark.parametrize("domain", ["commons", "native"])
def test_prepare_loads_and_augments_once_and_keeps_first_view_identical(domain):
    rgb = torch.full((2, 3, 32, 32), 0.2)
    clean = (
        {"rgb": rgb}
        if domain == "commons"
        else {"camera_rgb": rgb, "wb": torch.ones(2, 3), "matrix": torch.eye(3).repeat(2, 1, 1)}
    )
    before = {k: v.clone() for k, v in clean.items()}
    config = {
        "data_seed_per_step": True,
        "camera_supervision": "sensor-valid-v1",
        "reconstruct_highlights": True,
        "preserve_negative_read_noise": True,
    }
    model = SimpleNamespace(config=SimpleNamespace(physical_fp32=True))
    rng = torch.random.get_rng_state().clone()
    first = training.prepare_training_batch(
        7, domain, clean, model=model, device="cpu", config=config, seed=67
    )
    paired = training.prepare_training_batch(
        7,
        domain,
        clean,
        model=model,
        device="cpu",
        config={**config, "noise_pair_draws": 2},
        seed=67,
    )
    assert len(paired["packed"]) == 4 and all(
        torch.equal(v, paired[k][:2]) for k, v in first.items()
    )
    assert all(torch.equal(v, before[k]) for k, v in clean.items())
    assert torch.equal(rng, torch.random.get_rng_state())


def test_real_paired_step_never_degrades_or_duplicates(monkeypatch):
    def forbid(*args, **kwargs):
        raise AssertionError("Real pairs must not draw synthetic noise")

    for name in ["degrade", "degrade_raw_clean", "independent_noise_view"]:
        monkeypatch.setattr(training, name, forbid)
    clean = {"packed": torch.zeros(2, 4, 16, 16), "sensor_reference": torch.ones(2, 3, 32, 32)}
    batch = training.prepare_training_batch(
        1,
        "paired",
        clean,
        model=None,
        device="cpu",
        config={"noise_pair_draws": 2, "conditional_mean_weight": 0.25, "data_seed_per_step": True},
        seed=67,
    )
    assert batch.keys() == clean.keys() and all(torch.equal(v, batch[k]) for k, v in clean.items())


def test_zero_weight_exactly_matches_original_loss_and_gradients(pair):
    prediction = (pair["target"] + 0.01).detach().requires_grad_()
    options = {
        "camera_supervision": "sensor-valid-v1",
        "reconstruction_charbonnier_epsilon": 0.0003,
    }
    baseline, old_terms = reconstruction_loss(prediction, pair, **options)
    expected = torch.autograd.grad(baseline, prediction)[0]
    actual, terms = conditional_mean_reconstruction_loss(prediction, pair, weight=0, **options)
    assert torch.equal(baseline, actual) and old_terms.keys() == terms.keys()
    assert all(torch.equal(v, terms[k]) for k, v in old_terms.items())
    assert torch.equal(torch.autograd.grad(actual, prediction)[0], expected)


@pytest.mark.parametrize("autocast", [False, True])
def test_convex_loss_and_gradients_match_explicit_mean_supervision(pair, autocast):
    prediction = (
        (
            pair["target"]
            + torch.linspace(-0.03, 0.07, pair["target"].numel()).reshape_as(pair["target"])
        )
        .detach()
        .requires_grad_()
    )
    auxiliary = pair["packed"].clone().requires_grad_()
    options = {
        "camera_supervision": "sensor-valid-v1",
        "reconstruction_charbonnier_epsilon": 0.0003,
    }
    before = torch.random.get_rng_state().clone()
    with torch.autocast("cpu", dtype=torch.bfloat16, enabled=autocast):
        actual, terms = conditional_mean_reconstruction_loss(
            prediction, pair, auxiliary, weight=0.25, **options
        )
    single, _ = reconstruction_loss(prediction, pair, auxiliary, **options)
    half = {k: v[:2] for k, v in pair.items()}
    mean, _ = reconstruction_loss(
        (prediction[:2] + prediction[2:]) * 0.5,
        half,
        (auxiliary[:2] + auxiliary[2:]) * 0.5,
        **options,
    )
    expected = 0.75 * single + 0.25 * mean
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)
    gradients = torch.autograd.grad(actual, (prediction, auxiliary), retain_graph=True)
    reference = torch.autograd.grad(expected, (prediction, auxiliary))
    for a, b in zip(gradients, reference, strict=True):
        assert torch.isfinite(a).all() and torch.count_nonzero(a)
        torch.testing.assert_close(a, b, rtol=0, atol=0)
    assert torch.equal(before, torch.random.get_rng_state())
    assert torch.equal(terms["per_view_loss"], single)


@pytest.mark.parametrize(
    "field",
    [
        "target",
        "sensor_target",
        "colors",
        "wb",
        "matrix",
        "shot",
        "read",
        "adc_black_level",
        "adc_bit_depth",
        "noise_pair_id",
        "noise_view",
    ],
)
def test_mismatched_pairs_rejected_before_loss(field, pair, monkeypatch):
    import demosaic.noise_pairs as module

    broken = {k: v.clone() for k, v in pair.items()}
    broken[field][2].add_(1)
    monkeypatch.setattr(
        module,
        "reconstruction_loss",
        lambda *args, **kwargs: pytest.fail("Invalid pairs reached reconstruction"),
    )
    with pytest.raises(ValueError, match="differs"):
        module.conditional_mean_reconstruction_loss(pair["target"], broken, weight=0.25)


@pytest.mark.parametrize(
    "config",
    [
        {"noise_pair_draws": True},
        {"noise_pair_draws": 3},
        {"conditional_mean_weight": 0.25},
        {"noise_pair_draws": 2, "conditional_mean_weight": True},
        {"noise_pair_draws": 2, "conditional_mean_weight": float("nan")},
        {"noise_pair_draws": 2, "conditional_mean_weight": -1},
        {"noise_pair_draws": 2, "conditional_mean_weight": 1.1},
        {"noise_pair_draws": 2, "noise_pair_policy": "other"},
    ],
)
def test_invalid_policy_rejected(config):
    with pytest.raises(ValueError):
        noise_pair_options(config)


def test_legacy_resume_and_changed_policy():
    require_resume_noise_pairs({}, {"noise_pair_draws": 1, "conditional_mean_weight": 0})
    for current in [
        {"noise_pair_draws": 2},
        {"noise_pair_draws": 2, "conditional_mean_weight": 0.25},
    ]:
        with pytest.raises(ValueError, match="Resume independent-noise"):
            require_resume_noise_pairs({}, current)


def test_actual_training_resume_and_source_trace_use_only_first_view(tmp_path, monkeypatch):
    import numpy as np

    cache = tmp_path / "image.npy"
    np.save(cache, np.full((40, 40, 3), 12000, np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": split, "split": split, "cache": str(cache)})
            for split in ["train", "val"]
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
        "source_loss_every": 1,
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
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    full = training.train(path)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    checkpoint = training.train(path, stop_after=2)
    final = training.train(path, resume=checkpoint, stop_after=2)
    a, b = (torch.load(p, map_location="cpu", weights_only=True) for p in [full, final])
    for group in ["model", "ema"]:
        assert all(torch.equal(v, b[group][k]) for k, v in a[group].items())
    assert all(float(s["step"]) == 4 for s in b["optimizer"]["state"].values())
    lines = [
        json.loads(l) for l in (tmp_path / "resumed/source-loss.jsonl").read_text().splitlines()
    ]
    assert len(lines) == 4 and all(r["source_trace_noise_view"] == 0 for r in lines)
    config["conditional_mean_weight"] = 0
    path.write_text(yaml.safe_dump(config))
    monkeypatch.setattr(
        training,
        "JointDemosaic",
        lambda *args: pytest.fail("Changed-policy resume constructed a model"),
    )
    with pytest.raises(ValueError, match="Resume independent-noise"):
        training.train(path, resume=final, stop_after=1)
