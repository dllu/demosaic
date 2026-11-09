"""Private, preliminary native views of already-saved V200 outputs; no inference.

Missing EMA crops are omitted, never replaced with fixture or inherited pixels.
Full review/audit/publication remains separate from these selected previews.
"""

from pathlib import Path

import numpy as np
from directional_trial_protocol import REPO, read, ref, save
from lossless_native import load_native
from PIL import Image, ImageDraw, ImageFont
from review_scale_supported_cfa_wave import review_plan, source_guard
from train_scale_supported_cfa_wave import ROOT


def display(value, arrays, d):
    x, y, w, h = d["ROI_xywh"]
    value = value[..., y : y + h, x : x + w].astype(np.float64)
    anchor = np.array(d["anchor"], dtype=np.float64).reshape(1, 3, 1, 1)
    value = anchor + d["contrast"] * (value - anchor)
    linear = np.einsum(
        "bij,bjhw->bihw",
        arrays["matrix"].astype(np.float64),
        value * d["exposure"] * arrays["wb"].astype(np.float64)[..., None, None],
    ).clip(0, 1)
    srgb = np.where(linear <= 0.0031308, linear * 12.92, 1.055 * linear ** (1 / 2.4) - 0.055)
    return np.rint(srgb[0].transpose(1, 2, 0) * 255).astype(np.uint8)


def preview():
    plan = review_plan()
    source_guard(plan)
    out = ROOT / "preliminary-native-preview-v1"
    assert not out.exists()
    prior = REPO / "docs/images/v198-cfa-innovation-wave-v1/manifest-v1.json"
    historical = read(prior)
    fixture = read(ROOT / "viewer-fixture-v1/images/manifest-v1.json")
    # Only choose the fixed six IDs/ROIs; never use the fixture's alias pixels.
    selected = [(i["case"]["id"], i["ROI_xywh"]) for i in fixture["images"]]
    design = read(plan["design"]["path"])["observations"]
    indices = {case["id"]: i for i, case in enumerate(design)}
    audit = read(ROOT / "training-audit-v1.json")
    states = {r["endpoint"]: r for r in audit["checkpoint_states"] if r["step"] == 1000}
    assert set(states) == {"raw", "EMA"}
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    out.mkdir()
    figures, channels = [], 0
    for case_id, roi in selected:
        d = next(
            i
            for i in historical["images"]
            if i["case"]["id"] == case_id and i["ROI_xywh"] == roi and not i["triplet"]
        )
        assert ref(d["image"]["path"]) == d["image"]
        source = np.array(Image.open(d["image"]["path"]).convert("RGB"))
        assert ref(d["case"]["arrays"]["path"]) == d["case"]["arrays"]
        with np.load(d["case"]["arrays"]["path"], allow_pickle=False) as a:
            arrays = {k: a[k] for k in ("wb", "matrix")}
        panels = []

        def copy_panel(panel, *, panels=panels, source=source, d=d):
            x, y, w, h = panel["xywh"]
            assert w == h == 160
            panels.append(
                (
                    panel["label"],
                    source[y : y + h, x : x + w],
                    {
                        "source_figure": d["image"],
                        "source_xywh": panel["xywh"],
                    },
                )
            )

        copy_panel(d["panels"][0])
        inherited = load_native(d["predictions"]["V195-whole-response-EMA"])
        for method in ("V195-whole-response-EMA", "V198-CFA-wave-raw", "V198-CFA-wave-EMA"):
            binding = d["predictions"][method]
            value = load_native(binding)
            crop = display(value, arrays, d)
            p = next(p for p in d["panels"] if p["label"] == method)
            x, y, w, h = p["xywh"]
            np.testing.assert_array_equal(crop, source[y : y + h, x : x + w])
            panels.append((method, crop, {"prediction": binding}))
        available = []
        for endpoint in ("raw", "EMA"):
            method = f"V200-scale-wave-{endpoint}"
            path = ROOT / "artifacts/native" / f"{method}-{indices[case_id]:03d}.native.json"
            if not path.exists():
                continue
            binding = ref(path)
            wave_binding = ref(path.with_name(f"{method}-wave-{indices[case_id]:03d}.native.json"))
            value, wave = load_native(binding), load_native(wave_binding)
            np.testing.assert_array_equal(value, inherited + wave)
            channels += value.size
            panels.append(
                (
                    method,
                    display(value, arrays, d),
                    {
                        "prediction": binding,
                        "wave": wave_binding,
                        "checkpoint_state": states[endpoint],
                    },
                )
            )
            available.append(endpoint)
        assert "raw" in available
        for panel in d["panels"]:
            if panel["label"] == "Exact constructed GT" or panel["label"].startswith("ISO"):
                copy_panel(panel)
        canvas = Image.new("RGB", (8 + 168 * len(panels), 212), "#eeeeee")
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (8, 4),
            f"PRELIMINARY actual saved outputs; full review/audit pending | {case_id}",
            font=font,
            fill="black",
        )
        recorded = []
        for column, (label, crop, provenance) in enumerate(panels):
            x, y = 8 + 168 * column, 44
            draw.text(
                (x, 26),
                label.replace("-whole-response-", " ")
                .replace("-CFA-wave-", " ")
                .replace("-scale-wave-", " "),
                font=font,
                fill="black",
            )
            canvas.paste(Image.fromarray(crop), (x, y))
            recorded.append({"label": label, "xywh": [x, y, 160, 160], **provenance})
        path = out / f"preview-{len(figures):02d}.png"
        canvas.save(path)
        saved = np.array(Image.open(path).convert("RGB"))
        for column, (_, crop, _) in enumerate(panels):
            x = 8 + 168 * column
            np.testing.assert_array_equal(saved[44:204, x : x + 160], crop)
        figures.append(
            {
                "image": ref(path),
                "case": d["case"],
                "ROI_xywh": roi,
                "exposure": d["exposure"],
                "contrast": d["contrast"],
                "anchor": d["anchor"],
                "available_V200_states": available,
                "panels": recorded,
                "no_resize": True,
                "preliminary_full_review_and_audit_pending": True,
            }
        )
    save(
        out / "manifest-v1.json",
        {
            "status": "six-preliminary-actual-saved-native-comparisons-full-quality-pending",
            "source": dict(ref(__file__), text=Path(__file__).read_text()),
            "prior_manifest": ref(prior),
            "training_audit": ref(ROOT / "training-audit-v1.json"),
            "images": figures,
            "native_addition_channels_checked": channels,
            "new_neural_forwards": 0,
            "scope": "Selected preliminary actual saved outputs,not fixture aliases. Missing EMA omitted. "
            "No population-quality or promotion claim;full1644review/audit/viewing remains required. "
            "All native160px source coordinates/transforms identical across methods;real ISO100/JPEG references independent/not exactGT. "
            "No new data/noise,RAW decode,original/dataz access or external writes.",
        },
    )
    print(
        "Wrote6preliminarynativeboards;",
        [(i["case"]["id"], i["available_V200_states"]) for i in figures],
    )


if __name__ == "__main__":
    preview()
