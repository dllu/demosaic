from pathlib import Path

import numpy as np
import pytest
import torch
import yaml

from demosaic.cfa import PATTERNS, color_indices
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import PretrainedRgbDemosaic
from demosaic.raw_global_features import require_resume_global_features
from demosaic.raw_global_memory_features import MemoryOnlyRawGlobalFeatures
from demosaic.raw_patch_memory_features import (
    PatchMemoryRawGlobalFeatures,
    neighboring_gradients,
)


def test_shared_initial_state_zero_patch_and_constructor_rng_under_meta_default():
    before = torch.get_rng_state()
    original = MemoryOnlyRawGlobalFeatures()
    with torch.device("meta"):
        patch = PatchMemoryRawGlobalFeatures()
    assert torch.equal(before, torch.get_rng_state())
    assert all(p.device.type == "cpu" for p in patch.parameters())
    old, new = original.state_dict(), patch.state_dict()
    assert len(new) == 16 and sum(v.numel() for v in new.values()) == 16192
    assert new.keys() - old.keys() == {"patch_embed.weight"}
    assert all(torch.equal(v, new[k]) for k, v in old.items())
    assert new["patch_embed.weight"].shape == (32, 64, 1, 1)
    assert new["patch_embed.weight"].count_nonzero() == 0
    assert new["project.weight"].count_nonzero() == 0


@pytest.mark.parametrize("shape", [(1, 1), (3, 5)])
def test_neighbor_coordinates_and_embedding_match_independent_numpy(shape):
    height, width = shape
    rng = np.random.default_rng(140)
    content = rng.normal(size=(2, 8, height, width))
    expected = np.zeros((2, 64, height, width))
    offsets = [(dy, dx) for dy in [-1, 0, 1] for dx in [-1, 0, 1] if (dy, dx) != (0, 0)]
    for slot, (dy, dx) in enumerate(offsets):
        for y in range(height):
            for x in range(width):
                if 0 <= y + dy < height and 0 <= x + dx < width:
                    expected[:, 8 * slot : 8 * (slot + 1), y, x] = content[:, :, y + dy, x + dx]
    actual = neighboring_gradients(torch.from_numpy(content))
    np.testing.assert_array_equal(actual.numpy(), expected)
    model = PatchMemoryRawGlobalFeatures().double()
    with torch.no_grad():
        model.patch_embed.weight.copy_(torch.from_numpy(rng.normal(size=(32, 64, 1, 1))))
    point = content.transpose(0, 2, 3, 1).reshape(2, height * width, 8)
    point = point @ model.embed.weight.detach().numpy().T
    patch = np.einsum(
        "oi,bihw->bohw", model.patch_embed.weight.detach().numpy()[:, :, 0, 0], expected
    )
    gold = point + patch.transpose(0, 2, 3, 1).reshape(2, height * width, 32)
    np.testing.assert_allclose(
        model.embed_content(torch.from_numpy(content)).detach().numpy(),
        gold,
        rtol=2e-13,
        atol=2e-13,
    )


def test_spatial_arrangement_changes_descriptor_without_center_or_opposite_edge_leakage():
    model = PatchMemoryRawGlobalFeatures()
    with torch.no_grad():
        model.embed.weight.zero_()
        # Slot4 is the east neighbor in the independently specified row-major order.
        model.patch_embed.weight.zero_()
        model.patch_embed.weight[0, 4 * 8, 0, 0] = 1
    content = torch.zeros(1, 8, 3, 5)
    content[0, 0, 1, 3] = 2
    embedded = model.embed_content(content).reshape(1, 3, 5, 32)
    assert embedded[0, 1, 2, 0] == 2
    assert embedded[0, 1, 3, 0] == 0  # The center is not a neighbor.
    assert embedded[0, 1, 4, 0] == 0  # No opposite-border wrap.
    content[0, 0, 1, 3], content[0, 0, 0, 0] = 0, 2
    assert model.embed_content(content).reshape(1, 3, 5, 32)[0, 1, 2, 0] == 0


@pytest.mark.parametrize("shape", [(1, 1), (3, 11), (13, 9)])
def test_all_phase_constants_remain_exact_zero_after_nonzero_adaptation(shape):
    model = PatchMemoryRawGlobalFeatures()
    gen = torch.Generator().manual_seed(1401)
    with torch.no_grad():
        for p in model.parameters():
            p.normal_(std=0.2, generator=gen)
    raw = torch.arange(4).float()[None, :, None, None].expand(4, 4, *shape) / 4
    variance = torch.rand(raw.shape, generator=gen)
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    assert model(raw, variance, colors).count_nonzero() == 0


