import json

import numpy as np
import torch
import yaml

from demosaic.cfa import color_indices
from demosaic.data import degrade
from demosaic.model import CoarseRgbNoiseRefiner, JointDemosaic, ModelConfig
from demosaic.train import train


def test_coarse_warm_start_preserves_image_and_adc_while_only_new_branch_learns():
    torch.set_num_threads(2)
    options = {
        "width": 8,
        "encoder_blocks": (1,),
        "middle_blocks": 1,
        "decoder_blocks": (1,),
        "noise_refinement": True,
        "refinement_width": 12,
        "refinement_blocks": 1,
    }
    base = JointDemosaic(ModelConfig(**options))
    torch.nn.init.normal_(base.head.weight, std=0.01)
    corrected = JointDemosaic(ModelConfig(**options, coarse_refinement_factor=8))
    missing, unexpected = corrected.load_state_dict(base.restoration_state_dict(), strict=False)
    assert not unexpected and missing and all(k.startswith("coarse_refiner.") for k in missing)
    corrected.requires_grad_(False)
    corrected.coarse_refiner.requires_grad_(True)
    # These sensor dimensions require independent, phase-safe padding at the
    # base-model and coarse-RGB scales.
    batch = degrade(torch.rand(2, 3, 72, 100))
    args = [batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")]
    result = corrected(*args)
    torch.testing.assert_close(result, base(*args), atol=0, rtol=0)
    (result - batch["target"]).square().mean().backward()
    assert corrected.coarse_refiner.network.head.weight.grad.abs().sum() > 0
    assert all(
        p.grad is None
        for n, p in corrected.named_parameters()
        if not n.startswith("coarse_refiner.")
    )
    torch.nn.init.normal_(corrected.coarse_refiner.network.head.weight, std=0.1)
    args[1] = torch.zeros_like(args[1])
    torch.testing.assert_close(corrected(*args), base(*args), atol=0, rtol=0)


def test_coarse_correction_can_remove_broad_error_without_following_fine_detail():
    module = CoarseRgbNoiseRefiner(8, factor=8, width=12, blocks=0, window=31)
    with torch.no_grad():
        for parameter in module.parameters():
            parameter.zero_()
        for c in range(12):
            module.network.stem.weight[c, c, 1, 1] = 1
            module.network.head.weight[c, c, 1, 1] = -1
    y, x = torch.meshgrid(torch.arange(256), torch.arange(256), indexing="ij")
    # A binary 16-bit grid makes the pooled-nullspace assertion exact rather
    # than dependent on cancellation error when averaging decimal .1 values.
    error = (64 * torch.sin(x.float() * 2 * torch.pi / 64)).round() / 65536
    rgb = (0.125 + error)[None, None].expand(1, 3, -1, -1)
    fine = ((x + y) % 2 * 2 - 1).float()[None, None] / 128
    var = torch.full((1, 4, 128, 128), 1e-4)
    features = torch.zeros(1, 8, 128, 128)
    args = (var, color_indices("RGGB"), features)
    correction = module(rgb, *args)
    torch.testing.assert_close(module(rgb + fine, *args), correction, atol=0, rtol=0)
    before = (rgb - 0.125)[..., 64:-64, 64:-64].square().mean()
    after = (rgb + correction - 0.125)[..., 64:-64, 64:-64].square().mean()
    assert after < before / 10


def test_coarse_only_training_resumes_exactly_and_preserves_frozen_weights(tmp_path):
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
        "coarse_refiner_only": True,
        "model": {
            **base.config.to_dict(),
            "coarse_refinement_factor": 4,
            "coarse_refinement_width": 12,
            "coarse_refinement_blocks": 0,
            "coarse_refinement_window": 7,
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
    assert actual["model"]["coarse_refiner.network.head.weight"].abs().sum() > 0
