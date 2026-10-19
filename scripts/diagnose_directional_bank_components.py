"""Read-only inference-component diagnosis; no retraining or quality promotion."""

import argparse
import gc
import hashlib
import json
import math
import os
import time
from pathlib import Path

import diagnose_texture_response as probe
import psutil
import torch
import yaml
from evaluate_texture_candidates import flat_metrics
from profile_raw_kernel_inference import model_hash

from demosaic.inference import load_checkpoint
from demosaic.precision import amp_context
from demosaic.suite import observation


def read(path):
    return json.loads(Path(path).read_text())


def ref(path):
    path = Path(path).absolute()
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"path": str(path), "sha256": digest}


def fingerprint(batch):
    digest = hashlib.sha256()
    for name, value in sorted(batch.items()):
        value = value.detach().cpu().contiguous()
        digest.update(name.encode() + str(value.dtype).encode() + str(tuple(value.shape)).encode())
        digest.update(value.numpy().tobytes())
    return digest.hexdigest()


def save(path, value):
    path = Path(path)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")
    temporary.replace(path)


@torch.inference_mode()
def components(model, batch, device):
    """Keep the trunk's return-features path intact; replay only its last module."""
    branch = model.pretrained_rgb.raw_directional
    assert branch is not None
    captured = {}

    def capture(_module, args, output):
        captured["args"], captured["output"] = args, output

    def capture_bank(_module, args, output):
        captured["bank_input"], captured["bank_logits"] = args[0], output

    handles = [branch.register_forward_hook(capture)]
    if branch.bank is not None:
        handles.append(branch.bank.register_forward_hook(capture_bank))
    try:
        with amp_context(device, dtype="float32"):
            full = model(*(batch[k] for k in ("packed", "variance", "colors", "wb", "matrix")))
    finally:
        for handle in handles:
            handle.remove()
    args = captured["args"]
    assert torch.equal(full, captured["output"]), "A later model operation invalidates this cut"
    with amp_context(device, dtype="float32"):
        replay = branch(*args)
    assert torch.equal(replay, full), "Exact module replay must pass before ablation"
    outputs = {"full": full, "base": args[0]}
    statistics = {
        "variance_floor_fraction": float((args[2] <= 1e-8).float().mean()),
        "censored_input_fraction": float((args[1] >= 1 - 0.5 / 65535).float().mean()),
        "full_replays_exactly": True,
        "model_output_is_final_directional_output": True,
    }
    if branch.bank is not None:
        # Execute the real module normally, then remove only its logit output.
        # Retaining the module avoids changing the trunk or candidate ordering.
        handle = branch.bank.register_forward_hook(
            lambda _module, _args, output: torch.zeros_like(output)
        )
        try:
            with amp_context(device, dtype="float32"):
                outputs["bank-logits-zero"] = branch(*args)
        finally:
            handle.remove()
        region = captured["bank_input"]
        logits = captured["bank_logits"]
        statistics.update(
            bank_input_clamped_fraction=float((region.abs() >= 8).float().mean()),
            bank_input_RMS=float(region.square().mean().sqrt()),
            bank_logit_RMS=float(logits.square().mean().sqrt()),
            bank_logit_abs_max=float(logits.abs().max()),
        )
    assert not branch._forward_hooks
    assert branch.bank is None or not branch.bank._forward_hooks
    assert all(torch.isfinite(value).all() for value in outputs.values())
    return {name: value.float().cpu() for name, value in outputs.items()}, statistics


