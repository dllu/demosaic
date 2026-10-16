import hashlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch
from torch import nn
from torch.nn import functional as F

from demosaic.cfa import PATTERNS, color_indices, malvar
from demosaic.model import JointDemosaic, ModelConfig
from demosaic.pretrained_rgb import PretrainedRgbDemosaic
from demosaic.train import make_optimizer, set_learning_rate


def config():
    return ModelConfig(
        restoration_backbone="pretrained-rgb", width=64, camera_conditioning=True,
        variance_stabilization=True, physical_anchors=True, rgb_processing_scale=2,
        packed_detail_prior=True,
    )


class IdentityTrunk(nn.Module):
    def forward(self, rgb, noise, **kwargs):
        return rgb, rgb.new_zeros(len(rgb), 64, *rgb.shape[-2:])


def test_default_packed_branch_matches_pinned_v38_implementation():
    path = Path(__file__).parent / "fixtures/pretrained_rgb_packed_v1.py"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == "970aaa305e277bd833b174172aad2b149e5af6f7ed5d940cb2989847251e18ff"
    spec = importlib.util.spec_from_file_location("demosaic._packed_v1", path)
    legacy = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy)
    torch.manual_seed(13)
    old = legacy.PretrainedRgbDemosaic(stabilized=True, physical_anchors=True, processing_scale=2)
    new = PretrainedRgbDemosaic(stabilized=True, physical_anchors=True, processing_scale=2)
    new.load_state_dict(old.state_dict(), strict=True)
    raw = torch.rand(2, 4, 9, 13) * .1
    colors = torch.stack([color_indices("RGGB"), color_indices("GRBG")])
    wb = torch.tensor([[2., 1., 1.5], [1.5, 1., 2.3]])
    for branch in [old, new]:
        branch.set_noise([.001, 0], [1e-6, 1e-6])
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        expected = old(raw, torch.ones_like(raw), colors, wb)
        actual = new(raw, torch.ones_like(raw), colors, wb)
    torch.testing.assert_close(actual, expected, rtol=0, atol=0)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_highpass_variance_matches_monte_carlo_per_color_phase_with_wb(pattern):
    branch = PretrainedRgbDemosaic(stabilized=True, processing_scale=2, detail_prior=True)
    colors = color_indices(pattern)[None]
    wb = torch.tensor([[2., 1., 1.5]])
    expected = branch.detail_noise_variance(colors, wb)[0]
    torch.manual_seed(87)
    raw = torch.randn(8192, 4, 6, 6)
    rgb = malvar(raw, colors.expand(len(raw), -1), wb)
    expanded = F.interpolate(F.avg_pool2d(rgb, 2), scale_factor=2, mode="bilinear", align_corners=False)
    actual = (rgb - expanded)[..., 6:8, 6:8].var(0)
    torch.testing.assert_close(actual, expected, rtol=.06, atol=0)


@pytest.mark.parametrize("pattern", PATTERNS)
def test_detail_prior_preserves_adc_native_ramp_under_bf16(pattern):
    model = JointDemosaic(config()).to(memory_format=torch.channels_last)
    model.pretrained_rgb.network = IdentityTrunk()
    model.set_noise(0, 0)
    raw = .3 + torch.arange(4 * 9 * 13).reshape(1, 4, 9, 13) / 65535
    colors = color_indices(pattern)
    with torch.no_grad(), torch.autocast("cpu", dtype=torch.bfloat16):
        actual = model(raw, torch.zeros_like(raw), colors)
    assert actual.shape == (1, 3, 18, 26) and actual.dtype == torch.float32
    assert torch.unique(actual).numel() > 256
    torch.testing.assert_close(actual, malvar(raw, colors), rtol=0, atol=1 / 65535 / 8)


def test_zero_variance_keeps_detail_and_flat_gaussian_noise_is_attenuated():
    model = JointDemosaic(config())
    branch = model.pretrained_rgb
    detail = torch.randn(2, 3, 18, 26)
    torch.testing.assert_close(branch.filter_detail(detail, torch.zeros_like(detail)), detail, rtol=0, atol=0)
    branch.network = IdentityTrunk()
    model.set_noise(0, 1e-4)
    torch.manual_seed(109)
    raw = .2 + torch.randn(16, 4, 32, 32) * .01
    colors = color_indices("RGGB")
    with torch.no_grad():
        actual = model(raw, torch.full_like(raw, 1e-4), colors)
    initial = malvar(raw, colors)
    roi = (..., slice(8, -8), slice(8, -8))
    before = (initial[roi] - .2).square().mean()
    after = (actual[roi] - .2).square().mean()
    assert after < before * .65