def test_zero_patch_preserves_point_tokens_and_all_outputs_follow_memory():
    old, new = MemoryOnlyRawGlobalFeatures(), PatchMemoryRawGlobalFeatures()
    gen = torch.Generator().manual_seed(1402)
    content = torch.rand(2, 8, 9, 13, generator=gen)
    torch.testing.assert_close(
        old.embed_content(content), new.embed_content(content), rtol=0, atol=0
    )
    raw = torch.rand(2, 4, 9, 13, generator=gen)
    variance = torch.rand(raw.shape, generator=gen) * 0.001
    colors = torch.stack([color_indices(p) for p in ["GRBG", "GBRG"]])
    assert new(raw, variance, colors).count_nonzero() == 0
    with torch.no_grad():
        new.project.weight.normal_(std=0.1, generator=gen)
        new.patch_embed.weight.normal_(std=0.03, generator=gen)
    value = new(raw, variance, colors)
    torch.testing.assert_close(
        value[:1], new(raw[:1], variance[:1], colors[:1]), atol=3e-7, rtol=3e-6
    )
    torch.testing.assert_close(
        value,
        new(raw.contiguous(memory_format=torch.channels_last), variance, colors),
        rtol=0,
        atol=0,
    )
    value.square().mean().backward()
    assert all(
        p.grad is not None and torch.isfinite(p.grad).all() and p.grad.abs().max() > 0
        for p in new.parameters()
    )
    reloaded = PatchMemoryRawGlobalFeatures()
    reloaded.load_state_dict(new.state_dict(), strict=True)
    torch.testing.assert_close(value, reloaded(raw, variance, colors), rtol=0, atol=0)
    damaged = dict(new.state_dict())
    damaged.pop("patch_embed.weight")
    with pytest.raises(RuntimeError, match="Missing key"):
        reloaded.load_state_dict(damaged, strict=True)
    with torch.no_grad():
        new.write_out.weight.zero_()
    assert new(raw, variance, colors).count_nonzero() == 0


def test_explicit_factory_and_global_tensor_scope():
    with pytest.raises(ValueError, match="conditioning requires global features"):
        JointDemosaic(ModelConfig(raw_global_conditioning="patch-memory-v4"))
    model = PretrainedRgbDemosaic(
        stabilized=True,
        physical_anchors=True,
        raw_global_features=True,
        raw_global_conditioning="patch-memory-v4",
    )
    assert type(model.raw_global) is PatchMemoryRawGlobalFeatures
    from train_reviewed_shadow_trial import verify_initial_restoration

    parent = {f"parent.{i}": torch.tensor(float(i)) for i in range(91)}
    state = parent | {
        "pretrained_rgb.raw_global." + k: v for k, v in model.raw_global.state_dict().items()
    }
    verify_initial_restoration(
        state, parent, spatial=False, fresh=True, global_features=True, global_tensors=16
    )
    verify_initial_restoration(
        state, state, spatial=False, fresh=False, global_features=True, global_tensors=16
    )


@pytest.mark.parametrize("other", ["legacy-v1", "cosine-rms-v2", "memory-only-v3"])
@pytest.mark.parametrize("reverse", [False, True])
def test_changed_patch_mode_rejects_before_resume(other, reverse):
    configs = [
        {"model": {"raw_global_features": True, "raw_global_conditioning": m}}
        for m in [other, "patch-memory-v4"]
    ]
    if reverse:
        configs.reverse()
    with pytest.raises(ValueError, match="global conditioning differs"):
        require_resume_global_features(*configs)


def test_recipe_changes_only_the_declared_architecture():
    configs = [
        yaml.safe_load(Path(p).read_text())
        for p in [
            "configs/quality-v120-raw-patch-memory-pilot-v140.yaml",
            "configs/quality-v120-raw-global-memory-only-pilot-v139.yaml",
        ]
    ]
    for c in configs:
        c.pop("experiment_notes")
        c.pop("run")
        c["model"].pop("raw_global_conditioning")
    assert configs[0] == configs[1]
