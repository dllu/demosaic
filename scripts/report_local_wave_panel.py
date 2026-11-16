"""Full paired local/global RAW-wave review after all frozen outputs close."""

import argparse
import math
import os
import shutil
import sys
import time
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import (
    checked,
    freeze_sources,
    read_json,
    reference,
    verify_plan,
    write_json,
)

METHODS = ("V143", "global-t2", "local-t2")
METADATA = {"profile", "source", "placement", "method"}
REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").exists())


def prepare(producer, root):
    plan = read_json(producer / "plan.json")
    if len(plan["rows"]) != 1152 or len(plan["finite_groups"]) != 384 or plan["thresholds"] != [2]:
        raise ValueError("Require the original complete three-prior threshold2 panel")
    pilot = REPO / ".cache/experiments/local-validated-wave-pilot-v1"
    model = read_json(producer / "analytic-model-v2.json")
    old = read_json(pilot / "analytic-model-v2.json")
    if model["source"]["sha256"] != old["source"]["sha256"] or model["config"] != old["config"]:
        raise ValueError("Protected real crops must use this exact numerical stage/configuration")
    parent = model["parent_bindings_by_domain"]["finite-wire"]
    if parent["label"] != "V143" or set(parent["priors"]) != {"iso400", "iso1600", "iso6400"}:
        raise ValueError("Require all three actual V143 cache bindings")
    for item in parent["priors"].values():
        source = read_json(checked(item["source_plan"]))["parent"]
        if (
            item["parent"]["sha256"] != source["sha256"]
            or source["sha256"]
            != "96d146d017c54196288c585f8b7eddcf030e8a235061049c31e985b9380b7ce4"
        ):
            raise ValueError("The procedural parent must be the actual V143 cache checkpoint")
    root.mkdir(parents=True, exist_ok=False)
    work, files = freeze_sources(
        REPO,
        root,
        entries=(
            "report_local_wave_panel.py",
            "audit_local_wave_panel.py",
            "report_checkpoint_pilot.py",
            "audit_checkpoint_pilot.py",
        ),
    )
    own = {
        "producer": str(producer),
        "producer_plan": reference(producer / "plan.json"),
        "launch": reference(producer / "launch.json"),
        "lineage_watcher": reference(producer / "lineage-watcher-launch.json"),
        "model": reference(producer / "analytic-model-v2.json"),
        "pilot_model": reference(pilot / "analytic-model-v2.json"),
        "pilot_report": reference(pilot / "report-v2/report.json"),
        "pilot_audit": reference(pilot / "independent-audit-v2.json"),
        "work": str(work),
        "script": reference(work / "scripts/report_local_wave_panel.py"),
        "python": sys.executable,
        "expected_owner": read_json(producer / "launch.json")["owner"],
        "expected_watcher": read_json(producer / "lineage-watcher-launch.json"),
        "native_selection": {
            "sources": list(range(8)),
            "profiles": ["iso400", "iso1600", "iso6400"],
            "placements": ["near", "far"],
            "pattern": "RGGB",
            "repeat": 0,
            "role": 2,
            "ROI_xywh": [176, 176, 160, 160],
            "display_exposure": 2,
            "display_contrast": 1,
        },
        "inputs": [
            reference(producer / "plan.json"),
            reference(producer / "launch.json"),
            reference(producer / "analytic-model-v2.json"),
            reference(pilot / "analytic-model-v2.json"),
            reference(pilot / "report-v2/report.json"),
            reference(pilot / "independent-audit-v2.json"),
            reference(producer / "lineage-watcher-launch.json"),
        ],
        "frozen_files": files,
        "scope": "Wait for exact producer and lineage-correction completion, no signals/restarts. All1152 predictions must close before new GT analysis. Recover omitted CFA/repeat/index metadata by strict frozen row order; independently audit all1152 metric rows and native boards. Eight source geometries are bootstrap clusters, all64 views per cell retained. Exact empirical cluster-bootstrap percentiles over8^8 ordered resamples, not calibrated population confidence. Native selection fixed before full results:all48 RGGB/repeat0 source/prior/placement role2 cases, native160/exposure2; both protected real families adopted from identical completed pilot with accurate reference/JPEG labels. Zero new inference/RAW/noise/training work.",
    }
    own["inputs"].extend(item["source_plan"] for item in parent["priors"].values())
    write_json(root / "plan.json", own)
    verify_plan(own)
    return root / "plan.json"


