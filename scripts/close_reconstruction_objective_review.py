"""Queue CPU-only color arithmetic and native boards after the exact review exits."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

import psutil

TERMINAL = "completed-objective-inference-awaiting-statistical-and-manual-native-closure"
STAGES = {"boundary", "known", "unseen", "full427", "statistics", "sensitivity",
          "gfx", "analytic", "hue", "highlights"}


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def ref(path):
    return {"path": str(Path(path).absolute()), "sha256": sha(path)}


def read(path):
    return json.loads(Path(path).read_text())


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def ready(status, owner):
    if status["controller"] != owner:
        raise RuntimeError("Review owner identity differs")
    if status["status"].startswith("failed-"):
        raise RuntimeError("Review failed; no automatic closure/retry")
    if alive(owner):
        return False
    if status["status"] != TERMINAL:
        raise RuntimeError("Review exited without complete inference")
    if set(status["completed"]) != STAGES or len(status["completed"]) != len(STAGES):
        raise RuntimeError("Review stages are incomplete")
    return not alive(status["child"])


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def main(plan_path):
    os.nice(10)
    plan = read(plan_path)
    root = Path(plan["root"])
    assert ref(__file__) == plan["worker"]
    assert ref(plan["review_plan"]["path"]) == plan["review_plan"]
    with (root / "closure.claim").open("x") as stream:
        stream.write(str(psutil.Process().pid))
    status = {"controller": {"pid": psutil.Process().pid,
                             "created": psutil.Process().create_time()},
              "plan": ref(plan_path), "completed": []}
    def record(stage, **values):
        status.update(status=stage, updated_unix=time.time(), **values)
        save(root / "closure-status.json", status)
        print(json.dumps({"status": stage}), flush=True)
    try:
        record("waiting-for-exact-objective-review-owner-exit")
        review = read(plan["review_plan"]["path"])
        while not ready(read(Path(review["root"]) / "status.json"), plan["review_owner"]):
            time.sleep(5)
        sys.path[:0] = [str(Path(review["work"]) / p) for p in ("scripts", "src")]
        import torch
        from audit_analytic_summary import main as analytic_audit
        from audit_color_grid_summary import main as summary_audit
        from audit_saved_color_flats import main as case_audit
        from build_native_crop_board import build
        from train_reconstruction_objective_trial import guard

        torch.set_num_threads(2)
        assert not torch.cuda.is_initialized()
        assert psutil.virtual_memory().available > 24 * 2**30
        guard(review)
        out = Path(review["work"]) / "outputs/closure"
        out.mkdir(parents=True, exist_ok=False)
        outputs = {key: Path(value) for key, value in review["outputs"].items()}
        record("auditing-saved-hue-predictions-and-native-renders")
        hue = outputs["hue"] / "report.json"
        case_audit(hue, out / "hue-cases", plan["extra_palettes"])
        report = read(out / "hue-cases/audit.json")
        assert report["observations"] == 1176 and report["float_predictions"] == 3528
        status["completed"].append("hue-case-array-metrics-and-native-renders")
        record("auditing-hue-summary-and-analytic-arithmetic")
        summary_audit(hue, out / "hue-cases/audit.json", out / "hue-summary-audit.json")
        analytic_audit(outputs["analytic"], out / "analytic-audit.json", candidates=2)
        status["completed"].extend(["hue-summary", "analytic-summary"])
        record("checking-previously-viewed-photo-and-camera-crops-after-producer-exit")
        photo = read(root / "early-photo-native/report.json")
        for crop in photo["native_crops"]:
            for key in ("native_source_png", "native_source_metadata"):
                item = crop["model"][key]
                assert ref(item["path"]) == item
        camera = read(root / "camera-native/manual-view.json")
        for item in camera["unchanged_source_PNGs_rechecked"]:
            assert ref(item["path"]) == item
        for board in camera["boards"]:
            assert ref(board["report"]["path"]) == board["report"]
            for crop in read(board["report"]["path"])["native_crops"]:
                item = crop["model"]["original_crop"]
                assert ref(item["path"]) == item
        view_refs = [ref(root / p) for p in (
            "early-photo-native/manual-view.json", "camera-native/manual-view.json")]
        status["completed"].append("early-photo-camera-source-pixels-unchanged")
        record("building-remaining-native-boards-without-resampling")
        boards = []
        for panel, filename, kind in [("gfx", "report.json", "gfx"),
                                      ("analytic", "summary.json", "analytic"),
                                      ("hue", "report.json", "hue"),
                                      ("highlights", "report.json", "highlights")]:
            result = build([outputs[panel] / filename], out / (panel + "-native.png"), kind)
            boards.append({"panel": panel, "board": result["board"],
                           "receipt": ref(out / (panel + "-native.json")),
                           "native_cells": result["native_cells_exact"]})
        extra = out / "hue-extra-native"
        extra.mkdir()
        for crop in report["additional_native_crops"]:
            source = out / "hue-cases" / crop["image"]
            assert sha(source) == crop["png_sha256"]
            shutil.copyfile(source, extra / source.name)
        save(extra / "report.json", {"native_crops": report["additional_native_crops"],
                                     "scope": "Same fixed additional palettes from saved arrays."})
        result = build([extra / "report.json"], out / "hue-extra-native.png", "hue")
        boards.append({"panel": "hue-extra", "board": result["board"],
                       "receipt": ref(out / "hue-extra-native.json"),
                       "native_cells": result["native_cells_exact"]})
        status["completed"].append("remaining-native-boards-created")
        assert not torch.cuda.is_initialized()
        guard(review)
        result = {"status": "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review",
                  "closure_plan": ref(plan_path), "review_terminal": ref(root / "status.json"),
                  "hue_cases": ref(out / "hue-cases/audit.json"),
                  "hue_summary": ref(out / "hue-summary-audit.json"),
                  "analytic_summary": ref(out / "analytic-audit.json"),
                  "previous_native_views_revalidated": view_refs, "boards": boards,
                  "CUDA_initialized": False,
                  "scope": "No new model inference, noise or image selection. CPU-only independent "
                  "saved-array/color/analytic arithmetic and exact native PNG rearrangement. Four extra "
                  "palettes were declared before new hue outputs existed. All new boards still require "
                  "actual manual review and full quality/continuation decision; no promotion."}
        save(root / "closure-result.json", result)
        record(result["status"], result=ref(root / "closure-result.json"))
    except BaseException as error:
        record("failed-CPU-objective-closure-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
