"""Small native README triplets copied exactly from the audited real boards."""

import time

import numpy as np
from directional_trial_protocol import read, ref, save
from PIL import Image, ImageDraw, ImageFont
from publish_cfa_innovation_wave import EVIDENCE, IMAGES


def run():
    manifest = read(IMAGES / "manifest-v1.json")
    assert manifest["fixture"] is False and manifest["native_figures"] == 60
    specifications = [
        (
            "main-building-detail",
            [176, 176, 160, 160],
            "readme-building-v1.png",
            "Building detail",
        ),
        ("mesh-nominal", [426, 189, 160, 160], "readme-cab-v1.png", "Fine cab mesh"),
    ]
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    images = []
    channels = 0
    for case_id, roi, name, title in specifications:
        old = next(
            b
            for b in manifest["images"]
            if b["case"]["id"] == case_id
            and b["ROI_xywh"] == roi
            and not b["triplet"]
            and b["contrast"] == 1
        )
        assert ref(old["image"]["path"]) == old["image"]
        source = Image.open(old["image"]["path"]).convert("RGB")
        canvas = Image.new("RGB", (512, 212), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (8, 4), f"{title} | native160px | exposure{old['exposure']:g}", font=font, fill="black"
        )
        panels = []
        for column, (label, short) in enumerate(
            [
                (old["panels"][0]["label"], "Noisy Malvar"),
                ("V198-CFA-wave-EMA", "CFA EMA"),
                ("ISO100 AHD, not GT", "ISO100 AHD, not GT"),
            ]
        ):
            panel = next(p for p in old["panels"] if p["label"] == label)
            x, y, w, h = panel["xywh"]
            assert w == h == 160
            dx, dy = 8 + 168 * column, 44
            draw.text((dx, 26), short, font=font, fill="black")
            canvas.paste(source.crop((x, y, x + w, y + h)), (dx, dy))
            panels.append(
                {"label": label, "source_xywh": panel["xywh"], "xywh": [dx, dy, 160, 160]}
            )
        path = IMAGES / name
        assert not path.exists()
        canvas.save(path)
        actual = np.asarray(Image.open(path).convert("RGB"))
        original = np.asarray(source)
        for panel in panels:
            x, y, w, h = panel["source_xywh"]
            dx, dy, _, _ = panel["xywh"]
            np.testing.assert_array_equal(
                actual[dy : dy + h, dx : dx + w], original[y : y + h, x : x + w]
            )
            channels += w * h * 3
        images.append(
            {
                "image": ref(path),
                "source_figure": old["image"],
                "case": old["case"],
                "ROI_xywh": roi,
                "exposure": old["exposure"],
                "contrast": old["contrast"],
                "anchor": old["anchor"],
                "panels": panels,
                "checkpoint": manifest["method_checkpoints"]["V198-CFA-wave-EMA"],
                "reference_role": "Independent ISO100 AHD qualitative reference,not exactGT;aperture/exposure/motion differ",
                "no_resize": True,
            }
        )
    assert len(images) == 2 and channels == 460800
    save(
        EVIDENCE / "representative-figures-v1.json",
        {
            "status": "pass-two-native-real-README-triplets-exact-core-panel-copies",
            "created_unix_UTC": time.time(),
            "source": ref(__file__),
            "core_manifest": ref(IMAGES / "manifest-v1.json"),
            "images": images,
            "RGB_channels_exact_source_copy": channels,
            "new_neural_forwards": 0,
            "new_source_noise_draws": 0,
            "scope": "Three160px native cells each;copy originalPNG panelpixels withoutresize,recoloringor newinference. Corepanelsalreadyindependentlydisplaychecked;actualviewingandqualityinterpretationremainseparate. SamecabandbuildingROIsasV197;realreferenceisnotexactGT.",
        },
    )
    print("PASS2nativeREADMEtriplets/460800exact-sourceRGBchannels")


if __name__ == "__main__":
    run()
