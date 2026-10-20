"""Late semantic access, physical parent preservation and portable training state."""

from copy import deepcopy

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from demosaic.cfa import color_indices
from demosaic.inference import load_checkpoint
from demosaic.late_rgb import LateRgbRefinement
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.train import make_optimizer, set_learning_rate

CHANNELS = (2, 3, 4, 5)


def inputs(batch=2, height=34, width=50):
    generator = torch.Generator().manual_seed(891)
    values = [torch.rand(batch, c, height, width, generator=generator) for c in [3, 67, 21]]
    features = tuple(
        torch.rand(
            batch, c, (height + -height % 32) // s, (width + -width % 32) // s, generator=generator
        )
        for c, s in zip(CHANNELS, [4, 8, 16, 32], strict=True)
    )
    return *values, features


@pytest.mark.parametrize("amp", [False, True])
def test_zero_output_preserves_parent_gradient_and_head_and_prompts_learn(amp):
    branch = LateRgbRefinement(CHANNELS, "spatial", width=8)
    p, f, c, dino = inputs()
    for value in [p, f, c, *dino]:
        value.requires_grad_()
    optimizer = torch.optim.SGD(branch.parameters(), lr=0.1)
    with torch.autocast("cpu", enabled=amp, dtype=torch.bfloat16):
        output = branch(p, f, c, dino)
    assert output.dtype == torch.float32 and torch.equal(output, p)
    output.square().mean().backward()
    reference = p.detach().clone().requires_grad_()
    reference.square().mean().backward()
    assert torch.equal(p.grad, reference.grad)
    assert not f.grad.count_nonzero() and not c.grad.count_nonzero()
    assert all(v.grad is None for v in dino)
    assert branch.output.weight.grad.count_nonzero()
    assert all(not layer.weight.grad.count_nonzero() for layer in branch.modulations)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    with torch.autocast("cpu", enabled=amp, dtype=torch.bfloat16):
        branch(p, f, c, dino).square().mean().backward()
    assert all(layer.weight.grad.count_nonzero() for layer in branch.modulations)
    assert all(torch.isfinite(p.grad).all() for p in branch.parameters())


def test_global_pooling_is_spatially_invariant_while_spatial_features_change_refinement():
    models = [LateRgbRefinement(CHANNELS, mode, width=8) for mode in ["global", "spatial"]]
    models[1].load_state_dict(models[0].state_dict())
    with torch.no_grad():
        for model in models:
            model.output.weight.fill_(0.01)
            for layer in model.modulations:
                layer.weight.fill_(0.125)
    p, f, c, features = inputs(batch=1)
    features = tuple(torch.arange(v.numel()).reshape_as(v).float() / 4096 for v in features)
    changed = tuple(v.flip(-1) for v in features)
    with torch.no_grad():
        a, b = [models[0](p, f, c, ds) for ds in [features, changed]]
        torch.testing.assert_close(a, b, atol=1e-7, rtol=1e-6)
        a, b = [models[1](p, f, c, ds) for ds in [features, changed]]
    assert (a - b).abs().max() > 1e-5


def test_spatial_prompts_crop_padded_coordinates_without_resizing_and_batches_are_independent():
    model = LateRgbRefinement(CHANNELS, "spatial", width=8).eval()
    with torch.no_grad():
        model.input.weight.zero_()
        model.input.bias.zero_()
        for layer in model.modulations:
            layer.weight.fill_(0.01)
        model.output.weight.fill_(0.01)
    p, f, c, features = inputs()
    captured = []
    hook = model.blocks.register_forward_pre_hook(lambda _m, args: captured.append(args[0].clone()))
    with torch.no_grad():
        together = model(p, f, c, features)
        for i in range(2):
            separate = model(
                p[i : i + 1], f[i : i + 1], c[i : i + 1], tuple(v[i : i + 1] for v in features)
            )
            torch.testing.assert_close(separate, together[i : i + 1], atol=2e-6, rtol=1e-6)
        captured.clear()
        model(p, f, c, features)
        model(*[F.pad(v, (0, 14, 0, 30), mode="replicate") for v in [p, f, c]], features)
    hook.remove()
    torch.testing.assert_close(captured[0], captured[1][..., :34, :50], atol=0, rtol=0)
    with pytest.raises(ValueError, match="padded native"):
        model(p, f, c, tuple(v[..., :-1, :] for v in features))


@pytest.fixture
def tiny_convnext(monkeypatch):
    from transformers import AutoModel, DINOv3ConvNextConfig, DINOv3ConvNextModel

    backbone = DINOv3ConvNextModel(
        DINOv3ConvNextConfig(hidden_sizes=[8, 16, 24, 32], depths=[1, 1, 1, 1])
    ).eval()
    monkeypatch.setattr(AutoModel, "from_pretrained", lambda *args, **kwargs: deepcopy(backbone))


def config(mode="none", **extra):
    values = {
        "restoration_backbone": "pretrained-rgb",
        "width": 64,
        "camera_conditioning": True,
        "variance_stabilization": True,
        "physical_anchors": True,
        "rgb_middle_skip_fp32": True,
        "dino": True,
        "dino_feature_fusion": "convnext-pyramid",
        "late_rgb_refinement": mode,
    }
    return ModelConfig(**(values | extra))


