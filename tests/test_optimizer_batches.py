import hashlib
import importlib.util
import json
from functools import partial
from pathlib import Path

import numpy as np
import pytest
import torch
import yaml
from test_paired_training import make_manifest
from test_raw_batch_learning import fixture as physical_fixture
from test_raw_batch_learning import prototype as reference

import demosaic.train as training
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.optimizer_batches import backward_groups, batch_layout, optimizer_batches


def options(forward=1):
    return {
        "optimizer_batch_groups": 4,
        "optimizer_forward_groups": forward,
        "data_seed_per_step": True,
        "amp": False,
        "precision": "float32",
        "model": {"restoration_backbone": "packed-isotropic"},
    }


@pytest.mark.parametrize("forward", [1, 2, 4])
def test_grouped_backward_matches_joined_mixed_loss_and_clips_once(forward):
    model, batches = physical_fixture()
    domains = ["paired", "native", "commons", "paired"]
    before = {name: value.clone() for name, value in model.state_dict().items()}
    expected = reference().grouped_loss(model, batches, domains)
    expected.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
    gradients = {name: p.grad.clone() for name, p in model.named_parameters()}
    model.zero_grad(set_to_none=True)
    selected = [
        (index + 1, domain, batch)
        for index, (domain, batch) in enumerate(zip(domains, batches, strict=True))
    ]
    actual, _, actual_norm, records = backward_groups(
        model,
        selected,
        lambda step, domain, batch: batch,
        options(forward),
        fingerprint=training.batch_fingerprint,
    )
    torch.testing.assert_close(actual, expected, rtol=1e-6, atol=1e-7)
    torch.testing.assert_close(actual_norm, norm, rtol=1e-5, atol=1e-6)
    for name, p in model.named_parameters():
        torch.testing.assert_close(p.grad, gradients[name], rtol=1e-4, atol=1e-6)
    assert [r["batch_sha256"] for r in records] == [training.batch_fingerprint(b) for b in batches]
    assert all(torch.equal(value, before[name]) for name, value in model.state_dict().items())


def test_clipping_uses_accumulated_gradient_not_individual_groups():
    model, batches = physical_fixture()
    domains = ["native", "commons", "native", "commons"]
    config = {**options(), "normalized_sensor_weight": 20}
    losses = []
    for batch in batches:
        prediction, auxiliary = model(
            *(batch[k] for k in ["packed", "variance", "colors", "wb", "matrix"]), auxiliary=True
        )
        loss, _ = training.reconstruction_loss(
            prediction, batch, auxiliary, normalized_sensor_weight=20
        )
        losses.append(loss)
    torch.stack(losses).mean().backward()
    expected_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
    assert expected_norm > 1
    gradients = [p.grad.clone() for p in model.parameters()]
    model.zero_grad(set_to_none=True)
    selected = [
        (i + 1, domain, batch)
        for i, (domain, batch) in enumerate(zip(domains, batches, strict=True))
    ]
    _, _, norm, _ = backward_groups(model, selected, lambda step, domain, batch: batch, config)
    torch.testing.assert_close(norm, expected_norm, rtol=1e-5, atol=1e-6)
    for actual, expected in zip(model.parameters(), gradients, strict=True):
        torch.testing.assert_close(actual.grad, expected, rtol=1e-4, atol=1e-6)


@pytest.mark.parametrize("forward", [1, 4])
def test_optional_objective_reaches_both_domains_with_matching_accumulated_gradients(forward):
    model, batches = physical_fixture()
    domains = ["paired", "native", "commons", "paired"]
    losses = []
    for domain, batch in zip(domains, batches, strict=True):
        prediction, auxiliary = model(
            *(batch[k] for k in ["packed", "variance", "colors", "wb", "matrix"]), auxiliary=True
        )
        function = (training.paired_reconstruction_loss if domain == "paired"
                    else training.reconstruction_loss)
        value, _ = function(prediction, batch, auxiliary, objective="image-log-mse-v1")
        losses.append(value)
    expected = torch.stack(losses).mean()
    expected.backward()
    norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
    gradients = [p.grad.clone() for p in model.parameters()]
    model.zero_grad(set_to_none=True)
    selected = [(i + 1, d, b) for i, (d, b) in enumerate(zip(domains, batches, strict=True))]
    value, _, actual_norm, _ = backward_groups(
        model, selected, lambda step, domain, batch: batch,
        {**options(forward), "reconstruction_objective": "image-log-mse-v1"},
    )
    torch.testing.assert_close(value, expected)
    torch.testing.assert_close(actual_norm, norm)
    for p, gradient in zip(model.parameters(), gradients, strict=True):
        torch.testing.assert_close(p.grad, gradient, rtol=1e-4, atol=1e-6)


