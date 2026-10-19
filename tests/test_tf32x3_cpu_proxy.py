import numpy as np
import pytest
import torch
from torch import nn

from scripts.probe_tf32x3_cpu import (
    hidden_operand_precision,
    operand_convolution,
    round_tf32,
    split_tf32,
)


def test_halfway_rounding_is_away_from_zero_and_preserves_sign_and_zero():
    values = torch.tensor([0., -0., 1., -1., 1. + 2**-11, -1. - 2**-11])
    actual = round_tf32(values)
    assert torch.equal(actual, torch.tensor([0., -0., 1., -1., 1. + 2**-10, -1. - 2**-10]))
    assert torch.signbit(actual).tolist() == [False, True, False, True, False, True]
    assert torch.equal(round_tf32(values, nearest=False), torch.tensor([0., -0., 1., -1., 1., -1.]))


def test_independent_float64_arithmetic_reference_for_normal_operand_rounding():
    rng = np.random.default_rng(73)
    values = (rng.uniform(-2., 2., 10000) * np.exp2(rng.integers(-40, 40, 10000))).astype(np.float32)
    # Arithmetic frexp/ldexp reference uses no bit masks or implementation helper.
    magnitude = np.abs(values.astype(np.float64))
    mantissa, exponent = np.frexp(magnitude)
    expected = np.copysign(np.ldexp(np.floor(mantissa * 2048 + .5) / 2048, exponent), values)
    actual = round_tf32(torch.from_numpy(values))
    np.testing.assert_array_equal(actual.numpy(), expected.astype(np.float32))


@pytest.mark.parametrize("value", [float('inf'), float('nan'), 2**-140, torch.finfo(torch.float32).max])
def test_unsupported_ranges_are_rejected(value):
    with pytest.raises(ValueError):
        round_tf32(torch.tensor([value], dtype=torch.float32))


def test_cpu_float32_required():
    with pytest.raises(ValueError, match="CPU float32"):
        round_tf32(torch.ones(2, dtype=torch.float64))


def test_three_products_match_explicit_scalar_fp64_reference_and_recover_small_term():
    x = torch.tensor([[[[.1251, -.2014], [.7312, -.6421]]]])
    w = torch.tensor([[[[.38291, -.61328], [.15377, -.27138]]]])
    high, low = split_tf32(w)
    a, b = split_tf32(x)
    actual = operand_convolution(x, high, low)
    reference = (a.double() * high.double() + a.double() * low.double() + b.double() * high.double()).sum()
    exact = (x.double() * w.double()).sum()
    high_only = operand_convolution(x, high, low, three=False).item()
    assert abs(actual.item() - reference.item()) < 1e-7
    assert abs(actual.item() - exact.item()) < abs(high_only - exact.item()) * .01


def test_context_preserves_parameters_and_restores_forward_even_after_exception():
    network = nn.Sequential(nn.Conv2d(4, 4, 3, padding=1, bias=False), nn.ReLU()).eval()
    weights = {k: v.clone() for k, v in network.state_dict().items()}
    ids = [id(v) for v in network.parameters()]
    value = torch.linspace(-.3, .7, 64).reshape(1, 4, 4, 4)
    with torch.inference_mode():
        before = network(value)
        with pytest.raises(RuntimeError, match="sentinel"), hidden_operand_precision(network) as names:
            assert names == ['0'] and 'forward' in network[0].__dict__
            assert torch.isfinite(network(value)).all()
            raise RuntimeError('sentinel')
        assert 'forward' not in network[0].__dict__
        assert torch.equal(network(value), before)
    assert ids == [id(v) for v in network.parameters()]
    assert all(torch.equal(v, weights[k]) for k, v in network.state_dict().items())


def test_probe_rejects_training_and_unsupported_layer_before_modification():
    network = nn.Sequential(nn.Conv2d(4, 4, 3, padding=1, bias=False))
    with pytest.raises(ValueError, match="disabled gradients"), hidden_operand_precision(network):
        pass
    network.eval()
    with torch.inference_mode():
        network[0].groups = 2
        with pytest.raises(ValueError, match="unmodified dense"), hidden_operand_precision(network):
            pass
        assert 'forward' not in network[0].__dict__
