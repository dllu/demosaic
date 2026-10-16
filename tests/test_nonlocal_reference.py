"""Independent RAW packing/noise/range contracts for the optional reference."""

import pytest
import torch
from torch import nn

from demosaic.cfa import PATTERNS, color_indices, malvar
from demosaic.nonlocal_reference import NonlocalRawReference


class RecordingNetwork(nn.Module):
    def __init__(self, *, shifts=None):
        super().__init__()
        self.inputs = []
        self.shifts = shifts

    def forward(self, x):
        self.inputs.append(x.detach().clone())
        output = x[:, :4].clone()
        if self.shifts is not None:
            output += output.new_tensor(self.shifts)[None, :, None, None]
        return output


@pytest.mark.parametrize("pattern", PATTERNS)
def test_authors_phase_order_std_and_independent_malvar(pattern):
    network = RecordingNetwork(shifts=[-0.3, 0.1, 0.6, -0.2])
    model = NonlocalRawReference(network).set_noise(0.00256, 0.0000262144)
    raw = torch.arange(4 * 7 * 9).reshape(1, 4, 7, 9).float() / 251
    raw[..., 0, 0], raw[..., -1, -1] = -0.02, 1.1
    colors = color_indices(pattern)
    wb = torch.tensor([[2.0, 1.0, 1.5]])
    result = model(raw, torch.full_like(raw, 99.0), colors, wb)
    # Oracle enumerates physical rows/columns, independently of tensor gather.
    letter_grid = [pattern[:2], pattern[2:]]
    red_y = next(y for y, row in enumerate(letter_grid) if "R" in row)
    blue_y = 1 - red_y
    red_x = letter_grid[red_y].index("R")
    blue_x = letter_grid[blue_y].index("B")
    order = [
        2 * red_y + red_x,
        2 * red_y + (1 - red_x),
        2 * blue_y + blue_x,
        2 * blue_y + (1 - blue_x),
    ]
    captured = network.inputs[0]
    expected_raw = torch.stack([raw[0, i].clamp(0, 1) for i in order])[None]
    assert torch.equal(captured[:, :4], expected_raw)
    torch.testing.assert_close(captured[:, 4:].square(), 0.00256 * expected_raw + 0.0000262144)
    canonical = torch.empty_like(raw)
    for i, phase in enumerate(order):
        canonical[:, phase] = (expected_raw[:, i] + network.shifts[i]).clamp(0, 1)
    assert torch.equal(result, malvar(canonical, colors, wb))
    assert result.dtype == torch.float32 and result.shape == (1, 3, 14, 18)


def test_mixed_cfa_batch_adc_no_bypass_and_native_precision_under_autocast():
    network = RecordingNetwork()
    model = NonlocalRawReference(network).set_noise(0, 0)
    raw = torch.linspace(0.1, 0.3, 4 * 4 * 8 * 8).reshape(4, 4, 8, 8)
    raw[0, :, :, :4] = 12000 / 65535
    raw[0, :, :, 4:] = 12001 / 65535
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    with torch.autocast("cpu", dtype=torch.bfloat16):
        output = model(raw, torch.ones_like(raw), colors)
    expected = torch.cat([malvar(raw[i : i + 1], colors[i : i + 1]) for i in range(4)])
    assert torch.equal(output, expected)
    assert len(network.inputs) == 4 and all(x.shape[0] == 1 for x in network.inputs)
    assert all(x.dtype == torch.float32 and not x[:, 4:].count_nonzero() for x in network.inputs)
    assert output[0, 1, 4, 4] != output[0, 1, 4, 12]


@pytest.mark.parametrize("shot,read", [(-1, 0), (0, -1), (float("nan"), 0), (0, float("inf"))])
def test_rejects_invalid_noise(shot, read):
    with pytest.raises(ValueError, match="nonnegative"):
        NonlocalRawReference(RecordingNetwork()).set_noise(shot, read)


def test_requires_explicit_conditioning_and_valid_cfa():
    model = NonlocalRawReference(RecordingNetwork())
    raw = torch.full((1, 4, 8, 8), 0.2)
    with pytest.raises(ValueError, match="conditioning"):
        model(raw, raw, color_indices("RGGB"))
    model.set_noise(0, 0)
    for colors in [torch.tensor([0, 1, 2, 1]), torch.tensor([0, 0, 1, 2])]:
        with pytest.raises(ValueError, match="Bayer"):
            model(raw, raw, colors)
    with pytest.raises(ValueError, match="finite"):
        model(raw * float("nan"), raw, color_indices("RGGB"))


@pytest.mark.parametrize(
    "output", [torch.zeros(1, 3, 8, 8), torch.full((1, 4, 8, 8), float("nan"))]
)
def test_rejects_invalid_network_outputs(output):
    class BrokenNetwork(nn.Module):
        def forward(self, x):
            return output

    model = NonlocalRawReference(BrokenNetwork()).set_noise(0.001, 0.000001)
    raw = torch.full((1, 4, 8, 8), 0.2)
    with pytest.raises(ValueError, match="invalid packed RAW"):
        model(raw, raw, color_indices("RGGB"))


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA unavailable")
def test_nondefault_cuda_stream_is_rejected_before_unvalidated_native_launch():
    model = NonlocalRawReference(RecordingNetwork()).cuda().set_noise(.001, .000001)
    with torch.cuda.stream(torch.cuda.Stream()):
        raw = torch.full((1, 4, 8, 8), .2, device="cuda")
        with pytest.raises(ValueError, match="default CUDA stream"):
            model(raw, raw, color_indices("RGGB", device="cuda"))
