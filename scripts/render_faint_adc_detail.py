"""Render a fixed40x contrast diagnostic from saved faint-ADC predictions."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import noisy_malvar


def render(root):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Contrast display is CPU/NumPy only")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    plan = read(root / "plan-v1.json")
    guard(plan)
    audit = read(root / "independent-audit-v1.json")
    assert audit["status"] == "passed-independent-FFT-metric-and-native-pixel-audit"
    collection = read(root / "collection-v1.json")
    assert collection["plan"] == ref(root / "plan-v1.json")
    rows = {r["id"]: r for r in collection["observations"]}
    destination = root / "contrast-display-v1"
    destination.mkdir(exist_ok=False)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    images, channels, maximum = [], 0, 0
    for observation in plan["observations"]:
        if observation["pattern"] != "RGGB":
            continue
        case = observation["case"]
        with np.load(case["original_target"]["path"], allow_pickle=False) as data:
            original = data["target"]
        with np.load(observation["target"]["path"], allow_pickle=False) as data:
            target = data["target"]
        with np.load(observation["arrays"]["path"], allow_pickle=False) as data:
            arrays = {k: data[k] for k in data.files}
        dc = original.astype(np.float64).mean((-1, -2), keepdims=True)
        methods = [("ADC Malvar", noisy_malvar(arrays), None)]
        for control in observation["controls"]:
            methods.append(
                (
                    control["model"]["label"],
                    np.load(control["prediction"]["path"], allow_pickle=False),
                    control["prediction"],
                )
            )
        methods.append(
            (
                plan["model_label"],
                np.load(rows[observation["id"]]["prediction"]["path"], allow_pickle=False),
                rows[observation["id"]]["prediction"],
            )
        )
        methods.append(
            (
                "GT synthetic"
                if case["original_case_id"] in ("bark", "raccoon-fur")
                else "Binned ref (not GT)",
                target,
                observation["target"],
            )
        )
        board = Image.new("RGB", (8 + 168 * len(methods), 192), "#eeeeee")
        draw = ImageDraw.Draw(board)
        panels = []
        for i, (label, value, binding) in enumerate(methods):
            amplified = dc + 40 * (value.astype(np.float64) - dc)
            balanced = amplified * arrays["wb"][..., None, None]
            rgb = np.einsum("bij,bjhw->bihw", arrays["matrix"].astype(np.float64), balanced).clip(
                0, 1
            )
            display = np.where(rgb <= 0.0031308, 12.92 * rgb, 1.055 * rgb ** (1 / 2.4) - 0.055)
            pixels = np.rint(display[0, :, 48:208, 48:208].transpose(1, 2, 0) * 255).astype(
                np.uint8
            )
            x = 8 + 168 * i
            draw.text((x, 5), label, fill="black", font=font)
            board.paste(Image.fromarray(pixels), (x, 24))
            # Independent long-double scalar-channel rendering, same fixed DC.
            independent_dc = original.astype(np.longdouble).mean((-1, -2), keepdims=True)
            stretched = independent_dc + 40 * (value.astype(np.longdouble) - independent_dc)
            independent_rgb = np.stack(
                [
                    sum(
                        stretched[:, c]
                        * np.longdouble(arrays["wb"][0, c])
                        * np.longdouble(arrays["matrix"][0, channel, c])
                        for c in range(3)
                    )
                    for channel in range(3)
                ],
                axis=1,
            ).clip(0, 1)
            independent_display = np.where(
                independent_rgb <= np.longdouble("0.0031308"),
                independent_rgb * np.longdouble("12.92"),
                np.longdouble("1.055") * independent_rgb ** (np.longdouble(5) / 12)
                - np.longdouble("0.055"),
            )
            expected = np.rint(
                independent_display[0, :, 48:208, 48:208].transpose(1, 2, 0) * 255
            ).astype(np.uint8)
            error = int(np.max(abs(expected.astype(np.int16) - pixels.astype(np.int16))))
            assert error <= 1
            maximum = max(maximum, error)
            channels += pixels.size
            panels.append(
                {"label": label, "prediction_or_target": binding, "png_xywh": [x, 24, 160, 160]}
            )
        output = destination / (observation["case_id"] + "-contrast40.png")
        board.save(output)
        reread = np.asarray(Image.open(output))
        for panel in panels:
            x, y, w, h = panel["png_xywh"]
            assert reread[y : y + h, x : x + w].shape == (160, 160, 3)
        images.append(
            {
                "image": ref(output),
                "panels": panels,
                "case": case,
                "checkpoint": plan["checkpoint"],
                "noise": observation["noise"],
                "input_arrays": observation["arrays"],
                "ROI_xywh": [48, 48, 160, 160],
                "display_exposure_EV": 0,
                "camera_DC": dc.reshape(3).tolist(),
                "contrast_about_camera_DC": 40,
                "no_resize": True,
            }
        )
    assert len(images) == 4
    save(
        destination / "manifest.json",
        {
            "status": "fixed-contrast-display-from-audited-native-predictions",
            "report_plan": ref(root / "plan-v1.json"),
            "source_audit": ref(root / "independent-audit-v1.json"),
            "renderer": ref(__file__),
            "images": images,
            "independent_render_channels": channels,
            "maximum_longdouble_render_difference_DN8": maximum,
            "new_neural_forwards": 0,
            "new_noise_observations": 0,
            "RAW_decodes": 0,
            "scope": "Display only: reference original per-camera-channel whole256 DC plus40 times deviations, then common WB/matrix/sRGB,+0EV. No resizing or parameter fitting; this restores target display contrast, also magnifies model/ADC/interpolation errors. Primary scores use unamplified faint targets. Never a normal-exposure photograph or independent native GT claim.",
        },
    )
    print({"images": len(images), "render_channels": channels, "maximum_DN8_difference": maximum})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis_root", type=Path)
    render(parser.parse_args().analysis_root.resolve())
