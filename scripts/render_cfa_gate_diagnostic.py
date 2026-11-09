"""Native diagnostic gate boards, with real references explicitly non-exact."""

import numpy as np
from diagnose_cfa_wave_gates import ROOT
from directional_trial_protocol import guard, read, ref, save
from lossless_native import load_native
from PIL import Image, ImageDraw, ImageFont
from readout_gate_interventions import POLICIES, local_intervention
from report_checkpoint_pilot import pixels
from report_late_spectral_mixed_quiet import independent_display

LABELS = {
    "actual": "Actual V198",
    "shared-spatial": "Shared spatial",
    "shared-spatial-RMS": "Shared spatial RMS",
    "color-constant": "Color constant",
    "shared-constant": "Shared constant",
    "shared-constant-RMS": "Shared constant RMS",
    "positive-only": "Positive only",
}


def render():
    plan = read(ROOT / "plan-v1.json")
    guard(plan)
    assert ref(__file__) == plan["renderer"]
    assert read(ROOT / "audit-v1.json")["status"].startswith("pass-saved19native")
    result = read(ROOT / "result-v1.json")
    observations = {(o["case"], o["state"]): o for o in result["observations"]}
    rows = {(r["case"], r["state"], r["policy"]): r for r in result["rows"]}
    bundles = {r["display"]: r for r in result["crop_artifacts"]}
    out = ROOT / "figures-v1"
    out.mkdir()
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    images = []
    display_channels = source_channels = 0
    for display in plan["displays"]:
        case_id = display["case"]["id"]
        artifact = bundles[display["index"]]
        assert ref(artifact["arrays"]["path"]) == artifact["arrays"]
        with np.load(artifact["arrays"]["path"], allow_pickle=False) as archive:
            bundle = dict(archive)
        assert ref(display["image"]["path"]) == display["image"]
        source = np.asarray(Image.open(display["image"]["path"]).convert("RGB"))
        with np.load(display["case"]["arrays"]["path"], allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in ["wb", "matrix"]}
        x, y, w, h = display["ROI_xywh"]
        inherited = load_native(artifact["inherited_prediction"])[..., y : y + h, x : x + w]
        anchor = np.asarray(display["anchor"], dtype=np.float64).reshape(1, 3, 1, 1)
        references = [
            p
            for p in display["panels"]
            if p["label"] == "Exact constructed GT" or p["label"].startswith("ISO")
        ]
        for state in ["raw", "EMA"]:
            o = observations[case_id, state]

            def make(
                selections,
                triplet=False,
                *,
                case_id=case_id,
                state=state,
                display=display,
                bundle=bundle,
                o=o,
                inherited=inherited,
                anchor=anchor,
                arrays=arrays,
                source=source,
                artifact=artifact,
            ):
                nonlocal display_channels, source_channels
                canvas = Image.new("RGB", (8 + 168 * len(selections), 212), "#eeeeee")
                draw = ImageDraw.Draw(canvas)
                draw.text(
                    (8, 4),
                    f"DIAGNOSTIC, not retrained | {case_id} | {state} | exposure{display['exposure']:g},contrast{display['contrast']:g}",
                    font=font,
                    fill="black",
                )
                panels = []
                for col, selection in enumerate(selections):
                    dx, dy = 8 + 168 * col, 44
                    if isinstance(selection, str) and selection != "actual":
                        row = rows[case_id, state, selection]
                        wave = local_intervention(
                            bundle, state, selection, o["constants"], row["normalization"]["scale"]
                        )
                        value = inherited + wave
                        transformed = anchor + display["contrast"] * (
                            value.astype(np.float64) - anchor
                        )
                        crop = pixels(transformed, arrays, [0, 0, 160, 160], display["exposure"])
                        np.testing.assert_array_equal(
                            crop,
                            independent_display(
                                transformed, arrays, [0, 0, 160, 160], display["exposure"]
                            ),
                        )
                        label = LABELS[selection]
                        provenance = {
                            "policy": selection,
                            "normalization": row["normalization"],
                            "artifact": artifact["arrays"],
                        }
                        display_channels += crop.size
                    else:
                        panel = (
                            next(
                                p
                                for p in display["panels"]
                                if p["label"] == f"V198-CFA-wave-{state}"
                            )
                            if selection == "actual"
                            else selection
                        )
                        sx, sy, pw, ph = panel["xywh"]
                        assert pw == ph == 160
                        crop = source[sy : sy + ph, sx : sx + pw].copy()
                        source_channels += crop.size
                        label = (
                            LABELS["actual"] + " " + state
                            if selection == "actual"
                            else panel["label"]
                        )
                        provenance = {
                            "source_figure": display["image"],
                            "source_xywh": panel["xywh"],
                        }
                    assert crop.shape == (160, 160, 3)
                    draw.text((dx, 26), label, font=font, fill="black")
                    canvas.paste(Image.fromarray(crop), (dx, dy))
                    panels.append({"label": label, "xywh": [dx, dy, 160, 160], **provenance})
                path = out / f"comparison-{len(images):02d}.png"
                canvas.save(path)
                images.append(
                    {
                        "image": ref(path),
                        "source_display": display["index"],
                        "case": display["case"],
                        "state": state,
                        "checkpoint": plan["checkpoints"][f"V198-CFA-wave-{state}"],
                        "ROI_xywh": display["ROI_xywh"],
                        "exposure": display["exposure"],
                        "contrast": display["contrast"],
                        "anchor": display["anchor"],
                        "panels": panels,
                        "triplet": triplet,
                        "no_resize": True,
                        "diagnostic_not_retrained": True,
                    }
                )

            make(
                [
                    display["panels"][0],
                    next(p for p in display["panels"] if p["label"] == "V195-whole-response-EMA"),
                    *POLICIES,
                    *references,
                ]
            )
            if display["index"] in [0, 4]:
                for policy in ["actual", "shared-spatial-RMS"]:
                    make([display["panels"][0], policy, references[0]], triplet=True)
    assert len(images) == 46 and sum(x["triplet"] for x in images) == 8
    sheets = []
    for start in range(0, len(images), 4):
        group = images[start : start + 4]
        canvas = Image.new(
            "RGB",
            (max(Image.open(x["image"]["path"]).width for x in group), 212 * len(group)),
            "#eeeeee",
        )
        for index, item in enumerate(group):
            canvas.paste(Image.open(item["image"]["path"]), (0, 212 * index))
        path = out / f"sheet-{len(sheets):02d}.png"
        canvas.save(path)
        sheets.append(
            {
                "indices": list(range(start, start + len(group))),
                "image": ref(path),
                "no_resize": True,
            }
        )
    save(
        ROOT / "figures-v1.json",
        {
            "status": "rendered46native-gate-diagnostic-figures-awaiting-viewing",
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "images": images,
            "sheets": sheets,
            "native_figures": 46,
            "native_triplets": 8,
            "no_resize": True,
            "counterfactual_RGB_channels_independently_displayed": display_channels,
            "earlier_noisy_anchor_actual_reference_channels_copied": source_channels,
            "new_neural_forwards": 0,
            "source": ref(__file__),
            "scope": "Fixed-measurement gate interventions,not retrained models. Actual V198/noisy/reference panels copied byte-for-byte;counterfactuals use shared source coordinates/transforms. RMS controls may exceed trained gate bounds. Real ISO100/AHD/JPEG references are independent,not exactGT. No promotion/population-quality claim.",
        },
    )
    print("Rendered46nativefigures/8triplets/12sheets; actual viewing pending")


if __name__ == "__main__":
    render()
