"""Output-space band-loss diagnosis on saved training predictions, no model calls."""

import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path

import numpy as np
import psutil
import torch
from torch.nn import functional as F

from demosaic.cfa import mosaic
from demosaic.losses import reconstruction_loss


def band(value, small=3, large=9):
    def mean(size):
        pad = size//2
        return F.avg_pool2d(F.pad(value, (pad, pad, pad, pad), mode="reflect"), size, 1)
    return mean(small)-mean(large)


def support(target):
    valid = ((target >= 0) & (target < .98)).all(1, keepdim=True).to(target.dtype)
    valid = 1-F.max_pool2d(1-valid, 9, 1, 4)
    return valid[..., 8:-8, 8:-8]


def band_penalty(prediction, target, *, normalized):
    """Experimental synthetic-target-only term; not wired into training.

    The target-derived per-image scale is fixed during backpropagation. All
    channels/neighbors must be valid; the outer eight pixels are excluded.
    """
    mask = support(target)
    count = mask.sum((1, 2, 3))*3
    error = band(prediction-target)[..., 8:-8, 8:-8]
    if normalized:
        clean = band(target)[..., 8:-8, 8:-8]
        scale = ((clean.square()*mask).sum((1, 2, 3))/count.clamp_min(1)).sqrt().clamp_min(.001).detach()
        error = error/scale[:, None, None, None]
        epsilon, weight = .1, .0003
    else:
        epsilon, weight = .0003, .1
    values = (((error.square()+epsilon**2).sqrt()-epsilon)*mask).sum((1, 2, 3))/count.clamp_min(1)
    return weight*values.masked_fill(count == 0, 0).sum()/(count > 0).sum().clamp_min(1)


def numpy_band(value, small=3, large=9):
    """Independent summed-area-table means, rather than Torch pooling."""
    def mean(size):
        pad = size//2
        a = np.pad(value, ((0, 0), (0, 0), (pad, pad), (pad, pad)), mode="reflect")
        integral = np.pad(a, ((0, 0), (0, 0), (1, 0), (1, 0))).cumsum(-2).cumsum(-1)
        return (integral[..., size:, size:]-integral[..., :-size, size:]
                -integral[..., size:, :-size]+integral[..., :-size, :-size])/size**2
    return mean(small)-mean(large)


def numpy_penalty(prediction, target, *, normalized):
    target, prediction = target.astype(np.float64), prediction.astype(np.float64)
    valid = ((target >= 0) & (target < .98)).all(1, keepdims=True)
    windows = np.lib.stride_tricks.sliding_window_view(valid, (9, 9), axis=(-2, -1))
    mask = windows.all((-2, -1))[..., 4:-4, 4:-4]
    count = mask.sum((1, 2, 3))*3
    error = numpy_band(prediction-target)[..., 8:-8, 8:-8]
    if normalized:
        clean = numpy_band(target)[..., 8:-8, 8:-8]
        scale = np.maximum(np.sqrt(np.sum(clean**2*mask, axis=(1, 2, 3))/np.maximum(count, 1)), .001)
        error = error/scale[:, None, None, None]
        epsilon, weight = .1, .0003
    else:
        epsilon, weight = .0003, .1
    values = np.sum((np.sqrt(error**2+epsilon**2)-epsilon)*mask, axis=(1, 2, 3))/np.maximum(count, 1)
    return float(weight*np.where(count > 0, values, 0).sum()/max(int((count > 0).sum()), 1))


def binding(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        return {"path": str(path), "sha256": hashlib.file_digest(stream, "sha256").hexdigest()}


def save(path, value):
    with Path(path).open("x") as stream:
        stream.write(json.dumps(value, indent=2, allow_nan=False)+"\n")


def guard(plan):
    for item in plan["inputs"]:
        assert binding(item["path"]) == item, item["path"]
    for path, digest in plan["frozen_files"].items():
        assert binding(path)["sha256"] == digest, path


def distribution(values):
    if not values:
        return None
    a = np.array(values)
    return {"cases": len(a), "median": float(np.median(a)), "q25": float(np.quantile(a, .25)),
            "q75": float(np.quantile(a, .75)), "min": float(a.min()), "max": float(a.max())}


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["contrast"], row["condition"]].append(row)
    result = []
    for (contrast, condition), cases in sorted(groups.items()):
        methods = []
        for name in ("raw-band", "normalized-band"):
            eligible = [r for r in cases if r["missing_coefficient"] > 0 and r["methods"]["baseline"]["directional"] < -1e-12]
            methods.append({"name": name, "eligible_cases": len(eligible),
                            "gradient_norm_ratio": distribution([r["methods"][name]["norm"]/r["methods"]["baseline"]["norm"] for r in cases]),
                            "corrective_slope_ratio": distribution([r["methods"][name]["directional"]/r["methods"]["baseline"]["directional"] for r in eligible]),
                            "correction_per_gradient_ratio": distribution([(r["methods"][name]["directional"]/r["methods"]["baseline"]["directional"])/(r["methods"][name]["norm"]/r["methods"]["baseline"]["norm"]) for r in eligible]),
                            "cosine_change": distribution([r["methods"][name]["cosine"]-r["methods"]["baseline"]["cosine"] for r in cases]),
                            "correction_lowers_loss_count": sum(r["methods"][name]["directional"] < 0 for r in cases)})
        result.append({"contrast": contrast, "condition": condition, "cases": len(cases),
                       "target_band_rms": distribution([r["target_band_rms"] for r in cases]), "methods": methods})
    return result


