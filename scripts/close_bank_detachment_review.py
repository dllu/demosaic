"""Audit saved arrays and build native V82/V83 boards; actual viewing stays pending."""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

import psutil
from close_directional_bank_review import native_report, read, ready, ref, save, sha


def main(plan_path, *, historical_criteria=None):
    os.nice(10)
    plan = read(plan_path)
    root = Path(plan["root"])
    historical = plan.get("historical_replay", False)
    assert historical is (historical_criteria is not None)
    for path, digest in plan["frozen_files"].items():
        assert sha(path) == digest, path
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    assert ref(__file__) == plan["worker"]
    assert ref(plan["review_plan"]["path"]) == plan["review_plan"]
    for item in plan["retained_native_reports"].values():
        assert ref(item["path"]) == item
    with (root / "closure.claim").open("x") as stream:
        stream.write(str(psutil.Process().pid))
    status = {
        "controller": {"pid": psutil.Process().pid, "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": [],
    }

    def record(stage, **values):
        status.update(status=stage, updated_unix=time.time(), **values)
        save(root / "closure-status.json", status)
        print(json.dumps({"status": stage}), flush=True)

    try:
        record("waiting-for-exact-directional-bank-review-owner-exit")
        review = read(plan["review_plan"]["path"])
        while not ready(read(Path(review["root"]) / "status.json"), plan["review_owner"]):
            time.sleep(5)
        sys.path[:0] = [str(Path(review["work"]) / p) for p in ("scripts", "src")]
        import torch
        from audit_analytic_summary import main as analytic_audit
        from audit_color_grid_summary import main as summary_audit
        from audit_saved_color_flats import main as case_audit
        from build_native_crop_board import build
        from train_directional_interval_trial import guard

        torch.set_num_threads(2)
        assert not torch.cuda.is_initialized()
        assert psutil.virtual_memory().available > 24 * 2**30
        guard(review)
        out = Path(plan["output"])
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
        record("binding-fresh-and-retained-native-photo-and-camera-crops")
        boards = []
        for panel, kind in [("full427", "synthetic"), ("known", "camera"), ("unseen", "camera")]:
            report_path = native_report(
                outputs[panel] / "summary.json",
                Path(plan["retained_native_reports"][panel]["path"]),
                out / (panel + "-native-sources"),
                kind,
                plan["retained_parent_sha256"],
                plan["retained_RawNIND_sha256"],
            )
            result = build([report_path], out / (panel + "-native.png"), kind)
            boards.append(
                {
                    "panel": panel,
                    "board": result["board"],
                    "receipt": ref(out / (panel + "-native.json")),
                    "native_cells": result["native_cells_exact"],
                }
            )
        status["completed"].append("fresh-and-retained-photo-camera-native-boards")
        record("building-remaining-native-boards-without-resampling")
        for panel, filename, kind in [
            ("gfx", "report.json", "gfx"),
            ("analytic", "summary.json", "analytic"),
            ("hue", "report.json", "hue"),
            ("highlights", "report.json", "highlights"),
        ]:
            result = build([outputs[panel] / filename], out / (panel + "-native.png"), kind)
            boards.append(
                {
                    "panel": panel,
                    "board": result["board"],
                    "receipt": ref(out / (panel + "-native.json")),
                    "native_cells": result["native_cells_exact"],
                }
            )
        extra = out / "hue-extra-native"
        extra.mkdir()
        for crop in report["additional_native_crops"]:
            source = out / "hue-cases" / crop["image"]
            assert sha(source) == crop["png_sha256"]
            shutil.copyfile(source, extra / source.name)
        save(
            extra / "report.json",
            {
                "native_crops": report["additional_native_crops"],
                "scope": "Same fixed additional palettes from saved arrays.",
            },
        )
        result = build([extra / "report.json"], out / "hue-extra-native.png", "hue")
        boards.append(
            {
                "panel": "hue-extra",
                "board": result["board"],
                "receipt": ref(out / "hue-extra-native.json"),
                "native_cells": result["native_cells_exact"],
            }
        )
        status["completed"].append("remaining-native-boards-created")
        if historical:
            score_criteria = historical_criteria
        else:
            from score_bank_detachment_eligibility import main as score_criteria

        score_criteria(Path(plan["review_plan"]["path"]), out / "numerical-criteria.json")
        status["completed"].append("predeclared-primary-weak-carrier-and-ADC-criteria")
        assert not torch.cuda.is_initialized()
        guard(review)
        for item in plan["inputs"]:
            assert ref(item["path"]) == item
        result = {
            "status": "completed-historical-closure-replay-no-current-quality-evidence"
            if historical
            else "completed-CPU-numerical-and-native-board-preparation-awaiting-manual-review",
            "historical_replay": historical,
            "closure_plan": ref(plan_path),
            "review_terminal": ref(Path(review["root"]) / "status.json"),
            "hue_cases": ref(out / "hue-cases/audit.json"),
            "hue_summary": ref(out / "hue-summary-audit.json"),
            "analytic_summary": ref(out / "analytic-audit.json"),
            "numerical_criteria": ref(out / "numerical-criteria.json"),
            "boards": boards,
            "CUDA_initialized": False,
            "manual_native_review_complete": False,
            "model_promoted_or_default_changed": False,
            "scope": "No new model inference, noise or image selection. CPU-only independent "
            "saved-array/color/analytic arithmetic and exact native PNG rearrangement. Four extra "
            "palettes were declared before new hue outputs existed. All new boards still require "
            "actual manual review and full quality/continuation decision; no promotion.",
        }
        save(root / "closure-result.json", result)
        record(result["status"], result=ref(root / "closure-result.json"))
    except BaseException as error:
        record("failed-CPU-bank-detachment-closure-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
