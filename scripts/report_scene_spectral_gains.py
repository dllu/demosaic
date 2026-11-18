"""Compare source-disjoint gain calibration with exact band-gain fits on the same proposal."""

import argparse
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
from report_fold_support_pooling import insert_camera_panels
from report_full_faint_photo_panel import LUMA, band, band_sums, original_masks
from scipy.fft import dctn

from demosaic.archive_metrics import linear_rgb, photometry
from demosaic.experiments.artifacts import checked, read_json, reference, write_json
from demosaic.reporting import display_crop

METHODS = ("parent", "learned", "long-only", "cross-fit", "RGB-oracle", "weak-band-oracle")
DN16 = 65535
FREQ = np.arange(32) / 64
RADIAL = np.hypot(FREQ[:, None], FREQ[None, :])
LOW = (1 / 32 <= RADIAL) & (RADIAL < 1 / 8)


def normal(basis, target):
    return np.einsum("...ni,...nj->...ij", basis, basis), np.einsum(
        "...ni,...n->...i", basis, target
    )


def bounded_pair(gram, product, bound=2.0):
    """Exact minimum on a closed square, including singular/all-zero bases."""
    unit = np.einsum("...ij,...j->...i", np.linalg.pinv(gram, hermitian=True), product)
    candidates = [np.clip(unit, 0, bound), np.zeros_like(unit)]
    for fixed in (0, 1):
        free = 1 - fixed
        for edge in (0.0, bound):
            item = np.zeros_like(unit)
            item[..., fixed] = edge
            diagonal = gram[..., free, free]
            usable = diagonal > 0
            rhs = product[..., free] - edge * gram[..., free, fixed]
            item[..., free] = np.clip(
                np.divide(rhs, diagonal, out=np.zeros_like(rhs), where=usable), 0, bound
            )
            candidates.append(item)
    candidates = np.stack(candidates, axis=-2)
    quad = np.einsum("...ki,...ij,...kj->...k", candidates, gram, candidates)
    quad -= 2 * np.einsum("...ki,...i->...k", candidates, product)
    best = np.argmin(quad, axis=-1)
    return np.take_along_axis(candidates, best[..., None, None], axis=-2).squeeze(-2)


def arrays(row):
    d = row["kind"] == "development"
    prefix = "crop_" if d else ""
    fields = ("wb", "matrix", "target") if d else ("wb", "matrix")
    with np.load(checked(row["inputs"]), allow_pickle=False) as f:
        context = {key: f[prefix + key] for key in fields}
    base, learned, basis = [
        np.load(checked(row[key]), allow_pickle=False) for key in ("parent", "learned", "basis")
    ]
    return context, base, learned, basis


def fit_inputs(context, base, basis):
    desired = (context["target"] - base.astype(np.float64)).reshape(len(base), -1)
    design = basis.astype(np.float64).reshape(2, len(base), -1).transpose(1, 2, 0)
    gram, product = normal(design, desired)
    normalization = max(float(np.vdot(desired, desired)), desired.size / DN16**2)
    return gram, product, normalization


def apply(base, basis, multipliers):
    return base.astype(np.float64) + np.einsum("abcdj,ba->bcdj", basis, multipliers)


def luma(value, context):
    return np.einsum("c,bchw->bhw", LUMA, linear_rgb(value, context))


def blocks32(value):
    return value[..., 16:240, 16:240].reshape(*value.shape[:-2], 7, 32, 7, 32).swapaxes(-3, -2)


def long_band(rgb):
    view = blocks32(np.einsum("c,bchw->bhw", LUMA, rgb))
    return dctn(view, axes=(-2, -1), norm="ortho")[..., LOW], view.mean((-2, -1))


def metrics(context, base, learned, basis, cross):
    rgb = linear_rgb(context["target"], context)
    true = band(np.einsum("c,bchw->bhw", LUMA, rgb))
    parent = band(luma(base, context))
    separated = np.stack([band(luma(p, context)) for p in basis], -1)
    wanted = true - parent
    masks = original_masks(context["target"], context)
    vote = masks["0"]
    per_block_g, per_block_p = normal(separated, wanted)
    weak_gram = (per_block_g * vote[..., None, None]).sum(1)
    weak_product = (per_block_p * vote[..., None]).sum(1)
    exact_weak = bounded_pair(weak_gram, weak_product)
    exact_weak[~vote.any(1)] = (1, 1)
    gram, product, _ = fit_inputs(context, base, basis)
    oracle = bounded_pair(gram, product)
    local_gains = bounded_pair(per_block_g[vote], per_block_p[vote])
    local_error = np.sum(
        (np.einsum("nki,ni->nk", separated[vote], local_gains) - wanted[vote]) ** 2
    )
    target_long, mean = long_band(rgb)
    strength = np.linalg.norm(target_long, axis=-1) / 32
    valid = ((blocks32(rgb) >= 0) & (blocks32(rgb) <= 1)).all((1, -2, -1))
    long_mask = (
        valid & (mean >= 0.02) & (mean <= 0.9) & (strength >= 1e-5) & (strength < 0.02 * mean)
    )
    rendered = {
        "parent": base,
        "learned": learned,
        "long-only": (base.astype(np.float64) + basis[0]),
        "cross-fit": apply(base, basis, np.broadcast_to(cross, (len(base), 2))),
        "RGB-oracle": apply(base, basis, oracle),
        "weak-band-oracle": apply(base, basis, exact_weak),
    }
    rows = {}
    for name, values in rendered.items():
        moments = band_sums(band(luma(values, context)), true, masks)
        actual_long, _ = long_band(linear_rgb(values, context))
        quiet = [m["quiet"] for m in moments if "quiet" in m]
        weak = [m["0"] for m in moments if "0" in m]
        error = actual_long[long_mask] - target_long[long_mask]
        rows[name] = {
            "crop_PSNR_dB": photometry(values, context)["srgb_psnr"].tolist(),
            "weak_blocks": int(vote.sum()),
            "weak_error_sq": sum(m["error"] for m in weak),
            "weak_target_sq": sum(m["target"] for m in weak),
            "weak_signed_cross": sum(m["cross"] for m in weak),
            "quiet_blocks": int(sum(m["blocks"] for m in quiet)),
            "quiet_error_sq": sum(m["error"] for m in quiet),
            "long_blocks": int(long_mask.sum()),
            "long_error_sq": float(np.sum(error**2)),
        }
    return (
        rendered,
        rows,
        {
            "RGB_oracle_gains": oracle.tolist(),
            "weak_band_oracle_gains": exact_weak.tolist(),
            "local_weak_oracle_error_sq": float(local_error),
        },
    )


