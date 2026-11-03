"""GT-using coefficient witnesses for V148; never an inference method."""

import argparse
import os
import shutil
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import guard, read, ref, save

from demosaic.cfa import malvar, mosaic
from demosaic.late_spectral_matrix import LateSpectralMatrixDetail, bounded_real_image_mixing
from demosaic.raw_frequency_features import frequency_descriptor, hermitian_projection

MODES = (
    "GT-scalar-frozen-support",
    "GT-scalar-full-support",
    "GT-matrix-frozen-support",
    "GT-matrix-full-support",
    "GT-matrix-image-alpha",
    "GT-L2-relaxation-full-support",
    "GT-band-residual-full-support",
    "GT-unbanded-residual-full-support",
)


def coefficient_witnesses(innovation, desired, cap):
    """Per-bin GT witnesses, relaxing the shared neural parameterization.

    Scalar is the isotropic least-squares real gain in[-cap,cap]. The rank-one
    matrix maps innovation toward desired, capped by V148's sqrt(1*inf) gauge.
    It is a feasible witness, not the optimal matrix under that gauge. The L2
    row is the closest coefficient vector in the larger induced2-norm ball;
    it is not an RGB-error bound. All rows use the exact desired coefficients.
    """
    tiny = torch.finfo(innovation.real.dtype).tiny
    power = innovation.abs().square().sum(1, keepdim=True)
    scalar = (innovation.conj() * desired).sum(1, keepdim=True).real / power.clamp_min(tiny)
    scalar = torch.maximum(torch.minimum(scalar, cap), -cap)
    size = innovation.shape[-1]
    reverse = (-torch.arange(size, device=innovation.device)) % size
    scalar = (scalar + scalar.index_select(-2, reverse).index_select(-1, reverse)) * 0.5
    scalar_delta = scalar * innovation

    raw = desired[:, :, None] * innovation[:, None].conj() / power[:, :, None].clamp_min(tiny)
    absolute = raw.abs()
    gauge = (absolute.sum(1).amax(1) * absolute.sum(2).amax(1)).sqrt()[:, None]
    divisor = torch.maximum(cap, gauge).clamp_min(tiny)
    matrix = raw / divisor[:, :, None]
    # Keep real/imaginary entries strictly inside tanh's finite-logit range.
    epsilon = 1e-6
    matrix = torch.complex(
        matrix.real.clamp(-1 + epsilon, 1 - epsilon),
        matrix.imag.clamp(-1 + epsilon, 1 - epsilon),
    )
    matrix = bounded_real_image_mixing(matrix)
    matrix_delta = cap * torch.einsum("noihw,nihw->nohw", matrix, innovation)
    radius = cap * power.sqrt()
    desired_norm = desired.abs().square().sum(1, keepdim=True).sqrt()
    relaxed_delta = desired * (radius / desired_norm.clamp_min(tiny)).clamp_max(1)
    relaxed_delta = hermitian_projection(relaxed_delta)
    return scalar_delta, matrix_delta, relaxed_delta, matrix


def image_alpha(base, target, correction):
    """GT-only global camera-RGB MSE line search on the entire context."""
    c = correction.double()
    denominator = c.square().sum()
    if denominator == 0:
        return 0.0
    return float(((target.double() - base.double()) * c).sum().div(denominator).clamp(0, 1))


