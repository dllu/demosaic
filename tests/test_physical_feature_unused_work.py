"""Numerical and autograd parity when anchored channels are built directly."""

import contextlib

import pytest
import torch
from torch.utils._python_dispatch import TorchDispatchMode

from demosaic.cfa import PATTERNS, color_indices
from demosaic.pretrained_rgb import physical_rgb_features
from demosaic.vst import GeneralizedAnscombe
from tests.fixtures.physical_features_before_elimination import original_anchored_features


def profiles():
    return [
        (GeneralizedAnscombe(0.00256, 0.0000262144), 1.0, True),
        (None, 1.0, False),
        (None, 0.01, True),
        (GeneralizedAnscombe(1e-10, 0.0001), 1.0, True),
    ]


def inputs(mode, supplied_rgb, masked):
    packed = torch.linspace(-0.05, 2.0, 4 * 4 * 7 * 9).reshape(4, 4, 7, 9)
    variance = torch.linspace(0.0, 0.2, packed.numel()).reshape_as(packed)
    if mode == "flat-anchored":
        packed.zero_()
        variance.zero_()
    args = [
        packed,
        variance,
        torch.stack([color_indices(p) for p in PATTERNS]),
        torch.tensor([[2.0, 1.0, 1.5], [0.7, 1.0, 2.0], [1.0, 1.0, 1.0], [4.0, 0.8, 1.5]]),
        torch.eye(3).expand(4, -1, -1),
    ]
    kwargs = {"stabilized": mode != "linear"}
    if mode.endswith("anchored"):
        kwargs["photometry_profiles"] = profiles()
    if masked:
        kwargs["normalization_mask"] = torch.tensor([False, True, False, True])
    if supplied_rgb:
        kwargs["rgb"] = torch.linspace(-0.1, 3.0, 4 * 3 * 14 * 18).reshape(4, 3, 14, 18)
    return args, kwargs


def bytes_equal(first, second):
    assert torch.equal(first.contiguous().view(torch.uint8), second.contiguous().view(torch.uint8))


@pytest.mark.parametrize("mode", ["linear", "stabilized", "anchored", "flat-anchored"])
@pytest.mark.parametrize("supplied_rgb", [False, True])
@pytest.mark.parametrize("masked", [False, True])
@pytest.mark.parametrize("autocast", [False, True])
@pytest.mark.parametrize("channels_last", [False, True])
def test_features_and_input_gradients_exact(mode, supplied_rgb, masked, autocast, channels_last):
    args, kwargs = inputs(mode, supplied_rgb, masked)
    if channels_last:
        args[:2] = [v.contiguous(memory_format=torch.channels_last) for v in args[:2]]
        if supplied_rgb:
            kwargs["rgb"] = kwargs["rgb"].contiguous(memory_format=torch.channels_last)
    for value in args[:2]:
        value.requires_grad_()
    leaves = args[:2]
    if supplied_rgb:
        kwargs["rgb"].requires_grad_()
        leaves = [*leaves, kwargs["rgb"]]
    results, gradients = [], []
    for function in [original_anchored_features, physical_rgb_features]:
        context = (
            torch.autocast("cpu", dtype=torch.bfloat16) if autocast else contextlib.nullcontext()
        )
        with context:
            output = function(*args, **kwargs)
        objective = sum((i + 1) * value.square().mean() for i, value in enumerate(output))
        gradient = torch.autograd.grad(objective, leaves)
        assert all(torch.isfinite(v).all() for v in [*output, *gradient])
        results.append(output)
        gradients.append(gradient)
    for first, second in zip(results[0], results[1], strict=True):
        bytes_equal(first, second)
        assert first.stride() == second.stride()
    for first, second in zip(gradients[0], gradients[1], strict=True):
        bytes_equal(first, second)


class FeatureDispatchCensus(TorchDispatchMode):
    def __init__(self):
        super().__init__()
        self.full_condition_concats = 0
        self.full_condition_concat_elements = 0
        self.log_elements = 0

    def __torch_dispatch__(self, function, types, args=(), kwargs=None):
        result = function(*args, **(kwargs or {}))
        if function is torch.ops.aten.cat.default and result.ndim == 4 and result.shape[1] == 21:
            self.full_condition_concats += 1
            self.full_condition_concat_elements += result.numel()
        if function is torch.ops.aten.log.default:
            self.log_elements += result.numel()
        return result


def test_anchored_path_does_not_compute_discarded_channels_or_concatenate_twice():
    args, kwargs = inputs("anchored", True, False)
    counts = []
    for function in [original_anchored_features, physical_rgb_features]:
        counter = FeatureDispatchCensus()
        with counter:
            function(*args, **kwargs)
        counts.append(counter)
    assert [v.full_condition_concats for v in counts] == [2, 1]
    assert [v.full_condition_concat_elements for v in counts] == [42336, 21168]
    assert [v.log_elements for v in counts] == [3024, 0]
