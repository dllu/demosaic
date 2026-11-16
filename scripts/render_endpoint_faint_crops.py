"""Show retained faint-ADC detail with one common, recorded linear display transform."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from train_directional_bank_trial import read, ref, save

from demosaic.archive_metrics import linear_rgb, noisy_malvar


def checked(binding):
    if ref(binding["path"]) != binding:
        raise ValueError("Retained source changed")
    return binding["path"]


def render(root, output, contrast=40.0):
    if not np.isfinite(contrast) or contrast <= 0:
        raise ValueError("Positive finite contrast required")
    plan = read(root / "plan-v1.json")
    collection = read(root / "collection-v1.json")
    audit = read(root / "independent-audit-v1.json")
    assert (
        collection["plan"] == ref(root / "plan-v1.json")
        and audit["status"] == "passed-independent-FFT-metric-and-native-pixel-audit"
    )
    rows = {r["id"]: r for r in collection["observations"]}
    records = []
    output.mkdir(parents=True, exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    for obs in plan["observations"]:
        if (
            obs["kind"] != "material"
            or "contrast0p025-adc" not in obs["case_id"]
            or obs.get("pattern") != "RGGB"
        ):
            continue
        with np.load(checked(obs["arrays"]), allow_pickle=False) as z:
            arrays = dict(z)
        with np.load(checked(obs["target"]), allow_pickle=False) as z:
            target = z["target"]
        new = np.load(checked(rows[obs["id"]]["prediction"]), allow_pickle=False)
        x, y, w, h = obs["ROI_xywh"]
        assert (w, h) == (160, 160)
        exposure = obs["display_exposure"]
        truth = linear_rgb(target.astype(np.float64), arrays) * exposure
        anchor = truth[..., y : y + h, x : x + w].mean((-1, -2), keepdims=True)
        exact = obs["original_case_id"] in ["bark", "raccoon-fur"]
        reference_label = "Exact synthetic GT" if exact else "Binned ref, not GT"
        values = (
            [("Noisy Malvar", noisy_malvar(arrays))]
            + [
                (
                    c.get("label", c.get("model", {}).get("label")),
                    np.load(checked(c["prediction"]), allow_pickle=False),
                )
                for c in obs["controls"]
            ]
            + [(plan["model_label"], new), (reference_label, target)]
        )
        cells = []
        clipping = []
        for label, value in values:
            mapped = 0.18 + contrast * (
                linear_rgb(value.astype(np.float64), arrays) * exposure - anchor
            )
            region = mapped[0, :, y : y + h, x : x + w]
            clipping.append(
                {
                    "method": label,
                    "fraction_channels_clipped": float(np.mean((region < 0) | (region > 1))),
                }
            )
            v = region.clip(0, 1)
            srgb = np.where(v <= 0.0031308, 12.92 * v, 1.055 * v ** (1 / 2.4) - 0.055)
            cells.append((label, np.rint(srgb.transpose(1, 2, 0) * 255).astype(np.uint8)))

        def board(name, parts):
            image = Image.new("RGB", (8 + 168 * len(parts), 192), "#eeeeee")
            draw = ImageDraw.Draw(image)
            panels = []
            for i, (label, pixels) in enumerate(parts):
                draw.text((8 + 168 * i, 5), label, font=font, fill="black")
                image.paste(Image.fromarray(pixels), (8 + 168 * i, 24))
                panels.append({"label": label, "xywh": [8 + 168 * i, 24, 160, 160]})
            path = output / name
            image.save(path)
            check = np.asarray(Image.open(path))
            for panel, (_, pixels) in zip(panels, parts, strict=True):
                px, py, pw, ph = panel["xywh"]
                np.testing.assert_array_equal(check[py : py + ph, px : px + pw], pixels)
            return {"image": ref(path), "panels": panels}

        stem = obs["case_id"]
        suffix = f"-contrast{contrast:g}"
        comparison = board(stem + suffix + "-comparison.png", cells)
        triplet = board(stem + suffix + "-triplet.png", [cells[0], cells[-2], cells[-1]])
        records.append(
            {
                "observation": obs,
                "prediction": rows[obs["id"]]["prediction"],
                "checkpoint": plan["checkpoint"],
                "comparison": comparison,
                "triplet": triplet,
                "no_resize": True,
                "reference_role": obs["reference_role"],
                "exact_constructed_GT": exact,
                "display": {
                    "linear_exposure": exposure,
                    "contrast": contrast,
                    "scene_linear_RGB_anchor": anchor.reshape(3).tolist(),
                    "mapped_anchor": 0.18,
                    "equation": "sRGB(clip(0.18 + contrast*(WB/matrix(cameraRGB)*exposure - common_GT_ROI_mean),0,1))",
                    "GT_used_only_for_common_display_anchor": True,
                },
                "clipping": clipping,
            }
        )
    assert len(records) == 4
    save(
        output / "manifest.json",
        {
            "figures": records,
            "source_plan": ref(root / "plan-v1.json"),
            "source_collection": ref(root / "collection-v1.json"),
            "source_audit": ref(root / "independent-audit-v1.json"),
            "script": ref(__file__),
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "scope": f"All four fixed RGGB faint-ADC source ROIs. Shared fixed contrast{contrast:g}/anchor transform across methods, native160 pixels never resized. Amplified diagnostic only, not a new model/metric. GT used only to define the common display anchor, never an inference input. Independent/binned references remain not GT.",
        },
    )
    print("rendered all4 retained faint-ADC comparisons/triplets, contrast", contrast)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--contrast", type=float, default=40.0)
    a = p.parse_args()
    render(a.root.resolve(), a.output.resolve(), a.contrast)
