"""Bundle verified native report assets without resizing, inference or promotion."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
from build_native_crop_board import case_key, identity, read_crop
from close_directional_bank_review import STAGES, TERMINAL, alive
from PIL import Image
from review_directional_bank import require_completed
from train_directional_interval_trial import guard, read, ref, save

from demosaic.safety import writable_path

KINDS = {
    "full427": "synthetic",
    "known": "camera",
    "unseen": "camera",
    "gfx": "gfx",
    "analytic": "analytic",
    "hue": "hue",
    "hue-extra": "hue",
    "highlights": "highlights",
}


def checked_reference(item):
    if ref(item["path"]) != item:
        raise ValueError("Report input checksum changed")
    return Path(item["path"])


def validate_board(receipt_ref):
    """Recheck every shared cell and every original triplet's source metadata."""
    receipt_path = checked_reference(receipt_ref)
    board = read(receipt_path)
    checked_reference(board["board"])
    for report in board["reports"]:
        checked_reference(report)
    sources = {}
    for entry in board["source_triplets"]:
        report = Path(board["reports"][entry["report_index"]]["path"])
        parts, _, original = read_crop(report, entry["crop"], board["kind"])
        if original != entry["image"]:
            raise ValueError("Triplet source identity differs from board receipt")
        identity(entry["crop"])
        for panel, part in zip(entry["crop"]["panels"], parts, strict=True):
            sources[(original["path"], tuple(panel["png_xywh"]))] = (original["sha256"], part)
    with Image.open(board["board"]["path"]) as image:
        pixels = np.asarray(image).copy()
    for cell in board["cells"]:
        digest, source = sources[(cell["image"]["path"], tuple(cell["source_xywh"]))]
        x, y, w, h = cell["board_xywh"]
        _a, _b, u, v = cell["source_xywh"]
        actual = pixels[y : y + h, x : x + w]
        if (
            (w, h, u, v) != (160,) * 4
            or actual.shape != (160, 160, 3)
            or digest != cell["image"]["sha256"]
            or not np.array_equal(actual, source)
            or hashlib.sha256(actual.tobytes()).hexdigest() != cell["pixel_sha256"]
        ):
            raise ValueError("Native board cell differs from its original pixels")
    if len(board["cells"]) != board["native_cells_exact"]:
        raise ValueError("Board cell coverage is incomplete")
    return board


