"""Measure zero-head coefficient gradients on frozen, balanced training batches.

The follow-up projects gradients through the actual shared output layer at zero
initialization. Ten fresh native-head forwards independently check all parameter
gradients under the old floor and a16DN loss floor. It does not measure quality
or later training dynamics. The original coefficient-only run remains frozen.
"""

import argparse
import json
import os
import shutil
import time
from collections import Counter
from pathlib import Path

import psutil
from train_directional_bank_trial import guard, read, ref, save

REPO = Path(__file__).resolve().parents[1]


def prepare(root):
    root = root.absolute()
    assert root.is_relative_to(REPO / ".cache") and not root.exists()
    previous = REPO / ".cache/quality-20261103/V149-coherent-phase-v1"
    old = read(previous / "plan-v1.json")
    guard(old)
    prior = REPO / ".cache/quality-20261103/V149-loss-allocation-v1/result-v1.json"
    assert read(prior)["status"] == "completed-zero-head-gradient-diagnostic"
    cache = read(old["cache"]["path"])
    counts, selected = Counter(), []
    for row in cache["batches"]:
        domain = row["metadata"]["domain"]
        if counts[domain] < 20:
            counts[domain] += 1
            selected.append(row)
    assert counts == dict.fromkeys(["mesh", "weak", "flat", "mixed", "photo"], 20)
    assert len(selected) == 100
    assert psutil.virtual_memory().available > 52 * 2**30
    assert shutil.disk_usage(REPO).free > 98 * 2**30
    assert shutil.disk_usage("/mnt/external").free > 208 * 2**30
    root.mkdir(parents=True)
    work = root / "work"
    for source in (REPO / "src/demosaic").glob("*.py"):
        target = work / "src/demosaic" / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    for name in [Path(__file__).name, "train_directional_bank_trial.py"]:
        target = work / "scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPO / "scripts" / name, target)
    runner = work / "scripts" / Path(__file__).name
    save(
        root / "plan-v1.json",
        {
            "root": str(root),
            "work": str(work),
            "runner": ref(runner),
            "inputs": [
                ref(previous / "plan-v1.json"),
                old["cache"],
                old["shared_recipe"],
                ref(prior),
            ],
            "prior_coefficient_diagnostic": ref(prior),
            "frozen_files": {str(p): ref(p)["sha256"] for p in work.rglob("*") if p.is_file()},
            "cache": old["cache"],
            "shared_recipe": old["shared_recipe"],
            "selected": selected,
            "selection": "First20 batches in each of5 domains in original cached order;100 batches/400 observations. No quality outputs or selection by measured gradients.",
            "clean_power_noise_ratio_bins": [[0, 0.1], [0.1, 1], [1, 10], [10, None]],
            "focused_weight": "1+7*r/(1+r), r=sum(clean FFT power)/sum(floored frame noise proxy); no weight renormalization; floor1/max8",
            "additional_loss_floor_DN16": 16,
            "scope": "Zero-head initialization only. Fixed synthesis/gate0.5/Malvar. Project the coefficient cotangents through the actual initial48-to32 frequency convolution and shared32-to32 complex-matrix output. All other parameter gradients are zero at initialization. Compare old2DN floor with16DN for both RGB scale and spectral variance, without changing model inputs. No claim about subsequent Adam dynamics or trained quality. The original coefficient-only diagnostic remains unchanged. Ten full fresh-head forwards each check all12 actual parameter gradients under both floors.100 additional initial frequency-hidden convolution evaluations. No optimizer/new parent/DINO/noise calls, no RAW/original media lookup.",
        },
    )
    print(root / "plan-v1.json")


