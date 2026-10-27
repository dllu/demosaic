import numpy as np
import pytest
import torch
import yaml

from demosaic.cfa import PATTERNS, color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import PretrainedRgbDemosaic
from demosaic.raw_global_conditioned_features import (
    ConditionedRawGlobalFeatures,
    normalized_cross_attention,
)
from demosaic.raw_global_features import RawGlobalFeatures, require_resume_global_features


def test_normalized_attention_matches_independent_cosine_formula_and_scaling():
    rng = np.random.default_rng(137)
    q, k, v = [rng.normal(size=s) for s in [(2, 5, 8), (2, 7, 8), (2, 7, 8)]]
    expected = np.empty_like(q)
    for b in range(2):
        for h in range(2):
            sl = slice(h * 4, (h + 1) * 4)
            a, z = q[b, :, sl], k[b, :, sl]
            a = a / np.linalg.norm(a, axis=1, keepdims=True)
            z = z / np.linalg.norm(z, axis=1, keepdims=True)
            logits = 2 * a @ z.T
            weights = np.exp(logits - logits.max(1, keepdims=True))
            weights /= weights.sum(1, keepdims=True)
            expected[b, :, sl] = weights @ v[b, :, sl]
    tensors = [torch.from_numpy(x) for x in [q, k, v]]
    actual = normalized_cross_attention(*tensors, heads=2)
    np.testing.assert_allclose(actual.numpy(), expected, rtol=1e-13, atol=1e-14)
    scaled = normalized_cross_attention(tensors[0] * 0.01, tensors[1] * 30, tensors[2], heads=2)
    torch.testing.assert_close(actual, scaled, rtol=1e-13, atol=1e-14)


def test_zero_keys_remain_finite_and_uniform_without_cross_image_pooling():
    query = torch.zeros(2, 3, 8)
    key = torch.zeros(2, 7, 8)
    value = torch.arange(112).float().reshape(2, 7, 8)
    actual = normalized_cross_attention(query, key, value, heads=2)
    torch.testing.assert_close(actual, value.mean(1, keepdim=True).expand(-1, 3, -1))
    assert not torch.equal(actual[0], actual[1])


def test_initial_tensors_and_zero_projection_match_legacy_without_rng_change():
    before = torch.get_rng_state()
    original, conditioned = RawGlobalFeatures(), ConditionedRawGlobalFeatures()
    assert torch.equal(before, torch.get_rng_state())
    a, b = original.state_dict(), conditioned.state_dict()
    assert len(a) == len(b) == 18 and sum(p.numel() for p in b.values()) == 18272
    assert all(torch.equal(a[k], b[k]) for k in a)
    packed = torch.linspace(0, 1, 4 * 9 * 13).reshape(1, 4, 9, 13)
    colors = color_indices("RGGB")[None]
    assert conditioned(packed, packed * 0.001, colors).count_nonzero() == 0


@pytest.mark.parametrize("shape", [(1, 1), (3, 11), (13, 9)])
def test_all_cfa_spatial_constants_stay_exactly_zero_after_adaptation(shape):
    model = ConditionedRawGlobalFeatures()
    generator = torch.Generator().manual_seed(1371)
    with torch.no_grad():
        for p in model.parameters():
            p.normal_(generator=generator)
    packed = torch.arange(4).float()[None, :, None, None].expand(4, 4, *shape) / 4
    variance = torch.rand(packed.shape, generator=generator)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    assert model(packed, variance, colors).count_nonzero() == 0


def test_conditioned_branch_batch_independence_gradients_and_strict_reload():
    model = ConditionedRawGlobalFeatures()
    generator = torch.Generator().manual_seed(1372)
    packed = torch.rand(2, 4, 9, 13, generator=generator)
    variance = torch.rand(packed.shape, generator=generator) * 0.001
    colors = torch.stack([color_indices(p) for p in ["GRBG", "GBRG"]])
    with torch.no_grad():
        model.project.weight.normal_(generator=generator, std=0.1)
    actual = model(packed, variance, colors)
    solo = model(packed[:1], variance[:1], colors[:1])
    torch.testing.assert_close(actual[:1], solo, atol=2e-7, rtol=2e-6)
    channels_last = model(packed.contiguous(memory_format=torch.channels_last), variance, colors)
    torch.testing.assert_close(actual, channels_last, atol=0, rtol=0)
    actual.square().mean().backward()
    assert all(
        p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().max() > 0
        for p in model.parameters()
    )
    loaded = ConditionedRawGlobalFeatures()
    loaded.load_state_dict(model.state_dict(), strict=True)
    torch.testing.assert_close(actual, loaded(packed, variance, colors), atol=0, rtol=0)


@pytest.mark.parametrize("mode", [None, False, 1, "unknown"])
def test_invalid_mode_rejects_before_constructing_restoration(mode):
    with pytest.raises(ValueError, match="global conditioning"):
        JointDemosaic(ModelConfig(raw_global_conditioning=mode))


def test_conditioned_mode_requires_global_branch():
    with pytest.raises(ValueError, match="conditioning requires global features"):
        JointDemosaic(ModelConfig(raw_global_conditioning="cosine-rms-v2"))


def test_old_checkpoint_default_and_explicit_conditioned_operator():
    assert ModelConfig().raw_global_conditioning == "legacy-v1"
    legacy = PretrainedRgbDemosaic(stabilized=True, physical_anchors=True, raw_global_features=True)
    conditioned = PretrainedRgbDemosaic(
        stabilized=True,
        physical_anchors=True,
        raw_global_features=True,
        raw_global_conditioning="cosine-rms-v2",
    )
    assert type(legacy.raw_global) is RawGlobalFeatures
    assert type(conditioned.raw_global) is ConditionedRawGlobalFeatures
    assert all(
        torch.equal(value, conditioned.raw_global.state_dict()[key])
        for key, value in legacy.raw_global.state_dict().items()
    )


@pytest.mark.parametrize(
    "old,new", [("legacy-v1", "cosine-rms-v2"), ("cosine-rms-v2", "legacy-v1")]
)
def test_resume_cannot_silently_change_operator_with_same_tensor_shapes(old, new):
    with pytest.raises(ValueError, match="global conditioning differs"):
        require_resume_global_features(
            {"model": {"raw_global_features": True, "raw_global_conditioning": old}},
            {"model": {"raw_global_features": True, "raw_global_conditioning": new}},
        )
    require_resume_global_features(
        {"model": {"raw_global_features": True}},
        {"model": {"raw_global_features": True, "raw_global_conditioning": "legacy-v1"}},
    )


def test_matched_pilot_changes_only_the_explicit_operator():
    from pathlib import Path

    configs = Path(__file__).resolve().parents[1] / "configs"
    old = yaml.safe_load((configs / "quality-v120-raw-global-pilot-v136.yaml").read_text())
    new = yaml.safe_load(
        (configs / "quality-v120-raw-global-conditioned-pilot-v137.yaml").read_text()
    )
    assert new["model"].pop("raw_global_conditioning") == "cosine-rms-v2"
    for key in ("run", "experiment_notes"):
        old.pop(key)
        new.pop(key)
    assert old == new
    assert new["steps"] == 1000 and new["seed"] == 70
