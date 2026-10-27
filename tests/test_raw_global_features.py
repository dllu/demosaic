import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.raw_global_features import (
    RawGlobalFeatures,
    cross_attention,
    require_resume_global_features,
)


def test_cross_attention_matches_independent_dense_softmax():
    rng = np.random.default_rng(136)
    q, k, v = [rng.normal(size=s) for s in [(2, 5, 8), (2, 7, 8), (2, 7, 8)]]
    expected = np.empty((2, 5, 8))
    for b in range(2):
        for h in range(2):
            sl = slice(h * 4, (h + 1) * 4)
            logits = q[b, :, sl] @ k[b, :, sl].T / 2
            weights = np.exp(logits - logits.max(1, keepdims=True))
            weights /= weights.sum(1, keepdims=True)
            expected[b, :, sl] = weights @ v[b, :, sl]
    actual = cross_attention(*(torch.from_numpy(x) for x in (q, k, v)), heads=2)
    np.testing.assert_allclose(actual.numpy(), expected, atol=2e-15, rtol=2e-14)


def test_global_mixer_transfers_a_distant_value_without_cross_image_mixing():
    m = RawGlobalFeatures()
    with torch.no_grad():
        for p in m.parameters():
            p.zero_()
        for layer in (m.to_values, m.read_out, m.write_value, m.write_out):
            layer.weight.copy_(torch.eye(32))
    content = torch.zeros(2, 101, 32)
    content[0, -1] = 1
    content[1, -1] = 4
    actual = m.mix(content, torch.zeros(2, 101, 16))
    expected = content + content.mean(1, keepdim=True)
    torch.testing.assert_close(actual, expected, atol=2e-8, rtol=2e-6)
    assert actual[0, 0, 0] > 0


def test_constructor_preserves_rng_and_uses_explicit_cpu_allocations(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Constructor must not seed CUDA")

    monkeypatch.setattr(torch.cuda, "manual_seed_all", forbidden)
    before = torch.get_rng_state()
    with torch.device("meta"):
        m = RawGlobalFeatures()
    assert torch.equal(before, torch.get_rng_state())
    assert all(p.device.type == "cpu" for p in m.parameters())
    assert len(m.state_dict()) == 18 and sum(p.numel() for p in m.parameters()) == 18272


@pytest.mark.parametrize("shape", [(1, 1), (3, 11), (13, 9)])
def test_all_CFA_constants_stay_exactly_zero_after_adaptation(shape):
    m = RawGlobalFeatures()
    generator = torch.Generator().manual_seed(1361)
    with torch.no_grad():
        for p in m.parameters():
            p.normal_(generator=generator)
    packed = torch.arange(4).float()[None, :, None, None].expand(4, 4, *shape) / 4
    variance = torch.rand(packed.shape, generator=generator)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    assert torch.count_nonzero(m(packed, variance, colors)) == 0


def test_channels_last_batch_independence_gradient_flow_and_strict_reload():
    m = RawGlobalFeatures()
    generator = torch.Generator().manual_seed(1362)
    packed = torch.rand(2, 4, 9, 13, generator=generator)
    variance = packed * 0.001
    colors = torch.stack([color_indices(p) for p in ["GRBG", "GBRG"]])
    assert torch.count_nonzero(m(packed, variance, colors)) == 0
    with torch.no_grad():
        m.project.weight.normal_(generator=generator, std=0.1)
    output = m(packed, variance, colors)
    other = m(
        packed.contiguous(memory_format=torch.channels_last),
        variance.contiguous(memory_format=torch.channels_last),
        colors,
    )
    torch.testing.assert_close(output, other, atol=0, rtol=0)
    solo = m(packed[:1], variance[:1], colors[:1])
    torch.testing.assert_close(output[:1], solo, atol=2e-7, rtol=2e-6)
    output.square().mean().backward()
    assert all(
        p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().max() > 0
        for p in m.parameters()
    )
    restored = RawGlobalFeatures()
    restored.load_state_dict(m.state_dict(), strict=True)
    torch.testing.assert_close(output, restored(packed, variance, colors), atol=0, rtol=0)
    state = dict(m.state_dict())
    state.pop("latents")
    with pytest.raises(RuntimeError, match="Missing key"):
        restored.load_state_dict(state, strict=True)


@pytest.mark.parametrize(
    "change",
    [
        {"raw_global_features": 1},
        {"variance_stabilization": False},
        {"raw_frequency_features": True},
        {"raw_spatial_features": True},
        {"rgb_processing_scale": 2},
        {"late_rgb_refinement": "spatial"},
    ],
)
def test_incompatible_global_configs_reject_before_trunk_construction(change):
    config = {
        "restoration_backbone": "pretrained-rgb",
        "width": 64,
        "variance_stabilization": True,
        "physical_anchors": True,
        "raw_global_features": True,
    }
    config.update(change)
    with pytest.raises(ValueError, match="global features"):
        JointDemosaic(ModelConfig(**config))


@pytest.mark.parametrize("old,new", [(True, False), (False, True), (1, True)])
def test_resume_rejects_changed_or_nonboolean_mode(old, new):
    with pytest.raises(ValueError, match="global features"):
        require_resume_global_features(
            {"model": {"raw_global_features": old}}, {"model": {"raw_global_features": new}}
        )


def test_legacy_resume_and_checkpoint_flag_default_to_disabled():
    require_resume_global_features({}, {"model": {"raw_global_features": False}})
    assert not ModelConfig.from_checkpoint({}).raw_global_features


def test_genuine_state_contract_checks_every_common_tensor_and_zero_projection():
    from train_reviewed_shadow_trial import verify_initial_restoration

    parent = {f"common.{i}": torch.tensor([float(i)]) for i in range(91)}
    actual = {k: v.clone() for k, v in parent.items()}
    actual.update({f"pretrained_rgb.raw_global.layer{i}": torch.ones(1) for i in range(17)})
    actual["pretrained_rgb.raw_global.project.weight"] = torch.zeros(1)
    verify_initial_restoration(actual, parent, spatial=False, fresh=True, global_features=True)
    actual["common.90"].add_(1)
    with pytest.raises(AssertionError):
        verify_initial_restoration(actual, parent, spatial=False, fresh=True, global_features=True)
    actual["common.90"].sub_(1)
    actual["pretrained_rgb.raw_global.project.weight"].fill_(1)
    with pytest.raises(AssertionError):
        verify_initial_restoration(actual, parent, spatial=False, fresh=True, global_features=True)
    verify_initial_restoration(actual, actual, spatial=False, fresh=False, global_features=True)


def test_global_pilot_recipe_changes_only_the_declared_architecture():
    from pathlib import Path

    import yaml

    configs = [
        yaml.safe_load(Path(p).read_text())
        for p in [
            "configs/quality-v120-raw-global-pilot-v136.yaml",
            "configs/quality-v120-reviewed-detail-pilot-v129.yaml",
        ]
    ]
    candidate, baseline = configs
    ignored = {"run", "experiment_notes", "model"}
    assert {k: v for k, v in candidate.items() if k not in ignored} == {
        k: v for k, v in baseline.items() if k not in ignored
    }
    assert candidate["model"].pop("raw_global_features") is True
    assert candidate["model"] == baseline["model"]