def native_board(output, declaration, context, predictions):
    i = declaration["case"]["crop_index"]
    roi = declaration["case"]["ROI_xywh"]
    x, y, w, h = roi
    names = {
        "long-only": "Long band only",
        "cross-fit": "Calibrated gains",
        "weak-band-oracle": "GT-aided gains",
    }
    added = []
    for key, label in names.items():
        if key not in predictions:
            continue
        p = torch.from_numpy(predictions[key][i : i + 1].astype(np.float32))
        wb, matrix = [torch.from_numpy(context[k][i : i + 1]) for k in ("wb", "matrix")]
        image = display_crop(p, wb, matrix, roi, exposure=declaration["display_exposure"])
        added.append((label, np.rint(image.clip(0, 1) * 255).astype(np.uint8)))
    retain = (
        "Noisy (Malvar)",
        "V120 EMA",
        "Spatial spectral",
        "Exact GT",
        "ISO100 AHD, not GT",
        "ISO6400 camera JPEG",
        "ISO100 camera JPEG",
    )
    old = {**declaration, "panels": [p for p in declaration["panels"] if p["label"] in retain]}
    image, panels = insert_camera_panels(output, old["id"], old, "Spatial spectral", added)
    return {
        **declaration,
        "prior_board": old["image"],
        "image": image,
        "panels": panels,
        "changes_DN16": {
            k: float(
                np.sqrt(
                    np.mean(
                        (
                            predictions[k][i, :, y : y + h, x : x + w]
                            - predictions["parent"][i, :, y : y + h, x : x + w]
                        )
                        ** 2
                    )
                )
                * DN16
            )
            for k in names
            if k in predictions
        },
    }


def report(path, collection):
    plan = read_json(path)
    assert plan["reporter"] == reference(__file__)
    result = read_json(collection)
    assert result["plan"] == reference(path) and result["replayed_outputs_exact"] == 134
    native = read_json(checked(plan["native_pilot"]))
    assert native["collection"] == plan["completed_pilot"]
    rows = [read_json(checked(b)) for b in result["rows"]]
    totals = defaultdict(lambda: (np.zeros((2, 2)), np.zeros(2)))
    for r in rows:
        if r["kind"] == "camera":
            continue
        context, base, _, basis = arrays(r)
        gram, product, scale = fit_inputs(context, base, basis)
        a, b = totals[r["source_id"]]
        totals[r["source_id"]] = (a + gram.sum(0) / scale, b + product.sum(0) / scale)
    assert len(totals) == 64
    gram, product = (np.sum([v[i] for v in totals.values()], axis=0) for i in range(2))
    gains = bounded_pair(gram, product)
    cross = {k: bounded_pair(gram - a, product - b) for k, (a, b) in totals.items()}
    output = Path(plan["root"]) / "report"
    output.mkdir()
    scores, boards = [], []
    for index, r in enumerate(rows):
        context, base, learned, basis = arrays(r)
        if r["kind"] == "development":
            predicted, summary, oracle = metrics(
                context, base, learned, basis, cross[r["source_id"]]
            )
            scores.append({"id": r["id"], "source": r["source_id"], "by_method": summary, **oracle})
        else:
            predicted = {
                "parent": base,
                "learned": learned,
                "long-only": base.astype(np.float64) + basis[0],
                "cross-fit": apply(base, basis, gains[None]),
            }
        for b in native["boards"]:
            if b["observation"] == r["id"]:
                boards.append(native_board(output, b, context, predicted))
        if index % 16 == 0:
            print(index + 1, r["id"], flush=True)
    assert len(scores) == 128 and len(boards) == 16
    write_json(
        output / "result.json",
        {
            "driver": reference(__file__),
            "basis_stage": reference(collection),
            "source_review_plan": plan["original"],
            "gain_bounds": [0, 2],
            "camera_calibration": gains.tolist(),
            "leave_source_out_calibration": {k: v.tolist() for k, v in cross.items()},
            "per_case": scores,
            "native": boards,
            "scope": "The two oracles explicitly receive exact synthetic GT. "
            "Separate cross-fit estimates exclude both noise draws and all crops of the scored source. "
            "GFX receives only an all-development gain fit, and no fit or error uses real references.",
        },
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("collection", type=Path)
    a = p.parse_args()
    torch.set_num_threads(2)
    report(a.plan.resolve(), a.collection.resolve())
