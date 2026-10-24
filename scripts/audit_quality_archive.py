"""Independently rescore retained predictions and prepare native photo triplets."""

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from demosaic.archive_metrics import color, display, noisy_malvar, photometry, texture
from demosaic.prediction_archive import iter_predictions
from demosaic.safety import writable_path


def binding(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def write(path, value):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False)+"\n")


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def _key(stage, row, label):
    if stage == "color":
        return label, row["case"]
    return label, row["id" if stage in {"photo", "texture"} else "tile_id"], row.get("condition"), row["pattern"]


def _check(actual, expected, errors, stage):
    for name, value in actual.items():
        reference = expected[name]
        if not np.isfinite(np.asarray(value)).all():
            if not np.isnan(value).all() or reference is not None:
                raise ValueError(f"Unexpected missing metric: {name}")
            continue
        delta = float(np.max(np.abs(np.asarray(value)-np.asarray(reference))))
        tolerance = (2e-10 if stage == "color" else 3e-9 if stage == "texture"
                     else 5e-4 if "psnr" in name else 2e-6)
        if not np.isfinite(delta) or delta > tolerance:
            raise ValueError(f"Metric disagreement: {stage}/{name}: {delta} > {tolerance}")
        errors[name] = max(errors[name], delta)


def _triplet(output, record, prediction, targets, index, source):
    context = record["context"]
    identity = context["ids"][index]
    one = {k: v[index:index+1] for k, v in targets.items()}
    values = [noisy_malvar(one), prediction[index:index+1], one["target"]]
    labels = ["Noisy (Malvar)", record["model"]["label"], "GT (synthetic)"]
    canvas = Image.new("RGB", (512, 192), "#eeeeee")
    draw = ImageDraw.Draw(canvas)
    cells = []
    for i, (label, value) in enumerate(zip(labels, values, strict=True)):
        pixels = np.rint(display(value[..., 48:208, 48:208], one)[0].transpose(1, 2, 0)*255).astype(np.uint8)
        if pixels.shape != (160, 160, 3):
            raise ValueError("Triplets require native 256 contexts and 160 crops")
        x = 8+i*168
        draw.text((x, 5), label, fill="black")
        canvas.paste(Image.fromarray(pixels), (x, 24))
        cells.append({"label": label, "png_xywh": [x, 24, 160, 160],
                      "pixel_sha256": hashlib.sha256(pixels.tobytes()).hexdigest()})
    key = record["model"]["sha256"]+record["model"]["self_ensemble"]+identity
    path = output/("crop-"+hashlib.sha256(key.encode()).hexdigest()[:16]+".png")
    with path.open("xb") as stream:
        canvas.save(stream, format="PNG")
    receipt = {"image": binding(path), "source_id": identity, "source": source,
               "record_index": record["index"], "context": context, "model": record["model"],
               "prediction": record["prediction"], "supervision": record["supervision"],
               "ROI_xywh_in_retained_context": [48, 48, 160, 160], "native_context_shape": list(prediction.shape[-2:]),
               "white_balance": one["wb"].tolist(), "camera_to_srgb": one["matrix"].tolist(),
               "display_exposure": 1, "display_transform": "NumPy64 shared WB/matrix, clipped sRGB, round-to-nearest uint8",
               "reference": "Exact synthetic target saved by the evaluator", "panels": cells,
               "pixel_scale": "One native image pixel per PNG pixel; no resizing",
               "review_status": "prepared; human native viewing pending"}
    write(path.with_suffix(".json"), receipt)
    # Reopen and verify actual encoded cells, not merely the in-memory canvas.
    with Image.open(path) as image:
        actual = np.array(image)
    for cell in cells:
        x, y, w, h = cell["png_xywh"]
        if hashlib.sha256(actual[y:y+h, x:x+w].tobytes()).hexdigest() != cell["pixel_sha256"]:
            raise ValueError("Native PNG pixels changed during encoding")
    return receipt


