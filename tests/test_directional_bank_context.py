"""Parent preservation, long-range measurement access and bank learning."""

import copy

import pytest
import torch

import demosaic.raw_directional as directional
from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.inference import load_checkpoint
from demosaic.model import JointDemosaic, ModelConfig


def configuration(**kwargs):
    return ModelConfig(
        restoration_backbone="pretrained-rgb",
        width=64,
        camera_conditioning=True,
        variance_stabilization=True,
        physical_anchors=True,
        raw_directional_residual=True,
        **kwargs,
    )


@pytest.mark.parametrize("amp", [False, True])
def test_zero_bank_preserves_trained_parent_values_common_gradients_rng_and_checkpoint(
    tmp_path, amp
):
    torch.manual_seed(91)
    parent = JointDemosaic(configuration())
    with torch.no_grad():
        head = parent.pretrained_rgb.raw_directional
        head.mix_weight.normal_(std=0.02)
        head.mix_bias.normal_(std=0.01)
        head.censored_weight.normal_(std=0.02)
    before = torch.get_rng_state()
    candidate = JointDemosaic(configuration(raw_directional_bank_context=True))
    # Full model construction normally draws RNG; the independent bank does not.
    torch.manual_seed(91)
    ordinary = JointDemosaic(configuration())
    ordinary_rng = torch.get_rng_state()
    torch.manual_seed(91)
    JointDemosaic(configuration(raw_directional_bank_context=True))
    assert torch.equal(ordinary_rng, torch.get_rng_state())
    del ordinary
    torch.set_rng_state(before)
    state = parent.restoration_state_dict()
    incompatible = candidate.load_state_dict(state, strict=False)
    assert len(incompatible.missing_keys) == 6 and not incompatible.unexpected_keys
    assert all(
        k.startswith("pretrained_rgb.raw_directional.bank.") for k in incompatible.missing_keys
    )
    raw = torch.rand(1, 4, 12, 16) * 0.7
    raw[..., :3, :3] = 1
    variance = torch.full_like(raw, 0.001)
    colors = color_indices("GBRG")
    for net in (parent, candidate):
        net.set_noise(torch.tensor([0.001]), torch.tensor([0.00001]))
    with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        a, aa = parent(raw, variance, colors, auxiliary=True)
        b, ba = candidate(raw, variance, colors, auxiliary=True)
    assert torch.equal(a, b) and torch.equal(aa, ba)
    a.square().mean().backward()
    b.square().mean().backward()
    other = dict(candidate.named_parameters())
    for name, p in parent.named_parameters():
        assert torch.equal(p.grad, other[name].grad), name
    bank = candidate.pretrained_rgb.raw_directional.bank
    assert bank[-1].weight.grad.count_nonzero() and bank[-1].bias.grad.count_nonzero()
    path = tmp_path / "bank.pt"
    torch.save(
        {"model_config": candidate.config.to_dict(), "model": candidate.restoration_state_dict()},
        path,
    )
    loaded, _ = load_checkpoint(path)
    loaded.set_noise(torch.tensor([0.001]), torch.tensor([0.00001]))
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
        assert torch.equal(loaded(raw, variance, colors), b)


def test_bank_sees_distant_raw_evidence_and_reuses_each_candidate_once(monkeypatch):
    head = directional.RawDirectionalResidual(bank_context=True)
    base, features = torch.zeros(1, 3, 48, 48), torch.zeros(1, 67, 48, 48)
    raw = torch.zeros(1, 4, 24, 24)
    variance = torch.full_like(raw, 0.01)
    colors = color_indices("RGGB")
    inputs = []
    head.bank.register_forward_pre_hook(lambda _, args: inputs.append(args[0].detach().clone()))
    original, calls = directional.line_mean, []

    def count(value, direction, window=33):
        calls.append(direction)
        return original(value, direction, window)

    monkeypatch.setattr(directional, "line_mean", count)
    head(base, raw, variance, colors, features)
    changed = raw.clone()
    changed[..., 2, 12] = 0.33
    head(base, changed, variance, colors, features)
    assert calls == list(directional.DIRECTIONS) * 2
    assert torch.equal(raw[..., 10:15, 10:15], changed[..., 10:15, 10:15])
    assert inputs[0][0, 8, 12, 12] == 0
    assert inputs[1][0, 8, 12, 12] > 0.09  # 33-point vertical mean, outside local5x5.


@pytest.mark.parametrize("pattern", PATTERNS)
def test_arbitrary_learned_bank_preserves_uncensored_constant_measurements(pattern):
    head = directional.RawDirectionalResidual(bank_context=True)
    with torch.no_grad():
        for parameter in head.parameters():
            parameter.normal_(std=0.2)
    base = torch.tensor([-0.03, 0.00001, 0.7])[None, :, None, None].expand(1, 3, 18, 22)
    colors = color_indices(pattern)
    raw = mosaic(base, colors)
    result = head(base, raw, torch.full_like(raw, 0.001), colors, torch.randn(1, 67, 18, 22))
    torch.testing.assert_close(result, base, rtol=0, atol=3e-7)


