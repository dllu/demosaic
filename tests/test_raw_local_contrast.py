import importlib.util
import sys
from pathlib import Path

import pytest
import torch
from torch.nn import functional as F

from demosaic import packed_isotropic
from demosaic.cfa import PATTERNS, bilinear, color_indices
from demosaic.model import JointDemosaic, ModelConfig


def prototype():
    directory = str(Path("scripts").absolute())
    sys.path.insert(0, directory)
    try:
        spec = importlib.util.spec_from_file_location(
            "raw_local_contrast", Path("scripts/probe_raw_local_contrast.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(directory)


@pytest.mark.parametrize("window", [7, 31])
def test_fixed_phase_filter_matches_direct_reflected_mean_and_stays_fp32(window):
    torch.manual_seed(4)
    raw = torch.rand(2, 4, 35, 41) - 0.03
    before = raw.clone()
    radius = window // 2
    expected = (raw - F.avg_pool2d(F.pad(raw, (radius,) * 4, mode="reflect"), window, 1)) * 32
    with torch.autocast("cpu", dtype=torch.bfloat16):
        actual = prototype().raw_features(raw, f"local{window}-residual32")
    assert actual.dtype == torch.float32 and torch.equal(raw, before)
    torch.testing.assert_close(actual, expected, rtol=0, atol=4e-5)


def test_filter_is_local_preserves_16bit_change_and_removes_constant_level():
    module = prototype()
    raw = torch.full((1, 4, 35, 41), 0.25)
    assert torch.count_nonzero(module.raw_features(raw, "local7-residual32")) == 0
    changed = raw.clone()
    changed[:, 2, 17, 20] += 1 / 65535
    mapped = module.raw_features(changed, "local7-residual32")
    assert mapped[0, 2, 17, 20] > 0 and torch.count_nonzero(mapped[:, :2]) == 0
    assert torch.count_nonzero(mapped[..., :14, :]) == 0
    torch.testing.assert_close(
        module.raw_features(changed[..., 5:30, 6:35], "local7-residual32")[..., 3:-3, 3:-3],
        mapped[..., 8:27, 9:32],
        rtol=0,
        atol=0,
    )


@pytest.mark.parametrize(
    "mode", ["raw", "gain32-residual32", "local7-residual32", "local31-residual32"]
)
def test_actual_model_keeps_physical_skip_metadata_and_restores_context(mode):
    module = prototype()
    torch.manual_seed(51)
    model = JointDemosaic(
        ModelConfig(
            restoration_backbone="packed-isotropic",
            camera_conditioning=True,
            width=8,
            isotropic_groups=1,
            isotropic_blocks=1,
            isotropic_local_width=8,
        )
    ).eval()
    raw = torch.rand(4, 4, 17, 25) * 0.6 - 0.02
    variance = raw.clamp_min(0) * 0.002 + 1e-6
    colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
    original = packed_isotropic.physical_features
    before = {name: value.clone() for name, value in model.state_dict().items()}
    identities = [id(p) for p in model.parameters()]
    metadata = original(raw, variance, colors)[:, 4:]
    hooks = dict(model.packed_isotropic.head._forward_hooks)
    with torch.inference_mode(), module.coordinates(model, mode, {}):
        assert torch.equal(model(raw, variance, colors), bilinear(raw, colors))
        assert torch.equal(
            packed_isotropic.physical_features(raw, variance, colors)[:, 4:], metadata
        )
    with pytest.raises(RuntimeError, match="intentional"), module.coordinates(model, mode, {}):
        raise RuntimeError("intentional")
    assert packed_isotropic.physical_features is original
    assert dict(model.packed_isotropic.head._forward_hooks) == hooks
    assert identities == [id(p) for p in model.parameters()]
    assert all(torch.equal(value, before[name]) for name, value in model.state_dict().items())


def test_unknown_coordinate_mode_rejected():
    with pytest.raises(ValueError, match="mode"):
        prototype().raw_features(torch.ones(1, 4, 7, 9), "unknown")
