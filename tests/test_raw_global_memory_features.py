import numpy as np
import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import PretrainedRgbDemosaic
from demosaic.raw_global_conditioned_features import ConditionedRawGlobalFeatures
from demosaic.raw_global_features import require_resume_global_features
from demosaic.raw_global_memory_features import MemoryOnlyRawGlobalFeatures


def test_initial_state_is_the_exact_shared_subset_without_local_mlp_or_rng_change():
    before = torch.get_rng_state()
    original, memory = ConditionedRawGlobalFeatures(), MemoryOnlyRawGlobalFeatures()
    assert torch.equal(before, torch.get_rng_state())
    old, new = original.state_dict(), memory.state_dict()
    assert old.keys() - new.keys() == {"up.weight", "down.weight", "ff_gain"}
    assert len(new) == 15 and sum(p.numel() for p in new.values()) == 14144
    assert all(torch.equal(v, old[k]) for k, v in new.items())
    assert memory.project.weight.count_nonzero() == 0


def test_memory_mixer_matches_independent_two_attention_formula():
    model = MemoryOnlyRawGlobalFeatures().double()
    rng = np.random.default_rng(139)
    content, condition = rng.normal(size=(2, 7, 32)), rng.normal(size=(2, 7, 16))
    state = {k: v.detach().numpy() for k, v in model.state_dict().items()}

    def linear(x, name):
        return x @ state[name + ".weight"].T

    def norm(x, gain):
        return x / np.sqrt(np.mean(x * x, axis=-1, keepdims=True) + 1e-4) * state[gain]

    def attention(q, k, v):
        out = np.empty_like(q)
        for b in range(2):
            for h in range(4):
                sl = slice(h * 8, (h + 1) * 8)
                a, z = q[b, :, sl], k[b, :, sl]
                a = a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-6)
                z = z / np.maximum(np.linalg.norm(z, axis=-1, keepdims=True), 1e-6)
                logits = np.sqrt(8) * a @ z.T
                p = np.exp(logits - logits.max(-1, keepdims=True))
                p /= p.sum(-1, keepdims=True)
                out[b, :, sl] = p @ v[b, :, sl]
        return out

    normalized = norm(content, "content_gain")
    keys = linear(normalized, "to_keys") + linear(condition, "condition")
    assert state["latents"].shape == (1, 64, 32)
    queries = np.broadcast_to(linear(state["latents"], "read_query"), (2, 64, 32))
    scale = np.sqrt(np.mean(content * content, axis=(1, 2), keepdims=True) + 1e-4)
    memory = linear(attention(queries, keys, linear(content / scale, "to_values")), "read_out")
    query = linear(normalized, "write_query") + linear(condition, "condition")
    context = linear(
        attention(
            query, linear(norm(memory, "memory_gain"), "write_key"), linear(memory, "write_value")
        ),
        "write_out",
    )
    actual = model.mix(torch.from_numpy(content), torch.from_numpy(condition))
    np.testing.assert_allclose(actual.detach().numpy(), context * scale, atol=2e-14, rtol=2e-12)


@pytest.mark.parametrize("shape", [(1, 1), (3, 11), (13, 9)])
def test_per_phase_constants_remain_zero_after_all_weights_change(shape):
    model = MemoryOnlyRawGlobalFeatures()
    gen = torch.Generator().manual_seed(1391)
    with torch.no_grad():
        for parameter in model.parameters():
            parameter.normal_(std=0.2, generator=gen)
    raw = torch.arange(4).float()[None, :, None, None].expand(4, 4, *shape) / 4
    variance = torch.rand(raw.shape, generator=gen)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    assert model(raw, variance, colors).count_nonzero() == 0


def test_no_local_bypass_and_batch_independence_gradients_and_strict_reload():
    model = MemoryOnlyRawGlobalFeatures()
    gen = torch.Generator().manual_seed(1392)
    raw = torch.rand(2, 4, 9, 13, generator=gen)
    variance = torch.rand(raw.shape, generator=gen) * 0.001
    colors = torch.stack([color_indices(p) for p in ("GRBG", "GBRG")])
    assert model(raw, variance, colors).count_nonzero() == 0
    with torch.no_grad():
        model.project.weight.normal_(std=0.1, generator=gen)
    actual = model(raw, variance, colors)
    assert actual.count_nonzero() > 0
    torch.testing.assert_close(
        actual[:1], model(raw[:1], variance[:1], colors[:1]), atol=2e-7, rtol=2e-6
    )
    torch.testing.assert_close(
        actual,
        model(raw.contiguous(memory_format=torch.channels_last), variance, colors),
        atol=0,
        rtol=0,
    )
    actual.square().mean().backward()
    assert all(
        p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().max() > 0
        for p in model.parameters()
    )
    restored = MemoryOnlyRawGlobalFeatures()
    restored.load_state_dict(model.state_dict(), strict=True)
    torch.testing.assert_close(actual, restored(raw, variance, colors), atol=0, rtol=0)
    with torch.no_grad():
        model.write_out.weight.zero_()
    assert model(raw, variance, colors).count_nonzero() == 0


def test_explicit_mode_constructs_memory_operator_and_requires_global_features():
    with pytest.raises(ValueError, match="conditioning requires global features"):
        JointDemosaic(ModelConfig(raw_global_conditioning="memory-only-v3"))
    model = PretrainedRgbDemosaic(
        stabilized=True,
        physical_anchors=True,
        raw_global_features=True,
        raw_global_conditioning="memory-only-v3",
    )
    assert type(model.raw_global) is MemoryOnlyRawGlobalFeatures
    assert ModelConfig().raw_global_conditioning == "legacy-v1"


@pytest.mark.parametrize("other", ["legacy-v1", "cosine-rms-v2"])
@pytest.mark.parametrize("reverse", [False, True])
def test_changed_semantic_mode_rejects_resume(other, reverse):
    configs = [
        {"model": {"raw_global_features": True, "raw_global_conditioning": m}}
        for m in (other, "memory-only-v3")
    ]
    if reverse:
        configs.reverse()
    with pytest.raises(ValueError, match="global conditioning differs"):
        require_resume_global_features(*configs)


def test_memory_mode_initial_state_contract_checks_all_parent_and_branch_tensors():
    from train_reviewed_shadow_trial import verify_initial_restoration

    parent = {f"parent.{i}": torch.tensor(float(i)) for i in range(91)}
    actual = parent | {
        "pretrained_rgb.raw_global." + k: v
        for k, v in MemoryOnlyRawGlobalFeatures().state_dict().items()
    }
    verify_initial_restoration(
        actual, parent, spatial=False, fresh=True, global_features=True, global_tensors=15
    )
    verify_initial_restoration(
        actual, actual, spatial=False, fresh=False, global_features=True, global_tensors=15
    )
    damaged = dict(actual)
    damaged["parent.0"] = torch.ones(())
    with pytest.raises(AssertionError):
        verify_initial_restoration(
            damaged, parent, spatial=False, fresh=True, global_features=True, global_tensors=15
        )
