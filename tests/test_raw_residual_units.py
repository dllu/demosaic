import importlib.util
import sys
from pathlib import Path

import pytest
import torch

from demosaic import packed_isotropic
from demosaic.cfa import PATTERNS, bilinear, color_indices
from demosaic.model import JointDemosaic, ModelConfig


def prototype():
    directory = str(Path("scripts").absolute())
    sys.path.insert(0, directory)
    try:
        spec = importlib.util.spec_from_file_location(
            "raw_residual_units", Path("scripts/probe_raw_residual_units.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(directory)


def fixture():
    torch.manual_seed(51)
    model = JointDemosaic(
        ModelConfig(
            restoration_backbone="packed-isotropic",
            camera_conditioning=True,
            width=8,
            isotropic_groups=1,
            isotropic_blocks=1,
            isotropic_local_width=8,
        )
    ).eval()
    packed = torch.rand(4, 4, 7, 9) * 0.6 - 0.02
    variance = packed.clamp_min(0) * 0.002 + 1e-6
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    batch = {"shot": 0.002, "read": 1e-6}
    return model, (packed, variance, colors), batch


def test_zero_head_preserves_physical_signal_and_16bit_changes_all_cfas():
    module = prototype()
    model, args, batch = fixture()
    before = {name: value.clone() for name, value in model.state_dict().items()}
    identities = [id(parameter) for parameter in model.parameters()]
    inputs = [value.clone() for value in args]
    with torch.inference_mode():
        for mode in ["raw", "gain32", "noise-compand", "gain32-residual32"]:
            with module.coordinates(model, mode, batch):
                output = model(*args)
            assert output.dtype == torch.float32
            assert torch.equal(output, bilinear(args[0], args[2]))
        changed = args[0].clone()
        changed[:, 0, 3, 4] += 1 / 65535
        with module.coordinates(model, "gain32-residual32", batch):
            actual = model(changed, *args[1:])
        assert torch.equal(actual, bilinear(changed, args[2]))
        assert not torch.equal(actual, output)
    assert all(torch.equal(value, original) for value, original in zip(args, inputs, strict=True))
    assert all(torch.equal(value, before[name]) for name, value in model.state_dict().items())
    assert identities == [id(parameter) for parameter in model.parameters()]


def test_nonzero_learned_residual_is_scaled_while_signal_skip_stays_fixed():
    module = prototype()
    model, args, batch = fixture()
    torch.nn.init.normal_(model.packed_isotropic.head.weight, std=0.01)
    torch.nn.init.normal_(model.packed_isotropic.head.bias, std=0.01)
    with torch.inference_mode():
        with module.coordinates(model, "gain32", batch):
            unscaled = model(*args)
        with module.coordinates(model, "gain32-residual32", batch):
            scaled = model(*args)
        baseline = bilinear(args[0], args[2])
    torch.testing.assert_close(scaled, baseline + (unscaled - baseline) / 32, rtol=0, atol=6e-8)


def test_zero_head_common_loss_and_head_gradient_scale_without_new_parameters():
    module = prototype()
    model, args, batch = fixture()
    target = torch.rand(4, 3, 14, 18)
    results = {}
    for mode in ["gain32", "gain32-residual32"]:
        model.zero_grad(set_to_none=True)
        with module.coordinates(model, mode, batch):
            loss = (model(*args) - target).square().mean()
        loss.backward()
        gradients = {name: parameter.grad.clone() for name, parameter in model.named_parameters()}
        assert all(
            torch.count_nonzero(value) == 0
            for name, value in gradients.items()
            if ".head." not in name
        )
        results[mode] = loss.detach(), gradients
    assert torch.equal(results["gain32"][0], results["gain32-residual32"][0])
    for name in results["gain32"][1]:
        torch.testing.assert_close(
            results["gain32-residual32"][1][name],
            results["gain32"][1][name] / 32,
            rtol=0,
            atol=0,
        )


def test_context_restores_feature_function_and_head_hooks_after_exception():
    module = prototype()
    model, args, batch = fixture()
    original = packed_isotropic.physical_features
    hooks = dict(model.packed_isotropic.head._forward_hooks)
    with (
        pytest.raises(RuntimeError, match="intentional"),
        module.coordinates(model, "gain32-residual32", batch),
    ):
        model(*args)
        raise RuntimeError("intentional")
    assert packed_isotropic.physical_features is original
    assert dict(model.packed_isotropic.head._forward_hooks) == hooks


@pytest.mark.parametrize("scale", [0, -1, float("nan"), float("inf")])
def test_invalid_residual_units_rejected(scale):
    model, _, _ = fixture()
    with (
        pytest.raises(ValueError, match="finite and positive"),
        prototype().residual_units(model, scale),
    ):
        pass


def test_other_architecture_rejected():
    model = JointDemosaic(ModelConfig(width=8))
    with (
        pytest.raises(ValueError, match="packed isotropic"),
        prototype().residual_units(model, 1 / 32),
    ):
        pass
