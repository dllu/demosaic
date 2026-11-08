"""Check reused exact-GT panels against their declared native display transform."""

import numpy as np
from directional_trial_protocol import ref, save
from phase_admission_protocol import read
from PIL import Image
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display
from review_innovation_wave import review_plan, source_guard
from train_innovation_wave import ROOT


def run():
    plan = review_plan()
    source_guard(plan)
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
    assert panels == 58 and channels == 4454400
    save(
        ROOT / "reference-display-preflight-v1.json",
        {
            "status": "pass58existing-V195-exact-GT-panels-current-native-display",
            "prior_figures": plan["prior_figures"],
            "exact_GT_panels_checked": panels,
            "native_RGB_channels_checked": channels,
            "new_neural_forwards": 0,
            "new_images_written": 0,
            "source": ref(__file__),
            "scope": "Existing V195 exact-constructed GT crops match two display implementations before V197 figures exist. Real independent references are not read/scored. No quality claim or source/noise draws.",
        },
    )
    print("PASS58existingexactGTpanels/4454400nativechannels/no new images")


if __name__ == "__main__":
    run()
