"""Publish and independently check saved V199 gate crops; no neural imports/calls.

Run after the report is ready. Original experiment receipts remain byte-for-byte
copies. Reconstructed PNG panels are checked after saving, using the saved local
basis and whole-context constants. This does not rerun whole-case quality metrics.
"""

import csv
import io
import re
import shutil
import sys
import time
from pathlib import Path

import numpy as np
from directional_trial_protocol import REPO, guard, read, ref, save
from lossless_native import load_native
from phase_admission_protocol import owner_live
from PIL import Image

ROOT = REPO / ".cache/quality-20261108/V199-readout-gate-diagnostic-v1"
PUBLIC = REPO / "docs/results/v199-cfa-gate-diagnostic-v1"
IMAGES = REPO / "docs/images/v199-cfa-gate-diagnostic-v1"
REPORT = REPO / "docs/cfa-wave-gate-diagnostic.md"
GALLERY = REPO / "docs/cfa-wave-gate-diagnostic-gallery.md"
INDEX = REPO / "docs/results/v199-cfa-gate-diagnostic-completed-v1.json"
PROOF = REPO / "docs/results/v199-cfa-gate-diagnostic-publication-verification-v1.json"
DIARY = REPO / "diary/2026-11-08-16-44-30-cfa-wave-gate-diagnostic.md"
FIELDS = [
    "case",
    "state",
    "policy",
    "correction_RMS_DN16",
    "template_gain",
    "full_error_RMS_DN16",
    "scale",
    "effective_maximum_gate_abs",
]


def table_row(row):
    return {
        "case": row["case"],
        "state": row["state"],
        "policy": row["policy"],
        "correction_RMS_DN16": row["whole_correction"]["RMS_DN16"],
        "template_gain": row["metrics"].get("template_gain", ""),
        "full_error_RMS_DN16": row["metrics"].get("full_error_RMS_DN16", ""),
        "scale": row["normalization"]["scale"],
        "effective_maximum_gate_abs": row["effective_maximum_gate_abs"],
    }


def png(path):
    with Image.open(path) as im:
        assert im.mode == "RGB"
        return np.array(im)


def counterfactual_pixels(bundle, endpoint, policy, constants, scale, inherited, d, arrays):
    """Independent crop synthesis; no call to the intervention or render helpers."""
    basis, original = bundle["basis"], bundle["gate_" + endpoint]
    if policy in ("shared-spatial", "shared-spatial-RMS"):
        gate = original.mean(axis=2, keepdims=True, dtype=np.float32)
    elif policy == "color-constant":
        gate = np.array(constants["color"], dtype=np.float32)
    elif policy in ("shared-constant", "shared-constant-RMS"):
        gate = np.array(constants["shared"], dtype=np.float32)
    elif policy == "positive-only":
        gate = np.maximum(original, np.float32(0))
    else:
        raise ValueError(policy)
    correction = (basis * gate).sum(axis=1, dtype=np.float32)
    correction[~np.broadcast_to(bundle["mask"], correction.shape)] = 0
    correction = (correction * scale).astype(np.float32)
    value = (inherited + correction).astype(np.float32)
    center = np.array(d["anchor"], dtype=np.float64).reshape(1, 3, 1, 1)
    value = center + d["contrast"] * (value.astype(np.float64) - center)
    linear = np.einsum(
        "bij,bjhw->bihw",
        arrays["matrix"].astype(np.float64),
        value * d["exposure"] * arrays["wb"].astype(np.float64)[..., None, None],
    ).clip(0, 1)
    srgb = np.where(
        linear <= 0.0031308,
        linear * 12.92,
        1.055 * np.power(linear, 1 / 2.4) - 0.055,
    )
    return np.rint(srgb[0].transpose(1, 2, 0) * 255).astype(np.uint8)