def manifests(tmp_path):
    source = tmp_path / "clean.npy"
    np.save(source, np.random.default_rng(7).integers(0, 65536, (64, 64, 3), dtype=np.uint16))
    commons = tmp_path / "manifest.jsonl"
    commons.write_text(
        "\n".join(
            json.dumps({"id": split, "split": split, "cache": source.name})
            for split in ["train", "val"]
        )
    )
    native = tmp_path / "native.json"
    native.write_text(
        json.dumps(
            {
                "split": "train",
                "rows": [
                    {
                        "split": "train",
                        "scene": "blood_oranges",
                        "color_space": "linear-camera-RGB",
                        "cache": source.name,
                        "cache_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "shape": [64, 64, 3],
                        "raw_metadata": {
                            "white_balance": [1.5, 1, 1.8],
                            "camera_to_srgb": torch.eye(3).tolist(),
                        },
                    }
                ],
            }
        )
    )
    return commons, native, make_manifest(tmp_path)


@pytest.mark.parametrize("forward", [1, 2, 4])
def test_actual_mixed_training_resumes_with_original_source_noise_and_moments(tmp_path, forward):
    commons, native, pairs = manifests(tmp_path)
    recipe = {
        **options(forward),
        "manifest": str(commons),
        "raw_clean_manifest": str(native),
        "paired_manifest": str(pairs),
        "paired_fraction": 0.25,
        "raw_clean_fraction": 0.25,
        "run": str(tmp_path / "full"),
        "device": "cpu",
        "steps": 3,
        "seed": 51,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "raw_clean_workers": 0,
        "paired_workers": 0,
        "cpu_threads": 2,
        "warmup_steps": 1,
        "checkpoint_every": 3,
        "log_every": 1,
        "min_available_gb": 0,
        "val_batches": 1,
        "trace_observations": True,
        "model": {
            "restoration_backbone": "packed-isotropic",
            "camera_conditioning": True,
            "width": 4,
            "isotropic_groups": 1,
            "isotropic_blocks": 1,
            "isotropic_local_width": 4,
            "isotropic_raw_gain": 32,
            "isotropic_residual_scale": 1 / 32,
        },
    }
    path = tmp_path / "recipe.yaml"
    path.write_text(yaml.safe_dump(recipe))
    full = training.train(path)
    recipe["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(recipe))
    partial_path = training.train(path, stop_after=1)
    resumed = training.train(path, resume=partial_path)
    expected, actual = [torch.load(p, weights_only=True) for p in [full, resumed]]
    assert actual["step"] == 3 and actual["data_step"] == 12 and actual["example_draws"] == 12
    for kind in ["model", "ema"]:
        for name, value in expected[kind].items():
            assert torch.equal(value, actual[kind][name])
    for index, state in expected["optimizer"]["state"].items():
        for name, value in state.items():
            assert torch.equal(value, actual["optimizer"]["state"][index][name])
    assert torch.equal(expected["torch_rng"], actual["torch_rng"])
    assert expected["python_rng"] == actual["python_rng"]
    logs = [
        [
            json.loads(line)
            for line in (p.parent / "metrics.jsonl").read_text().splitlines()
            if json.loads(line).get("event") == "train"
        ]
        for p in [full, resumed]
    ]
    observations = [[group for row in log for group in row["source_groups"]] for log in logs]
    assert observations[0] == observations[1] and len(observations[0]) == 12
    assert {row["domain"] for row in observations[0]} == {"commons", "native", "paired"}
    cfg = ModelConfig(**recipe["model"])
    model = JointDemosaic(cfg)
    loaders = {
        "commons": torch.utils.data.DataLoader(
            training.CleanDataset(commons, patch_size=32, seed=51),
            batch_size=1,
            sampler=training.domain_indices("commons", 0, 12, 1, 51, 0.25, 0.25),
        ),
        "native": torch.utils.data.DataLoader(
            training.RawCleanDataset(native, patch_size=32, seed=51),
            batch_size=1,
            sampler=training.domain_indices("native", 0, 12, 1, 51, 0.25, 0.25),
        ),
        "paired": torch.utils.data.DataLoader(
            training.PairedDataset(pairs, patch_size=32, seed=51),
            batch_size=1,
            sampler=training.domain_indices("paired", 0, 12, 1, 51, 0.25, 0.25),
        ),
    }
    prepare = partial(
        training.prepare_training_batch,
        model=model,
        device=torch.device("cpu"),
        config=recipe,
        seed=51,
    )
    for item, record in zip(
        training.selected_batches(loaders, 0, 12, 51, 0.25, 0.25), observations[0], strict=True
    ):
        assert training.batch_fingerprint(prepare(*item)) == record["batch_sha256"]
    for key, value in [
        ("optimizer_forward_groups", 2 if forward != 2 else 1),
        ("batch_size", 2),
        ("ema_decay", 0.99),
    ]:
        changed = {**recipe, key: value}
        path.write_text(yaml.safe_dump(changed))
        with pytest.raises(ValueError, match="Resume"):
            training.train(path, resume=resumed)


def test_group_iterator_checks_boundaries_and_resume_positions():
    values = [(i, "commons", i) for i in range(9, 17)]
    grouped = list(optimizer_batches(values, 4))
    assert [step for step, _ in grouped] == [3, 4]
    assert [item for _, group in grouped for item in group] == values
    for values in [
        [(2, "commons", 0)],
        [(1, "commons", 0)],
        [(1, "commons", 0), (3, "commons", 0)],
    ]:
        with pytest.raises(ValueError):
            list(optimizer_batches(values, 4))


@pytest.mark.parametrize(
    "changes",
    [
        {"optimizer_batch_groups": True},
        {"optimizer_batch_groups": 0},
        {"optimizer_forward_groups": 3},
        {"data_seed_per_step": False},
        {"model": {}},
    ],
)
def test_invalid_layout_rejected(changes):
    with pytest.raises(ValueError):
        batch_layout({**options(), **changes})


def test_legacy_default_update_matches_archived_training_loop(tmp_path):
    archive = Path(
        "/mnt/external/demosaic/benchmarks/packed-isotropic-fresh-coordinate-CPU-v1/work/src/demosaic/train.py"
    )
    if not archive.exists():
        pytest.skip("Local archived loop is an additional integration fixture")
    spec = importlib.util.spec_from_file_location("demosaic._legacy_training_groups_check", archive)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    commons, _, _ = manifests(tmp_path)
    recipe = {
        **options(),
        "optimizer_batch_groups": 1,
        "manifest": str(commons),
        "run": str(tmp_path / "legacy"),
        "device": "cpu",
        "steps": 3,
        "batch_size": 1,
        "patch_size": 32,
        "workers": 0,
        "cpu_threads": 2,
        "amp": False,
        "warmup_steps": 1,
        "checkpoint_every": 3,
        "log_every": 1,
        "val_batches": 1,
        "min_available_gb": 0,
        "trace_observations": True,
        "model": {
            "restoration_backbone": "packed-isotropic",
            "camera_conditioning": True,
            "width": 4,
            "isotropic_groups": 1,
            "isotropic_blocks": 1,
            "isotropic_local_width": 4,
        },
    }
    path = tmp_path / "legacy.yaml"
    path.write_text(yaml.safe_dump(recipe))
    legacy = module.train(path)
    recipe["run"] = str(tmp_path / "current")
    path.write_text(yaml.safe_dump(recipe))
    current = training.train(path)
    old, new = [torch.load(p, weights_only=True) for p in [legacy, current]]
    for key in ["model", "ema"]:
        for name, value in old[key].items():
            assert torch.equal(value, new[key][name])
    for index, state in old["optimizer"]["state"].items():
        for name, value in state.items():
            assert torch.equal(value, new["optimizer"]["state"][index][name])
    assert torch.equal(old["torch_rng"], new["torch_rng"])
