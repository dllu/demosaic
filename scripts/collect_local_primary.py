"""Matched CPU primary panels for local full models using exact canonical inputs."""

import argparse
import math
import os
import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import psutil
import torch
from profile_raw_kernel_inference import model_hash

from demosaic.experiments.artifacts import checked, read_json, reference, verify_plan, write_json
from demosaic.frozen_encoder_replay import FrozenDinoReplay
from demosaic.inference import load_checkpoint
from demosaic.metrics import quality_metrics
from demosaic.precision import ieee_fp32
from demosaic.prediction_archive import fingerprint
from demosaic.real_suite import measured_sensor_psnr
from demosaic.suite import summarize

ARGUMENTS = ("packed", "variance", "colors", "wb", "matrix")


def numbers(metrics):
    return {
        key: [float(v) if math.isfinite(float(v)) else None for v in values]
        for key, values in metrics.items()
    }


def summarize_stages(metric_rows):
    summaries = {}
    for stage, rows in metric_rows.items():
        if stage == "photo":
            summaries[stage] = summarize(rows)
            continue
        groups = defaultdict(list)
        for row in rows:
            groups[row["model"], row["scene"], row["pair"], row["pattern"]].append(row)
        pairs = []
        for (arm, scene, pair, pattern), values in groups.items():
            keys = values[0]["metrics"]
            metrics = {
                key: [row["metrics"][key] for row in values if row["metrics"][key] is not None]
                for key in keys
            }
            pairs.append(
                {
                    "model": arm,
                    "id": scene,
                    "kind": "real",
                    "condition": pair,
                    "pattern": pattern,
                    "metrics": {
                        key: float(np.mean(v)) if v else None for key, v in metrics.items()
                    },
                }
            )
        summaries[stage] = {
            "per_pair": pairs,
            **summarize(
                pairs, comparison_metrics=("sensor_psnr", "ahd_srgb_psnr", "ahd_srgb_ssim")
            ),
        }
    return summaries