def rgb_losses(output, target, variance, config):
    scale = variance.clamp_min(0).mean((1, 2, 3), keepdim=True).sqrt()
    scale = scale.clamp_min(config["noise_unit_floor_DN16"] / 65535)
    error = (output - target) / scale
    pixel = (error.square() + config["pixel_epsilon_in_noise_units"] ** 2).sqrt().mean()
    derivative = [error[..., 1:] - error[..., :-1], error[..., 1:, :] - error[..., :-1, :]]
    gradient = (
        sum(
            (v.square() + config["gradient_epsilon_in_noise_units"] ** 2).sqrt().mean()
            for v in derivative
        )
        / 2
    )
    return pixel, gradient


def matrix_cotangent(gradient, innovation, factor):
    from demosaic.raw_frequency_features import hermitian_projection

    raw = gradient[:, :, None] * innovation[:, None].conj()
    return hermitian_projection(raw) * factor[:, None]


def output_parameter_gradient(field, hidden):
    import torch

    bias = field.real.sum((0, 3, 4)).flatten()
    channels = torch.stack((field.real, field.imag), 3).flatten(1, 3)
    weight = torch.einsum("nohw,nihw->oi", channels, hidden).flatten()
    return torch.cat((bias, weight))


def runtime(root):
    import torch

    os.nice(10)
    os.sched_setaffinity(0, sorted(os.sched_getaffinity(0))[:2])
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
    return torch


