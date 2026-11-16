"""Fit explicit GT oracles to a closed, input-only additional-wave bank.

These are free constant gains per carrier/color/role, not learned predictions.
They witness what this restricted synthesis can deliver, without bounding the
spatially varying head. The phase-free/unbounded variants relax its constraints.
"""

import argparse
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

REPO = next(p for p in Path(__file__).resolve().parents if (p / "PROMPT.md").is_file())
METHODS = ("oracle-real-bounded", "oracle-real-unbounded", "oracle-phase-free")


def native_basis(waves, bins, *, quadrature=False):
    """One role/color: Kx2xhxw measured waves -> Kx2hx2w native basis.

    The first K columns exactly use the real-gate synthesis. Optional next K
    columns multiply the complex wave by i before taking its native real part.
    This allows phase rotation and is outside the actual real-gated head.
    """
    waves, bins = np.asarray(waves), np.asarray(bins)
    if (
        waves.ndim != 4
        or waves.shape[1] != 2
        or waves.dtype not in (np.float32, np.float64)
        or bins.shape != (len(waves), 2)
        or bins.dtype.kind not in "iu"
        or not np.isfinite(waves).all()
    ):
        raise ValueError("Require finite Kx2xhxw waves and integer Kx2 bins")
    k, _, h, w = waves.shape
    if np.any(bins < 0) or np.any(bins >= [h, w]):
        raise ValueError("FFT bins are outside the supplied packed axes")
    signed = np.where(bins <= (np.array([h, w]) - 1) // 2, bins, bins - [h, w])
    offsets = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], np.float64)
    angle = np.pi * (signed.astype(np.float64) / [h, w]) @ offsets.T
    cosine, sine = [f(angle).astype(waves.dtype)[:, :, None, None] for f in (np.cos, np.sin)]
    real, imag = waves[:, 0, None], waves[:, 1, None]
    parts = [real * cosine - imag * sine]
    if quadrature:
        parts.append(-real * sine - imag * cosine)
    return (
        np.concatenate(parts)
        .reshape(-1, 2, 2, h, w)
        .transpose(0, 3, 1, 4, 2)
        .reshape(k * len(parts), 2 * h, 2 * w)
    )


def fit_constant_gains(basis, residual, *, bounded):
    """Solve the small global normal problem in FP64, retaining a KKT bound.

    Eigenspace truncation is numerical rank only (1e-12 of the largest Gram
    eigenvalue). No ridge, spatial gates, target-dependent carrier selection or
    fitting-region selection is introduced. Zero is always feasible.
    """
    basis, residual = np.asarray(basis, np.float64), np.asarray(residual, np.float64)
    if basis.ndim != 3 or basis.shape[1:] != residual.shape or not np.isfinite(basis).all():
        raise ValueError("Require matching finite KxHxW basis and HxW target residual")
    if not np.isfinite(residual).all() or not len(basis):
        raise ValueError("Require finite target residual and nonempty carrier slots")
    design = basis.reshape(len(basis), -1)
    target = residual.ravel()
    gram = design @ design.T / len(target)
    rhs = design @ target / len(target)
    eigenvalues, vectors = np.linalg.eigh(gram)
    scale = float(eigenvalues[-1])
    if eigenvalues[0] < -max(scale, 1e-30) * 1e-10:
        raise ArithmeticError("Wave Gram is not positive semidefinite")
    keep = eigenvalues > max(scale * 1e-12, 0)
    if not keep.any():
        coefficients = np.zeros(len(basis))
    else:
        values, active = eigenvalues[keep], vectors[:, keep]
        if bounded:
            from scipy.optimize import lsq_linear

            reduced = np.sqrt(values)[:, None] * active.T
            response = (active.T @ rhs) / np.sqrt(values)
            fitted = lsq_linear(
                reduced, response, bounds=(-1, 1), method="bvls", tol=1e-12, max_iter=200
            )
            if not fitted.success:
                raise ArithmeticError("Bounded constant-gain solve did not converge")
            coefficients = fitted.x
        else:
            coefficients = active @ ((active.T @ rhs) / values)
    delivered = (coefficients @ design).reshape(residual.shape)
    zero_mse = float(np.mean(residual**2))
    mse = float(np.mean((delivered - residual) ** 2))
    gradient = gram @ coefficients - rhs
    # Convex box dual gap bounds suboptimality of the full untruncated problem.
    gap = float(np.sum(gradient * coefficients + np.abs(gradient))) if bounded else None
    tolerance = max(1e-20, zero_mse * 1e-9)
    if mse > zero_mse + tolerance or (bounded and np.max(np.abs(coefficients)) > 1 + 1e-12):
        raise ArithmeticError("Oracle failed zero-feasibility or coefficient bounds")
    if bounded and gap > max(1e-18, zero_mse * 1e-7):
        raise ArithmeticError("Full-space bounded-gain optimality gap is too large")
    return delivered, {
        "coefficients": coefficients.tolist(),
        "numerical_rank": int(keep.sum()),
        "slots": len(basis),
        "zero_MSE": zero_mse,
        "fitted_MSE": mse,
        "box_duality_gap_half_MSE": max(0.0, gap) if bounded else None,
        "gradient_infinity_norm": float(np.max(np.abs(gradient))),
        "maximum_absolute_gain": float(np.max(np.abs(coefficients))),
        "gains_at_bounds": int(np.sum(np.abs(coefficients) >= 1 - 1e-9)) if bounded else 0,
    }


