"""Independently audit saved native40x faint-ADC display PNG pixels."""

import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import noisy_malvar


def audit(root):
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or "torch" in sys.modules:
        raise RuntimeError("Saved display auditing is CPU-only without Torch")
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
    plan = read(root / "plan-v1.json")
    guard(plan)
    manifest_path = root / "contrast-display-v1/manifest.json"
    manifest = read(manifest_path)
    assert manifest["report_plan"] == ref(root / "plan-v1.json")
    output = root / "contrast-display-v1/pixel-audit-v1.json"
    assert not output.exists()
    channels = different = maximum = 0
    for row in manifest["images"]:
        assert ref(row["image"]["path"]) == row["image"]
        assert row["ROI_xywh"] == [48, 48, 160, 160]
        assert (
            row["display_exposure_EV"] == 0
            and row["contrast_about_camera_DC"] == 40
            and row["no_resize"]
        )
        with np.load(row["case"]["original_target"]["path"], allow_pickle=False) as data:
            original = data["target"].astype(np.longdouble)
        dc = original.sum((-1, -2), keepdims=True) / (256 * 256)
        np.testing.assert_allclose(
            dc.reshape(3).astype(np.float64), row["camera_DC"], rtol=0, atol=2e-16
        )
        assert ref(row["input_arrays"]["path"]) == row["input_arrays"]
        with np.load(row["input_arrays"]["path"], allow_pickle=False) as data:
            arrays = {k: data[k] for k in data.files}
        png = np.asarray(Image.open(row["image"]["path"]))
        assert png.shape == (192, 8 + 168 * len(row["panels"]), 3)
        for i, panel in enumerate(row["panels"]):
            binding = panel["prediction_or_target"]
            if binding is None:
                assert i == 0 and panel["label"] == "ADC Malvar"
                value = noisy_malvar(arrays)
            else:
                assert ref(binding["path"]) == binding
                loaded = np.load(binding["path"], allow_pickle=False)
                if isinstance(loaded, np.lib.npyio.NpzFile):
                    with loaded:
                        value = loaded["target"]
                else:
                    value = loaded
            # Algebraically independent stretch:40x minus39 times the original DC.
            stretched = value.astype(np.longdouble) * 40 - dc * 39
            rgb = np.stack(
                [
                    sum(
                        stretched[:, c]
                        * np.longdouble(arrays["wb"][0, c])
                        * np.longdouble(arrays["matrix"][0, k, c])
                        for c in range(3)
                    )
                    for k in range(3)
                ],
                axis=1,
            ).clip(0, 1)
            display = np.where(
                rgb <= np.longdouble("0.0031308"),
                rgb * np.longdouble("12.92"),
                np.longdouble("1.055") * np.power(rgb, np.longdouble(5) / 12)
                - np.longdouble("0.055"),
            )
            expected = np.rint(display[0, :, 48:208, 48:208].transpose(1, 2, 0) * 255).astype(
                np.uint8
            )
            x, y, w, h = panel["png_xywh"]
            assert (x, y, w, h) == (8 + 168 * i, 24, 160, 160)
            delta = abs(png[y : y + h, x : x + w].astype(np.int16) - expected.astype(np.int16))
            maximum = max(maximum, int(delta.max()))
            different += int(np.count_nonzero(delta))
            channels += expected.size
    assert len(manifest["images"]) == 4 and maximum <= 1
    save(
        output,
        {
            "status": "passed-independent-saved-native-contrast-display-audit",
            "manifest": ref(manifest_path),
            "auditor": ref(__file__),
            "images": 4,
            "RGB_channels_checked": channels,
            "RGB_channels_exact": channels - different,
            "maximum_difference_DN8": maximum,
            "new_neural_forwards": 0,
            "stochastic_noise_draws": 0,
            "RAW_decodes": 0,
            "scope": "Every actual saved native160 panel reread and independently rendered with long-double channel reductions and algebraic40x-minus39DC contrast. Shared previously audited NumPy Malvar preview only. Primary scores/normal-contrast triplets remain separate.",
        },
    )
    print({"channels": channels, "exact": channels - different, "max_DN8": maximum})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("analysis_root", type=Path)
    audit(parser.parse_args().analysis_root.resolve())
