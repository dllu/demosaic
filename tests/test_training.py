import json

import numpy as np
import pytest
import torch
import yaml

from demosaic.paired_training import paired_step
from demosaic.raw_clean import raw_clean_step
from demosaic.train import domain_indices, selected_batches, train


@pytest.mark.parametrize("first,last", [(0, 37), (19, 37)])
def test_mixed_training_fetches_only_selected_examples_with_original_global_indices(first, last):
    from torch.utils.data import DataLoader, Dataset

    seed, batch_size = 45, 2
    expected = {}
    for step in range(first + 1, last + 1):
        # Original domain schedule, independent of the new loading helpers.
        expected[step] = (
            "paired"
            if paired_step(step, seed, 0.25)
            else "native"
            if raw_clean_step(step, seed, 0.25, 0.25)
            else "commons"
        )
    calls = {domain: [] for domain in ("commons", "paired", "native")}

    class Guarded(Dataset):
        def __init__(self, domain):
            self.domain = domain

        def __getitem__(self, index):
            assert expected[index // batch_size + 1] == self.domain
            calls[self.domain].append(index)
            return index

    loaders = {
        domain: DataLoader(
            Guarded(domain),
            batch_size=batch_size,
            sampler=domain_indices(domain, first, last, batch_size, seed, 0.25, 0.25),
            num_workers=0,
        )
        for domain in calls
    }
    actual = list(selected_batches(loaders, first, last, seed, 0.25, 0.25))
    assert [step for step, _, _ in actual] == list(expected)
    for step, domain, values in actual:
        assert domain == expected[step]
        assert values.tolist() == list(range((step - 1) * batch_size, step * batch_size))
    assert sum(map(len, calls.values())) == (last - first) * batch_size
    assert all(calls.values())


def test_domain_with_no_selected_steps_never_starts_its_loader():
    class Unused:
        def __iter__(self):
            raise AssertionError("Unused domain must not start workers or augmentation")

    loaders = {"commons": Unused(), "native": Unused(), "paired": ["a", "b"]}
    assert list(selected_batches(loaders, 0, 2, 45, 1.0, 0.0)) == [
        (1, "paired", "a"),
        (2, "paired", "b"),
    ]


@pytest.mark.parametrize(
    "warm_start,legacy_metadata,new_recipe,spawn_workers,weak_recipe",
    [
        (False, False, False, False, False),
        (True, False, False, False, False),
        (True, True, False, False, False),
        (True, False, True, False, False),
        (False, False, True, True, False),
        (False, False, True, True, True),
    ],
)
def test_checkpoint_resume_matches_uninterrupted_training(
    tmp_path, warm_start, legacy_metadata, new_recipe, spawn_workers, weak_recipe
):
    """RNG, augmentation, draw position, optimizer, LR and EMA survive a restart."""
    source = tmp_path / "clean.npy"
    rng = np.random.default_rng(7)
    side = 80 if weak_recipe else 40
    np.save(source, rng.integers(0, 65536, (side, side, 3), dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            json.dumps(
                {
                    "id": split,
                    "cache": source.name,
                    "split": split,
                    **({"bin_factor": 4} if weak_recipe else {}),
                }
            )
            for split in ("train", "val")
        )
    )
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "steps": 4,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 4,
        "min_available_gb": 0,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "middle_blocks": 0,
            "decoder_blocks": [1],
            "attention": False,
        },
    }
    if new_recipe:
        config.update(broad_camera=True, normalized_sensor_weight=0.02)
    if spawn_workers:
        config.update(workers=1, worker_start_method="spawn")
    if weak_recipe:
        config.update(augmentation_downsample=2, synthetic_fraction=1, weak_texture_fraction=1)
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    initialize = None
    if warm_start:
        initialize = train(path)
        config["run"] = str(tmp_path / "fine-full")
        path.write_text(yaml.safe_dump(config))
    full = train(path, initialize=initialize)
    with pytest.raises(ValueError, match="already has checkpoints"):
        train(path)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    interrupted = train(path, initialize=initialize, stop_after=2)
    assert torch.load(interrupted, weights_only=True)["step"] == 2
    if legacy_metadata:
        state = torch.load(interrupted, weights_only=True)
        del state["config"]["initialized_from"]
        del state["config"]["flat_chroma_stops"]
        torch.save(state, interrupted)
    resumed = train(path, resume=interrupted)
    expected = torch.load(full, weights_only=True)
    actual = torch.load(resumed, weights_only=True)
    assert actual["step"] == 4
    assert actual["config"].get("initialized_from") == expected["config"].get("initialized_from")
    for group in ("model", "ema"):
        for name, value in expected[group].items():
            assert torch.equal(actual[group][name], value), name