def test_prior_backpropagates_and_checkpoint_roundtrip_keeps_exact_output(tmp_path):
    from demosaic.inference import load_checkpoint

    model = JointDemosaic(config()).to(memory_format=torch.channels_last)
    model.set_noise(0, 1e-6)
    raw = torch.rand(1, 4, 9, 13) * .2
    variance = torch.full_like(raw, 1e-6)
    output = model(raw, variance, color_indices("GBRG"))
    output.square().mean().backward()
    for module in [model.pretrained_rgb.phase_head, model.pretrained_rgb.phase_adapter]:
        assert torch.isfinite(module.weight.grad).all() and module.weight.grad.abs().sum() > 0
    path = tmp_path / "prior.pt"
    torch.save({"model_config": model.config.to_dict(), "model": model.restoration_state_dict()}, path)
    loaded, _ = load_checkpoint(path)
    loaded.to(memory_format=torch.channels_last).set_noise(0, 1e-6)
    with torch.no_grad():
        actual = loaded(raw, variance, color_indices("GBRG"))
    torch.testing.assert_close(actual, output, rtol=0, atol=0)


class TinyPhaseModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.base = nn.Linear(2, 2)
        self.pretrained_rgb = nn.Module()
        self.pretrained_rgb.phase_head = nn.Linear(2, 2)
        self.pretrained_rgb.phase_adapter = nn.Linear(2, 2)
        self.config = SimpleNamespace(rgb_processing_scale=2)

    def forward(self, x):
        return self.base(x) + self.pretrained_rgb.phase_head(x) + self.pretrained_rgb.phase_adapter(x)


def test_phase_lr_groups_schedule_and_optimizer_resume_match():
    torch.manual_seed(99)
    model = TinyPhaseModel()
    optimizer = make_optimizer(model, {"lr": 3e-5, "phase_lr_multiplier": 10})
    assert [g["lr"] for g in optimizer.param_groups] == pytest.approx([3e-5, 3e-4])
    assigned = [id(p) for g in optimizer.param_groups for p in g["params"]]
    assert len(set(assigned)) == len(list(model.parameters())) == len(assigned)
    x = torch.ones(1, 2)
    for lr in [1e-6, 3e-5, 2e-5]:
        set_learning_rate(optimizer, lr)
        assert [g["lr"] for g in optimizer.param_groups] == [lr, lr * 10]
        optimizer.zero_grad()
        model(x).square().mean().backward()
        optimizer.step()
    restored = TinyPhaseModel()
    restored.load_state_dict(model.state_dict())
    other = make_optimizer(restored, {"lr": 3e-5, "phase_lr_multiplier": 10})
    # Optimizer state tensors must be independent of the reference step.
    import copy

    other.load_state_dict(copy.deepcopy(optimizer.state_dict()))
    for m, o in [(model, optimizer), (restored, other)]:
        set_learning_rate(o, 1e-5)
        o.zero_grad()
        m(x).square().mean().backward()
        o.step()
    for a, b in zip(model.parameters(), restored.parameters()):
        torch.testing.assert_close(a, b, rtol=0, atol=0)
    default = make_optimizer(TinyPhaseModel(), {"lr": 3e-5})
    assert len(default.param_groups) == 1 and "lr_multiplier" not in default.param_groups[0]


@pytest.mark.parametrize("value", [0, -1, float("inf"), float("nan")])
def test_invalid_phase_lr_rejected(value):
    with pytest.raises(ValueError, match="finite and positive"):
        make_optimizer(TinyPhaseModel(), {"phase_lr_multiplier": value})


def test_invalid_prior_or_nonphase_lr_configuration_rejected():
    with pytest.raises(ValueError, match="requires RGB processing scale 2"):
        JointDemosaic(ModelConfig(packed_detail_prior=True))
    with pytest.raises(ValueError, match="requires trainable packed phase"):
        make_optimizer(nn.Linear(2, 2), {"phase_lr_multiplier": 10})