@torch.inference_mode()
def main(plan_path, output, *, device="cpu", preflight=False):
    plan = read(plan_path)
    for item in plan["inputs"]:
        assert ref(item["path"]) == item
    for name, digest in plan["frozen_files"].items():
        assert ref(name)["sha256"] == digest, name
    output = Path(os.path.abspath(output))
    assert output.is_relative_to(Path(plan["root"]).absolute())
    assert Path(plan["root"]).is_relative_to(Path("/home/dllu/proj/demosaic"))
    output.mkdir(parents=True, exist_ok=False)
    os.nice(10)
    started = time.monotonic()
    torch.set_num_threads(4 if device == "cuda" else 2)
    device = torch.device(device)
    if device.type == "cuda":
        device = torch.device("cuda", torch.cuda.current_device())
        if not preflight:
            prior = read(Path(plan["root"]) / "cpu-preflight/summary.json")
            assert prior["status"] == "completed-CPU-hook-and-state-preflight-no-quality-result"
            assert prior["driver"]["sha256"] == plan["worker"]["sha256"]
        assert psutil.virtual_memory().available > 48 * 2**30
        torch.cuda.set_per_process_memory_fraction(
            min(16 * 2**30 / torch.cuda.get_device_properties(device).total_memory, 0.5),
            device,
        )
        torch.set_float32_matmul_precision("high")
        torch.backends.cudnn.benchmark = True
    else:
        assert not torch.cuda.is_initialized()
    size, roi = (64, [8, 8, 48, 48]) if preflight else (probe.SIZE, probe.ROI)
    protocol = yaml.safe_load(Path(plan["protocol"]["path"]).read_text())
    conditions = [
        next(c for c in protocol["conditions"] if c["name"] == name) for name in probe.CONDITIONS
    ]
    specs = (
        [("carrier", 0.01, 0.02, 4), ("carrier", 0.18, 0.02, 16), ("flat", 0.18, 0, None)]
        if preflight
        else [
            ("carrier", level, contrast, period)
            for level in probe.LEVELS
            for contrast in probe.CONTRASTS
            for period in probe.PERIODS
        ]
        + [("flat", level, 0, None) for level in probe.LEVELS]
    )
    original = {}
    if not preflight:
        with Path(plan["original_cases"]["path"]).open() as stream:
            for line in stream:
                row = json.loads(line)
                key = tuple(
                    row[k]
                    for k in (
                        "kind",
                        "level",
                        "contrast",
                        "period",
                        "condition",
                        "pattern",
                        "draw",
                        "model",
                    )
                )
                original[key] = row["metrics"]
    rows, case_stats, observations, weights = [], [], {}, []
    replay_errors = {}
    stream_path = output / "per-case.jsonl"
    with stream_path.open("x") as stream:
        for model_index, checkpoint in enumerate(plan["checkpoints"]):
            assert psutil.virtual_memory().available > 24 * 2**30
            model, state = load_checkpoint(checkpoint["path"], device)
            assert state["loaded_sha256"] == checkpoint["sha256"]
            label = f"{model_index}:{Path(state['config']['run']).name}:step-{state['step']}"
            del state
            model.eval().requires_grad_(False)
            if device.type == "cuda":
                model.to(memory_format=torch.channels_last)
            before = model_hash(model)
            dino_before = model_hash(model.context.backbone)
            assert dino_before == plan["DINO_sha256"]
            for kind, level, contrast, period in specs:
                coords = torch.arange(size, dtype=torch.float32)
                rgb = (
                    (level * (1 + contrast * (coords * (2 * math.pi / period)).cos()))[
                        None, None, None
                    ]
                    .expand(probe.DRAWS, 3, size, size)
                    .clone()
                    if kind == "carrier"
                    else torch.full((probe.DRAWS, 3, size, size), level)
                )
                ids = [
                    f"carrier-l{level}-c{contrast}-p{period}-draw{i}"
                    if kind == "carrier"
                    else f"flat-l{level}-draw{i}"
                    for i in range(probe.DRAWS)
                ]
                for condition in conditions:
                    model.set_noise(condition["shot"], condition["read"])
                    for pattern in protocol["patterns"]:
                        assert time.monotonic() - started < plan["timeout_seconds"]
                        cpu = observation(
                            rgb,
                            ids,
                            condition,
                            pattern,
                            protocol["white_balance"],
                            protocol["camera_to_srgb"],
                            probe.SEED,
                        )
                        key = json.dumps(
                            [kind, level, contrast, period, condition["name"], pattern]
                        )
                        digest = fingerprint(cpu)
                        if model_index == 0:
                            observations[key] = digest
                        else:
                            assert observations[key] == digest
                        batch = {k: v.to(device) for k, v in cpu.items()}
                        predictions, stats = components(model, batch, device)
                        case_stats.append(
                            {
                                "model": checkpoint["arm"],
                                "case": json.loads(key),
                                "input_sha256": digest,
                                **stats,
                            }
                        )
                        target = probe.linear_srgb(cpu["target"], cpu["wb"], cpu["matrix"])
                        for mode, prediction in predictions.items():
                            linear = probe.linear_srgb(prediction, cpu["wb"], cpu["matrix"])
                            metric = (
                                probe.response_metrics(linear, target, period, roi)
                                if kind == "carrier"
                                else flat_metrics(linear, target, roi)
                            )
                            for draw in range(probe.DRAWS):
                                values = {k: v[draw] for k, v in metric.items()}
                                assert all(math.isfinite(v) for v in values.values())
                                row = {
                                    "kind": kind,
                                    "level": level,
                                    "contrast": contrast,
                                    "period": period,
                                    "condition": condition["name"],
                                    "pattern": pattern,
                                    "draw": draw,
                                    "model": checkpoint["arm"] + "/" + mode,
                                    "metrics": values,
                                }
                                if mode == "full" and not preflight:
                                    reference = original[
                                        kind,
                                        level,
                                        contrast,
                                        period,
                                        condition["name"],
                                        pattern,
                                        draw,
                                        label,
                                    ]
                                    for name, value in values.items():
                                        error = abs(value - reference[name])
                                        replay_errors[name] = max(replay_errors.get(name, 0), error)
                                        tolerance = (
                                            plan["baseline_gain_atol"]
                                            if "gain" in name or name == "amplitude_ratio"
                                            else plan["baseline_absolute_error_atol"]
                                        )
                                        assert error <= tolerance, (row, name, error, tolerance)
                                rows.append(row)
                                stream.write(json.dumps(row, allow_nan=False) + "\n")
                        stream.flush()
                print(
                    json.dumps(
                        {
                            "model": checkpoint["arm"],
                            "kind": kind,
                            "level": level,
                            "contrast": contrast,
                            "period": period,
                            "rows": len(rows),
                        }
                    ),
                    flush=True,
                )
            assert model_hash(model) == before and model_hash(model.context.backbone) == dino_before
            weights.append(
                {
                    "checkpoint": checkpoint,
                    "full_state_sha256_before_and_after": before,
                    "DINO_sha256": dino_before,
                }
            )
            del model, predictions, batch, cpu, target, linear
            gc.collect()
            if device.type == "cuda":
                torch.cuda.empty_cache()
    expected_batches = len(specs) * len(conditions) * len(protocol["patterns"])
    assert len(observations) == expected_batches and len(case_stats) == expected_batches * 2
    assert len(rows) == expected_batches * probe.DRAWS * 5
    if not preflight:
        assert len(rows) == 2240 and len(observations) == 112
    for name, digest in plan["frozen_files"].items():
        assert ref(name)["sha256"] == digest
    result = {
        "status": "completed-CPU-hook-and-state-preflight-no-quality-result"
        if preflight
        else "completed-read-only-bank-component-diagnostic",
        "plan": ref(plan_path),
        "driver": ref(__file__),
        "device": str(device),
        "preflight": preflight,
        "size": size,
        "roi_xywh": roi,
        "observations": observations,
        "shared_inputs_exact": True,
        "weights_unchanged": weights,
        "input_batches": len(observations),
        "distinct_observations_per_mode": expected_batches * probe.DRAWS,
        "baseline_metric_replay_max_abs_errors": replay_errors,
        "case_component_statistics": case_stats,
        "per_case": ref(stream_path),
        "carrier_summary": probe.summarize([r for r in rows if r["kind"] == "carrier"]),
        "flat_summary": probe.summarize([r for r in rows if r["kind"] == "flat"]),
        "new_training_updates": 0,
        "new_checkpoint_or_default": False,
        "scope": "Fixed trained weights, paired original CPU observations, final-module replay and bank-output-zero intervention. The base uses the same trunk return-features path. Effects are conditional inference contributions, not independently retrained architecture effects or new restoration-quality/promotion evidence. Known carrier frequency enters scoring only.",
    }
    save(output / "summary.json", result)
    print(
        json.dumps(
            {"status": result["status"], "rows": len(rows), "observations": len(observations)}
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    main(args.plan, args.output, device=args.device, preflight=args.preflight)