def audit(manifest, report, output, *, stage, material_ids=(), source_manifest=None):
    """Check complete archive/report joins, never construct a model or observation."""
    if stage not in {"photo", "known", "unseen", "texture", "color"}:
        raise ValueError("Unknown numerical stage")
    output = writable_path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    original = json.loads(Path(report).read_text())
    models = original["checkpoints" if stage == "color" else "models"]
    labels = {}
    for index, model in enumerate(models):
        if "sha256" in model:
            key = model["sha256"], model.get("self_ensemble", "none")
            if key in labels:
                raise ValueError("Ambiguous report model identity")
            labels[key] = index if stage == "color" else model["label"]
    row_file = {"photo": "per-image.jsonl", "known": "per-crop.jsonl", "unseen": "per-crop.jsonl", "texture": "per-case.jsonl"}
    rows = original["results"] if stage == "color" else read_rows(Path(report).parent/row_file[stage])
    lookup = {_key(stage, r, r["model_index" if stage == "color" else "model"]): r for r in rows}
    if len(lookup) != len(rows):
        raise ValueError("Duplicate report observation")
    sources = {r["id"]: r for r in read_rows(source_manifest)} if source_manifest else {}
    errors, observations, aligned, seen, rebuilt, crops, cropped = defaultdict(float), defaultdict(int), {}, set(), [], [], set()
    for record, prediction, targets in iter_predictions(manifest):
        model = record["model"]
        identity = model["sha256"], model["self_ensemble"]
        label = labels[identity]
        context = record["context"]
        context_key = json.dumps(context, sort_keys=True)
        group = aligned.setdefault(identity, {})
        if context_key in group:
            raise ValueError("Duplicate archive observation")
        group[context_key] = record["supervision_values"]
        if stage == "color":
            measures = color(prediction, targets)
        elif stage == "texture":
            measures = texture(prediction, targets, period=context["period"] if context["kind"] == "carrier" else None)
        else:
            border = original.get("border", 32) if stage in {"known", "unseen"} else original["protocol"].get("border", 8)
            measures = photometry(prediction, targets, border=border, camera=stage in {"known", "unseen"})
        for i, source_id in enumerate(context["ids"]):
            observed = ({"case": context["case_index"]} if stage == "color" else
                        {"id" if stage in {"photo", "texture"} else "tile_id": source_id,
                         "condition": context.get("condition", {}).get("name"), "pattern": context["pattern"]})
            key = _key(stage, observed, label)
            if key in seen:
                raise ValueError("Duplicate scored observation")
            seen.add(key)
            row = lookup[key]
            if stage in {"known", "unseen"} and row["scene"] != context["scene"]:
                raise ValueError("Camera scene differs from report")
            if stage == "color" and any(row[k] != context["definition"][k] for k in ("pattern", "source", "palette")):
                raise ValueError("Color definition differs from report")
            if stage == "color" and row["condition"] != context["definition"]["condition"]["name"]:
                raise ValueError("Color condition differs from report")
            if stage == "texture" and any(row[k] != context[k] for k in ("kind", "level", "contrast", "period")):
                raise ValueError("Texture definition differs from report")
            actual = measures if stage == "color" else {k: None if np.isnan(v[i]) else float(v[i]) for k, v in measures.items()}
            # Missing camera scores are permitted only with fewer than 1024 CFA samples.
            comparable = {k: np.nan if v is None else v for k, v in actual.items()}
            _check(comparable, row["metrics"], errors, stage)
            rebuilt.append({**{k: v for k, v in row.items() if k != "metrics"}, "checkpoint_sha256": model["sha256"], "metrics": actual})
            observations[model["label"]] += 1
            crop_key = identity, source_id
            if (stage == "photo" and source_id in material_ids and context["condition"]["name"] == "iso12800-prior"
                    and context["pattern"] == "RGGB" and crop_key not in cropped):
                crops.append(_triplet(output, record, prediction, targets, i, sources.get(source_id, {})))
                cropped.add(crop_key)
    if not aligned or any(group != next(iter(aligned.values())) for group in aligned.values()):
        raise ValueError("Models have different contexts or supervision")
    archived_labels = {labels[identity] for identity in aligned}
    expected = {_key(stage, r, r["model_index" if stage == "color" else "model"]) for r in rows
                if r["model_index" if stage == "color" else "model"] in archived_labels}
    if seen != expected:
        raise ValueError("Archive/report coverage differs")
    if stage == "photo" and material_ids and len(crops) != len(aligned)*len(material_ids):
        raise ValueError("Required native material triplets missing")
    write(output/"rows.json", rebuilt)
    result = {"stage": stage, "manifest": binding(manifest), "report": binding(report),
              "original_rows": binding(Path(report).parent/row_file[stage]) if stage != "color" else binding(report),
              "independent_rows": binding(output/"rows.json"), "observations": dict(observations),
              "models": len(aligned), "maximum_metric_discrepancies": dict(errors), "native_triplets": crops,
              "Torch_imported": "torch" in sys.modules, "new_neural_forwards": 0, "RAW_decodes": 0,
              "scope": "NumPy64 primary/analytic reductions from actual archived targets. SSIM and masked boundary/shadow metrics retain original evaluation implementation. Native PNG bytes verified; actual human viewing remains separate."}
    write(output/"result.json", result)
    return result