def verify_saved_pixels(plan, result, figures):
    rows = {(r["case"], r["state"], r["policy"]): r for r in result["rows"]}
    observations = {(o["case"], o["state"]): o for o in result["observations"]}
    artifacts = {a["display"]: a for a in result["crop_artifacts"]}
    channels = {"source_panels": 0, "independent_counterfactual_panels": 0, "sheet_pixels": 0}
    for d in plan["displays"]:
        artifact = artifacts[d["index"]]
        assert ref(artifact["arrays"]["path"]) == artifact["arrays"]
        with np.load(artifact["arrays"]["path"], allow_pickle=False) as archive:
            bundle = dict(archive)
        with np.load(d["case"]["arrays"]["path"], allow_pickle=False) as archive:
            arrays = {k: archive[k] for k in ("wb", "matrix")}
        source = png(d["image"]["path"])
        assert ref(d["image"]["path"]) == d["image"]
        x, y, w, h = d["ROI_xywh"]
        assert w == h == 160
        inherited = load_native(artifact["inherited_prediction"])[..., y : y + h, x : x + w]
        for item in [f for f in figures["images"] if f["source_display"] == d["index"]]:
            assert ref(item["image"]["path"]) == item["image"]
            rendered = png(item["image"]["path"])
            assert rendered.shape == (212, 8 + 168 * len(item["panels"]), 3)
            assert item["no_resize"] and item["diagnostic_not_retrained"]
            for key in ("ROI_xywh", "exposure", "contrast", "anchor"):
                assert item[key] == d[key]
            state, case = item["state"], d["case"]["id"]
            assert item["checkpoint"] == plan["checkpoints"][f"V198-CFA-wave-{state}"]
            for i, panel in enumerate(item["panels"]):
                assert panel["xywh"] == [8 + 168 * i, 44, 160, 160]
                if "policy" in panel:
                    row = rows[case, state, panel["policy"]]
                    assert panel["normalization"] == row["normalization"]
                    assert panel["artifact"] == artifact["arrays"]
                    expected = counterfactual_pixels(
                        bundle,
                        state,
                        panel["policy"],
                        observations[case, state]["constants"],
                        row["normalization"]["scale"],
                        inherited,
                        d,
                        arrays,
                    )
                    key = "independent_counterfactual_panels"
                else:
                    assert panel["source_figure"] == d["image"]
                    sx, sy, sw, sh = panel["source_xywh"]
                    assert sw == sh == 160
                    if panel["label"].startswith("Actual V198"):
                        original = next(
                            p for p in d["panels"] if p["label"] == f"V198-CFA-wave-{state}"
                        )
                    else:
                        original = next(p for p in d["panels"] if p["label"] == panel["label"])
                    assert panel["source_xywh"] == original["xywh"]
                    expected = source[sy : sy + sh, sx : sx + sw]
                    key = "source_panels"
                dx, dy, pw, ph = panel["xywh"]
                np.testing.assert_array_equal(rendered[dy : dy + ph, dx : dx + pw], expected)
                channels[key] += expected.size
    for sheet in figures["sheets"]:
        assert ref(sheet["image"]["path"]) == sheet["image"]
        image = png(sheet["image"]["path"])
        for i, index in enumerate(sheet["indices"]):
            original = png(figures["images"][index]["image"]["path"])
            np.testing.assert_array_equal(
                image[212 * i : 212 * (i + 1), : original.shape[1]], original
            )
            channels["sheet_pixels"] += original.size
    assert (
        channels["source_panels"]
        == figures["earlier_noisy_anchor_actual_reference_channels_copied"]
    )
    assert (
        channels["independent_counterfactual_panels"]
        == figures["counterfactual_RGB_channels_independently_displayed"]
    )
    assert channels["source_panels"] + channels["independent_counterfactual_panels"] == 32_256_000
    return channels


