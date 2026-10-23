"""Build a source-bound descriptive PSNR history from completed primary reports."""

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODEL_SELECTION = REPO / "configs/current-model.json"
STUDIES = [
    ("geometry-corpus-v34-v36-review.json", [32, 34, 35, 36], "geometry-corpus-v34-v36-review.md"),
    ("native-corpus-2k-review.json", [37, 39, 43], "native-corpus-2k-review.md"),
    (
        "long-commons-v63-v64-original20k-review.json",
        [63, 64],
        "long-commons-v63-v64-original20k-review.md",
    ),
    (
        "normalization-v68-v69-original4k-review.json",
        [68, 69],
        "normalization-v68-v69-original4k-review.md",
    ),
    (
        "packed-isotropic-mixed16-quarter-review-v1.json",
        [72, 73],
        "packed-isotropic-mixed16-quarter-review.md",
    ),
    (
        "reconstruction-objective-first1k-complete-v1.json",
        [74, 75],
        "reconstruction-objective-first1k-review.md",
    ),
    (
        "camera-supervision-first1k-complete-v1.json",
        [76, 77],
        "camera-supervision-first1k-review.md",
    ),
    (
        "directional-interval-original4k-complete-v1.json",
        [78, 79],
        "directional-interval-original4k-review.md",
    ),
    (
        "directional-bank-original4k-complete-v1.json",
        [80, 81],
        "directional-bank-original4k-review.md",
    ),
    (
        "bank-detachment-original4k-complete-v1.json",
        [82, 83],
        "bank-detachment-original4k-review.md",
    ),
    ("native-data-original20k-complete-v1.json", [84, 85], "native-data-original20k-review.md"),
    (
        "training-context-original4k-complete-v1.json",
        [86, 87],
        "training-context-original4k-review.md",
    ),
    ("spectral-original4k-primary-statistics-v1.json", [88, 89], "spectral-original4k-review.md"),
    ("late-rgb-original4k-primary-statistics-v1.json", [90, 91], "late-rgb-original4k-review.md"),
    (
        "late-rgb-head-only-original4k-primary-statistics-v1.json",
        [92],
        "late-rgb-head-only-original4k-review.md",
    ),
    (
        "v43-curated-original20k-primary-statistics-v1.json",
        [93, 94, 95],
        "v43-curated-original20k-review.md",
    ),
    (
        "v95-palette-primary-statistics-v1.json",
        [96, 97],
        "v95-flat-palette-quality-review.md",
    ),
    (
        "v95-adc-primary-statistics-v1.json",
        [98, 99],
        "v95-adc-training-quality-review.md",
    ),
    (
        "v84-curated-quality-primary-statistics-v1.json",
        [100, 101],
        "v84-curated-quality-review.md",
    ),
    (
        "v101-detail-diversity-primary-statistics-v1.json",
        [102, 103],
        "v102-v103-quality-review.md",
    ),
    (
        "v104-reviewed-corpus-primary-statistics-v1.json",
        [104],
        "v104-reviewed-corpus-quality.md",
    ),
]
METRICS = {
    ("full427", "photo", "srgb_psnr"): "photo_srgb_PSNR",
    ("known", "real", "sensor_psnr"): "known_CFA_PSNR",
    ("unseen", "real", "sensor_psnr"): "unseen_CFA_PSNR",
}
# Each missing metric must be intentional; older studies still require all panels.
REQUIRED_METRICS_BY_STUDY = {
    "v104-reviewed-corpus-photo-statistics-v1.json": ("photo_srgb_PSNR",),
}


def metric_points(points, field):
    """Omit unfinished panels rather than inventing or carrying forward a score."""
    completed = [p for p in points if field in p]
    for point in completed:
        value = point[field]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"Completed {field} must be finite: V{point['version']}")
    return [p["version"] for p in completed], [p[field] for p in completed]


def metric_text(point, field):
    return f"{point[field]:.5f}" if field in point else "pending"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_reference(item):
    path = Path(item["path"])
    assert digest(path) == item["sha256"], path
    return json.loads(path.read_text())


def primary(data):
    if "comparisons" in data:
        return data
    if "primary_comparisons" in data:
        return {"comparisons": data["primary_comparisons"]}
    value = data["primary_statistics"]
    if "data" in value:
        return value["data"]
    if "comparisons" in value:
        return value
    return checked_reference(value)


