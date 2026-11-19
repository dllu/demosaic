import random
import sys
from pathlib import Path

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from train_factored_detail import auxiliary_supervision
from train_local_paired_continuation import CORE, PATCH, wire_pair


def test_counterfactual_wire_preserves_the_exterior_and_the_weak_direction():
    photo = torch.full((3, PATCH, PATCH), 0.3)
    strong, double_gap, paired = wire_pair(photo, random.Random(137), pair_axis="strong")
    weak, _, normal = wire_pair(photo, random.Random(137))
    assert paired == normal
    torch.testing.assert_close(strong, weak, rtol=0, atol=1e-7)
    difference = strong - double_gap
    assert difference[:, CORE, CORE].abs().max() > 1e-3
    assert torch.count_nonzero(difference[:, :60]).item() == 0
    assert torch.count_nonzero(difference[:, :, :60]).item() == 0


def test_signed_proposal_loss_stays_active_with_the_gate_closed():
    detail = torch.zeros((6, 1, PATCH, PATCH), requires_grad=True)
    confidence = torch.full_like(detail, -30, requires_grad=True)
    scale = torch.full_like(detail, 0.012)
    size = CORE.stop - CORE.start
    coverage = torch.ones(4, 1, size, size)
    target = torch.full((1, size, size), 0.005)
    losses = auxiliary_supervision(detail, confidence, scale, (coverage, target), teach_phase=True)
    proposal_gradient, gate_gradient = torch.autograd.grad(
        losses["phase"], (detail, confidence), retain_graph=True, allow_unused=True
    )
    assert gate_gradient is None
    assert (proposal_gradient[0:4:2, :, CORE, CORE] < 0).all()
    assert not proposal_gradient[1:4:2].any()

    gate_gradient = torch.autograd.grad(losses["support"], confidence)[0]
    assert (gate_gradient[0:4:2, :, CORE, CORE] < 0).all()
    assert (gate_gradient[1:4:2, :, CORE, CORE] > 0).all()
