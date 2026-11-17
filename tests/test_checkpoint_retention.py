"""A retained best checkpoint must survive later atomic last-state replacement."""

import torch

from demosaic.train import checkpoint_cpu_snapshot, retain_checkpoint


def test_snapshot_owns_nested_tensor_storage_without_changing_rng():
    original = torch.arange(12.0).reshape(3, 4).t().requires_grad_()
    rng = torch.get_rng_state().clone()
    state = {
        "model": {"weight": original},
        "optimizer": [{"step": torch.tensor(6.0)}],
        "rng": (rng, 70, None),
    }
    snapshot = checkpoint_cpu_snapshot(state)
    assert isinstance(snapshot["optimizer"], list) and isinstance(snapshot["rng"], tuple)
    assert snapshot["model"]["weight"].device.type == "cpu"
    assert not snapshot["model"]["weight"].requires_grad
    torch.testing.assert_close(snapshot["model"]["weight"], original, rtol=0, atol=0)
    with torch.no_grad():
        original.add_(100)
        state["optimizer"][0]["step"].add_(1)
    assert snapshot["model"]["weight"][0, 0] == 0
    assert snapshot["optimizer"][0]["step"] == 6
    torch.testing.assert_close(torch.get_rng_state(), rng, rtol=0, atol=0)


def test_retained_state_includes_optimizer_rng_and_survives_next_save(tmp_path):
    last, best = tmp_path / "last.pt", tmp_path / "best.pt"
    state = {
        "step": 6000,
        "model": torch.arange(8),
        "ema": torch.arange(8) + 1,
        "optimizer": {"step": 6000, "exp_avg": torch.arange(8).float()},
        "torch_rng": torch.get_rng_state(),
    }
    torch.save(state, last)
    retain_checkpoint(last, best)
    assert best.read_bytes() == last.read_bytes()
    replacement = tmp_path / "last.tmp"
    torch.save({"step": 6001}, replacement)
    replacement.replace(last)
    saved = torch.load(best, weights_only=True)
    assert saved["step"] == saved["optimizer"]["step"] == 6000
    for key in ["model", "ema", "torch_rng"]:
        torch.testing.assert_close(saved[key], state[key], atol=0, rtol=0)
    assert torch.load(last, weights_only=True)["step"] == 6001
    retain_checkpoint(last, best)
    assert torch.load(best, weights_only=True)["step"] == 6001


def test_stale_retention_temporary_does_not_replace_completed_best(tmp_path):
    import pytest

    last, best = tmp_path / "last.pt", tmp_path / "best.pt"
    torch.save({"step": 1}, last)
    retain_checkpoint(last, best)
    previous = best.read_bytes()
    (tmp_path / "best.retain.tmp").write_bytes(b"original unfinished retention")
    with pytest.raises(FileExistsError):
        retain_checkpoint(last, best)
    assert best.read_bytes() == previous
    assert (tmp_path / "best.retain.tmp").read_bytes() == b"original unfinished retention"
