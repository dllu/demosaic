import hashlib
import json

import numpy as np
import torch
import yaml
from PIL import Image

from demosaic.model import JointDemosaic, ModelConfig
from demosaic.reporting import center_crop, save_triplet
from demosaic.suite import run_suite


def test_native_triplet_preserves_every_quantized_pixel(tmp_path):
    rng = np.random.default_rng(5)
    panels = [(name, rng.random((160, 160, 3))) for name in ("Noisy", "Denoised", "GT")]
    receipt = save_triplet(tmp_path, "fixed-case", panels, caption="Case", metadata={"xy": [3, 7]})
    png = tmp_path / receipt["image"]
    image = np.asarray(Image.open(png))
    assert image.shape == (192, 512, 3)
    for (_, values), panel in zip(panels, receipt["panels"]):
        x, y, w, h = panel["png_xywh"]
        np.testing.assert_array_equal(image[y : y + h, x : x + w], np.rint(values * 255))
    assert hashlib.sha256(png.read_bytes()).hexdigest() == receipt["png_sha256"]
    assert json.loads(png.with_suffix(".json").read_text())["xy"] == [3, 7]
    assert center_crop((1, 3, 64, 64), border=8) == [8, 8, 48, 48]


def test_quality_suite_writes_native_crops_and_embedded_report(tmp_path):
    torch.set_num_threads(2)
    source = tmp_path / "clean.npy"
    np.save(source, np.full((192, 192, 3), 10000, dtype=np.uint16))
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(json.dumps({"id": "fixed", "cache": source.name, "split": "val"}) + "\n")
    config = ModelConfig(width=4, encoder_blocks=(1,), middle_blocks=0, decoder_blocks=(1,))
    model = JointDemosaic(config)
    checkpoint = tmp_path / "model.pt"
    torch.save(
        {
            "model_config": config.to_dict(),
            "model": model.state_dict(),
            "step": 1,
            "config": {"run": "test"},
        },
        checkpoint,
    )
    protocol = tmp_path / "protocol.yaml"
    protocol.write_text(
        yaml.safe_dump(
            {
                "patterns": ["RGGB"],
                "white_balance": [1.0, 1.0, 1.0],
                "camera_to_srgb": np.eye(3).tolist(),
                "border": 8,
                "conditions": [{"name": "noise", "exposure": 1, "shot": 0.001, "read": 0.000001}],
            }
        )
    )
    result = run_suite(
        [checkpoint],
        manifest,
        tmp_path / "report",
        protocol,
        patch_size=192,
        synthetic_count=0,
        device="cpu",
    )
    assert len(result["native_crops"]) == 1
    crop = result["native_crops"][0]
    assert crop["evaluation_tile_xywh"] == [16, 16, 160, 160]
    assert crop["model"]["sha256"] == hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    assert crop["image"] in (tmp_path / "report/report.md").read_text()
