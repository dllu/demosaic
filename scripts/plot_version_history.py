"""Build a source-bound descriptive PSNR history from completed primary reports."""

import argparse
import csv
import gzip
import hashlib
import json
import math
import re
import tarfile
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MODEL_SELECTION = REPO / "configs/current-model.json"
COVERAGE_NOTE = (
    "**Coverage reviewed November 19, 2026.** Corpus 20k and Corpus 100k have "
    "completed the fixed photo and both camera panels. "
    "Corpus 100k gains 0.20739 dB on the 427-photo panel over V120, with "
    "a 0.03046 dB unseen-camera loss. "
    "[Corpus 20k](full-corpus-control20k-primary.md) · "
    "[Corpus 100k](full-corpus-long100k.md#broader-evaluation). "
    "Both matched scene 12k endpoints have [completed fixed camera panels](expanded-scene-12000-cameras.md). "
    "The matched near-ADC 800-update endpoints also have [completed camera panels](near-adc-bridge-cameras.md). "
    "The matched scene 50k pair and two 512-update continuations have "
    "[completed fixed camera panels](scene-50000-cameras.md). "
    "The two independent-redraw endpoints also have "
    "[completed fixed camera panels](local-redraw-average.md#fixed-camera-panels). "
    "The mean-redraw parent and three repeat and gap continuations have completed "
    "[the fixed photo panel](local-redraw-stability.md#fixed-photo-panel) and "
    "[both camera panels](local-redraw-stability.md#fixed-camera-panels). "
    "The three signed wire continuations have completed "
    "[the fixed photo panel](local-wire-response.md#fixed-photo-panel) and "
    "[both camera panels](local-wire-response.md#fixed-camera-panels). "
    "The continuing-wire trial has "
    "[completed fixed camera panels](local-continuing-wire.md#fixed-camera-panels). "
    "Both regional weak-wire endpoints have "
    "[completed fixed camera panels](local-regional-wire-1024.md#fixed-camera-panels). "
    "Thirteen full427 scores are pending. "
    "The V131 point uses the independent CPU-to-CPU audit: photo 37.08008 dB, "
    "known/unseen CFA 54.31993/53.96491 dB. Its photo gain has unseen-camera and "
    "ADC-color costs; see the [broad review](v131-broad-primary.md). "
    "V132 has only a targeted endpoint review, and V198/V200 and later detail "
    "components use different panels. They do not have comparable full427 points "
    "here. The opt-in V131 ADC-only repair is not a second all-condition point. "
    "The [previous chart and registry](history/before-2026-11-17-cleanup/performance-history.md) "
    "are preserved."
)
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
    ("v111-v112-primary-quality-v1.json", [111, 112], "v111-v112-primary-quality.md"),
    ("v114-v115-quality-complete-v1.json", [114, 115], "v114-v115-quality.md"),
    ("v116-quality-complete-v1.json", [116], "v116-quality.md"),
    ("v117-v118-quality-complete-v1.json", [117, 118], "v117-v118-quality.md"),
    ("v119-quality-complete-v1.json", [119], "v119-quality.md"),
    ("v120-v121-primary-v1.json", [120, 121], "v120-v121-primary.md"),
    ("v122-v123-quality-complete-v1.json", [122, 123], "v122-v123-quality.md"),
    (
        "v131-broad-completed-v1/audit-audited-comparisons-v2.json.gz",
        [131],
        "v131-broad-primary.md",
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
    "v111-camera-complete-v1.json": ("known_CFA_PSNR", "unseen_CFA_PSNR"),
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
            raise ValueError(f"Completed {field} must be finite: {endpoint_label(point)}")
    return [p.get("plot_position", p["version"]) for p in completed], [p[field] for p in completed]


def endpoint_label(point):
    return point.get("label", f"V{point['version']}")


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
        source = json.loads(
            gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
        )
        evidence.append(
            {
                "path": str(path.relative_to(REPO)),
                "sha256": digest(path),
                "versions": versions,
                "report": report,
            }
        )
        selected = {}
        if filename == "v131-broad-completed-v1/audit-audited-comparisons-v2.json.gz":
            # Use the canonical CPU-to-CPU independent audit, not the earlier
            # mixed-precision comparison or the four-material endpoint means.
            plan_path = path.with_name("producer-plan.json.gz")
            plan = json.loads(gzip.decompress(plan_path.read_bytes()))
            checkpoint = next(c for c in plan["checkpoints"] if c["arm"] == "V131")
            step = checkpoint["expected_lineage"]["step"]
            assert step == 20000
            point = {
                "version": 131,
                "checkpoint_sha256": checkpoint["sha256"],
                "endpoint": "step-20000",
                "step": step,
                "report": report,
                "source": filename,
                "evaluation_metadata": {},
            }
            evidence.append(
                {
                    "path": str(plan_path.relative_to(REPO)),
                    "sha256": digest(plan_path),
                    "versions": versions,
                    "report": report,
                }
            )
            for stage, field, metric, units, observations in (
                ("photo", "photo_srgb_PSNR", "srgb_psnr", 427, 11956),
                ("known", "known_CFA_PSNR", "sensor_psnr", 4, 72),
                ("unseen", "unseen_CFA_PSNR", "sensor_psnr", 5, 90),
            ):
                row = next(
                    r for r in source["stages"][stage]["comparisons"] if r["metric"] == metric
                )
                assert (row["units"], row["observations"]) == (units, observations)
                point[field] = row["current_mean"]
                point["evaluation_metadata"][stage] = {
                    "units": units,
                    "observations": observations,
                    "precision": "Independent NumPy64 audit of saved FP32 predictions",
                    "input_provenance": plan["stages"][stage],
                }
            selected[131] = point
        elif "runs" in source:
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


def attach_corpus_photo(point, path, arm, camera_models):
    """Attach a source-balanced fixed photo score with its verified collector."""
    photo = json.loads(path.read_text())
    archive = REPO / photo["archive"]["path"]
    assert photo["all_complete"] and digest(archive) == photo["archive"]["sha256"]
    with tarfile.open(archive) as bundle:
        result_bytes = bundle.extractfile("collector-result.json").read()
    assert hashlib.sha256(result_bytes).hexdigest() == photo["source_result"]["sha256"]
    primary = json.loads(result_bytes)
    assert primary["all_complete"] and primary["kind"] == "full" and primary["cases"] == 3162
    assert photo["photo_sources"] == len(photo["source_averages"]) == 427
    assert (photo["noise_conditions"], photo["CFAs"], photo["observations_per_model"]) == (7, 4, 11956)
    assert primary["models"] == photo["models"]
    for label in (arm, "V120"):
        assert photo["models"][label]["checkpoint"] == camera_models[label]["checkpoint"]
        row = next(
            row for row in primary["summaries"]["photo"]["overall"]
            if row["model"] == label and row["kind"] == "photo"
        )
        metric = row["metrics"]["srgb_psnr"]
        assert metric["count"] == 427
        assert math.isclose(
            metric["mean"], photo["source_balanced"][label]["srgb_psnr"], rel_tol=0, abs_tol=1e-11
        )
        if label == arm:
            point["photo_srgb_PSNR"] = metric["mean"]
    point["inference_policy"] = "EMA, CPU IEEE FP32, exact canonical inputs"
    point["evaluation_metadata"]["photo"] = {
        "photo_sources": 427,
        "observations_per_model": photo["observations_per_model"],
        "conditions": 7,
        "CFAs": 4,
        "canonical_inputs_sha256": photo["canonical_inputs"]["sha256"],
        "precision": "CPU IEEE FP32",
    }
    return photo, archive


def collect_corpus_endpoints():
    """Bind completed photo and camera panels for the named corpus endpoints."""
    directory = REPO / "docs/results"
    short_camera = directory / "full-corpus-control20k-camera-v1/summary.json"
    short_photo = directory / "full-corpus-control20k-primary-v1/primary.json"
    long_photo = directory / "full-corpus-long100k-primary-v1/primary.json"
    long_camera = directory / "full-corpus-long100k-camera-v1/publication.json"
    long_training = directory / "full-corpus-long100k-training-v1/publication.json"
    short, long, training = (
        json.loads(path.read_text()) for path in (short_camera, long_camera, long_training)
    )
    assert long["complete_camera_panels"]
    short_arm, long_arm = "scale-control20k", "scale-long100k"
    short_model, long_model = short["models"][short_arm], training["model"]
    assert all(model["weights"] == "EMA" for model in (short_model, long_model))
    long_archive = long_camera.with_name(Path(long["archive"]["path"]).name)
    assert digest(long_archive) == long["archive"]["sha256"]
    with tarfile.open(long_archive) as archive:
        long_panels = {
            stage: json.load(archive.extractfile(f"{stage}/analysis.json"))
            for stage in ("known", "unseen")
        }
    short_point = {
        "version": None,
        "label": "Corpus 20k",
        "endpoint": short_arm,
        "step": short_model["step"],
        "checkpoint_sha256": short_model["checkpoint"]["sha256"],
        "report": "full-corpus-control20k-primary.md",
        "source": str(short_photo.relative_to(directory)),
        "evaluation_metadata": {},
    }
    long_point = {
        "version": None,
        "label": "Corpus 100k",
        "endpoint": long_arm,
        "step": long_model["step"],
        "checkpoint_sha256": long_model["checkpoint"]["sha256"],
        "report": "full-corpus-long100k.md",
        "source": str(long_photo.relative_to(directory)),
        "evaluation_metadata": {},
    }
    short_panels = []
    for stage, batches, scenes in (("known", 24, 4), ("unseen", 30, 5)):
        short_path = short_camera.with_name(f"{stage}.json")
        short_panels.append(short_path)
        paired_panels = (
            (json.loads(short_path.read_text()), short_arm, short_model),
            (long_panels[stage], long_arm, long_model),
        )
        camera = long["results"][stage]
        assert (camera["batches"], camera["metric_rows"]) == (batches, scenes * 36)
        assert len(camera["scenes"]) == scenes * 2
        assert camera["overall"]["V120"]["sensor_psnr"] == short["measured_CFA_PSNR"][stage]["V120"]
        field = f"{stage}_CFA_PSNR"
        short_point[field] = short["measured_CFA_PSNR"][stage][short_arm]
        long_point[field] = camera["overall"][long_arm]["sensor_psnr"]
        for point, (panel, arm, model) in zip(
            (short_point, long_point), paired_panels, strict=True
        ):
            assert panel["models"][arm]["checkpoint"]["sha256"] == model["checkpoint"]["sha256"]
            assert panel["models"]["V120"]["checkpoint"] == short["models"]["V120"]["checkpoint"]
            assert len(panel["cases"]) == batches and len(panel["per_scene"]) == 2 * scenes
            assert all(check["scores_bit_exact"] for check in panel["metric_checks"])
            actual = next(row for row in panel["summary"]["overall"] if row["model"] == arm)
            assert actual["metrics"]["sensor_psnr"]["mean"] == point[field]
            point["evaluation_metadata"][stage] = {
                "scene_count": scenes,
                "native_crops_per_model": scenes * 18,
                "precision": "CPU IEEE FP32 with measured-CFA reference",
            }
    short_result, short_archive = attach_corpus_photo(short_point, short_photo, short_arm, short["models"])
    long_result, long_photo_archive = attach_corpus_photo(
        long_point, long_photo, long_arm, long_panels["known"]["models"]
    )
    assert short_result["canonical_inputs"] == long_result["canonical_inputs"]
    assert short_result["known_unseen_camera_PSNR"] == short["measured_CFA_PSNR"]
    for stage in ("known", "unseen"):
        assert long_result["known_unseen_camera_PSNR"][stage] == {
            arm: long["results"][stage]["overall"][arm]["sensor_psnr"] for arm in ("V120", long_arm)
        }
    evidence = [
        {
            "path": str(path.relative_to(REPO)),
            "sha256": digest(path),
            "endpoints": [point["endpoint"]],
            "report": point["report"],
        }
        for point, path in (
            (short_point, short_photo),
            (short_point, short_archive),
            (short_point, short_camera),
            *((short_point, path) for path in short_panels),
            (long_point, long_camera),
            (long_point, long_archive),
            (long_point, long_training),
            (long_point, long_photo),
            (long_point, long_photo_archive),
        )
    ]
    return [short_point, long_point], evidence


def collect_matched_camera_endpoints(path, report, prefix, labels, step):
    """Bind selected EMA checkpoints from a completed camera-only archive."""
    record = json.loads(path.read_text())
    assert record["complete_camera_panels"] and record["weights"] == "EMA"
    source = REPO / record["archive"]["path"]
    assert digest(source) == record["archive"]["sha256"]
    points = []
    for arm, label in labels.items():
        model = record["models"][arm]
        assert model["step"] == step
        points.append(
            {
                "version": None,
                "label": label,
                "endpoint": f"{prefix}-{arm}",
                "step": model["step"],
                "checkpoint_sha256": model["checkpoint"]["sha256"],
                "inference_policy": "EMA, CPU IEEE FP32, exact canonical inputs",
                "report": report,
                "source": str(path.relative_to(REPO / "docs/results")),
                "evaluation_metadata": {},
            }
        )
    with tarfile.open(source) as bundle:
        for stage, batches, scenes in (("known", 24, 4), ("unseen", 30, 5)):
            panel = record["panels"][stage]
            assert (panel["batches"], panel["scenes"], panel["crops_per_model"]) == (
                batches, scenes, scenes * 18
            )
            raw = bundle.extractfile(f"{stage}/analysis.json").read()
            assert hashlib.sha256(raw).hexdigest() == panel["analysis"]["sha256"]
            analyzed = json.loads(raw)
            assert analyzed["models"] == record["models"] and analyzed["stage"] == stage
            assert len(analyzed["cases"]) == batches
            for point, arm in zip(points, labels, strict=True):
                metric = next(r for r in analyzed["summary"]["overall"] if r["model"] == arm)
                mean = metric["metrics"]["sensor_psnr"]["mean"]
                assert metric["metrics"]["sensor_psnr"]["count"] == scenes
                assert mean == panel["overall"][arm]["sensor_psnr"]
                checks = [check for check in analyzed["metric_checks"] if check["arm"] == arm]
                assert len(checks) == batches and all(c["scores_bit_exact"] for c in checks)
                assert sum(c["native_predictions"] for c in checks) == scenes * 18
                point[f"{stage}_CFA_PSNR"] = mean
                point["evaluation_metadata"][stage] = {
                    "scene_count": scenes,
                    "native_crops_per_model": scenes * 18,
                    "canonical_inputs_sha256": record["canonical_inputs"]["sha256"],
                    "precision": "CPU IEEE FP32 with measured-CFA reference",
                }
    evidence = [
        {
            "path": str(p.relative_to(REPO)),
            "sha256": digest(p),
            "endpoints": [point["endpoint"] for point in points],
            "report": report,
        }
        for p in (path, source)
    ]
    return points, evidence


def collect_expanded_scene_endpoints():
    path = REPO / "docs/results/expanded-scene-12000-v2/matched-primary-cameras.json"
    models = json.loads(path.read_text())["models"]
    assert all(models[arm]["kind"] == "scene" for arm in ("none", "spatial"))
    return collect_matched_camera_endpoints(
        path, "expanded-scene-12000-cameras.md", "expanded-scene-12000",
        {"none": "Local-only 12k", "spatial": "Spatial 12k"}, 12000,
    )


def collect_near_adc_endpoints():
    directory = REPO / "docs/results"
    path = directory / "near-adc-camera-audit-v1/publication.json"
    training = directory / "near-adc-bridge-training-v1/completed-training.json"
    trained = json.loads(training.read_text())["models"]
    measured = json.loads(path.read_text())
    labels = {"bridge-control": "Noise control 800", "bridge-trained": "Near-ADC 800"}
    for arm, key in (("bridge-control", "control"), ("bridge-trained", "bridge")):
        expected, actual = trained[key], measured["models"][arm]
        assert expected["checkpoint"] == actual["checkpoint"]
        assert expected["weights_for_review"] == actual["weights"] == "EMA"
        assert expected["step"] == actual["step"] == 800
    report = "near-adc-bridge-cameras.md"
    points, evidence = collect_matched_camera_endpoints(path, report, "near-adc", labels, 800)
    evidence.append(
        {
            "path": str(training.relative_to(REPO)),
            "sha256": digest(training),
            "endpoints": [point["endpoint"] for point in points],
            "report": report,
        }
    )
    return points, evidence


def collect_compact_camera_endpoints(path, report, prefix, names):
    """Bind trained endpoints to a complete compact CUDA camera archive."""
    record = json.loads(path.read_text())
    assert record["complete_camera_panels"] and record["weights"] == "EMA"
    assert max(map(abs, record["V120_minus_archived_dB"].values())) < 1e-4
    archive = REPO / record["archive"]["path"]
    assert digest(archive) == record["archive"]["sha256"]
    points = []
    with tarfile.open(archive) as evidence:
        plan_data = evidence.extractfile("plan.json").read()
        assert hashlib.sha256(plan_data).hexdigest() == record["plan"]["sha256"]
        assert json.loads(plan_data)["models"] == record["models"]
        stage_results = {}
        for stage, count, scenes in (("known", 24, 4), ("unseen", 30, 5)):
            data = evidence.extractfile(f"{stage}/analysis.json").read()
            assert hashlib.sha256(data).hexdigest() == record["analysis"][stage]["sha256"]
            panel = json.loads(data)
            assert panel == record["panels"][stage] and panel["matching_canonical_arrays"]
            assert (panel["batches"], panel["scenes"], panel["crops_per_model"]) == (
                count, scenes, 18 * scenes,
            )
            assert len(panel["cases"]) == count
            for sequence, case in enumerate(panel["cases"]):
                raw = evidence.extractfile(f"{stage}/cases/{sequence:05d}.json").read()
                assert hashlib.sha256(raw).hexdigest() == case["sha256"]
                value = json.loads(raw)
                assert value["stage"] == stage and value["batch"] == sequence
                assert value["plan"] == record["plan"]
            stage_results[stage] = panel
        for arm, (label, step) in names.items():
            specification = record["models"][arm]
            assert specification["step"] == step and specification["kind"] == "scene"
            point = {
                "version": None,
                "label": label,
                "endpoint": f"{prefix}-{arm}",
                "step": step,
                "checkpoint_sha256": specification["checkpoint"]["sha256"],
                "inference_policy": "EMA, CUDA IEEE FP32, exact canonical inputs",
                "source": str(path.relative_to(REPO / "docs/results")),
                "report": report,
                "evaluation_metadata": {},
            }
            for stage, panel in stage_results.items():
                measurement = panel["overall"][arm]
                values = list(measurement["per_scene"].values())
                assert len(values) == panel["scenes"]
                assert math.isclose(sum(values) / len(values), measurement["sensor_psnr"])
                point[f"{stage}_CFA_PSNR"] = measurement["sensor_psnr"]
                point["evaluation_metadata"][stage] = {
                    "scene_count": panel["scenes"],
                    "native_crops_per_model": panel["crops_per_model"],
                    "canonical_inputs_sha256": record["canonical_inputs"]["sha256"],
                    "precision": record["precision"],
                }
            points.append(point)
    sources = [
        {
            "path": str(p.relative_to(REPO)),
            "sha256": digest(p),
            "endpoints": [point["endpoint"] for point in points],
            "report": report,
        }
        for p in (path, archive)
    ]
    return points, sources


def collect_compact_scene_endpoints():
    path = REPO / "docs/results/scene-050000-camera-v1/publication.json"
    names = {
        "none": ("Local 50k", 50000),
        "spatial": ("Spatial 50k", 50000),
        "absolute": ("Absolute +512", 512),
        "paired": ("Paired +512", 512),
    }
    return collect_compact_camera_endpoints(
        path, "scene-50000-cameras.md", "scene-050000", names
    )


def attach_compact_photo_endpoints(points, source, camera_source, names, report):
    """Attach a compact CUDA photo panel after auditing all source observations."""
    photo = json.loads(source.read_text())
    camera = json.loads(camera_source.read_text())
    assert photo["complete"] and photo["weights"] == camera["weights"] == "EMA"
    matches = ("plan", "canonical_inputs", "models")
    assert all(photo[k] == camera[k] for k in matches)
    archive = REPO / photo["archive"]["path"]
    assert digest(archive) == photo["archive"]["sha256"]
    means = {}
    with tarfile.open(archive) as bundle:
        def load(name, ref):
            raw = bundle.extractfile(name).read()
            assert hashlib.sha256(raw).hexdigest() == ref["sha256"]
            return json.loads(raw)

        result = load("collector-result.json", photo["collector"])
        plan = load("plan.json", photo["plan"])
        canonical = load("canonical-inputs.json", photo["canonical_inputs"])
        preflight = load("preflight.json", photo["qualification"])
        assert result["complete"] and result["scope"] == "full"
        assert result["counts"] == photo["counts"] == {"known": 24, "unseen": 30, "photo": 3108}
        assert all(result[k] == photo[k] for k in (*matches, "policy"))
        assert result["models"] == plan["models"] == preflight["models"]
        assert result["policy"] == plan["policy"] and result["policy"].startswith("CUDA")
        assert plan["canonical_inputs"] == result["canonical_inputs"]
        assert result["qualification"] == photo["qualification"]
        assert preflight["scope"] == "preflight" and preflight["plan"] == result["plan"]
        checks = preflight["V120_CPU_comparisons"]
        assert any(r["stage"] == "photo" for r in checks)
        assert max(abs(delta) for item in checks for delta in item["delta_dB"]) < 1e-4
        assert canonical["all_input_witnesses_exact"]
        witnesses = {r["batch"]: r for r in canonical["records"] if r["stage"] == "photo"}
        case_refs = {Path(r["path"]).stem: r for r in result["cases"]}
        assert len(case_refs) == len(result["cases"]) == 3162
        assert len(witnesses) == 3108
        samples = {arm: defaultdict(dict) for arm in result["models"]}
        axes = set()
        for index in range(3108):
            native = witnesses[index]
            case = load(f"photo/{index:05d}.json", case_refs[f"photo-{index:05d}"])
            assert case["plan"] == result["plan"] and case["arrays"] == native["arrays"]
            assert (case["stage"], case["batch"]) == ("photo", index)
            assert set(case["variants"]) == set(samples)
            context = native["context"]
            axis = (context["condition"]["name"], context["pattern"])
            axes.add(axis)
            for arm, variant in case["variants"].items():
                for row, source_id in zip(variant["rows"], context["ids"], strict=True):
                    assert (row["model"], row["id"]) == (arm, source_id)
                    assert (row["condition"], row["pattern"]) == axis
                    if source_id.startswith("synthetic-"):
                        assert row["kind"] == "synthetic"
                        continue
                    assert row["kind"] == "photo"
                    entries = samples[arm][source_id]
                    value = row["metrics"]["srgb_psnr"]
                    assert axis not in entries and math.isfinite(value)
                    entries[axis] = value
        assert len({a for a, _ in axes}) == 7 and len({b for _, b in axes}) == 4
        overall = result["summaries"]["photo"]["overall"]
        assert photo["photo_summary"] == overall
        for arm, photos in samples.items():
            assert len(photos) == photo["photo_sources"] == 427
            assert all(set(v) == axes for v in photos.values())
            assert sum(map(len, photos.values())) == photo["observations_per_model"] == 11956
            means[arm] = math.fsum(math.fsum(v.values()) / len(v) for v in photos.values()) / len(photos)
            saved = next(r for r in overall if (r["model"], r["kind"]) == (arm, "photo"))
            measure = saved["metrics"]["srgb_psnr"]
            assert measure["count"] == len(photos)
            assert math.isclose(means[arm], measure["mean"], rel_tol=0, abs_tol=1e-10)
    for point, arm in zip(points, names, strict=True):
        assert point["checkpoint_sha256"] == photo["models"][arm]["checkpoint"]["sha256"]
        for stage in ("known", "unseen"):
            panel = camera["panels"][stage]["overall"][arm]
            assert math.isclose(
                point[f"{stage}_CFA_PSNR"], panel["sensor_psnr"], rel_tol=0, abs_tol=1e-10
            )
        point["photo_srgb_PSNR"] = means[arm]
        point["evaluation_metadata"]["photo"] = {
            "photo_sources": 427,
            "observations_per_model": 11956,
            "conditions": 7,
            "CFAs": 4,
            "canonical_inputs_sha256": photo["canonical_inputs"]["sha256"],
            "precision": "CUDA IEEE FP32",
        }
    return [{
        "path": str(p.relative_to(REPO)),
        "sha256": digest(p),
        "endpoints": [r["endpoint"] for r in points],
        "report": report,
    } for p in (source, archive)]


def collect_redraw_endpoints():
    path = REPO / "docs/results/local-redraw-average-camera-v1/publication.json"
    names = {"individual": ("Draw-wise +512", 512), "mean": ("Mean draw +512", 512)}
    return collect_compact_camera_endpoints(
        path, "local-redraw-average.md", "local-redraw-average", names
    )


def collect_stability_endpoints(mean_parent):
    path = REPO / "docs/results/local-redraw-stability-camera-v1/publication.json"
    names = {
        "mean": ("Mean +320", 320),
        "repeat": ("Repeat +320", 320),
        "repeat-gap": ("Gap +320", 320),
    }
    report = "local-redraw-stability.md"
    points, evidence = collect_compact_camera_endpoints(path, report, "local-redraw-stability", names)
    photo = REPO / "docs/results/local-redraw-stability-primary-v1/publication.json"
    evidence.extend(attach_compact_photo_endpoints(
        [*points, mean_parent], photo, path, (*names, "prior-mean"), report
    ))
    return points, evidence


def collect_wire_response_endpoints():
    path = REPO / "docs/results/local-wire-response-camera-v1/publication.json"
    names = {
        "repeat": ("Repeat control", 320),
        "wire-mean": ("Full wire band", 320),
        "wire-aligned": ("Aligned wire", 320),
    }
    report = "local-wire-response.md"
    points, evidence = collect_compact_camera_endpoints(path, report, "local-wire-response", names)
    photo = REPO / "docs/results/local-wire-response-primary-v1/publication.json"
    evidence.extend(attach_compact_photo_endpoints(points, photo, path, names, report))
    return points, evidence


def collect_continuing_wire_endpoints():
    path = REPO / "docs/results/local-continuing-wire-camera-v1/publication.json"
    names = {
        "wire-aligned": ("Aligned control", 320),
        "strong-gap": ("Continuing wire", 320),
    }
    return collect_compact_camera_endpoints(
        path, "local-continuing-wire.md", "local-continuing-wire", names
    )


def collect_regional_wire_endpoints():
    path = REPO / "docs/results/local-regional-wire-camera-v1/publication.json"
    names = {
        "global-aligned": ("Whole core +1024", 1024),
        "regional-aligned": ("Regional +1024", 1024),
    }
    return collect_compact_camera_endpoints(
        path, "local-regional-wire-1024.md", "local-regional-wire", names
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--refresh-sources",
        action="store_true",
        help="Recollect archived report references (requires the original local archives).",
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="History JSON in docs/results; defaults to the current registry, with the historical seed as fallback.",
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

    destination = REPO / "docs/results/version-PSNR-history-corpus-v12.json"
    if args.data is not None:
        destination = args.data if args.data.is_absolute() else REPO / args.data
    elif not args.refresh_sources and not destination.exists():
        destination = REPO / "docs/results/version-PSNR-history-corpus-v11.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v10.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v9.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v8.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v7.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v6.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v5.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v4.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v3.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v2.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-corpus-v1.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history-v131-current-v1.json"
        if not destination.exists():
            destination = REPO / "docs/results/version-PSNR-history.json"
    if destination.resolve().parent != (REPO / "docs/results").resolve():
        parser.error("--data must name a JSON in this repository's docs/results directory")
    if destination.suffix != ".json":
        parser.error("--data must name a JSON file")
    selected = json.loads(MODEL_SELECTION.read_text())["preferred_version"]
    preferred = selected if args.preferred_version is None else args.preferred_version
    if args.refresh_sources:
        points, evidence = collect()
        corpus_points, corpus_evidence = collect_corpus_endpoints()
        points.extend(corpus_points)
        evidence.extend(corpus_evidence)
        scene_points, scene_evidence = collect_expanded_scene_endpoints()
        points.extend(scene_points)
        evidence.extend(scene_evidence)
        bridge_points, bridge_evidence = collect_near_adc_endpoints()
        points.extend(bridge_points)
        evidence.extend(bridge_evidence)
        fixed_points, fixed_evidence = collect_compact_scene_endpoints()
        points.extend(fixed_points)
        evidence.extend(fixed_evidence)
        redraw_points, redraw_evidence = collect_redraw_endpoints()
        points.extend(redraw_points)
        evidence.extend(redraw_evidence)
        mean_parent = next(p for p in redraw_points if p["endpoint"] == "local-redraw-average-mean")
        stability_points, stability_evidence = collect_stability_endpoints(mean_parent)
        points.extend(stability_points)
        evidence.extend(stability_evidence)
        wire_points, wire_evidence = collect_wire_response_endpoints()
        points.extend(wire_points)
        evidence.extend(wire_evidence)
        continuing_points, continuing_evidence = collect_continuing_wire_endpoints()
        points.extend(continuing_points)
        evidence.extend(continuing_evidence)
        regional_points, regional_evidence = collect_regional_wire_endpoints()
        points.extend(regional_points)
        evidence.extend(regional_evidence)
        result = {
            "coverage_note": COVERAGE_NOTE,
            "description": "Selected fixed primary endpoints, chosen by study scope, never by highest score. Each plotted metric has a completed primary panel; pending metrics remain blank. Version numbers are experiment labels; architectures, data, initialization, training budgets and recorded compute precision differ. This is descriptive history, not a controlled ranking or training curve. Missing versions lack a selected comparable primary report here.",
            "panels": {
                "photo_srgb_PSNR": "427 fixed photos, seven noise/exposure conditions, four CFAs; source-balanced sRGB PSNR",
                "known_CFA_PSNR": "4 scenes/8 pairs/72 crops, scene-balanced measured-CFA PSNR",
                "unseen_CFA_PSNR": "5 scenes/10 pairs/90 crops, scene-balanced measured-CFA PSNR",
            },
            "working_reference": f"V{preferred} is the working quality reference; V43 is a historical comparator",
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
    latest = max(p["version"] for p in points if p["version"] is not None)
    named = [p for p in points if p["version"] is None]
    for index, p in enumerate(named, 1):
        p["plot_position"] = latest + 8 * index
    for field in METRICS.values():
        metric_points(points, field)
    columns = [
        "version",
        *(["label"] if named else []),
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
    chart_width = 13 if len(named) > 12 else 11
    fig, axes = plt.subplots(2, 2, figsize=(chart_width, 7.6), sharex=True, layout="constrained")
    ticks = [32, 43, 63, 72, 78, 84, 92]
    if latest - ticks[-1] < 5:
        ticks[-1] = latest
    else:
        ticks.append(latest)
    tick_labels = [str(x) for x in ticks]
    ticks.extend(p["plot_position"] for p in named)
    tick_labels.extend(p["label"].removeprefix("Corpus ") for p in named)
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
            if named:
                axis.axvline(latest + 4, color="#a1aab5", linewidth=0.75, linestyle=":")
                axis.tick_params(axis="x", labelsize=9)
            axis.grid(axis="y", color="#dce2e8", linewidth=0.6)
            axis.legend(loc="best", frameon=False, fontsize=8)
            axis.set_xticks(ticks, tick_labels)
            if len(named) > 2:
                for label in axis.get_xticklabels():
                    label.set_rotation(40)
                    label.set_ha("right")
                    label.set_rotation_mode("anchor")
        highlighted = (
            [43, preferred, 72, 92, latest] if row == 0 else [34, 43, 63, preferred, 92, latest]
        )
        for version in dict.fromkeys(highlighted):
            p = next(r for r in shown if r["version"] == version)
            if "photo_srgb_PSNR" not in p:
                continue
            offset, alignment = (0, 7), "center"
            if 0 < latest - preferred <= 15:
                if version == preferred:
                    offset, alignment = (5, -20), "left"
                elif version == latest and not named:
                    offset, alignment = (12, 6), "left"
            photo.annotate(
                f"V{version}" + (" (ADC)" if p.get("inference_policy") else ""),
                (version, p["photo_srgb_PSNR"]),
                xytext=offset,
                textcoords="offset points",
                ha=alignment,
                fontsize=8,
            )
    axes[0, 0].set_title(
        f"Photo: {len(metric_points(points, 'photo_srgb_PSNR')[0])} completed endpoints",
        loc="left",
        fontsize=11,
    )
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
        axis.set_xlabel(
            "Model version or training endpoint"
            if named
            else "Model version (unequal training budgets)"
        )
    fig.suptitle("PSNR by model endpoint" if named else "PSNR by model version", fontsize=15)
    fig.supxlabel(
        f"Evaluated reference: V{preferred}. Pending metrics are omitted. (ADC) marks ADC-only sample projection.\nTraining budgets/data differ. Full values and provenance: CSV/JSON.",
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
        label = endpoint_label(p)
        endpoint = f"{label} / {p['endpoint']}" if p["version"] is not None else label
        rows.append(
            f"| {endpoint} | {photo_value} | {known_value} | {unseen_value} | [Review]({p['report']}) |"
        )
    original = next(p for p in points if p["version"] == 43)
    pending_photo = [p for p in points if "photo_srgb_PSNR" not in p]
    pending_note = ""
    if pending_photo:
        pending_note = (
            "\n\nCompleted camera panels with pending full-photo results: "
            + ", ".join(f"[{endpoint_label(p)}]({p['report']})" for p in pending_photo)
            + ". Selected material means are not substituted for full427 scores."
        )
    data_link = destination.relative_to(REPO / "docs").as_posix()
    csv_link = destination.with_suffix(".csv").relative_to(REPO / "docs").as_posix()
    (REPO / "docs/performance-history.md").write_text(
        f"# PSNR history\n\nV{preferred} is the working quality reference, with "
        f"{reference['photo_srgb_PSNR']:.5f} dB photographic PSNR and "
        f"{reference['known_CFA_PSNR']:.5f}/{reference['unseen_CFA_PSNR']:.5f} dB "
        f"known/unseen measured-CFA PSNR. Its photographic change from V43 is "
        f"+{reference['photo_srgb_PSNR'] - original['photo_srgb_PSNR']:.2f} dB. "
        "Training histories differ; current strengths, tradeoffs and native comparisons "
        "are in the [model guide](current-model.md). A version names an experiment, "
        "not a training step.\n\n"
        + result.get("coverage_note", "")
        + "\n\n![PSNR versus model version](images/version-PSNR-history.png)\n\n"
        + result["description"]
        + pending_note
        + f" Camera references are measured CFA samples; independently demosaiced RGB references are not exact GT. Small camera panels have scene uncertainty. The plot describes checkpoints with unequal budgets and data; use the linked comparisons to assess particular gains and weaknesses. Dashed lines show V{preferred}'s measured means. There are {len(metric_points(points, 'photo_srgb_PSNR')[0])} completed photo endpoints and {len(metric_points(points, 'known_CFA_PSNR')[0])}/{len(metric_points(points, 'unseen_CFA_PSNR')[0])} known/unseen camera endpoints. The lower panels omit V72/V73 RAW-native prototypes only to show the mature RGB range more clearly.\n\nAll photo points use the full fixed427-source panel, seven conditions and four CFAs. Known/unseen points balance captures within scenes, then scenes (4/5 scenes,72/90 crops). Precision, checkpoint hashes and per-source results remain in the source reports.\n\nV98/V99 use common ADC-only inference projection; only V99 trained through it. Their original V43/V95 references retain their checkpoint policies. The [completed ADC study](v95-adc-training-quality-review.md) improves ADC color but retains positive-noise color/detail weaknesses. Study-specific statistical gates do not prevent showing progress or choosing a stronger development baseline.\n\n"
        + "\n".join(rows)
        + f"\n\n[CSV]({csv_link}) · [Source records, checkpoint hashes and evaluation metadata]({data_link}) · [SVG](images/version-PSNR-history.svg) · [PDF](images/version-PSNR-history.pdf). Rebuild from the shipped JSON with `source scripts/env.sh` then `.venv/bin/python scripts/plot_version_history.py`; `--refresh-sources` additionally audits and recollects the original local report archives. `--data docs/results/NAME.json` chooses another recorded registry. These figures reuse completed reports and perform no model inference. Native noisy/restored/reference crops remain in each linked review and the README.\n"
    )
    print({"versions": len(points), "source_reports": len(evidence), "data": str(destination)})


if __name__ == "__main__":
    main()
