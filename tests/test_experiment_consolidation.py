"""Cross-boundary parity, immutable artifacts and crash-safe continuation."""

import copy
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from demosaic.cfa import color_indices
from demosaic.experiments.artifacts import freeze_sources, read_json, reference, write_json
from demosaic.experiments.checkpoints import capture_rng, restore_rng
from demosaic.experiments.evaluation.crops import display_pixels, write_triplet
from demosaic.experiments.runtime import exclusive_run
from demosaic.experiments.training import TrainingConfig, train
from demosaic.models.compat import build_component
from demosaic.models.wave import compose_legacy, legacy_state_dict, load_legacy_state_dict
from demosaic.prediction_archive import fingerprint


def assert_tree_equal(first, second):
    if torch.is_tensor(first):
        assert first.dtype == second.dtype and torch.equal(first, second)
    elif isinstance(first, dict):
        assert first.keys() == second.keys()
        for name in first:
            assert_tree_equal(first[name], second[name])
    elif isinstance(first, (list, tuple)):
        assert len(first) == len(second)
        for a, b in zip(first, second, strict=True):
            assert_tree_equal(a, b)
    else:
        assert first == second


class FrozenFixture(nn.Module):
    def forward(self, base, *args):
        return base * 0.9 + 0.001


class NetworkFixture(nn.Module):
    def forward(self, value):
        return value[:, :12] * 0.02


@pytest.mark.parametrize("kind", ["pooled-wave", "cfa-wave", "scale-supported-cfa-wave"])
@pytest.mark.parametrize("pattern", ["RGGB", "BGGR", "GRBG", "GBRG"])
def test_composed_forward_aux_gradients_and_ADC_equal_historical(kind, pattern):
    from demosaic.late_cfa_innovation_wave import LateCFAInnovationWaveDetail
    from demosaic.late_pooled_phase_wave import LatePooledPhaseWaveDetail
    from demosaic.late_scale_supported_cfa_wave import LateScaleSupportedCFAWaveDetail

    torch.set_num_threads(2)
    classes = {
        "pooled-wave": LatePooledPhaseWaveDetail,
        "cfa-wave": LateCFAInnovationWaveDetail,
        "scale-supported-cfa-wave": LateScaleSupportedCFAWaveDetail,
    }
    legacy = classes[kind](
        evidence_window=9, evidence_stride=8, support_windows=(7, 3), support_stride=4
    )
    legacy.frozen, legacy.network = FrozenFixture(), NetworkFixture()
    with torch.no_grad():
        legacy.wave_readout.mixing.bias.fill_(0.13)
        if hasattr(legacy, "cfa_readout"):
            legacy.cfa_readout.gates.bias.fill_(0.17)
            legacy.cfa_readout.gates.weight.fill_(0.02)
            legacy.cfa_readout.context.weight[:, -3:].fill_(0.03)
    composed = compose_legacy(copy.deepcopy(legacy))
    legacy.train()
    composed.train()
    rng = np.random.default_rng(20012)
    raw = torch.tensor(rng.normal(0.02, 0.003, (1, 4, 12, 17)), dtype=torch.float32)
    variance = torch.full_like(raw, 2e-6)
    variance[..., :4, :5] = 0
    base = torch.tensor(rng.normal(0.02, 0.003, (1, 3, 24, 34)), dtype=torch.float32)
    colors = color_indices(pattern)
    expected, old_aux = legacy(base, raw, variance, colors, return_aux=True)
    actual, aux = composed(base, raw, variance, colors, return_aux=True)
    assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))
    assert_tree_equal(aux, old_aux)
    (expected - base).square().mean().backward()
    (actual - base).square().mean().backward()
    old_gradients = [p.grad for p in legacy.parameters() if p.requires_grad]
    new_gradients = [p.grad for p in composed.parameters() if p.requires_grad]
    assert_tree_equal(old_gradients, new_gradients)
    assert all(p.grad is None for p in composed.parameters() if not p.requires_grad)
    expected = legacy(base, raw, variance * 0, colors)
    actual = composed(base, raw, variance * 0, colors)
    assert torch.equal(actual.view(torch.int32), expected.view(torch.int32))


def test_legacy_state_round_trip_and_init_rng():
    before = torch.get_rng_state().clone()
    composed = build_component("scale-supported-cfa-wave")
    assert torch.equal(before, torch.get_rng_state())
    state = legacy_state_dict(composed)
    assert len(state) == 197 and len([p for p in composed.parameters() if p.requires_grad]) == 4
    clone = build_component("scale-supported-cfa-wave")
    load_legacy_state_dict(clone, state)
    assert_tree_equal(composed.state_dict(), clone.state_dict())
    broken = dict(state)
    broken["cfa_readout.gates.bias"] = torch.zeros(4)
    with pytest.raises(ValueError):
        load_legacy_state_dict(clone, broken)
    assert_tree_equal(composed.state_dict(), clone.state_dict())


