"""Stream the established camera-RGB detail/blank/quiet metrics."""

import importlib.util
from collections import defaultdict

import numpy as np


def load_metric(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DetailMetrics:
    def __init__(self, sources):
        self.error_metric, self.photo_metric = [
            load_metric(p["path"], f"balanced_metric{i}") for i, p in enumerate(sources)
        ]
        yy, xx = np.mgrid[-1:1:512j, -1:1:512j]
        self.q = np.linalg.qr(
            np.stack([np.ones_like(xx), xx, yy], -1).reshape(-1, 3), mode="reduced"
        )[0]

    def detrend(self, value):
        value = value.reshape(3, -1).T
        return value - self.q @ (self.q.T @ value)

    def measure(self, case, arrays, base, value):
        assert value.shape == base.shape and value.dtype == np.float32 and np.isfinite(value).all()
        v, b = value.astype(np.float64), base.astype(np.float64)
        change = v - b
        row = {
            "id": case["id"],
            "kind": case["kind"],
            "cohort": case.get("cohort"),
            "correction_RMS_DN16": float(np.sqrt(np.mean(change**2)) * 65535),
            "changed": not np.array_equal(value, base),
        }
        if case["kind"] == "real":
            row["reference_scored"] = False
            return row
        target = arrays["target"]
        row.update(self.error_metric.errors(value, target, case["ROI_xywh"]))
        x, y, w, h = case["ROI_xywh"]
        error = v - target.astype(np.float64)
        crop = error[..., y : y + h, x : x + w]
        mean = crop.mean((-2, -1), keepdims=True)
        # Separate norm reduction checks full RMS and the crop decomposition.
        independent = float(np.linalg.norm(error.ravel()) / np.sqrt(error.size) * 65535)
        assert abs(independent - row["full_error_RMS_DN16"]) < 1e-10
        assert abs(np.mean(crop**2) - np.mean((crop - mean) ** 2) - np.mean(mean**2)) < 1e-18
        if case["kind"] == "mesh":
            empty = arrays["target_empty"][0].astype(np.float64)
            signal = self.detrend(arrays["target_present"][0].astype(np.float64) - empty)
            blank = (
                np.all(arrays["target_present"] == arrays["target_empty"], axis=1)[0]
                if case["present"]
                else np.ones((512, 512), bool)
            )
            row.update(
                present=case["present"],
                seed=case["seed"],
                blank_pixels=int(blank.sum()),
                template_gain=float(
                    np.sum(self.detrend(v[0] - empty) * signal) / np.sum(signal**2)
                ),
                blank_added_RMS_DN16=float(np.sqrt(np.mean(change[0][:, blank] ** 2)) * 65535)
                if blank.any()
                else None,
            )
            if blank.any():
                e = error[0][:, blank]
                dc = e.mean(1, keepdims=True)
                row.update(
                    blank_error_RMS_DN16=float(np.sqrt(np.mean(e**2)) * 65535),
                    blank_spatial_RMS_DN16=float(np.sqrt(np.mean((e - dc) ** 2)) * 65535),
                    blank_DC_RMS_DN16=float(np.sqrt(np.mean(dc**2)) * 65535),
                )
        elif case["kind"] == "photo":
            row.update(
                variant=case["variant"]["name"],
                **self.photo_metric.photo_metrics(value, target, arrays, case["ROI_xywh"]),
            )
        elif case["kind"] == "mixed-quiet":
            row.update(
                noise=case["noise"]["name"],
                quiet_error_RMS_DN16=float(np.sqrt(np.mean(crop**2)) * 65535),
                quiet_spatial_RMS_DN16=row["crop_spatial_RMS_DN16"],
                quiet_DC_RMS_DN16=row["crop_DC_RMS_DN16"],
                quiet_added_RMS_DN16=float(
                    np.sqrt(np.mean(change[..., y : y + h, x : x + w] ** 2)) * 65535
                ),
            )
        else:
            assert case["kind"] == "flat"
            dc = error.mean((-2, -1), keepdims=True)
            height, width = error.shape[-2:]
            blocks = error.reshape(1, 3, height // 32, 32, width // 32, 32).mean((3, 5))
            cb = crop.reshape(1, 3, 5, 32, 5, 32).mean((3, 5))
            row.update(
                noise=case["noise"]["name"],
                full_spatial_RMS_DN16=float(np.sqrt(np.mean((error - dc) ** 2)) * 65535),
                block32_RMS_DN16=float(np.sqrt(np.mean((blocks - dc) ** 2)) * 65535),
                crop_block32_RMS_DN16=float(np.sqrt(np.mean((cb - mean) ** 2)) * 65535),
                maximum_abs_DC_DN16=float(np.max(np.abs(dc)) * 65535),
            )
        return row


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[
            row["kind"],
            row.get("present", row.get("variant", row.get("noise"))),
            row.get("cohort"),
            row["method"],
        ].append(row)
    summaries = []
    for (kind, condition, cohort, method), group in groups.items():
        result = {
            "kind": kind,
            "condition": condition,
            "cohort": cohort,
            "method": method,
            "cases": len(group),
        }
        for field in group[0]:
            if field.endswith(("DN16", "gain", "error")) and all(
                isinstance(v.get(field), (int, float)) and not isinstance(v.get(field), bool)
                for v in group
            ):
                result[field] = float(np.mean([v[field] for v in group]))
        summaries.append(result)
    return summaries