def prepare(root, trial):
    assert not root.exists()
    training = read(trial / "plan-v1.json")
    guard(training)
    assert psutil.virtual_memory().available > 52 * 2**30
    assert shutil.disk_usage(trial).free > 120 * 2**30
    root.mkdir()
    source = root / "worker-v1.py"
    shutil.copyfile(__file__, source)
    design = read(trial / "quality-design-v1.json")
    cases = [c for c in design["observations"] if c["kind"] != "real"]
    assert len(cases) == 792 and all(
        c["kind"] in ("mesh", "photo", "flat", "mixed-quiet") for c in cases
    )
    for case in cases:
        with np.load(case["arrays"]["path"]) as arrays:
            assert "target" in arrays.files
    collections = read(trial / "review-result-v1.json")["collections"]
    binding = collections["phase-matrix-raw-step1000"]
    collection = read(binding["path"])
    inputs = [ref(trial / "plan-v1.json"), ref(trial / "quality-design-v1.json"), binding]
    inputs += [ref(trial / "figures-v1.json"), collection["export"]]
    metric_paths = [
        trial.parent / "collaborative-detail-v1/transfer-v1.py",
        trial.parent / "V144-V145-photo-supplement-v1/operator-v2.py",
        trial.parent / "collaborative-detail-v1/audit-transfer-v1.py",
    ]
    inputs += [ref(p) for p in metric_paths]
    save(
        root / "plan-v1.json",
        {
            "root": str(root),
            "trial": str(trial),
            "training_plan": ref(trial / "plan-v1.json"),
            "worker": ref(source),
            "source_modules": training["source_modules"],
            "inputs": inputs,
            "frozen_files": training["frozen_files"],
            "export": collection["export"],
            "collection": binding,
            "cases": cases,
            "modes": list(MODES),
            "new_component_forwards": 792,
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "estimated_output_GiB": 20,
            "CUDA_quota_GiB": 12,
            "RAM_admission_GiB": 52,
            "RAM_runtime_floor_GiB": 32,
            "internal_disk_floor_GiB": 96,
            "external_disk_floor_GiB": 208,
            "oracle_uses_exact_GT": True,
            "shared_neural_parameterization_relaxed": True,
            "definitions": {
                "desired": "analysis(mosaic(exact_constructed_target))-parent_spectrum",
                "innovation": "analysis(observed_RAW)-parent_spectrum",
                "cap": "same_observed_power_fraction*same_radial_band",
                "frozen_support": "Actual V148 raw1k support, held fixed after replay of original forward; not recomputed from an oracle proposal",
                "full_support": "Shared spatial support1, the sigmoid-family closure",
                "matrix": "Rank-one per-bin feasible witness under exact V148 matrix bound. Strict real/imaginary entries within1-1e-6. This is not an optimal gauge-constrained solve or a shared-network representability proof.",
                "L2": "Closest isotropic coefficient vector under relaxed induced2-norm cap; not an image-error bound or exact V148 family",
                "band_residual": "desired*radial_band, without innovation/power amplitude restriction",
                "unbanded_residual": "desired directly through the same affine-removal/STFT synthesis/Malvar geometry",
                "image_alpha": "Whole-context exact-GT camera-RGB MSE line search in[0,1] after the full-support feasible matrix witness; no crop selection",
            },
            "scope": "Fixed posthoc mechanism diagnostic on all792 retained constructed-target cases. Eight GT-using rows, no endpoint selection. Real6 contexts excluded because their references are not exactGT; standing real evidence remains the completed V148 review. Target-aware outputs are unavailable as inference and cannot be promoted as quality improvements. No noise draws, parent/DINO calls or RAW decoding.",
        },
    )
    print("Prepared792 cases and8 explicitly GT-using diagnostic rows")