class ToyHead(nn.Module):
    def __init__(self, _):
        super().__init__()
        self.register_buffer("frozen", torch.ones(1))
        self.readout = nn.Sequential(nn.Conv2d(3, 3, 1), nn.Dropout(0.25))

    def forward(self, base, packed, variance, colors, wb, *, return_aux=False):
        output = base + self.readout(base) * 0.001
        return output, {"frozen_output": base}


def cached_fixture(root):
    root.mkdir()
    rng = np.random.default_rng(52)
    rows, units = [], []
    for step in range(1, 5):
        arrays = {
            "packed": rng.uniform(0.01, 0.03, (2, 4, 16, 16)).astype(np.float32),
            "variance": np.full((2, 4, 16, 16), 0 if step == 3 else 2e-6, dtype=np.float32),
            "colors": np.array([[0, 1, 1, 2]] * 2),
            "wb": np.ones((2, 3), np.float32),
            "target": rng.uniform(0.01, 0.03, (2, 3, 32, 32)).astype(np.float32),
            "pair_indices": np.array([[0, 1]]),
        }
        parent = arrays["target"] + 0.001
        path, parent_path = root / f"{step}.npz", root / f"{step}.npy"
        np.savez(path, **arrays)
        np.save(parent_path, parent)
        rows.append(
            {
                "step": step,
                "arrays": reference(path),
                "parent": reference(parent_path),
                "metadata": {"domain": "mesh"},
                "inputs": {k: fingerprint(v) for k, v in arrays.items()},
                "parent_values": fingerprint(parent),
            }
        )
        units.append({"step": step, "batch": reference(path), "candidate_units_FP32": [0.001]})
    write_json(root / "cache.json", {"batches": rows})
    write_json(root / "units.json", {"rows": units})
    return reference(root / "cache.json"), reference(root / "units.json")


def plan_fixture(root, cache, units):
    root.mkdir()
    recipe = {
        "model": {},
        "cache": cache,
        "pair_units": units,
        "training": TrainingConfig(steps=4, warmup=1).to_dict(),
        "runtime": {"device": "cpu", "minimum_ram_gib": 0, "minimum_disk_gib": 0},
        "domain_weights": {"mesh": 4.0},
    }
    write_json(root / "plan.json", {"recipe": recipe, "inputs": [cache, units], "frozen_files": {}})


def test_real_loop_checkpoint_resume_matches_uninterrupted_Adam_EMA_RNG(tmp_path):
    rng = capture_rng()
    try:
        cache, units = cached_fixture(tmp_path / "data")
        full, split = tmp_path / "full", tmp_path / "split"
        for root in (full, split):
            plan_fixture(root, cache, units)
        train(full, model_factory=ToyHead)
        train(split, stop_after=2, model_factory=ToyHead)
        train(split, resume=True, model_factory=ToyHead)
        first = torch.load(full / "checkpoints/row-000004.pt", weights_only=True)
        second = torch.load(split / "checkpoints/row-000004.pt", weights_only=True)
        first.pop("plan")
        second.pop("plan")
        assert_tree_equal(first, second)
        assert read_json(split / "result.json")["updates"] == 3
        with pytest.raises(ValueError, match="already completed"):
            train(split, resume=True, model_factory=ToyHead)
    finally:
        restore_rng(rng)


def test_progress_failure_adopts_committed_row_without_replaying_inputs(tmp_path, monkeypatch):
    from demosaic.experiments import training
    from demosaic.experiments.data.cache import CachedBatches

    cache, units = cached_fixture(tmp_path / "data")
    root = tmp_path / "run"
    plan_fixture(root, cache, units)
    original_write = training.write_json

    def fail_progress(path, value, **kwargs):
        if Path(path).name == "progress.json":
            raise RuntimeError("reporting fixture")
        return original_write(path, value, **kwargs)

    monkeypatch.setattr(training, "write_json", fail_progress)
    with pytest.raises(RuntimeError, match="reporting fixture"):
        train(root, model_factory=ToyHead)
    monkeypatch.setattr(training, "write_json", original_write)
    observed = []
    original_load = CachedBatches.load

    def load(self, index):
        observed.append(index)
        return original_load(self, index)

    monkeypatch.setattr(CachedBatches, "load", load)
    train(root, resume=True, model_factory=ToyHead)
    assert observed == [1, 2, 3]


def test_exclusive_json_snapshot_and_worker_lock(tmp_path):
    receipt = tmp_path / "receipt.json"
    write_json(receipt, {"value": 1})
    before = receipt.read_bytes()
    with pytest.raises(FileExistsError):
        write_json(receipt, {"value": 2})
    assert receipt.read_bytes() == before
    with pytest.raises(ValueError):
        write_json(receipt, {"value": float("nan")}, replace=True)
    assert receipt.read_bytes() == before
    with exclusive_run(tmp_path), pytest.raises(RuntimeError, match="already owns"):  # noqa: SIM117
        with exclusive_run(tmp_path):
            pass
    repo = tmp_path / "repository"
    (repo / "src/demosaic").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "src/demosaic/module.py").write_text("VALUE = 1\n")
    (repo / "scripts/a.py").write_text("from b import VALUE\n")
    (repo / "scripts/b.py").write_text("VALUE = 2\n")
    work, bindings = freeze_sources(repo, tmp_path / "snapshot", ["a.py"])
    assert len(bindings) == 3 and (work / "scripts/b.py").exists()


