"""Paired variants must share the expensive forward and keep GT out of fitting."""

import importlib.util
from pathlib import Path

import torch


def test_one_real_forward_input_only_correction_and_unchanged_original(monkeypatch):
    monkeypatch.syspath_prepend(str(Path("scripts").absolute()))
    spec = importlib.util.spec_from_file_location(
        "parent_gain", Path("scripts/evaluate_parent_cfa_gain.py")
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    class Batch(dict):
        def __getitem__(self, key):
            assert key != "target", "Paired forward/correction cannot inspect GT"
            return super().__getitem__(key)

    class CountedModel:
        def __init__(self):
            self.calls = 0
            self.noise = []
            self.output = torch.ones((2, 3, 8, 8))

        def set_noise(self, shot, read):
            self.noise.append((shot, read))

        def __call__(self, *inputs):
            self.calls += 1
            assert len(inputs) == 5
            return self.output

    batch = Batch(
        packed=torch.full((2, 4, 4, 4), 0.5),
        variance=torch.ones((2, 4, 4, 4)),
        colors=torch.tensor([[0, 1, 1, 2], [2, 1, 1, 0]]),
        wb=torch.ones((2, 3)),
        matrix=torch.eye(3).expand(2, -1, -1),
        target=object(),
    )
    model = CountedModel()
    original, corrected, gains = module.paired_predictions(
        model, batch, {"shot": 0.00256, "read": 0.0000262144}
    )
    assert model.calls == 1 and model.noise == [(0.00256, 0.0000262144)]
    assert original is model.output and torch.equal(original, torch.ones_like(original))
    assert torch.equal(corrected, torch.full_like(original, 0.5))
    assert torch.equal(gains, torch.full((2, 3), 0.5, dtype=torch.float64))
