"""Protect source provenance, pre-bin geometry and the exact disabled data stream."""

import copy
import hashlib
import importlib.util
import json
import random
from pathlib import Path

import numpy as np
import pytest
import torch
import yaml

from demosaic.data import CleanDataset
from demosaic.reviewed_rois import require_resume_rois
from demosaic.train import train


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture
def corpus(tmp_path):
    rows = []
    for i, identity in enumerate(("one", "two", "validation")):
        values = np.random.default_rng(i).integers(1000, 62000, (640, 640, 3), dtype=np.uint16)
        cache = tmp_path / (identity + ".npy")
        np.save(cache, values)
        rows.append(
            {
                "id": identity,
                "split": "val" if i == 2 else "train",
                "cache": cache.name,
                "cache_sha256": digest(cache),
                "shape": list(values.shape),
                "dtype": "uint16",
                "bin_factor": 4,
                "color_space": "linear-sRGB",
            }
        )
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text("".join(json.dumps(row) + "\n" for row in rows))
    examples = []
    for row in rows[:2]:
        array = np.load(tmp_path / row["cache"], allow_pickle=False)
        crop = array[64:576, 64:576].copy()
        target = crop.astype(np.float32).reshape(256, 2, 256, 2, 3).mean((1, 3)) / 65535
        examples.append(
            {
                "id": row["id"],
                "source": row,
                "ROI_in_bin4_xywh": [64, 64, 512, 512],
                "actual_bin4_crop_sha256": hashlib.sha256(crop.tobytes()).hexdigest(),
                "native8_target_float32_sha256": hashlib.sha256(target.tobytes()).hexdigest(),
            }
        )
    data = {
        "source_manifest": {"path": str(manifest), "sha256": digest(manifest)},
        "source_split": "train",
        "source_bin_factor": 4,
        "final_area_reduction": 2,
        "effective_bin_factor": 8,
        "target_native_shape": [256, 256, 3],
        "examples": examples,
    }
    catalogue = tmp_path / "rois.json"
    catalogue.write_text(json.dumps(data))
    return manifest, catalogue, data


def dataset(corpus, **kwargs):
    manifest, catalogue, _ = corpus
    options = {
        "patch_size": 32,
        "augmentation_downsample": 2,
        "optical_blur_probability": 0,
        "synthetic_fraction": 0,
        "reviewed_roi_catalogue": catalogue,
        "reviewed_roi_fraction": 1,
    }
    options.update(kwargs)
    return CleanDataset(manifest, **options)


def test_selected_region_is_loaded_before_augmentation_without_loading_replaced_photo(
    corpus, monkeypatch
):
    data = dataset(corpus, patch_size=256)
    selected = data.reviewed_roi_for_index(0)
    expected_path = data.manifest.parent / selected.record["cache"]
    array = np.load(expected_path, allow_pickle=False)
    x, y, w, h = selected.xywh
    raw = array[y : y + h, x : x + w].astype(np.float32)
    calls, captured = [], []
    loader = np.load

    def observed(path, *args, **kwargs):
        calls.append(Path(path))
        return loader(path, *args, **kwargs)

    def area_only(rgb, size, rng, **kwargs):
        captured.append(rgb.clone())
        return torch.nn.functional.avg_pool2d(rgb, 2)

    monkeypatch.setattr("demosaic.data.np.load", observed)
    monkeypatch.setattr("demosaic.data.augment_before_downsample", area_only)
    output = data[0]
    assert calls == [expected_path]
    torch.testing.assert_close(
        captured[0], torch.from_numpy(raw).permute(2, 0, 1) / 65535, rtol=0, atol=0
    )
    expected = raw.reshape(256, 2, 256, 2, 3).mean((1, 3)) / 65535
    torch.testing.assert_close(
        output["rgb"], torch.from_numpy(expected).permute(2, 0, 1), rtol=0, atol=2e-7
    )
    assert output["rgb"].shape == (3, 256, 256) and output["index"] == 0


def test_sparse_roi_selection_leaves_every_untreated_sample_bit_exact(corpus):
    manifest, catalogue, _ = corpus
    options = {
        "patch_size": 32,
        "augmentation_downsample": 2,
        "optical_blur_probability": 0.25,
        "synthetic_fraction": 0.3,
        "flat_fraction": 0.1,
        "weak_texture_fraction": 0.1,
        "photographic_low_contrast_fraction": 0.25,
        "seed": 58,
    }
    control = CleanDataset(manifest, **options)
    candidate = CleanDataset(
        manifest, **options, reviewed_roi_catalogue=catalogue, reviewed_roi_fraction=0.35
    )
    torch_rng, python_rng = torch.get_rng_state(), random.getstate()
    treated = untouched = procedural = 0
    for index in range(120):
        region = candidate.reviewed_roi_for_index(index)
        first, second = control[index], candidate[index]
        assert first.keys() == second.keys() == {"rgb", "index"}
        if region is None:
            assert torch.equal(first["rgb"], second["rgb"])
            untouched += 1
        else:
            assert not torch.equal(first["rgb"], second["rgb"])
            treated += 1
        if random.Random(58 + index).random() < 0.4:
            assert region is None
            procedural += 1
    assert treated > 15 and untouched > 40 and procedural > 20
    assert torch.equal(torch_rng, torch.get_rng_state()) and python_rng == random.getstate()