@pytest.mark.parametrize("amp", [False, True])
def test_whole_model_zero_heads_preserve_common_rng_values_gradients_and_one_DINO_pass(
    tiny_convnext, amp
):
    models, rngs = [], []
    for mode in ["none", "global", "spatial"]:
        torch.manual_seed(25)
        models.append(JointDemosaic(config(mode)))
        rngs.append(torch.get_rng_state().clone())
    assert all(torch.equal(rngs[0], r) for r in rngs)
    parent = models[0]
    with torch.no_grad():
        for gate in parent.context.gates:
            gate.fill_(0.1)
    for model in models[1:]:
        missing = model.load_state_dict(parent.restoration_state_dict(), strict=False)
        assert not missing.unexpected_keys
        expected = {
            key
            for key in model.state_dict()
            if key.startswith(("context.backbone.", "pretrained_rgb.rgb_refinement."))
        }
        assert set(missing.missing_keys) == expected
    raw = torch.rand(2, 4, 17, 25) * 0.2 + 0.1
    variance = torch.ones_like(raw) * 0.0002
    wb = torch.tensor([[2.0, 1.0, 1.5], [0.8, 1.0, 1.2]])
    colors = torch.stack([color_indices(p) for p in ["GBRG", "RGGB"]])
    outputs = []
    for model in models:
        model.set_noise(torch.tensor([0.001, 0]), torch.tensor([0.000001, 0]))
        calls = []
        hook = model.context.backbone.register_forward_hook(
            lambda *_args, calls=calls: calls.append(True)
        )
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
            output, auxiliary = model(raw, variance, colors, wb, auxiliary=True)
        hook.remove()
        assert len(calls) == 1
        output.square().mean().backward()
        outputs.append((output, auxiliary))
        assert all(
            p.grad is None and not p.requires_grad for p in model.context.backbone.parameters()
        )
    for prediction in outputs[1:]:
        for a, b in zip(outputs[0], prediction, strict=True):
            assert torch.equal(a, b)
    for model in models[1:]:
        actual = dict(model.named_parameters())
        for name, value in parent.named_parameters():
            if value.requires_grad:
                assert torch.equal(value.grad, actual[name].grad), name
    for name, value in models[1].restoration_state_dict().items():
        assert torch.equal(value, models[2].state_dict()[name]), name


def test_nonzero_refinement_and_mode_round_trip_and_missing_weights_fail(tiny_convnext, tmp_path):
    model = JointDemosaic(config("spatial")).eval()
    model.set_noise(0.001, 0.000001)
    with torch.no_grad():
        model.pretrained_rgb.rgb_refinement.output.weight.fill_(0.001)
        model.pretrained_rgb.rgb_refinement.modulations[0].weight.fill_(0.001)
    state = model.restoration_state_dict()
    path = tmp_path / "late.pt"
    torch.save({"model_config": model.config.to_dict(), "model": state}, path)
    loaded, _ = load_checkpoint(path)
    loaded.set_noise(0.001, 0.000001)
    loaded.eval()
    raw = torch.rand(1, 4, 17, 25) * 0.2
    with torch.no_grad():
        args = (raw, torch.full_like(raw, 0.0002), color_indices("BGGR"))
        assert torch.equal(model(*args), loaded(*args))
    assert loaded.config.late_rgb_refinement == "spatial"
    del state["pretrained_rgb.rgb_refinement.output.weight"]
    torch.save({"model_config": model.config.to_dict(), "model": state}, path)
    with pytest.raises(ValueError, match="Incompatible checkpoint"):
        load_checkpoint(path)
    legacy = config().to_dict()
    del legacy["late_rgb_refinement"]
    assert ModelConfig.from_checkpoint(legacy).late_rgb_refinement == "none"


@pytest.mark.parametrize(
    "extra",
    [
        {"late_rgb_refinement": "bad"},
        {"late_rgb_refinement": False},
        {"dino": False},
        {"dino_feature_fusion": "bottleneck"},
        {"variance_stabilization": False},
        {"physical_anchors": False},
        {"rgb_processing_scale": 2},
        {"raw_spectral_residual": True},
        {"raw_directional_residual": True},
        {"raw_kernel_reconstruction": True},
        {"adc_cfa_projection": True},
    ],
)
def test_invalid_modes_rejected_before_backbone_loading(extra):
    with pytest.raises(ValueError, match="Late RGB"):
        JointDemosaic(config("spatial", **extra))


def test_optimizer_exact_new_parameter_group_and_invalid_multiplier():
    model = nn.Module()
    model.config = config("global")
    model.common = nn.Linear(2, 2)
    model.pretrained_rgb = nn.Module()
    model.pretrained_rgb.rgb_refinement = LateRgbRefinement(CHANNELS, "global", width=8)
    optimizer = make_optimizer(model, {"lr": 1e-5, "late_rgb_lr_multiplier": 20})
    assert {id(p) for p in optimizer.param_groups[1]["params"]} == {
        id(p) for p in model.pretrained_rgb.rgb_refinement.parameters()
    }
    assert {id(p) for g in optimizer.param_groups for p in g["params"]} == {
        id(p) for p in model.parameters()
    }
    set_learning_rate(optimizer, 3e-6)
    assert [g["lr"] for g in optimizer.param_groups] == [3e-6, 3e-6 * 20]
    for value in [0, -1, float("nan"), float("inf")]:
        with pytest.raises(ValueError, match="Late RGB"):
            make_optimizer(model, {"late_rgb_lr_multiplier": value})
    model.config.late_rgb_refinement = "none"
    with pytest.raises(ValueError, match="requires late RGB"):
        make_optimizer(model, {"late_rgb_lr_multiplier": 20})
