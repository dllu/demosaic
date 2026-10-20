"""Retain exact inverse values/derivatives while avoiding unused table-mode work."""

import importlib.util
import math
from collections import Counter
from pathlib import Path

import pytest
import torch
from torch.utils._python_dispatch import TorchDispatchMode

from demosaic.vst import GeneralizedAnscombe

SPEC = importlib.util.spec_from_file_location(
    "vst_reference", Path(__file__).parent / "fixtures/vst_inverse_before_elimination.py"
)
LEGACY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LEGACY)


def bytes_equal(first, second):
    return torch.equal(
        first.detach().contiguous().reshape(-1).view(torch.uint8),
        second.detach().contiguous().reshape(-1).view(torch.uint8),
    )


@pytest.mark.parametrize("mode", ["table", "closedform", "algebraic"])
@pytest.mark.parametrize(
    "shot,read",
    [
        (0.001, 0.0),
        (0.001, 1.6e-7),
        (0.00256, 0.0000262144),
        (0.001, 0.000256),
        (1e-5, 1e-4),
        (1e-10, 1e-4),
    ],
)
@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
def test_original_values_and_input_derivatives_are_byte_identical(mode, shot, read, dtype):
    transform = GeneralizedAnscombe(shot, read, inverse=mode)
    values = torch.linspace(-2 * math.sqrt(transform.q) - 4, 2e4, 32, dtype=dtype)
    if mode == "table":
        anchors = transform.expected[[0, 1, 100, 1600, -1]].to(dtype)
        values = torch.cat(
            [
                values,
                anchors,
                torch.nextafter(anchors, torch.full_like(anchors, -float("inf"))),
                torch.nextafter(anchors, torch.full_like(anchors, float("inf"))),
            ]
        )
    # A strided input exercises the inverse's contiguous search keys too.
    storage = torch.stack([values, values]).T
    current = storage[:, 0].detach().requires_grad_()
    reference = storage.clone()[:, 0].detach().requires_grad_()
    before = current.detach().clone()
    actual = transform.inverse(current)
    expected = LEGACY.inverse_before_elimination(transform, reference)
    assert (
        actual.dtype == torch.float32
        and torch.isfinite(actual).all()
        and bytes_equal(actual, expected)
    )
    weights = torch.linspace(-0.9, 0.8, len(actual))
    first = torch.autograd.grad((actual * weights).sum(), current)[0]
    second = torch.autograd.grad((expected * weights).sum(), reference)[0]
    assert torch.isfinite(first).all() and bytes_equal(first, second)
    assert bytes_equal(current, before)


class Operations(TorchDispatchMode):
    def __init__(self):
        super().__init__()
        self.calls = Counter()
        self.cubed_elements = 0

    def __torch_dispatch__(self, func, types, args=(), kwargs=None):
        self.calls[str(func)] += 1
        if str(func) == "aten.pow.Tensor_Scalar" and args[1] == 3:
            self.cubed_elements += args[0].numel()
        return func(*args, **(kwargs or {}))


def test_table_path_avoids_unused_full_canvas_cube_and_dispatches():
    transform = GeneralizedAnscombe(0.00256, 0.0000262144)
    value = torch.linspace(-1.0, 30.0, 3 * 64 * 80).reshape(1, 3, 64, 80)
    with Operations() as old:
        expected = LEGACY.inverse_before_elimination(transform, value)
    with Operations() as new:
        actual = transform.inverse(value)
    assert bytes_equal(actual, expected)
    assert old.cubed_elements == value.numel() and new.cubed_elements == 0
    assert sum(old.calls.values()) - sum(new.calls.values()) >= 10