def prepare(root):
    closed_path = REPO / ".cache/experiments/complementary-phase-diagnostic-v1/selections.json"
    closed = read_json(closed_path)
    cache_path = REPO / ".cache/experiments/near-edge-response-iso400-v1/cache.json"
    cache = read_json(cache_path)
    scores_path = REPO / ".cache/experiments/complementary-edge-review-corrected-v1/scores.json"
    scores = read_json(scores_path)
    selected = {r["index"]: r for r in closed["rows"] if r["profile"] == "iso400"}
    rows = []
    for item in cache["rows"]:
        if item["metadata"]["placement"] != "far":
            continue
        choice = selected[item["index"]]
        if choice["arrays"] != item["arrays"]:
            raise ValueError("Closed carrier input differs from the fixed quality panel")
        rows.append(
            {
                "index": item["index"],
                "arrays": item["arrays"],
                "anchor": choice["anchor"],
                "learned": scores["native_predictions"]["iso400"][str(item["index"])]["ema"],
                "field": choice["field"],
                "choice": choice["choices"]["additional-only"],
                "metadata": item["metadata"],
                "input_fingerprints": item["inputs"],
            }
        )
    expected = {
        (s, c, r) for s in range(8) for c in ["RGGB", "GRBG", "GBRG", "BGGR"] for r in [0, 1]
    }
    actual = {
        (r["metadata"]["recipe"]["source"], r["metadata"]["pattern"], r["metadata"]["repeat"])
        for r in rows
    }
    if len(rows) != 64 or actual != expected:
        raise ValueError("Require all64 far/400 views, all8 sources,4 CFAs,2 repeats")
    root.mkdir(parents=True, exist_ok=False)
    frozen = REPO / ".cache/experiments/complementary-edge-review-corrected-v1/work"
    work, files = freeze_sources(frozen, root)
    tested_sources = []
    for name in [
        "late_cfa_innovation_wave.py",
        "late_scale_supported_cfa_wave.py",
        "late_local_phase_evidence_matching.py",
        "cfa.py",
        "experiments/evaluation/edge_response.py",
    ]:
        current, actual = REPO / "src/demosaic" / name, work / "src/demosaic" / name
        if reference(current)["sha256"] != reference(actual)["sha256"]:
            raise ValueError(
                "Tested current synthesis/metric source differs from frozen evaluation"
            )
        tested_sources.append(reference(actual))
    for name in ["pyproject.toml", "uv.lock"]:
        shutil.copyfile(REPO / name, work / name)
        files[str(work / name)] = reference(work / name)["sha256"]
    recipe_path = REPO / "configs/experiments/complementary.json"
    config = read_json(recipe_path)["model"]["config"]
    if config["evidence_window"] != 65 or config["evidence_stride"] != 32:
        raise ValueError("Original trained measurement window/stride differs")
    script = work / "scripts" / Path(__file__).name
    script.parent.mkdir()
    shutil.copyfile(__file__, script)
    files[str(script)] = reference(script)["sha256"]
    dependencies = [reference(p) for p in [closed_path, cache_path, scores_path, recipe_path]]
    dependencies += [r[k] for r in rows for k in ["arrays", "anchor", "learned"]]
    plan = {
        "root": str(root),
        "work": str(work),
        "script": reference(script),
        "python": sys.executable,
        "closed_selections": reference(closed_path),
        "source_cache": reference(cache_path),
        "saved_learned_scores": reference(scores_path),
        "tested_current_sources_exact": tested_sources,
        "rows": rows,
        "window": 65,
        "stride": 32,
        "methods": list(METHODS),
        "maximum_phase_seconds": 3600,
        "inputs": list({(b["path"], b["sha256"]): b for b in dependencies}.values()),
        "frozen_files": files,
        "scope": "All64 fixed400/far views,8 sources x4 CFAs x2 independent repeats,3 roles. Additional8-slot bank only, anchored at saved full V200EMA. PhaseA loads only packed/variance/colors and saved anchor, never target arrays or recipe geometry; same frozen physical-wave source/CUDA backend as trained evaluation, no selector/model/readout calls. All measured bases close before PhaseB GT access. PhaseB fits constant gains per carrier/color/role to full native512 camera-RGB target residual. Real bounded [-1,1], unbounded real and relaxed phase-free oracles. Explicit GT diagnostics, not inference, not a spatial-head capacity bound or independent confidence. Zero new model/parent/DINO/readout/source/noise/RAW/optimizer work. Original V132 training untouched.",
    }
    write_json(root / "plan.json", plan)
    verify_plan(plan)
    return root / "plan.json"


