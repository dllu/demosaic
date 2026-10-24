"""Native comparisons from audited PNGs and retained full-frame GFX floats."""

import hashlib
import shutil
from pathlib import Path

import numpy as np
from audit_quality_archive import binding, write
from compare_quality_archives import canonical, read_bound
from PIL import Image, ImageDraw

from demosaic.archive_metrics import display, noisy_malvar


def pixel_hash(pixels):
    return hashlib.sha256(np.ascontiguousarray(pixels).tobytes()).hexdigest()


def board(path, columns, labels, captions, provenance):
    """Copy native 160px cells; reopen every encoded cell before receipting."""
    path = Path(path)
    canvas = Image.new("RGB", (8+168*len(columns), 8+188*len(labels)), "#eeeeee")
    draw, cells = ImageDraw.Draw(canvas), []
    for col, (values, caption) in enumerate(zip(columns, captions, strict=True)):
        for row, (pixels, label) in enumerate(zip(values, labels, strict=True)):
            if pixels.dtype != np.uint8 or pixels.shape != (160, 160, 3):
                raise ValueError("Comparison cells must be native160 RGB8 pixels")
            x, y = 8+168*col, 24+188*row
            draw.text((x, y-20), f"{caption}: {label}", fill="black")
            canvas.paste(Image.fromarray(pixels), (x, y))
            cells.append({"column": col, "label": label, "png_xywh": [x, y, 160, 160],
                          "pixel_sha256": pixel_hash(pixels)})
    with path.open("xb") as stream:
        canvas.save(stream, format="PNG")
    with Image.open(path) as image:
        decoded = np.array(image)
    for cell in cells:
        x, y, w, h = cell["png_xywh"]
        if pixel_hash(decoded[y:y+h, x:x+w]) != cell["pixel_sha256"]:
            raise ValueError("Native comparison PNG changed a crop pixel")
    receipt = {"image": binding(path), "panels": cells, "sources": provenance,
               "pixel_scale": "One native image pixel per PNG pixel; no resizing",
               "review_status": "Prepared; human viewing pending"}
    write(path.with_suffix(".json"), receipt)
    return receipt


def triplet_pixels(receipt):
    read_bound_image = receipt["image"]
    if binding(read_bound_image["path"]) != read_bound_image:
        raise ValueError("Changed audited triplet image")
    with Image.open(read_bound_image["path"]) as image:
        pixels = np.array(image.convert("RGB"))
    result = []
    for panel in receipt["panels"]:
        x, y, w, h = panel["png_xywh"]
        crop = pixels[y:y+h, x:x+w]
        if crop.shape != (160, 160, 3) or pixel_hash(crop) != panel["pixel_sha256"]:
            raise ValueError("Changed native triplet panel")
        result.append(crop)
    if len(result) != 3:
        raise ValueError("Require noisy/restored/exact-GT triplets")
    return result


def photo_comparison(stage, output, *, labels=("V114 control", "V116 candidate")):
    """Preserve both complete candidate triplets plus a matched four-method board."""
    output = Path(output)
    indexed = []
    for role in ("control", "candidate"):
        selected = [r for r in stage[f"{role}_native_triplets"]
                    if {k: r["model"][k] for k in ("sha256", "self_ensemble")} == stage[role]["model"]]
        group = {r["source_id"]: r for r in selected}
        if len(group) != 2 or len(group) != len(selected):
            raise ValueError("Require the two declared material triplets per endpoint")
        indexed.append(group)
    if indexed[0].keys() != indexed[1].keys():
        raise ValueError("Material sources differ")
    columns, provenance, copies = [], [], []
    shared = ("source", "context", "ROI_xywh_in_retained_context", "native_context_shape",
              "white_balance", "camera_to_srgb", "display_exposure", "display_transform", "reference")
    for i, source in enumerate(sorted(indexed[0])):
        old, new = (group[source] for group in indexed)
        if any(old[key] != new[key] for key in shared):
            raise ValueError("Triplet ROI, source, observation or display differs")
        a, b = triplet_pixels(old), triplet_pixels(new)
        if not np.array_equal(a[0], b[0]) or not np.array_equal(a[2], b[2]):
            raise ValueError("Material noisy/GT crop pixels differ")
        columns.append([a[0], a[1], b[1], a[2]])
        provenance.append({"control": old, "candidate": new})
        path = output/f"candidate-material-{i+1}.png"
        with path.open("xb") as stream, Path(new["image"]["path"]).open("rb") as original:
            shutil.copyfileobj(original, stream)
        copied = {**new, "image": binding(path), "original_image": new["image"]}
        write(path.with_suffix(".json"), copied)
        copies.append(copied)
    result = board(output/"matched-materials.png", columns,
                   ["Noisy", *labels, "Exact GT"], ["A", "B"], provenance)
    return {"comparison": result, "candidate_triplets": copies}


def bound_array(item):
    if binding(item["path"]) != item:
        raise ValueError("Changed retained float array")
    value = np.load(item["path"], allow_pickle=False)
    if value.dtype != np.float32 or not np.isfinite(value).all():
        raise ValueError("GFX requires finite original FP32 values")
    return value