def test_bank_learns_after_the_zero_head_opens_and_input_tensors_stay_unchanged():
    head = directional.RawDirectionalResidual(bank_context=True)
    values = [
        torch.rand(1, 3, 24, 24),
        torch.rand(1, 4, 12, 12),
        torch.full((1, 4, 12, 12), 0.001),
        color_indices("RGGB"),
        torch.randn(1, 67, 24, 24),
    ]
    copies = copy.deepcopy(values)
    optimizer = torch.optim.AdamW(head.parameters(), lr=0.001)
    for step in range(3):
        optimizer.zero_grad(set_to_none=True)
        result = head(*values)
        result.square().mean().backward()
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in head.parameters())
        if step:
            assert head.bank[0].weight.grad.count_nonzero()
        optimizer.step()
    assert all(torch.equal(a, b) for a, b in zip(values, copies, strict=True))


@pytest.mark.parametrize("amp", [False, True])
def test_detached_bank_matches_hook_gradients_and_preserves_values_and_head_learning(amp):
    torch.manual_seed(27)
    connected = directional.RawDirectionalResidual(bank_context=True)
    with torch.no_grad():
        for parameter in connected.parameters():
            parameter.normal_(std=0.04)
    detached, hook_model = copy.deepcopy(connected), copy.deepcopy(connected)
    detached.bank_detach_input = True
    handle = hook_model.bank.register_forward_pre_hook(lambda _, args: (args[0].detach(),))
    original = [
        torch.rand(1, 3, 24, 32) * 0.1,
        torch.rand(1, 4, 12, 16) * 0.1,
        torch.full((1, 4, 12, 16), 0.001),
        color_indices("GRBG"),
        torch.randn(1, 67, 24, 32),
    ]
    results = []
    for model in (connected, detached, hook_model):
        values = [v.clone() for v in original]
        values[0].requires_grad_()
        values[4].requires_grad_()
        with torch.autocast("cpu", dtype=torch.bfloat16, enabled=amp):
            prediction = model(*values)
            loss = (prediction - 0.06).square().mean()
        loss.backward()
        results.append((prediction.detach(), values[0].grad, values[4].grad))
    handle.remove()
    assert torch.equal(results[0][0], results[1][0])
    assert torch.equal(results[1][0], results[2][0])
    assert not torch.equal(results[0][1], results[1][1])
    assert torch.equal(results[1][1], results[2][1])
    assert all(torch.equal(results[0][2], r[2]) for r in results[1:])
    for name, parameter in connected.named_parameters():
        for model in (detached, hook_model):
            other = dict(model.named_parameters())[name]
            assert torch.equal(parameter.grad, other.grad), name
    assert detached.bank[-1].weight.grad.count_nonzero()
    assert detached.bank[0].weight.grad.count_nonzero()


def test_detached_bank_configuration_roundtrip_and_legacy_default(tmp_path):
    options = configuration(
        raw_directional_bank_context=True, raw_directional_bank_detach_input=True
    )
    model = JointDemosaic(options)
    assert model.pretrained_rgb.raw_directional.bank_detach_input
    path = tmp_path / "detached.pt"
    torch.save({"model_config": options.to_dict(), "model": model.restoration_state_dict()}, path)
    restored, _ = load_checkpoint(path)
    assert restored.config == options and restored.pretrained_rgb.raw_directional.bank_detach_input
    old = options.to_dict()
    old.pop("raw_directional_bank_detach_input")
    assert ModelConfig.from_checkpoint(old).raw_directional_bank_detach_input is False
    connected = JointDemosaic(ModelConfig.from_checkpoint(old))
    assert not connected.pretrained_rgb.raw_directional.bank_detach_input
    assert model.restoration_state_dict().keys() == connected.restoration_state_dict().keys()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"raw_directional_residual": False, "raw_directional_bank_context": True},
        {"raw_directional_bank_context": 1},
        {"raw_directional_bank_detach_input": True},
        {"raw_directional_bank_context": True, "raw_directional_bank_detach_input": 1},
    ],
)
def test_invalid_bank_configuration_is_rejected(kwargs):
    options = configuration().to_dict()
    options.update(kwargs)
    with pytest.raises(ValueError, match="directional bank"):
        JointDemosaic(ModelConfig(**options))


@pytest.mark.parametrize(
    "options", [{"bank_detach_input": True}, {"bank_context": True, "bank_detach_input": 1}]
)
def test_invalid_direct_bank_detachment_is_rejected(options):
    with pytest.raises(ValueError, match="bank input detachment"):
        directional.RawDirectionalResidual(**options)
