"""Preserve real augmented draws, exclusions, ROI overrides and resume provenance."""

import copy
import hashlib
import json
import random
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch
import yaml

from demosaic.data import CleanDataset
from demosaic.photo_sampling import PhotoSamplingReference, require_resume_photo_sampling
from demosaic.train import train


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_manifest(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


@pytest.fixture
def corpus(tmp_path):
    rows = []
    for index, identity in enumerate(("a", "b", "c", "d", "validation")):
        values = np.random.default_rng(index).integers(1000, 62000, (128, 160, 3), dtype=np.uint16)
        cache = tmp_path / (identity + ".npy")
        np.save(cache, values)
        rows.append(
            {
                "id": identity,
                "split": "val" if index == 4 else "train",
                "cache": cache.name,
                "cache_sha256": digest(cache),
                "shape": list(values.shape),
                "bin_factor": 4,
            }
        )
    reference, active = (tmp_path / name for name in ("reference.jsonl", "active.jsonl"))
    write_manifest(reference, rows)
    write_manifest(active, [row for row in rows if row["id"] not in {"b", "d"}])
    return reference, active, rows


def options():
    return {
        "patch_size": 32,
        "seed": 64,
        "augmentation_downsample": 2,
        "synthetic_fraction": 0.2,
        "flat_fraction": 0.1,
        "weak_texture_fraction": 0.1,
        "optical_blur_probability": 0.25,
        "photographic_low_contrast_fraction": 0.25,
    }


def test_real_augmented_reader_preserves_survivors_and_never_loads_excluded_sources(
    corpus, monkeypatch
):
    reference, active, rows = corpus
    original = CleanDataset(reference, **options())
    candidate = CleanDataset(active, **options(), photo_sampling_reference_manifest=reference)
    allowed = {
        str((active.parent / row["cache"]).absolute()) for row in rows if row["id"] in {"a", "c"}
    }
    load, draws = np.load, []
    current = None

    def observe(path, *args, **kwargs):
        if current == "candidate":
            assert str(Path(path).absolute()) in allowed
        draws.append(str(Path(path).absolute()))
        return load(path, *args, **kwargs)

    monkeypatch.setattr("demosaic.data.np.load", observe)
    before_python, before_torch = random.getstate(), torch.get_rng_state().clone()
    same, replacements, procedural = 0, 0, 0
    for index in range(100):
        current = "original"
        draws.clear()
        first = original[index]["rgb"]
        original_paths = list(draws)
        current = "candidate"
        draws.clear()
        second = candidate[index]["rgb"]
        if not original_paths:
            procedural += 1
            assert not draws and torch.equal(first, second)
        elif original_paths[0] in allowed:
            same += 1
            assert draws == original_paths and torch.equal(first, second)
        else:
            replacements += 1
            assert len(draws) == 1 and draws != original_paths
            assert torch.isfinite(second).all()
    assert same > 20 and replacements > 20 and procedural > 20
    assert random.getstate() == before_python and torch.equal(torch.get_rng_state(), before_torch)


def test_no_removed_sources_is_exact_for_all_procedural_and_photographic_draws(corpus):
    reference, _, _ = corpus
    first = CleanDataset(reference, **options())
    second = CleanDataset(reference, **options(), photo_sampling_reference_manifest=reference)
    for index in range(64):
        assert torch.equal(first[index]["rgb"], second[index]["rgb"])


def test_roi_override_does_not_retry_a_nominal_excluded_source_or_change_geometry(
    corpus, monkeypatch
):
    reference, active, rows = corpus
    controls = {
        "patch_size": 32,
        "synthetic_fraction": 0,
        "augmentation_downsample": 2,
        "seed": 64,
        "optical_blur_probability": 0.25,
    }
    first = CleanDataset(reference, **controls)
    second = CleanDataset(active, **controls, photo_sampling_reference_manifest=reference)
    region = SimpleNamespace(record=rows[0], xywh=(16, 16, 96, 96))
    monkeypatch.setattr(first, "reviewed_roi_for_index", lambda _index: region)
    monkeypatch.setattr(second, "reviewed_roi_for_index", lambda _index: region)
    retries = []

    def forbidden_retry(*args):
        retries.append(args)
        raise AssertionError("ROI override must precede exclusion retries")

    monkeypatch.setattr(second.photo_sampling_reference, "eligible", forbidden_retry)
    for index in range(32):
        assert torch.equal(first[index]["rgb"], second[index]["rgb"])
    assert not retries


@pytest.mark.parametrize(
    "damage", ["duplicate", "new-source", "changed-source", "empty", "relative-cache", "hash"]
)
def test_reference_rejects_ambiguous_or_non_subset_inputs(corpus, tmp_path, damage):
    reference, active, rows = corpus
    current = [row for row in rows if row["id"] in {"a", "c"}]
    expected = None
    if damage == "duplicate":
        write_manifest(reference, rows + [rows[0]])
    elif damage == "new-source":
        current = [dict(current[0], id="new")]
    elif damage == "changed-source":
        current = [dict(current[0], cache_sha256="0" * 64)]
    elif damage == "empty":
        current = []
    elif damage == "relative-cache":
        active = tmp_path / "another-parent/active.jsonl"
    else:
        expected = "0" * 64
    with pytest.raises(ValueError, match="sampling|source|reference|subset"):
        PhotoSamplingReference(reference, active, current, expected_sha256=expected)


def test_reference_validation_is_training_only_and_requires_its_manifest(corpus):
    reference, active, _ = corpus
    with pytest.raises(ValueError, match="only for training"):
        CleanDataset(reference, split="val", photo_sampling_reference_manifest=reference)
    with pytest.raises(ValueError, match="requires a manifest"):
        CleanDataset(active, photo_sampling_reference_sha256="0" * 64)
    require_resume_photo_sampling({}, {})
    for before, after in [
        ({}, {"photo_sampling_reference_sha256": "a"}),
        ({"photo_sampling_reference_sha256": "a"}, {}),
        ({"photo_sampling_reference_sha256": "a"}, {"photo_sampling_reference_sha256": "b"}),
    ]:
        with pytest.raises(ValueError, match="Resume photo sampling reference"):
            require_resume_photo_sampling(before, after)


def equal_state(first, second):
    if isinstance(first, torch.Tensor):
        assert torch.equal(first, second)
    elif isinstance(first, dict):
        assert first.keys() == second.keys()
        for key in first:
            equal_state(first[key], second[key])
    elif isinstance(first, (tuple, list)):
        assert len(first) == len(second)
        for left, right in zip(first, second, strict=True):
            equal_state(left, right)
    else:
        assert first == second


def test_actual_training_snapshots_reference_and_resumes_identically(corpus, tmp_path):
    reference, active, _ = corpus
    config = {
        "manifest": str(active),
        "photo_sampling_reference_manifest": str(reference),
        "run": str(tmp_path / "full"),
        "synthetic_fraction": 0,
        "augmentation_downsample": 2,
        "optical_blur_probability": 0,
        "device": "cpu",
        "steps": 4,
        "batch_size": 1,
        "patch_size": 32,
        "seed": 64,
        "workers": 0,
        "cpu_threads": 1,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 4,
        "val_batches": 1,
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
    full = train(path)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    partial = train(path, stop_after=2)
    resumed = train(path, resume=partial)
    first, second = [torch.load(p, map_location="cpu", weights_only=True) for p in (full, resumed)]
    for field in (
        "model",
        "ema",
        "optimizer",
        "torch_rng",
        "python_rng",
        "cuda_rng",
        "best",
        "step",
    ):
        equal_state(first[field], second[field])
    for state in (first, second):
        assert state["config"]["photo_sampling_reference_sha256"] == digest(reference)
        assert (
            Path(state["config"]["source_snapshot"]) / "photo-sampling-reference.jsonl"
        ).read_bytes() == reference.read_bytes()
    changed = copy.deepcopy(config)
    changed.pop("photo_sampling_reference_manifest")
    path.write_text(yaml.safe_dump(changed))
    with pytest.raises(ValueError, match="Resume photo sampling reference"):
        train(path, resume=resumed)
    reference.write_text(reference.read_text() + "\n")
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="Resume photo sampling reference"):
        train(path, resume=resumed)
