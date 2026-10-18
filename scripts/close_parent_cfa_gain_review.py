"""Finish saved-photo arithmetic and fixed sensitivities after the exact owner exits."""

import argparse
import json
import os
import shutil
import time
from pathlib import Path

import psutil

TERMINAL = "completed-shared-forward-photo-test-awaiting-native-camera-and-decision-review"


def read(path):
    return json.loads(Path(path).read_text())


def alive(owner):
    try:
        p = psutil.Process(owner["pid"])
        return p.create_time() == owner["created"] and p.status() != psutil.STATUS_ZOMBIE
    except psutil.NoSuchProcess:
        return False


def ready(status, owner, photo_plan):
    if status["controller"] != owner or status["plan"] != photo_plan:
        raise RuntimeError("Photographic producer/plan identity differs")
    if status["status"].startswith("failed-"):
        raise RuntimeError("Photographic test failed; no automatic closure/retry")
    if alive(owner):
        return False
    if status["status"] != TERMINAL:
        raise RuntimeError("Photographic producer exited before completing full grid")
    if any(
        status.get(k) != v
        for k, v in [
            ("sources_done", 443),
            ("actual_network_forwards", 3108),
            ("case_rows", 62020),
            ("native_triplets", 4),
        ]
    ):
        raise RuntimeError("Photographic completion counts differ")
    return True


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


