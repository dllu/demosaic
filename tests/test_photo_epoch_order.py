"""Check complete epochs, strict bindings and real deterministic clean draws."""

import json
import random
from pathlib import Path

import numpy as np
import pytest
import torch
import yaml
from prepare_photo_epoch_order import prepare

from demosaic.data import CleanDataset
from demosaic.photo_epoch_order import bind_photo_epoch_order, require_resume_photo_epoch_order


@pytest.fixture
def prepared(tmp_path):
    rows = []
    for i in range(9):
        cache = tmp_path / f"{i}.npy"
        np.save(cache, np.random.default_rng(i).integers(1000, 60000, (80, 96, 3), dtype=np.uint16))
        rows.append(
            {
                "id": str(i),
                "cache": str(cache),
                "split": "train" if i < 8 else "val",
                "bin_factor": 4,
            }
        )
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
    config = {
        "manifest": str(manifest),
        "seed": 70,
        "steps": 20,
        "batch_size": 4,
        "patch_size": 32,
        "augmentation_downsample": 2,
        "flat_fraction": 0.1,
        "synthetic_fraction": 0.2,
        "optical_blur_probability": 0,
        "paired_fraction": 0.25,
        "raw_clean_fraction": 0.25,
    }
    recipe = tmp_path / "recipe.yaml"
    recipe.write_text(yaml.safe_dump(config))
    header = prepare(recipe, tmp_path / "order")
    return config, rows, header


def test_epochs_cover_every_train_source_and_preserve_global_rng(prepared):
    config, rows, header = prepared
    state = random.getstate(), torch.get_rng_state().clone(), np.random.get_state()
    order = bind_photo_epoch_order({**config, "photo_epoch_order": str(header)}, rows)
    values = order.values[order.values >= 0]
    assert len(values) > 8
    for start in range(0, len(values) - 7, 8):
        assert sorted(values[start : start + 8].tolist()) == list(range(8))
    assert 8 not in values  # Validation source never enters the order.
    assert random.getstate() == state[0] and torch.equal(torch.get_rng_state(), state[1])
    after = np.random.get_state()
    assert (
        after[0] == state[2][0]
        and np.array_equal(after[1], state[2][1])
        and after[2:] == state[2][2:]
    )


def test_real_reader_random_access_and_procedural_parity(prepared):
    config, rows, header = prepared
    settings = {
        k: config[k]
        for k in [
            "seed",
            "patch_size",
            "augmentation_downsample",
            "flat_fraction",
            "synthetic_fraction",
            "optical_blur_probability",
        ]
    }
    old = CleanDataset(config["manifest"], **settings)
    new = CleanDataset(config["manifest"], **settings, photo_epoch_order=header, trace_sources=True)
    bound = bind_photo_epoch_order({**config, "photo_epoch_order": str(header)}, rows)
    indices = [i for i, value in enumerate(bound.values) if value >= 0]
    for index in reversed(indices[:12]):
        a, b = new[index], new[index]
        assert torch.equal(a["rgb"], b["rgb"])
        assert json.loads(a["source"])["source_id"] == rows[int(bound.values[index])]["id"]
    procedural = [
        i for i in range(len(bound.values)) if random.Random(config["seed"] + i).random() < 0.3
    ]
    for index in procedural[:8]:
        assert torch.equal(old[index]["rgb"], new[index]["rgb"])
    with pytest.raises(ValueError, match="No planned ordinary"):
        bound.ordinary(len(bound.values))
    with pytest.raises(ValueError, match="No planned ordinary"):
        bound.ordinary(next(i for i, v in enumerate(bound.values) if v < 0))


@pytest.mark.parametrize(
    "field,value",
    [
        ("seed", 71),
        ("steps", 21),
        ("batch_size", 8),
        ("paired_fraction", 0.1),
        ("flat_fraction", 0.2),
    ],
)
def test_changed_policy_is_rejected(prepared, field, value):
    config, rows, header = prepared
    with pytest.raises(ValueError, match="epoch order"):
        bind_photo_epoch_order({**config, field: value, "photo_epoch_order": str(header)}, rows)


def test_changed_payload_and_resume_binding_are_rejected(prepared):
    config, rows, header = prepared
    original = {**config, "photo_epoch_order": str(header)}
    bind_photo_epoch_order(original, rows)
    require_resume_photo_epoch_order({}, {})
    require_resume_photo_epoch_order(original, dict(original))
    for previous, current in [
        (original, {}),
        ({}, original),
        (original, {**original, "photo_epoch_order_sha256": "0" * 64}),
    ]:
        with pytest.raises(ValueError, match="Resume photographic epoch"):
            require_resume_photo_epoch_order(previous, current)
    payload = Path(header).parent / json.loads(header.read_text())["order"]["path"]
    values = np.load(payload)
    values[0] = -1 if values[0] >= 0 else 0
    np.save(payload, values)
    with pytest.raises(ValueError, match="payload hash"):
        bind_photo_epoch_order(original, rows)


def test_actual_training_resume_and_snapshot_order(prepared, tmp_path, monkeypatch):
    import demosaic.train as training

    config, _, _ = prepared
    config.update(
        steps=4,
        batch_size=1,
        paired_fraction=0,
        raw_clean_fraction=0,
        device="cpu",
        cpu_threads=1,
        workers=0,
        amp=False,
        min_available_gb=0,
        checkpoint_every=4,
        log_every=4,
        val_batches=1,
        warmup_steps=1,
        model={
            "width": 4,
            "encoder_blocks": [1],
            "decoder_blocks": [1],
            "middle_blocks": 0,
            "attention": False,
        },
    )
    recipe = tmp_path / "training.yaml"
    recipe.write_text(yaml.safe_dump(config))
    header = prepare(recipe, tmp_path / "training-order")
    config["photo_epoch_order"] = str(header)
    config["run"] = str(tmp_path / "full")
    recipe.write_text(yaml.safe_dump(config))
    full_path = training.train(recipe)
    config["run"] = str(tmp_path / "resumed")
    recipe.write_text(yaml.safe_dump(config))
    training.train(recipe, stop_after=2)
    prefix = Path(config["run"]) / "last.pt"
    assert torch.load(prefix, weights_only=True)["step"] == 2
    resumed_path = training.train(recipe, resume=prefix)
    full, resumed = (torch.load(p, weights_only=True) for p in (full_path, resumed_path))
    for key in ["model", "ema"]:
        assert full[key].keys() == resumed[key].keys()
        assert all(torch.equal(full[key][k], resumed[key][k]) for k in full[key])
    snapshot = Path(resumed["config"]["source_snapshot"])
    assert (snapshot / "photo-epoch-order.json").read_bytes() == header.read_bytes()
    name = json.loads(header.read_text())["order"]["path"]
    assert (snapshot / name).read_bytes() == (header.parent / name).read_bytes()

    changed = json.loads(header.read_text())
    changed["audit_note"] = "A changed frozen order must be rejected before construction"
    other = header.with_name("changed-header.json")
    other.write_text(json.dumps(changed))
    config["photo_epoch_order"] = str(other)
    recipe.write_text(yaml.safe_dump(config))

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed order reached model construction")

    monkeypatch.setattr(training, "JointDemosaic", forbidden)
    with pytest.raises(ValueError, match="Resume photographic epoch order"):
        training.train(recipe, resume=resumed_path)
