"""Recompute detail/flat reductions with independent NumPy64 and Decimal."""

import argparse
import os
from collections import defaultdict
from decimal import Decimal, localcontext
from pathlib import Path

import numpy as np
from score_relative_phase_trial import load_module
from train_directional_bank_trial import read, ref, save


def main(root):
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[2:4])
    design = read(root / "quality-design-v1.json")
    result = read(root / "scores-v1.json")
    assert result["design"] == ref(root / "quality-design-v1.json")
    independent_source = root.parent / "collaborative-detail-v1/audit-transfer-v1.py"
    metric = load_module(independent_source, "independent_late_spectral_metrics")
    review = read(root / "review-result-v1.json")
    maps = {}
    for label, binding in review["collections"].items():
        assert ref(binding["path"]) == binding
        collection = read(binding["path"])
        assert (
            collection["module_before"] == collection["module_after"]
            and collection["RNG_unchanged"]
        )
        assert collection["component_forwards"] == 822
        maps[label] = {o["id"]: o for o in collection["observations"]}
    by_id = defaultdict(list)
    for row in result["rows"]:
        by_id[row["id"]].append(row)
    cached = read(Path(read(root / "plan-v1.json")["previous"]) / "scores-v1.json")
    cached_rows = {
        (r["id"], r["method"]): r
        for r in cached["rows"]
        if r["method"] in ("parent", "periodic-detail")
    }
    checks = calls = retained = real = 0
    maximum = 0.0
    for index, case in enumerate(design["observations"]):
        assert ref(case["arrays"]["path"]) == case["arrays"]
        arrays = dict(np.load(case["arrays"]["path"]))
        expected = {
            "parent": case["parent"],
            **{k: m[case["id"]]["prediction"] for k, m in maps.items()},
        }
        if "periodic_detail" in case:
            expected["periodic-detail"] = case["periodic_detail"]
        assert set(expected) == {r["method"] for r in by_id[case["id"]]}
        parent = np.load(case["parent"]["path"]).astype(np.float64)
        for row in by_id[case["id"]]:
            label = row["method"]
            assert row["index"] == index and row["prediction"] == expected[label]
            assert ref(row["prediction"]["path"]) == row["prediction"]
            raw = np.load(row["prediction"]["path"])
            assert raw.dtype == np.float32 and raw.shape == parent.shape and np.isfinite(raw).all()
            value = raw.astype(np.float64)
            change = value - parent
            assert row["changed"] == (not np.array_equal(value, parent))
            assert row["new_forward"] == (label in maps)
            calls += label in maps
            if label in maps:
                binding = maps[label][case["id"]]
                assert binding["parent"] == case["parent"] and binding["module_forwards"] == 1
                for k, f in binding["inputs"].items():
                    import hashlib

                    v = np.ascontiguousarray(arrays[k])
                    assert f == {
                        "shape": list(v.shape),
                        "dtype": v.dtype.str,
                        "sha256": hashlib.sha256(v.tobytes()).hexdigest(),
                    }
            actual = {"correction_RMS_DN16": float(np.sqrt(np.mean(change**2)) * 65535)}
            if case["kind"] == "real":
                assert row["reference_scored"] is False and "full_error_RMS_DN16" not in row
                real += 1
                if value.shape[-1] == 512:
                    plane = metric.detrend(value[0])
                    blocks = np.stack(
                        [
                            plane[:, y : y + 32, x : x + 32].mean((-2, -1))
                            for y in range(0, 512, 32)
                            for x in range(0, 512, 32)
                        ],
                        -1,
                    )
                    actual["detrended_block32_variation_DN16"] = float(
                        np.sqrt(np.mean(blocks**2)) * 65535
                    )
            else:
                actual.update(
                    metric.photo_metrics(raw, arrays["target"], arrays, case["ROI_xywh"])
                    if case["kind"] == "photo"
                    else metric.errors(raw, arrays["target"], case["ROI_xywh"])
                )
                if case["kind"] == "mesh":
                    empty = arrays["target_empty"][0].astype(np.float64)
                    signal = metric.detrend(arrays["target_present"][0].astype(np.float64) - empty)
                    actual["template_gain"] = float(
                        np.sum(metric.detrend(value[0] - empty) * signal) / np.sum(signal**2)
                    )
                    blank = (
                        np.all(arrays["target_present"] == arrays["target_empty"], axis=1)[0]
                        if case["present"]
                        else np.ones((512, 512), bool)
                    )
                    assert row["blank_pixels"] == int(blank.sum())
                    if blank.any():
                        actual["blank_added_RMS_DN16"] = float(
                            np.sqrt(np.mean(change[0][:, blank] ** 2)) * 65535
                        )
                    else:
                        assert row["blank_added_RMS_DN16"] is None
                    if blank.any():
                        error = (value[0] - arrays["target"][0].astype(np.float64))[:, blank]
                        means = error.mean(1)
                        actual["blank_error_RMS_DN16"] = float(
                            np.linalg.norm(error) / np.sqrt(error.size) * 65535
                        )
                        actual["blank_DC_RMS_DN16"] = float(
                            np.linalg.norm(means) / np.sqrt(3) * 65535
                        )
                        actual["blank_spatial_RMS_DN16"] = float(
                            np.sqrt(max(0, np.mean(error**2) - np.mean(means**2))) * 65535
                        )
                elif case["kind"] == "mixed-quiet":
                    x, y, w, h = case["ROI_xywh"]
                    actual["quiet_error_RMS_DN16"] = float(
                        np.linalg.norm(
                            (value - arrays["target"].astype(np.float64))[
                                ..., y : y + h, x : x + w
                            ].ravel()
                        )
                        / np.sqrt(3 * w * h)
                        * 65535
                    )
                    actual["quiet_spatial_RMS_DN16"] = actual["crop_spatial_RMS_DN16"]
                    actual["quiet_added_RMS_DN16"] = float(
                        np.sqrt(np.mean(change[..., y : y + h, x : x + w] ** 2)) * 65535
                    )
                elif case["kind"] == "flat":
                    error = value - arrays["target"].astype(np.float64)
                    h, w = error.shape[-2:]
                    dc = error.mean((-2, -1))
                    blocks = np.stack(
                        [
                            error[..., y : y + 32, x : x + 32].mean((-2, -1))
                            for y in range(0, h, 32)
                            for x in range(0, w, 32)
                        ],
                        -1,
                    )
                    x, y, cw, ch = case["ROI_xywh"]
                    crop = error[..., y : y + ch, x : x + cw]
                    crop_dc = crop.mean((-2, -1))
                    cb = np.stack(
                        [
                            crop[..., j : j + 32, i : i + 32].mean((-2, -1))
                            for j in range(0, 160, 32)
                            for i in range(0, 160, 32)
                        ],
                        -1,
                    )
                    actual.update(
                        full_spatial_RMS_DN16=float(
                            np.sqrt(np.mean((error - dc[..., None, None]) ** 2)) * 65535
                        ),
                        block32_RMS_DN16=float(
                            np.sqrt(np.mean((blocks - dc[..., None]) ** 2)) * 65535
                        ),
                        crop_block32_RMS_DN16=float(
                            np.sqrt(np.mean((cb - crop_dc[..., None]) ** 2)) * 65535
                        ),
                        maximum_abs_DC_DN16=float(np.max(np.abs(dc)) * 65535),
                    )
            for field, value in actual.items():
                difference = abs(value - row[field])
                assert difference < 1e-9 * max(1, abs(value)), (case["id"], label, field)
                maximum = max(maximum, difference)
                checks += 1
            if label in ("parent", "periodic-detail") and (case["id"], label) in cached_rows:
                old = cached_rows[case["id"], label]
                assert row["prediction"] == old["prediction"]
                for field in actual:
                    if field in old:
                        assert abs(row[field] - old[field]) < 1e-10
                retained += 1
    assert calls == 3288 and retained == 1398 and real == 30 and len(result["rows"]) == 4686
    groups = defaultdict(list)
    for row in result["rows"]:
        groups[
            row["kind"],
            row.get("present", row.get("variant", row.get("noise"))),
            row.get("cohort"),
            row["method"],
        ].append(row)
    reductions = 0
    for item in result["summary"]:
        group = groups[item["kind"], item["condition"], item["cohort"], item["method"]]
        assert item["cases"] == len(group)
        for field in item.keys() - {
            "kind",
            "condition",
            "cohort",
            "method",
            "cases",
            "worst_abs_DC_DN16",
            "worst_blank_added_RMS_DN16",
            "worst_blank_error_RMS_DN16",
        }:
            values = [r[field] for r in group if r.get(field) is not None]
            with localcontext() as ctx:
                ctx.prec = 50
                number = float(sum(Decimal(str(v)) for v in values) / len(values))
            assert abs(number - item[field]) < 1e-10
            reductions += 1
        if item["kind"] == "mesh":
            assert item["worst_blank_added_RMS_DN16"] == max(
                r["blank_added_RMS_DN16"] or 0 for r in group
            )
        if item["kind"] == "mesh":
            assert item["worst_blank_error_RMS_DN16"] == max(
                r.get("blank_error_RMS_DN16", 0) for r in group
            )
        if item["kind"] == "flat":
            assert item["worst_abs_DC_DN16"] == max(r["maximum_abs_DC_DN16"] for r in group)
    save(
        root / "independent-metrics-audit-v1.json",
        {
            "status": "pass",
            "scores": ref(root / "scores-v1.json"),
            "auditor": ref(__file__),
            "independent_metric_source": ref(independent_source),
            "rows": 4686,
            "module_forwards_verified": calls,
            "retained_bindings_and_metrics": retained,
            "real_rows_unscored": real,
            "scalar_checks": checks,
            "maximum_scalar_difference": maximum,
            "Decimal_reductions": reductions,
            "new_forwards": 0,
            "new_noise_draws": 0,
        },
    )
    print("PASS independent scalar checks:", checks, "Decimal reductions:", reductions)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    main(parser.parse_args().root.resolve())
