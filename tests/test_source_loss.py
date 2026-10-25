import json
import math

import pytest
import torch

from demosaic.losses import reconstruction_loss
from demosaic.source_loss import SourceLossTrace, validate_source_loss_every


@pytest.mark.parametrize("value", [True, -1, 0.5, "1", None])
def test_invalid_trace_interval_rejected(value):
    with pytest.raises(ValueError, match="nonnegative integer"):
        validate_source_loss_every(value)


def test_detached_singleton_diagnostics_have_known_values_and_preserve_gradients(
    tmp_path, monkeypatch
):
    target = torch.stack([torch.full((3, 32, 32), 0.25), torch.ones(3, 32, 32)])
    prediction = target.clone()
    prediction[1] = torch.tensor([0.3, 0.6, 0.9])[:, None, None]
    prediction.requires_grad_()
    batch = {
        "target": target,
        "wb": torch.ones(2, 3),
        "matrix": torch.eye(3).repeat(2, 1, 1),
        "colors": torch.tensor([[0, 1, 1, 2]]).repeat(2, 1),
        "shot": torch.tensor([0, 0.001]).reshape(2, 1, 1, 1),
        "read": torch.tensor([0, 1e-6]).reshape(2, 1, 1, 1),
    }
    clean = {"rgb": target, "source": [json.dumps({"source_id": name}) for name in ("a", "b")]}
    baseline, _ = reconstruction_loss(prediction, batch)
    expected_gradient = torch.autograd.grad(baseline, prediction)[0]
    baseline_value = float(baseline.detach())
    before_rng = torch.get_rng_state().clone()

    def forbid(*args, **kwargs):
        raise AssertionError("Diagnostics must not call a neural module")

    monkeypatch.setattr(torch.nn.Module, "_call_impl", forbid)
    path = tmp_path / "trace.jsonl"
    tracer = SourceLossTrace(path, {})
    with torch.autocast("cpu", dtype=torch.bfloat16):
        tracer(7, "commons", clean, prediction, None, batch, step=2)
        assert torch.is_autocast_enabled("cpu")
    assert prediction.grad is None and torch.equal(torch.get_rng_state(), before_rng)
    loss, _ = reconstruction_loss(prediction, batch)
    loss.backward()
    assert torch.equal(prediction.grad, expected_gradient)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["source"]["source_id"] for r in rows] == ["a", "b"]
    assert all(r["step"] == 2 and r["data_step"] == 7 for r in rows)
    assert rows[0]["singleton_loss_fp32"] == pytest.approx(0.0016, abs=1e-8)
    # Closed-form constant RGB: gradient differences are zero and only the
    # second image has a saturated-reference highlight mask.
    rgb = [0.3, 0.6, 0.9]
    displayed = [1.055 * x ** (1 / 2.4) - 0.055 for x in rgb]
    linear = sum(math.sqrt((x - 1) ** 2 + 1e-6) for x in rgb) / 3
    rendered = sum(math.sqrt((x - 1) ** 2 + 1e-6) for x in displayed) / 3
    chroma = sum(abs(x - sum(displayed) / 3) for x in displayed) / 3
    expected = linear + 0.5 * rendered + 0.1 * 0.001 + 0.1 * chroma
    assert rows[1]["singleton_loss_fp32"] == pytest.approx(expected, abs=2e-7)
    assert abs(sum(r["singleton_loss_fp32"] for r in rows) / 2 - baseline_value) > 0.001
    tracer(8, "paired", {}, prediction, None, {}, step=2)
    tracer(9, "native", {}, prediction, None, {}, step=2)
    assert len(path.read_text().splitlines()) == 2