def empirical_bootstrap_weights(n=8):
    def compositions(total, width):
        if width == 1:
            yield (total,)
        else:
            for count in range(total + 1):
                for rest in compositions(total - count, width - 1):
                    yield (count, *rest)

    counts = np.array(list(compositions(n, n)), np.int64)
    weights = np.array(
        [math.factorial(n) // math.prod(math.factorial(int(c)) for c in row) for row in counts],
        np.int64,
    )
    if int(weights.sum()) != n**n or counts.shape != (math.comb(2 * n - 1, n - 1), n):
        raise ValueError("Exact source-bootstrap weights are incomplete")
    return counts, weights


def summarize(rows):
    counts, weights = empirical_bootstrap_weights()
    metrics = [
        k
        for k in rows[0]
        if k not in METADATA | {"group_index", "cache_index", "pattern", "repeat"}
    ]
    means, contrasts = [], []
    for profile in ["iso400", "iso1600", "iso6400"]:
        for placement in ["near", "far"]:
            group = [r for r in rows if r["profile"] == profile and r["placement"] == placement]
            source_means = {}
            for method in METHODS:
                values = [r for r in group if r["method"] == method]
                if len(values) != 64:
                    raise ValueError("Require all64 CFA/repeat views in each cell")
                source_means[method] = []
                for source in range(8):
                    subset = [r for r in values if r["source"] == source]
                    if {(r["pattern"], r["repeat"]) for r in subset} != {
                        (p, t) for p in ["RGGB", "BGGR", "GRBG", "GBRG"] for t in [0, 1]
                    }:
                        raise ValueError("Source CFA/repeat cluster differs")
                    source_means[method].append(
                        {k: float(np.mean([r[k] for r in subset])) for k in metrics}
                    )
                means.append(
                    {
                        "profile": profile,
                        "placement": placement,
                        "method": method,
                        "views": 64,
                        "sources": 8,
                        **{
                            k: float(np.mean([v[k] for v in source_means[method]])) for k in metrics
                        },
                    }
                )
            for first, second in [
                ("V143", "global-t2"),
                ("V143", "local-t2"),
                ("global-t2", "local-t2"),
            ]:
                fields = {}
                for k in metrics:
                    delta = np.array(
                        [
                            b[k] - a[k]
                            for a, b in zip(source_means[first], source_means[second], strict=True)
                        ]
                    )
                    boot = counts @ delta / 8
                    order = np.argsort(boot, kind="stable")
                    cdf = np.cumsum(weights[order])
                    interval = [
                        float(boot[order[np.searchsorted(cdf, q * 8**8)]]) for q in [0.025, 0.975]
                    ]
                    if abs(np.average(boot, weights=weights) - delta.mean()) > 1e-12:
                        raise ValueError("Bootstrap mean does not preserve source weighting")
                    fields[k] = {
                        "mean_delta": float(delta.mean()),
                        "source_deltas": delta.tolist(),
                        "source_bootstrap_percentiles_2p5_97p5": interval,
                        "sources_increased": int((delta > 0).sum()),
                        "sources_decreased": int((delta < 0).sum()),
                    }
                pairs = {
                    m: {
                        (r["source"], r["pattern"], r["repeat"]): r
                        for r in group
                        if r["method"] == m
                    }
                    for m in [first, second]
                }
                changes = [(pairs[first][key], pairs[second][key]) for key in pairs[first]]
                contrasts.append(
                    {
                        "profile": profile,
                        "placement": placement,
                        "first": first,
                        "second": second,
                        "fields": fields,
                        "weak_increased_views": sum(
                            b["weak_gain"] > a["weak_gain"] for a, b in changes
                        ),
                        "quiet_decreased_views": sum(
                            b["quiet_error_RMS_DN16"] < a["quiet_error_RMS_DN16"]
                            for a, b in changes
                        ),
                        "weak_increment_error_decreased_views": sum(
                            b["weak_increment_error_RMS_DN16"] < a["weak_increment_error_RMS_DN16"]
                            for a, b in changes
                        ),
                        "weak_up_quiet_and_increment_down_views": sum(
                            b["weak_gain"] > a["weak_gain"]
                            and b["quiet_error_RMS_DN16"] < a["quiet_error_RMS_DN16"]
                            and b["weak_increment_error_RMS_DN16"]
                            < a["weak_increment_error_RMS_DN16"]
                            for a, b in changes
                        ),
                    }
                )
    return {
        "means": means,
        "contrasts": contrasts,
        "bootstrap": {
            "source_clusters": 8,
            "count_vectors": len(counts),
            "ordered_resamples_represented": 8**8,
            "random_draws": 0,
            "scope": "Exact empirical8-source paired bootstrap percentiles conditional on this fixed development cohort; not calibrated confidence for arbitrary scenes/camera noise.",
        },
    }


def report(root):
    from PIL import Image, ImageDraw, ImageFont
    from report_checkpoint_pilot import pixels

    from demosaic.archive_metrics import noisy_malvar

    own = read_json(root / "plan.json")
    verify_plan(own)
    producer = Path(own["producer"])
    plan, collection = (
        read_json(checked(own["producer_plan"])),
        read_json(producer / "collection.json"),
    )
    canonical, corrected = (
        read_json(producer / "finite-scores-v2.json"),
        read_json(producer / "collection-v2.json"),
    )
    original_scores = read_json(producer / "finite-scores.json")
    if canonical["original_scores"] != reference(producer / "finite-scores.json") or len(
        original_scores["rows"]
    ) != len(canonical["rows"]):
        raise ValueError("Canonical label-only score derivation is incomplete")
    for original, derived in zip(original_scores["rows"], canonical["rows"], strict=True):
        if {k: v for k, v in original.items() if k != "method"} != {
            k: v for k, v in derived.items() if k != "method"
        } or derived["method"] != ("V143" if original["method"] == "V120" else original["method"]):
            raise ValueError("Lineage correction changed numeric results")
    if (
        collection["plan"] != own["producer_plan"]
        or len(collection["rows"]) != 1152
        or collection["target_or_reference_arrays_loaded"] != 0
        or corrected["actual_original_collection"] != reference(producer / "collection.json")
        or corrected["model"] != own["model"]
    ):
        raise ValueError("Require complete input-only closure and verified corrected lineage")
    by_id = {r["id"]: r for r in collection["rows"]}
    if set(by_id) != {r["id"] for r in plan["rows"]} or len(canonical["rows"]) != 384 * 3:
        raise ValueError("Full case/scalar coverage differs")
    rows, bindings = [], []
    for index, group in enumerate(plan["finite_groups"]):
        meta = group["metadata"]
        for offset, method in enumerate(METHODS):
            value = canonical["rows"][index * 3 + offset]
            expected = {
                "profile": group["profile"],
                "source": meta["recipe"]["source"],
                "placement": meta["placement"],
                "method": method,
            }
            if any(value[k] != v for k, v in expected.items()):
                raise ValueError("Cannot recover unambiguous scalar metadata from frozen order")
            rows.append(
                {
                    **value,
                    "group_index": index,
                    "cache_index": group["index"],
                    "pattern": meta["pattern"],
                    "repeat": meta["repeat"],
                }
            )
        parent = next(r["parent"] for r in plan["rows"] if r["id"] == group["cases"][0])
        bindings.append(
            {
                "group_index": index,
                "arrays": group["arrays"],
                "parent": parent,
                "predictions": {
                    m: [by_id[c]["predictions"][m] for c in group["cases"]] for m in METHODS[1:]
                },
            }
        )
    write_json(
        root / "rows.json",
        {
            "scores": reference(producer / "finite-scores-v2.json"),
            "collection": reference(producer / "collection.json"),
            "rows": rows,
            "groups": bindings,
            "scope": "Original numeric rows unchanged; CFA/repeat/index restored from verified original loop order.",
        },
    )
    summary = summarize(rows)
    write_json(root / "summary.json", {"rows": reference(root / "rows.json"), **summary})
    output = root / "native"
    output.mkdir()
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 10)
    figures = []
    selection = own["native_selection"]

    def board(name, cells, metadata):
        canvas = Image.new("RGB", (8 + 168 * len(cells), 192), "#eeeeee")
        draw, panels = ImageDraw.Draw(canvas), []
        for i, (label, cell) in enumerate(cells):
            if cell.shape != (160, 160, 3) or cell.dtype != np.uint8:
                raise ValueError("Require unchanged native160 RGB8")
            x, y = 8 + 168 * i, 24
            draw.text((x, 5), label, font=font, fill="black")
            canvas.paste(Image.fromarray(cell), (x, y))
            panels.append({"label": label, "xywh": [x, y, 160, 160]})
        path = output / (name + ".png")
        canvas.save(path)
        saved = np.asarray(Image.open(path))
        for panel, (_, cell) in zip(panels, cells, strict=True):
            x, y, w, h = panel["xywh"]
            np.testing.assert_array_equal(saved[y : y + h, x : x + w], cell)
        figures.append({"image": reference(path), "panels": panels, **metadata})

    for group, binding in zip(plan["finite_groups"], bindings, strict=True):
        meta = group["metadata"]
        if meta["pattern"] != "RGGB" or meta["repeat"] != 0:
            continue
        with np.load(checked(group["arrays"]), allow_pickle=False) as z:
            data = {k: z[k][2:3] for k in ["packed", "colors", "wb", "matrix", "target"]}
        values = {
            "V143": np.load(checked(binding["parent"]), allow_pickle=False)[2:3],
            **{
                m: np.load(checked(v[2]), allow_pickle=False)[None]
                for m, v in binding["predictions"].items()
            },
        }
        roi, exposure = selection["ROI_xywh"], selection["display_exposure"]
        cells = [("Noisy Malvar", pixels(noisy_malvar(data), data, roi, exposure))]
        cells.extend((m, pixels(v, data, roi, exposure)) for m, v in values.items())
        cells.append(("Exact constructed GT", pixels(data["target"], data, roi, exposure)))
        metadata = {
            "group_index": binding["group_index"],
            "group": group,
            "bindings": binding,
            "ROI_xywh": roi,
            "display_exposure": exposure,
            "display_contrast": 1,
            "calibration": {k: data[k].tolist() for k in ["wb", "matrix"]},
            "analytic_model": own["model"],
            "no_resize": True,
        }
        name = f"{group['profile']}-source{meta['recipe']['source']}-{meta['placement']}"
        board(name + "-comparison", cells, metadata)
        board(name + "-triplet", [cells[0], cells[3], cells[4]], metadata)
    if len(figures) != 96:
        raise ValueError("Predeclared48 paired native cases are incomplete")
    real = []
    real_output = root / "protected-real"
    real_output.mkdir()
    pilot_report = read_json(checked(own["pilot_report"]))
    for figure in pilot_report["figures"]:
        if figure["source"]["kind"] not in ["gfx", "mesh"]:
            continue
        source = checked(figure["image"])
        target = real_output / source.name
        shutil.copyfile(source, target)
        real.append(
            {**figure, "image": reference(target), "adopted_original_image": figure["image"]}
        )
    if len(real) != 16:
        raise ValueError("All protected real comparisons/triplets must remain present")
    write_json(
        root / "report.json",
        {
            "plan": reference(root / "plan.json"),
            "collection": reference(producer / "collection.json"),
            "model": own["model"],
            "summary": reference(root / "summary.json"),
            "finite_figures": figures,
            "protected_real_figures": real,
            "scope": "All48 fixed finite-wire cases/96 native boards plus16 exact adopted protected-real boards. Real ISO100/AHD/JPEG references are qualitative, not exact GT or scored. Original real source/ROI/noise/exposure/JPEG/checkpoint metadata retained. Actual viewing and independent audit pending.",
        },
    )
    plot(root, rows, summary)