def measure_basis(root):
    import torch

    from demosaic.cfa import mosaic
    from demosaic.experiments.evaluation.native import load_native
    from demosaic.experiments.runtime import RuntimePolicy, owner_identity
    from demosaic.late_cfa_innovation_wave import cfa_innovation_wave_maps
    from demosaic.prediction_archive import fingerprint

    plan = read_json(root / "plan.json")
    verify_plan(plan)
    if reference(__file__) != plan["script"]:
        raise ValueError("Use the declared frozen source")
    (root / "measure.claim").open("x").close()
    write_json(root / "measure-owner.json", owner_identity())
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    policy = RuntimePolicy(cuda_quota_gib=2, minimum_ram_gib=32, minimum_disk_gib=96)
    policy.resources(root)
    policy.apply()

    def forbidden(*args, **kwargs):
        raise RuntimeError("No neural construction or forward permitted in basis measurement")

    torch.nn.Module.__init__ = torch.nn.Module._call_impl = forbidden
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    output = root / "basis"
    output.mkdir()
    rows, began = [], time.monotonic()
    try:
        with torch.inference_mode():
            for row in plan["rows"]:
                if time.monotonic() - began >= plan["maximum_phase_seconds"]:
                    raise TimeoutError("Basis-measurement phase budget reached")
                policy.resources(root)
                # The npz also holds targets/masks. Deliberately load only input keys.
                with np.load(checked(row["arrays"]), allow_pickle=False) as z:
                    arrays = {k: z[k] for k in ["packed", "variance", "colors"]}
                if any(fingerprint(v) != row["input_fingerprints"][k] for k, v in arrays.items()):
                    raise ValueError("Retained RAW input values differ")
                packed, variance, colors = [torch.from_numpy(v).cuda() for v in arrays.values()]
                anchor = torch.from_numpy(load_native(row["anchor"])).cuda()
                field = packed - mosaic(anchor, colors)
                if fingerprint(field.cpu().numpy()) != row["field"]:
                    raise ValueError("Closed input-only residual differs")
                bins = torch.tensor(row["choice"]["bins_yx"], device="cuda")
                valid = torch.tensor(row["choice"]["valid"], device="cuda", dtype=torch.bool)
                context, waves, evidence = cfa_innovation_wave_maps(
                    field,
                    variance,
                    colors,
                    bins,
                    valid,
                    window=plan["window"],
                    stride=plan["stride"],
                )
                value = waves.cpu().numpy()
                if value.shape != (3, 8, 3, 2, 256, 256) or not np.isfinite(value).all():
                    raise ValueError("Physical measured-wave layout differs")
                path = output / f"waves-{row['index']:04d}.npy"
                with path.open("xb") as stream:
                    np.save(stream, value, allow_pickle=False)
                rows.append(
                    {"index": row["index"], "waves": reference(path), "values": fingerprint(value)}
                )
                del context, waves, evidence, field, anchor, packed, variance, colors
                if len(rows) % 8 == 0:
                    print("closed", len(rows), "of64 target-free measured bases", flush=True)
        if not torch.equal(cpu_rng, torch.get_rng_state()) or not torch.equal(
            cuda_rng, torch.cuda.get_rng_state()
        ):
            raise ValueError("Basis measurement changed RNG")
        verify_plan(plan)
        write_json(
            root / "closed-bases.json",
            {
                "status": "all64-input-only-physical-bases-closed-before-GT-access",
                "plan": reference(root / "plan.json"),
                "rows": rows,
                "neural_constructions_and_forwards": 0,
                "selector_calls": 0,
                "targets_loaded": 0,
                "new_source_noise_draws": 0,
                "RNG_unchanged": True,
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "elapsed_seconds": time.monotonic() - began,
            },
        )
    except BaseException as error:
        write_json(
            root / "measure-failure.json", {"error": repr(error), "completed_bases": len(rows)}
        )
        raise


