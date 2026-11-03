"""NumPy scores of the post-hoc local-support intervention, without inference."""

import argparse
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

import numpy as np
from score_late_spectral_trial import load_module
from train_directional_bank_trial import read, ref, save


def main(root):
    point = root / "support-ablation-v1"
    collection = read(point / "collection-v1.json")
    plan = read(point / "plan-v1.json")
    assert collection["plan"] == ref(point / "plan-v1.json")
    assert (
        collection["new_component_forwards"] == 766
        and collection["module_before"] == collection["module_after"]
    )
    assert (
        collection["new_parent_DINO_forwards"] == collection["new_noise_draws"] == 0
        and collection["RNG_unchanged"]
    )
    cases = read(plan["design"]["path"])["observations"]
    assert [o["id"] for o in cases] == [o["id"] for o in collection["observations"]]
    metric_path = root.parent / "collaborative-detail-v1/audit-transfer-v1.py"
    metric = load_module(metric_path, "independent_support_ablation_metrics")
    rows = []
    for case, output in zip(cases, collection["observations"], strict=True):
        assert ref(output["prediction"]["path"]) == output["prediction"]
        value = np.load(output["prediction"]["path"])
        assert value.dtype == np.float32 and np.isfinite(value).all()
        assert ref(case["arrays"]["path"]) == case["arrays"]
        a = dict(np.load(case["arrays"]["path"]))
        parent = np.load(case["parent"]["path"]).astype(np.float64)
        change = value.astype(np.float64) - parent
        row = {
            "id": case["id"],
            "kind": case["kind"],
            "cohort": case.get("cohort"),
            "method": "raw-full-local-support",
            "prediction": output["prediction"],
            "correction_RMS_DN16": float(np.sqrt(np.mean(change**2)) * 65535),
        }
        if case["kind"] == "real":
            row["reference_scored"] = False
        elif case["kind"] == "photo":
            row.update(
                variant=case["variant"]["name"],
                **metric.photo_metrics(value, a["target"], a, case["ROI_xywh"]),
            )
        else:
            row.update(metric.errors(value, a["target"], case["ROI_xywh"]))
            if case["kind"] == "mesh":
                signal = metric.detrend(
                    a["target_present"][0].astype(np.float64)
                    - a["target_empty"][0].astype(np.float64)
                )
                empty = a["target_empty"][0].astype(np.float64)
                blank = (
                    np.all(a["target_present"] == a["target_empty"], axis=1)[0]
                    if case["present"]
                    else np.ones((512, 512), bool)
                )
                row.update(
                    present=case["present"],
                    template_gain=float(
                        np.sum(metric.detrend(value[0].astype(np.float64) - empty) * signal)
                        / np.sum(signal**2)
                    ),
                    blank_added_RMS_DN16=float(np.sqrt(np.mean(change[0][:, blank] ** 2)) * 65535)
                    if blank.any()
                    else None,
                )
            else:
                assert case["kind"] == "flat"
                error = value.astype(np.float64) - a["target"].astype(np.float64)
                row.update(
                    noise=case["noise"]["name"],
                    full_spatial_RMS_DN16=float(
                        np.sqrt(np.mean((error - error.mean((-2, -1), keepdims=True)) ** 2)) * 65535
                    ),
                )
        rows.append(row)
    groups = defaultdict(list)
    for row in rows:
        groups[
            row["kind"], row.get("present", row.get("variant", row.get("noise"))), row.get("cohort")
        ].append(row)
    summary = []
    fields = (
        "full_error_RMS_DN16",
        "template_gain",
        "blank_added_RMS_DN16",
        "crop_relative_band_error",
        "crop_linear_sRGB_luma_band_gain",
        "full_spatial_RMS_DN16",
        "correction_RMS_DN16",
    )
    for (kind, condition, cohort), group in groups.items():
        item = {"kind": kind, "condition": condition, "cohort": cohort, "cases": len(group)}
        for field in fields:
            numbers = [r[field] for r in group if r.get(field) is not None]
            if numbers:
                item[field] = float(sum(Decimal(str(v)) for v in numbers) / len(numbers))
        summary.append(item)
    dest = point / "scores-v1.json"
    assert not dest.exists()
    save(
        dest,
        {
            "status": "completed-posthoc-full-support-array-scores",
            "collection": ref(point / "collection-v1.json"),
            "operator": ref(__file__),
            "metric_source": ref(metric_path),
            "rows": rows,
            "summary": summary,
            "control_replays_bit_exact": sum(
                o["control_bit_exact"] for o in collection["observations"]
            ),
            "maximum_control_difference_DN16": max(
                o["control_maximum_difference_DN16"] for o in collection["observations"]
            ),
            "new_forwards_in_scorer": 0,
            "new_noise_draws": 0,
            "scope": plan["scope"],
        },
    )
    for row in summary:
        if row["kind"] in ("mesh", "flat"):
            print(row)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
