"""Independent pixel-adjoint checks for V159's wider regional-bias transition."""

import numpy as np
import pytest
import torch
from regional_dc_objective import regional_dc_excess
from test_regional_dc_objective import reference


@pytest.mark.parametrize("increment", [1e-5, 0.01])
def test_wide_transition_matches_independent_box_enumeration_and_adjoint(increment):
    rng = np.random.default_rng(15901)
    shape = (2, 3, 17, 23)
    target = rng.uniform(0, 0.02, shape)
    parent = target + rng.normal(0, 0.002, shape)
    output = parent + increment
    scales = np.array([0.003, 0.008]).reshape(2, 1, 1, 1)
    expected, gradient, regrets = reference(output, parent, target, scales, 8, 1.0)
    positive = regrets[regrets > 0]
    assert positive.size and ((positive < 1).all() if increment < 0.001 else (positive > 1).all())
    value = torch.tensor(output, requires_grad=True)
    loss = regional_dc_excess(
        value, *[torch.tensor(v) for v in [parent, target, scales]], window=8, transition=1
    )
    loss.backward()
    assert loss.item() == pytest.approx(expected, rel=1e-7, abs=1e-14)
    np.testing.assert_allclose(value.grad, gradient, rtol=2e-7, atol=1e-10)


@pytest.mark.parametrize("perfect", [False, True])
def test_wide_parent_identity_and_detached_inputs(perfect):
    parent = torch.full((2, 3, 7, 11), 0.02, dtype=torch.float64, requires_grad=True)
    target = (parent.detach().clone() if perfect else torch.zeros_like(parent)).requires_grad_()
    scales = torch.full((2, 1, 1, 1), 16 / 65535, dtype=torch.float64, requires_grad=True)
    value = parent.detach().clone().requires_grad_()
    loss = regional_dc_excess(value, parent, target, scales, transition=1)
    first = torch.autograd.grad(loss, value, create_graph=True)[0]
    second = torch.autograd.grad(first.sum(), value)[0]
    assert loss == 0 and first.count_nonzero() == 0 and torch.isfinite(second).all()
    assert parent.grad is target.grad is scales.grad is None