def test_disabled_path_matches_frozen_v95_dataset_and_ignores_unused_catalogue(corpus):
    manifest, _, _ = corpus
    archived = (
        Path(__file__).resolve().parents[1]
        / ".cache/quality-first-20261020/V95-ADC-matched-training-v1/work/src/demosaic/data.py"
    )
    if not archived.exists():
        pytest.skip("The independent historical data implementation is a local experiment archive")
    spec = importlib.util.spec_from_file_location("demosaic._archived_data_roi_test", archived)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    options = {
        "patch_size": 32,
        "augmentation_downsample": 2,
        "optical_blur_probability": 0.25,
        "synthetic_fraction": 0.3,
        "flat_fraction": 0.1,
        "weak_texture_fraction": 0.1,
        "photographic_low_contrast_fraction": 0.25,
        "seed": 58,
    }
    before = module.CleanDataset(manifest, **options)
    after = CleanDataset(manifest, **options, reviewed_roi_catalogue="not-read-when-disabled.json")
    for index in range(80):
        assert torch.equal(before[index]["rgb"], after[index]["rgb"])
        assert after.reviewed_roi_for_index(index) is None


@pytest.mark.parametrize(
    "damage",
    [
        "manifest",
        "validation",
        "duplicate",
        "empty",
        "odd",
        "negative",
        "float-coordinate",
        "wrong-size",
        "bounds",
        "cache-hash",
        "crop-hash",
        "target-hash",
        "source-dtype",
        "source-metadata",
        "bin-factor",
    ],
)
def test_invalid_source_or_roi_provenance_is_rejected(corpus, damage):
    _, catalogue, original = corpus
    data = copy.deepcopy(original)
    example = data["examples"][0]
    if damage == "manifest":
        data["source_manifest"]["sha256"] = "0" * 64
    elif damage == "validation":
        example["source"]["split"] = "val"
    elif damage == "duplicate":
        data["examples"].append(copy.deepcopy(example))
    elif damage == "empty":
        data["examples"] = []
    elif damage == "odd":
        example["ROI_in_bin4_xywh"][0] = 65
    elif damage == "negative":
        example["ROI_in_bin4_xywh"][0] = -2
    elif damage == "float-coordinate":
        example["ROI_in_bin4_xywh"][0] = 64.0
    elif damage == "wrong-size":
        example["ROI_in_bin4_xywh"][2] = 256
    elif damage == "bounds":
        example["ROI_in_bin4_xywh"][0] = 200
    elif damage == "cache-hash":
        example["source"]["cache_sha256"] = "0" * 64
    elif damage == "crop-hash":
        example["actual_bin4_crop_sha256"] = "0" * 64
    elif damage == "target-hash":
        example["native8_target_float32_sha256"] = "0" * 64
    elif damage == "source-dtype":
        example["source"]["dtype"] = "float32"
    elif damage == "source-metadata":
        example["source"]["cache"] = "other.npy"
    else:
        data["source_bin_factor"] = 8
    catalogue.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        dataset(corpus)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"reviewed_roi_fraction": -0.1},
        {"reviewed_roi_fraction": float("nan")},
        {"reviewed_roi_fraction": True},
        {"split": "val"},
        {"augmentation_downsample": 1},
        {"reviewed_roi_catalogue": None},
        {"patch_size": 272},
        {"reviewed_roi_catalogue_sha256": "0" * 64},
        {"flat_fraction": 1},
    ],
)
def test_invalid_roi_recipe_cannot_sample(corpus, kwargs):
    with pytest.raises((ValueError, TypeError)):
        dataset(corpus, **kwargs)


def equal_state(first, second):
    if isinstance(first, torch.Tensor):
        assert torch.equal(first, second)
    elif isinstance(first, dict):
        assert first.keys() == second.keys()
        for key in first:
            equal_state(first[key], second[key])
    elif isinstance(first, (tuple, list)):
        assert len(first) == len(second)
        for a, b in zip(first, second, strict=True):
            equal_state(a, b)
    else:
        assert first == second


def test_actual_cpu_training_snapshots_catalogue_and_resumes_exactly(corpus, tmp_path, monkeypatch):
    manifest, catalogue, _ = corpus
    config = {
        "manifest": str(manifest),
        "run": str(tmp_path / "full"),
        "reviewed_roi_catalogue": str(catalogue),
        "reviewed_roi_fraction": 0.5,
        "synthetic_fraction": 0,
        "augmentation_downsample": 2,
        "optical_blur_probability": 0,
        "device": "cpu",
        "steps": 4,
        "batch_size": 1,
        "patch_size": 32,
        "seed": 58,
        "workers": 0,
        "cpu_threads": 1,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": 4,
        "log_every": 1,
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
        assert state["config"]["reviewed_roi_catalogue_sha256"] == digest(catalogue)
        assert (
            Path(state["config"]["source_snapshot"]) / "reviewed-photo-rois.json"
        ).read_bytes() == catalogue.read_bytes()
    changed = copy.deepcopy(config)
    changed["reviewed_roi_fraction"] = 0
    path.write_text(yaml.safe_dump(changed))
    import demosaic.train as training

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed reviewed data must reject before model construction")

    monkeypatch.setattr(training, "JointDemosaic", forbidden)
    with pytest.raises(ValueError, match="ROI fraction"):
        train(path, resume=resumed)
    changed_catalogue = tmp_path / "changed-catalogue.json"
    payload = json.loads(catalogue.read_text())
    payload["resume_rejection_fixture"] = True
    changed_catalogue.write_text(json.dumps(payload))
    changed = copy.deepcopy(config)
    changed["reviewed_roi_catalogue"] = str(changed_catalogue)
    path.write_text(yaml.safe_dump(changed))
    with pytest.raises(ValueError, match="ROI catalogue"):
        train(path, resume=resumed)
    catalogue.write_text(catalogue.read_text() + "\n")
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="ROI catalogue"):
        train(path, resume=resumed)
    require_resume_rois({}, {"reviewed_roi_fraction": 0})
