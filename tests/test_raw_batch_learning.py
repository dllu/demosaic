import importlib.util
import sys
from pathlib import Path

import pytest
import torch

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.model import JointDemosaic, ModelConfig


def prototype():
    directory = str(Path("scripts").absolute())
    sys.path.insert(0, directory)
    try:
        spec = importlib.util.spec_from_file_location(
            "raw_batch_learning", Path("scripts/probe_raw_batch_learning.py")
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(directory)


def fixture():
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
    )
    torch.nn.init.normal_(model.packed_isotropic.head.weight, std=0.002)
    batches = []
    for _ in range(4):
        colors = torch.stack([color_indices(pattern) for pattern in PATTERNS])
        target = torch.rand(4, 3, 16, 20) * 0.6 + 0.1
        packed = mosaic(target, colors) + torch.randn(4, 4, 8, 10) * 0.01
        mask = torch.zeros_like(target, dtype=torch.bool)
        for index in range(4):
            for phase, color in enumerate(colors[index]):
                mask[index, color, phase // 2 :: 2, phase % 2 :: 2] = True
        mask[..., :2, :] = False
        batches.append(
            {
                "packed": packed,
                "variance": packed.clamp_min(0) * 0.002 + 1e-6,
                "colors": colors,
                "target": target,
                "shot": torch.full((4, 1, 1, 1), 0.002),
                "read": torch.full((4, 1, 1, 1), 1e-6),
                "wb": torch.ones(4, 3),
                "matrix": torch.eye(3)[None].repeat(4, 1, 1),
                "sensor_reference": target * mask,
                "sensor_mask": mask,
            }
        )
    return model, batches


@pytest.mark.parametrize("mode", ["raw", "gain32-residual32"])
def test_actual_batch16_matches_four_domain_gradients_and_preserves_inputs(mode):
    module = prototype()
    model, batches = fixture()
    domains = ["paired", "native", "commons", "paired"]
    fingerprints = [module.batch_fingerprint(batch) for batch in batches]
    before = {name: value.clone() for name, value in model.state_dict().items()}
    with module.coordinates(model, mode, batches[0]):
        grouped = module.grouped_loss(model, batches, domains)
    grouped.backward()
    gradients = {name: parameter.grad.clone() for name, parameter in model.named_parameters()}
    assert torch.count_nonzero(gradients["packed_isotropic.stem.weight"]) > 0
    model.zero_grad(set_to_none=True)
    sequential = []
    for batch, domain in zip(batches, domains, strict=True):
        with module.coordinates(model, mode, batch):
            _, loss = module.loss_for(model, batch, domain)
        (loss / 4).backward()
        sequential.append(loss.detach())
    torch.testing.assert_close(grouped, torch.stack(sequential).mean(), rtol=1e-6, atol=1e-7)
    for name, parameter in model.named_parameters():
        torch.testing.assert_close(parameter.grad, gradients[name], rtol=1e-4, atol=1e-6)
    assert [module.batch_fingerprint(batch) for batch in batches] == fingerprints
    assert all(torch.equal(value, before[name]) for name, value in model.state_dict().items())


def test_single_group_matches_original_domain_loss():
    module = prototype()
    model, batches = fixture()
    for domain in ["commons", "native", "paired"]:
        grouped = module.grouped_loss(model, batches[:1], [domain])
        _, original = module.loss_for(model, batches[0], domain)
        torch.testing.assert_close(grouped, original, rtol=0, atol=0)


def test_empty_or_unequal_groups_rejected():
    module = prototype()
    model, batches = fixture()
    with pytest.raises(ValueError, match="nonempty"):
        module.grouped_loss(model, [], [])
    with pytest.raises(ValueError, match="nonempty"):
        module.grouped_loss(model, batches, ["commons"])
    batches[0] = {key: value[:2] for key, value in batches[0].items()}
    with pytest.raises(ValueError, match="equal sizes"):
        module.grouped_loss(model, batches, ["commons"] * 4)
