"""Matched MSE/robust delivered-RGB scores, including actual blank errors."""

import argparse
import importlib.util
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
from train_directional_bank_trial import read, ref, save


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def main(root):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[2:4])
    design_path = root / "quality-design-v1.json"
    design = read(design_path)
    review = read(root / "review-result-v1.json")
    assert read(review["plan"]["path"])["design"] == ref(design_path)
    metric_paths = [
        root.parent / "collaborative-detail-v1/transfer-v1.py",
        root.parent / "V144-V145-photo-supplement-v1/operator-v2.py",
    ]
    error_metric, photo_metric = [
        load_module(path, f"metric{i}") for i, path in enumerate(metric_paths)
    ]
    maps = {}
    for label, binding in review["collections"].items():
        assert ref(binding["path"]) == binding
        c = read(binding["path"])
        assert c["module_before"] == c["module_after"] and c["RNG_unchanged"]
        assert (
            c["component_forwards"] == 822
            and c["new_parent_DINO_forwards"] == c["new_noise_draws"] == 0
        )
        assert [o["id"] for o in c["observations"]] == [o["id"] for o in design["observations"]]
        maps[label] = {o["id"]: o["prediction"] for o in c["observations"]}
    yy, xx = np.mgrid[-1:1:512j, -1:1:512j]
    q = np.linalg.qr(np.stack([np.ones_like(xx), xx, yy], -1).reshape(-1, 3), mode="reduced")[0]

    def detrend(value):
        v = value.reshape(3, -1).T
        return v - q @ (q.T @ v)

    rows = []
    for index, case in enumerate(design["observations"]):
        assert ref(case["arrays"]["path"]) == case["arrays"]
        a = dict(np.load(case["arrays"]["path"]))
        bindings = {
            "parent": case["parent"],
            **{label: values[case["id"]] for label, values in maps.items()},
        }
        if "periodic_detail" in case:
            bindings["periodic-detail"] = case["periodic_detail"]
        parent = np.load(case["parent"]["path"])
        if case["kind"] == "mesh":
            empty = a["target_empty"][0].astype(np.float64)
            signal = detrend(a["target_present"][0].astype(np.float64) - empty)
            blank = (
                np.all(a["target_present"] == a["target_empty"], axis=1)[0]
                if case["present"]
                else np.ones((512, 512), bool)
            )
        for label, binding in bindings.items():
            assert ref(binding["path"]) == binding
            value = np.load(binding["path"])
            assert (
                value.dtype == np.float32
                and value.shape == parent.shape
                and np.isfinite(value).all()
            )
            v = value.astype(np.float64)
            change = v - parent.astype(np.float64)
            row = {
                "id": case["id"],
                "index": index,
                "kind": case["kind"],
                "cohort": case.get("cohort"),
                "method": label,
                "prediction": binding,
                "fresh": case.get("fresh", False),
                "new_forward": label in maps,
                "changed": not np.array_equal(value, parent),
                "correction_RMS_DN16": float(np.sqrt(np.mean(change**2)) * 65535),
            }
            if case["kind"] == "mesh":
                row.update(
                    present=case["present"],
                    seed=case["seed"],
                    **error_metric.errors(value, a["target"], case["ROI_xywh"]),
                    template_gain=float(np.sum(detrend(v[0] - empty) * signal) / np.sum(signal**2)),
                    blank_pixels=int(blank.sum()),
                    blank_added_RMS_DN16=float(np.sqrt(np.mean(change[0][:, blank] ** 2)) * 65535)
                    if blank.any()
                    else None,
                )
                if blank.any():
                    error = (v[0] - a["target"][0].astype(np.float64))[:, blank]
                    means = error.mean(1, keepdims=True)
                    row.update(
                        blank_error_RMS_DN16=float(np.sqrt(np.mean(error**2)) * 65535),
                        blank_spatial_RMS_DN16=float(
                            np.sqrt(np.mean((error - means) ** 2)) * 65535
                        ),
                        blank_DC_RMS_DN16=float(np.sqrt(np.mean(means**2)) * 65535),
                    )
            elif case["kind"] == "photo":
                row.update(
                    variant=case["variant"]["name"],
                    **photo_metric.photo_metrics(value, a["target"], a, case["ROI_xywh"]),
                )
            elif case["kind"] == "flat":
                error = v - a["target"].astype(np.float64)
                dc = error.mean((-2, -1), keepdims=True)
                h, w = error.shape[-2:]
                blocks = error.reshape(1, 3, h // 32, 32, w // 32, 32).mean((3, 5))
                x, y, cw, ch = case["ROI_xywh"]
                crop = error[..., y : y + ch, x : x + cw]
                crop_dc = crop.mean((-2, -1), keepdims=True)
                cb = crop.reshape(1, 3, 5, 32, 5, 32).mean((3, 5))
                row.update(
                    noise=case["noise"]["name"],
                    **error_metric.errors(value, a["target"], case["ROI_xywh"]),
                    full_spatial_RMS_DN16=float(np.sqrt(np.mean((error - dc) ** 2)) * 65535),
                    block32_RMS_DN16=float(np.sqrt(np.mean((blocks - dc) ** 2)) * 65535),
                    crop_block32_RMS_DN16=float(np.sqrt(np.mean((cb - crop_dc) ** 2)) * 65535),
                    maximum_abs_DC_DN16=float(np.max(np.abs(dc)) * 65535),
                )
            elif case["kind"] == "mixed-quiet":
                row.update(
                    noise=case["noise"]["name"],
                    **error_metric.errors(value, a["target"], case["ROI_xywh"]),
                )
                x, y, w, h = case["ROI_xywh"]
                row.update(
                    quiet_error_RMS_DN16=float(
                        np.sqrt(
                            np.mean(
                                (v - a["target"].astype(np.float64))[..., y : y + h, x : x + w] ** 2
                            )
                        )
                        * 65535
                    ),
                    quiet_spatial_RMS_DN16=row["crop_spatial_RMS_DN16"],
                    quiet_added_RMS_DN16=float(
                        np.sqrt(np.mean(change[..., y : y + h, x : x + w] ** 2)) * 65535
                    ),
                )
            else:
                assert case["kind"] == "real"
                row["reference_scored"] = False
                if value.shape[-1] == 512:
                    plane = detrend(value[0]).T.reshape(3, 512, 512)
                    blocks = plane.reshape(3, 16, 32, 16, 32).mean((2, 4))
                    row["detrended_block32_variation_DN16"] = float(
                        np.sqrt(np.mean(blocks**2)) * 65535
                    )
            rows.append(row)
    assert len(rows) == 6330 and sum(r["new_forward"] for r in rows) == 4932
    groups = defaultdict(list)
    for row in rows:
        groups[
            row["kind"],
            row.get("present", row.get("variant", row.get("noise"))),
            row.get("cohort"),
            row["method"],
        ].append(row)
    fields = (
        "full_error_RMS_DN16",
        "crop_spatial_RMS_DN16",
        "crop_relative_band_error",
        "crop_linear_sRGB_luma_band_gain",
        "template_gain",
        "blank_added_RMS_DN16",
        "blank_error_RMS_DN16",
        "blank_spatial_RMS_DN16",
        "blank_DC_RMS_DN16",
        "full_spatial_RMS_DN16",
        "block32_RMS_DN16",
        "crop_block32_RMS_DN16",
        "correction_RMS_DN16",
        "quiet_error_RMS_DN16",
        "quiet_spatial_RMS_DN16",
        "quiet_added_RMS_DN16",
    )
    summary = []
    for (kind, condition, cohort, method), group in groups.items():
        item = {
            "kind": kind,
            "condition": condition,
            "cohort": cohort,
            "method": method,
            "cases": len(group),
        }
        for field in fields:
            values = [r[field] for r in group if r.get(field) is not None]
            if values:
                item[field] = float(np.mean(values))
        if kind == "mesh":
            item["worst_blank_added_RMS_DN16"] = max(r["blank_added_RMS_DN16"] or 0 for r in group)
        if kind == "mesh":
            item["worst_blank_error_RMS_DN16"] = max(
                r.get("blank_error_RMS_DN16", 0) for r in group
            )
        if kind == "flat":
            item["worst_abs_DC_DN16"] = max(r["maximum_abs_DC_DN16"] for r in group)
        summary.append(item)
    save(
        root / "scores-v1.json",
        {
            "status": "completed-array-only-scores",
            "design": ref(design_path),
            "review": ref(root / "review-result-v1.json"),
            "scorer": ref(__file__),
            "metric_sources": [ref(p) for p in metric_paths],
            "rows": rows,
            "summary": summary,
            "new_module_forwards_in_scorer": 0,
            "new_noise_draws": 0,
            "real_reference_scores": 0,
        },
    )
    print("Scored6330 paired rows; real references unscored")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
