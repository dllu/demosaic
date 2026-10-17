import json
import random

import numpy as np
import pytest
import torch
import yaml
from torch import nn

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import physical_rgb_features
from demosaic.train import normalization_augmentation_mask, train


@pytest.mark.parametrize("stochastic", [False, True])
def test_selected_feature_coordinates_match_direct_crop_without_changing_measurements(stochastic):
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    raw = torch.rand(4, 4, 16, 24)
    variance = torch.full_like(raw, float(stochastic))
    wb = torch.tensor([1.4, 1.0, 2.1])[None].expand(4, -1)
    # A supplied transformed RGB canvas allows a direct cropped-feature oracle
    # without giving MHC a different boundary. Unit/zero variance stays constant.
    rgb = torch.randn(4, 3, 32, 48) * 3
    original_raw, original_rgb = raw.clone(), rgb.clone()
    normal = physical_rgb_features(raw, variance, colors, wb, rgb=rgb, stabilized=True)
    zero = physical_rgb_features(
        raw,
        variance,
        colors,
        wb,
        rgb=rgb,
        stabilized=True,
        normalization_mask=torch.zeros(4, dtype=torch.bool),
    )
    for a, b in zip(normal, zero, strict=True):
        assert torch.equal(a, b)
    mask = torch.tensor([False, True, False, True])
    actual = physical_rgb_features(
        raw, variance, colors, wb, rgb=rgb, stabilized=True, normalization_mask=mask
    )
    cropped = physical_rgb_features(
        raw[..., 4:12, 6:18],
        variance[..., 4:12, 6:18],
        colors,
        wb,
        rgb=rgb[..., 8:24, 12:36],
        stabilized=True,
    )
    for index in range(4):
        if mask[index]:
            for component in [1, 2, 3]:
                assert torch.equal(
                    actual[component][index, ..., 8:24, 12:36], cropped[component][index]
                )
            for component in [4, 5]:
                assert torch.equal(actual[component][index], cropped[component][index])
        else:
            for a, b in zip(actual, normal, strict=True):
                assert torch.equal(a[index], b[index])
    measured, phase_mask = actual[3][:, :3], actual[3][:, 3:6]
    reconstructed = mosaic(measured * actual[5] + actual[4] * phase_mask, colors)
    torch.testing.assert_close(reconstructed, raw, atol=2e-6, rtol=0)
    assert torch.equal(raw, original_raw) and torch.equal(rgb, original_rgb)
    assert torch.equal(actual[0], normal[0])
    # Each image's choice and coordinates are independent of batch companions.
    single = physical_rgb_features(
        raw[1:2],
        variance[1:2],
        colors[1:2],
        wb[1:2],
        rgb=rgb[1:2],
        stabilized=True,
        normalization_mask=mask[1:2],
    )
    for a, b in zip(single, actual, strict=True):
        assert torch.equal(a[0], b[1])


def test_mask_protocol_is_stateless_reproducible_and_does_not_consume_rng():
    rng, python_rng = torch.get_rng_state().clone(), random.getstate()
    a = normalization_augmentation_mask(49, 101, 17, "cpu")
    assert a.dtype == torch.bool and a.shape == (17,)
    assert torch.equal(a, normalization_augmentation_mask(49, 101, 17, "cpu"))
    assert torch.equal(a[:9], normalization_augmentation_mask(49, 101, 9, "cpu"))
    assert not torch.equal(a, normalization_augmentation_mask(49, 102, 17, "cpu"))
    assert not torch.equal(a, normalization_augmentation_mask(50, 101, 17, "cpu"))
    assert torch.equal(rng, torch.get_rng_state()) and random.getstate() == python_rng
    for step, size in [(0, 1), (1, 0)]:
        with pytest.raises(ValueError, match="positive"):
            normalization_augmentation_mask(49, step, size, "cpu")


@pytest.mark.parametrize("mask", [torch.ones(2), torch.ones(1, dtype=torch.bool), [True, False]])
def test_invalid_feature_masks_rejected(mask):
    raw = torch.rand(2, 4, 8, 8)
    with pytest.raises(ValueError, match="one device-local boolean"):
        physical_rgb_features(
            raw, torch.ones_like(raw), color_indices("RGGB"), normalization_mask=mask
        )


class IdentityTrunk(nn.Module):
    def forward(self, rgb, noise, **kwargs):
        return rgb


