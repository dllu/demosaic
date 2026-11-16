"""Stream independent full-cohort scalar, cluster-statistic and native-pixel checks."""

import math
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
from audit_checkpoint_pilot import crop
from PIL import Image

from demosaic.archive_metrics import noisy_malvar
from demosaic.experiments.artifacts import checked, read_json, reference, write_json


def _scalars(target, value, quiet, edge):
    target, value = target.astype(np.float64), value.astype(np.float64)
    error, result = value - target, {}
    for name, mask in [("quiet", quiet), ("edge", edge)]:
        selected = error[..., mask]
        dc = selected.mean(axis=-1)
        result[name + "_error_RMS_DN16"] = float(
            np.linalg.norm(selected.ravel()) / np.sqrt(selected.size) * 65535
        )
        result[name + "_DC_RMS_DN16"] = float(np.linalg.norm(dc.ravel()) / np.sqrt(dc.size) * 65535)
        residual = selected - dc[..., None]
        result[name + "_spatial_RMS_DN16"] = float(
            np.linalg.norm(residual.ravel()) / np.sqrt(residual.size) * 65535
        )
    result["full_error_RMS_DN16"] = float(
        np.linalg.norm(error.ravel()) / np.sqrt(error.size) * 65535
    )
    for name, a, b in [("strong", 0, 1), ("weak", 1, 2)]:
        truth, predicted = (target[b] - target[a]).ravel(), (value[b] - value[a]).ravel()
        gain = float(np.vdot(predicted, truth) / np.vdot(truth, truth))
        result[name + "_gain"] = gain
        result[name + "_increment_error_RMS_DN16"] = float(
            np.linalg.norm(predicted - truth) / np.sqrt(truth.size) * 65535
        )
        result[name + "_orthogonal_RMS_DN16"] = float(
            np.linalg.norm(predicted - gain * truth) / np.sqrt(truth.size) * 65535
        )
    return result


