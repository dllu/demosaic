"""Observe the trained spectral gate and fixed counterfactuals; no training."""

import argparse
import gc
import math
import shutil
import time
from pathlib import Path

import diagnose_texture_response as probe
import numpy as np
import psutil
import torch
import yaml
from evaluate_texture_candidates import flat_metrics
from profile_raw_kernel_inference import model_hash
from train_directional_bank_trial import read, ref, save

from demosaic.cfa import malvar
from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.raw_spectral import spectral_innovation, spectral_mask
from demosaic.reporting import display_crop, save_triplet
from demosaic.safety import writable_path
from demosaic.suite import observation


def fingerprint(batch):
    import hashlib

    h = hashlib.sha256()
    for name, value in sorted(batch.items()):
        value = value.detach().cpu().contiguous()
        h.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        h.update(value.numpy().tobytes(order="C"))
    return h.hexdigest()


def guard(plan):
    for item in plan["inputs"]:
        assert ref(item["path"]) == item, item["path"]
    for name, digest in plan["frozen_files"].items():
        assert ref(name)["sha256"] == digest, name
    for item in plan["completed_predecessors"]:
        state = read(item["status"]["path"])
        assert state["controller"] == item["owner"] and state["status"] == item["terminal"]
        try:
            proc = psutil.Process(item["owner"]["pid"])
            assert (
                proc.create_time() != item["owner"]["created"]
                or proc.status() == psutil.STATUS_ZOMBIE
            )
        except psutil.NoSuchProcess:
            pass


def resources(plan):
    assert psutil.virtual_memory().available > 24 * 2**30
    assert shutil.disk_usage(plan["root"]).free > 500 * 2**30
    assert shutil.disk_usage("/home/dllu/proj/demosaic").free > 64 * 2**30


def key(row):
    return tuple(
        row[k] for k in ("kind", "level", "contrast", "period", "condition", "pattern", "draw")
    )


