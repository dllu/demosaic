"""Publish native procedural target/empty pairs; no model-quality claim."""

import argparse
import math
import random
import shutil
from pathlib import Path

import numpy as np
import torch
from PIL import Image, ImageDraw, ImageFont
from train_directional_bank_trial import ref, save

from demosaic.data import augment_before_downsample
from demosaic.textures import crossed_line_texture


def report(root):
    torch.set_num_threads(2)
    root.mkdir(parents=True, exist_ok=False)
    source = root / "source"
    source.mkdir()
    paths = [Path(__file__), Path("src/demosaic/textures.py"), Path("src/demosaic/data.py")]
    for p in paths:
        shutil.copyfile(p, source / p.name)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    rows = []
    for seed in (2, 7, 19, 43, 89, 123):
        a, b = random.Random(seed), random.Random(seed)
        present, recipe = crossed_line_texture(512, a, pixel_scale=2, present=True)
        empty, absence = crossed_line_texture(512, b, pixel_scale=2, present=False)
        assert a.getstate() == b.getstate()
        p = augment_before_downsample(present, 256, a, optical_blur_probability=0)
        e = augment_before_downsample(empty, 256, b, optical_blur_probability=0)
        assert a.getstate() == b.getstate()
        target = root / f"seed-{seed}-targets.npz"
        np.savez(target, present=p.numpy(), empty=e.numpy())
        exposure = min(64.0, 0.18 / recipe["level"])
        panels = [
            ("Empty background", e),
            ("Crossed-line target", p),
            ("Target detail x10", e + 10 * (p - e)),
        ]
        canvas = Image.new("RGB", (512, 192), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        cells = []
        for index, (label, value) in enumerate(panels):
            rgb = (value[:, 48:208, 48:208].numpy().astype(np.float64) * exposure).clip(0, 1)
            srgb = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)
            cell = np.rint(srgb.transpose(1, 2, 0) * 255).astype(np.uint8)
            draw.text((8 + 168 * index, 5), label, fill="black", font=font)
            canvas.paste(Image.fromarray(cell), (8 + 168 * index, 24))
            cells.append(cell)
        path = root / f"seed-{seed}-training-pair.png"
        canvas.save(path)
        reread = np.asarray(Image.open(path))
        for index, cell in enumerate(cells):
            np.testing.assert_array_equal(reread[24:184, 8 + 168 * index : 168 + 168 * index], cell)
        rows.append(
            {
                "seed": seed,
                "recipe": recipe,
                "empty_recipe": absence,
                "targets": ref(target),
                "image": ref(path),
                "ROI_xywh": [48, 48, 160, 160],
                "display_exposure": exposure,
                "display_EV": math.log2(exposure),
                "third_cell_only_detail_multiplier": 10,
                "no_resize": True,
                "native_shape": [256, 256],
                "space": "scene-linear-sRGB",
                "geometry_and_final_area2": True,
                "optical_blur_probability": 0,
            }
        )
    save(
        root / "manifest-v1.json",
        {
            "status": "generated-and-native-pixel-checked-procedural-training-examples",
            "sources": [ref(p) for p in source.iterdir()],
            "examples": rows,
            "PNG_channels_exact": len(rows) * 3 * 160 * 160 * 3,
            "new_model_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "scope": "Six exact procedural target/empty counterfactuals, through actual geometry/area2. "
            "Training-data inspection only; no restored output, GT photograph, quality score or improved-model claim. "
            "Third cell amplifies target-minus-empty solely for display; training retains original FP32 targets.",
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    report(p.parse_args().root)