def test_package_imports_without_scripts_and_native_pixels_have_no_resampling(tmp_path):
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    command = (
        "from demosaic.experiments.data.shared_edge import pair_recipe; "
        "from demosaic.experiments.objectives.directional import objective; "
        "from demosaic.experiments.evaluation.detail import DetailMetrics; "
        "import sys; from demosaic.models import load_model, model_presets; "
        "assert callable(load_model) and model_presets()[0]['name']=='v120'; "
        "assert 'torch' not in sys.modules"
    )
    subprocess.run([sys.executable, "-c", command], cwd=tmp_path, env=env, check=True)
    rng = np.random.default_rng(4)
    values = rng.uniform(0, 0.1, (1, 3, 16, 20)).astype(np.float32)
    arrays = {
        "wb": np.array([[1.5, 1, 2]], np.float32),
        "matrix": np.eye(3, dtype=np.float32)[None],
    }
    path = tmp_path / "triplet.png"
    write_triplet(
        path,
        values,
        values,
        values,
        arrays,
        roi=[2, 4, 9, 8],
        exposure=4,
        source="fixture",
        checkpoint={"sha256": "fixture"},
        noise={"shot": 0.001},
        reference_kind="independent-ISO100-reference",
    )
    from PIL import Image

    pixels = np.asarray(Image.open(path))
    assert pixels.shape == (8, 27, 3)
    expected = display_pixels(values, arrays, [2, 4, 9, 8], 4)
    assert np.array_equal(pixels[:, :9], expected)
    assert np.array_equal(pixels[:, :9], pixels[:, 9:18])
    assert read_json(path.with_suffix(".json"))["reference_kind"] == "independent-ISO100-reference"


def test_frozen_package_resolves_checkout_output_root(tmp_path, monkeypatch):
    from demosaic.experiments import paths

    project = tmp_path / "project"
    (project / "src/demosaic").mkdir(parents=True)
    (project / "pyproject.toml").write_text("[project]\nname='fixture'\n")
    frozen = project / ".cache/run/work/src/demosaic/experiments/paths.py"
    monkeypatch.setattr(paths, "__file__", str(frozen))
    assert paths.repository_root() == project
    assert paths.writable_output(project / "output.pt") == project / "output.pt"
    with pytest.raises(ValueError):
        paths.writable_output("/home/dllu/pictures/output.pt")


def test_established_pure_metrics_and_display_without_script_sources():
    from demosaic.experiments.evaluation.metrics import errors, photo_metrics

    rng = np.random.default_rng(32)
    target = rng.uniform(0.001, 0.02, (1, 3, 160, 160)).astype(np.float32)
    arrays = {"wb": np.ones((1, 3), np.float32), "matrix": np.eye(3, dtype=np.float32)[None]}
    row = photo_metrics(target, target, arrays, [0, 0, 160, 160])
    assert row["crop_linear_sRGB_luma_band_gain"] == 1
    assert row["crop_relative_band_error"] == row["crop_orthogonal_band_RMS_DN16"] == 0
    row = errors(np.ones_like(target), np.zeros_like(target), [0, 0, 160, 160])
    assert row == {
        "full_error_RMS_DN16": 65535,
        "crop_DC_RMS_DN16": 65535,
        "crop_spatial_RMS_DN16": 0,
    }


def test_streamed_real_evaluation_has_no_target_scoring_or_parent_inference(tmp_path):
    from demosaic.experiments.evaluation.runner import evaluate_cases

    class SuppliedParent(nn.Module):
        def forward(self, base, packed, variance, colors, wb):
            return base

    cache, _ = cached_fixture(tmp_path / "data")
    row = read_json(cache["path"])["batches"][0]
    with np.load(row["arrays"]["path"], allow_pickle=False) as archive:
        arrays = {k: archive[k] for k in ("packed", "variance", "colors", "wb")}
    observation = tmp_path / "real.npz"
    np.savez(observation, **arrays)
    manifest = tmp_path / "cases.json"
    write_json(
        manifest,
        {
            "observations": [
                {
                    "id": "real-fixture",
                    "kind": "real",
                    "arrays": reference(observation),
                    "parent": row["parent"],
                }
            ]
        },
    )
    output = tmp_path / "evaluation"
    binding = evaluate_cases(
        SuppliedParent(), manifest, output, checkpoint={"sha256": "fixture"}, method="fixture"
    )
    result = read_json(binding["path"])
    assert result["rows"][0]["reference_scored"] is False
    assert result["new_parent_DINO_forwards"] == result["new_noise_draws"] == 0
