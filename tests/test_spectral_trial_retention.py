"""The final trainer save may repeat, while changed retained states must fail."""

import importlib
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from demosaic.train import save_checkpoint


def test_real_checkpoint_double_save_is_idempotent_and_changed_state_is_refused(
    tmp_path, monkeypatch
):
    monkeypatch.syspath_prepend(str(Path("scripts").resolve()))
    driver = importlib.import_module("train_spectral_trial")
    model = torch.nn.Linear(2, 1)
    model.config = SimpleNamespace(to_dict=lambda: {"fixture": "retention-only"})
    model.restoration_state_dict = model.state_dict
    optimizer = torch.optim.AdamW(model.parameters())
    ema = {k: p.detach().clone() for k, p in model.state_dict().items()}
    checkpoint = tmp_path / "last.pt"
    for _ in range(2):
        save_checkpoint(checkpoint, model, optimizer, ema, 4000, {"steps": 4000}, 2.0)
        retained = driver.retain_checkpoint(checkpoint, 4000)
        assert retained["sha256"] == driver.ref(checkpoint)["sha256"]
    original = (tmp_path / "step-004000.pt").read_bytes()
    with torch.no_grad():
        model.weight.add_(0.01)
    save_checkpoint(checkpoint, model, optimizer, ema, 4000, {"steps": 4000}, 2.0)
    with pytest.raises(ValueError, match="Repeated retained checkpoint differs"):
        driver.retain_checkpoint(checkpoint, 4000)
    assert (tmp_path / "step-004000.pt").read_bytes() == original
