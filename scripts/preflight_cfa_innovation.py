"""Validate cached input layouts and unchanged native reference display, no network."""

from collections import Counter

import numpy as np
from directional_trial_protocol import ref, save
from PIL import Image
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from review_cfa_innovation_wave import review_plan, source_guard
from train_cfa_innovation_wave import ROOT


def run():
    plan = review_plan()
    seal = source_guard(plan)
    assert ref(__file__) == seal["display_preflight"]
    from directional_trial_protocol import read

    layouts = Counter()
    design = read(plan["design"]["path"])["observations"]
    for case in design:
        assert ref(case["arrays"]["path"]) == case["arrays"]
        with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
            colors = archive["colors"]
        assert colors.shape == (1, 4) and colors.dtype == np.int64
        allowed = np.array([[0, 1, 1, 2], [2, 1, 1, 0], [1, 0, 2, 1], [1, 2, 0, 1]])
        assert (colors[:, None] == allowed).all(-1).any(-1).all()
        layouts[str(colors.tolist())] += 1
    assert sum(layouts.values()) == len(design) == 822
    save(
        ROOT / "input-layout-preflight-v1.json",
        {
            "status": "pass-all822cached-layouts-Nx4-int64",
            "design": plan["design"],
            "source": ref(__file__),
            "color_layout_counts": dict(layouts),
            "target_arrays_read": 0,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
        },
    )
    prior = read(plan["prior_figures"]["path"])
    panels = channels = 0
    for item in prior["images"]:
        references = [p for p in item["panels"] if p["label"] == "Exact constructed GT"]
        if not references:
            continue
        with np.load(item["case"]["arrays"]["path"], allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in ["target", "wb", "matrix"]}
        assert ref(item["image"]["path"]) == item["image"]
        image = np.asarray(Image.open(item["image"]["path"]).convert("RGB"))
        anchor = np.asarray(item["anchor"], dtype=np.float64).reshape(1, 3, 1, 1)
        displayed = anchor + item["contrast"] * (arrays["target"].astype(np.float64) - anchor)
        expected = pixels(displayed, arrays, item["ROI_xywh"], item["exposure"])
        np.testing.assert_array_equal(
            expected, independent_display(displayed, arrays, item["ROI_xywh"], item["exposure"])
        )
        for panel in references:
            x, y, w, h = panel["xywh"]
            assert w == h == 160 and item["no_resize"]
            np.testing.assert_array_equal(image[y : y + h, x : x + w], expected)
            panels += 1
            channels += expected.size
    assert panels == 64 and channels == 4915200
    save(
        ROOT / "reference-display-preflight-v1.json",
        {
            "status": "pass64existing-V197-exact-GT-panels-current-native-display",
            "prior_figures": plan["prior_figures"],
            "exact_GT_panels_checked": panels,
            "native_RGB_channels_checked": channels,
            "new_neural_forwards": 0,
            "new_images_written": 0,
            "source": ref(__file__),
            "scope": "Existing V197 exact-GT crop pixels match two independent display implementations. Real ISO100/JPEG references are qualitative and not scored. No source/noise draws or quality claims.",
        },
    )
    print("PASS822cachedlayouts/64existingGTpanels/4915200nativechannels/no new images")


if __name__ == "__main__":
    run()
