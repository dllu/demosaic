"""Independent linear adjoints for deliberate common-loss gradient routing."""

import numpy as np
import pytest
import torch

from demosaic.archive_metrics import noisy_malvar
from demosaic.cfa import PATTERNS, color_indices, malvar
from paired_common_objective import paired_common_error_loss
from paired_common_routing import _UseCorrectionAdjoint, common_output_with_fixed_support


class IdentitySynthesis:
    def synthesis(self, values, geometry):
        assert geometry == "identity"
        return values


def malvar_matrix(height, width, colors, wb):
    """Build an independent NumPy linear operator from impulse basis vectors."""
    columns = []
    for k in range(4 * height * width):
        packed = np.zeros((1, 4, height, width), dtype=np.float64)
        packed.reshape(-1)[k] = 1
        columns.append(noisy_malvar({"packed": packed, "colors": colors, "wb": wb}).ravel())
    return np.stack(columns, 1)


def fixture(pattern, height=3, width=4):
    rng = np.random.default_rng(16601)
    colors = color_indices(pattern)[None].expand(2, -1)
    wb = torch.tensor([[1.3, 1.0, 1.8]]).expand(2, -1)
    delta = torch.tensor(rng.normal(size=(2, 4, height, width)) * 1e-4, dtype=torch.float32, requires_grad=True)
    logits = torch.tensor(rng.normal(size=(2, 1, height, width)), dtype=torch.float32, requires_grad=True)
    # Support depends on proposal as well as its own parameter: both indirect
    # and direct derivatives through the support activation must be removed.
    support = (logits + delta.mean(1, keepdim=True) * 1000).sigmoid()
    spatial = torch.tensor(rng.normal(size=(2, 3, 2 * height, 2 * width)) * 1e-4, dtype=torch.float32, requires_grad=True)
    base = torch.tensor(rng.uniform(0.001, 0.01, size=spatial.shape), dtype=torch.float32)
    output = base + malvar(delta * support, colors, wb) + spatial
    aux = {"spectral_delta": delta, "geometry": "identity", "support": support, "spatial_correction": spatial}
    return output, aux, colors, wb, delta, logits, spatial


@pytest.mark.parametrize("pattern", PATTERNS)
def test_values_and_complete_adjoint_against_independent_numpy_operator(pattern):
    output, aux, colors, wb, delta, logits, spatial = fixture(pattern)
    rng = np.random.default_rng(16602)
    upstream = rng.normal(size=output.shape).astype(np.float32)
    result = common_output_with_fixed_support(IdentitySynthesis(), output, aux, colors, wb)
    assert np.array_equal(result.detach().numpy().view(np.int32), output.detach().numpy().view(np.int32))
    gradients = torch.autograd.grad((result * torch.tensor(upstream)).sum(), (delta, logits, spatial, output), allow_unused=True)
    operator = malvar_matrix(3, 4, colors[:1].numpy(), wb[:1].numpy())
    expected = np.stack([(operator.T @ g.ravel()).reshape(4, 3, 4) for g in upstream]) * aux["support"].detach().numpy()
    np.testing.assert_allclose(gradients[0].numpy(), expected, rtol=3e-6, atol=1e-6)
    assert gradients[1] is None and gradients[3] is None
    assert torch.equal(gradients[2], torch.tensor(upstream))


@pytest.mark.parametrize("pattern", PATTERNS)
def test_full_common_loss_value_and_intended_parameter_gradients(pattern):
    output, aux, colors, wb, delta, logits, spatial = fixture(pattern)
    target = output.detach() + torch.arange(output.numel(), dtype=torch.float32).reshape(output.shape) * 1e-7
    target.requires_grad_()
    routed = common_output_with_fixed_support(IdentitySynthesis(), output, aux, colors, wb)
    loss = paired_common_error_loss(routed, target, [[0, 1]])
    ordinary = paired_common_error_loss(output, target, [[0, 1]])
    assert torch.equal(loss, ordinary)
    grads = torch.autograd.grad(loss, (delta, logits, spatial, target), allow_unused=True, retain_graph=True)
    error = output.detach().numpy().astype(np.float64) - target.detach().numpy().astype(np.float64)
    z = (error[0] + error[1]) / (2 * 16 / 65535)
    g = z / np.sqrt(1 + z * z) / (2 * 16 / 65535) / z.size
    operator = malvar_matrix(3, 4, colors[:1].numpy(), wb[:1].numpy())
    expected = np.stack([(operator.T @ g.ravel()).reshape(4, 3, 4)] * 2) * aux["support"].detach().numpy()
    np.testing.assert_allclose(grads[0].numpy(), expected, rtol=4e-6, atol=1e-7)
    np.testing.assert_allclose(grads[2].numpy(), np.stack([g, g]), rtol=3e-6, atol=1e-7)
    assert grads[1] is None and grads[3] is None
    # This is an intentional gradient intervention, not an algebraic rewrite
    # that should preserve ordinary support derivatives.
    full_gate = torch.autograd.grad(ordinary, logits)[0]
    assert full_gate.abs().max() > 0


def test_preserves_signed_zero_and_routes_only_correction_derivative():
    value = torch.tensor([-0.0, 0.0, 1e-30, -1e-30, 1.0], requires_grad=True)
    correction = torch.tensor([4.0, -3.0, 1e30, -1e30, 2.0], requires_grad=True)
    result = _UseCorrectionAdjoint.apply(value.detach(), correction)
    assert torch.equal(result.detach().view(torch.int32), value.detach().view(torch.int32))
    result.sum().backward()
    assert value.grad is None and torch.equal(correction.grad, torch.ones_like(correction))


def test_zero_ADC_weight_and_ordinary_losses_keep_original_gate_graph():
    output, aux, colors, wb, delta, logits, spatial = fixture("RGGB")
    result = common_output_with_fixed_support(IdentitySynthesis(), output, aux, colors, wb)
    loss = paired_common_error_loss(result, torch.zeros_like(result), [[0, 1]]) * 0
    zero = torch.autograd.grad(loss, (delta, spatial), retain_graph=True)
    assert all(g.count_nonzero() == 0 for g in zero)
    (output.square().mean()).backward()
    assert logits.grad is not None and logits.grad.abs().max() > 0


def test_does_not_change_rng_or_input_tensors():
    output, aux, colors, wb, *_ = fixture("RGGB")
    before = [v.detach().clone() for v in (output, aux["support"], aux["spatial_correction"])]
    rng = torch.get_rng_state().clone()
    common_output_with_fixed_support(IdentitySynthesis(), output, aux, colors, wb)
    assert torch.equal(rng, torch.get_rng_state())
    assert all(torch.equal(a, b) for a, b in zip(before, (output, aux["support"], aux["spatial_correction"]), strict=True))


@pytest.mark.parametrize("change", ["dtype", "odd", "missing", "support", "spatial", "proposal"])
def test_invalid_auxiliary_contracts(change):
    output, aux, colors, wb, *_ = fixture("RGGB")
    if change == "dtype":
        output = output.double()
    elif change == "odd":
        output = output[..., :-1]
    elif change == "missing":
        del aux["geometry"]
    elif change == "support":
        aux["support"] = aux["support"][:, :, :-1]
    elif change == "spatial":
        aux["spatial_correction"] = aux["spatial_correction"][:, :, :-1]
    else:
        aux["spectral_delta"] = aux["spectral_delta"][:, :3]
    with pytest.raises(ValueError):
        common_output_with_fixed_support(IdentitySynthesis(), output, aux, colors, wb)
