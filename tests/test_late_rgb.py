"""Late semantic access, physical parent preservation and portable training state."""

import json
from copy import deepcopy

import numpy as np
import pytest
import torch
import yaml
from torch import nn
from torch.nn import functional as F

from demosaic.cfa import color_indices
from demosaic.inference import load_checkpoint
from demosaic.late_rgb import LateRgbRefinement
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.train import make_optimizer, set_learning_rate, update_ema, validate_late_rgb_only

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


@pytest.mark.parametrize("mode", ["global", "spatial"])
@pytest.mark.parametrize("amp", [False, True])
def test_head_only_updates_hold_common_model_and_EMA_exact_without_common_backward(
    tiny_convnext, mode, amp
):
    torch.manual_seed(91)
    model = JointDemosaic(config(mode)).train()
    initial = {k: v.detach().clone() for k, v in model.state_dict().items()}
    ema = {k: v.detach().clone() for k, v in model.restoration_state_dict().items()}
    optimizer = make_optimizer(
        model, {"lr": 1e-5, "late_rgb_lr_multiplier": 20, "late_rgb_only": True}
    )
    head = model.pretrained_rgb.rgb_refinement
    head_ids = {id(p) for p in head.parameters()}
    assert {id(p) for p in model.parameters() if p.requires_grad} == head_ids
    assert [len(g["params"]) for g in optimizer.param_groups] == [0, 24]
    set_learning_rate(optimizer, 3e-6)
    assert [g["lr"] for g in optimizer.param_groups] == [3e-6, 3e-6 * 20]
    head_inputs, encoder_calls = [], []
    handles = [
        head.register_forward_pre_hook(lambda _m, args: head_inputs.append(args)),
        model.context.backbone.register_forward_hook(lambda *_: encoder_calls.append(True)),
    ]
    raw = torch.rand(2, 4, 17, 25) * 0.2 + 0.1
    args = (raw, torch.ones_like(raw) * 0.0002, color_indices("GBRG"))
    model.set_noise(0.001, 0.000001)
    try:
        for _ in range(3):
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
                prediction = model(*args)
                loss = prediction.square().mean()
            loss.backward()
            assert all(
                p.grad is not None and torch.isfinite(p.grad).all() for p in head.parameters()
            )
            assert all(p.grad is None for p in model.parameters() if id(p) not in head_ids)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1, error_if_nonfinite=True)
            optimizer.step()
            update_ema(model, ema, 0.9, trainable_only=True)
    finally:
        for handle in handles:
            handle.remove()
    assert len(encoder_calls) == len(head_inputs) == 3
    for prediction, features, condition, dino in head_inputs:
        assert not any(v.requires_grad for v in [prediction, features, condition, *dino])
    for name, value in model.state_dict().items():
        if not name.startswith("pretrained_rgb.rgb_refinement."):
            assert torch.equal(value, initial[name]), name
            if name in ema:
                assert torch.equal(ema[name], initial[name]), name
    assert head.output.weight.count_nonzero()
    assert all(layer.weight.count_nonzero() for layer in head.modulations)
    assert not torch.equal(ema["pretrained_rgb.rgb_refinement.output.weight"], head.output.weight)
    assert len(optimizer.state) == 24
    assert all(int(v["step"]) == 3 for v in optimizer.state.values())


@pytest.mark.parametrize("value", [0, 1, None, "true"])
def test_head_only_rejects_non_boolean_selection(value):
    with pytest.raises(ValueError, match="must be a boolean"):
        validate_late_rgb_only({"late_rgb_only": value})


@pytest.mark.parametrize(
    "other", ["raw_kernel_only", "refiner_only", "coarse_refiner_only", "pyramid_refiner_only"]
)
def test_head_only_rejects_combined_scopes(other):
    with pytest.raises(ValueError, match="cannot combine"):
        validate_late_rgb_only({"late_rgb_only": True, other: True})


def test_head_only_requires_an_actual_late_head():
    model = nn.Module()
    model.config = config()
    with pytest.raises(ValueError, match="requires late RGB refinement"):
        make_optimizer(model, {"late_rgb_only": True})


def test_trainable_only_EMA_leaves_frozen_parameters_and_buffers_untouched():
    model = nn.Module()
    model.head = nn.Parameter(torch.tensor([3.0]))
    model.common = nn.Parameter(torch.tensor([5.0]), requires_grad=False)
    model.register_buffer("buffer", torch.tensor([7.0]))
    model.register_buffer("integer", torch.tensor([9]))
    model.restoration_state_dict = model.state_dict
    initial = {k: torch.zeros_like(v) for k, v in model.state_dict().items()}
    scoped = deepcopy(initial)
    update_ema(model, scoped, 0.5, trainable_only=True)
    assert torch.equal(scoped["head"], torch.tensor([1.5]))
    assert all(torch.equal(scoped[k], initial[k]) for k in ["common", "buffer", "integer"])
    # The absent/false option preserves the existing complete-state update.
    update_ema(model, initial, 0.5)
    assert torch.equal(initial["head"], scoped["head"])
    assert torch.equal(initial["common"], torch.tensor([2.5]))
    assert torch.equal(initial["buffer"], torch.tensor([3.5]))
    assert torch.equal(initial["integer"], model.integer)


def test_head_only_training_restart_preserves_all_states_and_rejects_scope_change(
    tiny_convnext, tmp_path
):
    from demosaic.train import train

    torch.manual_seed(92)
    parent = JointDemosaic(config())
    weights = {k: v.detach().clone() for k, v in parent.restoration_state_dict().items()}
    parent_path = tmp_path / "parent.pt"
    torch.save(
        {"model": weights, "ema": weights, "model_config": parent.config.to_dict()}, parent_path
    )
    np.save(tmp_path / "clean.npy", np.full((40, 40, 3), 11796, dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps({"id": split, "cache": "clean.npy", "split": split})
            for split in ["train", "val"]
        )
    )
    cfg = {
        "model": config("global").to_dict(),
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
        "training_execution": "deterministic-v1",
        "data_seed_per_step": True,
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 1,
        "val_batches": 1,
        "validation_images": 1,
        "min_available_gb": 0,
        "late_rgb_only": True,
        "late_rgb_lr_multiplier": 20,
        "lr": 1e-5,
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg))
    full = train(path, initialize=parent_path)
    cfg["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(cfg))
    middle = train(path, initialize=parent_path, stop_after=2)
    assert torch.load(middle, weights_only=True)["step"] == 2
    resumed = train(path, resume=middle)
    actual = torch.load(resumed, weights_only=True)
    expected = torch.load(full, weights_only=True)

    def identical(a, b):
        assert type(a) is type(b)
        if torch.is_tensor(a):
            assert torch.equal(a, b)
        elif isinstance(a, dict):
            assert a.keys() == b.keys()
            for key in a:
                identical(a[key], b[key])
        elif isinstance(a, (list, tuple)):
            assert len(a) == len(b)
            for x, y in zip(a, b, strict=True):
                identical(x, y)
        else:
            assert a == b

    for key in ["model", "ema", "optimizer", "torch_rng", "python_rng", "cuda_rng", "best", "step"]:
        identical(actual[key], expected[key])
    for field in ["model", "ema"]:
        for name, value in weights.items():
            assert torch.equal(actual[field][name], value), (field, name)
    assert len(actual["optimizer"]["state"]) == 24
    cfg["late_rgb_only"] = False
    path.write_text(yaml.safe_dump(cfg))
    with pytest.raises(ValueError, match="Resume late RGB training scope differs"):
        train(path, resume=resumed)