@torch.inference_mode()
def components(model, batch, device):
    branch = model.pretrained_rgb.raw_spectral
    captured = {}

    def capture(_module, args, output):
        captured["args"], captured["output"] = args, output

    handle = branch.register_forward_hook(capture)
    try:
        with amp_context(device, dtype="float32"):
            full = model(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
    finally:
        handle.remove()
    args = captured["args"]
    assert torch.equal(full, captured["output"])
    with amp_context(device, dtype="float32"):
        replay = branch(*args)
        base, packed, variance, colors, features, wb = args
        pooled = features.float().mean((-2, -1))
        gate = torch.nn.functional.linear(pooled, branch.weight, branch.bias).tanh()
        delta = spectral_innovation(base, packed, variance, colors, wb)
        _spectrum, mask = spectral_mask(packed, variance)
        assert torch.equal(replay, full)
        assert torch.equal(base.float() + gate[..., None, None] * delta, full)
        unit = base.float() + delta
    assert not branch._forward_hooks
    values = {
        "full": full,
        "base": base,
        "unit": unit,
        "innovation": delta,
        "gate": gate,
        "pooled": pooled,
        "mask": mask,
    }
    assert all(torch.isfinite(v).all() for v in values.values())
    return {k: v.float().cpu() for k, v in values.items()}


@torch.inference_mode()
def main(plan_path, output, device, preflight):
    plan = read(plan_path)
    guard(plan)
    resources(plan)
    root = writable_path(output)
    assert root.is_relative_to(Path(plan["root"]))
    root.mkdir(parents=True, exist_ok=False)
    (root / "arrays").mkdir()
    assert ref(__file__) == plan["worker"]
    torch.set_num_threads(2 if device == "cpu" else 4)
    device = torch.device(device)
    if device.type == "cuda":
        assert not preflight
        prior = read(Path(plan["root"]) / "cpu-preflight/summary.json")
        assert prior["status"] == "completed-CPU-spectral-hook-preflight-no-quality-decision"
        assert prior["driver"] == plan["worker"]
        assert psutil.virtual_memory().available > 40 * 2**30
        device = torch.device("cuda", torch.cuda.current_device())
        torch.cuda.set_per_process_memory_fraction(
            16 * 2**30 / torch.cuda.get_device_properties(device).total_memory, device
        )
        torch.set_float32_matmul_precision("high")
        torch.backends.cudnn.benchmark = True
    else:
        assert preflight and not torch.cuda.is_initialized()
    started = time.monotonic()
    protocol = yaml.safe_load(Path(plan["protocol"]["path"]).read_text())
    size, roi, draws = (
        (64, [8, 8, 48, 48], 1) if preflight else (probe.SIZE, probe.ROI, probe.DRAWS)
    )
    specs = (
        [("carrier", 0.01, 0.1, 8), ("carrier", 0.18, 0.02, 16), ("flat", 0.18, 0, None)]
        if preflight
        else [
            ("carrier", level, contrast, period)
            for level in probe.LEVELS
            for contrast in probe.CONTRASTS
            for period in probe.PERIODS
        ]
        + [("flat", level, 0, None) for level in probe.LEVELS]
    )
    conditions = [
        next(c for c in protocol["conditions"] if c["name"] == name) for name in probe.CONDITIONS
    ]
    patterns = ["RGGB"] if preflight else protocol["patterns"]
    original = {
        (key(row), row["model"]): row["metrics"]
        for row in [
            read_row(line) for line in Path(plan["original_cases"]["path"]).read_text().splitlines()
        ]
    }
    rows, statistics, crops, errors = [], [], [], {}
    cpu_rng = torch.get_rng_state().clone()
    cuda_rng = torch.cuda.get_rng_state(device).clone() if device.type == "cuda" else None
    with torch.random.fork_rng(devices=[device.index] if device.type == "cuda" else []):
        model, state = load_checkpoint(plan["checkpoint"]["path"], device)
        assert state["loaded_sha256"] == plan["checkpoint"]["sha256"] and state["step"] == 4000
        del state
        model.eval().requires_grad_(False)
        if device.type == "cuda":
            model.to(memory_format=torch.channels_last)
        before, dino = model_hash(model), model_hash(model.context.backbone)
        assert dino == plan["DINO_sha256"]
        branch = model.pretrained_rgb.raw_spectral
        assert branch.weight.numel() + branch.bias.numel() == 68
        head = {
            "weight": branch.weight.detach().cpu().numpy(),
            "bias": branch.bias.detach().cpu().numpy(),
        }
        with (root / "per-case.jsonl").open("x") as stream:
            for kind, level, contrast, period in specs:
                coord = torch.arange(size, dtype=torch.float32)
                rgb = (
                    (level * (1 + contrast * (coord * (2 * math.pi / period)).cos()))[
                        None, None, None
                    ]
                    .expand(draws, 3, size, size)
                    .clone()
                    if kind == "carrier"
                    else torch.full((draws, 3, size, size), level)
                )
                ids = [
                    f"carrier-l{level}-c{contrast}-p{period}-draw{i}"
                    if kind == "carrier"
                    else f"flat-l{level}-draw{i}"
                    for i in range(draws)
                ]
                for condition in conditions:
                    model.set_noise(condition["shot"], condition["read"])
                    for pattern in patterns:
                        assert time.monotonic() - started < plan["timeout_seconds"]
                        resources(plan)
                        cpu = observation(
                            rgb,
                            ids,
                            condition,
                            pattern,
                            protocol["white_balance"],
                            protocol["camera_to_srgb"],
                            probe.SEED,
                        )
                        repeated = observation(
                            rgb,
                            ids,
                            condition,
                            pattern,
                            protocol["white_balance"],
                            protocol["camera_to_srgb"],
                            probe.SEED,
                        )
                        digest = fingerprint(cpu)
                        assert digest == fingerprint(repeated)
                        batch = {k: v.to(device) for k, v in cpu.items()}
                        values = components(model, batch, device)
                        noisy = malvar(cpu["packed"], cpu["colors"], cpu["wb"])
                        target = probe.linear_srgb(cpu["target"], cpu["wb"], cpu["matrix"])
                        predictions = {
                            "full": values["full"],
                            "base": values["base"],
                            "unit": values["unit"],
                            "malvar": noisy,
                        }
                        metrics_by_mode = {}
                        for mode, prediction in predictions.items():
                            linear = probe.linear_srgb(prediction, cpu["wb"], cpu["matrix"])
                            metrics = (
                                probe.response_metrics(linear, target, period, roi)
                                if kind == "carrier"
                                else flat_metrics(linear, target, roi)
                            )
                            metrics_by_mode[mode] = metrics
                            for draw in range(draws):
                                row = {
                                    "kind": kind,
                                    "level": level,
                                    "contrast": contrast,
                                    "period": period,
                                    "condition": condition["name"],
                                    "pattern": pattern,
                                    "draw": draw,
                                    "model": mode,
                                    "metrics": {k: v[draw] for k, v in metrics.items()},
                                }
                                if not preflight and mode in ["full", "malvar"]:
                                    label = plan["original_label"] if mode == "full" else "malvar"
                                    previous = original[(key(row), label)]
                                    for name, value in row["metrics"].items():
                                        error = abs(value - previous[name])
                                        errors[mode + "/" + name] = max(
                                            errors.get(mode + "/" + name, 0), error
                                        )
                                        bound = (
                                            0
                                            if mode == "malvar"
                                            else (
                                                plan["gain_replay_atol"]
                                                if "gain" in name or name == "amplitude_ratio"
                                                else plan["absolute_replay_atol"]
                                            )
                                        )
                                        assert error <= bound, (row, name, error, bound)
                                assert all(math.isfinite(v) for v in row["metrics"].values())
                                rows.append(row)
                                import json

                                stream.write(json.dumps(row, allow_nan=False) + "\n")
                        stat = {
                            "kind": kind,
                            "level": level,
                            "contrast": contrast,
                            "period": period,
                            "condition": condition["name"],
                            "pattern": pattern,
                            "input_sha256": digest,
                            "gate": values["gate"].flatten().tolist(),
                            "nonzero_mask_bins": (values["mask"] > 0)
                            .sum((-2, -1))
                            .flatten()
                            .tolist(),
                            "censored_input_fraction": float(
                                (cpu["packed"] >= 1 - 0.5 / 65535).float().mean()
                            ),
                            "full_branch_and_cut_replay_exact": True,
                        }
                        if kind == "carrier":
                            delta_linear = probe.linear_srgb(
                                values["innovation"], cpu["wb"], cpu["matrix"]
                            )
                            delta_gain = probe.response_metrics(delta_linear, target, period, roi)[
                                "in_phase_gain"
                            ]
                            full_gain, base_gain, unit_gain = [
                                np.asarray(metrics_by_mode[k]["in_phase_gain"])
                                for k in ["full", "base", "unit"]
                            ]
                            gate = values["gate"].flatten().numpy().astype(np.float64)
                            identity_error = float(
                                np.max(
                                    np.abs(full_gain - base_gain - gate * np.asarray(delta_gain))
                                )
                            )
                            assert identity_error <= plan["gain_replay_atol"]
                            stat.update(
                                innovation_signed_gain=delta_gain,
                                known_carrier_mask_weight=values["mask"][
                                    :, 0, 0, size // period
                                ].tolist(),
                                gain_decomposition_max_error=identity_error,
                                unit_gain_decomposition_max_error=float(
                                    np.max(np.abs(unit_gain - base_gain - np.asarray(delta_gain)))
                                ),
                            )
                            assert (
                                stat["unit_gain_decomposition_max_error"]
                                <= plan["gain_replay_atol"]
                            )
                        number = len(statistics)
                        arrays = root / "arrays" / f"batch-{number:03d}.npz"
                        np.savez_compressed(
                            arrays,
                            **{k: v.numpy() for k, v in cpu.items()},
                            **{k: v.numpy() for k, v in values.items()},
                            head_weight=head["weight"],
                            head_bias=head["bias"],
                        )
                        stat["arrays"] = ref(arrays)
                        statistics.append(stat)
                        selected = (
                            kind == "carrier"
                            and (level, contrast, period) in [(0.01, 0.1, 8), (0.18, 0.02, 16)]
                        ) or (kind == "flat" and level == 0.18)
                        if (
                            not preflight
                            and selected
                            and condition["name"] == "iso12800-prior"
                            and pattern == "RGGB"
                        ):
                            for mode in ["full", "base", "unit"]:
                                crops.append(
                                    save_triplet(
                                        root,
                                        ids[0] + ":" + mode,
                                        [
                                            (
                                                name,
                                                display_crop(
                                                    value[:1], cpu["wb"][:1], cpu["matrix"][:1], roi
                                                ),
                                            )
                                            for name, value in [
                                                ("Noisy (Malvar)", noisy),
                                                (mode, predictions[mode]),
                                                ("GT (analytic)", cpu["target"]),
                                            ]
                                        ],
                                        caption=ids[0] + " / V89 / " + mode,
                                        metadata={
                                            "source_id": ids[0],
                                            "source": {
                                                "kind": kind,
                                                "level": level,
                                                "contrast": contrast,
                                                "period": period,
                                                "seed": probe.SEED,
                                            },
                                            "evaluation_tile_xywh": roi,
                                            "condition": condition,
                                            "pattern": pattern,
                                            "white_balance": protocol["white_balance"],
                                            "camera_to_srgb": protocol["camera_to_srgb"],
                                            "display_exposure": 1,
                                            "checkpoint_sha256": plan["checkpoint"]["sha256"],
                                            "model_label": "V89/" + mode,
                                            "reference": "Exact analytic target. Base and unit are fixed diagnostic interventions, not separately trained methods.",
                                        },
                                    )
                                )
                        stream.flush()
                print(
                    {
                        "event": "completed-spec",
                        "kind": kind,
                        "level": level,
                        "contrast": contrast,
                        "period": period,
                        "batches": len(statistics),
                    },
                    flush=True,
                )
        assert model_hash(model) == before and model_hash(model.context.backbone) == dino
        del model
        gc.collect()
    assert torch.equal(cpu_rng, torch.get_rng_state())
    assert cuda_rng is None or torch.equal(cuda_rng, torch.cuda.get_rng_state(device))
    assert len(statistics) == len(specs) * len(conditions) * len(patterns)
    assert len(rows) == len(statistics) * draws * 4
    assert preflight or (len(statistics) == 112 and len(rows) == 1792 and len(crops) == 9)
    guard(plan)
    result = {
        "status": "completed-CPU-spectral-hook-preflight-no-quality-decision"
        if preflight
        else "completed-read-only-spectral-gate-component-diagnostic",
        "driver": ref(__file__),
        "plan": ref(plan_path),
        "checkpoint": plan["checkpoint"],
        "device": str(device),
        "preflight": preflight,
        "size": size,
        "roi_xywh": roi,
        "draws": draws,
        "model_state_sha256_unchanged": before,
        "DINO_sha256_unchanged": dino,
        "CPU_CUDA_RNG_unchanged": True,
        "input_batches": len(statistics),
        "distinct_observations_per_mode": len(statistics) * draws,
        "case_component_statistics": statistics,
        "baseline_metric_replay_max_errors": errors,
        "per_case": ref(root / "per-case.jsonl"),
        "native_crops": crops,
        "carrier_summary": probe.summarize([x for x in rows if x["kind"] == "carrier"]),
        "flat_summary": probe.summarize([x for x in rows if x["kind"] == "flat"]),
        "new_training_updates": 0,
        "new_checkpoint_or_default": False,
        "scope": "Fixed V89 weights and actual original CPU-seeded analytic inputs. Exact final-module replay and zero/unit scalar interventions conditional on the same trunk output. Frequency/target enter diagnostics only, never the input-only spectral inference. No gate search, retraining, photo/real/GFX inference, architecture-effect estimate or promotion. Original neural metric replay is bounded, not necessarily bitwise.",
    }
    save(root / "summary.json", result)
    print({"status": result["status"], "rows": len(rows), "batches": len(statistics)}, flush=True)


def read_row(line):
    import json

    return json.loads(line)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("plan", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--preflight", action="store_true")
    a = p.parse_args()
    main(a.plan, a.output, a.device, a.preflight)