def collect():
    output, evidence = [], []
    for filename, versions, report in STUDIES:
        path = REPO / "docs/results" / filename
        source = json.loads(path.read_text())
        evidence.append(
            {
                "path": str(path.relative_to(REPO)),
                "sha256": digest(path),
                "versions": versions,
                "report": report,
            }
        )
        selected = {}
        if "runs" in source:
            for panel in ("full427", "known", "unseen"):
                if panel not in source["runs"]:
                    continue
                summary = source["runs"][panel]
                if "path" in summary and "sha256" in summary:
                    summary = checked_reference(summary)
                models = {m["label"]: m for m in summary["models"]}
                for row in summary["overall"]:
                    name = row["model"]
                    match = re.search(r"(?:-|\b)v(\d+)(?=:|-|\b)", name, re.IGNORECASE)
                    if not match or int(match[1]) not in versions:
                        continue
                    version = int(match[1])
                    model = models[name]
                    point = selected.setdefault(
                        version,
                        {
                            "version": version,
                            "checkpoint_sha256": model["sha256"],
                            "endpoint": f"step-{model['step']}",
                            "step": model["step"],
                            "report": report,
                            "source": filename,
                        },
                    )
                    assert point["checkpoint_sha256"] == model["sha256"]
                    effective = model.get("effective_model_config", model.get("model_config", {}))
                    if effective.get("adc_cfa_projection", False):
                        point["inference_policy"] = "ADC-only CFA projection"
                        point["endpoint"] = f"step-{model['step']} (ADC-projected)"
                    metric = "srgb_psnr" if panel == "full427" else "sensor_psnr"
                    if panel == "full427" and row["kind"] != "photo":
                        continue
                    field = "photo_srgb_PSNR" if panel == "full427" else panel + "_CFA_PSNR"
                    point[field] = row["metrics"][metric]["mean"]
                    point.setdefault("evaluation_metadata", {})[panel] = {
                        k: summary.get(k)
                        for k in (
                            "sources",
                            "protocol",
                            "precision",
                            "observation_and_metrics_precision",
                            "prepared_sha256",
                            "manifest_sha256",
                            "patch_size",
                            "native_crop",
                        )
                        if k in summary
                    }
        else:
            stats = primary(source)
            comparisons = stats["comparisons"]
            for row in comparisons:
                key = row.get("panel"), row.get("kind"), row.get("metric")
                if key not in METRICS:
                    continue
                assert row["sources"] == {"full427": 427, "known": 4, "unseen": 5}[row["panel"]]
                for side in ("first", "second"):
                    match = re.search(r"\bV(\d+)(?=\b|-|_)", row[side], re.IGNORECASE)
                    if not match or int(match[1]) not in versions:
                        continue
                    version, sha = int(match[1]), row[side + "_checkpoint_sha256"]
                    # Completed primary comparisons lead with their reviewed
                    # endpoint. Later own-parent/progress rows cannot replace it.
                    point = selected.setdefault(
                        version,
                        {
                            "version": version,
                            "checkpoint_sha256": sha,
                            "endpoint": row[side],
                            "report": report,
                            "source": filename,
                        },
                    )
                    if point["checkpoint_sha256"] != sha:
                        continue
                    value = row[side + "_source_balanced_mean"]
                    field = METRICS[key]
                    if field in point:
                        assert abs(point[field] - value) < 1e-9
                    point[field] = value
            # Bind raw evaluation provenance without re-evaluating predictions.
            for item in stats.get("sources", []):
                if not isinstance(item, dict):
                    continue
                for side in ("first", "second"):
                    entry = item.get(side, {})
                    if not isinstance(entry, dict):
                        continue
                    for point in selected.values():
                        if entry.get("checkpoint_sha256") == point["checkpoint_sha256"]:
                            point.setdefault("evaluation_sources", []).append(entry)
        assert set(selected) == set(versions), (filename, set(selected), versions)
        for point in selected.values():
            required = REQUIRED_METRICS_BY_STUDY.get(filename, tuple(METRICS.values()))
            assert all(k in point for k in required), (filename, point)
            for field in METRICS.values():
                metric_points([point], field)
            output.append(point)
    output.sort(key=lambda r: r["version"])
    assert len({r["version"] for r in output}) == len(output)
    return output, evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-sources",
        action="store_true",
        help="Recollect archived report references (requires the original local archives).",
    )
    parser.add_argument(
        "--preferred-version",
        type=int,
        help="Explicit documented recommendation while an active run pins an older selector.",
    )
    args = parser.parse_args()
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    destination = REPO / "docs/results/version-PSNR-history.json"
    selected = json.loads(MODEL_SELECTION.read_text())["preferred_version"]
    preferred = selected if args.preferred_version is None else args.preferred_version
    if args.refresh_sources:
        points, evidence = collect()
        result = {
            "description": "Selected fixed primary endpoints, chosen by study scope, never by highest score. Each plotted metric has a completed primary panel; pending metrics remain blank. Version numbers are experiment labels; architectures, data, initialization, training budgets and recorded compute precision differ. This is descriptive history, not a controlled ranking or training curve. Missing versions lack a selected comparable primary report here.",
            "panels": {
                "photo_srgb_PSNR": "427 fixed photos, seven noise/exposure conditions, four CFAs; source-balanced sRGB PSNR",
                "known_CFA_PSNR": "4 scenes/8 pairs/72 crops, scene-balanced measured-CFA PSNR",
                "unseen_CFA_PSNR": "5 scenes/10 pairs/90 crops, scene-balanced measured-CFA PSNR",
            },
            "working_reference": f"V{preferred} is the fully evaluated inference reference; V43 is a historical comparator",
            "model_selection": {
                "path": "configs/current-model.json",
                "sha256": digest(MODEL_SELECTION),
                "preferred_version": selected,
                "explicit_recommendation_override": args.preferred_version,
            },
            "sources": evidence,
            "points": points,
        }
        destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n")
    else:
        result = json.loads(destination.read_text())
        points, evidence = result["points"], result["sources"]
    for field in METRICS.values():
        metric_points(points, field)
    columns = [
        "version",
        "endpoint",
        "checkpoint_sha256",
        "inference_policy",
        *METRICS.values(),
        "report",
        "source",
    ]
    with destination.with_suffix(".csv").open("w") as stream:
        writer = csv.DictWriter(stream, columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(points)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )
    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6), sharex=True, layout="constrained")
    latest = points[-1]["version"]
    ticks = [32, 43, 63, 72, 78, 84, 92]
    if latest - ticks[-1] < 5:
        ticks[-1] = latest
    else:
        ticks.append(latest)
    reference = next(p for p in points if p["version"] == preferred)
    assert all(field in reference for field in METRICS.values()), "Reference panels are incomplete"
    for row in range(2):
        shown = points if row == 0 else [p for p in points if p["version"] not in (72, 73)]
        photo, camera = axes[row]
        photo.scatter(*metric_points(shown, "photo_srgb_PSNR"), c="#2563a6", s=24)
        photo.axhline(
            reference["photo_srgb_PSNR"],
            color="#d98b14",
            linewidth=1,
            linestyle="--",
            label=f"V{preferred} evaluated reference",
        )
        photo.scatter(
            [preferred],
            [reference["photo_srgb_PSNR"]],
            marker="*",
            c="#d98b14",
            edgecolors="#8c5a08",
            s=150,
            zorder=5,
        )
        photo.set_ylabel("Photo sRGB PSNR (dB)")
        for field, color, marker, title in [
            ("known_CFA_PSNR", "#2563a6", "o", "Known: 4 scenes"),
            ("unseen_CFA_PSNR", "#7c4c9c", "s", "Unseen: 5 scenes"),
        ]:
            camera.scatter(*metric_points(shown, field), c=color, marker=marker, s=23, label=title)
            camera.axhline(reference[field], color=color, linewidth=0.8, linestyle="--", alpha=0.6)
        camera.set_ylabel("Measured-CFA PSNR (dB)")
        for axis in (photo, camera):
            axis.axvline(preferred, color="#d98b14", linewidth=1, alpha=0.5)
            axis.grid(axis="y", color="#dce2e8", linewidth=0.6)
            axis.legend(loc="best", frameon=False, fontsize=8)
            axis.set_xticks(ticks)
        highlighted = (
            [43, preferred, 72, 92, latest] if row == 0 else [34, 43, 63, preferred, 92, latest]
        )
        for version in dict.fromkeys(highlighted):
            p = next(r for r in shown if r["version"] == version)
            if "photo_srgb_PSNR" not in p:
                continue
            offset, alignment = (0, 7), "center"
            if 0 < latest - preferred <= 3:
                if version == preferred:
                    offset, alignment = (-12, 20), "right"
                elif version == latest:
                    offset, alignment = (12, 6), "left"
            photo.annotate(
                f"V{version}" + (" (ADC)" if p.get("inference_policy") else ""),
                (version, p["photo_srgb_PSNR"]),
                xytext=offset,
                textcoords="offset points",
                ha=alignment,
                fontsize=8,
            )
    axes[0, 0].set_title(f"All {len(points)} selected endpoints", loc="left", fontsize=11)
    axes[0, 1].set_title(
        f"Measured CFA: {len(metric_points(points, 'known_CFA_PSNR')[0])} known / "
        f"{len(metric_points(points, 'unseen_CFA_PSNR')[0])} unseen endpoints",
        loc="left",
        fontsize=10,
    )
    axes[1, 0].set_title("Mature RGB models: closer view", loc="left", fontsize=11)
    axes[1, 1].set_title(
        "Camera detail: V72/V73 omitted only from this zoom", loc="left", fontsize=10
    )
    for axis in axes[1]:
        axis.set_xlabel("Model version (unequal training budgets)")
    fig.suptitle("PSNR by model version", fontsize=15)
    fig.supxlabel(
        f"Evaluated reference: V{preferred}. Pending metrics are omitted. ADC labels: ADC-only sample projection.\nTraining budgets/data differ. Full values and provenance: CSV/JSON.",
        fontsize=9,
        color="#4b5563",
    )
    for extension in ("png", "svg", "pdf"):
        fig.savefig(REPO / "docs/images" / ("version-PSNR-history." + extension), dpi=160)
    svg = REPO / "docs/images/version-PSNR-history.svg"
    svg.write_text("\n".join(line.rstrip() for line in svg.read_text().splitlines()) + "\n")
    rows = [
        "| Version / endpoint | Photo sRGB | Known CFA | Unseen CFA | Report |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for p in points:
        photo_value, known_value, unseen_value = [
            metric_text(p, field) for field in METRICS.values()
        ]
        rows.append(
            f"| V{p['version']} / {p['endpoint']} | {photo_value} | {known_value} | {unseen_value} | [Review]({p['report']}) |"
        )
    original = next(p for p in points if p["version"] == 43)
    (REPO / "docs/performance-history.md").write_text(
        f"# PSNR history\n\nV{preferred} is the fully evaluated inference reference, with "
        f"{reference['photo_srgb_PSNR']:.5f} dB photographic PSNR and "
        f"{reference['known_CFA_PSNR']:.5f}/{reference['unseen_CFA_PSNR']:.5f} dB "
        f"known/unseen measured-CFA PSNR. Its photographic change from V43 is "
        f"+{reference['photo_srgb_PSNR'] - original['photo_srgb_PSNR']:.2f} dB. "
        "Training histories differ; current strengths, tradeoffs and native comparisons "
        "are in the [model guide](current-model.md). A version names an experiment, "
        "not a training step.\n\n![PSNR versus model version](images/version-PSNR-history.png)\n\n"
        + result["description"]
        + f" Camera references are measured CFA samples; independently demosaiced RGB references are not exact GT. Small camera panels have scene uncertainty. The plot describes checkpoints with unequal budgets and data; use the linked comparisons to assess particular gains and weaknesses. Dashed lines show V{preferred}'s measured means. There are {len(metric_points(points, 'photo_srgb_PSNR')[0])} completed photo endpoints and {len(metric_points(points, 'known_CFA_PSNR')[0])}/{len(metric_points(points, 'unseen_CFA_PSNR')[0])} known/unseen camera endpoints. The lower panels omit V72/V73 RAW-native prototypes only to show the mature RGB range more clearly.\n\nAll photo points use the full fixed427-source panel, seven conditions and four CFAs. Known/unseen points balance captures within scenes, then scenes (4/5 scenes,72/90 crops). Precision, checkpoint hashes and per-source results remain in the source reports.\n\nV98/V99 use common ADC-only inference projection; only V99 trained through it. Their original V43/V95 references retain their checkpoint policies. The [completed ADC study](v95-adc-training-quality-review.md) improves ADC color but retains positive-noise color/detail weaknesses. Study-specific statistical gates do not prevent showing progress or choosing a stronger development baseline.\n\n"
        + "\n".join(rows)
        + "\n\n[CSV](results/version-PSNR-history.csv) · [Source records, checkpoint hashes and evaluation metadata](results/version-PSNR-history.json) · [SVG](images/version-PSNR-history.svg) · [PDF](images/version-PSNR-history.pdf). Rebuild from the shipped JSON with `source scripts/env.sh` then `.venv/bin/python scripts/plot_version_history.py`; `--refresh-sources` additionally audits and recollects the original local report archives. These figures reuse completed reports and perform no model inference. Native noisy/restored/reference crops remain in each linked review and the README.\n"
    )
    print({"versions": len(points), "source_reports": len(evidence), "data": str(destination)})


if __name__ == "__main__":
    main()
