import copy

import pytest
import torch
from lossless_native import ref
from phase_wave_training_state import fresh_state, inherited_hash, update_ema
from spatial_wave_training_state import expand_checkpoint, pack_checkpoint, restore_factored

from demosaic.late_spatial_context_wave import LateSpatialContextWaveDetail


def example(tmp_path):
    model = LateSpatialContextWaveDetail()
    state = model.state_dict()
    p = tmp_path / "V183-EMA.pt"
    torch.save(
        {"state_dict": {n: v for n, v in state.items() if not n.startswith("wave_readout.")}}, p
    )
    optimizer, ema = fresh_state(model, lr=0.001, weight_decay=0.01)
    loss = sum(p.square().sum() for p in model.wave_readout.parameters())
    loss.backward()
    optimizer.step()
    update_ema(model, ema, updates=1)
    payload = {
        "models": model.state_dict(),
        "ema": ema,
        "optimizer": optimizer.state_dict(),
        "updates": 1,
        "inherited_hash": inherited_hash(model),
        "CPU_RNG": torch.get_rng_state(),
        "CUDA_RNG": None,
    }
    return model, optimizer, payload, ref(p)


def test_factored_checkpoint_full_state_and_restore_exact(tmp_path):
    model, optimizer, payload, initializer = example(tmp_path)
    packed = pack_checkpoint(payload, initializer)
    assert "models" not in packed and len(packed["head"]) == 4
    expanded = expand_checkpoint(packed)
    assert len(expanded["models"]) == 193
    assert all(torch.equal(v, expanded["models"][n]) for n, v in payload["models"].items())
    replacement = LateSpatialContextWaveDetail()
    restored, ema = restore_factored(replacement, packed, lr=0.001, weight_decay=0.01)
    assert all(torch.equal(v, replacement.state_dict()[n]) for n, v in model.state_dict().items())
    assert all(torch.equal(v, ema[n]) for n, v in payload["ema"].items())
    for old, new in zip(optimizer.state.values(), restored.state.values(), strict=True):
        assert all(torch.equal(v, new[n]) for n, v in old.items())


@pytest.mark.parametrize("change", ["frozen", "raw-name", "ema-name", "source-bytes"])
def test_invalid_factoring_rejected(tmp_path, change):
    _model, _optimizer, payload, initializer = example(tmp_path)
    if change == "frozen":
        payload["models"] = copy.deepcopy(payload["models"])
        name = next(n for n in payload["models"] if not n.startswith("wave_readout."))
        payload["models"][name].flatten()[0] += 1
        with pytest.raises(ValueError):
            pack_checkpoint(payload, initializer)
    elif change == "source-bytes":
        packed = pack_checkpoint(payload, initializer)
        with open(initializer["path"], "ab") as stream:
            stream.write(b"x")
        with pytest.raises(ValueError):
            expand_checkpoint(packed)
    else:
        packed = pack_checkpoint(payload, initializer)
        packed["head" if change == "raw-name" else "ema"].pop("wave_readout.context.bias")
        with pytest.raises(ValueError):
            expand_checkpoint(packed)
