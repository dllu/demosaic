"""Observational capture, exact physical replay and target-free counterfactuals."""

import pytest
import torch
from late_rgb_component_tools import capture_forward, component_outputs
from torch import nn

import demosaic.pretrained_rgb as rgb_module
from demosaic.cfa import color_indices
from demosaic.late_rgb import LateRgbRefinement
from demosaic.vst import GeneralizedAnscombe


class Toy(nn.Module):
    def __init__(self, mode, profile):
        super().__init__()
        self.pretrained_rgb = nn.Module()
        rgb = self.pretrained_rgb
        rgb.processing_scale = 1
        rgb.raw_kernel = rgb.raw_directional = rgb.raw_spectral = None
        rgb.adc_projection = False
        rgb._noise_profiles = (profile,)
        rgb.rgb_refinement = LateRgbRefinement((4, 8, 16, 32), mode)
        with torch.no_grad():
            for layer in [*rgb.rgb_refinement.modulations, rgb.rgb_refinement.output]:
                layer.weight.fill_(0.002)
        self.fail_after_head = False

    def forward(self, packed, variance, colors, wb, matrix):
        rgb = self.pretrained_rgb
        _, normalized, _, condition, offset, span = rgb_module.physical_rgb_features(
            packed, variance, colors, wb, matrix
        )
        b, _, h, w = normalized.shape
        features = torch.cat((normalized.repeat(1, 22, 1, 1)[:, :64], normalized), 1)
        dino = []
        for i, c in enumerate((4, 8, 16, 32)):
            stride = 4 * 2**i
            height, width = (h + -h % 32) // stride, (w + -w % 32) // stride
            field = torch.linspace(-1, 1, width).expand(b, c, height, width).clone()
            dino.append(field)
        output = rgb.rgb_refinement(normalized, features, condition, dino)
        if self.fail_after_head:
            raise RuntimeError("unit failure after observational hooks")
        value = output * span + offset
        transform, scale, _stochastic = rgb._noise_profiles[0]
        return (
            transform.inverse(value) if transform is not None else (value.double() * scale).float()
        )


def inputs():
    generator = torch.Generator().manual_seed(4103)
    return {
        "packed": torch.rand(1, 4, 8, 10, generator=generator) * 0.1,
        "variance": torch.full((1, 4, 8, 10), 1e-4),
        "colors": color_indices("RGGB")[None],
        "wb": torch.tensor([[2.0, 1.0, 1.5]]),
        "matrix": torch.eye(3)[None],
    }


@pytest.mark.parametrize("mode", ["global", "spatial"])
@pytest.mark.parametrize("kind", ["ADC", "Gaussian", "GAT"])
@torch.inference_mode()
def test_capture_and_replay_preserve_actual_output_state_and_rng(mode, kind):
    profile = {
        "ADC": (None, 1.0, False),
        "Gaussian": (None, 0.01, True),
        "GAT": (GeneralizedAnscombe(0.00256, 0.0000262144), 1, True),
    }[kind]
    with torch.random.fork_rng():
        torch.manual_seed(52)
        model = Toy(mode, profile).eval()
    arguments = inputs()
    state = {k: v.clone() for k, v in model.state_dict().items()}
    rng = torch.get_rng_state().clone()
    baseline = model(*arguments.values())
    actual, capture = capture_forward(model, arguments)
    assert torch.equal(actual, baseline)
    result = component_outputs(model, actual, capture)
    assert set(result) == ({"full", "bypass"} if mode == "global" else {"full", "bypass", "pooled"})
    assert torch.equal(result["full"], baseline)
    assert not torch.equal(result["bypass"], baseline)
    if mode == "spatial":
        assert not torch.equal(result["pooled"], baseline)
    assert model.pretrained_rgb.rgb_refinement.mode == mode
    assert torch.equal(rng, torch.get_rng_state())
    assert all(torch.equal(v, state[k]) for k, v in model.state_dict().items())


def test_target_cannot_enter_the_forward():
    model = Toy("global", (None, 1, False)).eval()
    with pytest.raises(ValueError, match="five measurement"):
        capture_forward(model, dict(inputs(), target=torch.zeros(1)))


def test_hooks_and_original_physical_function_are_restored_on_exception():
    model = Toy("spatial", (None, 1, False)).eval()
    model.fail_after_head = True
    original = rgb_module.physical_rgb_features
    head = model.pretrained_rgb.rgb_refinement
    with pytest.raises(RuntimeError, match="unit failure"):
        capture_forward(model, inputs())
    assert rgb_module.physical_rgb_features is original
    assert not head._forward_hooks and not head._forward_pre_hooks


def test_incompatible_projection_is_not_silently_omitted():
    model = Toy("global", (None, 1, False)).eval()
    model.pretrained_rgb.adc_projection = True
    with pytest.raises(ValueError, match="RGB-only"):
        capture_forward(model, inputs())