def paired_changes(current, control, *, stage, metric, bootstrap_draws=10000):
    """Pair complete observations, then average captures within camera scenes.

    Callers pass one method per list. Fixed source/scene units, not independent
    crops or repeated training seeds, are the bootstrap units.
    """
    photo = stage == "photo"
    fields = ("id", "condition", "pattern") if photo else ("scene", "pair", "tile_id", "pattern")
    def indexed(rows):
        selected = [r for r in rows if not photo or r["kind"] == "photo"]
        result = {tuple(r[k] for k in fields): r for r in selected}
        if len(result) != len(selected) or not result:
            raise ValueError("Empty or duplicate paired observations")
        return result
    a, b = indexed(current), indexed(control)
    if a.keys() != b.keys():
        raise ValueError("Current/control observation coverage differs")
    groups = defaultdict(lambda: defaultdict(list))
    for key, row in a.items():
        values = row["metrics"][metric], b[key]["metrics"][metric]
        if any(v is None or not np.isfinite(v) for v in values):
            raise ValueError("Paired source/scene summaries require finite scores")
        unit = row["id" if photo else "scene"]
        groups[unit]["all" if photo else row["pair"]].append(values)
    units = sorted(groups)
    means = np.array([np.mean([np.mean(values, axis=0) for values in groups[u].values()], axis=0) for u in units])
    delta = means[:, 0]-means[:, 1]
    rng = np.random.default_rng(42)
    sampled = delta[rng.integers(len(delta), size=(bootstrap_draws, len(delta)))].mean(1)
    return {"metric": metric, "units": len(units), "observations": len(a),
            "current_mean": float(means[:, 0].mean()), "control_mean": float(means[:, 1].mean()),
            "change": float(delta.mean()), "units_increased": int((delta > 0).sum()),
            "bootstrap_95_interval": np.quantile(sampled, [.025, .975]).tolist(),
            "unit_changes": [{"unit": u, "change": float(d)} for u, d in zip(units, delta, strict=True)],
            "aggregation": "Mean crops within capture, captures within scene, scenes equally" if not photo else "Mean conditions/CFAs within source, sources equally",
            "interpretation": "Paired fixed evaluation units; no training-seed or general-camera uncertainty"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--stage", choices=["photo", "known", "unseen", "texture", "color"], required=True)
    parser.add_argument("--material-ids", nargs="*", default=[])
    parser.add_argument("--source-manifest", type=Path)
    options = parser.parse_args()
    result = audit(options.manifest, options.report, options.output, stage=options.stage,
                   material_ids=options.material_ids, source_manifest=options.source_manifest)
    print({"stage": result["stage"], "observations": result["observations"], "crops": len(result["native_triplets"])}, flush=True)