def audit(root):
    if "torch" in sys.modules:
        raise RuntimeError("Require NumPy-only independent review")
    report, enriched = read_json(root / "report.json"), read_json(root / "rows.json")
    own = read_json(root / "plan.json")
    plan = read_json(checked(own["producer_plan"]))
    if report["collection"] != enriched["collection"] or report["model"] != own["model"]:
        raise ValueError("Closed collection/model differs")
    recorded = {(r["group_index"], r["method"]): r for r in enriched["rows"]}
    if len(recorded) != 1152 or len(enriched["groups"]) != 384:
        raise ValueError("Complete scalar join differs")
    actual, fields, max_scalar = [], 0, 0.0
    for binding, group in zip(enriched["groups"], plan["finite_groups"], strict=True):
        with np.load(checked(binding["arrays"]), allow_pickle=False) as z:
            target, quiet, edge = z["target"], z["quiet"], z["edge_band"]
        meta = group["metadata"]
        index = binding["group_index"]
        for method in ["V143", "global-t2", "local-t2"]:
            value = (
                np.load(checked(binding["parent"]), allow_pickle=False)
                if method == "V143"
                else np.stack(
                    [
                        np.load(checked(b), allow_pickle=False)
                        for b in binding["predictions"][method]
                    ]
                )
            )
            if (
                value.shape != target.shape
                or value.dtype != np.float32
                or not np.isfinite(value).all()
            ):
                raise ValueError("Native prediction shape/dtype/finiteness differs")
            values = _scalars(target, value, quiet, edge)
            row = recorded[index, method]
            expected = {
                "profile": group["profile"],
                "source": meta["recipe"]["source"],
                "placement": meta["placement"],
                "pattern": meta["pattern"],
                "repeat": meta["repeat"],
                "cache_index": group["index"],
            }
            if any(row[k] != v for k, v in expected.items()):
                raise ValueError("Recovered CFA/repeat/source identity differs")
            for key, value in values.items():
                error = abs(value - row[key])
                max_scalar = max(max_scalar, error)
                fields += 1
                if error > 1e-10:
                    raise ValueError("Independent finite-increment metric differs")
            actual.append({**row, **values})
    summary = read_json(root / "summary.json")
    max_summary = 0.0
    metrics = list(values)
    for mean in summary["means"]:
        selected = [
            r for r in actual if all(r[k] == mean[k] for k in ["profile", "placement", "method"])
        ]
        if len(selected) != 64 or len({r["source"] for r in selected}) != 8:
            raise ValueError("Expected64 views/eight source clusters")
        for key in metrics:
            max_summary = max(
                max_summary, abs(float(np.mean([r[key] for r in selected])) - mean[key])
            )
    # A separate stars-and-bars enumeration compresses all8^8 ordered draws.
    counts = np.array(
        [np.diff([-1, *bars, 15]) - 1 for bars in combinations(range(15), 7)], np.int64
    )
    weights = []
    for row in counts:
        remaining, weight = 8, 1
        for number in row:
            weight *= math.comb(remaining, int(number))
            remaining -= int(number)
        weights.append(weight)
    weights = np.array(weights, np.int64)
    if int(weights.sum()) != 8**8 or len(weights) != 6435:
        raise ValueError("Independent bootstrap enumeration differs")
    bootstrap_fields, max_boot = 0, 0.0
    for contrast in summary["contrasts"]:
        cell = [
            r
            for r in actual
            if r["profile"] == contrast["profile"] and r["placement"] == contrast["placement"]
        ]
        for key, expected in contrast["fields"].items():
            delta = []
            for source in range(8):
                means = {
                    m: float(
                        np.mean(
                            [r[key] for r in cell if r["source"] == source and r["method"] == m]
                        )
                    )
                    for m in [contrast["first"], contrast["second"]]
                }
                delta.append(means[contrast["second"]] - means[contrast["first"]])
            delta = np.array(delta)
            boot = np.sum(counts * delta, axis=1) / 8
            order = np.argsort(boot)
            cdf = np.cumsum(weights[order]) / 8**8
            limits = [float(boot[order[np.flatnonzero(cdf >= q)[0]]]) for q in [0.025, 0.975]]
            max_boot = max(
                max_boot,
                abs(delta.mean() - expected["mean_delta"]),
                float(
                    np.max(
                        np.abs(np.array(limits) - expected["source_bootstrap_percentiles_2p5_97p5"])
                    )
                ),
                float(np.max(np.abs(delta - expected["source_deltas"]))),
            )
            if (
                abs(np.average((boot - delta.mean()) ** 2, weights=weights) - np.var(delta) / 8)
                > 1e-10
            ):
                raise ValueError("Source bootstrap variance identity failed")
            bootstrap_fields += 11
    channels = 0
    for figure in report["finite_figures"]:
        binding = figure["bindings"]
        with np.load(checked(binding["arrays"]), allow_pickle=False) as z:
            data = {k: z[k][2:3] for k in ["packed", "colors", "wb", "matrix", "target"]}
        values = {
            "V143": np.load(checked(binding["parent"]), allow_pickle=False)[2:3],
            **{
                m: np.load(checked(v[2]), allow_pickle=False)[None]
                for m, v in binding["predictions"].items()
            },
        }
        png = np.asarray(Image.open(checked(figure["image"])))
        for panel in figure["panels"]:
            label = panel["label"]
            value = (
                noisy_malvar(data)
                if label == "Noisy Malvar"
                else data["target"]
                if label == "Exact constructed GT"
                else values[label]
            )
            cell = crop(value, data, figure["ROI_xywh"], figure["display_exposure"])
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(png[y : y + h, x : x + w], cell)
            channels += cell.size
    for figure in report["protected_real_figures"]:
        if (
            checked(figure["image"]).read_bytes()
            != checked(figure["adopted_original_image"]).read_bytes()
        ):
            raise ValueError("Adopted protected-real PNG bytes differ")
    if max_summary > 1e-10 or max_boot > 1e-10 or fields != 14976 or channels != 29491200:
        raise ValueError("Full summary/bootstrap/native verification differs")
    write_json(
        root / "independent-audit.json",
        {
            "status": "passed-streamed-full-cohort-independent-review",
            "report": reference(root / "report.json"),
            "rows": reference(root / "rows.json"),
            "summary": reference(root / "summary.json"),
            "auditor": reference(__file__),
            "independent_display_helper": reference(
                Path(__file__).with_name("audit_checkpoint_pilot.py")
            ),
            "metric_fields": fields,
            "summary_mean_fields": len(summary["means"]) * len(metrics),
            "bootstrap_fields": bootstrap_fields,
            "native_boards": len(report["finite_figures"]),
            "native_RGB_channels_exact": channels,
            "adopted_protected_real_boards_exact": len(report["protected_real_figures"]),
            "maximum_absolute_errors": {
                "finite_scalar": max_scalar,
                "summary_mean": max_summary,
                "source_bootstrap": max_boot,
            },
            "Torch_imported": False,
            "new_inference_calls": 0,
            "scope": "Independent L2/dot-product scalar reductions over every1152 row, separate stars-and-bars bootstrap enumeration and variance identity, channelwise RGB64 display against every native finite cell. Protected real boards adopted byte-for-byte from previously audited same-stage pilot. Shared known Malvar preview helper; real references remain qualitative and unscored.",
        },
    )