def gfx_comparison(control_result, candidate_result, control_sha, candidate_sha, output, *,
                   labels=("V114 control", "V116 candidate")):
    """Render all methods with one NumPy64 transform; ISO100 remains approximate."""
    stages = [read_bound(binding(path)) for path in (control_result, candidate_result)]
    reports = [read_bound(stage["report"]) for stage in stages]
    for field in ("selection", "sources", "conditioning", "reference_calibration"):
        if reports[0][field] != reports[1][field]:
            raise ValueError(f"GFX shared {field} differs")
    methods = []
    for stage, report, sha in zip(stages, reports, (control_sha, candidate_sha), strict=True):
        native = [r for r in stage["full_native_floats"] if r["checkpoint"]["sha256"] == sha]
        crops = [r for r in report["native_crops"] if r["checkpoint_sha256"] == sha and r["full_frame"]]
        floats = {(r["region"]["name"], r["role"]): r for r in report["float_contexts"]}
        group, pixels = {}, {}
        for item in native:
            name = item["region"]["name"]
            crop = [r for r in crops if r["region"] == item["region"]]
            if name in group or len(crop) != 1:
                raise ValueError("Missing or duplicate full-frame native region")
            crop = crop[0]
            shared = {k: crop[k] for k in ("region", "conditioning", "display_exposure", "shared_wb", "shared_matrix", "reference")}
            arrays, bindings, metadata = {}, {}, {}
            for role in ("noisy-packed", "reference-rgb"):
                receipt = floats[(name, role)]
                path = Path(stage["report"]["path"]).parent/receipt["image"]
                bindings[role] = {"path": str(path), "sha256": receipt["sha256"]}
                metadata[role] = {k: v for k, v in receipt.items() if k not in {"image", "sha256"}}
                arrays[role] = bound_array(bindings[role])
                if list(arrays[role].shape) != receipt["shape"] or receipt["region"] != shared["region"]:
                    raise ValueError("GFX float shape/ROI differs from receipt")
            prediction = bound_array(item["array"])
            if prediction.shape != (1, 3, 160, 160) or arrays["reference-rgb"].shape != prediction.shape:
                raise ValueError("Require native160 full-frame/reference floats")
            data = {"wb": np.array([shared["shared_wb"]], np.float64),
                    "matrix": np.array([shared["shared_matrix"]], np.float64),
                    "packed": arrays["noisy-packed"],
                    "colors": np.array([["RGB".index(c) for c in metadata["noisy-packed"]["pattern"]]])}
            nx, ny = shared["region"]["noisy_xy"]
            tx, ty, w, h = metadata["noisy-packed"]["context_xywh"]
            x, y = nx-tx, ny-ty
            if (w, h) != (512, 512) or min(x, y) < 0 or max(x+160, y+160) > 512:
                raise ValueError("GFX noisy ROI outside its retained context")
            noisy = noisy_malvar(data)[..., y:y+160, x:x+160]
            values = [noisy, prediction, arrays["reference-rgb"]]
            pixels[name] = [np.rint(display(value.astype(np.float64), data, shared["display_exposure"])[0]
                                    .transpose(1, 2, 0)*255).astype(np.uint8) for value in values]
            group[name] = {"shared": shared, "float_metadata": metadata, "shared_float_bindings": bindings,
                           "shared_value_sha256": {key: pixel_hash(value) for key, value in arrays.items()},
                           "prediction": item, "report": stage["report"]}
        if len(group) != 6:
            raise ValueError("Require all six standing GFX regions")
        methods.append((group, pixels))
    (a, ap), (b, bp) = methods
    if a.keys() != b.keys():
        raise ValueError("GFX region coverage differs")
    names, columns, provenance = sorted(a), [], []
    for name in names:
        for key in ("shared", "float_metadata", "shared_value_sha256"):
            if canonical(a[name][key]) != canonical(b[name][key]):
                raise ValueError("GFX input/reference/transform values differ")
        if any(not np.array_equal(ap[name][i], bp[name][i]) for i in (0, 2)):
            raise ValueError("GFX common-render noisy/reference pixels differ")
        columns.append([ap[name][0], ap[name][1], bp[name][1], ap[name][2]])
        provenance.append({"control": a[name], "candidate": b[name]})
    boards = [board(Path(output)/f"matched-gfx-{i//3+1}.png", columns[i:i+3],
                    ["Noisy", *labels, "ISO100 ref (not GT)"],
                    [str(j+1) for j in range(i, i+3)], provenance[i:i+3]) for i in (0, 3)]
    return {"boards": boards, "regions_in_column_order": names,
            "display": "Shared NumPy64 WB/matrix and exposure, clipped sRGB, round-to-nearest RGB8",
            "reference": "Independently demosaiced ISO100 f/5.6; aperture/moving-subject differences; not pixelwise GT",
            "new_neural_forwards": 0, "RAW_decodes": 0, "quality_scores": None}