def test_training_coordinates_preserve_physical_identity_and_are_refused_in_eval():
    model = JointDemosaic(
        ModelConfig(
            restoration_backbone="pretrained-rgb",
            width=64,
            camera_conditioning=True,
            variance_stabilization=True,
            physical_anchors=True,
        )
    )
    model.pretrained_rgb.network = IdentityTrunk()
    raw = torch.rand(4, 4, 8, 12) * 0.3
    variance = torch.ones_like(raw) * 1e-5
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    model.set_noise(
        torch.tensor([0.001, 0.0, 0.00002, 0.0]), torch.tensor([4e-6, 1e-6, 1.6e-9, 0.0])
    )
    with torch.no_grad():
        normal = model(raw, variance, colors)
        augmented = model(raw, variance, colors, normalization_mask=torch.ones(4, dtype=torch.bool))
    torch.testing.assert_close(normal, augmented, atol=3e-7, rtol=3e-6)
    model.eval()
    with pytest.raises(ValueError, match="anchored RGB training"):
        model(raw, variance, colors, normalization_mask=torch.zeros(4, dtype=torch.bool))
    with torch.no_grad():
        assert torch.equal(normal, model(raw, variance, colors))


class TinyTrunk(nn.Module):
    def __init__(self):
        super().__init__()
        self.input = nn.Conv2d(4, 3, 1)
        self.adapter = nn.Conv2d(64, 3, 1, bias=False)

    def forward(self, rgb, noise, head_offset, **kwargs):
        return self.input(torch.cat((rgb, noise), 1)) + self.adapter(head_offset)


def identical(a, b):
    if isinstance(a, torch.Tensor):
        assert torch.equal(a, b)
    elif isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            identical(a[key], b[key])
    elif isinstance(a, (tuple, list)):
        assert len(a) == len(b)
        for x, y in zip(a, b, strict=True):
            identical(x, y)
    else:
        assert a == b


def test_actual_trainer_restart_masks_input_hashes_and_policy_change_guard(tmp_path, monkeypatch):
    import demosaic.train as training

    constructor = training.JointDemosaic

    def fixture(config):
        net = constructor(config)
        net.pretrained_rgb.network = TinyTrunk()
        return net

    monkeypatch.setattr(training, "JointDemosaic", fixture)
    source = tmp_path / "source.npy"
    np.save(source, np.random.default_rng(49).integers(0, 65536, (48, 48, 3), dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps({"id": s, "split": s, "cache": source.name}) for s in ["train", "val"])
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
        "log_every": 1,
        "trace_observations": True,
        "min_available_gb": 0,
        "val_batches": 1,
        "seed": 49,
        "noise_free_fraction": 0.25,
        "data_seed_per_step": True,
        "normalization_augmentation": "center-half-mix-v1",
        "model": {
            "restoration_backbone": "pretrained-rgb",
            "width": 64,
            "camera_conditioning": True,
            "variance_stabilization": True,
            "physical_anchors": True,
        },
    }
    with torch.random.fork_rng():
        torch.manual_seed(49)
        initial_model = fixture(ModelConfig(**config["model"]))
    initializer = tmp_path / "fixture-initializer.pt"
    torch.save(
        {
            "model_config": initial_model.config.to_dict(),
            "model": initial_model.restoration_state_dict(),
            "step": 0,
        },
        initializer,
    )
    del initial_model
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    full = train(path, initialize=initializer)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    interrupted = train(path, initialize=initializer, stop_after=2)
    resumed = train(path, resume=interrupted)
    expected, actual = [torch.load(p, weights_only=True) for p in [full, resumed]]
    for key in ["model", "ema", "optimizer", "torch_rng", "python_rng", "cuda_rng", "best", "step"]:
        identical(expected[key], actual[key])
    rows = []
    for run in ["full", "resumed"]:
        rows.append(
            [
                json.loads(line)
                for line in (tmp_path / run / "metrics.jsonl").read_text().splitlines()
                if json.loads(line)["event"] == "train"
            ]
        )
    assert len(rows[0]) == len(rows[1]) == 4
    for a, b in zip(*rows, strict=True):
        assert a["batch_sha256"] == b["batch_sha256"]
        assert (
            a["normalization_mask"]
            == b["normalization_mask"]
            == normalization_augmentation_mask(49, a["step"], 1, "cpu").tolist()
        )
    config["run"] = str(tmp_path / "control")
    config["normalization_augmentation"] = "none"
    path.write_text(yaml.safe_dump(config))
    control = train(path, initialize=initializer)
    controls = [
        json.loads(line)
        for line in (tmp_path / "control/metrics.jsonl").read_text().splitlines()
        if json.loads(line)["event"] == "train"
    ]
    assert [r["batch_sha256"] for r in controls] == [r["batch_sha256"] for r in rows[0]]
    assert all("normalization_mask" not in r for r in controls)
    with pytest.raises(ValueError, match="Resume normalization augmentation differs"):
        train(path, resume=resumed)
    assert torch.load(control, weights_only=True)["config"]["normalization_augmentation"] == "none"


@pytest.mark.parametrize(
    "config",
    [
        {"normalization_augmentation": "unknown"},
        {"normalization_augmentation": "center-half-mix-v1", "model": {"width": 4}},
    ],
)
def test_invalid_training_policy_refused_before_data_access(tmp_path, config):
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="normalization|Normalization"):
        train(p)