@torch.inference_mode()
def collect(plan_path):
    plan = read_json(plan_path)
    verify_plan(plan)
    assert reference(__file__) == plan["driver"]
    assert not torch.cuda.is_initialized()
    os.sched_setaffinity(0, plan["CPU_affinity"])
    os.nice(10)
    torch.set_num_threads(plan["CPU_threads"])
    root = Path(plan["root"])
    output = root / "collection"
    output.mkdir()
    write_json(
        output / "owner.json",
        {
            "pid": os.getpid(),
            "create_time": psutil.Process().create_time(),
            "plan": reference(plan_path),
        },
    )
    if psutil.virtual_memory().available < plan["minimum_start_RAM_GiB"] * 2**30:
        raise RuntimeError("CPU local primary RAM admission unavailable")
    canonical = read_json(checked(plan["canonical_inputs"]))
    assert canonical["all_input_witnesses_exact"]
    selected = [
        r
        for stage in ["known", "unseen", "photo"]
        for r in canonical["records"]
        if r["stage"] == stage
    ]
    assert Counter(r["stage"] for r in selected) == {"photo": 3108, "known": 24, "unseen": 30}
    if plan["kind"] == "preflight":
        keys = {tuple(v) for v in plan["selected_cases"]}
        selected = [r for r in selected if (r["stage"], r["batch"]) in keys]
        assert len(selected) == len(keys) == 3
    else:
        assert plan["kind"] == "full" and len(selected) == 3162
        qualified = read_json(checked(plan["preflight"]))
        assert qualified["all_complete"] and qualified["kind"] == "preflight"
        assert qualified["cases"] == 3 and qualified["models"] == plan["models"]
    models, before, counters = {}, {}, {}
    for arm, specification in plan["models"].items():
        model, state = load_checkpoint(checked(specification["checkpoint"]), "cpu")
        assert state["loaded_sha256"] == specification["checkpoint"]["sha256"]
        assert state["step"] == specification["step"] and "ema" in state
        actual = model.restoration_state_dict()
        assert len(actual) == len(state["ema"]) == 91
        assert all(torch.equal(value, state["ema"][key]) for key, value in actual.items())
        model.eval().to(memory_format=torch.contiguous_format)
        assert model_hash(model.context.backbone) == plan["DINO_sha256"]
        models[arm] = model
        before[arm] = model_hash(model)
        counters[arm] = {"root": 0}
        model.register_forward_pre_hook(
            lambda *_, c=counters[arm]: c.__setitem__("root", c["root"] + 1)
        )
        del state, actual
    replay = FrozenDinoReplay([m.context.backbone for m in models.values()])
    rng = torch.get_rng_state().clone()
    parent_checks = {(r["stage"], r["batch"]): r for r in plan.get("parent_reference_checks", [])}
    metric_rows, cases, comparisons = defaultdict(list), [], []
    totals = {
        "root": 0,
        "local_DINO_requests": 0,
        "local_DINO_executions": 0,
        "local_DINO_replays": 0,
    }
    began = time.monotonic()
    with ieee_fp32():
        for record in selected:
            key = record["stage"], record["batch"]
            if psutil.virtual_memory().available < plan["minimum_runtime_RAM_GiB"] * 2**30:
                raise RuntimeError("CPU local primary runtime RAM floor reached")
            if shutil.disk_usage(root).free < plan["minimum_disk_GiB"] * 2**30:
                raise RuntimeError("CPU local primary internal disk reserve reached")
            if time.monotonic() - began > plan["maximum_seconds"]:
                raise TimeoutError("CPU local primary deadline reached; no automatic retry")
            with np.load(checked(record["arrays"]), allow_pickle=False) as values:
                batch = {name: torch.from_numpy(values[name].copy()) for name in values.files}
            fingerprints = {name: fingerprint(batch[name]) for name in ARGUMENTS}
            assert fingerprints == {name: record["fingerprints"][name] for name in ARGUMENTS}
            noise = record["context"]["condition" if key[0] == "photo" else "noise"]
            folder = output / f"{key[0]}-{key[1]:05d}"
            folder.mkdir()
            variants = []
            with replay.group() as statistics:
                for arm, model in models.items():
                    model.set_noise(noise["shot"], noise["read"])
                    tick = time.monotonic()
                    prediction = model(*(batch[name] for name in ARGUMENTS))
                    inference_seconds = time.monotonic() - tick
                    assert prediction.dtype == torch.float32 and torch.isfinite(prediction).all()
                    if arm == plan["parent_label"] and key in parent_checks:
                        comparison = parent_checks[key]
                        assert comparison["canonical_arrays"] == record["arrays"]
                        assert comparison["checkpoint"] == plan["models"][arm]["checkpoint"]
                        previous = np.load(checked(comparison["prediction"]), allow_pickle=False)
                        np.testing.assert_array_equal(prediction.numpy(), previous)
                        comparisons.append(
                            {
                                "stage": key[0],
                                "batch": key[1],
                                "all_output_values_bitexact": True,
                                "previous_prediction": comparison["prediction"],
                            }
                        )
                    path = folder / (arm + "-RGB-f32.npy")
                    with path.open("xb") as stream:
                        np.save(stream, prediction.numpy(), allow_pickle=False)
                    border = 8 if key[0] == "photo" else 32
                    region = (..., slice(border, -border), slice(border, -border))
                    tick = time.monotonic()
                    # Retain the original formulas; avoid the host's oneDNN
                    # grouped-Gaussian SSIM JIT failure on these layouts.
                    with torch.backends.mkldnn.flags(enabled=False):
                        target = batch["target" if key[0] == "photo" else "reference_rgb"]
                        measured = quality_metrics(
                            prediction[region], target[region], batch["wb"], batch["matrix"]
                        )
                    if key[0] != "photo":
                        sensor, count = measured_sensor_psnr(
                            prediction[region],
                            batch["sensor_reference"][region],
                            batch["sensor_mask"][region],
                        )
                        measured = {
                            "sensor_psnr": sensor,
                            "reference_samples": count,
                            **{"ahd_" + name: value for name, value in measured.items()},
                        }
                    values = numbers(measured)
                    rows = []
                    for index, identity in enumerate(record["context"]["ids"]):
                        row = {
                            "id": identity,
                            "model": arm,
                            "pattern": record["context"]["pattern"],
                            "metrics": {name: v[index] for name, v in values.items()},
                        }
                        if key[0] == "photo":
                            row.update(
                                kind="synthetic" if identity.startswith("synthetic-") else "photo",
                                condition=noise["name"],
                            )
                        else:
                            row.update(
                                scene=record["context"]["scene"],
                                pair=record["context"]["raw_source"]["sha256"],
                            )
                        rows.append(row)
                    if arm == plan["parent_label"] and key in parent_checks:
                        assert rows == parent_checks[key]["rows"]
                        comparisons[-1]["all_metric_rows_bitexact"] = True
                    variants.append(
                        {
                            "arm": arm,
                            "checkpoint": plan["models"][arm]["checkpoint"],
                            "weights": "EMA",
                            "prediction": reference(path),
                            "rows": rows,
                            "inference_seconds": inference_seconds,
                            "metric_seconds": time.monotonic() - tick,
                        }
                    )
                    metric_rows[key[0]].extend(rows)
            assert statistics == {
                "requests": len(models),
                "executions": 1,
                "replays": len(models) - 1,
            }
            assert fingerprints == {name: fingerprint(batch[name]) for name in ARGUMENTS}
            result = {
                "stage": key[0],
                "batch": key[1],
                "canonical_arrays": record["arrays"],
                "input_fingerprints": fingerprints,
                "variants": variants,
                "new_root_calls": len(models),
                "local_frozen_DINO": dict(statistics),
            }
            write_json(folder / "result.json", result)
            cases.append(reference(folder / "result.json"))
            totals["root"] += len(models)
            for name in ["requests", "executions", "replays"]:
                totals["local_DINO_" + name] += statistics[name]
            write_json(
                output / "progress.json",
                {
                    "completed_cases": len(cases),
                    "total_cases": len(selected),
                    "stage": key[0],
                    "seconds": time.monotonic() - began,
                    "counts": totals,
                },
                replace=True,
            )
            print(key[0], key[1], len(cases), "of", len(selected), flush=True)
    after = {arm: model_hash(model) for arm, model in models.items()}
    assert (
        before == after
        and torch.equal(rng, torch.get_rng_state())
        and not torch.cuda.is_initialized()
    )
    assert all(c["root"] == len(selected) for c in counters.values())
    assert len(comparisons) == len(parent_checks)
    write_json(
        output / "result.json",
        {
            "plan": reference(plan_path),
            "kind": plan["kind"],
            "all_complete": True,
            "cases": len(cases),
            "case_records": cases,
            "models": plan["models"],
            "summaries": summarize_stages(metric_rows),
            "counts": totals,
            "parent_reference_checks": comparisons,
            "seconds": time.monotonic() - began,
            "full_model_before": before,
            "full_model_after": after,
            "CPU_rng_unchanged": True,
            "scope": "Same-CPU EMA local full models, exact canonical historic inputs/targets/noise, B4 preserved. Shared checked frozen local DINO; no scene context/RAW decode/new corruption/GPU/optimizer work.3-case preflight is not a primary score; only full3162 cases comprise427-photo plus known/unseen primary panels. Unchanged metric formulas/reference CPU SSIM; independent AHD camera RGB is auxiliary, not exact GT. Actual native review and source-bound history publication separate.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    collect(parser.parse_args().plan)