def test_explicit_fp32_guards_forward_and_backward_and_refuses_precision_change(
    tmp_path, monkeypatch
):
    import demosaic.train as training

    source = tmp_path / "clean.npy"
    np.save(source, np.full((40, 40, 3), 12000, np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps({"id": s, "cache": source.name, "split": s}) for s in ("train", "val"))
    )
    constructor = training.JointDemosaic
    observed = {"forward": 0, "backward": 0}

    def check(stage):
        assert torch.backends.cudnn.conv.fp32_precision == "ieee"
        assert torch.backends.cuda.matmul.fp32_precision == "ieee"
        observed[stage] += 1

    def instrument(config):
        model = constructor(config)
        model.register_forward_pre_hook(lambda *args: check("forward"))
        model.register_full_backward_pre_hook(lambda *args: check("backward"))
        return model

    monkeypatch.setattr(training, "JointDemosaic", instrument)
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "run"),
        "device": "cpu",
        "steps": 2,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": True,
        "precision": "float32",
        "checkpoint_every": 2,
        "min_available_gb": 0,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "decoder_blocks": [1],
            "middle_blocks": 1,
            "attention": False,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    previous = (torch.backends.cudnn.conv.fp32_precision, torch.backends.cuda.matmul.fp32_precision)
    try:
        torch.backends.cudnn.conv.fp32_precision = "tf32"
        torch.backends.cuda.matmul.fp32_precision = "tf32"
        checkpoint = train(path)
        assert observed["forward"] >= 3 and observed["backward"] == 2
        assert torch.backends.cudnn.conv.fp32_precision == "tf32"
        assert torch.backends.cuda.matmul.fp32_precision == "tf32"
        config["precision"] = "bfloat16"
        path.write_text(yaml.safe_dump(config))
        with pytest.raises(ValueError, match="training precision differs"):
            train(path, resume=checkpoint)
    finally:
        torch.backends.cudnn.conv.fp32_precision, torch.backends.cuda.matmul.fp32_precision = (
            previous
        )


def test_pre_downsample_training_keeps_frozen_validation_and_resume_recipe(tmp_path):
    import hashlib

    train_cache = tmp_path / "train4.npy"
    np.save(train_cache, np.full((80, 80, 3), 12000, np.uint16))
    val_cache = tmp_path / "val8.npy"
    np.save(val_cache, np.full((40, 40, 3), 16000, np.uint16))
    manifests = {}
    for split, cache, factor in [("train", train_cache, 4), ("val", val_cache, 8)]:
        path = tmp_path / f"{split}.jsonl"
        path.write_text(
            json.dumps({"id": split, "cache": cache.name, "split": split, "bin_factor": factor})
            + "\n"
        )
        manifests[split] = path
    config = {
        "manifest": str(manifests["train"]),
        "validation_manifest": str(manifests["val"]),
        "augmentation_downsample": 2,
        "run": str(tmp_path / "run"),
        "device": "cpu",
        "steps": 2,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": 2,
        "min_available_gb": 0,
        "model": {
            "width": 4,
            "encoder_blocks": [1],
            "decoder_blocks": [1],
            "middle_blocks": 0,
            "attention": False,
        },
    }
    path = tmp_path / "recipe.yaml"
    path.write_text(yaml.safe_dump(config))
    checkpoint = train(path, stop_after=1)
    state = torch.load(checkpoint, weights_only=True)
    assert (
        state["config"]["validation_manifest_sha256"]
        == hashlib.sha256(manifests["val"].read_bytes()).hexdigest()
    )
    train(path, resume=checkpoint)
    for key, value, error in [
        ("weak_texture_fraction", 0.1, "weak texture fraction"),
        ("synthetic_fraction", 0.3, "synthetic fraction"),
        ("flat_fraction", 0.1, "flat fraction"),
        ("flat_chroma_stops", 8, "flat chroma stops"),
    ]:
        config[key] = value
        path.write_text(yaml.safe_dump(config))
        with pytest.raises(ValueError, match=error):
            train(path, resume=checkpoint)
        config.pop(key)
    config["augmentation_downsample"] = 1
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="augmentation downsample"):
        train(path, resume=checkpoint)
    config["augmentation_downsample"] = 2
    path.write_text(yaml.safe_dump(config))
    manifests["val"].write_text(manifests["val"].read_text().rstrip("\n") + " \n")
    with pytest.raises(ValueError, match="validation manifest"):
        train(path, resume=checkpoint)