def run(path):
    plan = json.loads(Path(path).read_text())
    guard(plan)
    assert os.environ["CUDA_VISIBLE_DEVICES"] == "" and not torch.cuda.is_initialized()
    assert binding(__file__) == plan["worker"]
    root = Path(plan["output"])
    root.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(2)
    rng = torch.get_rng_state().clone()
    def forbid(*_a, **_kw):
        raise RuntimeError("Learned/module forwards forbidden in saved-output gradient study")
    torch.nn.Module._call_impl = forbid
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    rows, errors = [], defaultdict(float)
    for index, case in enumerate(plan["cases"]):
        assert psutil.virtual_memory().available > 24*2**30
        with np.load(case["arrays"]["path"], allow_pickle=False) as archive:
            arrays = {k: archive[k].copy() for k in archive.files}
        prediction = torch.from_numpy(arrays.pop("prediction")).requires_grad_(True)
        direction = torch.from_numpy(arrays.pop("band_direction"))
        batch = {k: torch.from_numpy(v) for k, v in arrays.items()}
        batch["sensor_target"] = batch["target"]
        loss, _ = reconstruction_loss(prediction, batch, mosaic(prediction, batch["colors"]),
                                      camera_supervision="sensor-valid-v1", reconstruction_charbonnier_epsilon=.0003)
        baseline = torch.autograd.grad(loss, prediction)[0]
        old = next(e for e in case["epsilons"] if e["epsilon"] == .0003)
        norm, slope = float(baseline.norm()), float((baseline*direction).sum())
        assert norm == old["gradient_L2"] and slope == old["detail_direction_derivative"]
        methods = {"baseline": baseline}
        gradients = {"baseline": baseline.numpy()}
        for normalized, name in ((False, "raw-band"), (True, "normalized-band")):
            value = band_penalty(prediction, batch["target"], normalized=normalized)
            gradient = torch.autograd.grad(value, prediction)[0]
            methods[name] = baseline+gradient
            gradients[name] = gradient.numpy()
            a, t, d = prediction.detach().double().numpy(), batch["target"].double().numpy(), direction.double().numpy()
            h = .001
            finite = (numpy_penalty(a+h*d, t, normalized=normalized)-numpy_penalty(a-h*d, t, normalized=normalized))/(2*h)
            actual = float((gradient*direction).sum())
            error = abs(finite-actual)
            assert error < 2e-9+2e-4*abs(actual), (index, name, actual, finite, error)
            errors[name] = max(errors[name], error)
        measures = {}
        for name, gradient in methods.items():
            derivative = float((gradient*direction).sum())
            measures[name] = {"norm": float(gradient.norm()), "directional": derivative,
                              "cosine": -derivative/max(float(gradient.norm()*direction.norm()), 1e-30)}
        extra_bands = {}
        for small, large in ((1, 5), (5, 17)):
            b = band(batch["target"], small, large)
            b[..., :8, :] = b[..., -8:, :] = b[..., :, :8] = b[..., :, -8:] = 0
            coefficient = ((batch["target"]-prediction.detach())*b).sum()/b.square().sum().clamp_min(1e-20)
            delta = coefficient*b
            extra_bands[f"{small}-{large}"] = {"missing_coefficient": float(coefficient),
                                               "directional": {k: float((v*delta).sum()) for k, v in methods.items()}}
        np.savez(root/f"gradients-{index:03d}.npz", **gradients)
        rows.append({"source_id": case["source_id"], "contrast": case["additional_contrast_factor"], "condition": case["condition"],
                     "arrays": case["arrays"], "gradients": binding(root/f"gradients-{index:03d}.npz"),
                     "target_band_rms": case["target_band_RMS"], "missing_coefficient": case["missing_band_coefficient"],
                     "methods": measures, "secondary_analysis_bands": extra_bands})
        if index % 12 == 0:
            print({"completed_saved_cases": index+1, "planned": len(plan["cases"])}, flush=True)
    assert len(rows) == 108 and torch.equal(rng, torch.get_rng_state()) and not torch.cuda.is_initialized()
    guard(plan)
    save(root/"rows.json", rows)
    save(root/"result-v1.json", {"plan": binding(path), "worker": binding(__file__), "owner": owner,
                                "rows": binding(root/"rows.json"), "groups": summarize(rows),
                                "maximum_new_term_F64_directional_errors": dict(errors), "all108_baseline_gradient_norms_and_slopes_exact": True,
                                "new_neural_forwards": 0, "new_encoder_forwards": 0, "optimizer_updates": 0, "RAW_decodes": 0,
                                "new_noise_observations": 0, "CUDA_initialized": False, "Torch_RNG_unchanged": True,
                                "scope": plan["scope"]})
    print({"result": str(root/"result-v1.json"), "cases": len(rows)}, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    run(parser.parse_args().plan)
