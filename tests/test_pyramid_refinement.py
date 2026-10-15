import json

import numpy as np
import pytest
import torch
import yaml

from demosaic.cfa import PATTERNS, color_indices, mosaic
from demosaic.data import degrade
from demosaic.model import JointDemosaic, ModelConfig, PyramidNoiseRefiner
from demosaic.precision import amp_context
from demosaic.train import train


def test_pyramid_warm_start_shapes_gradients_and_zero_variance():
    torch.set_num_threads(2)
    options = {"width": 8, "encoder_blocks": (1,), "middle_blocks": 1, "decoder_blocks": (1,)}
    base = JointDemosaic(ModelConfig(**options))
    model = JointDemosaic(
        ModelConfig(**options, pyramid_refinement=True, pyramid_width=12, pyramid_blocks=1)
    )
    missing, extra = model.load_state_dict(base.restoration_state_dict(), strict=False)
    assert not extra and missing and all(k.startswith("pyramid_refiner.") for k in missing)
    model.requires_grad_(False)
    model.pyramid_refiner.requires_grad_(True)
    batch = degrade(torch.rand(2, 3, 74, 102))
    args = [batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")]
    output = model(*args)
    torch.testing.assert_close(output, base(*args), atol=0, rtol=0)
    (output - batch["target"]).square().mean().backward()
    assert model.pyramid_refiner.head.weight.grad.abs().sum() > 0
    assert all(
        p.grad is None for n, p in model.named_parameters() if not n.startswith("pyramid_refiner.")
    )
    torch.nn.init.normal_(model.pyramid_refiner.head.weight, std=0.1)
    args[1] = torch.zeros_like(args[1])
    torch.testing.assert_close(model(*args), base(*args), atol=0, rtol=0)


def test_innovation_exposes_correct_cfa_measurements_and_ablation_removes_access():
    module = PyramidNoiseRefiner(8, width=12, blocks=1)
    with torch.no_grad():
        for p in module.parameters():
            p.zero_()
        # Route one innovation channel through the full-resolution skip.
        module.stem.weight[0, 24, 1, 1] = 1
        module.head.weight[0, 0, 1, 1] = 1
    colors = torch.stack([color_indices(p) for p in PATTERNS])
    rgb = torch.tensor([0.2, 0.3, 0.4])[None, :, None, None].expand(4, 3, 64, 72)
    packed = mosaic(rgb, colors).clone()
    variance = torch.full_like(packed, 1e-4)
    features = torch.zeros(4, 8, 32, 36)
    assert module(rgb, packed, variance, colors, features).count_nonzero() == 0
    packed[:, 0] += 0.001
    result = module(rgb, packed, variance, colors, features)
    assert result.abs().sum() > 0
    torch.testing.assert_close(
        result[:, 0, ::2, ::2], torch.full((4, 32, 36), 0.001), atol=2e-8, rtol=0
    )
    weights = {k: v.clone() for k, v in module.state_dict().items()}
    module.measurements = False
    assert module(rgb, packed, variance, colors, features).count_nonzero() == 0
    assert all(torch.equal(v, weights[k]) for k, v in module.state_dict().items())


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA half refinement")
def test_pyramid_half_neural_ops_preserve_fp32_outputs_and_physical_zero():
    module = PyramidNoiseRefiner(8, width=12, blocks=1).cuda()
    torch.nn.init.normal_(module.head.weight, std=0.01)
    module.compute_precision = "float16"
    rgb = torch.rand(2, 3, 64, 72, device="cuda") * 0.3
    colors = color_indices("GRBG", device="cuda")
    packed = mosaic(rgb, colors) + torch.randn(2, 4, 32, 36, device="cuda") * 0.001
    variance = torch.full_like(packed, 1e-5)
    variance[1].zero_()
    features = torch.rand(2, 8, 32, 36, device="cuda")
    types = []
    hook = module.head.register_forward_hook(lambda m, a, out: types.append(out.dtype))
    with amp_context("cuda", dtype="bfloat16"):
        result = module(rgb, packed, variance, colors, features)
    hook.remove()
    assert types == [torch.float16]
    assert result.dtype == torch.float32 and torch.isfinite(result).all()
    assert result[1].count_nonzero() == 0


def test_pyramid_only_exact_resume_and_frozen_original_weights(tmp_path):
    torch.set_num_threads(2)
    array = tmp_path / "clean.npy"
    np.save(array, np.full((40, 40, 3), 10000, dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps({"id": s, "split": s, "cache": array.name}) for s in ("train", "val"))
    )
    base = JointDemosaic(
        ModelConfig(width=4, encoder_blocks=(1,), middle_blocks=0, decoder_blocks=(1,))
    )
    source = tmp_path / "source.pt"
    torch.save(
        {
            "model_config": base.config.to_dict(),
            "model": base.restoration_state_dict(),
            "step": 0,
            "config": {},
        },
        source,
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
        "val_batches": 1,
        "log_every": 4,
        "min_available_gb": 0,
        "pyramid_refiner_only": True,
        "model": {
            **base.config.to_dict(),
            "pyramid_refinement": True,
            "pyramid_width": 12,
            "pyramid_blocks": 1,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config))
    full = train(path, initialize=source)
    config["run"] = str(tmp_path / "resumed")
    path.write_text(yaml.safe_dump(config))
    partial = train(path, initialize=source, stop_after=2)
    resumed = train(path, resume=partial)
    expected = torch.load(full, weights_only=True)
    actual = torch.load(resumed, weights_only=True)
    for group in ("model", "ema"):
        for key, value in expected[group].items():
            torch.testing.assert_close(value, actual[group][key], atol=0, rtol=0)
    for key, value in base.restoration_state_dict().items():
        torch.testing.assert_close(actual["model"][key], value, atol=0, rtol=0)
    assert actual["model"]["pyramid_refiner.head.weight"].abs().sum() > 0
    config["pyramid_refiner_only"] = False
    path.write_text(yaml.safe_dump(config))
    with pytest.raises(ValueError, match="trainable-parameter selection"):
        train(path, resume=partial)
