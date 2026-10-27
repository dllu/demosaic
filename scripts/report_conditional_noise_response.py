"""Analyze retained independent-noise endpoints and render native comparisons."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from train_directional_bank_trial import guard, read, ref, save

from demosaic.archive_metrics import display, linear_rgb, noisy_malvar
from demosaic.conditional_bias import error_moments
from demosaic.prediction_archive import iter_predictions

PATTERNS = ("RGGB", "BGGR", "GRBG", "GBRG")
EDGES = (0, 0.02, 0.05, 0.1, 0.2, None)


def bias_fraction(moments):
    mse = moments["empirical_per_draw_MSE"]
    return moments["unbiased_squared_conditional_bias"] / mse if mse else None


def checked(binding):
    if ref(binding["path"]) != binding:
        raise ValueError("Retained conditional-response artifact changed")
    return Path(binding["path"])


def validate_observations(cases, observations):
    ids = [case["id"] for case in cases]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("Declare distinct conditional-response targets")
    expected = {(case, pattern, draw) for case in ids for pattern in PATTERNS for draw in range(8)}
    actual = [(row["case_id"], row["pattern"], row["draw"]) for row in observations]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        raise ValueError("Observations must cover eight distinct draws of every target/CFA")
    names = [row["id"] for row in observations]
    if len(names) != len(set(names)):
        raise ValueError("Observation IDs must be unique")
    return len(expected)


def dct_band(values):
    values = np.asarray(values, dtype=np.float64)
    if values.shape[-2:] == (256, 256):
        values = values[..., 48:208, 48:208]
    if values.ndim != 4 or values.shape[1:] != (3, 160, 160):
        raise ValueError("Expected native Bx3x160x160 or 256px contexts")
    c = np.cos(np.pi * (np.arange(16)[None, :] + 0.5) * np.arange(16)[:, None] / 16)
    c *= np.sqrt(2 / 16)
    c[0] /= np.sqrt(2)
    f = np.arange(16) / 32
    radius = np.hypot(f[:, None], f[None, :])
    band = (radius >= 1 / 8) & (radius < 1 / 3)
    luma = np.einsum("c,bchw->bhw", np.array([0.2126, 0.7152, 0.0722]), values)
    blocks = luma.reshape(len(values), 10, 16, 10, 16).transpose(0, 1, 3, 2, 4)
    blocks = blocks.reshape(len(values), 100, 16, 16)
    return (c @ blocks @ c.T)[..., band], blocks.mean(axis=(-2, -1))


def group_statistics(values, data):
    target = data["target"][0]
    pixel = error_moments(values[..., 48:208, 48:208], target[..., 48:208, 48:208])
    rendered = linear_rgb(
        values,
        {
            "wb": np.repeat(data["wb"], 8, axis=0),
            "matrix": np.repeat(data["matrix"], 8, axis=0),
        },
    )
    reference = linear_rgb(data["target"], data)
    coefficients, _ = dct_band(rendered)
    truth, means = dct_band(reference)
    truth, means = truth[0], means[0]
    rgb = reference[0, :, 48:208, 48:208]
    valid = ((rgb >= 0) & (rgb <= 1)).all(0).reshape(10, 16, 10, 16)
    valid = valid.transpose(0, 2, 1, 3).reshape(100, 256).all(1)
    rms = np.sqrt(np.sum(truth**2, axis=-1) / 256)
    valid &= (means >= 0.02) & (means <= 0.9) & (rms >= 1e-5)
    contrast = rms / np.maximum(means, 1e-12)
    local = []
    for index, high in enumerate(EDGES[1:]):
        selected = valid & (contrast >= EDGES[index])
        if high is not None:
            selected &= contrast < high
        if not selected.any():
            continue
        p, t = coefficients[:, selected], truth[selected]
        moments = error_moments(p, t)
        gains = np.sum(p * t, axis=(1, 2)) / np.sum(t**2)
        local.append(
            {
                "bin": index,
                "blocks": int(selected.sum()),
                "moments": moments,
                "reference_projected_gain_mean": float(gains.mean()),
                "reference_projected_gain_draw_std": float(gains.std(ddof=1)),
                "bias_fraction_estimate": bias_fraction(moments),
            }
        )
    return {
        "camera_RGB_moments": pixel,
        "camera_RGB_bias_fraction_estimate": bias_fraction(pixel),
        "local_band": local,
    }


def aggregate(rows, cases, labels):
    summaries = []
    for case in cases:
        for label in labels:
            groups = [r for r in rows if r["case_id"] == case["id"] and r["method"] == label]
            if len(groups) != 4 or {r["pattern"] for r in groups} != set(PATTERNS):
                raise ValueError("Conditional summaries require four separate CFA groups")
            pixel = {
                key: float(np.mean([r["camera_RGB_moments"][key] for r in groups]))
                for key in groups[0]["camera_RGB_moments"]
                if key != "draws"
            }
            bands = []
            for index in range(5):
                selected = [b for r in groups for b in r["local_band"] if b["bin"] == index]
                if not selected:
                    continue
                if len(selected) != 4 or len({s["blocks"] for s in selected}) != 1:
                    raise ValueError("Reference-selected local strata differ across CFAs")
                moments = {
                    key: float(np.mean([b["moments"][key] for b in selected]))
                    for key in selected[0]["moments"]
                    if key != "draws"
                }
                bands.append(
                    {
                        "bin": index,
                        "unique_reference_blocks": selected[0]["blocks"],
                        "mean_gain": float(
                            np.mean([b["reference_projected_gain_mean"] for b in selected])
                        ),
                        "moments": moments,
                        "bias_fraction_estimate": bias_fraction(moments),
                    }
                )
            summaries.append(
                {
                    "case_id": case["id"],
                    "method": label,
                    "reference_role": case["reference_role"],
                    "camera_RGB_moments": pixel,
                    "camera_RGB_bias_fraction_estimate": bias_fraction(pixel),
                    "local_band": bands,
                }
            )
    return summaries


def analyze(plan_path, collection_path):
    plan = read(plan_path)
    guard(plan)
    root = Path(plan["root"])
    (root / "analysis.claim").open("x").close()
    collection = read(collection_path)
    if collection["plan"] != ref(plan_path):
        raise ValueError("Conditional collection refers to a different execution plan")
    labels = [m["label"] for m in plan["retained_methods"] + plan["methods"]]
    declared = {
        m["label"]: m["checkpoint"]["sha256"] for m in plan["retained_methods"] + plan["methods"]
    }
    if len(labels) != len(set(labels)):
        raise ValueError("Retained controls and new endpoints must have distinct labels")
    expected_count = validate_observations(plan["cases"], plan["observations"])
    observations = {(o["case_id"], o["pattern"], o["draw"]): o for o in plan["observations"]}
    cases = {case["id"]: case for case in plan["cases"]}
    groups, targets, records = defaultdict(dict), {}, {}
    archives = [plan["retained_archive"]]
    if collection.get("archive"):
        archives.append(collection["archive"])
    for archive in archives:
        for record, prediction, data in iter_predictions(checked(archive)):
            context = record["context"]
            method = record["model"]["label"]
            if method not in labels:
                raise ValueError("Unexpected method in retained conditional archive")
            if record["model"]["sha256"] != declared[method] or record["model"]["step"] != 20000:
                raise ValueError("Conditional prediction checkpoint or completed step differs")
            key = method, context["case_id"], context["pattern"]
            observed = observations[(*key[1:], context["draw"])]
            for field in ("id", "seed", "input_fingerprints"):
                if context[field] != observed[field]:
                    raise ValueError("Conditional observation identity/fingerprint differs")
            if context["noise"] != plan["noise"]:
                raise ValueError("Conditional noise profile differs")
            draw = context["draw"]
            if draw in groups[key] or record["model"]["self_ensemble"] != "none":
                raise ValueError("Duplicate or non-single-view conditional prediction")
            groups[key][draw] = prediction[0]
            if key in targets and any(
                not np.array_equal(v, targets[key][k]) for k, v in data.items()
            ):
                raise ValueError("Target or display metadata differs between noise draws")
            targets[key] = data
            records[(*key, draw)] = record
    if len(groups) != len(labels) * len(cases) * 4:
        raise ValueError("Conditional archive model/target/CFA coverage differs")
    rows = []
    for (method, case, pattern), group in groups.items():
        if set(group) != set(range(8)):
            raise ValueError("Every CFA needs exactly eight independent draws")
        values = np.stack([group[k] for k in range(8)]).astype(np.float64)
        with np.load(checked(cases[case]["target"]), allow_pickle=False) as original:
            if any(
                not np.array_equal(v, original[k])
                for k, v in targets[(method, case, pattern)].items()
            ):
                raise ValueError("Conditional reference differs from the original fixed target")
        rows.append(
            {
                "method": method,
                "case_id": case,
                "pattern": pattern,
                "reference_role": cases[case]["reference_role"],
                **group_statistics(values, targets[(method, case, pattern)]),
            }
        )
    summaries = aggregate(rows, plan["cases"], labels)
    output = Path(plan["work"]) / "artifacts/analysis"
    output.mkdir(parents=True, exist_ok=False)
    images = []
    for case in plan["cases"]:
        identity = case["id"]
        with np.load(checked(case["target"]), allow_pickle=False) as archive:
            data = {k: archive[k] for k in archive.files}
        observed = observations[(identity, "RGGB", 0)]
        with np.load(checked(observed["arrays"]), allow_pickle=False) as archive:
            noisy = {k: archive[k] for k in archive.files}

        def pixels(value, metadata=data):
            return np.rint(
                display(value, metadata)[0, :, 48:208, 48:208].transpose(1, 2, 0) * 255
            ).astype(np.uint8)

        noisy_pixels, truth_pixels = pixels(noisy_malvar(noisy)), pixels(data["target"])
        for kind in ("single", "mean8-diagnostic"):
            panels, names = [noisy_pixels], ["Noisy draw0"]
            for label in labels:
                group = groups[(label, identity, "RGGB")]
                value = (
                    group[0][None]
                    if kind == "single"
                    else np.mean(np.stack([group[k].astype(np.float64) for k in range(8)]), axis=0)[
                        None
                    ]
                )
                panel = pixels(value)
                panels.append(panel)
                names.append(label + (" draw0" if kind == "single" else " mean8*"))
                if (
                    kind == "single"
                    and identity in plan["exact_synthetic_cases"]
                    and label in plan.get("triplet_arms", plan["new_arms"])
                ):
                    triplet = Image.new("RGB", (512, 192), "#eeeeee")
                    drawing = ImageDraw.Draw(triplet)
                    for i, (name, cell) in enumerate(
                        zip(
                            ["Noisy draw0", label + " draw0", "Exact synthetic GT"],
                            [noisy_pixels, panel, truth_pixels],
                            strict=True,
                        )
                    ):
                        drawing.text((8 + 168 * i, 5), name, fill="black")
                        triplet.paste(Image.fromarray(cell), (8 + 168 * i, 24))
                    target = output / f"{label}-{identity}-single-triplet.png"
                    triplet.save(target)
                    images.append(
                        {
                            "image": ref(target),
                            "kind": "single-triplet",
                            "case_id": identity,
                            "method": label,
                            "checkpoint": next(
                                m["checkpoint"]
                                for m in plan["retained_methods"] + plan["methods"]
                                if m["label"] == label
                            ),
                            "ROI_xywh": [48, 48, 160, 160],
                            "display_exposure": 1,
                            "noise": plan["noise"],
                            "reference_role": case["reference_role"],
                            "source": case,
                            "observation": observed,
                            "display_metadata": {k: data[k].tolist() for k in ("wb", "matrix")},
                            "pixel_scale": "native160; no resizing",
                        }
                    )
            panels.append(truth_pixels)
            names.append(
                "Exact synthetic GT"
                if identity in plan["exact_synthetic_cases"]
                else "Low-noise ref (not GT)"
            )
            board = Image.new("RGB", (8 + 168 * len(panels), 208), "#eeeeee")
            drawing = ImageDraw.Draw(board)
            for i, (name, cell) in enumerate(zip(names, panels, strict=True)):
                drawing.text((8 + 168 * i, 5), name, fill="black")
                board.paste(Image.fromarray(cell), (8 + 168 * i, 24))
            drawing.text(
                (8, 190),
                "Single draw0"
                if kind == "single"
                else "mean8*: eight independent observations; unavailable from one capture",
                fill="black",
            )
            target = output / f"{identity}-{kind}.png"
            board.save(target)
            images.append(
                {
                    "image": ref(target),
                    "kind": kind,
                    "case_id": identity,
                    "labels": names,
                    "ROI_xywh": [48, 48, 160, 160],
                    "display_exposure": 1,
                    "reference_role": case["reference_role"],
                    "noise": plan["noise"],
                    "source": case,
                    "scope": "Native160 cells; no resizing. mean8 is a multiple-observation diagnostic, not an inference improvement.",
                }
            )
    if "torch" in sys.modules:
        raise RuntimeError("Conditional analysis must remain NumPy-only")
    result = {
        "plan": ref(plan_path),
        "collection": ref(collection_path),
        "per_group": rows,
        "summaries": summaries,
        "images": images,
        "methods": plan["retained_methods"] + plan["methods"],
        "observations_per_model": expected_count,
        "retained_control_predictions_reused": expected_count * len(plan["retained_methods"]),
        "new_neural_forwards": 0,
        "new_encoder_forwards": 0,
        "new_noise_observations": 0,
        "RAW_decodes": 0,
        "optimizer_updates": 0,
        "Torch_imported": False,
        "native_review_status": "Native boards/triplets prepared; actual viewing remains pending",
        "scope": "Fixed four-target/eight-noise-draw diagnostic. CFAs analyzed separately. Signed finite-sample bias estimates retained; no population/seed interval, exact native GT or automatic recommendation change.",
    }
    save(root / "analysis-v1.json", result)
    print(json.dumps({"groups": len(rows), "summaries": len(summaries), "images": len(images)}))
    return root / "analysis-v1.json"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("collection", type=Path)
    args = parser.parse_args()
    analyze(args.plan, args.collection)