def fit_oracles(root):
    from importlib.metadata import version

    from demosaic.experiments.evaluation.edge_response import measure
    from demosaic.experiments.evaluation.native import load_native
    from demosaic.experiments.runtime import RuntimePolicy, owner_identity
    from demosaic.prediction_archive import fingerprint

    if "torch" in sys.modules:
        raise RuntimeError("Run oracle fitting in a fresh NumPy/SciPy-only process")
    plan = read_json(root / "plan.json")
    verify_plan(plan)
    if reference(__file__) != plan["script"]:
        raise ValueError("Use the declared frozen source")
    closed = read_json(root / "closed-bases.json")
    if closed["plan"] != reference(root / "plan.json") or len(closed["rows"]) != 64:
        raise ValueError("Require the complete target-free basis closure")
    (root / "fit.claim").open("x").close()
    write_json(root / "fit-owner.json", owner_identity())
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[-2:])
    policy = RuntimePolicy(device="cpu", minimum_ram_gib=32, minimum_disk_gib=96)
    output = root / "oracle"
    output.mkdir()
    saved_scores = read_json(checked(plan["saved_learned_scores"]))
    old = {
        r["index"]: r
        for r in saved_scores["rows"]
        if r["profile"] == "iso400" and r["method"] == "complementary-ema" and r["gain_scale"] == 1
    }
    results, fits, predictions, began = [], [], {}, time.monotonic()
    for row, basis_row in zip(plan["rows"], closed["rows"], strict=True):
        policy.resources(root)
        if row["index"] != basis_row["index"]:
            raise ValueError("Closed basis identity/order differs")
        if time.monotonic() - began >= plan["maximum_phase_seconds"]:
            raise TimeoutError("Oracle-fitting phase budget reached")
        with np.load(checked(row["arrays"]), allow_pickle=False) as z:
            arrays = {k: z[k] for k in ["target", "quiet", "edge_band"]}
        if any(fingerprint(v) != row["input_fingerprints"][k] for k, v in arrays.items()):
            raise ValueError("Retained target/mask values differ")
        anchor, learned = [load_native(row[k]).astype(np.float64) for k in ["anchor", "learned"]]
        waves = np.load(checked(basis_row["waves"]), allow_pickle=False)
        if fingerprint(waves) != basis_row["values"]:
            raise ValueError("Closed measured basis values changed")
        bins = np.array(row["choice"]["bins_yx"]).reshape(3, 8, 2)
        residual = arrays["target"].astype(np.float64) - anchor
        values = {name: anchor.copy() for name in METHODS}
        for role in range(3):
            for color in range(3):
                real = native_basis(waves[role, :, color], bins[role])
                relaxed = native_basis(waves[role, :, color], bins[role], quadrature=True)
                for name, basis, bounded in [
                    (METHODS[0], real, True),
                    (METHODS[1], real, False),
                    (METHODS[2], relaxed, False),
                ]:
                    correction, receipt = fit_constant_gains(
                        basis, residual[role, color], bounded=bounded
                    )
                    values[name][role, color] += correction
                    fits.append(
                        {
                            "index": row["index"],
                            "role": role,
                            "color": color,
                            "method": name,
                            **receipt,
                        }
                    )
        saved = {}
        for name, value in {"V200-ema": anchor, "complementary-ema": learned, **values}.items():
            metrics = measure(arrays, value)
            if name == "complementary-ema" and any(
                metrics[k] != old[row["index"]][k] for k in metrics
            ):
                raise ValueError("Recomputed learned metrics differ from saved complete review")
            results.append(
                {
                    "index": row["index"],
                    "source": row["metadata"]["recipe"]["source"],
                    "pattern": row["metadata"]["pattern"],
                    "repeat": row["metadata"]["repeat"],
                    "method": name,
                    **metrics,
                }
            )
            if name in METHODS:
                path = output / f"{row['index']:04d}-{name}.npy"
                with path.open("xb") as stream:
                    np.save(stream, value, allow_pickle=False)
                saved[name] = reference(path)
        predictions[str(row["index"])] = saved
        if len(predictions) % 8 == 0:
            print("fitted", len(predictions), "of64 closed-basis GT oracles", flush=True)
    verify_plan(plan)
    if "torch" in sys.modules:
        raise RuntimeError("Oracle fitting imported Torch")
    write_json(root / "fits.json", {"rows": fits, "oracle_uses_GT": True})
    write_json(
        root / "scores.json",
        {
            "status": "completed-global-target-assisted-basis-diagnostic-not-inference",
            "plan": reference(root / "plan.json"),
            "closed_bases": reference(root / "closed-bases.json"),
            "rows": results,
            "fits": reference(root / "fits.json"),
            "predictions": predictions,
            "Torch_imported": False,
            "numpy": np.__version__,
            "scipy": version("scipy"),
            "new_neural_forwards": 0,
            "elapsed_seconds": time.monotonic() - began,
            "scope": plan["scope"],
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "measure", "fit"])
    parser.add_argument("root", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.mode == "prepare":
        print(prepare(root))
    elif args.mode == "measure":
        measure_basis(root)
    else:
        fit_oracles(root)