def plot(root, rows, summary):
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    for metric, short in [
        ("quiet_error_RMS_DN16", "quiet"),
        ("weak_increment_error_RMS_DN16", "increment"),
    ]:
        fig, axes = plt.subplots(2, 3, figsize=(11, 6), layout="constrained")
        for iy, placement in enumerate(["near", "far"]):
            for ix, profile in enumerate(["iso400", "iso1600", "iso6400"]):
                ax = axes[iy, ix]
                subset = [
                    r for r in rows if r["placement"] == placement and r["profile"] == profile
                ]
                base = {r["group_index"]: r for r in subset if r["method"] == "V143"}
                for method, color in [("global-t2", "#de8431"), ("local-t2", "#2678b6")]:
                    values = [r for r in subset if r["method"] == method]
                    x = [r[metric] - base[r["group_index"]][metric] for r in values]
                    y = [
                        100 * (r["weak_gain"] - base[r["group_index"]]["weak_gain"]) for r in values
                    ]
                    ax.scatter(x, y, s=9, alpha=0.35, color=color)
                    c = next(
                        v
                        for v in summary["contrasts"]
                        if v["profile"] == profile
                        and v["placement"] == placement
                        and v["first"] == "V143"
                        and v["second"] == method
                    )
                    sx, sy = c["fields"][metric], c["fields"]["weak_gain"]
                    mx, my = sx["mean_delta"], 100 * sy["mean_delta"]
                    bx = sx["source_bootstrap_percentiles_2p5_97p5"]
                    by = [100 * z for z in sy["source_bootstrap_percentiles_2p5_97p5"]]
                    ax.errorbar(
                        mx,
                        my,
                        xerr=np.array([[mx - bx[0]], [bx[1] - mx]]).clip(0),
                        yerr=np.array([[my - by[0]], [by[1] - my]]).clip(0),
                        fmt="o",
                        ms=6,
                        color=color,
                        label=method,
                        capsize=3,
                    )
                ax.axvline(0, color="gray", lw=0.6)
                ax.axhline(0, color="gray", lw=0.6)
                ax.set_title(profile + " / " + placement)
                ax.set_xlabel(short + " RMS change (DN16)")
                ax.set_ylabel("Weak response change (pp)")
                if (iy, ix) == (0, 0):
                    ax.legend(fontsize=8)
        fig.suptitle(
            "Fixed t2:64 views/cell; means and marginal8-source empirical-bootstrap percentiles"
        )
        fig.savefig(root / ("response-" + short + ".png"), dpi=160)
        plt.close(fig)