def run(path):
    import numpy as np
    import yaml

    from demosaic.cfa import malvar, mosaic
    from demosaic.late_spectral_matrix import LateSpectralMatrixDetail
    from demosaic.precision import ieee_fp32
    from demosaic.prediction_archive import fingerprint
    from demosaic.raw_frequency_features import frequency_descriptor

    plan = read(path)
    guard(plan)
    root = Path(plan["root"])
    assert ref(__file__) == plan["runner"]
    (root / "run.claim").open("x").close()
    owner = {"pid": os.getpid(), "created": psutil.Process().create_time()}
    torch = runtime(root)
    config = yaml.safe_load(Path(plan["shared_recipe"]["path"]).read_text())
    module = LateSpectralMatrixDetail(256).cuda().requires_grad_(False)
    initial = {k: v.detach().cpu().clone() for k, v in module.state_dict().items()}
    rows, checks, parameter_rows, vectors = [], [], [], []
    progress = {}
    try:
        with (root / "trace-v1.jsonl").open("x") as trace, ieee_fp32():
            for index, item in enumerate(plan["selected"]):
                assert psutil.virtual_memory().available > 32 * 2**30
                assert shutil.disk_usage(root).free > 96 * 2**30
                assert shutil.disk_usage("/mnt/external").free > 208 * 2**30
                assert ref(item["arrays"]["path"]) == item["arrays"]
                arrays = dict(np.load(item["arrays"]["path"]))
                base = torch.from_numpy(arrays.pop("parent")).cuda()
                assert {k: fingerprint(v) for k, v in arrays.items()} == item["inputs"]
                b = {k: torch.from_numpy(v).cuda() for k, v in arrays.items()}
                with torch.no_grad():
                    observed, geometry = module.analysis(b["packed"])
                    parent, _ = module.analysis(mosaic(base, b["colors"]), geometry[4])
                    clean, _ = module.analysis(mosaic(b["target"], b["colors"]), geometry[4])
                    noise = module.noise_power(b["variance"], geometry)
                    variance = noise[:, :, None, None].clamp_min((2 / 65535) ** 2)
                    band = getattr(module, f"band_{geometry[4]}")
                    ratio = clean.abs().square().sum(1) / variance.sum(1)
                    focus = 1 + 7 * ratio / (1 + ratio)
                    assert focus.min() >= 1 and focus.max() <= 8
                    count = geometry[5]
                    layouts = b["colors"][:, None].expand(-1, count, -1).reshape(-1, 4)
                    descriptor = frequency_descriptor(observed, noise, layouts)
                    innovation_descriptor = frequency_descriptor(
                        innovation := observed - parent, noise, layouts
                    )
                    hidden = torch.nn.functional.silu(
                        module.frequency_in(
                            torch.cat((descriptor, innovation_descriptor[:, :17]), 1)
                        )
                    )
                    factor = descriptor[:, :4].sum(1, keepdim=True) * band
                    innovation = observed - parent
                    desired = clean - parent
                delta = torch.zeros_like(observed, requires_grad=True)
                correction = malvar(module.synthesis(delta, geometry) * 0.5, b["colors"], b["wb"])
                output = base + correction
                assert torch.equal(output, base)
                pixel, gradient = rgb_losses(output, b["target"], b["variance"], config)
                output_spectrum, _ = module.analysis(mosaic(output, b["colors"]), geometry[4])
                denominator = band.sum().clamp_min(1) * len(clean) * 4
                coefficient_error = (delta - desired).abs().square() / variance * band
                output_error = (output_spectrum - clean).abs().square() / variance * band
                domain_weight = config["domain_loss_weights"][item["metadata"]["domain"]]
                terms = {
                    "pixel": domain_weight * pixel,
                    "gradient": domain_weight * config["gradient_weight"] * gradient,
                    "legacy_spectral": domain_weight
                    * config["spectral_weight"]
                    * coefficient_error.sum()
                    / denominator,
                    "post_spectral": domain_weight
                    * config["spectral_weight"]
                    * output_error.sum()
                    / denominator,
                    "focused_post_spectral": domain_weight
                    * config["spectral_weight"]
                    * (output_error * focus[:, None]).sum()
                    / denominator,
                }
                assert torch.equal(terms["legacy_spectral"], terms["post_spectral"])
                floor16 = plan["additional_loss_floor_DN16"]
                pixel16, gradient16 = rgb_losses(
                    output, b["target"], b["variance"], {**config, "noise_unit_floor_DN16": floor16}
                )
                variance16 = noise[:, :, None, None].clamp_min((floor16 / 65535) ** 2)
                terms.update(
                    {
                        "pixel16": domain_weight * pixel16,
                        "gradient16": domain_weight * config["gradient_weight"] * gradient16,
                        "spectral16": domain_weight
                        * config["spectral_weight"]
                        * ((delta - desired).abs().square() / variance16 * band).sum()
                        / denominator,
                    }
                )
                gradients = {
                    k: torch.autograd.grad(value, delta, retain_graph=i < len(terms) - 1)[
                        0
                    ].detach()
                    for i, (k, value) in enumerate(terms.items())
                }
                gradients["RGB"] = gradients["pixel"] + gradients["gradient"]
                for name in ["legacy", "post", "focused_post"]:
                    gradients[name + "_total"] = gradients["RGB"] + gradients[name + "_spectral"]
                gradients["floor16_total"] = (
                    gradients["pixel16"] + gradients["gradient16"] + gradients["spectral16"]
                )
                projected = {}
                energy = {}
                for name, grad in gradients.items():
                    field = matrix_cotangent(grad, innovation, factor)
                    energy[name] = field.abs().square().sum((1, 2))
                    projected[name] = output_parameter_gradient(field, hidden)
                    assert (
                        torch.isfinite(energy[name]).all() and torch.isfinite(projected[name]).all()
                    )
                    del field
                if index < 10:
                    check = LateSpectralMatrixDetail(256).cuda()
                    actual, aux = check(
                        base, b["packed"], b["variance"], b["colors"], b["wb"], return_aux=True
                    )
                    p, g = rgb_losses(actual, b["target"], b["variance"], config)
                    s = check.spectral_supervision(b["target"], b["colors"], aux)
                    actual_loss = domain_weight * (
                        p + config["gradient_weight"] * g + config["spectral_weight"] * s
                    )
                    actual_pixel16, actual_gradient16 = rgb_losses(
                        actual,
                        b["target"],
                        b["variance"],
                        {**config, "noise_unit_floor_DN16": floor16},
                    )
                    actual_spectral16 = (
                        (aux["spectral_delta"] - desired).abs().square() / variance16 * band
                    ).sum() / denominator
                    actual16 = domain_weight * (
                        actual_pixel16
                        + config["gradient_weight"] * actual_gradient16
                        + config["spectral_weight"] * actual_spectral16
                    )
                    parity = {}
                    for j, (key, value) in enumerate(
                        [("legacy_total", actual_loss), ("floor16_total", actual16)]
                    ):
                        actual_gradients = dict(
                            zip(
                                dict(check.named_parameters()),
                                torch.autograd.grad(
                                    value, tuple(check.parameters()), retain_graph=j == 0
                                ),
                                strict=True,
                            )
                        )
                        true_vector = torch.cat(
                            (
                                actual_gradients["frequency_real_bias"].flatten(),
                                actual_gradients["frequency_out.weight"].flatten(),
                            )
                        )
                        assert all(
                            g.count_nonzero() == 0
                            for name, g in actual_gradients.items()
                            if name not in ["frequency_real_bias", "frequency_out.weight"]
                        )
                        diff = projected[key] - true_vector
                        relative = float(
                            diff.double().norm() / true_vector.double().norm().clamp_min(1e-30)
                        )
                        assert relative < 5e-5, relative
                        parity[key] = {
                            "relative_L2_difference": relative,
                            "maximum_absolute_difference": float(diff.abs().max()),
                            "all_other_parameter_gradients_exact_zero": True,
                        }
                        if key == "legacy_total":
                            legacy_bias = actual_gradients["frequency_real_bias"].detach().clone()
                    true_bias = legacy_bias
                    manual_bias = matrix_cotangent(
                        gradients["legacy_total"], innovation, factor
                    ).real.sum((0, 3, 4))
                    torch.testing.assert_close(manual_bias, true_bias, rtol=2e-5, atol=1e-8)
                    assert torch.equal(actual, base) and torch.equal(
                        aux["support"], aux["support"].new_full(aux["support"].shape, 0.5)
                    )
                    assert torch.equal(p, pixel) and torch.equal(g, gradient)
                    torch.testing.assert_close(
                        domain_weight * config["spectral_weight"] * s,
                        terms["legacy_spectral"],
                        rtol=1e-6,
                        atol=1e-8,
                    )
                    checks.append(
                        {
                            "step": item["step"],
                            "domain": item["metadata"]["domain"],
                            "loss_matches": True,
                            "all1040_initial_output_parameter_gradients": parity,
                            "maximum_matrix_bias_gradient_difference": float(
                                (manual_bias - true_bias).abs().max()
                            ),
                        }
                    )
                    del (
                        check,
                        actual,
                        aux,
                        actual_loss,
                        true_bias,
                        manual_bias,
                        p,
                        g,
                        s,
                        actual_gradients,
                        true_vector,
                        diff,
                        actual_pixel16,
                        actual_gradient16,
                        actual_spectral16,
                        actual16,
                        legacy_bias,
                    )
                masks = [
                    ((ratio >= low) & (ratio < high if high is not None else True) & (band > 0))
                    for low, high in plan["clean_power_noise_ratio_bins"]
                ]
                vector_names = list(projected)
                vector = torch.stack([projected[k] for k in vector_names]).cpu().numpy()
                vectors.append(vector)
                parameter_rows.append(
                    {
                        "step": item["step"],
                        "domain": item["metadata"]["domain"],
                        "noise": item["metadata"]["noise"],
                        "batch": item["arrays"],
                        "parameter_squared_norm": {
                            name: float(projected[name].double().square().sum())
                            for name in vector_names
                        },
                    }
                )
                directional = {
                    name: -(grad.conj() * desired).real.sum(1) for name, grad in gradients.items()
                }
                for case_index, case in enumerate(item["metadata"]["cases"]):
                    selected = slice(case_index * count, (case_index + 1) * count)
                    entry = {
                        "batch_step": item["step"],
                        "batch": item["arrays"],
                        "domain": item["metadata"]["domain"],
                        "id": case["id"],
                        "pattern": case["pattern"],
                        "source_kind": case["source"]["kind"],
                        "present": case["source"].get("recipe", {}).get("present"),
                        "native_size": int(base.shape[-1]),
                        "noise": item["metadata"]["noise"],
                        "bins": [],
                    }
                    for mask in masks:
                        mask = mask[selected]

                        def reduce(values, selected=selected, mask=mask):
                            return float(values[selected].double()[mask].sum())

                        entry["bins"].append(
                            {
                                "active_bins": int(mask.sum()),
                                "clean_power": reduce(clean.abs().square().sum(1)),
                                "desired_power": reduce(desired.abs().square().sum(1)),
                                "focus_weight_sum": reduce(focus),
                                "matrix_field_gradient_squared_norm": {
                                    k: reduce(v) for k, v in energy.items()
                                },
                                "descent_dot_desired_coefficient_direction": {
                                    k: reduce(v) for k, v in directional.items()
                                },
                            }
                        )
                    rows.append(entry)
                    trace.write(json.dumps(entry, allow_nan=False) + "\n")
                trace.flush()
                progress = {
                    "batches": index + 1,
                    "observations": len(rows),
                    "last_original_step": item["step"],
                    "owner": owner,
                    "CUDA_peak_GiB": torch.cuda.max_memory_allocated() / 2**30,
                }
                save(
                    root / "status-v1.json",
                    {"status": "running-fixed-gradient-diagnostic", **progress},
                )
                if index == 0 or (index + 1) % 10 == 0:
                    print(json.dumps(progress), flush=True)
                del (
                    arrays,
                    b,
                    base,
                    observed,
                    parent,
                    clean,
                    noise,
                    variance,
                    ratio,
                    focus,
                    layouts,
                    descriptor,
                    factor,
                    innovation,
                    desired,
                    delta,
                    correction,
                    output,
                    pixel,
                    gradient,
                    output_spectrum,
                    coefficient_error,
                    output_error,
                    terms,
                    gradients,
                    energy,
                    directional,
                    masks,
                    projected,
                    hidden,
                    innovation_descriptor,
                    variance16,
                    pixel16,
                    gradient16,
                )
        assert len(rows) == 400 and len(checks) == 10
        assert all(torch.equal(v.cpu(), initial[k]) for k, v in module.state_dict().items())
        np.savez_compressed(
            root / "parameter-gradients-v1.npz",
            gradients=np.stack(vectors),
            original_steps=np.array([x["step"] for x in parameter_rows]),
        )
        save(
            root / "result-v1.json",
            {
                "status": "completed-zero-head-gradient-diagnostic",
                "plan": ref(path),
                "rows": rows,
                "preflight": checks,
                "parameter_rows": parameter_rows,
                "parameter_vectors": ref(root / "parameter-gradients-v1.npz"),
                "parameter_vector_names": vector_names,
                "parameter_vector_layout": "16 real matrix biases followed by32x32 frequency_out weight; all other parameter gradients are exactly zero at initialization",
                "additional_frequency_hidden_convolution_calls": 100,
                "neural_forward_calls": 10,
                "optimizer_updates": 0,
                "new_parent_DINO_calls": 0,
                "new_noise_draws": 0,
                "model_state_unchanged": True,
                "owner": owner,
                "CUDA_peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                "recorded_unix_UTC": time.time(),
                "scope": plan["scope"],
            },
        )
        save(
            root / "status-v1.json",
            {"status": "completed-zero-head-gradient-diagnostic", **progress},
        )
    except BaseException as error:
        save(root / "failure-v1.json", {"error": repr(error), "progress": progress, "owner": owner})
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "run"])
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args.path)
    else:
        run(args.path.absolute())