def main(plan_path):
    from probe_saved_cfa_gain_grid import ref

    os.nice(10)
    plan = read(plan_path)
    root = Path(plan["root"])
    output = Path(plan["output"])
    assert ref(__file__) == plan["worker"]
    for item in [
        *plan["source_files"],
        plan["photo_plan"],
        plan["cohorts"],
        plan["early_photo_evidence"],
        plan["global_real_rejection"],
    ]:
        assert ref(item["path"]) == item
    with (root / "claim").open("x") as stream:
        stream.write(str(os.getpid()))
    status = {
        "controller": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        "plan": ref(plan_path),
        "completed": [],
    }

    def record(state, **values):
        status.update(status=state, updated_unix=time.time(), **values)
        save(root / "status.json", status)
        print(json.dumps({"status": state}), flush=True)

    try:
        photo_plan = read(plan["photo_plan"]["path"])
        photo_root = Path(photo_plan["root"])
        record("waiting-for-exact-shared-forward-photo-owner-exit")
        while not ready(read(photo_root / "status.json"), plan["photo_owner"], plan["photo_plan"]):
            time.sleep(5)
        import torch
        from audit_commons_source_sensitivity import audit as audit_sensitivity
        from audit_fresh_dino_statistics import audit_photo
        from report_commons_source_sensitivity import run as sensitivity

        torch.set_num_threads(2)
        assert not torch.cuda.is_initialized()
        assert psutil.virtual_memory().available > 24 * 2**30
        assert psutil.disk_usage(root).free > 128 * 2**30
        output.mkdir(parents=True, exist_ok=False)
        photo = Path(photo_plan["output"])
        summary = read(photo / "summary.json")
        record("auditing-completed-full-photo-case-coverage-and-summary-arithmetic")
        audit = audit_photo(photo, expected_methods=5)
        save(output / "independent-photo-audit.json", audit)
        assert summary["actual_network_forwards"] == 3108 and summary["model_state_unchanged"]
        digest = photo_plan["checkpoint"]["sha256"]
        labels = ["V63-input-CFA-channel-gain", "V63-parent-fresh-FP32"]
        sources = []
        for label in labels:
            model = next(m for m in summary["models"] if m["label"] == label)
            assert model["sha256"] == digest
            sources.append(
                {
                    "label": label,
                    "checkpoint_sha256": digest,
                    "model_label": label,
                    "report": str(photo / "summary.json"),
                    "report_sha256": ref(photo / "summary.json")["sha256"],
                    "cases": str(photo / "per-image.jsonl"),
                    "cases_sha256": ref(photo / "per-image.jsonl")["sha256"],
                    "batch_size": 4,
                }
            )
        comparisons = []
        for kind in ["photo", "synthetic"]:
            for metric in ["linear_psnr", "srgb_psnr", "srgb_ssim"]:
                row = next(
                    r
                    for r in summary["paired_comparisons"]
                    if r["first"] == labels[0]
                    and r["second"] == labels[1]
                    and r["kind"] == kind
                    and r["metric"] == metric
                )
                means = [
                    next(
                        r for r in summary["overall"] if r["model"] == label and r["kind"] == kind
                    )["metrics"][metric]["mean"]
                    for label in labels
                ]
                comparisons.append(
                    {
                        "panel": "full427",
                        **row,
                        "first_checkpoint_sha256": digest,
                        "second_checkpoint_sha256": digest,
                        "first_source_balanced_mean": means[0],
                        "second_source_balanced_mean": means[1],
                    }
                )
        statistics = {
            "status": "completed-parent-input-gain-photo-statistics-awaiting-native-review",
            "audits": {"full427": audit},
            "comparisons": comparisons,
            "sources": [{"panel": "full427", "first": sources[0], "second": sources[1]}],
            "scope": "Same fresh network forward/observation for both variants. Complete photo/procedural arithmetic only; native/global real decision separate. No historical neural score reuse or new inference.",
        }
        save(output / "statistics.json", statistics)
        status["completed"].append("complete-photo-statistics")
        record("checking-all-fixed-source-cohorts-with-independent-Decimal-replay")
        sensitivity(
            output / "statistics.json",
            ref(output / "statistics.json")["sha256"],
            Path(plan["cohorts"]["path"]),
            plan["cohorts"]["sha256"],
            output / "sensitivity",
        )
        independent = audit_sensitivity(output / "sensitivity")
        save(output / "sensitivity/independent-audit.json", independent)
        shutil.copyfile(
            Path(__file__).with_name("audit_commons_source_sensitivity.py"),
            output / "sensitivity/independent-auditor-source.py",
        )
        status["completed"].append("three-fixed-photo-cohorts-independently-checked")
        record("revalidating-actually-viewed-early-photo-PNGs-and-metadata-after-producer-exit")
        early = read(plan["early_photo_evidence"]["path"])
        for crop in early["all_first_photo_triplets"]["data"]["native_crops"]:
            p = photo / crop["image"]
            assert ref(p)["sha256"] == crop["png_sha256"]
        for item in early["producer_crop_metadata"]:
            assert ref(item["path"]) == item
        assert (
            ref(early["actual_native_view"]["file"]["path"]) == early["actual_native_view"]["file"]
        )
        assert early["actual_native_view"]["data"]["native_cells_viewed"] == 8
        for item in [
            early["actual_native_view"]["data"]["board"],
            early["actual_native_view"]["data"]["board_receipt"]["file"],
        ]:
            assert ref(item["path"]) == item
        status["completed"].append("all-early-photo-source-pixels-and-metadata-unchanged")
        # These booleans report separate gates; no favorable patch statistic can
        # override the actually reviewed purple-sky failure of the global policy.
        criterion = photo_plan["eligibility_before_full_frame"]
        photo_psnr = next(
            r for r in comparisons if r["kind"] == "photo" and r["metric"] == "srgb_psnr"
        )
        ssim = next(r for r in comparisons if r["kind"] == "photo" and r["metric"] == "srgb_ssim")
        mean_ok = photo_psnr["mean_first_minus_second"] >= criterion["minimum_photo_gain_dB"]
        interval_ok = photo_psnr["source_bootstrap_95_interval"][0] > 0
        ssim_ok = (
            ssim["mean_first_minus_second"] >= -criterion["maximum_photo_SSIM_mean_regression"]
        )
        real = read(plan["global_real_rejection"]["path"])
        assert (
            real["status"]
            == "completed-saved-global-gain-real-GFX-review-rejected-color-regression"
        )
        assert real["manual_view"]["data"]["native_cells_viewed"] == 16
        result = {
            "status": "completed-photo-statistics-source-sensitivities-and-global-real-policy-rejection",
            "photo_terminal": ref(photo_root / "status.json"),
            "statistics": ref(output / "statistics.json"),
            "sensitivity": ref(output / "sensitivity/result.json"),
            "independent_sensitivity_audit": ref(output / "sensitivity/independent-audit.json"),
            "early_native_views_revalidated": plan["early_photo_evidence"],
            "global_real_rejection": plan["global_real_rejection"],
            "photo_minimum_gain_pass": mean_ok,
            "positive_source_interval_pass": interval_ok,
            "photo_SSIM_pass": ssim_ok,
            "global_real_native_pass": False,
            "eligible_for_promotion_or_full_frame_integration": False,
            "known_unseen_camera_tests": "Not launched: standing real global-policy gate fails",
            "actual_new_model_forwards": 0,
            "CUDA_initialized": False,
            "scope": "No inferred success from flat color/patch PSNR; preserve real purple-sky rejection. No automatic alternative gain formula, training extension, inference default, full-frame export or model promotion. Complete numerical evidence still requires final human publication review.",
        }
        save(output / "result.json", result)
        assert not torch.cuda.is_initialized()
        for item in plan["source_files"]:
            assert ref(item["path"]) == item
        record(result["status"], result=ref(output / "result.json"))
    except BaseException as error:
        record("failed-photo-gain-closure-no-automatic-retry", error=repr(error))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    main(parser.parse_args().plan)