def worker(root):
    plan_path = root / "plan-v1.json"
    plan = read(plan_path)
    guard(plan)
    assert ref(__file__) == plan["worker"]
    (root / "worker.claim").open("x").close()
    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[2:4])
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = torch.backends.cudnn.allow_tf32 = False
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    torch.cuda.set_per_process_memory_fraction(
        12 * 2**30 / torch.cuda.get_device_properties(0).total_memory
    )
    assert psutil.virtual_memory().available > 52 * 2**30
    saved = torch.load(plan["export"]["path"], map_location="cpu", weights_only=True)
    module = LateSpectralMatrixDetail(**saved["module_config"]).cuda().eval()
    module.load_state_dict(saved["state_dict"], strict=True)
    training = read(plan["training_plan"]["path"])
    assert (
        Path(module.forward.__code__.co_filename)
        .resolve()
        .is_relative_to(Path(training["work"]) / "src")
    )
    cpu_rng, cuda_rng = torch.get_rng_state().clone(), torch.cuda.get_rng_state().clone()
    initial = model_hash(module)
    old = {o["id"]: o for o in read(plan["collection"]["path"])["observations"]}
    count = [0]
    module.register_forward_hook(lambda *args: count.__setitem__(0, count[0] + 1))
    for mode in MODES:
        (root / mode).mkdir()
    journal = (root / "trace-v1.jsonl").open("x")
    observations = []
    with torch.inference_mode():
        for index, case in enumerate(plan["cases"]):
            assert psutil.virtual_memory().available > 32 * 2**30
            assert shutil.disk_usage(root).free > 96 * 2**30
            assert shutil.disk_usage("/mnt/external").free > 208 * 2**30
            assert ref(case["arrays"]["path"]) == case["arrays"]
            assert ref(case["parent"]["path"]) == case["parent"]
            a = dict(np.load(case["arrays"]["path"]))
            batch = {
                k: torch.from_numpy(a[k]).cuda() for k in ("packed", "variance", "colors", "wb")
            }
            base = torch.from_numpy(np.load(case["parent"]["path"])).cuda()
            output, aux = module(base, **batch, return_aux=True)
            np.testing.assert_array_equal(
                output.cpu().numpy(), np.load(old[case["id"]]["prediction"]["path"])
            )
            target = torch.from_numpy(a["target"]).cuda()
            observed, geometry = module.analysis(batch["packed"])
            desired, _ = module.analysis(mosaic(target, batch["colors"]), geometry[4])
            desired -= aux["parent_spectrum"]
            innovation = observed - aux["parent_spectrum"]
            layouts = batch["colors"][:, None].expand(-1, geometry[5], -1).reshape(-1, 4)
            descriptor = frequency_descriptor(observed, aux["noise_power"], layouts)
            band = getattr(module, f"band_{geometry[4]}")
            cap = descriptor[:, :4].sum(1, keepdim=True) * band
            scalar, matrix, relaxed, H = coefficient_witnesses(innovation, desired, cap)
            absolute = H.abs()
            bound = (absolute.sum(1).amax(1) * absolute.sum(2).amax(1)).sqrt()
            assert bound.max() <= 1 + 2e-6
            assert torch.isfinite(H).all()
            del H, absolute, output
            fields = {
                "scalar": scalar,
                "matrix": matrix,
                "L2": relaxed,
                "band": desired * band,
                "unbanded": desired,
            }
            proposals = {k: module.synthesis(v, geometry) for k, v in fields.items()}
            full_matrix = malvar(proposals["matrix"], batch["colors"], batch["wb"])
            alpha = image_alpha(base, target, full_matrix)
            predictions = {}
            for label in MODES:
                if "image-alpha" in label:
                    correction = full_matrix * alpha
                else:
                    key = (
                        "scalar"
                        if "scalar" in label
                        else "matrix"
                        if "matrix" in label
                        else "L2"
                        if "L2" in label
                        else "unbanded"
                        if "unbanded" in label
                        else "band"
                    )
                    proposal = proposals[key]
                    if "frozen-support" in label:
                        proposal = proposal * aux["support"]
                    correction = malvar(proposal, batch["colors"], batch["wb"])
                value = (base + correction).cpu().numpy()
                assert value.dtype == np.float32 and np.isfinite(value).all()
                dest = root / label / f"prediction-{index:03d}.npy"
                np.save(dest, value)
                predictions[label] = ref(dest)
            row = {
                "id": case["id"],
                "index": index,
                "predictions": predictions,
                "replayed_prediction_exact": True,
                "component_forwards": 1,
                "frozen_support_mean": float(aux["support"].mean()),
                "image_alpha": alpha,
                "maximum_matrix_gauge": float(bound.max()),
                "coefficient_squared_error": {
                    k: float((v - desired).abs().square().sum()) for k, v in fields.items()
                },
                "parent_coefficient_squared_error": float(desired.abs().square().sum()),
                "learned_coefficient_squared_error": float(
                    (aux["spectral_delta"] - desired).abs().square().sum()
                ),
            }
            observations.append(row)
            import json

            journal.write(json.dumps(row, allow_nan=False) + "\n")
            journal.flush()
            if index % 16 == 0:
                save(
                    root / "status-v1.json",
                    {
                        "status": "running-fixed-oracle-diagnostic",
                        "done": index + 1,
                        "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
                        "plan": ref(plan_path),
                    },
                )
                print("completed", index + 1, "of792", flush=True)
            del (
                a,
                batch,
                base,
                aux,
                target,
                observed,
                desired,
                innovation,
                layouts,
                descriptor,
                cap,
                scalar,
                matrix,
                relaxed,
                fields,
                proposals,
                full_matrix,
                correction,
                value,
                proposal,
                bound,
            )
    assert count[0] == 792 and model_hash(module) == initial
    assert torch.equal(cpu_rng, torch.get_rng_state()) and torch.equal(
        cuda_rng, torch.cuda.get_rng_state()
    )
    guard(plan)
    save(
        root / "result-v1.json",
        {
            "status": "completed-GT-using-diagnostic-awaiting-array-audit-native-review",
            "plan": ref(plan_path),
            "worker": ref(__file__),
            "observations": observations,
            "new_component_forwards": count[0],
            "new_parent_DINO_forwards": 0,
            "new_noise_draws": 0,
            "model_before": initial,
            "model_after": model_hash(module),
            "RNG_unchanged": True,
            "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
            "scope": plan["scope"],
        },
    )
    save(
        root / "status-v1.json",
        {
            "status": "completed-fixed-oracle-diagnostic",
            "result": ref(root / "result-v1.json"),
            "owner": {"pid": os.getpid(), "created": psutil.Process().create_time()},
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "worker"))
    parser.add_argument("root", type=Path)
    parser.add_argument("--trial", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.root.absolute(), args.trial.absolute())
    else:
        worker(args.root.absolute())