def bundle(closure, reference_receipt, checkpoints, output, *, purpose):
    """Create a crop section and index; actual visual/numerical review stays pending."""
    boards = {b["panel"]: b["receipt"] for b in closure["boards"]}
    boards.update({b["panel"]: b["receipt"] for b in reference_receipt["boards"]})
    if set(boards) != set(KINDS):
        raise ValueError("Expected all eight complete native review boards")
    if len(checkpoints) != 2 or len({c["sha256"] for c in checkpoints}) != 2:
        raise ValueError("Expected two distinct final checkpoints")
    verified = {panel: validate_board(item) for panel, item in boards.items()}
    for checkpoint in checkpoints:
        if ref(checkpoint["path"])["sha256"] != checkpoint["sha256"]:
            raise ValueError("Final checkpoint changed after evaluation")
    for panel, board in verified.items():
        if board["kind"] != KINDS[panel]:
            raise ValueError("Native board kind differs from its panel")
        for checkpoint in checkpoints:
            if not any(
                identity(e["crop"])[1] == checkpoint["sha256"] for e in board["source_triplets"]
            ):
                raise ValueError("A final checkpoint is absent from a native board")
    output = writable_path(output)
    if output.exists():
        raise ValueError("Choose a new report-assets directory")
    output.mkdir(parents=True)
    executed_source = output / "executed-source.py"
    shutil.copyfile(__file__, executed_source)
    assets = output / "images"
    assets.mkdir()
    selected = []
    lines = [
        "# Native crop section for the completed review",
        "",
        purpose,
        "",
        "Crop package only. Numerical interpretation and actual visual review remain required.",
        "All crop panels retain native160×160 pixels. PNGs are RGB8 viewing copies; metrics use unquantized predictions.",
        "Full white balance, camera matrix, CFA, source checksums and reference descriptions are in [the asset index](index.json).",
        "",
    ]
    common = {}
    for index, checkpoint in enumerate(checkpoints):
        lines += [
            f"## {checkpoint['label']}",
            "",
            f"Checkpoint SHA256: `{checkpoint['sha256']}`.",
            "",
        ]
        for panel, kind in (("full427", "synthetic"), ("gfx", "gfx")):
            board = verified[panel]
            chosen = [
                e
                for e in board["source_triplets"]
                if identity(e["crop"])[1] == checkpoint["sha256"]
            ]
            expected = 2 if kind == "synthetic" else 4
            if (
                len(chosen) != expected
                or len({case_key(e["crop"], kind) for e in chosen}) != expected
            ):
                raise ValueError("Missing or duplicate required model/crop cases")
            if kind == "gfx" and {e["crop"]["region"]["name"] for e in chosen} != {
                "overcast-sky",
                "building-detail",
                "foliage",
                "chain-link-fence",
            }:
                raise ValueError("Missing standing GFX sky/building/foliage/fence coverage")
            for entry in chosen:
                crop = entry["crop"]
                report = Path(board["reports"][entry["report_index"]]["path"])
                parts, settings, png = read_crop(report, crop, kind)
                key = (kind, case_key(crop, kind))
                if key in common:
                    previous = common[key]
                    if (
                        settings != previous[0]
                        or not np.array_equal(parts[0], previous[1])
                        or not np.array_equal(parts[2], previous[2])
                    ):
                        raise ValueError(
                            "Methods differ in source/ROI/noise/display or noisy/reference pixels"
                        )
                else:
                    common[key] = (settings, parts[0], parts[2])
                name = crop["source_id"][:12] if kind == "synthetic" else crop["region"]["name"]
                target = assets / f"model-{index}-{panel}-{name}.png"
                shutil.copyfile(png["path"], target)
                if target.read_bytes() != Path(png["path"]).read_bytes():
                    raise ValueError("Report PNG copy changed bytes")
                label = (
                    "Noisy / restored / exact synthetic GT"
                    if kind == "synthetic"
                    else "Noisy / restored / independent ISO100 reference (not GT)"
                )
                lines += [f"![{checkpoint['label']}: {label}](images/{target.name})", ""]
                condition = crop.get("condition", crop.get("conditioning"))
                roi = crop.get("displayed_cache_ROI_xywh", crop.get("region"))
                lines += [
                    f"Source/ROI: `{json.dumps(roi, sort_keys=True)}`; noise/conditioning: `{json.dumps(condition, sort_keys=True)}`; display exposure ×{crop['display_exposure']}.",
                    "",
                ]
                if kind == "synthetic":
                    source = crop["source"]
                    lines += [
                        f"Source [{source['title']}]({source['page_url']}), {source['author']}; [{source['license']}]({source['license_url']}). Binned, cropped, simulated noise and restoration.",
                        "",
                    ]
                else:
                    lines += [
                        "DSCF3879 ISO6400 and independently demosaiced DSCF3880 ISO100 differ in aperture, exposure time and moving subjects. The ISO100 image is a qualitative reference, not a pixelwise scoring target.",
                        "",
                    ]
                selected.append(
                    {
                        "checkpoint": checkpoint,
                        "panel": panel,
                        "case": case_key(crop, kind),
                        "asset": ref(target),
                        "original_PNG": png,
                        "metadata": crop,
                    }
                )
    final_boards = []
    for panel, board in verified.items():
        target = assets / (panel + "-all-methods-native.png")
        shutil.copyfile(board["board"]["path"], target)
        if ref(target)["sha256"] != board["board"]["sha256"]:
            raise ValueError("Copied native board changed")
        final_boards.append(
            {
                "panel": panel,
                "asset": ref(target),
                "original_receipt": boards[panel],
                "native_cells": board["native_cells_exact"],
                "triplets": len(board["source_triplets"]),
            }
        )
    (output / "crops.md").write_text("\n".join(lines) + "\n")
    save(
        output / "index.json",
        {
            "status": "prepared-native-report-assets-manual-review-pending",
            "purpose": purpose,
            "driver": ref(executed_source),
            "checkpoints": checkpoints,
            "selected_triplets": selected,
            "all_boards": final_boards,
            "native_cells_verified": sum(x["native_cells"] for x in final_boards),
            "source_triplets_verified": sum(x["triplets"] for x in final_boards),
            "crop_section": ref(output / "crops.md"),
            "manual_review_completed": False,
            "quality_decision": None,
            "scope": "Verbatim native PNG copies with complete source/ROI/noise/display/checkpoint/reference metadata. No inference, resampling, numerical performance calculation, manual-view claim, README update or promotion.",
        },
    )
    return output / "index.json"


def main(plan_path, output):
    plan = read(plan_path)
    guard(plan)
    require_completed(plan)
    root = Path(plan["root"])
    queue = read(root / "queue-launch.json")
    if any(alive(queue[k]) for k in ("review_owner", "closure_owner", "reference_owner")):
        raise RuntimeError("All review/closure/reference owners must exit before packaging")
    state = read(root / "status.json")
    if (
        state["controller"] != queue["review_owner"]
        or state["status"] != TERMINAL
        or set(state["completed"]) != STAGES
        or len(state["completed"]) != len(STAGES)
    ):
        raise ValueError("Review is not the exact complete queued review")
    closure = read(root / "closure-result.json")
    if (
        closure["status"]
        != "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review"
    ):
        raise ValueError("CPU closure is incomplete")
    closure_status = read(root / "closure-status.json")
    if (
        closure_status["controller"] != queue["closure_owner"]
        or closure_status["status"] != closure["status"]
    ):
        raise ValueError("CPU closure belongs to a different owner or failed")
    if checked_reference(closure["review_terminal"]) != root / "status.json":
        raise ValueError("Closure belongs to another review")
    reference = read(Path(plan["work"]) / "outputs/reference-closure/receipt.json")
    if (
        reference["status"]
        != "prepared-directional-working-reference-boards-awaiting-manual-review"
    ):
        raise ValueError("Working reference supplement is incomplete")
    boundary = read(root / "training-boundary.json")
    checkpoints = boundary["checkpoints"]
    if [c["label"] for c in checkpoints] != ["V80-original4000", "V81-original4000"]:
        raise ValueError("Expected completed V80/V81 boundaries")
    result = bundle(
        closure,
        reference,
        checkpoints,
        output,
        purpose="Actual completed V80/V81 output crops; actual visual review and full performance report still required.",
    )
    guard(plan)
    print({"report_assets": ref(result)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-plan", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.review_plan.absolute(), args.output)
