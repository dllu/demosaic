"""Reused frozen features must preserve values, inputs, state and failure cleanup."""

from types import SimpleNamespace

import pytest
import torch
from torch import nn

from demosaic.frozen_encoder_replay import FrozenDinoReplay


class Encoder(nn.Module):
    def __init__(self, value=2.0):
        super().__init__()
        self.weight = nn.Parameter(torch.tensor(value), requires_grad=False)
        self.config = SimpleNamespace(model_type="dinov3_convnext")
        self.calls = 0
        self.eval()

    def forward(self, *, pixel_values, output_hidden_states):
        self.calls += 1
        return SimpleNamespace(hidden_states=(pixel_values * self.weight,))


def test_identical_values_with_one_execution_and_restored_forward():
    encoders = [Encoder() for _ in range(3)]
    replay = FrozenDinoReplay(encoders)
    x = torch.arange(12).reshape(1, 3, 2, 2).float()
    with torch.inference_mode(), replay.group() as statistics:
        values = [m(pixel_values=x, output_hidden_states=True).hidden_states[0] for m in encoders]
    assert statistics == {"requests": 3, "executions": 1, "replays": 2}
    assert [m.calls for m in encoders] == [1, 0, 0]
    for value in values:
        torch.testing.assert_close(value, x * 2, atol=0, rtol=0)
    encoders[1](pixel_values=x, output_hidden_states=True)
    assert encoders[1].calls == 1


def test_changed_input_rejected_before_replay_and_cleanup_allows_fresh_group():
    first, second = Encoder(), Encoder()
    replay = FrozenDinoReplay([first, second])
    x = torch.ones(1, 3, 2, 2)
    with pytest.raises(ValueError, match="inputs differ"), torch.inference_mode(), replay.group():
        first(pixel_values=x, output_hidden_states=True)
        second(pixel_values=x + 1, output_hidden_states=True)
    assert second.calls == 0
    with torch.inference_mode(), replay.group():
        value = second(pixel_values=x + 1, output_hidden_states=True).hidden_states[0]
    torch.testing.assert_close(value, (x + 1) * 2, atol=0, rtol=0)


def test_reject_different_weights_and_trainable_backbone():
    with pytest.raises(ValueError, match="state tensors differ"):
        FrozenDinoReplay([Encoder(), Encoder(3)])
    first, second = Encoder(), Encoder()
    second.train()
    with pytest.raises(ValueError, match="evaluation mode"):
        FrozenDinoReplay([first, second])


def test_changed_returned_features_detected_and_forward_restored():
    first, second = Encoder(), Encoder()
    replay = FrozenDinoReplay([first, second])
    x = torch.ones(1, 3, 2, 2)
    with (
        pytest.raises(ValueError, match="consumer modified"),
        torch.inference_mode(),
        replay.group(),
    ):
        out = first(pixel_values=x, output_hidden_states=True)
        out.hidden_states[0].zero_()
    assert not replay.active
    value = second(pixel_values=x, output_hidden_states=True).hidden_states[0]
    torch.testing.assert_close(value, x * 2, atol=0, rtol=0)


def test_same_weights_with_different_configuration_rejected():
    first, second = Encoder(), Encoder()
    first.config.activation = "gelu"
    second.config.activation = "relu"
    with pytest.raises(ValueError, match="configurations differ"):
        FrozenDinoReplay([first, second])