def run(root):
    import psutil

    own = read_json(root / "plan.json")
    verify_plan(own)
    if reference(__file__) != own["script"]:
        raise RuntimeError("Require frozen review source")
    (root / "run.claim").open("x").close()
    identity = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    write_json(root / "owner.json", identity)
    write_json(
        root / "status.json",
        {
            "status": "waiting-for-exact-completed-full-panel",
            "owner": identity,
            "plan": reference(root / "plan.json"),
        },
    )
    producer = Path(own["producer"])
    deadline = time.monotonic() + 10800
    while True:
        state = read_json(producer / "status.json")
        if (
            state["owner"] != own["expected_owner"]
            or state["plan"] != own["producer_plan"]
            or state["status"].startswith("failed")
        ):
            raise RuntimeError("Original producer identity/status changed")
        if (producer / "lineage-correction-result.json").exists() and state["status"].startswith(
            "completed-three-prior-numerical"
        ):
            break
        if not state["status"].startswith("completed-three-prior-numerical"):
            p = psutil.Process(own["expected_owner"]["pid"])
            if p.create_time() != own["expected_owner"]["created"] or not p.is_running():
                raise RuntimeError("Expected producer owner is no longer live")
        else:
            watcher = own["expected_watcher"]["owner"]
            p = psutil.Process(watcher["pid"])
            if p.create_time() != watcher["created"] or not p.is_running():
                raise RuntimeError(
                    "Original lineage watcher stopped without its completion receipt"
                )
        if time.monotonic() > deadline:
            raise TimeoutError("Bounded review wait expired; no source restart")
        time.sleep(15)
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    write_json(
        root / "status.json",
        {
            "status": "running-completed-panel-analysis",
            "owner": identity,
            "plan": reference(root / "plan.json"),
        },
        replace=True,
    )
    report(root)
    from audit_local_wave_panel import audit

    audit(root)
    if "torch" in sys.modules:
        raise RuntimeError("Read-only review unexpectedly imported Torch")
    write_json(
        root / "completed.json",
        {
            "status": "completed-full-numerical-native-audit-awaiting-viewing",
            "report": reference(root / "report.json"),
            "audit": reference(root / "independent-audit.json"),
            "summary": reference(root / "summary.json"),
            "new_inference_calls": 0,
        },
    )
    write_json(
        root / "status.json",
        {
            "status": "completed-full-numerical-native-audit-awaiting-viewing",
            "owner": identity,
            "completed": reference(root / "completed.json"),
        },
        replace=True,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode", choices=["prepare", "run"])
    p.add_argument("root", type=Path)
    p.add_argument(
        "--producer", type=Path, default=REPO / ".cache/experiments/local-validated-wave-panel-v1"
    )
    args = p.parse_args()
    if args.mode == "prepare":
        print(prepare(args.producer.resolve(), args.root.resolve()))
    else:
        try:
            run(args.root.resolve())
        except BaseException as error:
            write_json(
                args.root.resolve() / "failure.json",
                {"error": repr(error), "no_training_or_inference_signals": True},
            )
            raise
