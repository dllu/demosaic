import json
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
import yaml
from test_losses import noise_batch
from test_optimizer_batches import manifests, options

from demosaic.cfa import mosaic
from demosaic.detail_loss import normalized_band_loss
from demosaic.losses import reconstruction_loss
from demosaic.train import train

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"scripts"))
from probe_band_supervision import band_penalty


@pytest.mark.parametrize("invalid", [-1, float("nan"), float("inf"), True, None, "bad", 1e40])
def test_invalid_weights_fail_before_batch_access(invalid):
    with pytest.raises(ValueError, match="band weight"):
        reconstruction_loss(None, {}, normalized_band_weight=invalid)


def test_zero_weight_skips_all_band_work_and_preserves_legacy_terms(monkeypatch):
    def forbidden(*_a, **_kw):
        raise AssertionError("Default must not construct band targets")
    monkeypatch.setattr("demosaic.losses.normalized_band_loss", forbidden)
    batch = noise_batch()
    p = (batch["target"]+.002).requires_grad_(True)
    a, terms_a = reconstruction_loss(p, batch)
    b, terms_b = reconstruction_loss(p, batch, normalized_band_weight=0)
    assert torch.equal(a, b) and terms_a.keys() == terms_b.keys()
    assert all(torch.equal(terms_a[k], terms_b[k]) for k in terms_a)
    assert torch.equal(torch.autograd.grad(a, p)[0], torch.autograd.grad(b, p)[0])
    assert "normalized_band" not in terms_a


@pytest.mark.parametrize("batch_size", [1, 3])
def test_nonzero_term_matches_frozen_prototype_and_output_gradient(batch_size):
    rng = np.random.default_rng(72)
    target = torch.tensor(.2+rng.normal(0, .02, (batch_size, 3, 40, 44)), dtype=torch.float32)
    target[:, :, 4:9, 8:12] = 1  # Invalid neighborhoods must agree too.
    p = (target+torch.tensor(rng.normal(0, .002, target.shape), dtype=torch.float32)).requires_grad_(True)
    expected = band_penalty(p, target, normalized=True)
    actual = .0003*normalized_band_loss(p, target)
    torch.testing.assert_close(actual, expected, rtol=2e-7, atol=1e-12)
    torch.testing.assert_close(torch.autograd.grad(actual, p)[0], torch.autograd.grad(expected, p)[0], rtol=1e-6, atol=1e-10)


def test_term_uses_unclipped_sensor_target_and_leaves_existing_terms_exact():
    batch = noise_batch()
    batch["sensor_target"] = batch["target"].clone()
    batch["target"] = batch["target"]*.5
    p = (batch["sensor_target"]+torch.linspace(-.01, .02, 32)[None, None, None]).requires_grad_(True)
    aux = mosaic(p, batch["colors"])
    default, old = reconstruction_loss(p, batch, aux, camera_supervision="sensor-valid-v1")
    changed, new = reconstruction_loss(p, batch, aux, camera_supervision="sensor-valid-v1", normalized_band_weight=.0003)
    assert all(torch.equal(old[k], new[k]) for k in old)
    assert torch.equal(new["normalized_band"], normalized_band_loss(p, batch["sensor_target"]))
    assert torch.equal(changed, default+.0003*new["normalized_band"])
    with pytest.raises(ValueError, match="sensor-valid"):
        reconstruction_loss(p, batch, normalized_band_weight=.0003)
    with pytest.raises(ValueError, match="paired references"):
        reconstruction_loss(p, {**batch, "sensor_reference": batch["target"]}, camera_supervision="sensor-valid-v1", normalized_band_weight=.0003)


def test_empty_nonfinite_targets_have_zero_loss_gradient_and_scale_is_detached():
    p = torch.zeros(2, 3, 32, 32, requires_grad=True)
    target = torch.full_like(p, float("nan"), requires_grad=True)
    loss = normalized_band_loss(p, target)
    assert loss == 0 and torch.count_nonzero(torch.autograd.grad(loss, p)[0]) == 0
    assert target.grad is None
    with pytest.raises(ValueError, match="contexts"):
        normalized_band_loss(p[..., :16, :16], target[..., :16, :16])


@pytest.mark.parametrize("weight,legacy", [(0, True), (.0003, False)])
def test_actual_training_resume_and_changed_weight_rejection(tmp_path, weight, legacy):
    commons, native, pairs = manifests(tmp_path)
    recipe = {**options(4), "manifest": str(commons), "raw_clean_manifest": str(native), "paired_manifest": str(pairs),
              "paired_fraction": .25, "raw_clean_fraction": .25, "run": str(tmp_path/"full"), "device": "cpu",
              "steps": 2, "seed": 51, "batch_size": 1, "patch_size": 32, "workers": 0, "raw_clean_workers": 0,
              "paired_workers": 0, "cpu_threads": 2, "warmup_steps": 1, "checkpoint_every": 2, "log_every": 1,
              "min_available_gb": 0, "val_batches": 1, "trace_observations": True, "camera_supervision": "sensor-valid-v1",
              "reconstruct_highlights": True, "normalized_band_weight": weight,
              "model": {"restoration_backbone": "packed-isotropic", "camera_conditioning": True, "width": 4,
                        "isotropic_groups": 1, "isotropic_blocks": 1, "isotropic_local_width": 4, "isotropic_raw_gain": 32,
                        "isotropic_residual_scale": 1/32}}
    path = tmp_path/"config.yaml"
    path.write_text(yaml.safe_dump(recipe))
    full = train(path)
    logs = [json.loads(s) for s in (tmp_path/"full/metrics.jsonl").read_text().splitlines()]
    training_rows = [r for r in logs if r["event"] == "train"]
    if weight:
        assert any(r.get("normalized_band", 0) > 0 for r in training_rows)
    else:
        assert all("normalized_band" not in r for r in training_rows)
    recipe["run"] = str(tmp_path/"resumed")
    path.write_text(yaml.safe_dump(recipe))
    checkpoint = train(path, stop_after=1)
    if legacy:
        state = torch.load(checkpoint, weights_only=True)
        del state["config"]["normalized_band_weight"]
        torch.save(state, checkpoint)
        del recipe["normalized_band_weight"]
        path.write_text(yaml.safe_dump(recipe))
    actual = train(path, resume=checkpoint)
    expected, actual = [torch.load(p, weights_only=True) for p in (full, actual)]
    assert actual["config"]["normalized_band_weight"] == weight
    for key in ("model", "ema"):
        assert all(torch.equal(v, actual[key][k]) for k, v in expected[key].items())
    for k, values in expected["optimizer"]["state"].items():
        assert all(torch.equal(v, actual["optimizer"]["state"][k][n]) for n, v in values.items())
    assert torch.equal(expected["torch_rng"], actual["torch_rng"]) and expected["python_rng"] == actual["python_rng"]
    recipe["normalized_band_weight"] = .0006
    path.write_text(yaml.safe_dump(recipe))
    with pytest.raises(ValueError, match="Resume normalized band weight differs"):
        train(path, resume=checkpoint)