def main():
    assert "torch" not in sys.modules
    assert not any(p.exists() for p in (PUBLIC, IMAGES, GALLERY, INDEX, PROOF))
    plan, result, figures = [
        read(ROOT / n) for n in ("plan-v1.json", "result-v1.json", "figures-v1.json")
    ]
    guard(plan)
    assert not owner_live(result["owner"])
    assert result["owner"] == read(ROOT / "run-launch-v1.json")["owner"]
    assert result["plan"] == ref(ROOT / "plan-v1.json")
    assert figures["plan"] == result["plan"] and figures["result"] == ref(ROOT / "result-v1.json")
    audit = read(ROOT / "audit-v1.json")
    assert audit["status"].startswith("pass-saved19native") and audit["result"] == figures["result"]
    viewed = read(ROOT / "native-viewing-completion-v1.json")
    assert viewed["figures"] == ref(ROOT / "figures-v1.json")
    assert viewed["journal"] == ref(ROOT / "native-viewing-v1.jsonl")
    assert viewed["sheets"] == list(range(12)) and viewed["indices"] == list(range(46))
    assert "21 passed" in Path(plan["CPU_tests"]["path"]).read_text()
    assert len(plan["all105_neural_hashes"]) == 105
    for name, digest in plan["all105_neural_hashes"].items():
        assert ref(REPO / "src/demosaic" / name)["sha256"] == digest
    checks = verify_saved_pixels(plan, result, figures)
    # Copy only after the existing saved panels pass. Do not re-render science.
    PUBLIC.mkdir()
    IMAGES.mkdir()
    evidence = []
    names = [
        "plan-v1.json",
        "result-v1.json",
        "audit-v1.json",
        "figures-v1.json",
        "events-v1.jsonl",
        "run-launch-v1.json",
        "run-v1.log",
        "audit-v1.log",
        "render-v1.log",
        "native-viewing-v1.jsonl",
        "native-viewing-completion-v1.json",
        "record-viewing-worker-v1.py",
    ]
    for name in names:
        source, target = ROOT / name, PUBLIC / name
        shutil.copyfile(source, target)
        assert ref(source)["sha256"] == ref(target)["sha256"]
        evidence.append({"original": ref(source), "public": ref(target)})
    tests = PUBLIC / "CPU-tests-v1.log"
    shutil.copyfile(plan["CPU_tests"]["path"], tests)
    assert ref(tests)["sha256"] == plan["CPU_tests"]["sha256"]
    evidence.append({"original": plan["CPU_tests"], "public": ref(tests)})
    images = []
    for item in figures["images"]:
        source = Path(item["image"]["path"])
        target = IMAGES / source.name
        shutil.copyfile(source, target)
        assert ref(target)["sha256"] == item["image"]["sha256"]
        images.append({**item, "original_image": item["image"], "image": ref(target)})
    save(
        IMAGES / "manifest-v1.json",
        {
            "status": "published46-native-diagnostic-figures-not-retrained-models",
            "original": ref(ROOT / "figures-v1.json"),
            "images": images,
            "no_resize": True,
            "checkpoints": plan["checkpoints"],
            "scope": figures["scope"],
        },
    )
    text = io.StringIO(newline="")
    writer = csv.DictWriter(text, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(table_row(r) for r in result["rows"])
    table = PUBLIC / "metrics-v1.csv"
    with table.open("x", newline="") as stream:
        stream.write(text.getvalue())
    with table.open(newline="") as stream:
        written = list(csv.DictReader(stream))
    assert written == [{k: str(v) for k, v in table_row(r).items()} for r in result["rows"]]
    gallery = [
        "# V199 native gate diagnostic gallery",
        "",
        (
            "[Findings and method](cfa-wave-gate-diagnostic.md). These are fixed-head interventions, not newly trained models. "
            "All panels retain 160×160 native pixels. Open the linked PNG at 100% to inspect pixels. "
            "ISO100/AHD/JPEG references are independent captures, not exact GT. "
            "RMS-matched controls can exceed the trained gate bound and are diagnostic only."
        ),
        "",
        (
            "[Full checkpoint, noise, source, ROI and transform metadata](images/v199-cfa-gate-diagnostic-v1/manifest-v1.json). "
            "Each board uses noisy → V195 → actual → shared spatial → shared spatial RMS → color constant → "
            "shared constant → shared constant RMS → positive-only → reference(s)."
        ),
        "",
    ]
    for i, item in enumerate(images):
        name = Path(item["image"]["path"]).name
        title = f"{i:02d}: {item['case']['id']} / {item['state']}"
        gallery += [
            f"## {title}",
            "",
            f"ROI `{item['ROI_xywh']}`, exposure {item['exposure']:.9g}, contrast {item['contrast']:g}; "
            + (
                "noisy/restored/reference triplet."
                if item["triplet"]
                else "all seven gate policies."
            ),
            "",
            f"![{title}](images/v199-cfa-gate-diagnostic-v1/{name})",
            "",
        ]
    GALLERY.write_text("\n".join(gallery))
    for path in (REPORT, DIARY):
        assert path.is_file() and path.stat().st_size > 1000
    links = 0
    for document in (REPORT, GALLERY, DIARY):
        for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", document.read_text()):
            target = (document.parent / match[1].split("#")[0]).resolve()
            assert target.is_file() or target in (INDEX, PROOF), (document, target)
            links += 1
    save(
        INDEX,
        {
            "status": "completed-viewed-fixed14context-gate-diagnostic-not-quality-promotion",
            "created_unix_UTC": time.time(),
            "plan": ref(ROOT / "plan-v1.json"),
            "result": ref(ROOT / "result-v1.json"),
            "audit": ref(ROOT / "audit-v1.json"),
            "owner_terminal": {"owner": result["owner"], "terminal": True},
            "checkpoints": plan["checkpoints"],
            "all105_neural_hashes_unchanged": plan["all105_neural_hashes"],
            "public_evidence": evidence,
            "table": ref(table),
            "table_rows": len(written),
            "native_manifest": ref(IMAGES / "manifest-v1.json"),
            "report": ref(REPORT),
            "gallery": ref(GALLERY),
            "diary": ref(DIARY),
            "publisher": ref(__file__),
            "postsave_independent_RGB_channel_checks": checks,
            "scope": plan["scope"],
            "local_document_links_checked": links,
        },
    )
    # Verify exported copies and document/image links after writing them.
    index = read(INDEX)
    for item in images:
        assert ref(item["image"]["path"]) == item["image"]
    for binding in [index[k] for k in ("table", "report", "gallery", "diary", "native_manifest")]:
        assert ref(binding["path"]) == binding
    assert not owner_live(result["owner"]) and "torch" not in sys.modules
    save(
        PROOF,
        {
            "status": "pass-V199-postsave46figures-420nativepanels-no-neural-calls",
            "created_unix_UTC": time.time(),
            "publication": ref(INDEX),
            "source": ref(__file__),
            "private_and_public_images_byte_identical": 46,
            "native_triplets": 8,
            "viewed_sheets": 12,
            "postsave_independent_RGB_channel_checks": checks,
            "table_rows_source_checked": len(written),
            "neural_sources_unchanged": 105,
            "torch_imported": False,
            "new_neural_forwards": 0,
            "scope": "Reconstruct saved crop interventions and verify every PNG panel and sheet after save; "
            "original whole-case counterfactual metrics remain source-bound single-pass, not independently rerun. "
            "Preselected failure/control contexts are not population-quality evidence. No retraining/promotion claim.",
        },
    )
    assert INDEX.is_file() and PROOF.is_file()
    print("PASS46figures/420nativepanels/32256000RGBchannels/196table rows;published diagnostic")


if __name__ == "__main__":
    main()
